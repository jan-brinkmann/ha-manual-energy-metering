"""Config flow for Manual Energy Metering."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    DateTimeSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_TIMESTAMP,
    ATTR_VALUE,
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
from .meter import ManualEnergyMetering, ReadingError


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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the reading-entry options flow."""
        return ManualEnergyMeteringOptionsFlow()


class ManualEnergyMeteringOptionsFlow(OptionsFlow):
    """Manage timestamped readings from the options dialog."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Choose how to manage readings."""
        meter: ManualEnergyMetering = self.config_entry.runtime_data
        menu_options: list[str] = ["add_reading"]
        if meter.readings:
            menu_options.append("delete_reading")
        return self.async_show_menu(step_id="init", menu_options=menu_options)

    async def async_step_add_reading(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Add or correct a timestamped reading."""
        errors: dict[str, str] = {}
        if user_input is not None:
            meter: ManualEnergyMetering = self.config_entry.runtime_data
            try:
                await meter.async_add_reading(
                    user_input[ATTR_VALUE], user_input[ATTR_TIMESTAMP]
                )
            except ReadingError as err:
                errors["base"] = err.translation_key
            else:
                return self.async_create_entry(title="", data={})

        default_timestamp = (
            user_input[ATTR_TIMESTAMP]
            if user_input is not None and ATTR_TIMESTAMP in user_input
            else dt_util.now().replace(
                second=0, microsecond=0
            ).strftime("%Y-%m-%d %H:%M:%S")
        )
        return self.async_show_form(
            step_id="add_reading",
            data_schema=vol.Schema(
                {
                    vol.Required(ATTR_VALUE): NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            mode=NumberSelectorMode.BOX,
                            step="any",
                        )
                    ),
                    vol.Required(
                        ATTR_TIMESTAMP, default=default_timestamp
                    ): DateTimeSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_delete_reading(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Delete one existing reading."""
        errors: dict[str, str] = {}
        meter: ManualEnergyMetering = self.config_entry.runtime_data
        if user_input is not None:
            try:
                await meter.async_delete_reading(user_input[ATTR_TIMESTAMP])
            except ReadingError as err:
                errors["base"] = err.translation_key
            else:
                return self.async_create_entry(title="", data={})

        options: list[SelectOptionDict] = []
        for reading in reversed(meter.readings):
            local_timestamp = reading.timestamp.astimezone(
                dt_util.get_default_time_zone()
            )
            options.append(
                SelectOptionDict(
                    value=reading.timestamp.isoformat(),
                    label=(
                        f"{local_timestamp:%Y-%m-%d %H:%M:%S} - "
                        f"{reading.value:g} {meter.unit}"
                    ),
                )
            )

        if not options:
            return await self.async_step_init()

        return self.async_show_form(
            step_id="delete_reading",
            data_schema=vol.Schema(
                {
                    vol.Required(ATTR_TIMESTAMP): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )
