from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.errors import ValidationError
from radar.setup_news import build_setup_news, setup_news_events, validate_setup_news

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)


class SetupNewsTests(unittest.TestCase):
    def plugin(self, identity: str, *, added_at: datetime) -> dict:
        return {
            "name": identity.rsplit(".", 1)[-1].title(),
            "description": "A source-backed marketplace plugin.",
            "version": "1.0.0",
            "repository": f"https://github.com/example/{identity.rsplit('.', 1)[-1]}",
            "sourceUrl": f"https://github.com/example/{identity.rsplit('.', 1)[-1]}",
            "category": "System",
            "tags": ["system"],
            "addedAt": added_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "listingDated": True,
            "verification": "verified",
            "retired": False,
            "absenceCount": 0,
        }

    def test_full_catalog_rebuild_survives_rolling_feed_capacity(self) -> None:
        plugins = {
            f"org.example.plugin{index:04d}": self.plugin(
                f"org.example.plugin{index:04d}",
                added_at=CLOCK - timedelta(days=2, seconds=index),
            )
            for index in range(700)
        }
        snapshot = {
            "schemaVersion": 2,
            "events": [],
            "sources": {"marketplace": {"plugins": plugins}},
        }
        companion = build_setup_news(snapshot, published_at=CLOCK)
        self.assertEqual(700, len(companion["plugins"]))
        events = setup_news_events(companion)
        self.assertEqual(700, len(events))
        self.assertEqual(set(plugins), {item["entity"]["id"] for item in events})

    def test_expired_undated_and_retired_listings_are_not_reintroduced(self) -> None:
        plugins = {
            "org.example.current": self.plugin("org.example.current", added_at=CLOCK - timedelta(days=2)),
            "org.example.old": self.plugin("org.example.old", added_at=CLOCK - timedelta(days=31)),
            "org.example.undated": {
                **self.plugin("org.example.undated", added_at=CLOCK - timedelta(days=2)),
                "listingDated": False,
            },
            "org.example.retired": {
                **self.plugin("org.example.retired", added_at=CLOCK - timedelta(days=2)),
                "retired": True,
            },
        }
        companion = build_setup_news(
            {"schemaVersion": 2, "events": [], "sources": {"marketplace": {"plugins": plugins}}},
            published_at=CLOCK,
        )
        self.assertEqual(["org.example.current"], [item["id"] for item in companion["plugins"]])

    def test_validation_rejects_unknown_fields_and_non_plugin_activity(self) -> None:
        value = build_setup_news(
            {
                "schemaVersion": 2,
                "events": [],
                "sources": {"marketplace": {"plugins": {
                    "org.example.current": self.plugin(
                        "org.example.current", added_at=CLOCK - timedelta(days=2)
                    )
                }}},
            },
            published_at=CLOCK,
        )
        self.assertEqual(value, validate_setup_news(value, now=CLOCK))
        malformed = copy.deepcopy(value)
        malformed["tracking"] = "no"
        with self.assertRaises(ValidationError):
            validate_setup_news(malformed, now=CLOCK)
        event = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text())["events"][0]
        malformed = copy.deepcopy(value)
        malformed["events"] = [event]
        with self.assertRaises(ValidationError):
            validate_setup_news(malformed, now=CLOCK)


if __name__ == "__main__":
    unittest.main()
