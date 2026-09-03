from __future__ import annotations

import unittest

from radar.reading import LIST_SUMMARY_MAX, article_segments, list_summary
from radar.sources.youtube_text import NEUTRAL_SUMMARY


class ReadingSurfaceTests(unittest.TestCase):
    def test_list_summary_skips_link_sludge_and_keeps_leading_prose(self) -> None:
        body = (
            "https://sponsor.example/offer?utm_source=rss\n"
            "Thanks to our sponsor for this issue.\n"
            "Omarchy Quattro is out with a malleable desktop and a growing plugin ecosystem. "
            "A later section walks through patronage, themes, and the new Core Team at length. "
            + ("More official notes. " * 80)
        )
        teaser = list_summary(body, "Omarchy Quattro ships")
        self.assertLessEqual(len(teaser), LIST_SUMMARY_MAX)
        self.assertIn("malleable desktop", teaser)
        self.assertNotIn("http", teaser.casefold())
        self.assertNotIn("sponsor", teaser.casefold())
        self.assertNotIn("More official notes", teaser)
        self.assertGreater(len(body), len(teaser))

    def test_list_summary_falls_back_without_inventing_facts(self) -> None:
        self.assertEqual("Omarchy empty", list_summary("   ", "Omarchy empty"))
        self.assertEqual("Omarchy empty", list_summary(NEUTRAL_SUMMARY, "Omarchy empty"))

    def test_youtube_sanitized_prose_stays_short_on_cards(self) -> None:
        teaser = list_summary(
            "A calm tour of Omarchy Quattro with plugins and keyboard flow. "
            "Later chapters cover installation, themes, and a long marketplace walkthrough.",
            "Omarchy Quattro desktop walkthrough",
        )
        self.assertIn("keyboard flow", teaser)
        self.assertNotIn("marketplace walkthrough", teaser)
        self.assertLessEqual(len(teaser), LIST_SUMMARY_MAX)

    def test_article_segments_keep_validated_https_and_drop_unsafe_hrefs(self) -> None:
        body = (
            "Read the [Quattro announcement](https://omarchy.org/news/2026/08/omarchy-quattro-ships) "
            "and later https://github.com/basecamp/omarchy. "
            "Ignore [xss](javascript:alert(1)) and http://example.com/insecure."
        )
        segments = article_segments(body)
        links = [segment for segment in segments if segment["kind"] == "link"]
        self.assertEqual(
            [
                "https://omarchy.org/news/2026/08/omarchy-quattro-ships",
                "https://github.com/basecamp/omarchy",
            ],
            [segment["url"] for segment in links],
        )
        self.assertEqual("Quattro announcement", links[0]["text"])
        self.assertNotIn("javascript:", "".join(segment.get("url", "") for segment in links))
        teaser = list_summary(body, "Omarchy Quattro ships")
        self.assertIn("Quattro announcement", teaser)
        self.assertNotIn("http", teaser.casefold())
        self.assertNotIn("github.com", teaser.casefold())


if __name__ == "__main__":
    unittest.main()
