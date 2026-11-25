"""Regression tests for converted gas statistics and their saved settings."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

try:
    from homeassistant.core import HomeAssistant

    from custom_components.manual_energy_metering import meter as meter_module
    from custom_components.manual_energy_metering.meter import (
        ManualEnergyMetering,
        ReadingError,
    )
    from custom_components.manual_energy_metering.websocket_api import _meter_payload
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
