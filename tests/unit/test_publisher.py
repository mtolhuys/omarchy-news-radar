from __future__ import annotations

import copy
import base64
import json
import tempfile
import unittest
import struct
from pathlib import Path
from xml.etree import ElementTree

from radar.io import canonical_json_bytes
from radar.publisher import CSP, publish, render_html, render_rss
from radar.errors import ValidationError
from radar.images import inspect_raster

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

    def test_allowlisted_images_are_mirrored_and_unsafe_media_is_omitted(self) -> None:
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        feed = copy.deepcopy(self.feed)
        feed["events"][0]["image"] = {
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
            image = published["events"][0]["image"]
            self.assertTrue(image["path"].startswith("assets/images/"))
            self.assertTrue((destination / image["path"]).is_file())
            self.assertIn('<img src="assets/images/', (destination / "index.html").read_text(encoding="utf-8"))

            rejected = publish(
                feed,
                destination,
                image_fetcher=lambda url: (b"<svg><script/></svg>", "image/svg+xml"),
            )
            self.assertEqual(0, rejected["images"])
            self.assertEqual(1, len(rejected["imageFailures"]))
            public = json.loads((destination / "events.json").read_text(encoding="utf-8"))
            self.assertNotIn("image", public["events"][0])

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
