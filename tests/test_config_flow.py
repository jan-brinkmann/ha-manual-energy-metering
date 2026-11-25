"""Regression tests for reconfiguring a meter in Home Assistant."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from tempfile import TemporaryDirectory
from types import MappingProxyType, SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

try:
    from homeassistant.config_entries import (
        SOURCE_RECONFIGURE,
        SOURCE_USER,
        ConfigEntries,
        ConfigEntry,
        ConfigFlowResult,
    )
    from homeassistant.core import HomeAssistant
    from aiohttp import web
    from aiohttp.test_utils import make_mocked_request
    from homeassistant.components.http import KEY_HASS, KEY_HASS_USER
    from homeassistant.helpers.config_validation import custom_serializer
    try:
        from probatio import to_field_list as convert
    except ModuleNotFoundError:
        from voluptuous_serialize import convert

    from custom_components.manual_energy_metering import async_setup_entry
    from custom_components.manual_energy_metering import meter as meter_module
    from custom_components.manual_energy_metering.config_flow import (
        ManualEnergyMeteringConfigFlow,
    )
    from custom_components.manual_energy_metering.const import DOMAIN
    from custom_components.manual_energy_metering.csv_http import (
        CSV_IMPORT_URL,
        CsvImportView,
    )
    from custom_components.manual_energy_metering.csv_transfer import export_meter_csv
    from custom_components.manual_energy_metering.interpolation import Reading
except ModuleNotFoundError as err:
    if err.name != "homeassistant":
        raise
    raise unittest.SkipTest("Home Assistant is required for config flow tests") from err


def _form_value(form: ConfigFlowResult, name: str) -> Any:
    """Read the initial field value as serialized for the config flow dialog."""
    schema = convert(form["data_schema"], custom_serializer=custom_serializer)
    field = next(field for field in schema if field["name"] == name)
    return field.get("description", {}).get("suggested_value", field.get("default"))


class MeterConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    """Verify configuring and importing meters through the real flow manager."""

    async def asyncSetUp(self) -> None:
        """Register a meter with the real flow manager and stub platform setup."""
        config_dir = self.enterContext(TemporaryDirectory())
        self.hass = HomeAssistant(config_dir)
        self.entries = self.hass.config_entries = ConfigEntries(self.hass, {})
        self.hass.data[DOMAIN] = {}
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

    async def test_csv_import_creates_a_separate_meter_in_the_selected_unit(self) -> None:
        """Convert an exported reading into the new entry's primary unit and store it."""
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        content = export_meter_csv(
            "Electricity", "electricity", "kWh", [Reading(timestamp, 2)]
        )

        async def csv_chunks(_size: int):
            """Yield the downloaded CSV bytes, including its UTF-8 BOM."""
            yield content.encode("utf-8")

        with (
            patch(
                "homeassistant.config_entries._async_get_flow_handler",
                return_value=ManualEnergyMeteringConfigFlow,
            ),
            patch(
                "homeassistant.config_entries._support_single_config_entry_only",
                return_value=False,
            ),
            patch.object(
                ManualEnergyMeteringConfigFlow,
                "_async_external_panel_url",
                new_callable=AsyncMock,
                return_value="https://example.test/import",
            ),
            patch.object(self.entries, "async_setup"),
            patch.object(self.entries, "async_forward_entry_setups"),
            patch.object(meter_module, "async_add_external_statistics"),
        ):
            menu = await self.entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )
            flow_id = menu["flow_id"]
            external = await self.entries.flow.async_configure(
                flow_id, {"next_step_id": "import_csv"}
            )
            self.assertEqual(external["type"], "external")
            app = web.Application()
            app[KEY_HASS] = self.hass
            request = make_mocked_request(
                "POST",
                f"{CSV_IMPORT_URL}?flow_id={flow_id}&name=Electricity+in+MJ&unit=MJ",
                app=app,
                payload=SimpleNamespace(iter_chunked=csv_chunks),
            )
            request[KEY_HASS_USER] = SimpleNamespace(is_admin=True)
            accepted = await CsvImportView().post(request)
            self.assertEqual(accepted.status, 200, accepted.text)
            self.assertEqual(json.loads(accepted.text)["unit"], "MJ")
            vision = await self.entries.flow.async_configure(flow_id)
            self.assertEqual(vision["step_id"], "vision")
            result = await self.entries.flow.async_configure(flow_id, {})
            imported_entry = result["result"]
            self.assertNotEqual(imported_entry.unique_id, self.entry.unique_id)
            self.assertEqual(self.entry.data["unit"], "kWh")
            await async_setup_entry(self.hass, imported_entry)

        imported = imported_entry.runtime_data
        self.assertEqual(imported.unit, "MJ")
        self.assertEqual(len(imported.readings), 1)
        self.assertEqual(imported.latest_reading.timestamp, timestamp)
        self.assertAlmostEqual(imported.latest_reading.value, 7.2)
        self.assertNotEqual(imported.statistic_id, f"{DOMAIN}:{self.entry.unique_id}")
