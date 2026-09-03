from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from radar.constants import STATE_SCHEMA_VERSION, V9_CLIENT_SECTIONS
from radar.filters import default_section_filter
from radar.errors import StorageError, ValidationError
from radar.io import atomic_write_json
from radar.local_collection import local_source_snapshot_path
from radar.state import (
    LEGACY_CLIENT_SECTIONS,
    RefreshLock,
    StateLock,
    default_state,
    event_is_read,
    feed_path,
    load_feed,
    load_state,
    load_update_check,
    purge,
    save_feed,
    save_state,
    save_update_check,
    set_event_read,
    set_events_read,
    toggle_saved,
    update_check_path,
    update_preferences,
    update_section_filter,
    user_state_path,
)

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)
LEGACY_PROFILES = {
    "front-page": {"name": "Front Page"},
    "for-you": {"name": "For You"},
    "core": {"name": "Core"},
    "plugins": {"name": "Plugins"},
    "saved": {"name": "Saved"},
}


def v9_filters():
    return {section: default_section_filter() for section in V9_CLIENT_SECTIONS}


def legacy_filters():
    return {section: default_section_filter() for section in LEGACY_CLIENT_SECTIONS}


class StateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.environment = {
            "HOME": str(root / "home"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
        }
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_atomic_private_roundtrip_and_purge(self) -> None:
        save_feed(self.feed, self.environment, now=CLOCK)
        save_update_check("success", self.environment, now=CLOCK)
        save_state(default_state(), self.environment)
        atomic_write_json(
            local_source_snapshot_path(self.environment),
            json.loads(
                (ROOT / "tests/fixtures/source-snapshot-baseline.json").read_text(
                    encoding="utf-8"
                )
            ),
        )
        self.assertEqual(self.feed, load_feed(self.environment, now=CLOCK))
        self.assertEqual(0o600, feed_path(self.environment).stat().st_mode & 0o777)
        self.assertEqual(
            [
                "feed.json",
                "local-source-snapshot.json",
                "state.json",
                "update-check.json",
            ],
            purge(self.environment),
        )
        self.assertFalse(update_check_path(self.environment).exists())

    def test_update_check_metadata_is_bounded_private_and_fail_open(self) -> None:
        saved = save_update_check("failed", self.environment, now=CLOCK)
        self.assertEqual(
            {
                "schemaVersion": 1,
                "checkedAt": "2026-08-31T14:00:00Z",
                "outcome": "failed",
            },
            saved,
        )
        path = update_check_path(self.environment)
        self.assertEqual(0o600, path.stat().st_mode & 0o777)
        self.assertEqual(saved, load_update_check(self.environment, now=CLOCK))

        for malformed in (
            {
                "schemaVersion": True,
                "checkedAt": saved["checkedAt"],
                "outcome": "success",
            },
            {"schemaVersion": 1, "checkedAt": saved["checkedAt"], "outcome": []},
            {
                "schemaVersion": 1,
                "checkedAt": "2026-08-31T14:05:01Z",
                "outcome": "success",
            },
        ):
            atomic_write_json(path, malformed)
            self.assertIsNone(load_update_check(self.environment, now=CLOCK))

        path.unlink()
        sentinel = path.with_name("sentinel.json")
        sentinel.write_text("sentinel", encoding="utf-8")
        path.symlink_to(sentinel)
        self.assertIsNone(load_update_check(self.environment, now=CLOCK))
        with self.assertRaisesRegex(StorageError, "symlinked"):
            save_update_check("success", self.environment, now=CLOCK)
        self.assertEqual("sentinel", sentinel.read_text(encoding="utf-8"))
        path.unlink()

        save_update_check("success", self.environment, now=CLOCK + timedelta(minutes=5))
        self.assertIsNotNone(load_update_check(self.environment, now=CLOCK))

        with self.assertRaisesRegex(ValidationError, "outcome"):
            save_update_check("unknown", self.environment, now=CLOCK)

    def test_corrupt_state_is_quarantined_without_touching_feed(self) -> None:
        save_feed(self.feed, self.environment, now=CLOCK)
        path = user_state_path(self.environment)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{broken", encoding="utf-8")
        state, quarantine = load_state(self.environment)
        self.assertEqual(default_state(), state)
        self.assertIsNotNone(quarantine)
        self.assertIsNotNone(load_feed(self.environment, now=CLOCK))
        self.assertEqual(sorted(["feed.json", "state.json", str(quarantine)]), purge(self.environment))

    def test_per_event_read_overrides_are_explicit_bounded_and_save_is_independent(self) -> None:
        event = self.feed["events"][0]
        event_ids = {item["id"] for item in self.feed["events"]}
        state = default_state()
        self.assertFalse(event_is_read(state, event))
        with self.assertRaisesRegex(ValidationError, "boolean"):
            set_event_read(state, event, 1, current_event_ids=event_ids)  # type: ignore[arg-type]
        state = set_event_read(state, event, True, current_event_ids=event_ids)
        self.assertTrue(event_is_read(state, event))
        self.assertEqual({event["id"]: True}, state["readOverrides"])

        state = set_event_read(state, event, False, current_event_ids=event_ids)
        self.assertFalse(event_is_read(state, event))
        self.assertEqual({}, state["readOverrides"])

        state["readThrough"] = "2026-08-31T14:00:00Z"
        self.assertTrue(event_is_read(state, event))
        state = set_event_read(state, event, False, current_event_ids=event_ids)
        self.assertFalse(event_is_read(state, event))
        self.assertEqual({event["id"]: False}, state["readOverrides"])

        state["readOverrides"]["evt_ffffffffffffffffffffffff"] = True
        state = set_event_read(state, event, True, current_event_ids=event_ids)
        self.assertEqual({}, state["readOverrides"])

        updated, saved = toggle_saved(state, self.feed["events"][0], now=CLOCK)
        self.assertTrue(saved)
        self.assertEqual(state["readOverrides"], updated["readOverrides"])
        updated, saved = toggle_saved(updated, self.feed["events"][0], now=CLOCK)
        self.assertFalse(saved)

    def test_read_batches_are_bounded_atomic_and_reject_invalid_members(self) -> None:
        events = self.feed["events"][:3]
        event_ids = {item["id"] for item in self.feed["events"]}
        state = default_state()
        state["readOverrides"]["evt_ffffffffffffffffffffffff"] = True

        updated = set_events_read(
            state,
            events,
            True,
            current_event_ids=event_ids,
        )
        self.assertTrue(all(event_is_read(updated, event) for event in events))
        self.assertEqual(
            sorted(event["id"] for event in events),
            list(updated["readOverrides"]),
        )
        self.assertNotIn("evt_ffffffffffffffffffffffff", updated["readOverrides"])

        restored = set_events_read(
            updated,
            events,
            False,
            current_event_ids=event_ids,
        )
        self.assertTrue(all(not event_is_read(restored, event) for event in events))
        self.assertEqual({}, restored["readOverrides"])

        with self.assertRaisesRegex(ValidationError, "duplicate"):
            set_events_read(state, [events[0], events[0]], True, current_event_ids=event_ids)
        with self.assertRaisesRegex(ValidationError, "validated cache"):
            set_events_read(state, [events[0]], True, current_event_ids=set())

    def test_old_state_migrates_and_private_preferences_and_filters_are_strict(self) -> None:
        path = user_state_path(self.environment)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schemaVersion": 1, "seenThrough": "2026-08-30T10:00:00Z", "saved": {}}),
            encoding="utf-8",
        )
        state, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, state["schemaVersion"])
        self.assertEqual("2026-08-30T10:00:00Z", state["readThrough"])
        self.assertEqual({}, state["readOverrides"])
        self.assertTrue(state["preferences"]["barVisible"])
        self.assertEqual(
            {"period": "all", "significance": "all", "unreadOnly": False, "imagesOnly": False, "types": []},
            state["preferences"]["sectionFilters"]["front-page"],
        )
        tuned = update_preferences(
            state,
            bar_visible=False,
            images_visible=False,
        )
        self.assertNotIn("interests", tuned["preferences"])
        filtered = update_section_filter(
            tuned,
            "plugins",
            {
                "period": "7d",
                "significance": "notable",
                "unreadOnly": True,
                "imagesOnly": False,
                "types": ["plugin-released"],
            },
        )
        self.assertEqual("7d", filtered["preferences"]["sectionFilters"]["plugins"]["period"])
        self.assertEqual("all", filtered["preferences"]["sectionFilters"]["core"]["period"])
        with self.assertRaises(ValidationError):
            update_section_filter(state, "plugins", {"period": "forever"})
        self.assertNotIn("sectionProfiles", filtered["preferences"])

        path.write_text(
            json.dumps({
                "schemaVersion": 2,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": {"barVisible": False, "imagesVisible": False, "interests": ["security"]},
            }),
            encoding="utf-8",
        )
        v2, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertFalse(v2["preferences"]["barVisible"])
        self.assertNotIn("interests", v2["preferences"])

        v3_preferences = {
            "barVisible": True,
            "imagesVisible": True,
            "interests": [],
            "sectionFilters": legacy_filters(),
        }
        v3_preferences["sectionFilters"]["community"] = {
            "period": "all",
            "significance": "all",
            "unreadOnly": False,
            "imagesOnly": False,
            "types": [],
        }
        v3_preferences["sectionFilters"]["plugins"]["period"] = "30d"
        path.write_text(
            json.dumps({
                "schemaVersion": 3,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": v3_preferences,
            }),
            encoding="utf-8",
        )
        v3, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, v3["schemaVersion"])
        self.assertEqual("30d", v3["preferences"]["sectionFilters"]["plugins"]["period"])
        self.assertNotIn("sectionProfiles", v3["preferences"])

        v4_preferences = {
            "barVisible": True,
            "imagesVisible": True,
            "interests": [],
            "sectionFilters": legacy_filters(),
            "sectionProfiles": {
                "front-page": {"name": "Front Page", "icon": "newspaper", "tone": "clear"},
                "for-you": {"name": "For You", "icon": "spark", "tone": "clear"},
                "core": {"name": "Core", "icon": "core", "tone": "clear"},
                "plugins": {"name": "My Extensions", "icon": "spark", "tone": "accent"},
                "community": {"name": "Community", "icon": "community", "tone": "ink"},
                "saved": {"name": "Saved", "icon": "saved", "tone": "soft"},
            },
        }
        path.write_text(
            json.dumps({
                "schemaVersion": 4,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": v4_preferences,
            }),
            encoding="utf-8",
        )
        v4, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, v4["schemaVersion"])
        self.assertNotIn("sectionProfiles", v4["preferences"])
        self.assertNotIn("community", v4["preferences"]["sectionFilters"])

        v5_preferences = {
            "barVisible": False,
            "imagesVisible": False,
            "interests": ["security"],
            "sectionFilters": legacy_filters(),
            "sectionProfiles": copy.deepcopy(LEGACY_PROFILES),
        }
        v5_preferences["sectionFilters"]["community"] = {
            "period": "30d",
            "significance": "notable",
            "unreadOnly": True,
            "imagesOnly": True,
            "types": ["community-link"],
        }
        v5_preferences["sectionProfiles"]["community"] = {"name": "People"}
        v5_preferences["sectionProfiles"]["plugins"] = {"name": "Extensions"}
        path.write_text(
            json.dumps({
                "schemaVersion": 5,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": toggle_saved(default_state(), self.feed["events"][0], now=CLOCK)[0]["saved"],
                "preferences": v5_preferences,
            }),
            encoding="utf-8",
        )
        v5, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, v5["schemaVersion"])
        self.assertEqual("2026-08-30T10:00:00Z", v5["readThrough"])
        self.assertEqual(1, len(v5["saved"]))
        self.assertFalse(v5["preferences"]["barVisible"])
        self.assertFalse(v5["preferences"]["imagesVisible"])
        self.assertNotIn("interests", v5["preferences"])
        self.assertNotIn("sectionProfiles", v5["preferences"])
        self.assertNotIn("community", v5["preferences"]["sectionFilters"])

        v6_preferences = {
            "barVisible": True,
            "imagesVisible": True,
            "interests": [],
            "sectionFilters": v9_filters(),
            "sectionProfiles": copy.deepcopy(LEGACY_PROFILES),
        }
        path.write_text(
            json.dumps({
                "schemaVersion": 6,
                "seenThrough": "2026-08-31T10:00:00Z",
                "saved": {},
                "preferences": v6_preferences,
            }),
            encoding="utf-8",
        )
        v6, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, v6["schemaVersion"])
        self.assertEqual("2026-08-31T10:00:00Z", v6["readThrough"])
        self.assertEqual({}, v6["readOverrides"])

        v7_preferences = {
            "barVisible": True,
            "imagesVisible": True,
            "interests": ["security"],
            "sectionFilters": v9_filters(),
            "sectionProfiles": copy.deepcopy(LEGACY_PROFILES),
        }
        path.write_text(
            json.dumps({
                "schemaVersion": 7,
                "readThrough": "2026-08-31T10:00:00Z",
                "readOverrides": {self.feed["events"][0]["id"]: True},
                "saved": {},
                "preferences": v7_preferences,
            }),
            encoding="utf-8",
        )
        v7, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, v7["schemaVersion"])
        self.assertEqual({self.feed["events"][0]["id"]: True}, v7["readOverrides"])
        self.assertNotIn("interests", v7["preferences"])

        v8_preferences = {
            "barVisible": True,
            "imagesVisible": True,
            "sectionFilters": v9_filters(),
            "sectionProfiles": copy.deepcopy(LEGACY_PROFILES),
        }
        v8_preferences["sectionFilters"]["plugins"]["period"] = "7d"
        v8_preferences["sectionProfiles"]["plugins"] = {"name": "Extensions"}
        path.write_text(
            json.dumps({
                "schemaVersion": 8,
                "readThrough": "2026-08-31T10:00:00Z",
                "readOverrides": {self.feed["events"][0]["id"]: False},
                "saved": {},
                "preferences": v8_preferences,
            }),
            encoding="utf-8",
        )
        v8, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, v8["schemaVersion"])
        self.assertEqual("7d", v8["preferences"]["sectionFilters"]["plugins"]["period"])
        self.assertEqual({self.feed["events"][0]["id"]: False}, v8["readOverrides"])
        self.assertNotIn("sectionProfiles", v8["preferences"])
        self.assertIn("youtube", v8["preferences"]["sectionFilters"])

        v9_preferences = {
            "barVisible": True,
            "imagesVisible": True,
            "sectionFilters": v9_filters(),
        }
        v9_preferences["sectionFilters"]["core"]["period"] = "24h"
        path.write_text(
            json.dumps({
                "schemaVersion": 9,
                "readThrough": "2026-08-31T10:00:00Z",
                "readOverrides": {},
                "saved": {},
                "preferences": v9_preferences,
            }),
            encoding="utf-8",
        )
        v9, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, v9["schemaVersion"])
        self.assertEqual("24h", v9["preferences"]["sectionFilters"]["core"]["period"])
        self.assertIn("youtube", v9["preferences"]["sectionFilters"])

        self.assertEqual(
            {"core": True, "plugins": True, "youtube": True},
            v9["preferences"]["sectionVisibility"],
        )

        v10_preferences = {
            "barVisible": True,
            "imagesVisible": True,
            "sectionFilters": default_state()["preferences"]["sectionFilters"],
        }
        v10_preferences["sectionFilters"]["youtube"]["period"] = "7d"
        path.write_text(
            json.dumps({
                "schemaVersion": 10,
                "readThrough": "2026-08-31T10:00:00Z",
                "readOverrides": {},
                "saved": {},
                "preferences": v10_preferences,
            }),
            encoding="utf-8",
        )
        v10, quarantine = load_state(self.environment)
        self.assertIsNone(quarantine)
        self.assertEqual(STATE_SCHEMA_VERSION, v10["schemaVersion"])
        self.assertEqual("7d", v10["preferences"]["sectionFilters"]["youtube"]["period"])
        self.assertEqual(
            {"core": True, "plugins": True, "youtube": True},
            v10["preferences"]["sectionVisibility"],
        )

    def test_current_state_rejects_unknown_members_instead_of_normalizing_them_away(self) -> None:
        cases = []

        extra_state = default_state()
        extra_state["unexpected"] = True
        cases.append(extra_state)

        invalid_read_override = default_state()
        invalid_read_override["readOverrides"]["not-an-event"] = True
        cases.append(invalid_read_override)

        too_many_read_overrides = default_state()
        too_many_read_overrides["readOverrides"] = {
            f"evt_{index:024x}": True for index in range(501)
        }
        cases.append(too_many_read_overrides)

        extra_preferences = default_state()
        extra_preferences["preferences"]["unexpected"] = True
        cases.append(extra_preferences)

        extra_filter = default_state()
        extra_filter["preferences"]["sectionFilters"]["plugins"]["unexpected"] = True
        cases.append(extra_filter)

        saved_state, _ = toggle_saved(default_state(), self.feed["events"][0], now=CLOCK)
        saved_record = next(iter(saved_state["saved"].values()))
        saved_record["unexpected"] = True
        cases.append(saved_state)

        for candidate in cases:
            with self.subTest(keys=sorted(candidate)):
                with self.assertRaises(ValidationError):
                    save_state(candidate, self.environment)

    def test_malformed_legacy_states_are_quarantined_instead_of_partially_migrated(self) -> None:
        path = user_state_path(self.environment)
        path.parent.mkdir(parents=True, exist_ok=True)
        filters = legacy_filters()
        valid_v2_preferences = {
            "barVisible": True,
            "imagesVisible": True,
            "interests": [],
        }
        malformed = [
            {
                "schemaVersion": 1,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": {},
            },
            {
                "schemaVersion": 2,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
            },
            {
                "schemaVersion": 2,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": {**valid_v2_preferences, "unexpected": True},
            },
            {
                "schemaVersion": 3,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": valid_v2_preferences,
            },
            {
                "schemaVersion": 3,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": {
                    **valid_v2_preferences,
                    "sectionFilters": {
                        **copy.deepcopy(filters),
                        "plugins": {
                            **filters["plugins"],
                            "unexpected": True,
                        },
                    },
                },
            },
            {
                "schemaVersion": 4,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": None,
            },
            {
                "schemaVersion": 5,
                "seenThrough": "2026-08-30T10:00:00Z",
                "saved": {},
                "preferences": {},
                "unexpected": True,
            },
        ]

        for candidate in malformed:
            with self.subTest(version=candidate["schemaVersion"], keys=sorted(candidate)):
                path.write_text(json.dumps(candidate), encoding="utf-8")
                state, quarantine = load_state(self.environment)
                self.assertEqual(default_state(), state)
                self.assertIsNotNone(quarantine)
                self.assertTrue((path.parent / str(quarantine)).is_file())

    def test_symlink_targets_and_concurrent_refresh_are_refused(self) -> None:
        path = feed_path(self.environment)
        path.parent.mkdir(parents=True, exist_ok=True)
        target = path.parent / "elsewhere"
        target.write_text("safe", encoding="utf-8")
        path.symlink_to(target)
        with self.assertRaises(StorageError):
            save_feed(self.feed, self.environment, now=CLOCK)
        path.unlink()
        with RefreshLock(self.environment):
            with self.assertRaises(StorageError):
                with RefreshLock(self.environment):
                    pass
        with StateLock(self.environment):
            self.assertTrue((Path(self.environment["XDG_STATE_HOME"]) / "omarchy-news-radar/state.lock").is_file())

        root = Path(self.temporary.name)
        symlink_environment = dict(self.environment)
        symlink_environment["XDG_CACHE_HOME"] = str(root / "symlink-cache")
        owned_elsewhere = root / "owned-elsewhere"
        owned_elsewhere.mkdir()
        radar_root = Path(symlink_environment["XDG_CACHE_HOME"]) / "omarchy-news-radar"
        radar_root.parent.mkdir()
        radar_root.symlink_to(owned_elsewhere, target_is_directory=True)
        with self.assertRaises(StorageError):
            load_feed(symlink_environment, now=CLOCK)
        with self.assertRaises(StorageError):
            purge(symlink_environment)

    def test_refresh_lock_write_failure_releases_kernel_lock(self) -> None:
        lock = RefreshLock(self.environment)
        with mock.patch("radar.state.os.write", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(StorageError, "cannot create refresh lock"):
                lock.__enter__()
        self.assertIsNone(lock.descriptor)
        self.assertTrue(lock.path.exists())
        with RefreshLock(self.environment):
            self.assertTrue(lock.path.exists())

    def test_refresh_lock_is_released_after_abrupt_helper_exit(self) -> None:
        command = [
            sys.executable,
            "-c",
            (
                "import time; "
                "from radar.state import RefreshLock; "
                "lock = RefreshLock(); lock.__enter__(); "
                "print('locked', flush=True); time.sleep(30)"
            ),
        ]
        environment = {**os.environ, **self.environment}
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertIsNotNone(process.stdout)
            self.assertIsNotNone(process.stderr)
            assert process.stdout is not None
            self.assertEqual("locked", process.stdout.readline().strip())
            with self.assertRaisesRegex(StorageError, "already running"):
                with RefreshLock(self.environment):
                    pass
            process.kill()
            process.wait(timeout=5)
            with RefreshLock(self.environment):
                pass
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()

    def test_state_lock_serializes_cross_process_mutations(self) -> None:
        command = [
            sys.executable,
            "-c",
            (
                "from radar.state import StateLock; "
                "lock = StateLock(); lock.__enter__(); "
                "print('locked', flush=True); lock.__exit__(None, None, None)"
            ),
        ]
        environment = {**os.environ, **self.environment}
        with StateLock(self.environment):
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.1)
            self.assertIsNone(process.poll())
        stdout, stderr = process.communicate(timeout=5)
        self.assertEqual("locked", stdout.strip())
        self.assertEqual("", stderr)


if __name__ == "__main__":
    unittest.main()
