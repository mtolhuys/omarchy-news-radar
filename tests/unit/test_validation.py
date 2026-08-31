from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.errors import ValidationError
from radar.model import event_id, front_page, project_section
from radar.validation import normalize_text, validate_feed, validate_https_url

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))

    def test_valid_fixture_and_deterministic_id(self) -> None:
        validated = validate_feed(self.feed, now=NOW)
        self.assertEqual(6, len(validated["events"]))
        expected = "evt_ed4cdd2800453c22ba31be9c"
        self.assertEqual(
            expected,
            event_id(
                "plugin-released",
                "plugin",
                "io.github.mtolhuys.disk-lens",
                "version:0.4.0->0.4.1",
                "https://github.com/mtolhuys/omarchy-disk-lens/releases/tag/v0.4.1",
            ),
        )

    def test_rejects_schema_duplicate_order_enum_and_future(self) -> None:
        cases = []
        unsupported = copy.deepcopy(self.feed)
        unsupported["schemaVersion"] = 2
        cases.append(unsupported)
        duplicate = copy.deepcopy(self.feed)
        duplicate["events"].append(copy.deepcopy(duplicate["events"][-1]))
        cases.append(duplicate)
        unordered = copy.deepcopy(self.feed)
        unordered["events"] = list(reversed(unordered["events"]))
        cases.append(unordered)
        enum = copy.deepcopy(self.feed)
        enum["events"][0]["classification"]["significance"] = "popular"
        cases.append(enum)
        future = copy.deepcopy(self.feed)
        future["generatedAt"] = "2026-08-31T14:06:00Z"
        cases.append(future)
        for candidate in cases:
            with self.subTest(candidate=candidate.get("schemaVersion")):
                with self.assertRaises(ValidationError):
                    validate_feed(candidate, now=NOW)

    def test_remote_text_is_repaired_as_plain_text(self) -> None:
        self.assertEqual("hello world", normalize_text(" hello\x1b\nworld ", 40))
        hostile = copy.deepcopy(self.feed)
        hostile["events"][0]["title"] = "<script>alert(1)</script>"
        validated = validate_feed(hostile, now=NOW)
        self.assertEqual("<script>alert(1)</script>", validated["events"][0]["title"])

    def test_url_boundary(self) -> None:
        for value in (
            "http://github.com/example/project",
            "https://user:secret@example.com/path",
            "https://localhost/path",
            "https://127.0.0.1/path",
            "https://example.com:444/path",
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_https_url(value)
        self.assertEqual("https://github.com/example/project", validate_https_url("https://github.com/example/project"))

    def test_public_feed_accepts_only_content_addressed_same_origin_image_paths(self) -> None:
        internal = copy.deepcopy(self.feed)
        internal["events"][0]["image"] = {
            "sourceUrl": "https://plugins.omarchy.org/assets/img/plugins/fixture.webp",
            "alt": "Fixture preview",
            "credit": "Marketplace",
            "width": 720,
            "height": 405,
        }
        self.assertIn("image", validate_feed(internal, now=NOW)["events"][0])
        with self.assertRaises(ValidationError):
            validate_feed(internal, now=NOW, public_only=True)
        unsafe_path = copy.deepcopy(internal)
        unsafe_path["events"][0]["image"]["sourceUrl"] = "https://plugins.omarchy.org/unrelated/fixture.webp"
        with self.assertRaises(ValidationError):
            validate_feed(unsafe_path, now=NOW)
        internal["events"][0]["image"].pop("sourceUrl")
        internal["events"][0]["image"]["path"] = "assets/images/" + "a" * 64 + ".webp"
        self.assertIn("image", validate_feed(internal, now=NOW, public_only=True)["events"][0])

    def test_front_page_and_private_projections_are_deterministic(self) -> None:
        validated = validate_feed(self.feed, now=NOW)
        front = front_page(validated["events"], installed_plugin_ids=["io.github.mtolhuys.disk-lens"])
        self.assertEqual("omarchy-released", next(item for item in front if item["type"] == "omarchy-released")["type"])
        personalized = project_section(validated, "for-you", installed_plugin_ids=["io.github.mtolhuys.disk-lens"])
        self.assertEqual(2, len(personalized))
        self.assertTrue(all(item["entity"]["id"] == "io.github.mtolhuys.disk-lens" for item in personalized))


if __name__ == "__main__":
    unittest.main()
