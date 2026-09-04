from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.constants import MAX_EVENTS
from radar.model import canonical_events, retain_events

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)


def _template() -> dict:
    feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))
    return copy.deepcopy(feed["events"][0])


def _eid(suffix_hex24: str) -> str:
    body = suffix_hex24.lower()
    if len(body) != 24 or any(ch not in "0123456789abcdef" for ch in body):
        raise AssertionError(f"bad id body {suffix_hex24!r}")
    return "evt_" + body


def _event(
    *,
    event_id: str,
    event_type: str,
    occurred: datetime,
    title: str = "Fixture",
    section: str | None = None,
) -> dict:
    event = _template()
    event["id"] = event_id
    event["type"] = event_type
    event["title"] = title
    event["summary"] = title
    stamp = occurred.strftime("%Y-%m-%dT%H:%M:%SZ")
    event["occurredAt"] = stamp
    event["discoveredAt"] = stamp
    if section is None:
        section = {
            "omarchy-news": "core",
            "omarchy-released": "core",
            "youtube-video": "youtube",
            "community-link": "community",
        }.get(event_type, "plugins")
    event["classification"]["section"] = section
    if event_type.startswith("plugin"):
        event["entity"] = {
            "kind": "plugin",
            "id": f"org.example.{event_id[-8:]}",
            "name": title,
            "repository": "https://github.com/example/demo",
        }
        event["trust"]["marketplace"] = "verified"
    elif event_type == "youtube-video":
        event["entity"] = {"kind": "youtube", "id": event_id, "name": title}
        event["trust"]["marketplace"] = "not-applicable"
        event["source"] = {
            "label": "YouTube",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        }
    elif event_type in {"omarchy-news", "omarchy-released"}:
        event["entity"] = {"kind": "omarchy", "id": event_id, "name": "Omarchy"}
        event["trust"]["marketplace"] = "not-applicable"
        event["source"] = {
            "label": "Omarchy News",
            "url": "https://omarchy.org/news/2026/09/fixture",
        }
    event.pop("metrics", None)
    event.pop("image", None)
    return event


class RetentionTests(unittest.TestCase):
    def test_drops_events_older_than_retention_window(self) -> None:
        old = _event(
            event_id=_eid("a" * 24),
            event_type="plugin-added",
            occurred=CLOCK - timedelta(days=45),
            title="Too old",
        )
        recent = _event(
            event_id=_eid("b" * 24),
            event_type="plugin-added",
            occurred=CLOCK - timedelta(days=2),
            title="Recent",
        )
        kept = retain_events([old, recent], now=CLOCK, max_events=MAX_EVENTS)
        self.assertEqual([recent["id"]], [event["id"] for event in kept])

    def test_verification_flood_cannot_evict_recent_core_news(self) -> None:
        news = [
            _event(
                event_id=_eid(f"{index:024x}"),
                event_type="omarchy-news",
                occurred=CLOCK - timedelta(hours=index),
                title=f"News {index}",
            )
            for index in range(1, 6)
        ]
        flood = [
            _event(
                event_id=_eid(f"{(1000 + index):024x}"),
                event_type="plugin-verification-changed",
                occurred=CLOCK - timedelta(minutes=index),
                title=f"Verify {index}",
            )
            for index in range(1, 40)
        ]
        kept = retain_events(news + flood, now=CLOCK, max_events=20)
        self.assertEqual(5, sum(1 for event in kept if event["type"] == "omarchy-news"))
        self.assertEqual(20, len(kept))

    def test_canonical_events_uses_priority_trim(self) -> None:
        youtube = _event(
            event_id=_eid("c" * 24),
            event_type="youtube-video",
            occurred=CLOCK - timedelta(days=1),
            title="Video",
        )
        release = _event(
            event_id=_eid("d" * 24),
            event_type="omarchy-released",
            occurred=CLOCK - timedelta(days=1),
            title="Omarchy v9.9.9",
        )
        flood = [
            _event(
                event_id=_eid(f"{(2000 + index):024x}"),
                event_type="plugin-verification-changed",
                occurred=CLOCK - timedelta(minutes=index),
                title=f"Verify {index}",
            )
            for index in range(1, 30)
        ]
        kept = canonical_events([youtube, release, *flood], now=CLOCK)
        ids = {event["id"] for event in kept}
        self.assertIn(youtube["id"], ids)
        self.assertIn(release["id"], ids)


if __name__ == "__main__":
    unittest.main()
