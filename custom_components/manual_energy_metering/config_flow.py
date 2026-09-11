"""Config flow for Manual Energy Metering."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.helpers import http
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
    CONF_CSV_CONTENT,
    CONF_IMPORTED_READINGS,
    CONF_IMPORTED_STATISTICS,
    CONF_METER_ID,
    CONF_METER_TYPE,
    CONF_UNIT,
    CONF_VISION_API_TOKEN,
    CONF_VISION_API_URL,
    CONF_VISION_COMPRESS_IMAGE,
    CONF_VISION_MODEL,
    CONF_VISION_PROMPT,
    DEFAULT_VISION_COMPRESS_IMAGE,
    DEFAULT_VISION_MODEL,
    DEFAULT_VISION_PROMPT,
    DOMAIN,
    ELECTRICITY_UNITS,
    FIXED_UNITS,
    METER_TYPE_ELECTRICITY,
    METER_TYPES,
    UNIT_KWH,
)
from .csv_transfer import (
    CsvTransferError,
    STATISTICS_CSV_FORMAT_VERSION,
    convert_meter_csv_unit,
    parse_meter_csv,
    validate_meter_name,
)
from .panel import async_register_import_ui
from .vision import VisionError, chat_completions_url, normalize_vision_url

_HEADER_FRONTEND_BASE = "HA-Frontend-Base"


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
        vol.Optional(
            CONF_VISION_COMPRESS_IMAGE,
            default=defaults.get(
                CONF_VISION_COMPRESS_IMAGE, DEFAULT_VISION_COMPRESS_IMAGE
            ),
        ): bool,
    }
    if reconfigure:
        fields[vol.Optional(CONF_CLEAR_VISION_API_TOKEN, default=False)] = bool
    return vol.Schema(fields)


def _normalize_vision_input(user_input: dict[str, Any]) -> dict[str, Any]:
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
        CONF_VISION_COMPRESS_IMAGE: bool(
            user_input.get(
                CONF_VISION_COMPRESS_IMAGE, DEFAULT_VISION_COMPRESS_IMAGE
            )
        ),
    }


def _vision_input_errors(data: dict[str, Any]) -> dict[str, str]:
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

    VERSION = 6

    def __init__(self) -> None:
        """Initialize the flow."""
        self._meter_data: dict[str, Any] = {}
        self._import_readings: list[dict[str, Any]] | None = None
        self._import_statistics: dict[str, Any] | None = None
        self._frontend_base: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Choose meter creation, CSV import, or statistics export."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["manual", "import_csv", "export_statistics"],
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Collect the meter name and type for an empty meter."""
        if user_input is not None:
            self._import_readings = None
            self._import_statistics = None
            self._meter_data = user_input
            if user_input[CONF_METER_TYPE] == METER_TYPE_ELECTRICITY:
                return await self.async_step_unit()
            self._meter_data[CONF_UNIT] = FIXED_UNITS[user_input[CONF_METER_TYPE]]
            return await self.async_step_vision()

        return self.async_show_form(
            step_id="manual",
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

    async def async_step_import_csv(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Import one exported CSV through the authenticated external panel."""
        if user_input is not None:
            try:
                imported = parse_meter_csv(user_input[CONF_CSV_CONTENT])
                imported = convert_meter_csv_unit(
                    imported, user_input.get(CONF_UNIT, imported.unit)
                )
            except (CsvTransferError, KeyError, TypeError):
                return await self._async_show_csv_import()
            try:
                name = validate_meter_name(user_input.get(CONF_NAME, ""))
            except CsvTransferError:
                return await self._async_show_csv_import()
            self._meter_data = {
                CONF_NAME: name,
                CONF_METER_TYPE: imported.meter_type,
                CONF_UNIT: imported.unit,
            }
            self._import_readings = [
                {
                    "timestamp": reading.timestamp.isoformat(),
                    "value": reading.value,
                }
                for reading in imported.readings
            ]
            self._import_statistics = (
                {
                    "source_statistic_id": imported.source_statistic_id,
                    "excluded_hour_starts": [
                        item.isoformat()
                        for item in imported.excluded_hour_starts
                    ],
                }
                if imported.format_version == STATISTICS_CSV_FORMAT_VERSION
                else None
            )
            return self.async_external_step_done(next_step_id="vision")
        return await self._async_show_csv_import()

    async def _async_show_csv_import(self) -> dict[str, Any]:
        """Expose the file picker used by the external import step."""
        url = await self._async_external_panel_url(
            f"import_flow={self.flow_id}"
        )
        return self.async_external_step(step_id="import_csv", url=url)

    async def async_step_export_statistics(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Export a physical meter's long-term statistics through the panel."""
        if user_input is not None:
            return self.async_external_step_done(
                next_step_id="statistics_exported"
            )
        url = await self._async_external_panel_url(
            f"export_flow={self.flow_id}"
        )
        return self.async_external_step(step_id="export_statistics", url=url)

    async def async_step_statistics_exported(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Finish a config flow which was used only for exporting data."""
        return self.async_abort(reason="statistics_exported")

    async def _async_external_panel_url(self, query: str) -> str:
        """Return an absolute URL for one authenticated panel mode."""
        await async_register_import_ui(self.hass)
        request = http.current_request.get()
        if request is not None and (
            frontend_base := request.headers.get(_HEADER_FRONTEND_BASE)
        ):
            self._frontend_base = frontend_base
        if self._frontend_base is None:
            raise RuntimeError("The Home Assistant frontend base URL is unavailable")
        return f"{self._frontend_base.rstrip('/')}/{DOMAIN}?{query}"

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
            CONF_VISION_COMPRESS_IMAGE: DEFAULT_VISION_COMPRESS_IMAGE,
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
        defaults.setdefault(
            CONF_VISION_COMPRESS_IMAGE, DEFAULT_VISION_COMPRESS_IMAGE
        )
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
        if self._import_readings is not None:
            self._meter_data[CONF_IMPORTED_READINGS] = self._import_readings
        if self._import_statistics is not None:
            self._meter_data[CONF_IMPORTED_STATISTICS] = self._import_statistics
        return self.async_create_entry(
            title=self._meter_data[CONF_NAME], data=self._meter_data
        )
