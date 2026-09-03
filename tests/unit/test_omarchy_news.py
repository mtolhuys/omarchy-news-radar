from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from radar.collector import FixtureInputs, collect_from_fixtures, collect_production, empty_snapshot
from radar.errors import ValidationError
from radar.io import canonical_json_bytes
from radar.model import front_page, project_section
from radar.sources.marketplace import CATALOG_URL
from radar.sources.marketplace_engagement import ENGAGEMENT_URL
from radar.sources.omarchy_news import RSS_URL, diff_news, parse_news_rss
from radar.sources.omarchy_releases import API_URL
from radar.validation import validate_event, validate_feed

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class OmarchyNewsSourceTests(unittest.TestCase):
    def fixture(self, name: str) -> bytes:
        return (ROOT / f"tests/fixtures/{name}").read_bytes()

    def test_parse_strips_markup_and_builds_stable_ids(self) -> None:
        items = parse_news_rss(self.fixture("omarchy-news-baseline.xml"))
        self.assertEqual(
            ["meet-the-omarchy-core-team", "omarchy-quattro-ships"],
            list(items),
        )
        self.assertEqual("Meet the Omarchy Core Team", items["meet-the-omarchy-core-team"]["title"])
        self.assertNotIn("<", items["meet-the-omarchy-core-team"]["summary"])
        self.assertIn("Core Team", items["meet-the-omarchy-core-team"]["summary"])
        self.assertGreater(len(items["meet-the-omarchy-core-team"]["summary"]), 20)
        self.assertIn(
            "[Quattro announcement](https://omarchy.org/news/2026/08/omarchy-quattro-ships)",
            items["meet-the-omarchy-core-team"]["summary"],
        )
        self.assertIn(
            "[the relative news link](https://omarchy.org/news/2026/08/omarchy-quattro-ships)",
            items["meet-the-omarchy-core-team"]["summary"],
        )
        self.assertIn("this script", items["meet-the-omarchy-core-team"]["summary"])
        self.assertNotIn("javascript:", items["meet-the-omarchy-core-team"]["summary"])
        self.assertIn("\n\n", items["meet-the-omarchy-core-team"]["summary"])
        self.assertEqual("2026-08-30T12:00:00Z", items["omarchy-quattro-ships"]["publishedAt"])

    def test_plain_summary_keeps_paragraph_breaks(self) -> None:
        payload = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <item>
      <title>Paragraph spacing</title>
      <guid>https://omarchy.org/news/2026/08/paragraph-spacing</guid>
      <link>https://omarchy.org/news/2026/08/paragraph-spacing</link>
      <pubDate>Sun, 30 Aug 2026 12:00:00 +0000</pubDate>
      <content:encoded><![CDATA[
        <p>First paragraph with a <a href="https://omarchy.org/news/2026/08/omarchy-quattro-ships">link</a>.</p>
        <p>Second paragraph should breathe.</p>
      ]]></content:encoded>
    </item>
  </channel>
</rss>
"""
        items = parse_news_rss(payload.encode("utf-8"))
        summary = items["paragraph-spacing"]["summary"]
        self.assertIn("\n\n", summary)
        self.assertIn("[link](https://omarchy.org/news/2026/08/omarchy-quattro-ships)", summary)
        from radar.validation import normalize_article_summary
        kept = normalize_article_summary(summary, 8000)
        self.assertIn("\n\n", kept)

    def test_diff_emits_only_new_in_window_events(self) -> None:
        baseline = parse_news_rss(self.fixture("omarchy-news-baseline.xml"))
        current = parse_news_rss(self.fixture("omarchy-news-next.xml"))
        events = diff_news(
            baseline,
            current,
            discovered_at=CLOCK,
            window_from=datetime(2026, 6, 2, 14, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(["Patronage opens to everyone"], [event["title"] for event in events])
        event = events[0]
        self.assertEqual("omarchy-news", event["type"])
        self.assertEqual("core", event["classification"]["section"])
        self.assertEqual("routine", event["classification"]["significance"])
        validate_event(event)
        self.assertEqual([], diff_news(current, current, discovered_at=CLOCK, window_from=datetime(2026, 6, 2, tzinfo=timezone.utc)))

    def test_rejects_malformed_foreign_and_unbounded_feeds(self) -> None:
        with self.assertRaises(ValidationError):
            parse_news_rss(b"<html></html>")
        bad = self.fixture("omarchy-news-baseline.xml").replace(
            b"https://omarchy.org/news/2026/08/omarchy-quattro-ships",
            b"https://example.com/news/2026/08/omarchy-quattro-ships",
        )
        with self.assertRaises(ValidationError):
            parse_news_rss(bad)
        root = self.fixture("omarchy-news-baseline.xml").decode("utf-8")
        item = root.split("<item>", 1)[1].rsplit("</item>", 1)[0]
        bloated = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>']
        for index in range(101):
            bloated.append("<item>" + item.replace("omarchy-quattro-ships", f"item-{index}") + "</item>")
        bloated.append("</channel></rss>")
        with self.assertRaises(ValidationError):
            parse_news_rss("\n".join(bloated).encode("utf-8"))

    def test_collector_fail_closed_and_front_page_quota(self) -> None:
        inputs = FixtureInputs(
            ROOT / "tests/fixtures/releases-baseline.json",
            ROOT / "tests/fixtures/catalog-baseline.json",
            ROOT / "tests/fixtures/community",
            ROOT / "content/curation",
            ROOT / "tests/fixtures/engagement-baseline.json",
            omarchy_news=ROOT / "tests/fixtures/omarchy-news-baseline.xml",
        )
        feed, snapshot = collect_from_fixtures(
            inputs,
            previous_snapshot=None,
            now=CLOCK,
            bootstrap_marketplace=True,
        )
        news_events = [event for event in feed["events"] if event["type"] == "omarchy-news"]
        self.assertEqual(2, len(news_events))
        self.assertEqual("core", project_section(feed, "core")[0]["classification"]["section"])
        self.assertTrue(any(event["type"] == "omarchy-news" for event in project_section(feed, "core")))
        front = front_page(feed["events"])
        self.assertLessEqual(sum(1 for event in front if event["type"] == "omarchy-news"), 3)
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
            now=CLOCK,
            bootstrap_marketplace=False,
            failed_sources={"omarchy-news": "timeout"},
        )
        retained = {event["id"] for event in failed_feed["events"] if event["type"] == "omarchy-news"}
        self.assertEqual({event["id"] for event in news_events}, retained)
        self.assertEqual(snapshot["sources"]["omarchy-news"], failed_snapshot["sources"]["omarchy-news"])
        health = next(item for item in failed_feed["sources"] if item["id"] == "omarchy-news")
        self.assertEqual(("failed", "timeout"), (health["status"], health["reason"]))

    def test_production_fetches_canonical_rss(self) -> None:
        release = deepcopy(
            __import__("json").loads((ROOT / "tests/fixtures/releases-baseline.json").read_text(encoding="utf-8"))[0]
        )
        release["draft"] = True
        catalog = (ROOT / "tests/fixtures/catalog-baseline.json").read_bytes()
        engagement = (ROOT / "tests/fixtures/engagement-baseline.json").read_bytes()
        news = self.fixture("omarchy-news-baseline.xml")
        calls: list[str] = []

        def fixture_fetch(url, *, policy, headers=None):  # type: ignore[no-untyped-def]
            calls.append(url)
            if url.startswith(API_URL):
                return canonical_json_bytes([release]), {}, 200
            if url == CATALOG_URL:
                return catalog, {}, 200
            if url == ENGAGEMENT_URL:
                return engagement, {}, 200
            if url == RSS_URL:
                return news, {}, 200
            raise AssertionError(f"unexpected URL: {url}")

        with mock.patch("radar.collector.fetch_bytes", side_effect=fixture_fetch):
            feed, snapshot = collect_production(
                previous_snapshot=empty_snapshot(),
                community_directory=ROOT / "tests/fixtures/community",
                curation_directory=ROOT / "content/curation",
                now=CLOCK,
                bootstrap_marketplace=True,
            )
        self.assertIn(RSS_URL, calls)
        self.assertIn("omarchy-news", snapshot["sources"])
        self.assertTrue(any(event["type"] == "omarchy-news" for event in feed["events"]))


if __name__ == "__main__":
    unittest.main()
