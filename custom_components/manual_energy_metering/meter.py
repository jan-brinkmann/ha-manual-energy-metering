"""Runtime model and storage for Manual Energy Metering."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
import math
from typing import Any

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.components.recorder.util import get_instance
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_METER_ID,
    CONF_METER_TYPE,
    CONF_UNIT,
    DOMAIN,
    METER_TYPE_WATER,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)
from .interpolation import (
    DuplicateTimestampError,
    Reading,
    hourly_consumption,
    interpolate_value,
    remove_reading,
    replace_reading,
    upsert_reading,
    validate_readings,
)


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
        self._statistics_revision = 0

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

    async def _async_save_readings(self, updated: list[Reading]) -> None:
        """Persist a validated reading list and rebuild its statistics."""
        old_readings = self._readings
        self._readings = updated
        try:
            await self._store.async_save(
                {
                    "readings": [
                        {
                            "timestamp": item.timestamp.isoformat(),
                            "value": item.value,
                        }
                        for item in updated
                    ]
                }
            )
        except Exception:
            self._readings = old_readings
            raise

        self.async_rebuild_statistics()

    @callback
    def async_rebuild_statistics(self) -> None:
        """Clear and rebuild all hourly statistics from canonical readings."""
        self._statistics_revision += 1
        revision = self._statistics_revision

        def statistics_cleared() -> None:
            self.hass.loop.call_soon_threadsafe(
                self._async_import_statistics, revision
            )

        get_instance(self.hass).async_clear_statistics(
            [self.statistic_id], on_done=statistics_cleared
        )

    @callback
    def _async_import_statistics(self, revision: int) -> None:
        """Import the latest revision after its previous rows were cleared."""
        if revision != self._statistics_revision:
            return

        unit_class = "volume" if self.meter_type == METER_TYPE_WATER else "energy"
        metadata = StatisticMetaData(
            has_sum=True,
            mean_type=StatisticMeanType.NONE,
            name=self.name,
            source=DOMAIN,
            statistic_id=self.statistic_id,
            unit_class=unit_class,
            unit_of_measurement=self.unit,
        )
        statistics = [
            StatisticData(
                start=bucket.start,
                state=bucket.consumption,
                sum=bucket.cumulative,
            )
            for bucket in hourly_consumption(self._readings)
        ]
        if statistics:
            async_add_external_statistics(self.hass, metadata, statistics)

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
