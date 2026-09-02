from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.freshness import PAGES_CACHE_MAX_SECONDS, PUBLICATION_STALE_SECONDS, edition_timing
from radar.shortcut import RADAR_COMMAND


ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class ReleaseContractTests(unittest.TestCase):
    def test_schedule_has_four_off_peak_recovery_opportunities_per_hour(self) -> None:
        workflow = (ROOT / ".github/workflows/publication.yml").read_text(encoding="utf-8")
        for minute in (8, 23, 38, 53):
            self.assertIn(f'cron: "{minute} * * * *"', workflow)
        self.assertNotIn('cron: "8,23,38,53 * * * *"', workflow)
        self.assertNotIn('cron: "17 * * * *"', workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093", workflow)
        self.assertIn("--status success", workflow)
        self.assertIn("news-radar-source-snapshot-${{ steps.previous_state.outputs.run_id }}", workflow)
        self.assertIn("refusing to replay the committed baseline", workflow)
        self.assertIn("audit-marketplace-additions", workflow)
        self.assertIn("Prove every new marketplace plugin became news", workflow)

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
