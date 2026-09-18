"""Saved bookmarks must survive feed retention (issue #15)."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.client import (mark_section_read_state, projection_model,
                          set_event_read_state, toggle_saved_state)
from radar.client_projection import _filtered_section_events
from radar.errors import ValidationError
from radar.model import event_from_saved_record, include_persisted_saves, project_section
from radar.state import (default_state, load_state, save_feed, saved_record,
                         toggle_saved)
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

    def test_feed_absent_saved_story_can_be_read_bulk_read_and_unsaved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {
                "HOME": str(Path(directory) / "home"),
                "XDG_CACHE_HOME": str(Path(directory) / "cache"),
                "XDG_STATE_HOME": str(Path(directory) / "state"),
            }
            save_feed(self.feed, environment, now=CLOCK)
            self.assertTrue(
                toggle_saved_state(self.dropped["id"], environment, now=CLOCK)["saved"]
            )
            save_feed(self.current_feed, environment, now=CLOCK)

            projected = projection_model("saved", "[]", "", environment, now=CLOCK)
            self.assertEqual([self.dropped["id"]], [item["id"] for item in projected["events"]])
            self.assertTrue(projected["events"][0]["isArchivedSave"])
            self.assertTrue(projected["events"][0]["isUnread"])

            marked = set_event_read_state(self.dropped["id"], True, environment, now=CLOCK)
            self.assertEqual("ok", marked["status"])
            self.assertTrue(marked["read"])
            self.assertFalse(
                projection_model("saved", "[]", "", environment, now=CLOCK)["events"][0]["isUnread"]
            )

            set_event_read_state(self.dropped["id"], False, environment, now=CLOCK)
            bulk = mark_section_read_state("saved", "[]", environment, now=CLOCK)
            self.assertEqual(1, bulk["markedRead"])
            self.assertFalse(
                projection_model("saved", "[]", "", environment, now=CLOCK)["events"][0]["isUnread"]
            )

            removed = toggle_saved_state(self.dropped["id"], environment, now=CLOCK)
            self.assertFalse(removed["saved"])
            self.assertEqual(
                [], projection_model("saved", "[]", "", environment, now=CLOCK)["events"]
            )
            state, _ = load_state(environment)
            self.assertNotIn(self.dropped["id"], state["saved"])
            self.assertNotIn(self.dropped["id"], state["readOverrides"])

    def test_unknown_feed_absent_story_still_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {
                "HOME": str(Path(directory) / "home"),
                "XDG_CACHE_HOME": str(Path(directory) / "cache"),
                "XDG_STATE_HOME": str(Path(directory) / "state"),
            }
            save_feed(self.current_feed, environment, now=CLOCK)
            result = set_event_read_state(self.dropped["id"], True, environment, now=CLOCK)
            self.assertEqual("stale-event", result["status"])
            with self.assertRaisesRegex(ValidationError, "validated cache or saved items"):
                toggle_saved_state(self.dropped["id"], environment, now=CLOCK)


if __name__ == "__main__":
    unittest.main()
