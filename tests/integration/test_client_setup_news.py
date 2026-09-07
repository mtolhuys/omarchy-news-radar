from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from radar.client_setup_news import load_setup_news, refresh_setup_news
from radar.constants import SETUP_NEWS_URL
from radar.errors import FetchError
from radar.io import atomic_write_json
from radar.setup_news import build_setup_news
from radar.state import cache_root

CLOCK = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)


class ClientSetupNewsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.environment = {
            "HOME": str(base / "home"),
            "XDG_CACHE_HOME": str(base / "cache"),
            "XDG_STATE_HOME": str(base / "state"),
        }
        plugin = {
            "name": "Installed Example",
            "description": "A source-backed marketplace listing.",
            "version": "1.0.0",
            "repository": "https://github.com/example/installed",
            "sourceUrl": "https://github.com/example/installed",
            "category": "System",
            "tags": ["system"],
            "addedAt": "2026-09-01T12:00:00Z",
            "listingDated": True,
            "verification": "verified",
            "retired": False,
            "absenceCount": 0,
        }
        self.companion = build_setup_news(
            {
                "schemaVersion": 2,
                "events": [],
                "sources": {"marketplace": {"plugins": {"org.example.installed": plugin}}},
            },
            published_at=CLOCK,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_refresh_is_generic_conditional_and_preserves_cache_on_failure(self) -> None:
        payload = json.dumps(self.companion).encode()
        with mock.patch(
            "radar.client_setup_news.fetch_bytes",
            return_value=(payload, {"ETag": '"setup"'}, 200),
        ) as fetch:
            result = refresh_setup_news(self.environment, now=CLOCK)
        self.assertEqual("cached", result["status"])
        args, kwargs = fetch.call_args
        self.assertEqual((SETUP_NEWS_URL,), args)
        self.assertNotIn("org.example.installed", json.dumps(kwargs["headers"]))
        self.assertEqual(self.companion, load_setup_news(self.environment, now=CLOCK))
        metadata = (cache_root(self.environment) / "setup-news-http.json").read_bytes()
        with mock.patch(
            "radar.client_setup_news.fetch_bytes",
            side_effect=FetchError("network-error", "offline"),
        ):
            failed = refresh_setup_news(self.environment, now=CLOCK + timedelta(minutes=6))
        self.assertEqual("cached", failed["status"])
        self.assertEqual(metadata, (cache_root(self.environment) / "setup-news-http.json").read_bytes())
        self.assertEqual(self.companion, load_setup_news(self.environment, now=CLOCK))

    def test_test_boundary_loads_only_the_explicit_local_companion(self) -> None:
        path = Path(self.temporary.name) / "setup-news.json"
        atomic_write_json(path, self.companion)
        env = {
            **self.environment,
            "OMARCHY_NEWS_RADAR_TEST_MODE": "1",
            "OMARCHY_NEWS_RADAR_TEST_SETUP_NEWS": str(path),
        }
        result = refresh_setup_news(env, now=CLOCK)
        self.assertEqual(1, result["stories"])
        self.assertEqual(self.companion, load_setup_news(env, now=CLOCK))


if __name__ == "__main__":
    unittest.main()
