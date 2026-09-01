from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from radar.client import (
    indicator_model,
    installed_plugins,
    projection_model,
    read_model,
    refresh,
    set_event_read_state,
    set_preferences,
    set_section_filter,
    set_section_profile,
    toggle_saved_state,
)
from radar.errors import ValidationError
from radar.io import atomic_write_json
from radar.state import feed_path, load_feed

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class ClientIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))
        fixture = root / "candidate.json"
        atomic_write_json(fixture, self.feed)
        self.fixture = fixture
        self.environment = {
            "HOME": str(root / "home"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
            "OMARCHY_NEWS_RADAR_TEST_MODE": "1",
            "OMARCHY_NEWS_RADAR_TEST_FEED": str(fixture),
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_first_use_refresh_cached_read_and_private_projection(self) -> None:
        self.assertEqual("first-use", read_model(self.environment, now=CLOCK)["status"])
        result = refresh(self.environment, now=CLOCK)
        self.assertEqual("current", result["status"])
        self.assertEqual("cached", read_model(self.environment, now=CLOCK)["status"])
        projected = projection_model(
            "for-you",
            '["io.github.mtolhuys.disk-lens"]',
            "",
            self.environment,
            now=CLOCK,
        )
        self.assertEqual(2, len(projected["events"]))
        self.assertNotIn("installedPluginIds", result)

        front_page = projection_model("front-page", "[]", "", self.environment, now=CLOCK)
        self.assertIn("community-link", {event["type"] for event in front_page["events"]})
        with self.assertRaisesRegex(ValidationError, "unknown projection section"):
            projection_model("community", "[]", "", self.environment, now=CLOCK)

    def test_invalid_candidate_preserves_last_known_good(self) -> None:
        self.assertEqual("current", refresh(self.environment, now=CLOCK)["status"])
        good = feed_path(self.environment).read_bytes()
        invalid = copy.deepcopy(self.feed)
        invalid["schemaVersion"] = 99
        atomic_write_json(self.fixture, invalid)
        result = refresh(self.environment, now=CLOCK)
        self.assertEqual("invalid-feed", result["status"])
        self.assertTrue(result["cachePreserved"])
        self.assertEqual(good, feed_path(self.environment).read_bytes())

    def test_truncated_and_oversized_candidates_do_not_replace_cache(self) -> None:
        self.assertEqual("current", refresh(self.environment, now=CLOCK)["status"])
        self.fixture.write_text("{", encoding="utf-8")
        self.assertEqual("invalid-feed", refresh(self.environment, now=CLOCK)["status"])
        self.fixture.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        self.assertEqual("invalid-feed", refresh(self.environment, now=CLOCK)["status"])
        self.assertIsNotNone(load_feed(self.environment, now=CLOCK))

    def test_saved_state_roundtrip_uses_only_validated_cache_event(self) -> None:
        refresh(self.environment, now=CLOCK)
        event_id = projection_model(
            "front-page", "[]", "", self.environment, now=CLOCK
        )["events"][0]["id"]
        saved = toggle_saved_state(event_id, self.environment, now=CLOCK)
        self.assertTrue(saved["saved"])
        projected = projection_model("saved", "[]", "", self.environment, now=CLOCK)
        self.assertEqual([event_id], [event["id"] for event in projected["events"]])

    def test_indicator_read_state_and_display_preferences_stay_local(self) -> None:
        refresh(self.environment, now=CLOCK)
        indicator = indicator_model(self.environment, now=CLOCK)
        self.assertGreater(indicator["unread"], 0)
        event_id = projection_model(
            "front-page", "[]", "", self.environment, now=CLOCK
        )["events"][0]["id"]
        reading = set_event_read_state(event_id, True, self.environment, now=CLOCK)
        self.assertTrue(reading["read"])
        self.assertEqual(indicator["unread"] - 1, indicator_model(self.environment, now=CLOCK)["unread"])
        projected_read = projection_model("front-page", "[]", "", self.environment, now=CLOCK)
        decorated = next(event for event in projected_read["events"] if event["id"] == event_id)
        self.assertFalse(decorated["isUnread"])
        self.assertGreaterEqual(projected_read["unreadCounts"]["front-page"], 0)

        reading = set_event_read_state(event_id, False, self.environment, now=CLOCK)
        self.assertFalse(reading["read"])
        self.assertEqual(indicator["unread"], indicator_model(self.environment, now=CLOCK)["unread"])
        tuned = set_preferences(
            bar_visible=False,
            images_visible=False,
            environment=self.environment,
        )
        self.assertFalse(tuned["state"]["preferences"]["barVisible"])
        self.assertNotIn("interests", tuned["state"]["preferences"])
        self.assertEqual([], projection_model("for-you", "[]", "", self.environment, now=CLOCK)["events"])
        self.assertFalse(indicator_model(self.environment, now=CLOCK)["barVisible"])

    def test_projection_paginates_decorates_metrics_and_applies_local_section_filter(self) -> None:
        refresh(self.environment, now=CLOCK)
        first = projection_model("front-page", "[]", "", self.environment, now=CLOCK, limit=1)
        self.assertEqual(1, len(first["events"]))
        self.assertGreater(first["totalEvents"], 1)
        self.assertTrue(first["hasMore"])
        self.assertEqual("No extra filters", first["filterSummary"])
        self.assertIn("sectionRule", first)
        self.assertIn("Official Omarchy releases", first["sectionSources"])

        plugins = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        metric_story = next(event for event in plugins["events"] if event.get("metricItems"))
        metric_items = {item["id"]: item for item in metric_story["metricItems"]}
        self.assertEqual("145", metric_items["marketplace-views"]["valueText"])
        self.assertEqual("Views", metric_items["marketplace-views"]["label"])
        self.assertEqual("9", metric_items["marketplace-hearts"]["valueText"])
        self.assertIn("not installs", metric_story["metricsCaveat"])
        self.assertNotIn("metrics", metric_story)
        self.assertNotIn("metricSources", metric_story)
        self.assertEqual(
            "https://plugins.omarchy.org/plugin.html?id=io.github.mtolhuys.disk-lens",
            metric_story["marketplaceUrl"],
        )

        updated = set_section_filter(
            "plugins",
            {
                "period": "all",
                "significance": "all",
                "unreadOnly": False,
                "imagesOnly": False,
                "types": ["plugin-released"],
            },
            self.environment,
        )
        self.assertEqual(["plugin-released"], updated["state"]["preferences"]["sectionFilters"]["plugins"]["types"])
        filtered = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        self.assertTrue(filtered["events"])
        self.assertTrue(all(event["type"] == "plugin-released" for event in filtered["events"]))
        self.assertEqual("No extra filters", projection_model("core", "[]", "", self.environment, now=CLOCK)["filterSummary"])

        unread_filter = copy.deepcopy(updated["state"]["preferences"]["sectionFilters"]["plugins"])
        unread_filter["unreadOnly"] = True
        set_section_filter("plugins", unread_filter, self.environment)
        plugins_before = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        read_id = plugins_before["events"][0]["id"]
        set_event_read_state(read_id, True, self.environment, now=CLOCK)
        unread = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        self.assertTrue(all(event["isUnread"] for event in unread["events"]))
        self.assertNotIn(read_id, {event["id"] for event in unread["events"]})

        profiled = set_section_profile(
            "plugins",
            {"name": "My Extensions"},
            self.environment,
        )
        self.assertEqual(
            {"name": "My Extensions"},
            profiled["state"]["preferences"]["sectionProfiles"]["plugins"],
        )
        self.assertEqual(
            "Core",
            profiled["state"]["preferences"]["sectionProfiles"]["core"]["name"],
        )

        with self.assertRaisesRegex(ValidationError, "limit"):
            projection_model("plugins", "[]", "", self.environment, now=CLOCK, limit=0)

    def test_installed_plugin_discovery_fails_closed_on_unexpected_shell_shapes(self) -> None:
        invalid_shapes: list[object] = [
            None,
            {},
            {"plugins": None},
            {"plugins": {}},
            "plugins",
        ]
        for payload in invalid_shapes:
            completed = mock.Mock(returncode=0, stdout=json.dumps(payload))
            with self.subTest(payload=payload), mock.patch(
                "radar.client.subprocess.run",
                return_value=completed,
            ):
                self.assertEqual([], installed_plugins()["pluginIds"])

        with mock.patch(
            "radar.client.subprocess.run",
            side_effect=TimeoutError("shell did not respond"),
        ):
            self.assertEqual([], installed_plugins()["pluginIds"])

        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps(
                {
                    "plugins": [
                        {"id": "z.plugin", "enabled": True},
                        {"id": "a.plugin", "enabled": True},
                        {"id": "ignored", "enabled": False},
                        {"id": "x" * 161, "enabled": True},
                    ]
                }
            ),
        )
        with mock.patch("radar.client.subprocess.run", return_value=completed):
            self.assertEqual(["a.plugin", "z.plugin"], installed_plugins()["pluginIds"])


if __name__ == "__main__":
    unittest.main()
