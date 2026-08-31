from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from radar.errors import LauncherError
from radar.launcher import LauncherPaths, inspect, install, remove

ROOT = Path(__file__).resolve().parents[2]


class LauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.paths = LauncherPaths(
            source_desktop=ROOT / "share/applications/io.github.mtolhuys.news-radar.desktop",
            source_icon=ROOT / "assets/io.github.mtolhuys.news-radar.svg",
            desktop=root / "data/applications/io.github.mtolhuys.news-radar.desktop",
            icon=root / "data/icons/hicolor/scalable/apps/io.github.mtolhuys.news-radar.svg",
            receipt=root / "state/omarchy-news-radar/launcher.json",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_atomic_install_status_update_and_remove(self) -> None:
        self.assertEqual("absent", inspect(self.paths)["state"])
        result = install(self.paths)
        self.assertEqual("installed", result["state"])
        self.assertEqual(0o644, self.paths.desktop.stat().st_mode & 0o777)
        self.assertEqual(0o644, self.paths.icon.stat().st_mode & 0o777)
        self.assertEqual(0o600, self.paths.receipt.stat().st_mode & 0o777)
        self.assertEqual(self.paths.source_desktop.read_bytes(), self.paths.desktop.read_bytes())
        self.assertEqual("installed", inspect(self.paths)["state"])
        self.assertEqual("installed", install(self.paths)["state"])
        removed = remove(self.paths)
        self.assertEqual("absent", removed["state"])
        self.assertEqual(["desktop", "icon"], removed["removed"])
        self.assertFalse(self.paths.receipt.exists())

    def test_install_refuses_unmanaged_or_modified_targets(self) -> None:
        self.paths.desktop.parent.mkdir(parents=True)
        self.paths.desktop.write_text("personal launcher\n", encoding="utf-8")
        with self.assertRaisesRegex(LauncherError, "unmanaged or modified desktop"):
            install(self.paths)
        self.assertEqual("personal launcher\n", self.paths.desktop.read_text(encoding="utf-8"))

        self.paths.desktop.unlink()
        install(self.paths)
        self.paths.desktop.write_text("personal edit\n", encoding="utf-8")
        with self.assertRaisesRegex(LauncherError, "managed desktop target was modified"):
            install(self.paths)
        result = remove(self.paths)
        self.assertEqual("preserved-modified", result["state"])
        self.assertEqual(["desktop"], result["preserved"])
        self.assertEqual("personal edit\n", self.paths.desktop.read_text(encoding="utf-8"))

    def test_symlink_and_invalid_receipt_fail_closed(self) -> None:
        target = Path(self.temporary.name) / "elsewhere"
        target.write_text("safe\n", encoding="utf-8")
        self.paths.desktop.parent.mkdir(parents=True)
        self.paths.desktop.symlink_to(target)
        with self.assertRaisesRegex(LauncherError, "symlinked file"):
            install(self.paths)
        self.assertEqual("safe\n", target.read_text(encoding="utf-8"))

        self.paths.desktop.unlink()
        self.paths.receipt.parent.mkdir(parents=True)
        self.paths.receipt.write_text(json.dumps({"schemaVersion": 99}), encoding="utf-8")
        with self.assertRaisesRegex(LauncherError, "unknown shape"):
            install(self.paths)


if __name__ == "__main__":
    unittest.main()
