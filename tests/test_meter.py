"""Regression tests for secondary meter entities and their saved settings."""

from __future__ import annotations

import asyncio
import logging
import unittest
from datetime import UTC, datetime, timedelta
from tempfile import TemporaryDirectory
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

try:
    from homeassistant.config_entries import (
        ConfigEntries,
        ConfigEntry,
        ConfigEntryState,
    )
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import device_registry, entity_platform, entity_registry

    from custom_components.manual_energy_metering import meter as meter_module
    from custom_components.manual_energy_metering import sensor as sensor_platform
    from custom_components.manual_energy_metering import statistics_export
    from custom_components.manual_energy_metering.const import DOMAIN
    from custom_components.manual_energy_metering.csv_transfer import CsvTransferError
    from custom_components.manual_energy_metering.meter import (
        ManualEnergyMetering,
        ReadingError,
    )
    from custom_components.manual_energy_metering.sensor import (
        ManualEnergyMeteringSensor,
    )
    from custom_components.manual_energy_metering.websocket_api import (
        _meter_payload,
        websocket_card_add_reading,
    )
except ModuleNotFoundError as err:
    if err.name != "homeassistant":
        raise
    raise unittest.SkipTest("Home Assistant is required for meter tests") from err


class ConvertedGasStatisticsTests(unittest.IsolatedAsyncioTestCase):
    """Verify the option's recorder updates without starting a recorder thread."""

    async def asyncSetUp(self) -> None:
        """Use real storage and capture the tasks passed to the recorder."""
        self.hass = HomeAssistant(self.enterContext(TemporaryDirectory()))
        self.start = datetime(2026, 1, 1, tzinfo=UTC)
        self.publish = self.enterContext(
            patch.object(meter_module, "async_add_external_statistics")
        )
        self.recorder = self.enterContext(
            patch.object(meter_module, "get_instance")
        ).return_value
        self.list_statistics = self.enterContext(
            patch.object(
                meter_module, "async_list_statistic_ids", new_callable=AsyncMock
            )
        )

    def _meter(
        self, unit: str, *, meter_type: str = "gas", **settings: float
    ) -> ManualEnergyMetering:
        """Create or reload a meter with storage shared by entries of the same unit."""
        entry = SimpleNamespace(
            data={
                "meter_id": {"m³": "cubic_meters"}.get(unit, unit.lower()),
                "meter_type": meter_type,
                "unit": unit,
                **settings,
            }
        )
        return ManualEnergyMetering(self.hass, entry, "Meter")

    async def test_variant_units_and_default_conversion(self) -> None:
        """Convert hourly consumption and displayed registers in all gas units."""
        for unit, target, delta, expected in (
            ("m³", "kWh", 2, 20.9),
            ("L", "kWh", 2000, 20.9),
            ("kWh", "L", 20.9, 2000),
            ("MWh", "L", 0.0209, 2000),
        ):
            with self.subTest(unit=unit):
                meter = self._meter(unit)
                await meter.async_add_reading(delta, self.start)
                await meter.async_add_reading(
                    2 * delta, self.start + timedelta(hours=1)
                )
                payload = _meter_payload(meter)
                self.assertEqual(
                    payload["converted_statistics"],
                    {"unit": target, "statistic_id": None},
                )
                self.assertNotIn("converted_value", payload["readings"][0])

                await meter.async_set_converted_statistics(True)
                metadata, rows = self.publish.call_args.args[1:]
                payload = _meter_payload(meter)
                self.assertEqual(
                    payload["converted_statistics"]["statistic_id"],
                    meter.converted_statistic_id,
                )
                latest, first = payload["readings"]
                self.assertEqual(latest["value"], 2 * delta)
                self.assertAlmostEqual(latest["converted_value"], 2 * expected)
                self.assertAlmostEqual(first["converted_value"], expected)
                self.assertEqual(metadata["statistic_id"], meter.converted_statistic_id)
                self.assertEqual(metadata["unit_of_measurement"], target)
                self.assertEqual(
                    metadata["unit_class"], "volume" if target == "L" else "energy"
                )
                self.assertEqual(rows[0]["start"], self.start)
                self.assertAlmostEqual(rows[0]["state"], expected)
                self.assertAlmostEqual(rows[0]["sum"], expected)

    async def test_updates_removal_and_rebuild(self) -> None:
        """Keep both hourly plans aligned and rebuild only the converted statistic."""
        meter = self._meter("m³")
        middle = self.start + timedelta(hours=1)
        end = middle + timedelta(hours=1)
        await meter.async_add_reading(10, self.start)
        await meter.async_add_reading(14, end)
        await meter.async_set_converted_statistics(True)

        self.publish.reset_mock()
        await meter.async_add_reading(11, middle)
        primary, converted = (call.args[2] for call in self.publish.call_args_list)
        self.assertEqual([row["start"] for row in primary], [self.start, middle])
        self.assertEqual([row["start"] for row in converted], [self.start, middle])
        for base_row, converted_row in zip(primary, converted, strict=True):
            self.assertAlmostEqual(converted_row["state"], base_row["state"] * 10.45)
            self.assertAlmostEqual(converted_row["sum"], base_row["sum"] * 10.45)

        await meter.async_delete_reading(end)
        deleted = [call.args[0] for call in self.recorder.queue_task.call_args_list]
        self.assertEqual(
            [(task.statistic_id, task.starts) for task in deleted],
            [
                (meter.statistic_id, (middle,)),
                (meter.converted_statistic_id, (middle,)),
            ],
        )
        self.publish.reset_mock()
        await meter.async_set_converted_statistics(False)
        self.recorder.async_clear_statistics.assert_called_once_with(
            [meter.converted_statistic_id]
        )
        self.publish.assert_not_called()
        payload = _meter_payload(meter)
        self.assertIsNone(payload["converted_statistics"]["statistic_id"])
        self.assertNotIn("converted_value", payload["readings"][0])

        await meter.async_add_reading(15, end)
        self.publish.assert_called_once()
        self.publish.reset_mock()
        await meter.async_set_converted_statistics(True)
        self.publish.assert_called_once()
        metadata, rows = self.publish.call_args.args[1:]
        self.assertEqual(metadata["statistic_id"], meter.converted_statistic_id)
        self.assertEqual([row["start"] for row in rows], [self.start, middle])
        self.assertAlmostEqual(rows[-1]["sum"], 52.25)

    async def test_reload_and_changed_meter_factors(self) -> None:
        """Retain the setting and imported gaps when recalculating with new factors."""
        meter = self._meter("m³")
        end = self.start + timedelta(hours=2)
        await meter.async_import_readings(
            [
                {"timestamp": self.start, "value": 5},
                {"timestamp": end, "value": 9},
            ],
            {
                "source_statistic_id": "sensor.gas_meter",
                "excluded_hour_starts": [self.start],
            },
        )
        await meter.async_set_converted_statistics(True)
        self.list_statistics.return_value = [
            {"statistic_id": meter.converted_statistic_id}
        ]
        self.publish.reset_mock()

        reloaded = self._meter("m³")
        await reloaded.async_load()
        self.assertTrue(reloaded.converted_statistics_enabled)
        self.publish.assert_not_called()

        reconfigured = self._meter(
            "m³", gas_calorific_value=12, gas_correction_factor=0.8
        )
        await reconfigured.async_load()
        self.publish.assert_called_once()
        metadata, rows = self.publish.call_args.args[1:]
        self.assertEqual(metadata["statistic_id"], meter.converted_statistic_id)
        self.assertEqual(
            [row["start"] for row in rows], [self.start + timedelta(hours=1)]
        )
        self.assertAlmostEqual(rows[0]["state"], 19.2)
        self.assertAlmostEqual(rows[0]["sum"], 38.4)
        latest, first = _meter_payload(reconfigured)["readings"]
        self.assertAlmostEqual(latest["converted_value"], 86.4)
        self.assertAlmostEqual(first["converted_value"], 48)

    async def test_legacy_gas_selection_keeps_the_existing_statistic_id(self) -> None:
        """Load the former toggle's storage without replacing its recorder history."""
        for primary, legacy_unit, legacy_factors in (
            ("m³", "kWh", {"gas_calorific_value": 11.0, "gas_correction_factor": 0.95}),
            ("kWh", "L", {"gas_calorific_value": 11.0, "gas_correction_factor": 0.95}),
            ("L", "kWh", None),
        ):
            with self.subTest(primary=primary):
                meter = self._meter(primary)
                self.publish.reset_mock()
                self.recorder.reset_mock()
                legacy_id = f"manual_energy_metering:{meter.meter_id}_converted"
                await meter._store.async_save({
                    "readings": [{"timestamp": self.start.isoformat(), "value": 10}],
                    "converted_statistics": legacy_factors,
                })
                self.list_statistics.return_value = [{"statistic_id": legacy_id}]
                await meter.async_load()
                self.publish.assert_not_called()
                if legacy_factors is None:
                    self.assertEqual(meter.secondary_units, ())
                    self.recorder.async_clear_statistics.assert_called_once_with([legacy_id])
                else:
                    self.assertEqual(meter.secondary_units, (legacy_unit,))
                    self.assertEqual(_meter_payload(meter)["secondary_statistics"], {
                        legacy_unit: legacy_id
                    })
                    self.recorder.async_clear_statistics.assert_not_called()
                stored = await meter._store.async_load()
                self.assertEqual(stored["secondary_statistics"], {legacy_unit: legacy_factors is not None})

    async def test_multiple_secondary_units_survive_updates_and_reload(self) -> None:
        """Derive each unit's sensor, table readings, and history from one register."""
        meter = self._meter("kWh", meter_type="electricity")
        await meter.async_add_reading(10, self.start)
        await asyncio.gather(
            meter.async_set_secondary_unit("MWh", True),
            meter.async_set_secondary_unit("mWh", True),
        )
        ids = {unit: meter.secondary_statistic_id(unit) for unit in meter.secondary_units}
        self.assertEqual(set(ids), {"MWh", "mWh"})
        self.assertEqual(len(set(ids.values())), 2)
        self.publish.reset_mock()
        await meter.async_add_reading(12, self.start + timedelta(hours=1))
        changes = {
            call.args[1]["unit_of_measurement"]: call.args[2][0]["state"]
            for call in self.publish.call_args_list
        }
        self.assertEqual(changes, {"kWh": 2.0, "mWh": 2e6, "MWh": 0.002})
        self.assertEqual(
            _meter_payload(meter)["readings"][0]["converted_values"],
            {"mWh": 12e6, "MWh": 0.012},
        )
        sensor = ManualEnergyMeteringSensor(meter, "MWh")
        self.assertEqual(sensor.native_value, 0.012)
        self.assertEqual(sensor.native_unit_of_measurement, "MWh")
        self.assertIsNone(sensor.extra_state_attributes)

        await meter.async_set_secondary_unit("mWh", False)
        self.recorder.async_clear_statistics.assert_called_once_with([ids["mWh"]])
        self.list_statistics.return_value = [{"statistic_id": ids["MWh"]}]
        reloaded = self._meter("kWh", meter_type="electricity")
        await reloaded.async_load()
        self.assertEqual(reloaded.unit, "kWh")
        self.assertEqual(reloaded.secondary_units, ("MWh",))
        self.assertEqual(_meter_payload(reloaded)["secondary_statistics"], {"MWh": ids["MWh"]})
        self.assertEqual(reloaded.latest_reading.value, 12)

    async def test_reject_primary_and_incompatible_secondary_units(self) -> None:
        """Keep the primary water unit fixed and reject incompatible units."""
        meter = self._meter("m³", meter_type="water")
        for unit in ("m³", "Wh"):
            with self.subTest(unit=unit), self.assertRaises(ReadingError) as raised:
                await meter.async_set_secondary_unit(unit, True)
            self.assertEqual(raised.exception.translation_key, "invalid_secondary_unit")
        self.assertEqual(meter.secondary_units, ())

    async def _setup_sensor_platform(
        self, unit: str, *, meter_type: str = "gas"
    ) -> tuple[ManualEnergyMetering, entity_platform.EntityPlatform]:
        """Set up a meter's sensors in Home Assistant's real registries."""
        self.hass.config_entries = entries = ConfigEntries(self.hass, {})
        await entries.async_initialize()
        device_registry.async_setup(self.hass)
        await device_registry.async_load(self.hass, load_empty=True)
        await entity_registry.async_load(self.hass, load_empty=True)
        entry = ConfigEntry(
            data={"meter_type": meter_type, "meter_id": "meter", "unit": unit},
            discovery_keys=MappingProxyType({}),
            domain=DOMAIN,
            minor_version=1,
            options={},
            source="user",
            subentries_data=None,
            title=f"{meter_type.title()} Meter",
            unique_id="meter",
            version=6,
        )
        with patch.object(entries, "async_setup"):
            await entries.async_add(entry)
        meter = entry.runtime_data = ManualEnergyMetering(self.hass, entry, entry.title)
        platform = entity_platform.EntityPlatform(
            hass=self.hass,
            logger=logging.getLogger(__name__),
            domain="sensor",
            platform_name=DOMAIN,
            platform=sensor_platform,
            scan_interval=timedelta(seconds=30),
            entity_namespace=None,
        )
        self.addAsyncCleanup(platform.async_reset)
        with patch.object(entity_platform.PlatformData, "async_load_translations"):
            self.assertTrue(await platform.async_setup_entry(entry))
        return meter, platform

    async def test_sensor_platform_adds_and_removes_secondary_entities(self) -> None:
        """Check selection changes against Home Assistant's entity and device registries."""
        meter, platform = await self._setup_sensor_platform("CCF")
        registry = entity_registry.async_get(self.hass)
        await meter.async_add_reading(1, self.start)
        await meter.async_set_secondary_unit("kWh", True)
        await meter.async_set_secondary_unit("m³", True)
        primary_id = registry.async_get_entity_id("sensor", DOMAIN, meter.meter_id)
        energy_id = registry.async_get_entity_id(
            "sensor", DOMAIN, meter.secondary_sensor_id("kWh")
        )
        volume_id = registry.async_get_entity_id(
            "sensor", DOMAIN, meter.secondary_sensor_id("m³")
        )
        self.assertEqual(set(platform.entities), {primary_id, energy_id, volume_id})
        self.assertEqual(registry.async_get(primary_id).device_id, registry.async_get(energy_id).device_id)
        self.assertEqual(self.hass.states.get(energy_id).attributes["device_class"], "energy")
        self.assertEqual(self.hass.states.get(volume_id).attributes["device_class"], "gas")
        self.assertEqual(self.hass.states.get(volume_id).attributes["unit_of_measurement"], "m³")
        self.assertAlmostEqual(float(self.hass.states.get(volume_id).state), 2.8316846592)

        await meter.async_set_secondary_unit("kWh", False)
        self.assertIsNone(registry.async_get(energy_id))
        self.assertIsNone(self.hass.states.get(energy_id))
        self.assertIsNotNone(self.hass.states.get(volume_id))
        self.recorder.async_clear_statistics.assert_called_once_with(
            [f"{DOMAIN}:meter_converted"]
        )

        await meter.async_set_secondary_unit("kWh", True)
        self.assertIn(energy_id, platform.entities)

    async def test_secondary_energy_units_keep_distinct_entity_ids(self) -> None:
        """Keep mega- and milliwatt-hours separate when toggled in sequence."""
        meter, _ = await self._setup_sensor_platform("kWh", meter_type="electricity")
        registry = entity_registry.async_get(self.hass)
        entity_ids = {}
        for unit in ("MWh", "mWh"):
            await meter.async_set_secondary_unit(unit, True)
            entity_ids[unit] = registry.async_get_entity_id(
                "sensor", DOMAIN, meter.secondary_sensor_id(unit)
            )
            await meter.async_set_secondary_unit(unit, False)
        self.assertEqual(
            entity_ids,
            {
                "MWh": "sensor.electricity_meter_megawh",
                "mWh": "sensor.electricity_meter_milliwh",
            },
        )

        # A customized registry ID should still be restored on re-selection.
        await meter.async_set_secondary_unit("MWh", True)
        registry.async_update_entity(
            entity_ids["MWh"], new_entity_id="sensor.custom_energy"
        )
        await meter.async_set_secondary_unit("MWh", False)
        await meter.async_set_secondary_unit("MWh", True)
        self.assertEqual(
            registry.async_get_entity_id(
                "sensor", DOMAIN, meter.secondary_sensor_id("MWh")
            ),
            "sensor.custom_energy",
        )

    async def test_card_accepts_readings_only_for_the_primary_sensor(self) -> None:
        """Reject secondary submissions and derive both sensor values from one reading."""
        meter, _ = await self._setup_sensor_platform("kWh", meter_type="electricity")
        registry = entity_registry.async_get(self.hass)
        meter.entry._async_set_state(self.hass, ConfigEntryState.LOADED, None)
        await meter.async_set_secondary_unit("Wh", True)
        primary_id = registry.async_get_entity_id("sensor", DOMAIN, meter.meter_id)
        secondary_id = registry.async_get_entity_id(
            "sensor", DOMAIN, meter.secondary_sensor_id("Wh")
        )
        connection = Mock()
        connection.user.permissions.check_entity.return_value = True
        msg = {
            "id": 1,
            "entity_id": secondary_id,
            "value": 2,
            "timestamp": self.start.isoformat(),
        }
        await websocket_card_add_reading.__wrapped__(self.hass, connection, msg)
        connection.send_error.assert_called_once_with(
            1, "entity_not_found", "Select the primary meter entity."
        )
        self.assertEqual(meter.readings, ())

        await websocket_card_add_reading.__wrapped__(
            self.hass, connection, {**msg, "entity_id": primary_id}
        )
        connection.send_result.assert_called_once()
        self.assertEqual(meter.latest_reading.value, 2)
        self.assertEqual(float(self.hass.states.get(primary_id).state), 2)
        self.assertEqual(float(self.hass.states.get(secondary_id).state), 2000)

    async def test_csv_export_excludes_deselected_secondary_sensors(self) -> None:
        """Exclude lingering Recorder rows for a sensor removed from the registry."""
        meter, _ = await self._setup_sensor_platform("kWh", meter_type="electricity")
        registry = entity_registry.async_get(self.hass)
        await meter.async_set_secondary_unit("Wh", True)
        secondary_id = registry.async_get_entity_id(
            "sensor", DOMAIN, meter.secondary_sensor_id("Wh")
        )
        await meter.async_set_secondary_unit("Wh", False)
        self.assertIsNone(registry.async_get(secondary_id))
        self.hass.data[DOMAIN] = {meter.entry.entry_id: meter}
        self.enterContext(
            patch.object(
                statistics_export,
                "async_list_statistic_ids",
                AsyncMock(
                    return_value=[
                        {
                            "statistic_id": statistic_id,
                            "source": "recorder",
                            "has_sum": True,
                            "statistics_unit_of_measurement": "Wh",
                            "unit_class": "energy",
                        }
                        for statistic_id in (secondary_id, "sensor.external_meter")
                    ]
                ),
            )
        )
        recorder = self.enterContext(patch.object(statistics_export, "get_instance"))
        recorder.return_value.async_add_executor_job = AsyncMock(return_value={})

        options = await statistics_export.async_list_exportable_statistics(self.hass)
        self.assertEqual(
            {item["statistic_id"] for item in options},
            {meter.statistic_id, "sensor.external_meter"},
        )
        with self.assertRaises(CsvTransferError) as raised:
            await statistics_export.async_export_statistic(
                self.hass, secondary_id, "electricity"
            )
        self.assertEqual(raised.exception.code, "statistics_not_found")

    async def test_sub_watt_hour_correction_updates_terawatt_hour_statistics(self) -> None:
        """Publish a half watt-hour correction in the primary and secondary units."""
        meter = self._meter("TWh", meter_type="electricity")
        end = self.start + timedelta(hours=1)
        await meter.async_add_reading(0, self.start)
        await meter.async_add_reading(0.000000001, end)
        await meter.async_set_secondary_unit("Wh", True)
        self.publish.reset_mock()

        updated = 0.0000000010005
        await meter.async_update_reading(end, updated, end)

        rows = {
            metadata["unit_of_measurement"]: row
            for _, metadata, (row,) in (
                call.args for call in self.publish.call_args_list
            )
        }
        self.assertEqual(meter.latest_reading.value, updated)
        self.assertEqual(set(rows), {"TWh", "Wh"})
        for field in ("state", "sum"):
            self.assertAlmostEqual(rows["TWh"][field], updated, delta=1e-24)
            self.assertAlmostEqual(rows["Wh"][field], 1000.5)

    async def test_archive_includes_converted_readings(self) -> None:
        """Convert displayed readings on archived pages as well as the latest page."""
        meter = self._meter("m³")
        await meter.async_import_readings(
            [
                {"timestamp": self.start + timedelta(hours=index), "value": index}
                for index in range(12)
            ]
        )
        await meter.async_set_converted_statistics(True)

        payload = _meter_payload(meter, requested_page=2)
        self.assertEqual(payload["page"], 2)
        self.assertEqual(
            [row["converted_value"] for row in payload["readings"]], [10.45, 0.0]
        )

    async def test_unrepresentable_register_preserves_saved_reading(self) -> None:
        """Keep a reading accessible when its converted absolute value overflows."""
        meter = self._meter("m³")
        await meter.async_add_reading(1e308, self.start)
        await meter.async_set_converted_statistics(True)

        reading = _meter_payload(meter)["readings"][0]
        self.assertEqual(reading["value"], 1e308)
        self.assertIsNone(reading["converted_value"])

    async def test_other_meters_cannot_enable_conversion(self) -> None:
        """Hide the option and reject requests for a non-gas meter."""
        meter = self._meter("kWh", meter_type="electricity")
        self.assertIsNone(_meter_payload(meter)["converted_statistics"])
        with self.assertRaises(ReadingError) as raised:
            await meter.async_set_converted_statistics(True)
        self.assertEqual(raised.exception.translation_key, "not_gas_meter")
        self.publish.assert_not_called()
