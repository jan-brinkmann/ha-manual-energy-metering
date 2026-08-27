"""Tests for the pure interpolation logic."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

MODULE_DIR = (
    Path(__file__).parents[1] / "custom_components" / "manual_energy_metering"
)
sys.path.insert(0, str(MODULE_DIR))

from interpolation import Reading, hourly_consumption, interpolate_value  # noqa: E402


class HourlyConsumptionTests(unittest.TestCase):
    """Verify linear allocation into Home Assistant statistics hours."""

    def test_water_example_allocates_one_liter_per_hour(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, tzinfo=timezone.utc), 1),
            Reading(datetime(2026, 1, 2, tzinfo=timezone.utc), 25),
        ]

        result = hourly_consumption(readings)

        self.assertEqual(len(result), 24)
        self.assertTrue(all(item.consumption == 1 for item in result))
        self.assertEqual(result[-1].cumulative, 24)

    def test_electricity_example_allocates_one_kwh_per_hour(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, tzinfo=timezone.utc), 1000),
            Reading(datetime(2027, 1, 1, tzinfo=timezone.utc), 9760),
        ]

        result = hourly_consumption(readings)

        self.assertEqual(len(result), 365 * 24)
        self.assertTrue(all(item.consumption == 1 for item in result))
        self.assertEqual(result[-1].cumulative, 8760)

    def test_partial_hours_receive_proportional_consumption(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc), 10),
            Reading(datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc), 25),
        ]

        result = hourly_consumption(readings)

        self.assertEqual([item.consumption for item in result], [5, 10])
        self.assertEqual(result[-1].cumulative, 15)

    def test_multiple_segments_in_one_hour_are_combined(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), 0),
            Reading(datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc), 5),
            Reading(datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc), 20),
        ]

        result = hourly_consumption(readings)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].consumption, 20)

    def test_sensor_value_is_interpolated_between_future_endpoints(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), 10),
            Reading(datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc), 30),
        ]

        value = interpolate_value(
            readings, datetime(2026, 1, 1, 0, 45, tzinfo=timezone.utc)
        )

        self.assertEqual(value, 17.5)

    def test_decreasing_reading_is_rejected(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, tzinfo=timezone.utc), 10),
            Reading(datetime(2026, 1, 2, tzinfo=timezone.utc), 9),
        ]

        with self.assertRaisesRegex(ValueError, "must not decrease"):
            hourly_consumption(readings)


class IntegrationIdentityTests(unittest.TestCase):
    """Verify the canonical domain and its derived identifiers."""

    def test_domain_and_identifiers_are_consistent(self) -> None:
        manifest = json.loads((MODULE_DIR / "manifest.json").read_text())
        constants = (MODULE_DIR / "const.py").read_text()
        meter = (MODULE_DIR / "meter.py").read_text()
        sensor = (MODULE_DIR / "sensor.py").read_text()

        self.assertEqual(MODULE_DIR.name, "manual_energy_metering")
        self.assertEqual(manifest["domain"], "manual_energy_metering")
        self.assertIn("manual_energy_metering", constants)
        self.assertIn("STORAGE_KEY_PREFIX = DOMAIN", constants)
        self.assertIn("STORAGE_KEY_PREFIX}.{self.meter_id}", meter)
        self.assertIn("self._attr_unique_id = meter.meter_id", sensor)
        self.assertIn("identifiers={(DOMAIN, meter.meter_id)}", sensor)

    def test_visible_integration_names(self) -> None:
        manifest = json.loads((MODULE_DIR / "manifest.json").read_text())
        german = json.loads(
            (MODULE_DIR / "translations" / "de.json").read_text()
        )

        self.assertEqual(manifest["name"], "Manual Energy Metering")
        self.assertEqual(german["title"], "Manuelle Energiemessung")

if __name__ == "__main__":
    unittest.main()
