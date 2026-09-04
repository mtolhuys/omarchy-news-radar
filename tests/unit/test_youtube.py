from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.collector import FixtureInputs, collect_from_fixtures, empty_snapshot
from radar.errors import ValidationError
from radar.model import front_page, project_section
from radar.sources.youtube import (
    normalize_preferred_languages,
    parse_search_video_ids,
    parse_videos,
    preferred_languages_or_default,
    rank_youtube_videos,
    relevance_languages_for_search,
    search_url,
    should_refresh_youtube,
    youtube_events,
)
from radar.validation import validate_feed

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class YouTubeSourceTests(unittest.TestCase):
    def fixture_videos(self):
        return json.loads((ROOT / "tests/fixtures/youtube-baseline.json").read_text(encoding="utf-8"))["videos"]


    def test_search_url_biases_relevance_language(self) -> None:
        url = search_url(query="Omarchy", api_key="test-key")
        self.assertIn("relevanceLanguage=en", url)
        self.assertIn("q=Omarchy", url)
        dutch = search_url(query="Omarchy", api_key="test-key", relevance_language="nl")
        self.assertIn("relevanceLanguage=nl", dutch)

    def test_preferred_languages_normalize_and_primary_search_pass(self) -> None:
        self.assertEqual(("en", "nl", "zh-Hans"), normalize_preferred_languages("en, nl, en, XX, zh-Hans"))
        self.assertEqual(("en",), preferred_languages_or_default(None))
        self.assertEqual(("en",), preferred_languages_or_default("bogus"))
        # Multi-language preferences are accepted, but search still uses the primary today.
        self.assertEqual(("nl",), relevance_languages_for_search(["nl", "en"]))

    def test_keyword_filter_and_ranking_interleave(self) -> None:
        search = {
            "items": [
                {
                    "id": {"kind": "youtube#video", "videoId": "dQwOmarchy1"},
                    "snippet": {"title": "Omarchy walkthrough", "description": "demo"},
                },
                {
                    "id": {"kind": "youtube#video", "videoId": "xxxxxxxxxx1"},
                    "snippet": {"title": "Unrelated desktop", "description": "no match"},
                },
            ]
        }
        self.assertEqual(["dQwOmarchy1"], parse_search_video_ids(search))
        ranked = rank_youtube_videos(self.fixture_videos())
        self.assertEqual("dQwOmarchy4", ranked[0]["id"])  # highest views leads
        self.assertLessEqual(len(ranked), 24)

    def test_parse_videos_requires_keyword_and_builds_events(self) -> None:
        payload = {
            "items": [
                {
                    "id": "dQwOmarchy1",
                    "snippet": {
                        "title": "Omarchy Quattro",
                        "description": "About Omarchy",
                        "channelTitle": "Channel",
                        "publishedAt": "2026-08-30T12:00:00.000Z",
                    },
                    "statistics": {"viewCount": "10", "likeCount": "2"},
                },
                {
                    "id": "dQwOmarchyX",
                    "snippet": {
                        "title": "Something else",
                        "description": "no keyword",
                        "channelTitle": "Channel",
                        "publishedAt": "2026-08-30T12:00:00Z",
                    },
                    "statistics": {"viewCount": "99", "likeCount": "9"},
                },
            ]
        }
        videos = parse_videos(payload)
        self.assertEqual(["dQwOmarchy1"], [video["id"] for video in videos])
        events = youtube_events(videos, discovered_at=CLOCK)
        self.assertEqual(1, len(events))
        self.assertEqual("youtube-video", events[0]["type"])
        self.assertEqual("youtube", events[0]["classification"]["section"])
        self.assertEqual("yt:dQwOmarchy1", events[0]["entity"]["id"])
        self.assertTrue(events[0]["image"]["sourceUrl"].startswith("https://i.ytimg.com/vi/"))


    def test_youtube_entity_id_accepts_leading_underscore_video_ids(self) -> None:
        payload = {
            "items": [
                {
                    "id": "_CuibYl_Fh0",
                    "snippet": {
                        "title": "Omarchy interview",
                        "description": "About Omarchy",
                        "channelTitle": "Channel",
                        "publishedAt": "2026-08-30T12:00:00Z",
                    },
                    "statistics": {"viewCount": "10", "likeCount": "2"},
                }
            ]
        }
        videos = parse_videos(payload)
        events = youtube_events(videos, discovered_at=CLOCK)
        self.assertEqual("yt:_CuibYl_Fh0", events[0]["entity"]["id"])
        self.assertTrue(events[0]["source"]["url"].endswith("watch?v=_CuibYl_Fh0"))
        from radar.validation import validate_feed
        # Build a minimal validated path via collect fixture is heavy; validate_event through feed helper.
        from radar.validation import validate_event
        validate_event(events[0])

    def test_parse_videos_truncates_long_or_empty_description(self) -> None:
        long_description = ("Omarchy notes. " * 80).strip()
        payload = {
            "items": [
                {
                    "id": "dQwOmarchy1",
                    "snippet": {
                        "title": "Omarchy long desc",
                        "description": long_description,
                        "channelTitle": "Channel",
                        "publishedAt": "2026-08-30T12:00:00Z",
                    },
                    "statistics": {"viewCount": "10", "likeCount": "2"},
                },
                {
                    "id": "dQwOmarchy2",
                    "snippet": {
                        "title": "Omarchy empty desc",
                        "description": "   ",
                        "channelTitle": "Channel",
                        "publishedAt": "2026-08-30T11:00:00Z",
                    },
                    "statistics": {"viewCount": "5", "likeCount": "1"},
                },
            ]
        }
        videos = parse_videos(payload)
        self.assertEqual(["dQwOmarchy1", "dQwOmarchy2"], [video["id"] for video in videos])
        self.assertLessEqual(len(videos[0]["summary"]), 400)
        self.assertTrue(videos[0]["summary"].endswith("…"))
        from radar.sources.youtube_text import NEUTRAL_SUMMARY
        self.assertEqual(NEUTRAL_SUMMARY, videos[1]["summary"])

    def test_missing_key_fails_closed_and_retains_prior(self) -> None:
        inputs = FixtureInputs(
            ROOT / "tests/fixtures/releases-baseline.json",
            ROOT / "tests/fixtures/catalog-baseline.json",
            ROOT / "tests/fixtures/community",
            ROOT / "content/curation",
            ROOT / "tests/fixtures/engagement-baseline.json",
            ROOT / "tests/fixtures/youtube-baseline.json",
        )
        feed, snapshot = collect_from_fixtures(
            inputs,
            previous_snapshot=None,
            now=CLOCK,
            bootstrap_marketplace=True,
        )
        youtube_ids = {event["id"] for event in feed["events"] if event["type"] == "youtube-video"}
        self.assertTrue(youtube_ids)
        self.assertNotIn(
            "youtube-video",
            {event["type"] for event in front_page(feed["events"])},
        )
        ranked = project_section(feed, "youtube")
        self.assertEqual("youtube-video", ranked[0]["type"])
        validate_feed(feed, now=CLOCK)

        failed_feed, failed_snapshot = collect_from_fixtures(
            FixtureInputs(
                ROOT / "tests/fixtures/releases-next.json",
                ROOT / "tests/fixtures/catalog-next.json",
                ROOT / "tests/fixtures/community",
                ROOT / "content/curation",
                ROOT / "tests/fixtures/engagement-next.json",
            ),
            previous_snapshot=snapshot,
            now=CLOCK + timedelta(hours=7),
            bootstrap_marketplace=False,
            failed_sources={"youtube": "validation-failed"},
        )
        retained = {event["id"] for event in failed_feed["events"] if event["type"] == "youtube-video"}
        self.assertEqual(youtube_ids, retained)
        health = next(item for item in failed_feed["sources"] if item["id"] == "youtube")
        self.assertEqual(("failed", "validation-failed"), (health["status"], health["reason"]))
        self.assertEqual(snapshot["sources"]["youtube"], failed_snapshot["sources"]["youtube"])

    def test_refresh_cadence_and_schema_gate(self) -> None:
        self.assertTrue(should_refresh_youtube(None, now=CLOCK))
        self.assertTrue(
            should_refresh_youtube({"checkedAt": "2026-08-31T10:00:00Z", "videoIds": []}, now=CLOCK),
            "empty youtube snapshot must refresh immediately",
        )
        self.assertTrue(
            should_refresh_youtube({"checkedAt": "2026-08-31T10:00:00Z"}, now=CLOCK),
            "missing videoIds must refresh immediately",
        )
        self.assertFalse(
            should_refresh_youtube(
                {"checkedAt": "2026-08-31T13:00:00Z", "videoIds": ["yt:dQwOmarchy1"]},
                now=CLOCK,
            ),
            "within the two-hour cadence must not refresh",
        )
        self.assertTrue(
            should_refresh_youtube(
                {"checkedAt": "2026-08-31T11:59:00Z", "videoIds": ["yt:dQwOmarchy1"]},
                now=CLOCK,
            ),
            "past the two-hour cadence must refresh",
        )
        with self.assertRaises(ValidationError):
            parse_search_video_ids({"items": [{"id": {"videoId": "short"}}]})


    def test_youtube_refresh_does_not_wipe_prior_lane(self) -> None:
        """A thinner fresh ranking must not erase already-retained YouTube rows."""
        from copy import deepcopy

        inputs = FixtureInputs(
            ROOT / "tests/fixtures/releases-baseline.json",
            ROOT / "tests/fixtures/catalog-baseline.json",
            ROOT / "tests/fixtures/community",
            ROOT / "content/curation",
            ROOT / "tests/fixtures/engagement-baseline.json",
            ROOT / "tests/fixtures/youtube-baseline.json",
        )
        feed, snapshot = collect_from_fixtures(
            inputs,
            previous_snapshot=None,
            now=CLOCK,
            bootstrap_marketplace=True,
        )
        prior_ids = {event["id"] for event in feed["events"] if event["type"] == "youtube-video"}
        self.assertTrue(prior_ids)
        # Second collect with the same fixture should keep the lane (merge), not
        # shrink it to empty when prior rows remain in-window.
        feed2, _ = collect_from_fixtures(
            inputs,
            previous_snapshot=deepcopy(snapshot),
            now=CLOCK,
            bootstrap_marketplace=False,
        )
        after_ids = {event["id"] for event in feed2["events"] if event["type"] == "youtube-video"}
        self.assertTrue(prior_ids <= after_ids)


if __name__ == "__main__":
    unittest.main()
