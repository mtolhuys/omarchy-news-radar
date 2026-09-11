"""Saved bookmarks must survive feed retention (issue #15)."""

from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.client_projection import _filtered_section_events
from radar.model import event_from_saved_record, include_persisted_saves, project_section
from radar.state import default_state, saved_record, toggle_saved
from radar.validation import validate_event

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)


class SavedPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))
        self.live = self.feed["events"][0]
        self.dropped = self.feed["events"][1]
        # Publisher no longer carries the second event.
        self.current_feed = copy.deepcopy(self.feed)
        self.current_feed["events"] = [copy.deepcopy(self.live)]

    def test_event_from_saved_record_is_a_valid_degraded_event(self) -> None:
        record = saved_record(self.dropped, CLOCK)
        event = event_from_saved_record(self.dropped["id"], record)
        self.assertTrue(event["isArchivedSave"])
        self.assertEqual(event["id"], self.dropped["id"])
        self.assertEqual(event["title"], self.dropped["title"])
        self.assertEqual(event["source"]["url"], self.dropped["source"]["url"])
        self.assertIn("local saved copy", event["summary"].lower())
        # Must satisfy the same shape the reader already consumes.
        validate_event({k: v for k, v in event.items() if k != "isArchivedSave"})

    def test_include_persisted_saves_keeps_live_and_restores_missing(self) -> None:
        state, _ = toggle_saved(default_state(), self.live, now=CLOCK)
        state, _ = toggle_saved(state, self.dropped, now=CLOCK)
        live_only = project_section(
            self.current_feed, "saved", saved_ids=set(state["saved"])
        )
        self.assertEqual([self.live["id"]], [event["id"] for event in live_only])

        merged = include_persisted_saves(live_only, state["saved"])
        ids = {event["id"] for event in merged}
        self.assertEqual(ids, set(state["saved"]))
        archived = next(event for event in merged if event["id"] == self.dropped["id"])
        self.assertTrue(archived["isArchivedSave"])
        live = next(event for event in merged if event["id"] == self.live["id"])
        self.assertNotIn("isArchivedSave", live)

    def test_saved_section_projection_count_includes_feed_absent_bookmarks(self) -> None:
        state, _ = toggle_saved(default_state(), self.live, now=CLOCK)
        state, _ = toggle_saved(state, self.dropped, now=CLOCK)
        events = _filtered_section_events(
            self.current_feed,
            state,
            "saved",
            installed_plugin_ids=[],
            now=CLOCK,
            respect_mutes=False,
        )
        self.assertEqual(2, len(events))
        self.assertEqual(set(state["saved"]), {event["id"] for event in events})


if __name__ == "__main__":
    unittest.main()
