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
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_CLEAR_VISION_API_TOKEN,
    CONF_METER_ID,
    CONF_METER_TYPE,
    CONF_UNIT,
    CONF_VISION_API_TOKEN,
    CONF_VISION_API_URL,
    CONF_VISION_MODEL,
    CONF_VISION_PROMPT,
    DEFAULT_VISION_MODEL,
    DEFAULT_VISION_PROMPT,
    DOMAIN,
    ELECTRICITY_UNITS,
    FIXED_UNITS,
    METER_TYPE_ELECTRICITY,
    METER_TYPES,
    UNIT_KWH,
)
from .vision import VisionError, chat_completions_url, normalize_vision_url


def _vision_schema(
    defaults: dict[str, Any],
    *,
    reconfigure: bool = False,
) -> vol.Schema:
    """Build the per-meter vision-provider form schema."""
    fields: dict[vol.Marker, Any] = {
        vol.Optional(
            CONF_VISION_API_URL,
            default=defaults.get(CONF_VISION_API_URL, ""),
        ): TextSelector(),
        vol.Optional(
            CONF_VISION_API_TOKEN,
            default=(
                "" if reconfigure else defaults.get(CONF_VISION_API_TOKEN, "")
            ),
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Required(
            CONF_VISION_MODEL,
            default=defaults.get(CONF_VISION_MODEL, DEFAULT_VISION_MODEL),
        ): TextSelector(),
        vol.Required(
            CONF_VISION_PROMPT,
            default=defaults.get(CONF_VISION_PROMPT, DEFAULT_VISION_PROMPT),
        ): TextSelector(TextSelectorConfig(multiline=True)),
    }
    if reconfigure:
        fields[vol.Optional(CONF_CLEAR_VISION_API_TOKEN, default=False)] = bool
    return vol.Schema(fields)


def _normalize_vision_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Normalize the optional provider settings."""
    return {
        CONF_VISION_API_URL: normalize_vision_url(
            user_input.get(CONF_VISION_API_URL, "")
        ),
        CONF_VISION_API_TOKEN: user_input.get(
            CONF_VISION_API_TOKEN, ""
        ).strip(),
        CONF_VISION_MODEL: user_input.get(
            CONF_VISION_MODEL, DEFAULT_VISION_MODEL
        ).strip(),
        CONF_VISION_PROMPT: user_input.get(
            CONF_VISION_PROMPT, DEFAULT_VISION_PROMPT
        ).strip(),
    }


def _vision_input_errors(data: dict[str, str]) -> dict[str, str]:
    """Validate a disabled or complete per-meter provider configuration."""
    errors: dict[str, str] = {}
    api_url = data[CONF_VISION_API_URL]
    model = data[CONF_VISION_MODEL]
    if api_url:
        try:
            chat_completions_url(api_url)
        except VisionError:
            errors[CONF_VISION_API_URL] = "invalid_url"
    if not model:
        errors[CONF_VISION_MODEL] = "required"
    if not data[CONF_VISION_PROMPT]:
        errors[CONF_VISION_PROMPT] = "required"
    return errors


class ManualEnergyMeteringConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Manual Energy Metering config flow."""

    VERSION = 5

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
            return await self.async_step_vision()

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
            return await self.async_step_vision()

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

    async def async_step_vision(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Configure optional photo recognition for this meter."""
        errors: dict[str, str] = {}
        if user_input is not None:
            vision_data = _normalize_vision_input(user_input)
            errors = _vision_input_errors(vision_data)
            if not errors:
                self._meter_data.update(vision_data)
                return await self._async_create_meter()

        defaults = {
            CONF_VISION_MODEL: DEFAULT_VISION_MODEL,
            CONF_VISION_PROMPT: DEFAULT_VISION_PROMPT,
        }
        if user_input is not None:
            defaults.update(user_input)
        return self.async_show_form(
            step_id="vision",
            data_schema=_vision_schema(defaults),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Update photo recognition for one meter."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            vision_data = _normalize_vision_input(user_input)
            if user_input.get(CONF_CLEAR_VISION_API_TOKEN, False):
                vision_data[CONF_VISION_API_TOKEN] = ""
            elif not vision_data[CONF_VISION_API_TOKEN]:
                vision_data[CONF_VISION_API_TOKEN] = str(
                    entry.data.get(CONF_VISION_API_TOKEN, "")
                )
            errors = _vision_input_errors(vision_data)
            if not errors:
                await self.async_set_unique_id(entry.unique_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={**entry.data, **vision_data},
                )

        defaults = dict(entry.data)
        defaults.setdefault(CONF_VISION_MODEL, DEFAULT_VISION_MODEL)
        defaults.setdefault(CONF_VISION_PROMPT, DEFAULT_VISION_PROMPT)
        if user_input is not None:
            defaults.update(user_input)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_vision_schema(defaults, reconfigure=True),
            errors=errors,
        )

    async def _async_create_meter(self) -> dict[str, Any]:
        """Create the config entry."""
        meter_id = uuid4().hex
        await self.async_set_unique_id(meter_id)
        self._meter_data[CONF_METER_ID] = meter_id
        return self.async_create_entry(
            title=self._meter_data[CONF_NAME], data=self._meter_data
        )
