from __future__ import annotations

import unittest

from radar.constants import NEWS_FRONT_PAGE_QUOTA
from radar.model import front_page
from radar.topics import cluster_titles, diversify_by_topic


def news_event(event_id: str, title: str, summary: str, occurred: str) -> dict:
    return {
        "id": event_id,
        "type": "omarchy-news",
        "occurredAt": occurred,
        "discoveredAt": occurred,
        "title": title,
        "summary": summary,
        "source": {"label": "Omarchy News", "url": f"https://omarchy.org/news/2026/08/{event_id[4:]}"},
        "entity": {"kind": "omarchy", "id": event_id, "name": "Omarchy News"},
        "classification": {
            "section": "core",
            "significance": "routine",
            "curated": False,
            "tags": ["news"],
        },
        "trust": {"marketplace": "not-applicable", "securityAudit": False},
        "compatibility": {"channels": ["quattro"], "basis": "declared"},
    }


class TopicDiversityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = [
            news_event(
                "evt_aaaaaaaaaaaaaaaaaaaaaaa1",
                "The Omarchy Foundation",
                "A new foundation now stewards Omarchy development.",
                "2026-08-31T12:00:00Z",
            ),
            news_event(
                "evt_aaaaaaaaaaaaaaaaaaaaaaa2",
                "Patronage for the Omarchy Foundation",
                "Patronage tiers fund the foundation and its stewardship.",
                "2026-08-31T11:00:00Z",
            ),
            news_event(
                "evt_aaaaaaaaaaaaaaaaaaaaaaa3",
                "Foundation FAQ",
                "Answers about the foundation, patronage, and stewardship.",
                "2026-08-31T10:00:00Z",
            ),
            news_event(
                "evt_aaaaaaaaaaaaaaaaaaaaaaa4",
                "Hyprland 0.52 lands in Omarchy",
                "The compositor bump ships with new binds for the desktop.",
                "2026-08-31T09:00:00Z",
            ),
            news_event(
                "evt_aaaaaaaaaaaaaaaaaaaaaaa5",
                "Theme gallery refresh",
                "Fresh themes land in the picker this week.",
                "2026-08-31T08:00:00Z",
            ),
        ]

    def test_same_cycle_foundation_stories_share_one_cluster(self) -> None:
        clusters = cluster_titles(self.events)
        self.assertEqual(clusters["evt_aaaaaaaaaaaaaaaaaaaaaaa1"], clusters["evt_aaaaaaaaaaaaaaaaaaaaaaa2"])
        self.assertEqual(clusters["evt_aaaaaaaaaaaaaaaaaaaaaaa1"], clusters["evt_aaaaaaaaaaaaaaaaaaaaaaa3"])
        self.assertNotEqual(clusters["evt_aaaaaaaaaaaaaaaaaaaaaaa1"], clusters["evt_aaaaaaaaaaaaaaaaaaaaaaa4"])

    def test_front_page_takes_one_item_per_cluster_before_backfill(self) -> None:
        diversified = diversify_by_topic(self.events, NEWS_FRONT_PAGE_QUOTA)
        self.assertEqual(
            [
                "evt_aaaaaaaaaaaaaaaaaaaaaaa1",
                "evt_aaaaaaaaaaaaaaaaaaaaaaa4",
                "evt_aaaaaaaaaaaaaaaaaaaaaaa5",
            ],
            [event["id"] for event in diversified],
        )
        selected = front_page(self.events)
        news_ids = [event["id"] for event in selected if event["type"] == "omarchy-news"]
        self.assertEqual(3, len(news_ids))
        self.assertEqual(
            [
                "evt_aaaaaaaaaaaaaaaaaaaaaaa1",
                "evt_aaaaaaaaaaaaaaaaaaaaaaa4",
                "evt_aaaaaaaaaaaaaaaaaaaaaaa5",
            ],
            news_ids,
        )

    def test_single_topic_window_keeps_freshness_quota(self) -> None:
        only_foundation = self.events[:3]
        selected = diversify_by_topic(only_foundation, NEWS_FRONT_PAGE_QUOTA)
        self.assertEqual([event["id"] for event in only_foundation], [event["id"] for event in selected])


    def test_verification_changed_stays_off_front_page(self) -> None:
        events = list(self.events)
        events.append(
            {
                "id": "evt_bbbbbbbbbbbbbbbbbbbbbb01",
                "type": "plugin-verification-changed",
                "occurredAt": "2026-08-31T13:00:00Z",
                "discoveredAt": "2026-08-31T13:00:00Z",
                "title": "Demo: unverified -> verified",
                "summary": "Marketplace verification moved from unverified to verified.",
                "source": {"label": "Plugin source", "url": "https://github.com/example/demo"},
                "entity": {
                    "kind": "plugin",
                    "id": "org.example.demo",
                    "name": "Demo",
                    "repository": "https://github.com/example/demo",
                },
                "classification": {
                    "section": "plugins",
                    "significance": "routine",
                    "curated": False,
                    "tags": ["desktop"],
                },
                "trust": {"marketplace": "verified", "securityAudit": False},
                "compatibility": {"channels": [], "basis": "unknown"},
            }
        )
        selected = front_page(events)
        self.assertNotIn("plugin-verification-changed", {event["type"] for event in selected})



if __name__ == "__main__":
    unittest.main()
