"""Discovery must follow source events, including quiet and unsafe-cache paths."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from radar.discovery import automatic_discoveries, discovery_edition, CACHE_NAME
from radar.constants import FEED_MAX_BYTES
from radar.state import cache_root, default_state, purge

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, tzinfo=timezone.utc)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = {"HOME": self.temp.name, "XDG_CACHE_HOME": self.temp.name + "/cache", "XDG_STATE_HOME": self.temp.name + "/state"}
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text())
        self.projects = json.loads((ROOT / "tests/fixtures/insights-valid.json").read_text())["projects"]
        self.state = default_state()

    def home(self, feed=None, projects=None):
        return automatic_discoveries(feed or self.feed, feed or self.feed, self.state, projects or [])

    def test_source_text_dates_and_links_are_preserved_without_optional_insights(self):
        home = self.home()
        cards = home["recentAdditions"] + home["recentChanges"]
        self.assertEqual(3, len(cards))  # One core release per project, not both versions.
        events = {event["id"]: event for event in self.feed["events"]}
        for card in cards:
            event = events[card["eventId"]]
            for field in ("title", "summary", "occurredAt", "discoveredAt", "source"):
                self.assertEqual(event[field], card[field])
            self.assertEqual(event["summary"], card["body"])
            self.assertIn(event["occurredAt"][:10], card["comparisonLabel"])
            self.assertIn("automatically", card["selectionReason"])
            self.assertEqual([], card["projects"])
        self.assertEqual([], home["featuredCollections"])

    def test_live_addition_appears_and_reading_or_metrics_do_not_change_selection(self):
        before = self.home()
        event = copy.deepcopy(next(e for e in self.feed["events"] if e["type"] == "plugin-added"))
        event.update(id="evt_000000000000000000000001", occurredAt="2026-08-31T13:00:00Z")
        event["entity"]["id"] = "org.example.new"
        self.feed["events"].append(event)
        after = self.home()
        self.assertNotEqual(before["recentAdditions"], after["recentAdditions"])
        self.assertEqual(event["id"], after["recentAdditions"][0]["eventId"])
        self.state["readIds"] = [e["id"] for e in self.feed["events"]]
        for item in self.feed["events"]:
            item.pop("metrics", None)
        self.assertEqual(after, self.home())

    def test_latest_distinct_projects_are_bounded_and_late_discovery_is_not_redated(self):
        template = next(e for e in self.feed["events"] if e["type"] == "plugin-added")
        for number in range(15):
            event = copy.deepcopy(template)
            event.update(id=f"evt_{number:024x}", occurredAt=f"2026-08-{number + 10:02d}T00:00:00Z")
            event["entity"]["id"] = f"org.example.project{number}"
            self.feed["events"].append(event)
        cards = self.home()["recentAdditions"]
        self.assertEqual(6, len(cards))
        self.assertEqual(template["id"], cards[0]["eventId"])
        self.assertEqual("2026-08-24T00:00:00Z", cards[1]["occurredAt"])

    def test_quiet_and_offline_keep_dated_public_facts_without_copying_read_state(self):
        edition, retained, warning = discovery_edition(self.feed, self.env, now=CLOCK)
        self.assertFalse(retained)
        self.assertFalse(warning)
        empty = {**self.feed, "events": []}
        for feed in (empty, None):
            previous, retained, warning = discovery_edition(feed, self.env, now=CLOCK)
            self.assertEqual(edition, previous)
            self.assertTrue(retained)
            home = automatic_discoveries(previous, feed, self.state, [], retained=retained)
            self.assertIn("last available", home["discoveryStatus"])
            self.assertEqual("2026-08-31T14:00:00Z", home["activityDate"])
        self.assertEqual(set(self.feed), set(json.loads((cache_root(self.env) / CACHE_NAME).read_text())))
        self.assertIn(CACHE_NAME, purge(self.env))

    def test_retained_cards_respect_current_search_mutes_hidden_sources_and_retirement(self):
        edition, _, _ = discovery_edition(self.feed, self.env, now=CLOCK)
        self.state["relevance"]["mutedSources"] = ["marketplace"]
        home = automatic_discoveries(edition, None, self.state, [], retained=True)
        self.assertEqual([], home["recentAdditions"])
        self.assertEqual(1, len(home["recentChanges"]))
        self.state["preferences"]["sectionVisibility"]["core"] = False
        self.assertEqual([], automatic_discoveries(edition, None, self.state, [])["recentChanges"])
        self.state = default_state()
        self.assertEqual([], automatic_discoveries(edition, None, self.state, [], query="nonexistent")["recentAdditions"])
        added = next(e for e in self.feed["events"] if e["type"] == "plugin-added")
        current = {**self.feed, "events": [{**added, "type": "plugin-retired"}]}
        self.assertEqual([], automatic_discoveries(edition, current, self.state, [])["recentAdditions"])

    def test_release_notes_require_unambiguous_version_and_repository_match(self):
        def release_card():
            return next(c for c in self.home(projects=self.projects)["recentChanges"] if c["comparisonLabel"].startswith("Version update"))
        self.assertEqual("0.4.1", release_card()["releases"][0]["version"])
        self.projects[0]["releases"].append(copy.deepcopy(self.projects[0]["releases"][0]))
        self.assertEqual([], release_card()["releases"])
        self.projects[0]["source"]["url"] = "https://github.com/new-owner/other"
        self.assertEqual([], release_card()["projects"])

    def test_bad_cache_never_becomes_content_and_write_failure_keeps_current_feed(self):
        path = cache_root(self.env) / CACHE_NAME
        path.parent.mkdir(parents=True)
        for data in ("{", "x" * (FEED_MAX_BYTES + 1), '{"schemaVersion":900}'):
            path.write_text(data)
            edition, retained, warning = discovery_edition(None, self.env, now=CLOCK)
            self.assertIsNone(edition)
            self.assertFalse(retained)
            self.assertTrue(warning)
        path.unlink()
        target = Path(self.temp.name) / "target"
        target.write_text("untouched")
        path.symlink_to(target)
        edition, retained, warning = discovery_edition(self.feed, self.env, now=CLOCK)
        self.assertTrue(edition["events"])
        self.assertTrue(warning)
        self.assertEqual("untouched", target.read_text())
        path.unlink()
        with patch("radar.discovery.atomic_write_json", side_effect=OSError("full disk")):
            edition, _, warning = discovery_edition(self.feed, self.env, now=CLOCK)
        self.assertTrue(edition["events"])
        self.assertIn("could not be retained", warning)

    def test_no_history_has_an_honest_empty_state(self):
        edition, retained, warning = discovery_edition(None, self.env, now=CLOCK)
        home = automatic_discoveries(edition, None, self.state, [], retained=retained, warning=warning)
        self.assertEqual([], home["recentAdditions"])
        self.assertEqual([], home["recentChanges"])
        self.assertIn("No matching", home["discoveryStatus"])
