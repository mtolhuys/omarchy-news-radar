from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.client import indicator_model, projection_model, read_model, refresh, set_preferences, toggle_saved_state
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
        event_id = self.feed["events"][0]["id"]
        saved = toggle_saved_state(event_id, self.environment, now=CLOCK)
        self.assertTrue(saved["saved"])
        projected = projection_model("saved", "[]", "", self.environment, now=CLOCK)
        self.assertEqual([event_id], [event["id"] for event in projected["events"]])

    def test_indicator_and_interests_stay_in_local_state(self) -> None:
        refresh(self.environment, now=CLOCK)
        indicator = indicator_model(self.environment, now=CLOCK)
        self.assertGreater(indicator["unread"], 0)
        tuned = set_preferences(
            bar_visible=False,
            images_visible=False,
            interests=["notes"],
            environment=self.environment,
        )
        self.assertFalse(tuned["state"]["preferences"]["barVisible"])
        projected = projection_model("for-you", "[]", "", self.environment, now=CLOCK)
        self.assertTrue(any("notes" in event["classification"]["tags"] for event in projected["events"]))
        self.assertFalse(indicator_model(self.environment, now=CLOCK)["barVisible"])


if __name__ == "__main__":
    unittest.main()
