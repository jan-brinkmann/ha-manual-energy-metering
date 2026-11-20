"""Regression tests for reconfiguring a meter in Home Assistant."""

from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Any
from unittest.mock import patch

try:
    from homeassistant.config_entries import (
        SOURCE_RECONFIGURE,
        ConfigEntries,
        ConfigEntry,
        ConfigFlowResult,
    )
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.config_validation import custom_serializer
    from voluptuous_serialize import convert

    from custom_components.manual_energy_metering.config_flow import (
        ManualEnergyMeteringConfigFlow,
    )
    from custom_components.manual_energy_metering.const import DOMAIN
except ModuleNotFoundError as err:
    if err.name != "homeassistant":
        raise
    raise unittest.SkipTest("Home Assistant is required for config flow tests") from err


def _form_value(form: ConfigFlowResult, name: str) -> Any:
    """Read the initial field value as serialized for the config flow dialog."""
    schema = convert(form["data_schema"], custom_serializer=custom_serializer)
    field = next(field for field in schema if field["name"] == name)
    return field.get("description", {}).get("suggested_value", field.get("default"))


class VisionReconfigureTests(unittest.IsolatedAsyncioTestCase):
    """Verify saving and reopening a meter's photo recognition settings."""

    async def asyncSetUp(self) -> None:
        """Register a meter with the real flow manager and stub platform setup."""
        config_dir = self.enterContext(TemporaryDirectory())
        self.hass = HomeAssistant(config_dir)
        self.entries = self.hass.config_entries = ConfigEntries(self.hass, {})
        self.entry = ConfigEntry(
            data={
                "name": "Electricity",
                "meter_type": "electricity",
                "meter_id": "meter",
                "unit": "kWh",
                "vision_api_url": "http://provider.example:11434",
                "vision_api_token": "stored-token",
                "vision_model": "custom-model",
                "vision_prompt": "Read the displayed value.",
                "vision_compress_image": False,
            },
            discovery_keys=MappingProxyType({}),
            domain=DOMAIN,
            minor_version=1,
            options={},
            source="user",
            subentries_data=None,
            title="Electricity",
            unique_id="meter",
            version=ManualEnergyMeteringConfigFlow.VERSION,
        )
        with patch.object(self.entries, "async_setup"):
            await self.entries.async_add(self.entry)
        self.reload_entry = self.enterContext(
            patch.object(self.entries, "async_schedule_reload")
        )

    async def _open_form(self) -> ConfigFlowResult:
        """Open the reconfigure flow for the test meter."""
        with patch(
            "homeassistant.config_entries._async_get_flow_handler",
            return_value=ManualEnergyMeteringConfigFlow,
        ):
            return await self.entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_RECONFIGURE, "entry_id": self.entry.entry_id},
            )

    async def test_cleared_address_stays_empty_on_reopen(self) -> None:
        """Persist the cleared address when the dialog omits the empty field."""
        form = await self._open_form()
        self.assertEqual(
            _form_value(form, "vision_api_url"), self.entry.data["vision_api_url"]
        )
        self.assertEqual(_form_value(form, "vision_api_token"), "")

        result = await self.entries.flow.async_configure(
            form["flow_id"],
            {
                "vision_model": self.entry.data["vision_model"],
                "vision_prompt": self.entry.data["vision_prompt"],
                "vision_compress_image": False,
            },
        )

        self.assertEqual(result["reason"], "reconfigure_successful")
        self.assertEqual(self.entry.data["vision_api_url"], "")
        self.assertEqual(self.entry.data["vision_api_token"], "stored-token")
        self.assertEqual(self.entry.data["vision_model"], "custom-model")
        self.assertEqual(self.entry.data["vision_prompt"], "Read the displayed value.")
        self.assertIs(self.entry.data["vision_compress_image"], False)
        self.reload_entry.assert_called_once_with(self.entry.entry_id)
        self.assertEqual(_form_value(await self._open_form(), "vision_api_url"), "")

    async def test_retry_keeps_address_and_token_removal(self) -> None:
        """Keep both deletion choices after another field fails validation."""
        form = await self._open_form()
        retry = await self.entries.flow.async_configure(
            form["flow_id"],
            {"vision_prompt": "   ", "clear_vision_api_token": True},
        )

        self.assertEqual(retry["errors"], {"vision_prompt": "required"})
        self.assertEqual(_form_value(retry, "vision_api_url"), "")
        self.assertIs(_form_value(retry, "clear_vision_api_token"), True)
        self.assertEqual(
            self.entry.data["vision_api_url"], "http://provider.example:11434"
        )
        self.assertEqual(self.entry.data["vision_api_token"], "stored-token")

        result = await self.entries.flow.async_configure(
            retry["flow_id"], {"vision_prompt": "Read the displayed value."}
        )

        self.assertEqual(result["reason"], "reconfigure_successful")
        self.assertEqual(self.entry.data["vision_api_url"], "")
        self.assertEqual(self.entry.data["vision_api_token"], "")
