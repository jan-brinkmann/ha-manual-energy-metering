"""Constants for the Manual Energy Metering integration."""

from __future__ import annotations

from homeassistant.const import Platform, UnitOfEnergy, UnitOfVolume

# This domain becomes persistent as soon as the integration is released.
DOMAIN = "manual_energy_metering"
PLATFORMS = (Platform.SENSOR,)

CONF_METER_ID = "meter_id"
CONF_METER_TYPE = "meter_type"
CONF_UNIT = "unit"
CONF_CONFIG_ENTRY_ID = "config_entry_id"
CONF_VISION_API_URL = "vision_api_url"
CONF_VISION_API_TOKEN = "vision_api_token"
CONF_VISION_MODEL = "vision_model"
CONF_VISION_PROMPT = "vision_prompt"
CONF_CLEAR_VISION_API_TOKEN = "clear_vision_api_token"

DEFAULT_VISION_MODEL = "qwen2.5vl:7b"
DEFAULT_VISION_PROMPT = (
    "Read the complete cumulative meter value shown in this image. Return only "
    'JSON in the form {"value":"123.45"}. Use a period as the decimal '
    "separator, no thousands separators, and no unit. Include all visible "
    "integer and decimal digits. If the value cannot be read reliably, return "
    '{"error":"unreadable"}.'
)

ATTR_TIMESTAMP = "timestamp"
ATTR_VALUE = "value"
ATTR_READING_COUNT = "reading_count"
ATTR_RECENT_READINGS = "recent_readings"
ATTR_LAST_READING = "last_reading"
ATTR_LAST_READING_TIMESTAMP = "last_reading_timestamp"
ATTR_STATISTIC_ID = "statistic_id"
ATTR_VISION_CONFIGURED = "vision_configured"

SERVICE_ADD_READING = "add_reading"
SERVICE_DELETE_READING = "delete_reading"
MAX_RECENT_READINGS = 50

METER_TYPE_ELECTRICITY = "electricity"
METER_TYPE_GAS = "gas"
METER_TYPE_WATER = "water"
METER_TYPES = (
    METER_TYPE_ELECTRICITY,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
)

UNIT_WH = UnitOfEnergy.WATT_HOUR
UNIT_KWH = UnitOfEnergy.KILO_WATT_HOUR
UNIT_LITERS = UnitOfVolume.LITERS

ELECTRICITY_UNITS = (UNIT_WH, UNIT_KWH)
FIXED_UNITS = {
    METER_TYPE_GAS: UNIT_KWH,
    METER_TYPE_WATER: UNIT_LITERS,
}

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = DOMAIN

SIGNAL_METER_UPDATED = f"{DOMAIN}_updated"
