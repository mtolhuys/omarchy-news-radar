from __future__ import annotations

import unittest

from radar.reading import LIST_SUMMARY_MAX, list_summary
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


if __name__ == "__main__":
    unittest.main()
