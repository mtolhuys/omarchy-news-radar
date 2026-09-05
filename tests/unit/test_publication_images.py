"""Optional previews cannot multiply network work or hold news in an endless queue."""

import base64
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from radar.publication_images import materialize_images

ROOT = Path(__file__).resolve().parents[2]
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class PublicationImageTests(unittest.TestCase):
    def setUp(self):
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text())
        for event in self.feed["events"]:
            event["image"] = {"sourceUrl": "https://plugins.omarchy.org/assets/img/plugins/shared.png",
                              "alt": "Marketplace preview", "credit": "Marketplace", "width": 1, "height": 1}

    def test_repeated_url_is_fetched_once_and_each_dimension_claim_is_checked(self):
        self.feed["events"][0]["image"]["width"] = 2
        fetch = Mock(return_value=(PNG, "image/png"))
        output, failures = materialize_images(self.feed, Path("unused"), image_fetcher=fetch)
        fetch.assert_called_once()
        self.assertEqual(1, len(failures))
        wrong = self.feed["events"][0]["id"]
        self.assertNotIn("image", next(item for item in output["events"] if item["id"] == wrong))
        self.assertTrue(all("image" in item for item in output["events"] if item["id"] != wrong))

    def test_exhausted_budget_omits_previews_and_preserves_every_story(self):
        fetch = Mock(side_effect=AssertionError("no queued image should start after the deadline"))
        with patch("radar.publication_images.IMAGE_INSPECTION_SECONDS", 0):
            output, failures = materialize_images(self.feed, Path("unused"), image_fetcher=fetch)
        fetch.assert_not_called()
        self.assertEqual({item["id"] for item in self.feed["events"]}, {item["id"] for item in output["events"]})
        self.assertTrue(all("image" not in item for item in output["events"]))
        self.assertEqual(len(self.feed["events"]), len(failures))
