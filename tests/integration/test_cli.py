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

from radar.cli import client_main
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


if __name__ == "__main__":
    unittest.main()
