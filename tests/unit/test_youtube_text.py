from __future__ import annotations

import unittest

from radar.sources.youtube import parse_videos, rank_youtube_videos, youtube_events
from radar.sources.youtube_text import (
    NEUTRAL_SUMMARY,
    REASON_CONTROVERSY,
    REASON_PROMOTIONAL,
    REASON_REPEATED_ALARM,
    REASON_WEAK_RELEVANCE,
    evaluate_eligibility,
    sanitize_description,
)
from radar.validation import validate_event

CLOCK_ISO = "2026-08-30T12:00:00Z"


def video_item(
    video_id: str,
    *,
    title: str,
    description: str,
    channel: str = "Example Channel",
    views: str = "10",
    likes: str = "1",
    published: str = CLOCK_ISO,
) -> dict:
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "description": description,
            "channelTitle": channel,
            "publishedAt": published,
        },
        "statistics": {"viewCount": views, "likeCount": likes},
    }


class YouTubeTextTests(unittest.TestCase):
    def test_sanitize_drops_leading_sponsor_course_affiliate_and_url_blocks(self) -> None:
        raw = (
            "Thanks to our sponsor SkillCourse — use code OMARCHY for 20% off\n"
            "My course: https://example.com/course?utm_source=desc&utm_campaign=yt\n"
            "Affiliate: buymeacoffee.com/host\n"
            "https://only.example/link\n"
            "Omarchy Quattro keeps the desktop keyboard-first and plugin-shaped.\n"
            "Chapters\n"
            "00:00 Intro\n"
            "Socials: @host\n"
        )
        cleaned = sanitize_description(raw)
        self.assertIn("keyboard-first", cleaned.prose)
        self.assertNotIn("sponsor", cleaned.prose.casefold())
        self.assertNotIn("course", cleaned.prose.casefold())
        self.assertNotIn("http", cleaned.prose.casefold())
        self.assertNotIn("utm_", cleaned.prose.casefold())
        self.assertGreater(cleaned.stripped_urls, 0)
        self.assertLessEqual(len(cleaned.summary), 400)

    def test_url_only_description_uses_neutral_fallback(self) -> None:
        cleaned = sanitize_description("https://example.com/a https://example.org/b")
        self.assertEqual("", cleaned.prose)
        self.assertEqual(NEUTRAL_SUMMARY, cleaned.summary)

    def test_multilingual_substantive_review_stays_eligible(self) -> None:
        title = "Omarchy Quattro revisión"
        prose = (
            "Omarchy Quattro mantiene el escritorio en el teclado y explica "
            "cómo los plugins reemplazan capas extra."
        )
        self.assertTrue(evaluate_eligibility(title=title, prose=prose).eligible)
        cleaned = sanitize_description("日本語のレビュー。Omarchy のキーボード操作を詳しく説明しています。")
        self.assertGreater(cleaned.prose_letters, 12)

    def test_incidental_link_mention_is_not_enough(self) -> None:
        decision = evaluate_eligibility(
            title="Weekend desktop tour",
            prose="I also linked omarchy.org somewhere near the end of this travel vlog.",
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(REASON_WEAK_RELEVANCE, decision.reason)

    def test_promo_and_link_only_with_weak_title_are_rejected(self) -> None:
        decision = evaluate_eligibility(title="Omarchy", prose="")
        self.assertFalse(decision.eligible)
        self.assertEqual(REASON_PROMOTIONAL, decision.reason)

    def test_critical_review_false_positives_survive(self) -> None:
        title = "Omarchy is not for everyone"
        prose = (
            "A careful review of Omarchy Quattro that explains what broke, "
            "what still works, and why this reviewer will not switch yet."
        )
        self.assertTrue(evaluate_eligibility(title=title, prose=prose).eligible)
        harsh = evaluate_eligibility(
            title="Omarchy review: catch the regressions",
            prose=(
                "This catch-up review lists the regressions that still block daily "
                "use and the one workflow that remains worth keeping."
            ),
        )
        self.assertTrue(harsh.eligible)

    def test_alarm_emoji_alone_does_not_drop_an_item(self) -> None:
        decision = evaluate_eligibility(
            title="Omarchy 🚨 setup notes",
            prose=(
                "A calm walkthrough of Omarchy installation, first-boot themes, "
                "and the keyboard bindings that matter on day one."
            ),
        )
        self.assertTrue(decision.eligible)

    def test_controversy_needs_amplification_together(self) -> None:
        calm = evaluate_eligibility(
            title="Omarchy and local politics in one lab note",
            prose=(
                "The write-up mentions politics only to explain why a campus lab "
                "chose a local-first Omarchy image."
            ),
        )
        self.assertTrue(calm.eligible)
        loud = evaluate_eligibility(
            title="THE TRUTH ABOUT OMARCHY!!! 🚨🚨",
            prose="SHOCKING political drama. You won't believe this election take.",
        )
        self.assertFalse(loud.eligible)
        self.assertEqual(REASON_CONTROVERSY, loud.reason)

    def test_repeated_alarm_without_substance_is_dropped(self) -> None:
        decision = evaluate_eligibility(
            title="OMARCHY DESTROYED??? 🚨🚨",
            prose="INSANE!!! You won't believe this!!",
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(REASON_REPEATED_ALARM, decision.reason)

    def test_language_is_never_a_drop_reason(self) -> None:
        decision = evaluate_eligibility(
            title="Omarchy Quattro レビュー",
            prose="この動画は Omarchy の導入とキーボード操作を具体的に説明します。" * 2,
        )
        self.assertTrue(decision.eligible)
        self.assertEqual("", decision.reason)

    def test_parse_videos_applies_eligibility_and_neutral_empty_summary(self) -> None:
        payload = {
            "items": [
                video_item(
                    "dQwOmarchy1",
                    title="Omarchy long desc",
                    description=("Omarchy notes about the keyboard desktop. " * 40).strip(),
                ),
                video_item("dQwOmarchy2", title="Omarchy empty desc", description="   "),
                video_item(
                    "dQwOmarchyX",
                    title="Unrelated vlog",
                    description="See also https://omarchy.org/news for no reason.",
                ),
            ]
        }
        videos = parse_videos(payload)
        self.assertEqual(["dQwOmarchy1", "dQwOmarchy2"], [video["id"] for video in videos])
        self.assertLessEqual(len(videos[0]["summary"]), 400)
        self.assertTrue(videos[0]["summary"].endswith("…"))
        self.assertEqual(NEUTRAL_SUMMARY, videos[1]["summary"])

    def test_channel_cap_and_reupload_dedupe_are_deterministic(self) -> None:
        videos = [
            {
                "id": f"id{index:09d}",
                "title": "Omarchy walkthrough" if index < 2 else f"Omarchy topic {index}",
                "channelTitle": "Same Channel",
                "publishedAt": f"2026-08-2{index}T12:00:00Z",
                "views": 1000 - index * 10,
                "likes": 50 - index,
            }
            for index in range(4)
        ]
        ranked = rank_youtube_videos(videos)
        # index 0/1 share a title so reupload dedupe leaves 3 uniques; cap is 4.
        self.assertEqual(3, len(ranked))
        self.assertEqual({"Same Channel"}, {item["channelTitle"] for item in ranked})
        self.assertEqual("id000000000", ranked[0]["id"])
        again = rank_youtube_videos(list(reversed(videos)))
        self.assertEqual([item["id"] for item in ranked], [item["id"] for item in again])
        flooded = [
            {
                "id": f"flood{index:07d}",
                "title": f"Omarchy deep dive {index}",
                "channelTitle": "Prolific",
                "publishedAt": f"2026-08-{10+index:02d}T12:00:00Z",
                "views": 5000 - index,
                "likes": 200 - index,
            }
            for index in range(8)
        ]
        capped = rank_youtube_videos(flooded)
        self.assertEqual(4, len(capped))
        self.assertEqual({"Prolific"}, {item["channelTitle"] for item in capped})

    def test_events_stay_off_front_page_and_validate(self) -> None:
        videos = parse_videos(
            {
                "items": [
                    video_item(
                        "dQwOmarchy1",
                        title="Omarchy Quattro tour",
                        description="A calm Omarchy keyboard tour with plugins.",
                    )
                ]
            }
        )
        from datetime import datetime, timezone

        events = youtube_events(videos, discovered_at=datetime(2026, 8, 31, 14, tzinfo=timezone.utc))
        self.assertEqual(1, len(events))
        validate_event(events[0])
        self.assertEqual("youtube", events[0]["classification"]["section"])


if __name__ == "__main__":
    unittest.main()
