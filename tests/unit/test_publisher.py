from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from radar.io import canonical_json_bytes
from radar.publisher import CSP, publish, render_html, render_rss

ROOT = Path(__file__).resolve().parents[2]


class PublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))

    def test_json_rss_and_html_are_byte_stable(self) -> None:
        self.assertEqual(render_rss(self.feed), render_rss(copy.deepcopy(self.feed)))
        self.assertEqual(render_html(self.feed), render_html(copy.deepcopy(self.feed)))
        self.assertEqual(canonical_json_bytes(self.feed), (ROOT / "tests/fixtures/feed-valid.json").read_bytes())
        ElementTree.fromstring(render_rss(self.feed))

    def test_hostile_plain_text_is_contextually_escaped(self) -> None:
        feed = copy.deepcopy(self.feed)
        feed["events"][0]["title"] = '</h2><script src="https://evil.invalid/x"></script>'
        feed["events"][0]["summary"] = 'Quotes " and <img src=x onerror=alert(1)>'
        page = render_html(feed).decode("utf-8")
        self.assertNotIn("<script src=", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("&lt;script", page)
        self.assertIn(CSP.replace("'", "&#x27;"), page)
        xml = render_rss(feed)
        ElementTree.fromstring(xml)
        self.assertNotIn(b"<script", xml)

    def test_publish_outputs_complete_static_tree_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "dist"
            first = publish(self.feed, destination, source_revision="abc123")
            second = publish(self.feed, destination, source_revision="abc123")
            self.assertEqual(first, second)
            expected = {
                "BUILD-INFO.txt",
                "assets/site.css",
                "archive/2026-08.json",
                "events.json",
                "feed.xml",
                "index.html",
            }
            actual = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
