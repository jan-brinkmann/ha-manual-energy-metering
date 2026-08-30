"""Config flow for Manual Energy Metering."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_METER_ID,
    CONF_METER_TYPE,
    CONF_UNIT,
    DOMAIN,
    ELECTRICITY_UNITS,
    FIXED_UNITS,
    METER_TYPE_ELECTRICITY,
    METER_TYPES,
    UNIT_KWH,
)


class ManualEnergyMeteringConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Manual Energy Metering config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._meter_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Collect the meter name and type."""
        if user_input is not None:
            self._meter_data = user_input
            if user_input[CONF_METER_TYPE] == METER_TYPE_ELECTRICITY:
                return await self.async_step_unit()
            self._meter_data[CONF_UNIT] = FIXED_UNITS[user_input[CONF_METER_TYPE]]
            return await self._async_create_meter()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_METER_TYPE): SelectSelector(
                        SelectSelectorConfig(
                            options=list(METER_TYPES),
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key=CONF_METER_TYPE,
                        )
                    ),
                }
            ),
        )

    async def async_step_unit(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Choose Wh or kWh for an electricity meter."""
        if user_input is not None:
            self._meter_data.update(user_input)
            return await self._async_create_meter()

        return self.async_show_form(
            step_id="unit",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UNIT, default=UNIT_KWH): SelectSelector(
                        SelectSelectorConfig(
                            options=list(ELECTRICITY_UNITS),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def _async_create_meter(self) -> dict[str, Any]:
        """Create the config entry."""
        meter_id = uuid4().hex
        await self.async_set_unique_id(meter_id)
        self._meter_data[CONF_METER_ID] = meter_id
        return self.async_create_entry(
            title=self._meter_data[CONF_NAME], data=self._meter_data
        )
