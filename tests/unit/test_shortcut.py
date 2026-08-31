from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from radar.errors import ShortcutError
from radar.shortcut import (
    DEFAULT_LINE,
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
        self.omarchy = root / "omarchy"
        self.bindings = self.home / ".config/hypr/bindings.lua"
        self.default = self.omarchy / "default/hypr/bindings/applications.lua"
        self.bindings.parent.mkdir(parents=True)
        self.default.parent.mkdir(parents=True)
        self.original = b"-- personal bytes stay exact\n-- unicode: newspaper\n"
        self.bindings.write_bytes(self.original)
        self.default.write_text(DEFAULT_LINE + "\n", encoding="utf-8")
        self.environment = {"HOME": str(self.home), "OMARCHY_PATH": str(self.omarchy)}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def live(self):
        text = self.bindings.read_text(encoding="utf-8")
        if MANAGED_BLOCK in text:
            return [{"key": "N", "modmask": 65, "description": RADAR_DESCRIPTION, "dispatcher": "exec", "arg": RADAR_COMMAND}]
        return [{"key": "N", "modmask": 65, "description": "Editor", "dispatcher": "exec", "arg": "omarchy-launch-editor"}]

    def test_status_and_plain_install_are_read_only_preview(self) -> None:
        with mock.patch("radar.shortcut._live_bindings", side_effect=self.live):
            status = inspect(self.environment)
            self.assertEqual("default-editor", status.classification)
            result = install(replace_default_editor=False, environment=self.environment)
        self.assertEqual("authorization-required", result["status"])
        self.assertEqual(self.original, self.bindings.read_bytes())
        self.assertIn("--replace-default-editor", result["authorizationCommand"])

    def test_explicit_install_preserves_surrounding_bytes_and_remove_restores(self) -> None:
        with (
            mock.patch("radar.shortcut._live_bindings", side_effect=self.live),
            mock.patch("radar.shortcut._reload_expect"),
        ):
            installed = install(replace_default_editor=True, environment=self.environment)
            self.assertEqual("installed", installed["status"])
            candidate = self.bindings.read_bytes()
            self.assertTrue(candidate.startswith(self.original))
            self.assertEqual(1, candidate.decode("utf-8").count(MANAGED_BLOCK))
            unchanged = install(replace_default_editor=True, environment=self.environment)
            self.assertEqual("unchanged", unchanged["status"])
            removed = remove(self.environment)
            self.assertEqual("removed", removed["status"])
        self.assertEqual(self.original, self.bindings.read_bytes())
        backups = list(self.bindings.parent.glob("bindings.lua.news-radar-backup-*"))
        self.assertGreaterEqual(len(backups), 2)
        self.assertTrue(all((path.stat().st_mode & 0o777) == 0o600 for path in backups))

    def test_personal_multiple_and_unknown_conflicts_are_refused(self) -> None:
        self.bindings.write_text('hl.unbind("SUPER + SHIFT + N")\no.bind("SUPER + SHIFT + N", "Mine", "mine")\n', encoding="utf-8")
        with mock.patch("radar.shortcut._live_bindings", return_value=[{"key": "N", "modmask": 65, "description": "Mine"}]):
            self.assertEqual("personal-conflict", inspect(self.environment).classification)
            with self.assertRaises(ShortcutError):
                install(replace_default_editor=True, environment=self.environment)
        self.bindings.write_bytes(self.original)
        multiple = [
            {"key": "N", "modmask": 65, "description": "Editor"},
            {"key": "N", "modmask": 65, "description": "Other"},
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
                install(replace_default_editor=True, environment=self.environment)
        self.assertEqual(self.original, self.bindings.read_bytes())

    def test_named_replacement_is_not_a_general_force_flag(self) -> None:
        with mock.patch("radar.shortcut._live_bindings", return_value=[]):
            with self.assertRaisesRegex(ShortcutError, "applies only"):
                install(replace_default_editor=True, environment=self.environment)


if __name__ == "__main__":
    unittest.main()
