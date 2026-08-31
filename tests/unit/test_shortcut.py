from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from radar.errors import ShortcutError
from radar.shortcut import (
    MANAGED_BLOCK,
    RADAR_COMMAND,
    RADAR_DESCRIPTION,
    inspect,
    install,
    remove,
)


class ShortcutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.home = root / "home"
        self.bindings = self.home / ".config/hypr/bindings.lua"
        self.bindings.parent.mkdir(parents=True)
        self.original = b"-- personal bytes stay exact\n-- unicode: newspaper\n"
        self.bindings.write_bytes(self.original)
        self.environment = {"HOME": str(self.home)}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def live(self):
        text = self.bindings.read_text(encoding="utf-8")
        if MANAGED_BLOCK in text:
            return [{"key": "N", "modmask": 72, "description": RADAR_DESCRIPTION, "dispatcher": "exec", "arg": RADAR_COMMAND}]
        return []

    def test_status_reports_free_without_mutation(self) -> None:
        with mock.patch("radar.shortcut._live_bindings", side_effect=self.live):
            status = inspect(self.environment)
        self.assertEqual("free", status.classification)
        self.assertEqual(self.original, self.bindings.read_bytes())

    def test_install_preserves_surrounding_bytes_and_remove_releases_chord(self) -> None:
        with (
            mock.patch("radar.shortcut._live_bindings", side_effect=self.live),
            mock.patch("radar.shortcut._reload_expect"),
        ):
            installed = install(self.environment)
            self.assertEqual("installed", installed["status"])
            candidate = self.bindings.read_bytes()
            self.assertTrue(candidate.startswith(self.original))
            self.assertEqual(1, candidate.decode("utf-8").count(MANAGED_BLOCK))
            self.assertNotIn(b"hl.unbind", candidate)
            unchanged = install(self.environment)
            self.assertEqual("unchanged", unchanged["status"])
            removed = remove(self.environment)
            self.assertEqual("removed", removed["status"])
        self.assertEqual(self.original, self.bindings.read_bytes())
        backups = list(self.bindings.parent.glob("bindings.lua.news-radar-backup-*"))
        self.assertGreaterEqual(len(backups), 2)
        self.assertTrue(all((path.stat().st_mode & 0o777) == 0o600 for path in backups))

    def test_personal_multiple_and_unknown_conflicts_are_refused(self) -> None:
        self.bindings.write_text('o.bind("SUPER+ALT + N", "Mine", "mine")\n', encoding="utf-8")
        with mock.patch("radar.shortcut._live_bindings", return_value=[{"key": "N", "modmask": 72, "description": "Mine"}]):
            self.assertEqual("personal-conflict", inspect(self.environment).classification)
            with self.assertRaises(ShortcutError):
                install(self.environment)
        self.bindings.write_bytes(self.original)
        multiple = [
            {"key": "N", "modmask": 72, "description": "One"},
            {"key": "N", "modmask": 72, "description": "Other"},
        ]
        with mock.patch("radar.shortcut._live_bindings", return_value=multiple):
            self.assertEqual("ambiguous", inspect(self.environment).classification)

    def test_symlink_and_edited_block_are_refused(self) -> None:
        target = self.bindings.parent / "real.lua"
        target.write_bytes(self.original)
        self.bindings.unlink()
        self.bindings.symlink_to(target)
        with self.assertRaises(ShortcutError):
            inspect(self.environment)
        self.bindings.unlink()
        self.bindings.write_text(self.original.decode() + MANAGED_BLOCK.replace("Omarchy News Radar", "Edited"), encoding="utf-8")
        with mock.patch("radar.shortcut._live_bindings", return_value=self.live()):
            self.assertEqual("ambiguous", inspect(self.environment).classification)
            with self.assertRaises(ShortcutError):
                remove(self.environment)

    def test_reload_failure_rolls_back_exact_original(self) -> None:
        with (
            mock.patch("radar.shortcut._live_bindings", side_effect=self.live),
            mock.patch("radar.shortcut._reload_expect", side_effect=[ShortcutError("config error"), None]),
        ):
            with self.assertRaisesRegex(ShortcutError, "original bindings were restored"):
                install(self.environment)
        self.assertEqual(self.original, self.bindings.read_bytes())

    def test_live_conflict_is_refused_without_a_force_path(self) -> None:
        with mock.patch("radar.shortcut._live_bindings", return_value=[{"key": "N", "modmask": 72, "description": "Other"}]):
            self.assertEqual("personal-conflict", inspect(self.environment).classification)
            with self.assertRaises(ShortcutError):
                install(self.environment)


if __name__ == "__main__":
    unittest.main()
