"""Runtime model and storage for Manual Energy Metering."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Any

from homeassistant.components.recorder.db_schema import Statistics
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    async_list_statistic_ids,
)
from homeassistant.components.recorder.tasks import RecorderTask
from homeassistant.components.recorder.util import get_instance, session_scope
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_METER_ID,
    CONF_METER_TYPE,
    CONF_UNIT,
    DOMAIN,
    METER_TYPE_GAS,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
    UNIT_KWH,
    UNIT_LITERS,
)
from .csv_transfer import (
    CsvTransferError,
    GasConversion,
    convert_meter_value,
    csv_unit_options,
    meter_unit_class,
)
from .interpolation import (
    DuplicateTimestampError,
    HourlyConsumption,
    HourlyStatisticsUpdate,
    Reading,
    changed_hourly_statistics,
    hourly_consumption,
    interpolate_ordered_value,
    remove_reading,
    replace_reading,
    upsert_reading,
    validate_readings,
)

_DELETE_BATCH_SIZE = 500


# Home Assistant exposes upserts, but no public API for deleting selected
# external-statistic hours. Queue this targeted delete with recorder imports.
@dataclass(slots=True)
class _DeleteStatisticsRowsTask(RecorderTask):
    """Delete selected external-statistic hours in the recorder thread."""

    statistic_id: str
    starts: tuple[datetime, ...]

    def run(self, instance: Any) -> None:
        """Delete only rows with the supplied exact hour timestamps."""
        with session_scope(session=instance.get_session()) as session:
            metadata = instance.statistics_meta_manager.get_many(
                session, statistic_ids={self.statistic_id}
            )
            if self.statistic_id not in metadata:
                return
            metadata_id = metadata[self.statistic_id][0]
            timestamps = [start.timestamp() for start in self.starts]
            for offset in range(0, len(timestamps), _DELETE_BATCH_SIZE):
                batch = timestamps[offset : offset + _DELETE_BATCH_SIZE]
                session.query(Statistics).filter(
                    Statistics.metadata_id == metadata_id,
                    Statistics.start_ts.in_(batch),
                ).delete(synchronize_session=False)


class ReadingError(ValueError):
    """A user-facing invalid reading error."""

    def __init__(self, translation_key: str, message: str) -> None:
        """Initialize an invalid reading error."""
        super().__init__(message)
        self.translation_key = translation_key


class ManualEnergyMetering:
    """Hold one manual meter's readings and Energy Dashboard statistics."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, name: str
    ) -> None:
        """Initialize a meter."""
        self.hass = hass
        self.entry = entry
        self.name = name
        self.meter_id: str = entry.data[CONF_METER_ID]
        self.meter_type: str = entry.data[CONF_METER_TYPE]
        self.unit: str = entry.data[CONF_UNIT]
        self.gas_conversion = (
            GasConversion.from_input(entry.data)
            if self.meter_type == METER_TYPE_GAS
            else None
        )
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}.{self.meter_id}"
        )
        self._readings: list[Reading] = []
        self._listeners: set[Callable[[], None]] = set()
        self._lock = asyncio.Lock()
        self._statistics_baseline: float | None = None
        self._statistics_excluded_hours: set[datetime] = set()
        self._statistics_import_source: str | None = None
        self.available_secondary_units = csv_unit_options(
            self.meter_type,
            self.unit,
            allow_gas_conversion=self.gas_conversion is not None,
        )[1:]
        self._secondary_statistics: dict[str, bool] = {}
        self.async_update_secondary_sensor: (
            Callable[[str, bool], Awaitable[None]] | None
        ) = None

    @property
    def statistic_id(self) -> str:
        """Return the external statistic ID exposed to the Energy Dashboard."""
        return f"{DOMAIN}:{self.meter_id}"

    @property
    def converted_statistic_id(self) -> str:
        """Return the stable external statistic ID reserved for converted gas."""
        return f"{self.statistic_id}_converted"

    @property
    def converted_statistics_unit(self) -> str | None:
        """Return the unit formerly offered by the single gas conversion toggle."""
        if self.gas_conversion is None:
            return None
        return UNIT_KWH if self.unit_class == "volume" else UNIT_LITERS

    @property
    def converted_statistics_enabled(self) -> bool:
        """Return the legacy gas toggle's current state."""
        return self.converted_statistics_unit in self.secondary_units

    @property
    def secondary_units(self) -> tuple[str, ...]:
        """Return enabled secondary units in the order used by the panel."""
        return tuple(
            unit for unit in self.available_secondary_units
            if self._secondary_statistics.get(unit)
        )

    @property
    def disabled_secondary_units(self) -> tuple[str, ...]:
        """Return previously selected units whose derived state must be removed."""
        return tuple(
            unit for unit, enabled in self._secondary_statistics.items() if not enabled
        )

    def secondary_statistic_id(self, unit: str) -> str:
        """Return a case-safe statistic ID, preserving the original gas ID."""
        if unit == self.converted_statistics_unit:
            return self.converted_statistic_id
        suffix = {"mWh": "milliwh", "MWh": "megawh"}.get(unit, unit.lower())
        return f"{self.statistic_id}_secondary_{suffix.replace('³', '3')}"

    def secondary_sensor_id(self, unit: str) -> str:
        """Return the registry unique ID for the secondary sensor."""
        return self.secondary_statistic_id(unit).split(":", 1)[1]

    @property
    def unit_class(self) -> str:
        """Return the recorder unit class for the configured meter unit."""
        return meter_unit_class(self.unit)

    @property
    def readings(self) -> tuple[Reading, ...]:
        """Return an immutable snapshot of readings."""
        return tuple(self._readings)

    @property
    def latest_reading(self) -> Reading | None:
        """Return the chronologically latest reading."""
        return self._readings[-1] if self._readings else None

    @property
    def statistics_baseline(self) -> float:
        """Return the fixed baseline used by the cumulative statistic."""
        return self._statistics_baseline or 0.0

    @property
    def excluded_statistics_hours(self) -> frozenset[datetime]:
        """Return imported hours that must remain absent from the statistic."""
        return frozenset(self._statistics_excluded_hours)

    @property
    def statistics_import_source(self) -> str | None:
        """Return the original statistic ID for a version 2 import."""
        return self._statistics_import_source

    def value_at(self, timestamp: datetime) -> float | None:
        """Return the linearly interpolated reading at a timestamp."""
        return interpolate_ordered_value(self._readings, timestamp)

    def is_interpolating_at(self, timestamp: datetime) -> bool:
        """Return whether the timestamp lies between the first and last readings."""
        return bool(
            self._readings
            and self._readings[0].timestamp < timestamp < self._readings[-1].timestamp
        )

    def convert_register(self, value: float, unit: str) -> float | None:
        """Convert an absolute reading, returning None if it cannot be represented."""
        try:
            return convert_meter_value(
                value, self.meter_type, self.unit, unit,
                gas_conversion=self.gas_conversion,
            )
        except CsvTransferError:
            # The absolute register can overflow even when its differences fit.
            return None

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an update listener."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            """Unregister the listener created by the enclosing call."""
            self._listeners.discard(listener)

        return remove_listener

    async def async_load(self) -> None:
        """Load readings and restore current or legacy secondary statistics."""
        stored = await self._store.async_load()
        if not stored:
            return

        loaded: list[Reading] = []
        for item in stored.get("readings", []):
            timestamp = dt_util.parse_datetime(item.get("timestamp", ""))
            if timestamp is None:
                continue
            loaded.append(Reading(dt_util.as_utc(timestamp), float(item["value"])))

        try:
            self._readings = validate_readings(loaded)
        except ValueError:
            # Do not make Home Assistant fail to start because of a manually edited
            # storage file. New writes will replace the invalid data.
            self._readings = []

        stored_baseline = stored.get("statistics_baseline")
        try:
            baseline = (
                float(stored_baseline) if stored_baseline is not None else None
            )
        except (TypeError, ValueError):
            baseline = None
        if baseline is None or not math.isfinite(baseline):
            baseline = self._readings[0].value if self._readings else None
        self._statistics_baseline = baseline

        excluded_hours: set[datetime] = set()
        for value in stored.get("statistics_excluded_hours", []):
            timestamp = dt_util.parse_datetime(value)
            if timestamp is None:
                continue
            timestamp = dt_util.as_utc(timestamp)
            if timestamp.minute or timestamp.second or timestamp.microsecond:
                continue
            excluded_hours.add(timestamp)
        self._statistics_excluded_hours = excluded_hours
        source = stored.get("statistics_import_source")
        self._statistics_import_source = (
            source.strip() if isinstance(source, str) and source.strip() else None
        )
        await self._async_restore_secondary_statistics(stored)

    async def _async_restore_secondary_statistics(self, stored: dict[str, Any]) -> None:
        """Restore selections and reconcile missing, outdated, or removed statistics."""
        legacy_unit = self.converted_statistics_unit
        migrate_legacy = (
            "secondary_statistics" not in stored
            and "converted_statistics" in stored
            and legacy_unit is not None
        )
        if migrate_legacy:
            assert legacy_unit is not None
            saved_conversion = stored["converted_statistics"]
            self._secondary_statistics = {legacy_unit: saved_conversion is not None}
        else:
            saved_conversion = stored.get("gas_conversion")
            selections = stored.get("secondary_statistics", {})
            if isinstance(selections, dict):
                self._secondary_statistics = {
                    unit: selected
                    for unit, selected in selections.items()
                    if unit in self.available_secondary_units
                    and isinstance(selected, bool)
                }

        existing_ids: set[str] = set()
        active_units = self.secondary_units
        if active_units:
            existing_ids = {
                item["statistic_id"]
                for item in await async_list_statistic_ids(
                    self.hass,
                    {self.secondary_statistic_id(unit) for unit in active_units},
                )
            }
        factors_changed = (
            self.gas_conversion is not None
            and saved_conversion != self.gas_conversion.as_input()
        )
        rebuild = tuple(
            unit
            for unit in active_units
            if self.secondary_statistic_id(unit) not in existing_ids
            or (factors_changed and meter_unit_class(unit) != self.unit_class)
        )
        if rebuild:
            statistics = await self.hass.async_add_executor_job(
                self._build_secondary_statistics, rebuild
            )
            for unit, rows in statistics.items():
                async_add_external_statistics(
                    self.hass, self._statistics_metadata(unit), rows
                )
        disabled_units = self.disabled_secondary_units
        if disabled_units:
            # Repeat saved removals if shutdown interrupted the recorder.
            get_instance(self.hass).async_clear_statistics(
                [self.secondary_statistic_id(unit) for unit in disabled_units]
            )
        if migrate_legacy or (factors_changed and active_units):
            await self._async_store_state(
                self._readings,
                self._statistics_baseline,
                self._statistics_excluded_hours,
                self._statistics_import_source,
                self._secondary_statistics,
            )

    async def async_set_converted_statistics(self, enabled: bool) -> None:
        """Apply a request from the legacy single gas conversion toggle."""
        if (unit := self.converted_statistics_unit) is None:
            raise ReadingError(
                "not_gas_meter", "Converted statistics are only available for gas."
            )
        await self.async_set_secondary_unit(unit, enabled)

    async def async_set_secondary_unit(self, unit: str, enabled: bool) -> None:
        """Persist a unit selection and add or remove its statistic and sensor."""
        if unit not in self.available_secondary_units:
            raise ReadingError(
                "invalid_secondary_unit", "Invalid secondary meter unit."
            )
        async with self._lock:
            if self._secondary_statistics.get(unit, False) == enabled:
                if self.async_update_secondary_sensor is not None:
                    await self.async_update_secondary_sensor(unit, enabled)
                return

            statistics_by_unit = (
                await self.hass.async_add_executor_job(
                    self._build_secondary_statistics, (unit,)
                )
                if enabled
                else {}
            )
            selections = {**self._secondary_statistics, unit: enabled}
            await self._async_store_state(
                self._readings,
                self._statistics_baseline,
                self._statistics_excluded_hours,
                self._statistics_import_source,
                selections,
            )
            self._secondary_statistics = selections
            if enabled:
                async_add_external_statistics(
                    self.hass, self._statistics_metadata(unit), statistics_by_unit[unit]
                )
            else:
                get_instance(self.hass).async_clear_statistics(
                    [self.secondary_statistic_id(unit)]
                )
            if self.async_update_secondary_sensor is not None:
                await self.async_update_secondary_sensor(unit, enabled)

    async def async_wait_for_pending_writes(self) -> None:
        """Let in-flight reading and option writes finish before a reload."""
        async with self._lock:
            return

    def validate_secondary_statistics_factors(self, conversion: GasConversion) -> None:
        """Raise CsvTransferError if new factors cannot represent the saved history."""
        maximum = 0.0
        if len(self._readings) >= 2:
            first = self._readings[0].value
            last = self._readings[-1].value
            baseline = self.statistics_baseline
            maximum = max(last - first, abs(first - baseline), abs(last - baseline))
        for unit in self.secondary_units:
            if meter_unit_class(unit) != self.unit_class:
                convert_meter_value(
                    maximum, self.meter_type, self.unit, unit, gas_conversion=conversion
                )

    def _build_secondary_statistics(
        self, units: tuple[str, ...]
    ) -> dict[str, list[StatisticData]]:
        """Recreate the selected hours and convert them into each requested unit."""
        buckets = tuple(
            bucket
            for bucket in hourly_consumption(self._readings, self._statistics_baseline)
            if bucket.start not in self._statistics_excluded_hours
        )
        return {unit: self._converted_statistics_rows(buckets, unit) for unit in units}

    async def async_add_reading(self, value: Any, timestamp: Any) -> Reading:
        """Validate, persist, and publish a reading."""
        reading = Reading(
            timestamp=self._normalize_timestamp(timestamp),
            value=self._normalize_value(value),
        )

        async with self._lock:
            try:
                updated = upsert_reading(self._readings, reading)
            except ValueError as err:
                raise ReadingError("non_monotonic", str(err)) from err
            await self._async_save_readings(updated)

        for listener in tuple(self._listeners):
            listener()
        return reading

    async def async_import_readings(
        self,
        items: list[dict[str, Any]],
        statistics_import: dict[str, Any] | None = None,
    ) -> None:
        """Persist a complete, validated set of readings for a new meter."""
        imported = [
            Reading(
                timestamp=self._normalize_timestamp(item.get("timestamp")),
                value=self._normalize_value(item.get("value")),
            )
            for item in items
        ]
        try:
            imported = validate_readings(imported)
        except ValueError as err:
            raise ReadingError("invalid_import", str(err)) from err

        async with self._lock:
            if self._readings:
                raise ReadingError(
                    "invalid_import",
                    "CSV readings can only initialize an empty meter",
                )
            excluded_hours: set[datetime] | None = None
            source: str | None = None
            if statistics_import is not None:
                source_value = statistics_import.get("source_statistic_id")
                if not isinstance(source_value, str) or not source_value.strip():
                    raise ReadingError(
                        "invalid_import", "Missing source statistic ID"
                    )
                source = source_value.strip()
                excluded_hours = set()
                for value in statistics_import.get("excluded_hour_starts", []):
                    timestamp = self._normalize_timestamp(value)
                    if (
                        timestamp.minute
                        or timestamp.second
                        or timestamp.microsecond
                    ):
                        raise ReadingError(
                            "invalid_import",
                            "Excluded statistics hours must start on the hour",
                        )
                    excluded_hours.add(timestamp)
            await self._async_save_readings(
                imported,
                imported_excluded_hours=excluded_hours,
                imported_statistics_source=source,
            )

    async def async_update_reading(
        self, original_timestamp: Any, value: Any, timestamp: Any
    ) -> Reading:
        """Atomically update one existing reading."""
        original = self._normalize_timestamp(original_timestamp)
        reading = Reading(
            timestamp=self._normalize_timestamp(timestamp),
            value=self._normalize_value(value),
        )

        async with self._lock:
            try:
                updated, _ = replace_reading(
                    self._readings, original, reading
                )
            except KeyError as err:
                raise ReadingError(
                    "reading_not_found", "No reading exists at this timestamp"
                ) from err
            except DuplicateTimestampError as err:
                raise ReadingError(
                    "timestamp_exists",
                    "Another reading already exists at the selected timestamp",
                ) from err
            except ValueError as err:
                raise ReadingError("non_monotonic", str(err)) from err
            await self._async_save_readings(updated)

        for listener in tuple(self._listeners):
            listener()
        return reading

    async def async_delete_reading(self, timestamp: Any) -> Reading:
        """Delete one reading at an exact timestamp."""
        normalized_timestamp = self._normalize_timestamp(timestamp)

        async with self._lock:
            try:
                updated, deleted = remove_reading(
                    self._readings, normalized_timestamp
                )
            except KeyError as err:
                raise ReadingError(
                    "reading_not_found", "No reading exists at this timestamp"
                ) from err
            await self._async_save_readings(updated)

        for listener in tuple(self._listeners):
            listener()
        return deleted

    async def _async_save_readings(
        self,
        updated: list[Reading],
        *,
        imported_excluded_hours: set[datetime] | None = None,
        imported_statistics_source: str | None = None,
    ) -> None:
        """Persist readings and enqueue their minimal statistics update."""
        old_readings = self._readings
        old_baseline = self._statistics_baseline
        old_excluded_hours = self._statistics_excluded_hours
        baseline = old_baseline
        if len(old_readings) < 2:
            baseline = updated[0].value if updated else None
        elif baseline is None:
            baseline = old_readings[0].value
        statistics_update = changed_hourly_statistics(
            old_readings, updated, baseline
        )

        if imported_excluded_hours is None:
            excluded_hours = set(old_excluded_hours)
            excluded_hours.difference_update(
                item.start for item in statistics_update.upsert
            )
        else:
            excluded_hours = set(imported_excluded_hours)
        upsert = tuple(
            item
            for item in statistics_update.upsert
            if item.start not in excluded_hours
        )
        delete_starts = set(statistics_update.delete_starts)
        delete_starts.update(excluded_hours - old_excluded_hours)
        statistics_update = HourlyStatisticsUpdate(
            tuple(sorted(delete_starts)), upsert
        )

        stored_baseline = baseline
        if len(updated) < 2:
            stored_baseline = updated[0].value if updated else None
        source = (
            imported_statistics_source
            if imported_statistics_source is not None
            else self._statistics_import_source
        )
        converted_statistics = {
            unit: self._converted_statistics_rows(statistics_update.upsert, unit)
            for unit in self.secondary_units
        }
        await self._async_store_state(
            updated,
            stored_baseline,
            excluded_hours,
            source,
            self._secondary_statistics,
        )
        self._readings = updated
        self._statistics_baseline = stored_baseline
        self._statistics_excluded_hours = excluded_hours
        self._statistics_import_source = source

        self._async_apply_statistics_update(
            self._statistics_metadata(),
            statistics_update.delete_starts,
            [
                StatisticData(
                    start=bucket.start,
                    state=bucket.consumption,
                    sum=bucket.cumulative,
                )
                for bucket in statistics_update.upsert
            ],
        )
        for unit, rows in converted_statistics.items():
            self._async_apply_statistics_update(
                self._statistics_metadata(unit),
                statistics_update.delete_starts,
                rows,
            )

    async def _async_store_state(
        self,
        readings: list[Reading],
        baseline: float | None,
        excluded_hours: set[datetime],
        import_source: str | None,
        secondary_statistics: dict[str, bool],
    ) -> None:
        """Save readings, history metadata, and secondary selections together."""
        data = {
            "readings": [
                {"timestamp": item.timestamp.isoformat(), "value": item.value}
                for item in readings
            ],
            "statistics_baseline": baseline,
            "statistics_excluded_hours": [
                item.isoformat() for item in sorted(excluded_hours)
            ],
            "statistics_import_source": import_source,
            "secondary_statistics": secondary_statistics,
        }
        if self.gas_conversion is not None:
            data["gas_conversion"] = self.gas_conversion.as_input()
        await self._store.async_save(data)

    def _converted_statistics_rows(
        self, buckets: Iterable[HourlyConsumption], unit: str
    ) -> list[StatisticData]:
        """Convert hourly state and sum, raising a user-facing error on overflow."""
        convert = partial(
            convert_meter_value,
            meter_type=self.meter_type,
            source_unit=self.unit,
            target_unit=unit,
            gas_conversion=self.gas_conversion,
        )
        try:
            convert(0.0)
            return [
                StatisticData(
                    start=bucket.start,
                    state=convert(bucket.consumption),
                    sum=convert(bucket.cumulative),
                )
                for bucket in buckets
            ]
        except CsvTransferError as err:
            error = (
                "gas_statistics_conversion_failed"
                if meter_unit_class(unit) != self.unit_class
                else "secondary_statistics_conversion_failed"
            )
            raise ReadingError(error, str(err)) from err

    @callback
    def _async_apply_statistics_update(
        self,
        metadata: StatisticMetaData,
        delete_starts: tuple[datetime, ...],
        statistics: list[StatisticData],
    ) -> None:
        """Delete and upsert only the statistic rows in an update plan."""
        if delete_starts:
            get_instance(self.hass).queue_task(
                _DeleteStatisticsRowsTask(
                    statistic_id=metadata["statistic_id"],
                    starts=delete_starts,
                )
            )
        if statistics:
            async_add_external_statistics(self.hass, metadata, statistics)

    def _statistics_metadata(self, unit: str | None = None) -> StatisticMetaData:
        """Describe the primary or a secondary statistic for the Energy Dashboard."""
        statistic_id = (
            self.statistic_id if unit is None else self.secondary_statistic_id(unit)
        )
        return StatisticMetaData(
            has_sum=True,
            mean_type=StatisticMeanType.NONE,
            name=self.name if unit is None else f"{self.name} ({unit})",
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_class=meter_unit_class(unit or self.unit),
            unit_of_measurement=unit or self.unit,
        )

    def _normalize_timestamp(self, value: Any) -> datetime:
        """Parse a timestamp and interpret naive values in the HA timezone."""
        if isinstance(value, datetime):
            timestamp = value
        elif isinstance(value, str):
            timestamp = dt_util.parse_datetime(value)
            if timestamp is None:
                raise ReadingError("invalid_timestamp", "Invalid date and time")
        else:
            raise ReadingError("invalid_timestamp", "Invalid date and time")

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            timestamp = timestamp.replace(tzinfo=dt_util.get_default_time_zone())
        return dt_util.as_utc(timestamp)

    @staticmethod
    def _normalize_value(value: Any) -> float:
        """Return a finite non-negative meter value."""
        try:
            normalized = float(value)
        except (TypeError, ValueError) as err:
            raise ReadingError(
                "invalid_value", "The meter reading is not a number"
            ) from err
        if not math.isfinite(normalized) or normalized < 0:
            raise ReadingError(
                "invalid_value", "The meter reading must be finite and non-negative"
            )
        return normalized
