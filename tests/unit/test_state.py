from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.errors import StorageError, ValidationError
from radar.state import (
    RefreshLock,
    default_state,
    feed_path,
    load_feed,
    load_state,
    mark_seen,
    purge,
    save_feed,
    save_state,
    toggle_saved,
    user_state_path,
)

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


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
        save_state(default_state(), self.environment)
        self.assertEqual(self.feed, load_feed(self.environment, now=CLOCK))
        self.assertEqual(0o600, feed_path(self.environment).stat().st_mode & 0o777)
        self.assertEqual(["feed.json", "state.json"], purge(self.environment))

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

    def test_seen_is_monotonic_and_save_is_independent(self) -> None:
        state = mark_seen(default_state(), "2026-08-31T10:00:00Z")
        state = mark_seen(state, "2026-08-30T10:00:00Z")
        self.assertEqual("2026-08-31T10:00:00Z", state["seenThrough"])
        updated, saved = toggle_saved(state, self.feed["events"][0], now=CLOCK)
        self.assertTrue(saved)
        self.assertEqual("2026-08-31T10:00:00Z", updated["seenThrough"])
        updated, saved = toggle_saved(updated, self.feed["events"][0], now=CLOCK)
        self.assertFalse(saved)

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


if __name__ == "__main__":
    unittest.main()
