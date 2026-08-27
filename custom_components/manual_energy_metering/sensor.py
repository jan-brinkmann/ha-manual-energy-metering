"""Sensor platform for Manual Energy Metering."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_LAST_READING,
    ATTR_LAST_READING_TIMESTAMP,
    ATTR_RECENT_READINGS,
    ATTR_TIMESTAMP,
    ATTR_VALUE,
    ATTR_READING_COUNT,
    ATTR_STATISTIC_ID,
    CONF_METER_TYPE,
    DOMAIN,
    MAX_RECENT_READINGS,
    METER_TYPE_WATER,
)
from .meter import ManualEnergyMetering

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up a sensor for one meter."""
    async_add_entities([ManualEnergyMeteringSensor(entry.runtime_data)])


class ManualEnergyMeteringSensor(SensorEntity):
    """Represent a manually read utility meter."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _unrecorded_attributes = frozenset({ATTR_RECENT_READINGS})

    def __init__(self, meter: ManualEnergyMetering) -> None:
        """Initialize the sensor."""
        self._meter = meter
        self._attr_unique_id = meter.meter_id
        self._attr_native_unit_of_measurement = meter.unit
        self._attr_device_class = (
            SensorDeviceClass.WATER
            if meter.meter_type == METER_TYPE_WATER
            else SensorDeviceClass.ENERGY
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, meter.meter_id)},
            name=meter.name,
            manufacturer="Manual Energy Metering",
            model=meter.meter_type,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current interpolated meter reading."""
        return self._meter.value_at(dt_util.utcnow())

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose reading and Energy Dashboard metadata."""
        latest = self._meter.latest_reading
        return {
            CONF_METER_TYPE: self._meter.meter_type,
            ATTR_READING_COUNT: len(self._meter.readings),
            ATTR_LAST_READING: latest.value if latest else None,
            ATTR_LAST_READING_TIMESTAMP: (
                latest.timestamp.isoformat() if latest else None
            ),
            ATTR_RECENT_READINGS: [
                {
                    ATTR_TIMESTAMP: reading.timestamp.isoformat(),
                    ATTR_VALUE: reading.value,
                }
                for reading in self._meter.readings[-MAX_RECENT_READINGS:]
            ],
            ATTR_STATISTIC_ID: self._meter.statistic_id,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to stored reading and interpolation updates."""
        await super().async_added_to_hass()
        self.async_on_remove(self._meter.async_add_listener(self._handle_update))
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._handle_interval, timedelta(minutes=1)
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Write a newly stored reading."""
        self.async_write_ha_state()

    @callback
    def _handle_interval(self, now) -> None:
        """Refresh the displayed interpolation between dated readings."""
        readings = self._meter.readings
        if len(readings) >= 2 and readings[0].timestamp < now < readings[-1].timestamp:
            self.async_write_ha_state()
