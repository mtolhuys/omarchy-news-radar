from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from radar.errors import ValidationError
from radar.io import atomic_write_json
from radar.local_collection import (
    commit_local_source_snapshot,
    local_source_snapshot_path,
    prepare_local_source_snapshot,
)


ROOT = Path(__file__).resolve().parents[2]


class LocalCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.environment = {
            "HOME": str(root / "home"),
            "XDG_CACHE_HOME": str(root / "cache"),
        }
        self.tracked = root / "tracked.json"
        self.output = root / "work" / "source-snapshot.json"
        self.snapshot = json.loads(
            (ROOT / "tests/fixtures/source-snapshot-baseline.json").read_text(
                encoding="utf-8"
            )
        )
        atomic_write_json(self.tracked, self.snapshot)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_private_snapshot_advances_repeated_local_collection(self) -> None:
        first = prepare_local_source_snapshot(
            self.tracked, self.output, self.environment
        )
        self.assertEqual("tracked", first["source"])

        newer = deepcopy(self.snapshot)
        newer["sources"]["marketplace"]["generatedAt"] = "2026-08-31T15:00:00Z"
        atomic_write_json(self.output, newer)
        commit_local_source_snapshot(self.output, self.environment)

        atomic_write_json(self.output, self.snapshot)
        second = prepare_local_source_snapshot(
            self.tracked, self.output, self.environment
        )
        self.assertEqual("private", second["source"])
        self.assertEqual(
            "2026-08-31T15:00:00Z",
            json.loads(self.output.read_text(encoding="utf-8"))["sources"]
            ["marketplace"]["generatedAt"],
        )
        self.assertEqual(
            0o600,
            local_source_snapshot_path(self.environment).stat().st_mode & 0o777,
        )

    def test_invalid_private_snapshot_fails_closed(self) -> None:
        private = local_source_snapshot_path(self.environment)
        private.parent.mkdir(parents=True)
        private.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValidationError):
            prepare_local_source_snapshot(self.tracked, self.output, self.environment)


if __name__ == "__main__":
    unittest.main()
