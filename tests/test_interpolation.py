"""Tests for the pure interpolation logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest

MODULE_DIR = (
    Path(__file__).parents[1] / "custom_components" / "manual_energy_metering"
)
sys.path.insert(0, str(MODULE_DIR))

from interpolation import (  # noqa: E402
    DuplicateTimestampError,
    Reading,
    hourly_consumption,
    interpolate_value,
    paginate_readings,
    remove_reading,
    replace_reading,
    upsert_reading,
)


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

    def test_removing_middle_reading_replaces_interpolation(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), 0),
            Reading(datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc), 60),
            Reading(datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc), 90),
        ]

        updated, deleted = remove_reading(
            readings, datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        )
        result = hourly_consumption(updated)

        self.assertEqual(deleted, readings[1])
        self.assertEqual([item.consumption for item in result], [15] * 6)

    def test_inserting_middle_reading_splits_interpolation(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc), 0),
            Reading(datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc), 60),
        ]

        updated = upsert_reading(
            readings,
            Reading(datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc), 15),
        )
        result = hourly_consumption(updated)

        self.assertEqual(
            [item.consumption for item in result], [5, 5, 5, 15, 15, 15]
        )

    def test_replacing_reading_updates_timestamp_and_value(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc), 10),
            Reading(datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc), 20),
            Reading(datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc), 40),
        ]
        replacement_reading = Reading(
            datetime(2026, 1, 1, 16, 0, tzinfo=timezone.utc), 30
        )

        updated, original = replace_reading(
            readings,
            datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
            replacement_reading,
        )

        self.assertEqual(original, readings[1])
        self.assertEqual(updated[1], replacement_reading)

    def test_replacing_reading_rejects_an_occupied_timestamp(self) -> None:
        readings = [
            Reading(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc), 10),
            Reading(datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc), 20),
            Reading(datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc), 40),
        ]

        with self.assertRaises(DuplicateTimestampError):
            replace_reading(
                readings,
                datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
                Reading(
                    datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc), 30
                ),
            )


class PaginationTests(unittest.TestCase):
    """Verify the current page and reverse-chronological archive pages."""

    @staticmethod
    def _readings(count: int) -> list[Reading]:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return [
            Reading(start + timedelta(hours=index), index)
            for index in range(count)
        ]

    def test_first_page_contains_only_the_ten_newest_readings(self) -> None:
        readings, page, page_count = paginate_readings(self._readings(211))

        self.assertEqual((page, page_count), (1, 4))
        self.assertEqual(
            [reading.value for reading in readings], list(range(210, 200, -1))
        )

    def test_archive_pages_contain_up_to_one_hundred_readings(self) -> None:
        all_readings = self._readings(211)

        second, second_page, _ = paginate_readings(all_readings, 2)
        third, third_page, _ = paginate_readings(all_readings, 3)
        fourth, fourth_page, page_count = paginate_readings(all_readings, 4)

        self.assertEqual(
            (second_page, third_page, fourth_page, page_count), (2, 3, 4, 4)
        )
        self.assertEqual(
            [reading.value for reading in second], list(range(200, 100, -1))
        )
        self.assertEqual(
            [reading.value for reading in third], list(range(100, 0, -1))
        )
        self.assertEqual([reading.value for reading in fourth], [0])

    def test_ten_or_fewer_readings_use_a_single_latest_page(self) -> None:
        readings, page, page_count = paginate_readings(self._readings(7), 99)

        self.assertEqual((page, page_count), (1, 1))
        self.assertEqual(
            [reading.value for reading in readings], list(range(6, -1, -1))
        )


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
        hacs = json.loads((MODULE_DIR.parents[1] / "hacs.json").read_text())
        german = json.loads(
            (MODULE_DIR / "translations" / "de.json").read_text()
        )

        self.assertEqual(manifest["name"], "Manual Energy Metering")
        self.assertEqual(manifest["codeowners"], ["@jan-brinkmann"])
        self.assertEqual(hacs["name"], "Manual Energy Metering")
        self.assertFalse((MODULE_DIR / "hacs.json").exists())
        self.assertEqual(german["title"], "Manuelle Energiemessung")

    def test_readings_panel_replaces_the_options_flow(self) -> None:
        config_flow = (MODULE_DIR / "config_flow.py").read_text()
        init = (MODULE_DIR / "__init__.py").read_text()
        panel = (MODULE_DIR / "panel.py").read_text()
        frontend = (MODULE_DIR / "frontend" / "panel.js").read_text()

        self.assertNotIn("OptionsFlow", config_flow)
        self.assertIn("async_register_readings_panel(hass)", init)
        self.assertIn("config_panel_domain=DOMAIN", panel)
        self.assertIn('const second = zeroSeconds ? "00"', frontend)
        websocket_api = (MODULE_DIR / "websocket_api.py").read_text()
        self.assertIn("paginate_readings", websocket_api)
        self.assertIn("CONF_METER_TYPE: meter.meter_type", websocket_api)
        self.assertIn("useGrouping: false", frontend)
        self.assertIn("_renderPagination", frontend)
        self.assertIn("_renderMeterTypeIcon", frontend)
        for meter_type in ("electricity", "gas", "water"):
            icon = MODULE_DIR / "frontend" / "icons" / f"{meter_type}.png"
            self.assertTrue(icon.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
