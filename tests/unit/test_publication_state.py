from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar.errors import ValidationError
from radar.io import atomic_write_json
from radar.publication_state import (
    audit_marketplace_additions,
    migrate_legacy_source_snapshot,
    restore_publication_source_snapshot,
)


ROOT = Path(__file__).resolve().parents[2]
CLOCK = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class PublicationStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.previous = root / "previous.json"
        self.tracked = root / "tracked.json"
        self.output = root / "output.json"
        self.snapshot = json.loads(
            (ROOT / "tests/fixtures/source-snapshot-baseline.json").read_text(
                encoding="utf-8"
            )
        )
        self.snapshot["sources"]["marketplace"]["generatedAt"] = "2026-08-31T14:00:00Z"
        atomic_write_json(self.tracked, self.snapshot)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_current_previous_deployment_is_always_authoritative(self) -> None:
        previous = deepcopy(self.snapshot)
        previous["events"] = []
        atomic_write_json(self.previous, previous)
        result = restore_publication_source_snapshot(
            self.previous, self.tracked, self.output, now=CLOCK
        )
        self.assertEqual("previous-deployment", result["source"])
        self.assertEqual([], json.loads(self.output.read_text(encoding="utf-8"))["events"])

    def test_legacy_state_allows_one_fresh_tracked_transition(self) -> None:
        legacy = deepcopy(self.snapshot)
        legacy["schemaVersion"] = 1
        atomic_write_json(self.previous, legacy)
        result = restore_publication_source_snapshot(
            self.previous, self.tracked, self.output, now=CLOCK
        )
        self.assertEqual("tracked-transition", result["source"])
        self.assertEqual(2, json.loads(self.output.read_text(encoding="utf-8"))["schemaVersion"])

    def test_legacy_migration_drops_retimed_diff_events_only(self) -> None:
        legacy = deepcopy(self.snapshot)
        legacy["schemaVersion"] = 1
        legacy["events"][0]["type"] = "plugin-verification-changed"
        atomic_write_json(self.previous, legacy)
        result = migrate_legacy_source_snapshot(self.previous, self.output)
        migrated = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(2, migrated["schemaVersion"])
        self.assertEqual(1, result["removed"])
        self.assertNotIn(
            "plugin-verification-changed",
            {event["type"] for event in migrated["events"]},
        )

    def test_legacy_transition_refuses_a_stale_or_invalid_seed(self) -> None:
        legacy = deepcopy(self.snapshot)
        legacy["schemaVersion"] = 1
        atomic_write_json(self.previous, legacy)
        with self.assertRaisesRegex(ValidationError, "not fresh"):
            restore_publication_source_snapshot(
                self.previous,
                self.tracked,
                self.output,
                now=CLOCK + timedelta(hours=6, seconds=1),
            )
        atomic_write_json(self.previous, {"schemaVersion": 99})
        with self.assertRaisesRegex(ValidationError, "unsupported"):
            restore_publication_source_snapshot(
                self.previous, self.tracked, self.output, now=CLOCK
            )

    def test_marketplace_audit_requires_news_for_every_new_plugin(self) -> None:
        previous = deepcopy(self.snapshot)
        atomic_write_json(self.previous, previous)
        current = deepcopy(self.snapshot)
        current["sources"]["marketplace"]["plugins"]["org.example.notes"] = deepcopy(
            current["sources"]["marketplace"]["plugins"]["org.example.focus"]
        )
        feed = json.loads((ROOT / "tests/fixtures/feed-valid.json").read_text(encoding="utf-8"))
        addition = next(event for event in feed["events"] if event["type"] == "plugin-added")
        current["events"].append(addition)
        current["events"].sort(
            key=lambda event: (event["occurredAt"], event["id"]), reverse=True
        )
        atomic_write_json(self.tracked, current)
        result = audit_marketplace_additions(self.previous, self.tracked)
        self.assertEqual(1, result["newPlugins"])
        self.assertEqual(1, result["representedNewPlugins"])

        missing = deepcopy(current)
        missing["events"].remove(addition)
        atomic_write_json(self.output, missing)
        with self.assertRaisesRegex(ValidationError, "lack addition stories"):
            audit_marketplace_additions(self.previous, self.output)

    def test_marketplace_audit_accepts_legacy_previous_state_and_rejects_time_reversal(self) -> None:
        legacy = deepcopy(self.snapshot)
        legacy["schemaVersion"] = 1
        atomic_write_json(self.previous, legacy)
        result = audit_marketplace_additions(self.previous, self.tracked)
        self.assertEqual(0, result["newPlugins"])

        current = deepcopy(self.snapshot)
        current["sources"]["marketplace"]["generatedAt"] = "2026-08-31T13:59:59Z"
        atomic_write_json(self.output, current)
        with self.assertRaisesRegex(ValidationError, "moved backwards"):
            audit_marketplace_additions(self.previous, self.output)


if __name__ == "__main__":
    unittest.main()
