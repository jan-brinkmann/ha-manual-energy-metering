"""Runtime model and storage for Manual Energy Metering."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any

from homeassistant.components.recorder.db_schema import Statistics
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
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
    METER_TYPE_WATER,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
    UNIT_LITERS,
)
from .interpolation import (
    DuplicateTimestampError,
    HourlyStatisticsUpdate,
    Reading,
    changed_hourly_statistics,
    interpolate_value,
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
    """Hold one manual meter's readings and imported statistics."""

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
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}.{self.meter_id}"
        )
        self._readings: list[Reading] = []
        self._listeners: set[Callable[[], None]] = set()
        self._lock = asyncio.Lock()
        self._statistics_baseline: float | None = None
        self._statistics_excluded_hours: set[datetime] = set()
        self._statistics_import_source: str | None = None

    @property
    def statistic_id(self) -> str:
        """Return the external statistic ID exposed to the Energy Dashboard."""
        return f"{DOMAIN}:{self.meter_id}"

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
        return interpolate_value(self._readings, timestamp)

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an update listener."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    async def async_load(self) -> None:
        """Load readings from Home Assistant storage."""
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
        old_import_source = self._statistics_import_source
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
        self._readings = updated
        self._statistics_baseline = stored_baseline
        self._statistics_excluded_hours = excluded_hours
        if imported_statistics_source is not None:
            self._statistics_import_source = imported_statistics_source
        try:
            await self._store.async_save(
                {
                    "readings": [
                        {
                            "timestamp": item.timestamp.isoformat(),
                            "value": item.value,
                        }
                        for item in updated
                    ],
                    "statistics_baseline": stored_baseline,
                    "statistics_excluded_hours": [
                        item.isoformat() for item in sorted(excluded_hours)
                    ],
                    "statistics_import_source": self._statistics_import_source,
                }
            )
        except Exception:
            self._readings = old_readings
            self._statistics_baseline = old_baseline
            self._statistics_excluded_hours = old_excluded_hours
            self._statistics_import_source = old_import_source
            raise

        self._async_apply_statistics_update(statistics_update)

    @callback
    def _async_apply_statistics_update(
        self, update: HourlyStatisticsUpdate
    ) -> None:
        """Delete and upsert only the statistic rows in an update plan."""
        if update.delete_starts:
            get_instance(self.hass).queue_task(
                _DeleteStatisticsRowsTask(
                    statistic_id=self.statistic_id,
                    starts=update.delete_starts,
                )
            )
        if not update.upsert:
            return

        statistics = [
            StatisticData(
                start=bucket.start,
                state=bucket.consumption,
                sum=bucket.cumulative,
            )
            for bucket in update.upsert
        ]
        async_add_external_statistics(
            self.hass, self._statistics_metadata(), statistics
        )

    def _statistics_metadata(self) -> StatisticMetaData:
        """Return metadata for this meter's external statistic."""
        unit_class = (
            "volume"
            if self.meter_type == METER_TYPE_WATER
            or (self.meter_type == METER_TYPE_GAS and self.unit == UNIT_LITERS)
            else "energy"
        )
        return StatisticMetaData(
            has_sum=True,
            mean_type=StatisticMeanType.NONE,
            name=self.name,
            source=DOMAIN,
            statistic_id=self.statistic_id,
            unit_class=unit_class,
            unit_of_measurement=self.unit,
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
