"""Tests for the pure interpolation logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

MODULE_DIR = (
    Path(__file__).parents[1] / "custom_components" / "manual_energy_metering"
)
sys.path.insert(0, str(MODULE_DIR))

import interpolation as interpolation_module  # noqa: E402
from interpolation import (  # noqa: E402
    DuplicateTimestampError,
    Reading,
    changed_hourly_statistics,
    hourly_consumption,
    interpolate_value,
    paginate_readings,
    remove_reading,
    replace_reading,
    upsert_reading,
)
from vision import (  # noqa: E402
    MAX_VISION_IMAGE_BYTES,
    VisionError,
    chat_completions_url,
    normalize_vision_url,
    recognition_request,
    recognized_value,
    validate_image,
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


class HourlyStatisticsUpdateTests(unittest.TestCase):
    """Verify that only genuinely changed statistics hours are touched."""

    @staticmethod
    def _reading(hour: int, value: float) -> Reading:
        return Reading(datetime(2026, 1, 1, hour, tzinfo=timezone.utc), value)

    def test_identical_readings_do_not_create_an_update(self) -> None:
        readings = [self._reading(0, 0), self._reading(6, 60)]

        update = changed_hourly_statistics(readings, readings, 0)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual(update.upsert, ())

    def test_collinear_insert_preserves_every_existing_hour(self) -> None:
        old = [self._reading(0, 0), self._reading(6, 60)]
        new = [old[0], self._reading(3, 30), old[1]]

        with patch.object(
            interpolation_module,
            "_hourly_consumption_at",
            wraps=interpolation_module._hourly_consumption_at,
        ) as calculator:
            update = changed_hourly_statistics(old, new, 0)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual(update.upsert, ())
        calculator.assert_not_called()

    def test_middle_insert_updates_only_its_neighboring_intervals(self) -> None:
        old = [
            self._reading(0, 0),
            self._reading(6, 60),
            self._reading(9, 90),
        ]
        new = [old[0], self._reading(3, 15), old[1], old[2]]

        update = changed_hourly_statistics(old, new, 0)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual([item.start.hour for item in update.upsert], list(range(6)))

    def test_middle_delete_updates_only_its_neighboring_intervals(self) -> None:
        old = [
            self._reading(0, 0),
            self._reading(3, 15),
            self._reading(6, 60),
            self._reading(9, 90),
        ]
        new = [old[0], old[2], old[3]]

        update = changed_hourly_statistics(old, new, 0)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual([item.start.hour for item in update.upsert], list(range(6)))

    def test_middle_value_change_does_not_touch_later_intervals(self) -> None:
        old = [
            self._reading(0, 0),
            self._reading(3, 30),
            self._reading(6, 60),
            self._reading(9, 90),
        ]
        new = [old[0], self._reading(3, 15), old[2], old[3]]

        update = changed_hourly_statistics(old, new, 0)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual([item.start.hour for item in update.upsert], list(range(6)))

    def test_collinear_timestamp_change_preserves_every_hour(self) -> None:
        old = [
            self._reading(0, 0),
            self._reading(3, 30),
            self._reading(6, 60),
        ]
        new = [old[0], self._reading(4, 40), old[2]]

        update = changed_hourly_statistics(old, new, 0)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual(update.upsert, ())

    def test_change_within_one_hour_preserves_the_same_hour_total(self) -> None:
        old = [
            Reading(datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc), 0),
            Reading(datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc), 10),
            Reading(datetime(2026, 1, 1, 0, 50, tzinfo=timezone.utc), 20),
        ]
        new = [old[0], Reading(old[1].timestamp, 5), old[2]]

        update = changed_hourly_statistics(old, new, 0)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual(update.upsert, ())

    def test_partial_hours_update_only_across_the_neighboring_boundary(self) -> None:
        old = [
            Reading(datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc), 0),
            Reading(datetime(2026, 1, 1, 0, 40, tzinfo=timezone.utc), 30),
            Reading(datetime(2026, 1, 1, 1, 20, tzinfo=timezone.utc), 70),
            Reading(datetime(2026, 1, 1, 3, 20, tzinfo=timezone.utc), 190),
        ]
        new = [old[0], Reading(old[1].timestamp, 20), old[2], old[3]]

        update = changed_hourly_statistics(old, new, 0)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual([item.start.hour for item in update.upsert], [0, 1])

    def test_deleting_first_reading_only_removes_its_old_hours(self) -> None:
        old = [
            self._reading(0, 0),
            self._reading(3, 30),
            self._reading(6, 60),
        ]

        update = changed_hourly_statistics(old, old[1:], 0)

        self.assertEqual(
            [start.hour for start in update.delete_starts], [0, 1, 2]
        )
        self.assertEqual(update.upsert, ())

    def test_adding_earlier_reading_preserves_existing_later_hours(self) -> None:
        old = [self._reading(3, 30), self._reading(6, 60)]
        new = [self._reading(0, 0), *old]

        update = changed_hourly_statistics(old, new, 30)

        self.assertEqual(update.delete_starts, ())
        self.assertEqual([item.start.hour for item in update.upsert], [0, 1, 2])

    def test_deleting_last_reading_only_removes_its_old_hours(self) -> None:
        old = [
            self._reading(0, 0),
            self._reading(3, 30),
            self._reading(6, 60),
        ]

        update = changed_hourly_statistics(old, old[:-1], 0)

        self.assertEqual(
            [start.hour for start in update.delete_starts], [3, 4, 5]
        )
        self.assertEqual(update.upsert, ())


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


class VisionProtocolTests(unittest.TestCase):
    """Verify safe OpenAI-compatible image requests and responses."""

    def test_host_and_ollama_urls_are_normalized(self) -> None:
        self.assertEqual(
            normalize_vision_url("ollama:11434"), "http://ollama:11434"
        )
        self.assertEqual(
            chat_completions_url("http://ollama:11434"),
            "http://ollama:11434/v1/chat/completions",
        )
        self.assertEqual(
            chat_completions_url("http://ollama:11434/v1"),
            "http://ollama:11434/v1/chat/completions",
        )
        self.assertEqual(
            chat_completions_url("https://provider.example/chat/completions"),
            "https://provider.example/chat/completions",
        )

    def test_provider_url_rejects_credentials_query_and_invalid_port(self) -> None:
        invalid_urls = (
            "http://user:secret@ollama:11434",
            "http://ollama:11434?token=secret",
            "http://ollama:not-a-port",
        )
        for api_url in invalid_urls:
            with self.subTest(api_url=api_url):
                with self.assertRaises(VisionError):
                    chat_completions_url(api_url)

    def test_request_contains_only_prompt_and_image_content(self) -> None:
        request = recognition_request(
            "qwen2.5vl:7b",
            "Read the meter and return JSON.",
            "YWJj",
            "image/jpeg",
        )

        self.assertEqual(request["model"], "qwen2.5vl:7b")
        self.assertEqual(
            request["messages"],
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Read the meter and return JSON.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64,YWJj"
                            },
                        },
                    ],
                }
            ],
        )

    def test_recognized_value_accepts_json_and_decimal_comma(self) -> None:
        markdown = {
            "choices": [
                {"message": {"content": '```json\n{"value":"123.45"}\n```'}}
            ]
        }
        decimal_comma = {
            "choices": [{"message": {"content": '{"value":"12,5"}'}}]
        }

        self.assertEqual(recognized_value(markdown), 123.45)
        self.assertEqual(recognized_value(decimal_comma), 12.5)

    def test_unreadable_and_ambiguous_values_are_rejected(self) -> None:
        unreadable = {
            "choices": [{"message": {"content": '{"error":"unreadable"}'}}]
        }
        ambiguous = {
            "choices": [{"message": {"content": '{"value":"1,234.5"}'}}]
        }

        with self.assertRaisesRegex(VisionError, "not recognized"):
            recognized_value(unreadable)
        with self.assertRaisesRegex(VisionError, "not numeric"):
            recognized_value(ambiguous)

    def test_image_validation_enforces_type_content_and_size(self) -> None:
        validate_image(b"\xff\xd8\xffjpeg", "image/jpeg")
        validate_image(b"\x89PNG\r\n\x1a\npng", "image/png")
        validate_image(b"RIFF\x04\x00\x00\x00WEBP", "image/webp")
        with self.assertRaisesRegex(VisionError, "Unsupported"):
            validate_image(b"abc", "image/gif")
        with self.assertRaisesRegex(VisionError, "empty"):
            validate_image(b"", "image/jpeg")
        with self.assertRaisesRegex(VisionError, "does not match"):
            validate_image(b"not-a-jpeg", "image/jpeg")
        with self.assertRaisesRegex(VisionError, "too large"):
            validate_image(
                b"\xff\xd8\xff" + b"x" * MAX_VISION_IMAGE_BYTES,
                "image/jpeg",
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

    def test_documentation_is_concise_and_ordered(self) -> None:
        root = MODULE_DIR.parents[1]
        english = (root / "README.md").read_text()
        german = (root / "README.de.md").read_text()

        english_headings = [
            line[3:] for line in english.splitlines() if line.startswith("## ")
        ]
        german_headings = [
            line[3:] for line in german.splitlines() if line.startswith("## ")
        ]
        self.assertEqual(
            english_headings[english_headings.index("Energy Dashboard") + 1],
            "Dashboard card",
        )
        self.assertEqual(
            english_headings[
                english_headings.index("Timestamps and entity history") + 1
            ],
            "Examples",
        )
        self.assertEqual(
            german_headings[german_headings.index("Energy Dashboard") + 1],
            "Dashboard-Karte",
        )
        self.assertEqual(
            german_headings[
                german_headings.index("Zeitangaben und Entitätsverlauf") + 1
            ],
            "Beispiele",
        )
        dashboard_section = english.split("## Dashboard card", 1)[1].split(
            "\n## ", 1
        )[0]
        self.assertNotIn("```yaml", dashboard_section)
        self.assertNotIn("up to 100 older readings", english)
        self.assertNotIn("bis zu 100 ältere", german)
        self.assertNotIn("seconds set to `00`", english)
        self.assertNotIn("Sekunden `00`", german)
        self.assertNotIn("localized decimal separator", english)
        self.assertNotIn("lokalisierte Dezimaltrennzeichen", german)
        self.assertNotIn("1600 pixels", english)
        self.assertNotIn("20 MiB", english)
        self.assertNotIn("1600 Pixel", german)
        self.assertNotIn("20 MiB", german)

    def test_readings_panel_replaces_the_options_flow(self) -> None:
        config_flow = (MODULE_DIR / "config_flow.py").read_text()
        init = (MODULE_DIR / "__init__.py").read_text()
        meter = (MODULE_DIR / "meter.py").read_text()
        panel = (MODULE_DIR / "panel.py").read_text()
        frontend = (MODULE_DIR / "frontend" / "panel.js").read_text()

        self.assertNotIn("OptionsFlow", config_flow)
        self.assertIn("async_register_readings_panel(hass)", init)
        self.assertIn("config_panel_domain=DOMAIN", panel)
        self.assertIn('const second = zeroSeconds ? "00"', frontend)
        websocket_api = (MODULE_DIR / "websocket_api.py").read_text()
        self.assertIn("paginate_readings", websocket_api)
        self.assertIn("CONF_METER_TYPE: meter.meter_type", websocket_api)
        self.assertIn("ATTR_STATISTIC_ID: meter.statistic_id", websocket_api)
        self.assertIn("useGrouping: false", frontend)
        self.assertIn("_renderPagination", frontend)
        self.assertIn('dateTime: "Ablesedatum und Uhrzeit"', frontend)
        self.assertNotIn("jede folgende Archivseite", frontend)
        self.assertIn(
            "Zählerstände können auch zwischen zwei vorhandenen Zählerständen "
            "eingetragen werden.",
            frontend,
        )
        self.assertIn(
            "Nach dem Eintragen, Bearbeiten oder Löschen eines Zählerstands wird die "
            "Interpolation entsprechend angepasst.",
            frontend,
        )
        self.assertIn(
            'energyStatistic: "Entität für das Energy Dashboard:"', frontend
        )
        self.assertIn('energyStatistic: "Entity for the Energy Dashboard:"', frontend)
        self.assertIn("${this._renderStatisticId()}", frontend)
        self.assertIn("_renderMeterTypeIcon", frontend)
        self.assertIn("mdi:arrow-left", frontend)
        self.assertIn("window.history.back()", frontend)
        self.assertNotIn("async_clear_statistics", meter)
        self.assertNotIn("async_rebuild_statistics", meter)
        self.assertNotIn("async_rebuild_statistics", init)
        self.assertIn("changed_hourly_statistics", meter)
        self.assertIn("Statistics.start_ts.in_(batch)", meter)
        self.assertIn('"statistics_baseline"', meter)
        for meter_type in ("electricity", "gas", "water"):
            icon = MODULE_DIR / "frontend" / "icons" / f"{meter_type}.png"
            self.assertTrue(icon.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_dashboard_card_is_registered_and_entity_scoped(self) -> None:
        manifest = json.loads((MODULE_DIR / "manifest.json").read_text())
        panel = (MODULE_DIR / "panel.py").read_text()
        websocket_api = (MODULE_DIR / "websocket_api.py").read_text()
        card = (MODULE_DIR / "frontend" / "card.js").read_text()

        self.assertIn("frontend", manifest["dependencies"])
        self.assertIn("lovelace", manifest["dependencies"])
        self.assertIn("async_get_integration(hass, DOMAIN)", panel)
        self.assertIn(
            'hass, f"{CARD_URL}?v={integration.version}"',
            panel,
        )
        self.assertIn("ResourceStorageCollection", panel)
        self.assertIn("CONF_RESOURCE_TYPE_WS", panel)
        self.assertIn("resources.async_create_item", panel)
        self.assertIn("resources.async_update_item", panel)
        self.assertIn('item.get(CONF_URL, "").partition("?")[0]', panel)
        self.assertIn("add_extra_js_url(hass, card_url)", panel)
        self.assertIn('CARD_URL = f"{PANEL_URL}/card.js"', panel)
        self.assertIn("WS_CARD_ADD_READING", websocket_api)
        self.assertIn("POLICY_CONTROL", websocket_api)
        self.assertIn("permissions.check_entity", websocket_api)
        self.assertIn("entity_entry.platform != DOMAIN", websocket_api)
        self.assertIn('vol.Required("entity_id"): cv.entity_id', websocket_api)
        card_command = websocket_api[
            websocket_api.index('vol.Required("type"): WS_CARD_ADD_READING') :
        ]
        self.assertNotIn("@websocket_api.require_admin", card_command)
        self.assertIn("customElements.define(CARD_TAG", card)
        self.assertIn("window.customCards", card)
        self.assertIn("Object.assign(existingMetadata, cardMetadata)", card)
        self.assertIn("getConfigElement", card)
        self.assertIn('filter: [{ integration: DOMAIN, domain: "sensor" }]', card)
        self.assertIn("show_name", card)
        self.assertIn("show_last_reading", card)
        self.assertIn("show_last_reading_timestamp", card)
        self.assertIn("show_photo_buttons", card)
        self.assertIn("show_history_link", card)
        self.assertIn("prefill_digits: 0", card)
        self.assertIn('name: "prefill_digits"', card)
        self.assertIn('number: { min: 0, step: 1, mode: "box" }', card)
        self.assertIn("_ensurePrefilledValue()", card)
        self.assertIn("_prefilledReading()", card)
        self.assertIn("digitCount >= digitLimit", card)
        self.assertIn("this._valueDirty = true", card)
        self.assertIn("meterType: attributes.meter_type", card)
        self.assertIn("_renderMeterTypeIcon(data.meterType)", card)
        self.assertIn('water: "water.png"', card)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", card)
        self.assertIn(".summary div:only-child", card)
        self.assertNotIn('class="accent"', card)
        self.assertIn('class="form-actions"', card)
        self.assertIn('icon="mdi:plus"', card)
        self.assertIn("${this._renderHistoryLink()}", card)
        self.assertNotIn("${this._escape(t.newReading)}", card)
        self.assertNotIn("value-hint", card)
        self.assertIn('type: "config/entity_registry/get"', card)
        self.assertIn("entityEntry.config_entry_id", card)
        self.assertIn("encodeURIComponent", card)
        self.assertIn('type="datetime-local"', card)
        self.assertIn("${parts.minute}:00", card)
        self.assertIn('type: `${DOMAIN}/card/add`', card)
        self.assertIn("useGrouping: false", card)

    def test_photo_recognition_is_independent_per_meter_and_confirmed(self) -> None:
        constants = (MODULE_DIR / "const.py").read_text()
        config_flow = (MODULE_DIR / "config_flow.py").read_text()
        init = (MODULE_DIR / "__init__.py").read_text()
        sensor = (MODULE_DIR / "sensor.py").read_text()
        websocket_api = (MODULE_DIR / "websocket_api.py").read_text()
        vision_http = (MODULE_DIR / "vision_http.py").read_text()
        vision = (MODULE_DIR / "vision.py").read_text()
        card = (MODULE_DIR / "frontend" / "card.js").read_text()
        english_strings = json.loads((MODULE_DIR / "strings.json").read_text())
        german_strings = json.loads(
            (MODULE_DIR / "translations" / "de.json").read_text()
        )

        self.assertIn('DEFAULT_VISION_MODEL = "qwen2.5vl:7b"', constants)
        self.assertIn("DEFAULT_VISION_COMPRESS_IMAGE = True", constants)
        self.assertIn("DEFAULT_VISION_PROMPT", constants)
        self.assertNotIn("DATA_VISION_CONFIG", constants)
        self.assertIn("VERSION = 6", config_flow)
        self.assertIn("async_step_vision", config_flow)
        self.assertIn("async_step_reconfigure", config_flow)
        self.assertIn("TextSelectorType.PASSWORD", config_flow)
        self.assertIn("CONF_VISION_COMPRESS_IMAGE", config_flow)
        self.assertIn("data_updates={**entry.data, **vision_data}", config_flow)
        self.assertIn("async_migrate_entry", init)
        self.assertIn(
            "data[CONF_VISION_COMPRESS_IMAGE] = DEFAULT_VISION_COMPRESS_IMAGE",
            init,
        )
        self.assertIn("data[CONF_VISION_MODEL] = DEFAULT_VISION_MODEL", init)
        self.assertIn("data[CONF_VISION_PROMPT] = DEFAULT_VISION_PROMPT", init)
        self.assertNotIn("VisionConfigStore", init)
        self.assertIn("data = meter.entry.data", vision)
        self.assertIn("PROVIDER_CONNECT_TIMEOUT_SECONDS = 5", vision)
        self.assertIn("PROVIDER_RESPONSE_TIMEOUT_SECONDS = 90", vision)
        self.assertIn("sock_connect=PROVIDER_CONNECT_TIMEOUT_SECONDS", vision)
        self.assertIn("sock_read=PROVIDER_RESPONSE_TIMEOUT_SECONDS", vision)
        self.assertIn('"vision_provider_timeout"', vision)
        self.assertIn("VisionProgressCallback", vision)
        self.assertIn("ProgressBytesPayload", vision)
        self.assertIn('await report_progress("connecting")', vision)
        self.assertIn('await report_progress("request_sent")', vision)
        self.assertIn('await report_progress("response_received")', vision)
        self.assertIn('await report_progress("completed")', vision)
        self.assertIn('stream.content_type = "text/event-stream"', vision_http)
        self.assertIn('"event": "progress"', vision_http)
        self.assertIn('"event": "error"', vision_http)
        self.assertIn('"event": "result"', vision_http)
        self.assertIn("progress=send_progress", vision_http)
        self.assertIn("VISION_REQUEST_TIMEOUT_MS = 120 * 1000", card)
        self.assertIn("RECOGNITION_STAGES", card)
        self.assertIn('"connecting"', card)
        self.assertIn('"request_sent"', card)
        self.assertIn('"response_received"', card)
        self.assertIn('"completed"', card)
        self.assertIn("_renderRecognitionProgress()", card)
        self.assertIn("response.body.getReader()", card)
        self.assertIn('Accept: "text/event-stream, application/json"', card)
        self.assertIn("new AbortController()", card)
        self.assertIn("controller.signal.aborted", card)
        self.assertIn("window.clearTimeout(timeoutId)", card)
        self.assertNotIn("last_reading_timestamp", vision)
        self.assertNotIn("meter_type", vision)
        self.assertIn('ATTR_VISION_CONFIGURED = "vision_configured"', constants)
        self.assertIn("ATTR_VISION_CONFIGURED", sensor)
        self.assertIn("CONF_VISION_COMPRESS_IMAGE", sensor)
        self.assertNotIn("WS_CARD_RECOGNIZE", websocket_api)
        self.assertIn("permissions.check_entity", websocket_api)
        self.assertIn("permissions.check_entity", vision_http)
        self.assertIn("request.content.iter_chunked", vision_http)
        self.assertIn('request.headers.get("Content-Encoding"', vision_http)
        self.assertIn("bytes(image)", vision_http)
        self.assertIn("hass.http.register_view(VisionRecognitionView)", init)
        self.assertIn('capture="environment"', card)
        self.assertIn('icon="mdi:image-plus"', card)
        self.assertIn("_isAndroidCompanionApp()", card)
        self.assertIn('typeof window.externalApp !== "undefined"', card)
        self.assertIn('typeof window.externalAppV2 !== "undefined"', card)
        self.assertIn('facingMode: { exact: "environment" }', card)
        self.assertIn("navigator.mediaDevices", card)
        self.assertIn("navigator.mediaDevices.getUserMedia", card)
        self.assertIn("navigator.webkitGetUserMedia", card)
        self.assertIn("window.isSecureContext === false", card)
        self.assertIn('error.code = "camera_insecure_context"', card)
        self.assertIn("cameraSecureContextRequired", card)
        self.assertIn("stream.getTracks().forEach", card)
        self.assertIn("await this._recognizeFile(file, false)", card)
        capture_method = card[
            card.index("  async _captureCameraPhoto()") :
            card.index("  _closeCamera(render = true)")
        ]
        open_camera_method = card[
            card.index("  async _openCamera()") :
            card.index("  async _requestRearCameraStream()")
        ]
        self.assertLess(
            capture_method.index("this._closeCamera();"),
            capture_method.index("const blob = await blobPromise;"),
        )
        self.assertLess(
            capture_method.index('this._recognitionStage = "preparing";'),
            capture_method.index("this._closeCamera();"),
        )
        self.assertLess(
            capture_method.index("this._busy = true;"),
            capture_method.index("this._closeCamera();"),
        )
        self.assertIn("this._busy = false;", capture_method)
        self.assertIn("this._recognitionStage = undefined;", open_camera_method)
        self.assertIn("video.srcObject = null", card)
        self.assertIn("window.requestAnimationFrame", capture_method)
        self.assertEqual(card.count('data-read-photo-timestamp="true"'), 1)
        self.assertIn("canvas.toBlob", card)
        self.assertIn("if (compressImage)", card)
        self.assertIn("attributes.vision_compress_image !== false", card)
        self.assertIn("file.arrayBuffer()", card)
        self.assertIn("dateTimeOriginal: 0x9003", card)
        self.assertIn("dateTimeDigitized: 0x9004", card)
        self.assertIn("dateTime: 0x0132", card)
        self.assertIn("_findExifTiff(view)", card)
        self.assertIn("_formatExifDateTime(metadata)", card)
        self.assertIn("photoTimestamp || currentTimestamp", card)
        self.assertIn("this._formTimestamp = photoTimestamp", card)
        self.assertNotIn("pad(second)", card)
        self.assertNotIn("parts.second", card)
        self.assertIn("file: uploadFile", card)
        self.assertIn("body: prepared.file", card)
        self.assertIn("this._hass.fetchWithAuth", card)
        self.assertIn("this._formValue = this._formatInputReading", card)
        self.assertIn("this._formTimestamp = timestamp", card)
        self.assertNotIn("async_add_reading", vision)
        for step_id in ("vision", "reconfigure"):
            english_help = english_strings["config"]["step"][step_id][
                "data_description"
            ]["vision_compress_image"]
            german_help = german_strings["config"]["step"][step_id][
                "data_description"
            ]["vision_compress_image"]
            self.assertIn("1600", english_help)
            self.assertIn("20 MiB", english_help)
            self.assertIn("1600", german_help)
            self.assertIn("20 MiB", german_help)


if __name__ == "__main__":
    unittest.main()
