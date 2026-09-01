from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from radar.errors import ShortcutError
from radar.shortcut_cli import main as shortcut_main
from radar.shortcut import (
    LEGACY_MANAGED_BLOCK,
    MANAGED_BLOCK,
    RADAR_COMMAND,
    RADAR_DESCRIPTION,
    ShortcutStatus,
    inspect,
    install,
    migrate_owned_legacy,
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
        if MANAGED_BLOCK in text or LEGACY_MANAGED_BLOCK in text:
            return [{"key": "N", "modmask": 72, "description": RADAR_DESCRIPTION, "dispatcher": "exec", "arg": RADAR_COMMAND}]
        return []

    def test_status_reports_free_without_mutation(self) -> None:
        with mock.patch("radar.shortcut._live_bindings", side_effect=self.live):
            status = inspect(self.environment)
        self.assertEqual("free", status.classification)
        self.assertEqual(self.original, self.bindings.read_bytes())

    def test_cli_success_uses_the_shared_helper_protocol(self) -> None:
        with (
            mock.patch("radar.shortcut_cli.inspect") as inspect_mock,
            redirect_stdout(io.StringIO()) as output,
        ):
            inspect_mock.return_value = ShortcutStatus("free", self.bindings, (), "free")
            self.assertEqual(0, shortcut_main(["status"]))
        result = json.loads(output.getvalue())
        self.assertEqual(1, result["protocolVersion"])
        self.assertEqual("ok", result["status"])

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

    def test_exact_legacy_owned_block_is_reported_and_migrated(self) -> None:
        self.bindings.write_bytes(self.original + LEGACY_MANAGED_BLOCK.encode("utf-8"))
        with (
            mock.patch("radar.shortcut._live_bindings", side_effect=self.live),
            mock.patch("radar.shortcut._reload_expect"),
        ):
            before = inspect(self.environment)
            self.assertEqual("owned-legacy", before.classification)
            self.assertIn("migration", before.message.lower())
            migrated = install(self.environment)
            self.assertEqual("migrated", migrated["status"])
            self.assertEqual("owned", migrated["classification"])

        candidate = self.bindings.read_bytes()
        self.assertTrue(candidate.startswith(self.original))
        self.assertEqual(1, candidate.decode("utf-8").count(MANAGED_BLOCK))
        self.assertNotIn(LEGACY_MANAGED_BLOCK.encode("utf-8"), candidate)

    def test_owned_legacy_migration_command_repairs_only_the_legacy_block(self) -> None:
        self.bindings.write_bytes(self.original + LEGACY_MANAGED_BLOCK.encode("utf-8"))
        with (
            mock.patch("radar.shortcut._live_bindings", side_effect=self.live),
            mock.patch("radar.shortcut._reload_expect"),
        ):
            migrated = migrate_owned_legacy(self.environment)
        self.assertEqual("migrated", migrated["status"])
        self.assertIn(MANAGED_BLOCK.encode("utf-8"), self.bindings.read_bytes())
        self.assertNotIn(LEGACY_MANAGED_BLOCK.encode("utf-8"), self.bindings.read_bytes())

    def test_owned_legacy_migration_command_never_installs_a_free_binding(self) -> None:
        with mock.patch("radar.shortcut._live_bindings", side_effect=self.live):
            result = migrate_owned_legacy(self.environment)
        self.assertEqual("not-needed", result["status"])
        self.assertEqual("free", result["classification"])
        self.assertEqual(self.original, self.bindings.read_bytes())

    def test_owned_legacy_migration_command_never_changes_personal_or_edited_bindings(self) -> None:
        personal = b'o.bind("SUPER + ALT + N", "Mine", "mine")\n'
        self.bindings.write_bytes(personal)
        with mock.patch(
            "radar.shortcut._live_bindings",
            return_value=[{"key": "N", "modmask": 72, "description": "Mine"}],
        ):
            result = migrate_owned_legacy(self.environment)
        self.assertEqual("not-needed", result["status"])
        self.assertEqual("personal-conflict", result["classification"])
        self.assertEqual(personal, self.bindings.read_bytes())

        edited = self.original + LEGACY_MANAGED_BLOCK.replace(
            "Omarchy News Radar", "Personal Radar"
        ).encode("utf-8")
        self.bindings.write_bytes(edited)
        with mock.patch("radar.shortcut._live_bindings", return_value=self.live()):
            result = migrate_owned_legacy(self.environment)
        self.assertEqual("not-needed", result["status"])
        self.assertEqual("ambiguous", result["classification"])
        self.assertEqual(edited, self.bindings.read_bytes())

    def test_legacy_migration_failure_restores_exact_original(self) -> None:
        legacy = self.original + LEGACY_MANAGED_BLOCK.encode("utf-8")
        self.bindings.write_bytes(legacy)
        with (
            mock.patch("radar.shortcut._live_bindings", side_effect=self.live),
            mock.patch("radar.shortcut._reload_expect", side_effect=[ShortcutError("config error"), None]),
        ):
            with self.assertRaisesRegex(ShortcutError, "original bindings were restored"):
                install(self.environment)
        self.assertEqual(legacy, self.bindings.read_bytes())

    def test_remove_accepts_exact_legacy_owned_block(self) -> None:
        self.bindings.write_bytes(self.original + LEGACY_MANAGED_BLOCK.encode("utf-8"))
        with (
            mock.patch("radar.shortcut._live_bindings", side_effect=self.live),
            mock.patch("radar.shortcut._reload_expect"),
        ):
            removed = remove(self.environment)
        self.assertEqual("removed", removed["status"])
        self.assertEqual(self.original, self.bindings.read_bytes())

    def test_legacy_lookalikes_are_not_claimed(self) -> None:
        edited = LEGACY_MANAGED_BLOCK.replace("Omarchy News Radar", "Personal Radar")
        self.bindings.write_text(self.original.decode() + edited, encoding="utf-8")
        with mock.patch("radar.shortcut._live_bindings", return_value=self.live()):
            self.assertEqual("ambiguous", inspect(self.environment).classification)
            with self.assertRaises(ShortcutError):
                install(self.environment)

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
