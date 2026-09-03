from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from radar.client import (
    indicator_model,
    installed_plugins,
    mark_section_read_state,
    projection_model,
    read_model,
    refresh,
    refresh_if_due,
    set_event_read_state,
    set_preferences,
    set_section_filter,
    toggle_saved_state,
)
from radar.constants import CLIENT_SECTIONS
from radar.errors import ValidationError
from radar.io import atomic_write_json
from radar.state import feed_path, load_feed, update_check_path

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

    def visible_unread_ids(self, installed_json: str = "[]") -> set[str]:
        visible: set[str] = set()
        for section in CLIENT_SECTIONS:
            projection = projection_model(
                section,
                installed_json,
                "",
                self.environment,
                now=CLOCK,
                limit=500,
            )
            visible.update(
                event["id"] for event in projection["events"] if event["isUnread"]
            )
        return visible

    def assert_indicator_matches_visible_unread_union(
        self, installed_json: str = "[]"
    ) -> set[str]:
        visible = self.visible_unread_ids(installed_json)
        indicator = indicator_model(
            self.environment,
            now=CLOCK,
            installed_json=installed_json,
        )
        self.assertEqual(len(visible), indicator["unread"])
        return visible

    def test_first_use_refresh_cached_read_and_private_projection(self) -> None:
        self.assertEqual("first-use", read_model(self.environment, now=CLOCK)["status"])
        result = refresh(self.environment, now=CLOCK)
        self.assertEqual("updated", result["status"])
        self.assertEqual(len(self.feed["events"]), result["newStories"])
        self.assertTrue(result["editionChanged"])
        unchanged = refresh(self.environment, now=CLOCK)
        self.assertEqual("no-change", unchanged["status"])
        self.assertEqual(0, unchanged["newStories"])
        self.assertFalse(unchanged["editionChanged"])
        self.assertIn("No newer edition", unchanged["message"])
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

    def test_background_update_cadence_adopts_unread_without_opening_panel(self) -> None:
        initial = refresh(self.environment, now=CLOCK)
        initial_unread = indicator_model(self.environment, now=CLOCK)["unread"]
        stamp = json.loads(update_check_path(self.environment).read_text(encoding="utf-8"))
        self.assertEqual({"schemaVersion": 1, "checkedAt": "2026-08-31T14:00:00Z", "outcome": "success"}, stamp)
        self.assertEqual(0o600, update_check_path(self.environment).stat().st_mode & 0o777)

        newer = copy.deepcopy(self.feed)
        newer["generatedAt"] = "2026-08-31T14:15:00Z"
        newer["window"]["through"] = "2026-08-31T14:15:00Z"
        event = copy.deepcopy(newer["events"][0])
        event["id"] = "evt_eeeeeeeeeeeeeeeeeeeeeeee"
        event["occurredAt"] = "2026-08-31T14:15:00Z"
        event["discoveredAt"] = "2026-08-31T14:15:00Z"
        newer["events"].insert(0, event)
        atomic_write_json(self.fixture, newer)

        not_due = refresh_if_due(900, self.environment, now=CLOCK + timedelta(minutes=14, seconds=59))
        self.assertEqual("not-due", not_due["status"])
        self.assertEqual(1, not_due["nextCheckInSeconds"])
        adopted = refresh_if_due(900, self.environment, now=CLOCK + timedelta(minutes=15))
        self.assertEqual("updated", adopted["status"])
        self.assertEqual(1, adopted["newStories"])
        self.assertEqual(900, adopted["nextCheckInSeconds"])
        self.assertEqual(initial_unread + 1, indicator_model(self.environment, now=CLOCK + timedelta(minutes=15))["unread"])

        self.fixture.unlink()
        failed = refresh_if_due(900, self.environment, now=CLOCK + timedelta(minutes=30))
        self.assertEqual("offline", failed["status"])
        self.assertEqual(300, failed["nextCheckInSeconds"])
        retry_wait = refresh_if_due(900, self.environment, now=CLOCK + timedelta(minutes=34, seconds=59))
        self.assertEqual("not-due", retry_wait["status"])
        self.assertEqual(1, retry_wait["nextCheckInSeconds"])
        atomic_write_json(self.fixture, newer)
        retried = refresh_if_due(900, self.environment, now=CLOCK + timedelta(minutes=35))
        self.assertEqual("no-change", retried["status"])
        self.assertEqual(900, retried["nextCheckInSeconds"])
        self.assertTrue(initial["editionChanged"])

    def test_stale_publication_is_not_reported_current_when_sources_are_old_successes(self) -> None:
        result = refresh(
            self.environment,
            now=CLOCK + timedelta(minutes=90, seconds=1),
        )
        self.assertEqual("stale-publication", result["status"])
        self.assertTrue(result["timing"]["publisherStale"])
        self.assertTrue(all(source["status"] == "current" for source in result["feed"]["sources"]))
        self.assertIn("Publisher lag", result["message"])

    def test_newer_edition_reports_only_newly_adopted_story_ids(self) -> None:
        first = refresh(self.environment, now=CLOCK)
        self.assertEqual("updated", first["status"])
        newer = copy.deepcopy(self.feed)
        newer["generatedAt"] = "2026-08-31T14:01:00Z"
        newer["window"]["through"] = "2026-08-31T14:01:00Z"
        event = copy.deepcopy(newer["events"][0])
        event["id"] = "evt_ffffffffffffffffffffffff"
        event["occurredAt"] = "2026-08-31T14:01:00Z"
        event["discoveredAt"] = "2026-08-31T14:01:00Z"
        newer["events"].insert(0, event)
        atomic_write_json(self.fixture, newer)

        result = refresh(self.environment, now=CLOCK + timedelta(minutes=1))
        self.assertEqual("updated", result["status"])
        self.assertEqual(1, result["newStories"])
        self.assertIn("1 new story", result["message"])

    def test_invalid_candidate_preserves_last_known_good(self) -> None:
        self.assertEqual("updated", refresh(self.environment, now=CLOCK)["status"])
        good = feed_path(self.environment).read_bytes()
        invalid = copy.deepcopy(self.feed)
        invalid["schemaVersion"] = 99
        atomic_write_json(self.fixture, invalid)
        result = refresh(self.environment, now=CLOCK)
        self.assertEqual("invalid-feed", result["status"])
        self.assertTrue(result["cachePreserved"])
        self.assertEqual(good, feed_path(self.environment).read_bytes())

    def test_truncated_and_oversized_candidates_do_not_replace_cache(self) -> None:
        self.assertEqual("updated", refresh(self.environment, now=CLOCK)["status"])
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

    def test_indicator_counts_only_unread_stories_reachable_through_current_filters(self) -> None:
        refresh(self.environment, now=CLOCK)
        image_filter = {
            "period": "all",
            "significance": "all",
            "unreadOnly": False,
            "imagesOnly": True,
            "types": [],
        }
        for section in ("front-page", "core", "plugins"):
            set_section_filter(section, image_filter, self.environment)

        projected = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        self.assertEqual(0, projected["totalEvents"])
        self.assertEqual(0, projected["unreadCounts"]["plugins"])
        self.assertEqual(set(), self.assert_indicator_matches_visible_unread_union())

        installed_json = '["io.github.mtolhuys.disk-lens"]'
        for_you = projection_model("for-you", installed_json, "", self.environment, now=CLOCK)
        self.assertGreater(for_you["unreadCounts"]["for-you"], 0)
        visible_for_you = self.assert_indicator_matches_visible_unread_union(installed_json)
        self.assertEqual(
            {event["id"] for event in for_you["events"] if event["isUnread"]},
            visible_for_you,
        )

        toggle_saved_state(for_you["events"][0]["id"], self.environment, now=CLOCK)
        self.assertEqual(
            visible_for_you,
            self.assert_indicator_matches_visible_unread_union(installed_json),
        )

        hidden_plugin_id = "evt_53642b4d3e0e59c943494606"
        toggle_saved_state(hidden_plugin_id, self.environment, now=CLOCK)
        visible_with_saved = self.assert_indicator_matches_visible_unread_union(installed_json)
        self.assertEqual(visible_for_you | {hidden_plugin_id}, visible_with_saved)

        set_section_filter("saved", image_filter, self.environment)
        self.assertEqual(
            visible_for_you,
            self.assert_indicator_matches_visible_unread_union(installed_json),
        )

        set_section_filter(
            "plugins",
            {
                "period": "all",
                "significance": "all",
                "unreadOnly": False,
                "imagesOnly": False,
                "types": [],
            },
            self.environment,
        )
        revealed = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        self.assertGreater(revealed["unreadCounts"]["plugins"], 0)
        visible_revealed = self.assert_indicator_matches_visible_unread_union()
        self.assertEqual(
            {event["id"] for event in revealed["events"] if event["isUnread"]},
            visible_revealed,
        )

    def test_stale_read_mutation_after_refresh_is_a_benign_no_op(self) -> None:
        refresh(self.environment, now=CLOCK)
        result = set_event_read_state(
            "evt_ffffffffffffffffffffffff",
            True,
            self.environment,
            now=CLOCK,
        )
        self.assertEqual("stale-event", result["status"])
        self.assertEqual({}, result["state"]["readOverrides"])
        self.assertIn("left unchanged", result["message"])

    def test_mark_section_read_is_atomic_bounded_and_follows_section_filters(self) -> None:
        refresh(self.environment, now=CLOCK)
        first_page = projection_model(
            "plugins", "[]", "", self.environment, now=CLOCK, limit=1
        )
        self.assertTrue(first_page["hasMore"])
        plugin_unread = first_page["unreadCounts"]["plugins"]
        core_unread = first_page["unreadCounts"]["core"]
        searched = projection_model(
            "plugins", "[]", "Workspace Notes", self.environment, now=CLOCK, limit=1
        )
        self.assertEqual(1, searched["totalEvents"])

        marked = mark_section_read_state("plugins", "[]", self.environment, now=CLOCK)
        self.assertEqual(plugin_unread, marked["markedRead"])
        after = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        self.assertEqual(0, after["unreadCounts"]["plugins"])
        self.assertTrue(all(not event["isUnread"] for event in after["events"]))
        self.assertEqual(
            core_unread,
            projection_model("core", "[]", "", self.environment, now=CLOCK)["unreadCounts"]["core"],
        )

        for event in after["events"]:
            set_event_read_state(event["id"], False, self.environment, now=CLOCK)
        filtered_value = {
            "period": "all",
            "significance": "all",
            "unreadOnly": False,
            "imagesOnly": False,
            "types": ["plugin-released"],
        }
        set_section_filter("plugins", filtered_value, self.environment)
        filtered = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        marked = mark_section_read_state("plugins", "[]", self.environment, now=CLOCK)
        self.assertEqual(filtered["unreadCounts"]["plugins"], marked["markedRead"])
        self.assertEqual(0, projection_model("plugins", "[]", "", self.environment, now=CLOCK)["unreadCounts"]["plugins"])

        set_section_filter(
            "plugins",
            {**filtered_value, "types": []},
            self.environment,
        )
        unfiltered = projection_model("plugins", "[]", "", self.environment, now=CLOCK)
        self.assertGreater(unfiltered["unreadCounts"]["plugins"], 0)
        self.assertTrue(any(event["type"] != "plugin-released" and event["isUnread"] for event in unfiltered["events"]))

        with self.assertRaisesRegex(ValidationError, "unknown projection section"):
            mark_section_read_state("community", "[]", self.environment, now=CLOCK)

    def test_projection_paginates_decorates_metrics_and_applies_local_section_filter(self) -> None:
        refresh(self.environment, now=CLOCK)
        first = projection_model("front-page", "[]", "", self.environment, now=CLOCK, limit=1)
        self.assertEqual(1, len(first["events"]))
        self.assertGreater(first["totalEvents"], 1)
        self.assertTrue(first["hasMore"])
        self.assertEqual("No extra filters", first["filterSummary"])
        self.assertNotIn("sectionRule", first)
        self.assertIn("Official Omarchy releases", first["sectionSources"])
        lead = first["events"][0]
        self.assertIn("listSummary", lead)
        self.assertLessEqual(len(lead["listSummary"]), 220)
        self.assertGreaterEqual(len(lead["summary"]), len(lead["listSummary"]))

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

        retained = projection_model(
            "plugins",
            "[]",
            "",
            self.environment,
            now=CLOCK,
            retained_read_ids_json=json.dumps([read_id]),
        )
        retained_story = next(event for event in retained["events"] if event["id"] == read_id)
        self.assertFalse(retained_story["isUnread"])
        self.assertEqual(1, retained["retainedReadCount"])
        self.assertEqual(unread["unreadCounts"], retained["unreadCounts"])

        with self.assertRaisesRegex(ValidationError, "retained read ID"):
            projection_model(
                "plugins",
                "[]",
                "",
                self.environment,
                now=CLOCK,
                retained_read_ids_json='["not-an-event"]',
            )

        self.assertNotIn("sectionProfiles", updated["state"]["preferences"])

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
