from __future__ import annotations

import copy
import base64
import json
import tempfile
import unittest
import struct
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from radar.io import canonical_json_bytes
from radar.publisher import CSP, publish, render_html, render_rss
from radar.errors import ValidationError
from radar.images import inspect_raster

ROOT = Path(__file__).resolve().parents[2]


class PageElements(HTMLParser):
    def __init__(self, page: bytes) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.feed(page.decode("utf-8"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))

    def attributes(self, tag: str) -> list[dict[str, str | None]]:
        return [attrs for name, attrs in self.elements if name == tag]


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
        target = next(event for event in feed["events"] if event["type"] == "plugin-added")
        target["title"] = '</h2><script src="https://evil.invalid/x"></script>'
        target["summary"] = 'Quotes " and <img src=x onerror=alert(1)>'
        page = render_html(feed).decode("utf-8")
        self.assertNotIn("<script src=", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("&lt;script", page)
        self.assertIn(CSP.replace("'", "&#x27;"), page)
        xml = render_rss(feed)
        ElementTree.fromstring(xml)
        self.assertNotIn(b"<script", xml)

    def test_public_reader_exposes_install_walkthrough_and_feeds_without_active_content(self) -> None:
        page = PageElements(render_html(self.feed))
        anchors = {attrs["href"]: attrs for attrs in page.attributes("a")}
        marketplace = "https://plugins.omarchy.org/plugin.html?id=io.github.mtolhuys.news-radar"
        walkthrough = "https://github.com/mtolhuys/omarchy-news-radar#readme"
        for destination in (marketplace, walkthrough):
            self.assertIn(destination, anchors)
            self.assertEqual("noopener noreferrer external", anchors[destination]["rel"])
        for destination in ("#news", "feed.xml", "events.json"):
            self.assertIn(destination, anchors)
        self.assertEqual("news", page.attributes("main")[0]["id"])
        self.assertEqual("-1", page.attributes("main")[0]["tabindex"])
        self.assertFalse({tag for tag, _ in page.elements} & {"script", "form", "iframe", "video"})
        self.assertFalse(any(name.startswith("on") for _, attrs in page.elements for name in attrs))
        for event in self.feed["events"]:
            destination = event["source"]["url"]
            if destination in anchors:
                self.assertEqual("noopener noreferrer external", anchors[destination]["rel"])

    def test_sharing_metadata_is_fixed_and_uses_existing_public_paths(self) -> None:
        feed = copy.deepcopy(self.feed)
        feed["events"][0]["title"] = 'Remote "title" <cannot> control the page'
        page = PageElements(render_html(feed))
        metadata = {
            attrs.get("name", attrs.get("property")): attrs["content"]
            for attrs in page.attributes("meta")
            if "content" in attrs
        }
        canonical = next(attrs["href"] for attrs in page.attributes("link") if attrs.get("rel") == "canonical")
        self.assertEqual("https://mtolhuijs.nl/news-radar/", canonical)
        self.assertEqual(canonical, metadata["og:url"])
        self.assertEqual("Omarchy News Radar — catch up with what changed", metadata["og:title"])
        self.assertEqual(metadata["og:title"], metadata["twitter:title"])
        self.assertEqual(metadata["description"], metadata["og:description"])
        self.assertEqual(metadata["description"], metadata["twitter:description"])
        self.assertEqual("summary", metadata["twitter:card"])
        self.assertNotIn("og:image", metadata)
        self.assertNotIn("twitter:image", metadata)

    def test_empty_edition_retains_install_and_rss_paths(self) -> None:
        feed = copy.deepcopy(self.feed)
        feed["events"] = []
        page_bytes = render_html(feed)
        page = PageElements(page_bytes)
        self.assertEqual([], page.attributes("article"))
        self.assertIn(b"No stories in this edition yet.", page_bytes)
        self.assertTrue(any(attrs.get("href") == "feed.xml" for attrs in page.attributes("a")))
        self.assertTrue(any(attrs.get("class") == "install" for attrs in page.attributes("a")))

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
            published = json.loads((destination / "events.json").read_text(encoding="utf-8"))
            self.assertEqual(published["generatedAt"], published["publishedAt"])
            self.assertIn(
                f"publishedAt={published['publishedAt']}\n",
                (destination / "BUILD-INFO.txt").read_text(encoding="utf-8"),
            )


    def test_allowlisted_images_pass_through_and_unsafe_media_is_omitted(self) -> None:
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        feed = copy.deepcopy(self.feed)
        # Pin the fixture image on a Front Page story (not verification-changed).
        target = next(event for event in feed["events"] if event["type"] == "plugin-added")
        target["image"] = {
            "sourceUrl": "https://plugins.omarchy.org/assets/img/plugins/fixture.png",
            "alt": "Fixture preview",
            "credit": "Fixture marketplace",
            "width": 1,
            "height": 1,
        }
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "dist"
            result = publish(
                feed,
                destination,
                image_fetcher=lambda url: (png, "image/png"),
            )
            self.assertEqual(1, result["images"])
            published = json.loads((destination / "events.json").read_text(encoding="utf-8"))
            published_target = next(
                event for event in published["events"] if event["type"] == "plugin-added"
            )
            image = published_target["image"]
            self.assertEqual(
                "https://plugins.omarchy.org/assets/img/plugins/fixture.png",
                image["sourceUrl"],
            )
            self.assertNotIn("path", image)
            self.assertFalse((destination / "assets" / "images").exists())
            self.assertIn(
                '<img src="https://plugins.omarchy.org/assets/img/plugins/fixture.png"',
                (destination / "index.html").read_text(encoding="utf-8"),
            )

            rejected = publish(
                feed,
                destination,
                image_fetcher=lambda url: (b"<svg><script/></svg>", "image/svg+xml"),
            )
            self.assertEqual(0, rejected["images"])
            self.assertEqual(1, len(rejected["imageFailures"]))
            public = json.loads((destination / "events.json").read_text(encoding="utf-8"))
            public_target = next(event for event in public["events"] if event["type"] == "plugin-added")
            self.assertNotIn("image", public_target)


    def test_raster_inspector_rejects_truncated_jpeg_and_animated_webp(self) -> None:
        with self.assertRaisesRegex(ValidationError, "JPEG ending"):
            inspect_raster(b"\xff\xd8\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00", "image/jpeg")

        vp8x = bytes([0x02, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        vp8x_chunk = b"VP8X" + struct.pack("<I", len(vp8x)) + vp8x
        anim_payload = b"\x00" * 6
        anim_chunk = b"ANIM" + struct.pack("<I", len(anim_payload)) + anim_payload
        body = b"WEBP" + vp8x_chunk + anim_chunk
        animated = b"RIFF" + struct.pack("<I", len(body)) + body
        with self.assertRaisesRegex(ValidationError, "animated WebP"):
            inspect_raster(animated, "image/webp")


if __name__ == "__main__":
    unittest.main()
