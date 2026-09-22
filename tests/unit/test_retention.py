from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.errors import ValidationError
from radar.constants import CORE_RETENTION_FLOOR, MAX_EVENTS
from radar.model import canonical_events, event_sort_key, retain_events

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

    def test_release_volume_cannot_evict_the_core_news_floor(self) -> None:
        """The reported production shape: thousands of releases, news squeezed out.

        On 22 September 2026 the public edition carried 480 `plugin-released`
        rows and only five `omarchy-news` rows, leaving an eleven-day news
        window. Every eviction erased the reader's dismissal, so the story
        returned unread on the next collect (D073).
        """

        now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
        events = [
            _event(
                event_id=_eid(f"{index:024x}"),
                event_type="plugin-released",
                occurred=now - timedelta(days=index % 12, minutes=index),
                title=f"Release {index}",
            )
            for index in range(900)
        ]
        events += [
            _event(
                event_id=_eid(f"{0xC0 + index:024x}"),
                event_type="omarchy-news",
                occurred=now - timedelta(days=index),
                title=f"Official news {index}",
            )
            for index in range(28)
        ]
        kept = retain_events(events, now=now)
        news = [item for item in kept if item["type"] == "omarchy-news"]

        self.assertEqual(MAX_EVENTS, len(kept))
        self.assertEqual(CORE_RETENTION_FLOOR["omarchy-news"], len(news))
        # The floor keeps the newest rows, not an arbitrary slice.
        self.assertEqual(
            [item["title"] for item in sorted(news, key=event_sort_key)],
            [f"Official news {index}" for index in range(CORE_RETENTION_FLOOR["omarchy-news"])],
        )
        self.assertGreater(
            len([item for item in kept if item["type"] == "plugin-released"]), 400
        )

    def test_the_core_floor_never_breaks_the_bound_or_required_additions(self) -> None:
        now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
        additions = [
            _event(
                event_id=_eid(f"{0xADD00 + index:024x}"),
                event_type="plugin-added",
                occurred=now - timedelta(days=1, minutes=index),
                title=f"Added {index}",
            )
            for index in range(40)
        ]
        events = additions + [
            _event(
                event_id=_eid(f"{0xB0000 + index:024x}"),
                event_type="plugin-released",
                occurred=now - timedelta(days=2, minutes=index),
                title=f"Release {index}",
            )
            for index in range(800)
        ] + [
            _event(
                event_id=_eid(f"{0xC000 + index:024x}"),
                event_type="omarchy-news",
                occurred=now - timedelta(days=index),
                title=f"News {index}",
            )
            for index in range(28)
        ]
        required = {item["id"] for item in additions}
        kept = retain_events(events, now=now, required_event_ids=required)
        kept_ids = {item["id"] for item in kept}

        self.assertEqual(MAX_EVENTS, len(kept))
        self.assertTrue(required <= kept_ids, "mandatory additions must survive (D066)")
        self.assertEqual(
            CORE_RETENTION_FLOOR["omarchy-news"],
            len([item for item in kept if item["type"] == "omarchy-news"]),
        )
        self.assertEqual(len(kept_ids), len(kept), "retention must not duplicate an event")
        self.assertEqual(kept, sorted(kept, key=event_sort_key))

    def test_a_small_edition_is_unchanged_by_the_floor(self) -> None:
        now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
        events = [
            _event(
                event_id=_eid(f"{0xD000 + index:024x}"),
                event_type="plugin-released",
                occurred=now - timedelta(hours=index),
                title=f"Release {index}",
            )
            for index in range(5)
        ]
        self.assertEqual(
            sorted(events, key=event_sort_key), retain_events(events, now=now)
        )

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

    def test_marketplace_addition_flood_cannot_evict_plugin_releases(self) -> None:
        releases = [
            _event(
                event_id=_eid(f"{(3000 + index):024x}"),
                event_type="plugin-released",
                occurred=CLOCK - timedelta(days=2, minutes=index),
                title=f"Release {index}",
            )
            for index in range(3)
        ]
        additions = [
            _event(
                event_id=_eid(f"{(4000 + index):024x}"),
                event_type="plugin-added",
                occurred=CLOCK - timedelta(minutes=index),
                title=f"Addition {index}",
            )
            for index in range(30)
        ]
        kept = retain_events(releases + additions, now=CLOCK, max_events=10)
        self.assertEqual(
            {item["id"] for item in releases},
            {item["id"] for item in kept if item["type"] == "plugin-released"},
        )

    def test_required_additions_displace_protected_release_history(self) -> None:
        releases = [
            _event(
                event_id=_eid(f"{(5000 + index):024x}"),
                event_type="plugin-released",
                occurred=CLOCK - timedelta(minutes=index),
                title=f"Release {index}",
            )
            for index in range(10)
        ]
        additions = [
            _event(
                event_id=_eid(f"{(6000 + index):024x}"),
                event_type="plugin-added",
                occurred=CLOCK - timedelta(days=1, minutes=index),
                title=f"Addition {index}",
            )
            for index in range(2)
        ]
        required = {event["id"] for event in additions}

        kept = retain_events(
            releases + additions,
            now=CLOCK,
            max_events=10,
            required_event_ids=required,
        )

        self.assertEqual(required, {event["id"] for event in kept} & required)
        self.assertEqual(8, sum(event["type"] == "plugin-released" for event in kept))

    def test_required_event_contract_fails_before_silent_loss(self) -> None:
        addition = _event(
            event_id=_eid("f" * 24),
            event_type="plugin-added",
            occurred=CLOCK - timedelta(days=31),
            title="Expired addition",
        )
        with self.assertRaisesRegex(ValidationError, "retention window"):
            retain_events(
                [addition],
                now=CLOCK,
                max_events=10,
                required_event_ids={addition["id"]},
            )


if __name__ == "__main__":
    unittest.main()
