from __future__ import annotations

import base64
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from radar.client import projection_model, read_model, refresh
from radar.errors import ValidationError
from radar.local_edition import import_local_edition, marker_path
from radar.io import atomic_write_json
from radar.model import canonical_events
from radar.publisher import publish
from radar.state import feed_path, purge
from radar.sources.youtube import youtube_events

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 31, 14, 5, tzinfo=timezone.utc)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class LocalEditionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.environment = {
            "HOME": str(root / "home"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
        }
        feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))
        feed["events"][0]["image"] = {
            "sourceUrl": "https://plugins.omarchy.org/assets/img/plugins/local.png",
            "alt": "Validated local edition preview",
            "credit": "Plugin marketplace",
            "width": 1,
            "height": 1,
        }
        self.edition = root / "edition"
        publish(
            feed,
            self.edition,
            source_revision="a" * 40,
            image_fetcher=lambda url: (PNG, "image/png"),
        )
        self.published_feed = json.loads((self.edition / "events.json").read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_import_projects_marketplace_image_url_and_refuses_published_downgrade(self) -> None:
        result = import_local_edition(self.edition, self.environment, now=NOW)
        self.assertEqual(6, result["events"])
        self.assertEqual(1, result["images"])
        self.assertEqual("local", read_model(self.environment, now=NOW)["editionMode"])

        projected = projection_model("plugins", "[]", "", self.environment, now=NOW)
        pictured = next(event for event in projected["events"] if "image" in event)
        self.assertEqual(
            "https://plugins.omarchy.org/assets/img/plugins/local.png",
            pictured["imageUrl"],
        )

        with mock.patch("radar.client._fetch_feed", return_value=self.published_feed) as fetch:
            current = refresh(self.environment, now=NOW)
        fetch.assert_called_once()
        self.assertEqual("local-current", current["status"])
        self.assertEqual("local", current["editionMode"])

    def test_newer_published_feed_replaces_local_development_cache(self) -> None:
        import_local_edition(self.edition, self.environment, now=NOW)
        newer = json.loads(json.dumps(self.published_feed))
        newer["generatedAt"] = "2026-08-31T14:04:00Z"
        newer["publishedAt"] = "2026-08-31T14:04:00Z"
        newer["window"]["through"] = "2026-08-31T14:04:00Z"

        with mock.patch("radar.client._fetch_feed", return_value=newer) as fetch:
            current = refresh(self.environment, now=NOW)

        fetch.assert_called_once()
        self.assertEqual("updated", current["status"])
        self.assertEqual("published", current["editionMode"])
        self.assertEqual("published", read_model(self.environment, now=NOW)["editionMode"])
        self.assertEqual("2026-08-31T14:04:00Z", current["feed"]["generatedAt"])


    def test_published_feed_with_youtube_replaces_local_without_it(self) -> None:
        """Local live editions without YouTube adopt an older Forge feed that has it."""
        import_local_edition(self.edition, self.environment, now=NOW)
        self.assertEqual(
            0,
            sum(1 for event in self.published_feed["events"] if event["type"] == "youtube-video"),
        )

        older = json.loads(json.dumps(self.published_feed))
        older["generatedAt"] = "2026-08-31T13:50:00Z"
        older["publishedAt"] = "2026-08-31T13:50:00Z"
        older["window"]["through"] = "2026-08-31T13:50:00Z"
        videos = json.loads((ROOT / "tests/fixtures/youtube-baseline.json").read_text(encoding="utf-8"))["videos"]
        youtube = youtube_events(
            videos,
            discovered_at=datetime(2026, 8, 31, 13, 50, tzinfo=timezone.utc),
        )
        older["events"] = canonical_events(older["events"] + youtube)
        older["sources"] = list(older.get("sources", [])) + [
            {
                "id": "youtube",
                "status": "current",
                "checkedAt": "2026-08-31T13:50:00Z",
                "sourceUrl": "https://www.youtube.com",
            }
        ]

        with mock.patch("radar.client._fetch_feed", return_value=older) as fetch:
            current = refresh(self.environment, now=NOW)

        fetch.assert_called_once()
        self.assertEqual("updated", current["status"])
        self.assertEqual("published", current["editionMode"])
        self.assertGreater(
            sum(1 for event in current["feed"]["events"] if event["type"] == "youtube-video"),
            0,
        )

        # Ordinary D029 downgrade still holds when the published candidate also lacks YouTube.
        import_local_edition(self.edition, self.environment, now=NOW)
        older_without = json.loads(json.dumps(self.published_feed))
        older_without["generatedAt"] = "2026-08-31T13:40:00Z"
        older_without["publishedAt"] = "2026-08-31T13:40:00Z"
        older_without["window"]["through"] = "2026-08-31T13:40:00Z"
        with mock.patch("radar.client._fetch_feed", return_value=older_without) as fetch:
            refused = refresh(self.environment, now=NOW)
        fetch.assert_called_once()
        self.assertEqual("local-current", refused["status"])
        self.assertEqual("local", refused["editionMode"])

    def test_invalid_reimport_preserves_the_complete_previous_edition(self) -> None:
        import_local_edition(self.edition, self.environment, now=NOW)
        before = feed_path(self.environment).read_bytes()
        events = json.loads((self.edition / "events.json").read_text(encoding="utf-8"))
        pictured = next(event for event in events["events"] if "image" in event)
        pictured["image"]["sourceUrl"] = "https://evil.example/assets/img/plugins/local.png"
        (self.edition / "events.json").write_text(json.dumps(events), encoding="utf-8")
        with self.assertRaises(ValidationError):
            import_local_edition(self.edition, self.environment, now=NOW)
        self.assertEqual(before, feed_path(self.environment).read_bytes())
        self.assertTrue(marker_path(self.environment).is_file())

    def test_build_publication_metadata_must_match_the_feed(self) -> None:
        build_info = self.edition / "BUILD-INFO.txt"
        build_info.write_text(
            build_info.read_text(encoding="utf-8").replace(
                "publishedAt=2026-08-31T14:00:00Z",
                "publishedAt=2026-08-31T14:01:00Z",
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValidationError, "publication time"):
            import_local_edition(self.edition, self.environment, now=NOW)

    def test_marker_mismatch_falls_back_to_the_published_refresh_boundary(self) -> None:
        import_local_edition(self.edition, self.environment, now=NOW)
        marker = json.loads(marker_path(self.environment).read_text(encoding="utf-8"))
        marker["feedSha256"] = "0" * 64
        atomic_write_json(marker_path(self.environment), marker)
        self.assertEqual("published", read_model(self.environment, now=NOW)["editionMode"])
        with mock.patch("radar.client._fetch_feed", side_effect=OSError("offline")) as fetch:
            result = refresh(self.environment, now=NOW)
        fetch.assert_called_once()
        self.assertEqual("offline", result["status"])

    def test_purge_removes_local_marker_and_image_assets(self) -> None:
        import_local_edition(self.edition, self.environment, now=NOW)
        removed = purge(self.environment)
        self.assertIn("feed.json", removed)
        self.assertIn("local-edition.json", removed)
        self.assertFalse(marker_path(self.environment).exists())


if __name__ == "__main__":
    unittest.main()
