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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
    ATTR_LAST_READING,
    ATTR_LAST_READING_TIMESTAMP,
    ATTR_METER_UNIT,
    ATTR_READING_COUNT,
    ATTR_RECENT_READINGS,
    ATTR_STATISTIC_ID,
    ATTR_TIMESTAMP,
    ATTR_VALUE,
    ATTR_VISION_CONFIGURED,
    CONF_METER_TYPE,
    CONF_VISION_API_URL,
    CONF_VISION_COMPRESS_IMAGE,
    CONF_VISION_MODEL,
    DEFAULT_VISION_COMPRESS_IMAGE,
    DOMAIN,
    MAX_RECENT_READINGS,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
    SECONDARY_UNIT_ID_SUFFIXES,
)
from .csv_transfer import meter_unit_class
from .meter import ManualEnergyMetering

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the primary sensor and maintain the selected secondary sensors."""
    meter: ManualEnergyMetering = entry.runtime_data
    platform = async_get_current_platform()
    registry = er.async_get(hass)

    async def update_secondary_sensor(unit: str, enabled: bool) -> None:
        """Add the selected sensor or remove its state and registry entry."""
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, meter.secondary_sensor_id(unit)
        )
        if enabled:
            registry_entry = registry.async_get(entity_id) if entity_id else None
            if registry_entry is None or (
                not registry_entry.disabled and entity_id not in platform.entities
            ):
                await platform.async_add_entities(
                    [ManualEnergyMeteringSensor(meter, unit)]
                )
        elif entity_id is not None:
            if (entity := platform.entities.get(entity_id)) is not None:
                await entity.async_remove(force_remove=True)
            if registry.async_get(entity_id) is not None:
                registry.async_remove(entity_id)

    for unit in meter.disabled_secondary_units:
        await update_secondary_sensor(unit, False)
    meter.async_update_secondary_sensor = update_secondary_sensor
    async_add_entities(
        [
            ManualEnergyMeteringSensor(meter),
            *(
                ManualEnergyMeteringSensor(meter, unit)
                for unit in meter.secondary_units
            ),
        ]
    )


class ManualEnergyMeteringSensor(SensorEntity):
    """Represent the primary register or a computed register on the same device."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _unrecorded_attributes = frozenset({ATTR_RECENT_READINGS})

    def __init__(
        self, meter: ManualEnergyMetering, secondary_unit: str | None = None
    ) -> None:
        """Initialize the sensor and suggest distinct IDs for case-sensitive units."""
        self._meter = meter
        self._secondary_unit = secondary_unit
        unit = secondary_unit or meter.unit
        self._attr_name = secondary_unit
        self._attr_unique_id = (
            meter.meter_id
            if secondary_unit is None
            else meter.secondary_sensor_id(unit)
        )
        suffix = SECONDARY_UNIT_ID_SUFFIXES.get(unit)
        if secondary_unit is not None and suffix is not None:
            object_id = slugify(f"{meter.name}_{suffix}")
            self.entity_id = f"sensor.{object_id}"
        self._attr_native_unit_of_measurement = unit
        self._attr_suggested_unit_of_measurement = unit
        if meter.meter_type == METER_TYPE_WATER:
            self._attr_device_class = SensorDeviceClass.WATER
        elif meter.meter_type == METER_TYPE_GAS and meter_unit_class(unit) == "volume":
            self._attr_device_class = SensorDeviceClass.GAS
        else:
            self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, meter.meter_id)},
            name=meter.name,
            manufacturer="Manual Energy Metering",
            model=meter.meter_type,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current interpolation in the sensor's native unit."""
        value = self._meter.value_at(dt_util.utcnow())
        if value is None or self._secondary_unit is None:
            return value
        return self._meter.convert_register(value, self._secondary_unit)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Expose the reading-entry card's metadata on the primary entity."""
        if self._secondary_unit is not None:
            return None
        latest = self._meter.latest_reading
        return {
            CONF_METER_TYPE: self._meter.meter_type,
            ATTR_METER_UNIT: self._meter.unit,
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
            ATTR_VISION_CONFIGURED: bool(
                str(self._meter.entry.data.get(CONF_VISION_API_URL, "")).strip()
                and str(
                    self._meter.entry.data.get(CONF_VISION_MODEL, "")
                ).strip()
            ),
            CONF_VISION_COMPRESS_IMAGE: self._meter.entry.data.get(
                CONF_VISION_COMPRESS_IMAGE, DEFAULT_VISION_COMPRESS_IMAGE
            ),
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
        if self._meter.is_interpolating_at(now):
            self.async_write_ha_state()
