from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.freshness import PAGES_CACHE_MAX_SECONDS, PUBLICATION_STALE_SECONDS, edition_timing
from radar.shortcut import RADAR_COMMAND
from scripts.validate_repo import validate_release_documentation


ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class ReleaseContractTests(unittest.TestCase):
    def test_checkout_identity_and_documented_release_status_agree(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        version = manifest["version"]
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        validate_release_documentation(version, readme, ROOT / "docs" / "release-notes")
        self.assertIn(
            f'BUILD_ID = "news-radar-{version}"',
            (ROOT / "radar" / "constants.py").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f'__version__ = "{version}"',
            (ROOT / "radar" / "__init__.py").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f'news-radar-{version}+identity-2',
            (ROOT / "src" / "Panel.qml").read_text(encoding="utf-8"),
        )

    def test_documentation_accepts_a_published_checkout_and_a_later_local_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory)
            (notes / "0.4.16.md").write_text("# Omarchy News Radar 0.4.16\n", encoding="utf-8")
            readme = "## Install the published v0.4.16\n\nVersion `0.4.16` is the current release.\n"
            validate_release_documentation("0.4.16", readme, notes)
            (notes / "0.5.0.md").write_text(
                "# Omarchy News Radar 0.5.0\n\nStatus: local candidate; not published.\n", encoding="utf-8"
            )
            candidate_readme = readme + "\nVersion `0.5.0` is a local candidate, not a published release.\n"
            validate_release_documentation("0.5.0", candidate_readme, notes)

    def test_candidate_cannot_impersonate_the_published_install_or_lack_matching_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory)
            (notes / "0.4.16.md").write_text("# Omarchy News Radar 0.4.16\n", encoding="utf-8")
            (notes / "0.5.0.md").write_text(
                "# Omarchy News Radar 0.5.0\n\nStatus: local candidate; not published.\n", encoding="utf-8"
            )
            readme = (
                "## Install the published v0.4.16\n\nVersion `0.4.16` is the current release.\n"
                "\nVersion `0.5.0` is a local candidate, not a published release.\n"
            )
            invalid_readmes = (
                readme.replace("Install the published v0.4.16", "Install the published v0.5.0"),
                readme + "\n## Install the published v0.5.0\n",
                readme.replace("Version `0.5.0` is a local candidate, not a published release.\n", ""),
                readme.replace("Version `0.5.0` is a local candidate", "Version `0.5.1` is a local candidate"),
                readme + "\nVersion `0.5.0` is the current release.\n",
                readme + "\nVersion `0.5.1` is a local candidate, not a published release.\n",
            )
            for invalid_readme in invalid_readmes:
                with self.subTest(readme=invalid_readme), self.assertRaises(SystemExit):
                    validate_release_documentation("0.5.0", invalid_readme, notes)

    def test_candidate_notes_must_match_identity_and_state_unpublished_status(self) -> None:
        readme = (
            "## Install the published v0.4.16\n\nVersion `0.4.16` is the current release.\n"
            "\nVersion `0.5.0` is a local candidate, not a published release.\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory)
            (notes / "0.4.16.md").write_text("# Omarchy News Radar 0.4.16\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate_release_documentation("0.5.0", readme, notes)
            for candidate_notes in (
                "# Omarchy News Radar 0.4.16\n\nStatus: local candidate; not published.\n",
                "# Omarchy News Radar 0.5.0\n\nReady to install.\n",
            ):
                with self.subTest(notes=candidate_notes):
                    (notes / "0.5.0.md").write_text(candidate_notes, encoding="utf-8")
                    with self.assertRaises(SystemExit):
                        validate_release_documentation("0.5.0", readme, notes)

    def test_promoting_candidate_requires_updating_notes_and_public_status_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory)
            path = notes / "0.5.0.md"
            path.write_text("# Omarchy News Radar 0.5.0\n\nStatus: local candidate; not published.\n", encoding="utf-8")
            readme = "## Install the published v0.5.0\n\nVersion `0.5.0` is the current release.\n"
            with self.assertRaises(SystemExit):
                validate_release_documentation("0.5.0", readme, notes)
            path.write_text("# Omarchy News Radar 0.5.0\n", encoding="utf-8")
            validate_release_documentation("0.5.0", readme, notes)

    def test_forge_owns_publication_not_github_actions(self) -> None:
        workflows = ROOT / ".github/workflows"
        self.assertFalse((workflows / "publication.yml").exists())
        self.assertTrue((workflows / "test.yml").is_file())
        constants = (ROOT / "radar" / "constants.py").read_text(encoding="utf-8")
        self.assertIn('FEED_URL = "https://mtolhuijs.nl/news-radar/events.json"', constants)
        self.assertIn('FEED_ORIGIN = "https://mtolhuijs.nl"', constants)

    def test_every_public_launcher_uses_summon_activation(self) -> None:
        command = "omarchy-shell shell summon io.github.mtolhuys.news-radar"
        self.assertEqual(command, RADAR_COMMAND)
        self.assertIn(command, (ROOT / "src/BarWidget.qml").read_text(encoding="utf-8"))
        self.assertIn(command, (ROOT / "share/applications/io.github.mtolhuys.news-radar.desktop").read_text(encoding="utf-8"))

    def test_local_source_state_advances_only_after_complete_import(self) -> None:
        script = (ROOT / "scripts/sync_local_plugin.sh").read_text(encoding="utf-8")
        self.assertIn("prepare-local-source-snapshot", script)
        self.assertIn("commit-local-source-snapshot", script)
        self.assertLess(
            script.index("import-local-edition"),
            script.index("commit-local-source-snapshot"),
        )

    def test_publication_staleness_boundary_and_distinct_timestamps(self) -> None:
        feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))
        feed["publishedAt"] = "2026-08-31T14:01:00Z"
        for source in feed["sources"]:
            source["checkedAt"] = "2026-08-31T13:59:55Z"

        boundary = edition_timing(
            feed,
            now=CLOCK + timedelta(minutes=91),
            cached_at=CLOCK + timedelta(minutes=2),
        )
        self.assertFalse(boundary["publisherStale"])
        self.assertEqual(PUBLICATION_STALE_SECONDS, boundary["publicationAgeSeconds"])
        self.assertEqual(600, PAGES_CACHE_MAX_SECONDS)
        self.assertEqual("2026-08-31T13:59:55Z", boundary["latestSourceCheckedAt"])
        self.assertEqual("2026-08-31T14:00:00Z", boundary["collectedAt"])
        self.assertEqual("2026-08-31T14:01:00Z", boundary["publishedAt"])
        self.assertEqual("2026-08-31T14:02:00Z", boundary["cachedAt"])

        stale = edition_timing(
            feed,
            now=CLOCK + timedelta(minutes=91, seconds=1),
            cached_at=CLOCK + timedelta(minutes=2),
        )
        self.assertTrue(stale["publisherStale"])
        self.assertEqual(PUBLICATION_STALE_SECONDS + 1, stale["publicationAgeSeconds"])

    def test_legacy_feed_uses_an_explicit_publication_time_fallback(self) -> None:
        feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))
        timing = edition_timing(feed, now=CLOCK)
        self.assertTrue(timing["publishedAtInferred"])
        self.assertEqual(feed["generatedAt"], timing["publishedAt"])


if __name__ == "__main__":
    unittest.main()
