"""The Manual Energy Metering integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_TIMESTAMP,
    ATTR_VALUE,
    CONF_CONFIG_ENTRY_ID,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_READING,
    SERVICE_DELETE_READING,
)
from .meter import ManualEnergyMetering, ReadingError
from .panel import async_register_readings_panel
from .websocket_api import async_register_websocket_commands

ADD_READING_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
        vol.Required(ATTR_TIMESTAMP): cv.datetime,
    }
)

DELETE_READING_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_TIMESTAMP): cv.datetime,
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration-level actions."""
    hass.data.setdefault(DOMAIN, {})
    await async_register_readings_panel(hass)
    async_register_websocket_commands(hass)

    def get_meter(call: ServiceCall) -> ManualEnergyMetering:
        """Resolve a loaded meter from an action call."""
        entry_id: str = call.data[CONF_CONFIG_ENTRY_ID]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_found",
            )
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_loaded",
            )
        return entry.runtime_data

    async def async_add_reading(call: ServiceCall) -> None:
        """Handle the add reading action."""
        meter = get_meter(call)
        try:
            await meter.async_add_reading(
                call.data[ATTR_VALUE], call.data[ATTR_TIMESTAMP]
            )
        except ReadingError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=err.translation_key,
            ) from err

    async def async_delete_reading(call: ServiceCall) -> None:
        """Handle the delete reading action."""
        meter = get_meter(call)
        try:
            await meter.async_delete_reading(call.data[ATTR_TIMESTAMP])
        except ReadingError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=err.translation_key,
            ) from err

    if not hass.services.has_service(DOMAIN, SERVICE_ADD_READING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_READING,
            async_add_reading,
            schema=ADD_READING_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_DELETE_READING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DELETE_READING,
            async_delete_reading,
            schema=DELETE_READING_SCHEMA,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one manually configured meter."""
    meter = ManualEnergyMetering(hass, entry, entry.data.get(CONF_NAME, entry.title))
    await meter.async_load()
    entry.runtime_data = meter
    hass.data[DOMAIN][entry.entry_id] = meter

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a configured meter."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
