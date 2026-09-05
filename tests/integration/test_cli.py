from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from radar.cli import client_main, repository_main
from radar.client import indicator_model, refresh
from radar.io import atomic_write_json

ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class ClientCliIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        fixture = root / "candidate.json"
        atomic_write_json(
            fixture,
            json.loads(
                (ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8")
            ),
        )
        self.environment = {
            "HOME": str(root / "home"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
            "OMARCHY_NEWS_RADAR_TEST_MODE": "1",
            "OMARCHY_NEWS_RADAR_TEST_FEED": str(fixture),
        }
        refresh(self.environment, now=CLOCK)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_client(self, *arguments: str) -> tuple[int, dict[str, object]]:
        output = io.StringIO()
        with mock.patch.dict(os.environ, self.environment, clear=True):
            with redirect_stdout(output):
                status = client_main(arguments)
        return status, json.loads(output.getvalue())

    def test_indicator_cli_preserves_installed_plugin_projection_context(self) -> None:
        installed_json = '["io.github.mtolhuys.disk-lens"]'
        status, payload = self.run_client(
            "indicator",
            "--installed-json",
            installed_json,
        )

        self.assertEqual(0, status)
        self.assertEqual("ok", payload["status"])
        self.assertEqual(
            indicator_model(
                self.environment,
                now=CLOCK,
                installed_json=installed_json,
            )["unread"],
            payload["unread"],
        )

    def test_indicator_cli_rejects_invalid_installed_plugin_json(self) -> None:
        status, payload = self.run_client(
            "indicator",
            "--installed-json",
            "not-json",
        )

        self.assertEqual(2, status)
        self.assertEqual("failed", payload["status"])
        self.assertEqual("installed plugin IDs are invalid JSON", payload["message"])

    def test_explicit_briefing_and_onboarding_commands_share_one_snapshot(self) -> None:
        code, prepared = self.run_client("ensure-briefing", "--installed-json", '["io.github.mtolhuys.disk-lens"]')
        self.assertEqual(0, code)
        code, projected = self.run_client("project", "--section", "front-page")
        self.assertEqual(0, code)
        self.assertEqual(prepared["briefing"]["id"], projected["briefing"]["id"])
        group = next(event for event in projected["events"] if event["briefingReason"] == "installed")
        code, marked = self.run_client("mark-briefing-group-read", "--briefing-id", projected["briefing"]["id"], "--event-id", group["briefingGroupId"])
        self.assertEqual(0, code)
        self.assertEqual(2, marked["markedRead"])
        code, all_read = self.run_client("mark-briefing-read", "--briefing-id", projected["briefing"]["id"])
        self.assertEqual(0, code)
        self.assertGreaterEqual(all_read["markedRead"], 1)
        code, skipped = self.run_client("start-from-today", "--feed-digest", projected["feedDigest"])
        self.assertEqual(0, code)
        self.assertTrue(skipped["state"]["onboardingComplete"])
        self.assertEqual([], skipped["state"]["briefing"]["groups"])
        code, replacement = self.run_client("new-briefing", "--installed-json", "[]")
        self.assertEqual(0, code)
        self.assertTrue(replacement["briefing"]["complete"])

    def test_browse_cli_keeps_reading_state_and_invalid_action_fails_closed(self) -> None:
        code, browsed = self.run_client("complete-onboarding")
        self.assertEqual(0, code)
        self.assertEqual({}, browsed["state"]["readOverrides"])
        code, failed = self.run_client("mark-briefing-read", "--briefing-id", "invalid")
        self.assertEqual(2, code)
        self.assertEqual("failed", failed["status"])

    def test_insight_and_relevance_commands_keep_personalization_in_local_projection(self) -> None:
        self.environment["OMARCHY_NEWS_RADAR_TEST_INSIGHTS"] = str(ROOT / "tests/fixtures/insights-valid.json")
        code, refreshed = self.run_client("insights-refresh")
        self.assertEqual(0, code)
        self.assertEqual("cached", refreshed["status"])
        facts = '[{"id":"io.github.mtolhuys.disk-lens","version":"0.4.0"}]'
        code, result = self.run_client("project", "--section", "plugins", "--installed-facts-json", facts)
        self.assertEqual(0, code)
        self.assertEqual("behind", result["mySetup"][0]["comparisonState"])
        code, changed = self.run_client("set-relevance", "--kind", "creator", "--id", "github:example", "--mode", "follow")
        self.assertEqual(0, code)
        self.assertEqual({}, changed["state"]["readOverrides"])
        code, independent = self.run_client("insights-project", "--installed-facts-json", facts)
        self.assertEqual(0, code)
        self.assertEqual("github:example", independent["relevanceControls"][0]["id"])
        code, cleared = self.run_client("set-relevance", "--kind", "creator", "--id", "github:example", "--mode", "clear")
        self.assertEqual(0, code)
        self.assertEqual([], cleared["relevanceControls"])

    def test_invalid_installed_facts_and_missing_optional_insights_do_not_reset_state(self) -> None:
        code, before = self.run_client("set-relevance", "--kind", "source", "--id", "marketplace", "--mode", "mute")
        self.assertEqual(0, code)
        code, failed = self.run_client("project", "--section", "plugins", "--installed-facts-json", '[{"id":"../bad","version":"1.0.0"}]')
        self.assertEqual(2, code)
        code, result = self.run_client("insights-project")
        self.assertEqual(0, code)
        self.assertEqual("missing", result["insights"]["status"])
        self.assertEqual(before["state"], result["state"])

    def test_empty_and_unavailable_installed_facts_have_distinct_cli_status(self) -> None:
        for command in (("insights-project",), ("project", "--section", "for-you")):
            code, available = self.run_client(*command, "--installed-facts-json", "[]")
            self.assertEqual(0, code)
            self.assertTrue(available["insights"]["installedFactsAvailable"])
            code, unavailable = self.run_client(*command, "--installed-facts-status", "unavailable")
            self.assertEqual(0, code)
            self.assertFalse(unavailable["insights"]["installedFactsAvailable"])

    def test_site_is_offline_and_fixed_clock_outputs_are_deterministic(self) -> None:
        insights = json.loads((ROOT / "tests/fixtures/insights-valid.json").read_text())
        insights["projects"][0]["image"] = {
            "sourceUrl": "https://plugins.omarchy.org/assets/img/plugins/example.png",
            "alt": "A preview", "credit": "Marketplace", "width": 100, "height": 100,
        }
        base = Path(self.temporary.name)
        insight_path = base / "insights.json"
        atomic_write_json(insight_path, insights)
        first = base / "first"
        second = base / "second"
        with mock.patch("radar.publication_images.fetch_bytes", side_effect=AssertionError("offline site attempted network")) as fetch:
            for destination in (first, second):
                with redirect_stdout(io.StringIO()):
                    code = repository_main(["site", "--feed", str(ROOT / "tests/fixtures/feed-valid.json"),
                                            "--insights", str(insight_path), "--output", str(destination),
                                            "--published-at", "2026-08-31T14:00:00Z"])
                self.assertEqual(0, code)
            fetch.assert_not_called()
        for filename in ("events.json", "insights.json", "index.html", "discover/inspect-disk-space/index.html"):
            self.assertEqual((first / filename).read_bytes(), (second / filename).read_bytes())


if __name__ == "__main__":
    unittest.main()
