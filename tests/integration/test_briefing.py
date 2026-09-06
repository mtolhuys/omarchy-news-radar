from __future__ import annotations

import copy
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from radar.briefing import compose_briefing, feed_membership_digest
from radar.client import (
    complete_onboarding,
    ensure_briefing,
    indicator_model,
    mark_briefing_read,
    projection_model,
    set_event_read_state,
    set_preferences,
    start_from_today,
    toggle_saved_state,
)
from radar.constants import STATE_SCHEMA_VERSION
from radar.errors import ValidationError
from radar.io import atomic_write_json
from radar.model import event_sort_key
from radar.state import (
    EPOCH,
    default_state,
    event_is_read,
    load_state,
    save_feed,
    save_state,
    set_events_read,
    user_state_path,
)
from radar.validation import validate_state

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)
INSTALLED = '["io.github.mtolhuys.disk-lens"]'


class BriefingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.environment = {"HOME": str(root / "home"), "XDG_CACHE_HOME": str(root / "cache"), "XDG_STATE_HOME": str(root / "state")}
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text())
        save_feed(self.feed, self.environment, now=CLOCK)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def project(self, **kwargs: object) -> dict:
        return projection_model("front-page", INSTALLED, "", self.environment, now=CLOCK + timedelta(minutes=1), **kwargs)

    def begin(self) -> dict:
        ensure_briefing(INSTALLED, self.environment, now=CLOCK)
        return self.project()

    def newer_feed(self, *, same_plugin: bool = False) -> dict:
        newer = copy.deepcopy(self.feed)
        newer["generatedAt"] = "2026-08-31T14:01:00Z"
        newer["window"]["through"] = newer["generatedAt"]
        template = next(event for event in newer["events"] if event["type"] == ("plugin-released" if same_plugin else "plugin-added"))
        event = copy.deepcopy(template)
        event["id"] = "evt_eeeeeeeeeeeeeeeeeeeeeeee"
        # A late-discovered story may predate the onboarding clock. Identity,
        # not a timestamp baseline, must protect it from being silently read.
        event["occurredAt"] = "2026-08-30T12:00:00Z"
        event["discoveredAt"] = newer["generatedAt"]
        if not same_plugin:
            event["entity"]["id"] = "org.example.late-arrival"
        newer["events"].append(event)
        newer["events"].sort(key=event_sort_key)
        return newer

    def test_projection_and_indicator_never_initialize_or_mark_a_briefing(self) -> None:
        before = load_state(self.environment)[0]
        self.assertFalse(self.project()["briefing"]["initialized"])
        indicator_model(self.environment, now=CLOCK, installed_json=INSTALLED)
        self.assertEqual(before, load_state(self.environment)[0])
        initialized = self.begin()
        self.assertTrue(initialized["briefing"]["initialized"])
        self.assertEqual({}, initialized["state"]["readOverrides"])
        self.assertFalse(initialized["onboardingComplete"])

    def test_group_members_keep_sources_and_only_explicit_group_read_reads_them(self) -> None:
        projected = self.begin()
        group = next(event for event in projected["events"] if event.get("briefingReason") == "installed")
        self.assertEqual(2, group["briefingEventCount"])
        source_by_id = {event["id"]: event["source"] for event in self.feed["events"]}
        self.assertEqual("plugin-released", group["type"])
        for member in group["briefingEvents"]:
            self.assertEqual(source_by_id[member["id"]], member["source"])
        set_event_read_state(group["id"], True, self.environment, now=CLOCK)
        after = self.project()
        current = next(event for event in after["events"] if event["id"] == group["id"])
        self.assertFalse(current["isUnread"])
        self.assertEqual(1, current["briefingUnreadCount"])
        self.assertEqual(projected["briefing"]["id"], after["briefing"]["id"])
        result = mark_briefing_read(after["briefing"]["id"], self.environment, group_event_id=group["briefingGroupId"], now=CLOCK)
        self.assertEqual(1, result["markedRead"])
        for event in self.feed["events"]:
            self.assertEqual(event["id"] in {member["id"] for member in group["briefingEvents"]}, event_is_read(result["state"], event))

    def test_refresh_does_not_refill_or_extend_an_existing_group(self) -> None:
        before = self.begin()
        newer = self.newer_feed(same_plugin=True)
        save_feed(newer, self.environment, now=CLOCK + timedelta(minutes=1))
        ensured = ensure_briefing(INSTALLED, self.environment, now=CLOCK + timedelta(minutes=1))
        self.assertEqual(before["briefing"]["id"], ensured["briefing"]["id"])
        after = self.project()
        self.assertEqual([event["id"] for event in before["events"]], [event["id"] for event in after["events"]])
        marked = mark_briefing_read(before["briefing"]["id"], self.environment, now=CLOCK + timedelta(minutes=1))
        arrival = next(event for event in newer["events"] if event["id"] == "evt_eeeeeeeeeeeeeeeeeeeeeeee")
        self.assertFalse(event_is_read(marked["state"], arrival))
        completed = self.project()
        self.assertTrue(completed["briefing"]["complete"])
        self.assertTrue(completed["briefing"]["hasNewStories"])
        self.assertEqual(
            [event["id"] for event in before["events"]],
            [event["id"] for event in completed["events"]],
        )
        self.assertTrue(all(not event["isUnread"] for event in completed["events"]))
        self.assertTrue(any(not event_is_read(marked["state"], event) for event in newer["events"]))

    def test_stale_briefing_action_never_marks_a_new_selection(self) -> None:
        before = self.begin()
        mark_briefing_read(before["briefing"]["id"], self.environment, now=CLOCK)
        newer = self.newer_feed()
        save_feed(newer, self.environment, now=CLOCK + timedelta(minutes=1))
        ensure_briefing(INSTALLED, self.environment, now=CLOCK + timedelta(minutes=1), replace=True)
        state = load_state(self.environment)[0]
        result = mark_briefing_read(before["briefing"]["id"], self.environment, now=CLOCK + timedelta(minutes=1))
        self.assertEqual("stale-briefing", result["status"])
        self.assertEqual(state, result["state"])

    def test_new_briefing_advances_past_unfinished_groups_without_reading_them(self) -> None:
        before = self.begin()
        self.assertTrue(before["briefing"]["hasNewStories"])
        self.assertGreater(before["briefing"]["remaining"], 0)
        previous_ids = {
            event_id for group in before["state"]["briefing"]["groups"] for event_id in group["eventIds"]
        }
        result = ensure_briefing(INSTALLED, self.environment, now=CLOCK, replace=True)
        replacement_ids = {
            event_id for group in result["state"]["briefing"]["groups"] for event_id in group["eventIds"]
        }
        self.assertNotEqual(before["briefing"]["id"], result["briefing"]["id"])
        self.assertTrue(replacement_ids)
        self.assertTrue(previous_ids.isdisjoint(replacement_ids))
        self.assertEqual(before["state"]["readOverrides"], result["state"]["readOverrides"])
        for event in self.feed["events"]:
            self.assertFalse(event_is_read(result["state"], event))

    def test_new_briefing_selects_new_occurrence_without_older_unfinished_group_members(self) -> None:
        before = self.begin()
        original_group = next(group for group in before["state"]["briefing"]["groups"] if group["reason"] == "installed")
        save_feed(self.newer_feed(same_plugin=True), self.environment, now=CLOCK + timedelta(minutes=1))
        self.assertTrue(self.project()["briefing"]["hasNewStories"])
        result = ensure_briefing(INSTALLED, self.environment, now=CLOCK + timedelta(minutes=1), replace=True)
        new_group = next(group for group in result["state"]["briefing"]["groups"] if group["reason"] == "installed")
        self.assertEqual(["evt_eeeeeeeeeeeeeeeeeeeeeeee"], new_group["eventIds"])
        self.assertTrue(set(original_group["eventIds"]).isdisjoint(new_group["eventIds"]))
        self.assertEqual(before["state"]["readOverrides"], result["state"]["readOverrides"])

    def test_expired_members_are_reported_without_false_completion(self) -> None:
        before = self.begin()
        newer = copy.deepcopy(self.feed)
        expired_id = before["events"][0]["id"]
        newer["events"] = [event for event in newer["events"] if event["id"] != expired_id]
        save_feed(newer, self.environment, now=CLOCK)
        marked = mark_briefing_read(before["briefing"]["id"], self.environment, now=CLOCK)
        after = self.project()
        self.assertEqual(1, after["briefing"]["expiredEvents"])
        self.assertEqual(0, after["briefing"]["remaining"])
        self.assertFalse(after["briefing"]["complete"])
        self.assertNotIn(expired_id, marked["state"]["readOverrides"])

    def test_start_today_preserves_preferences_saves_and_explicit_unread(self) -> None:
        self.begin()
        selected = self.feed["events"][0]
        toggle_saved_state(selected["id"], self.environment, now=CLOCK)
        set_preferences(bar_visible=False, environment=self.environment)
        state = load_state(self.environment)[0]
        state["readOverrides"][selected["id"]] = False
        save_state(state, self.environment)
        result = start_from_today(self.project()["feedDigest"], self.environment, now=CLOCK)
        self.assertEqual("ok", result["status"])
        self.assertEqual(state["preferences"], result["state"]["preferences"])
        self.assertEqual(state["saved"], result["state"]["saved"])
        self.assertFalse(result["state"]["readOverrides"][selected["id"]])
        self.assertEqual(EPOCH, result["state"]["readThrough"])
        self.assertTrue(result["state"]["onboardingComplete"])
        self.assertEqual([], result["state"]["briefing"]["groups"])
        self.assertEqual("onboarding-complete", start_from_today(self.project()["feedDigest"], self.environment, now=CLOCK)["status"])

    def test_start_today_rejects_changed_membership_but_not_publication_only_churn(self) -> None:
        before = self.begin()
        original_state = load_state(self.environment)[0]
        self.assertEqual(len(self.feed["events"]), before["feedEventCount"])
        newer = self.newer_feed()
        save_feed(newer, self.environment, now=CLOCK + timedelta(minutes=1))
        current = self.project()
        self.assertEqual(len(newer["events"]), current["feedEventCount"])
        self.assertEqual(feed_membership_digest(newer), current["feedDigest"])
        result = start_from_today(before["feedDigest"], self.environment, now=CLOCK + timedelta(minutes=1))
        self.assertEqual("stale-edition", result["status"])
        self.assertEqual(original_state, load_state(self.environment)[0])
        changed_clock = copy.deepcopy(self.feed)
        changed_clock["generatedAt"] = newer["generatedAt"]
        changed_clock["window"]["through"] = newer["generatedAt"]
        save_feed(changed_clock, self.environment, now=CLOCK + timedelta(minutes=1))
        result = start_from_today(before["feedDigest"], self.environment, now=CLOCK + timedelta(minutes=1))
        self.assertEqual("ok", result["status"])
        save_feed(newer, self.environment, now=CLOCK + timedelta(minutes=1))
        arrival = next(event for event in newer["events"] if event["id"] == "evt_eeeeeeeeeeeeeeeeeeeeeeee")
        self.assertFalse(event_is_read(result["state"], arrival))

    def test_browse_choice_never_changes_reading_and_empty_brief_never_refills(self) -> None:
        before = self.begin()["state"]
        result = complete_onboarding(self.environment)
        self.assertEqual(before["readOverrides"], result["state"]["readOverrides"])
        self.assertEqual(before["saved"], result["state"]["saved"])
        mark_briefing_read(self.project()["briefing"]["id"], self.environment, now=CLOCK)
        # Read every remaining event, then explicitly take an empty briefing.
        for event in self.feed["events"]:
            set_event_read_state(event["id"], True, self.environment, now=CLOCK)
        empty = ensure_briefing(INSTALLED, self.environment, now=CLOCK, replace=True)
        self.assertTrue(empty["briefing"]["complete"])
        self.assertEqual(0, empty["briefing"]["total"])
        save_feed(self.newer_feed(), self.environment, now=CLOCK + timedelta(minutes=1))
        self.assertEqual(empty["briefing"]["id"], ensure_briefing(INSTALLED, self.environment, now=CLOCK + timedelta(minutes=1))["briefing"]["id"])
        self.assertEqual([], self.project()["events"])
        self.assertTrue(self.project()["briefing"]["hasNewStories"])

    def test_v11_migration_keeps_every_reading_fact_and_skips_first_use(self) -> None:
        state = default_state()
        state.pop("briefing")
        state.pop("onboardingComplete")
        state.pop("relevance")
        state["schemaVersion"] = 11
        state["readThrough"] = "2026-08-01T00:00:00Z"
        state["readOverrides"] = {self.feed["events"][0]["id"]: False}
        state["preferences"]["imagesVisible"] = False
        atomic_write_json(user_state_path(self.environment), state)
        migrated, quarantined = load_state(self.environment)
        self.assertIsNone(quarantined)
        self.assertEqual(STATE_SCHEMA_VERSION, migrated["schemaVersion"])
        self.assertTrue(migrated["onboardingComplete"])
        for key in ("readThrough", "readOverrides", "saved", "preferences"):
            self.assertEqual(state[key], migrated[key])

    def test_briefing_validation_rejects_duplicate_members_bounds_and_unknown_reason(self) -> None:
        snapshot = self.begin()["state"]
        duplicate = copy.deepcopy(snapshot)
        duplicate["briefing"]["groups"][0]["eventIds"].append(duplicate["briefing"]["groups"][0]["eventIds"][0])
        unknown = copy.deepcopy(snapshot)
        unknown["briefing"]["groups"][0]["reason"] = "best-plugin"
        oversized = copy.deepcopy(snapshot)
        oversized["briefing"]["groups"] *= 6
        for invalid in (duplicate, unknown, oversized):
            with self.assertRaises(ValidationError):
                validate_state(invalid)
        with self.assertRaises(ValidationError):
            start_from_today("not-a-digest", self.environment, now=CLOCK)

    def test_feed_replacement_waits_for_exact_first_use_transition(self) -> None:
        digest = feed_membership_digest(self.feed)
        mutation_started = threading.Event()
        release_mutation = threading.Event()
        writer_started = threading.Event()
        writer_finished = threading.Event()
        errors: list[BaseException] = []

        def controlled_read(*args: object, **kwargs: object) -> dict:
            mutation_started.set()
            if not release_mutation.wait(5):
                raise AssertionError("test did not release mutation")
            return set_events_read(*args, **kwargs)

        def start() -> None:
            try:
                start_from_today(digest, self.environment, now=CLOCK)
            except BaseException as exc:
                errors.append(exc)

        def write() -> None:
            try:
                writer_started.set()
                save_feed(self.newer_feed(), self.environment, now=CLOCK + timedelta(minutes=1))
                writer_finished.set()
            except BaseException as exc:
                errors.append(exc)

        with mock.patch("radar.client_briefing.set_events_read", side_effect=controlled_read):
            reader = threading.Thread(target=start)
            writer = threading.Thread(target=write)
            reader.start()
            self.assertTrue(mutation_started.wait(5))
            writer.start()
            self.assertTrue(writer_started.wait(5))
            self.assertFalse(writer_finished.wait(0.05))
            release_mutation.set()
            reader.join(5)
            writer.join(5)
        self.assertFalse(reader.is_alive())
        self.assertFalse(writer.is_alive())
        self.assertEqual([], errors)
        state = load_state(self.environment)[0]
        arrival = next(event for event in self.newer_feed()["events"] if event["id"] == "evt_eeeeeeeeeeeeeeeeeeeeeeee")
        self.assertFalse(event_is_read(state, arrival))

    def test_selection_is_bounded_deterministic_and_independent_of_metrics(self) -> None:
        events = copy.deepcopy(self.feed["events"])
        template = next(event for event in events if event["type"] == "plugin-added")
        for index in range(20):
            event = copy.deepcopy(template)
            event["id"] = f"evt_{index:024x}"
            event["entity"]["id"] = f"org.example.discovery-{index}"
            events.append(event)
        expected = compose_briefing(events, generated_at=self.feed["generatedAt"], installed_plugin_ids=json.loads(INSTALLED))
        for event in events:
            event["metrics"] = [{"id": "repository-stars", "value": 9000000}]
        actual = compose_briefing(reversed(events), generated_at=self.feed["generatedAt"], installed_plugin_ids=json.loads(INSTALLED))
        self.assertEqual(expected, actual)
        self.assertLessEqual(len(actual["groups"]), 5)
        self.assertEqual(1, sum(group["reason"] == "discovery" for group in actual["groups"]))
        all_ids = [event_id for group in actual["groups"] for event_id in group["eventIds"]]
        self.assertEqual(len(all_ids), len(set(all_ids)))


if __name__ == "__main__":
    unittest.main()
