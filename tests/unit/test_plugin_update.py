from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from radar.constants import HELPER_PROTOCOL_VERSION, PLUGIN_ID
from radar.plugin_update import apply_update, inspect_update


class PluginUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.home = root / "home"
        self.plugin = self.home / ".config/omarchy/plugins" / PLUGIN_ID
        self.plugin.mkdir(parents=True)
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin"}
        self._git("init")
        self._git("config", "user.email", "radar@example.com")
        self._git("config", "user.name", "Radar")
        (self.plugin / "manifest.json").write_text(
            json.dumps({"id": PLUGIN_ID, "version": "0.0.1"}),
            encoding="utf-8",
        )
        self._git("add", "manifest.json")
        self._git("commit", "-m", "base")
        self.base = self._rev("HEAD")
        self.remote = root / "remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        self._git("remote", "add", "origin", str(self.remote))
        self._git("push", "-u", "origin", "HEAD:main")
        subprocess.run(
            ["git", "--git-dir", str(self.remote), "symbolic-ref", "HEAD", "refs/heads/main"],
            check=True,
            capture_output=True,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.plugin), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def _rev(self, ref: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.plugin), "rev-parse", "--verify", ref],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _advance_remote(self, *, version: str | None = None) -> str:
        work = Path(self.temporary.name) / "work"
        if work.exists():
            subprocess.run(["rm", "-rf", str(work)], check=True)
        subprocess.run(["git", "clone", str(self.remote), str(work)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(work), "config", "user.email", "radar@example.com"], check=True)
        subprocess.run(["git", "-C", str(work), "config", "user.name", "Radar"], check=True)
        if version is None:
            (work / "extra.txt").write_text("server-only\n", encoding="utf-8")
            changed = "extra.txt"
        else:
            manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
            manifest["version"] = version
            (work / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            changed = "manifest.json"
        subprocess.run(["git", "-C", str(work), "add", changed], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(work), "commit", "-m", "next"], check=True, capture_output=True)
        tip = subprocess.run(
            ["git", "-C", str(work), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "-C", str(work), "push", "origin", "HEAD:main"],
            check=True,
            capture_output=True,
        )
        return tip

    def test_current_when_tip_matches(self) -> None:
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("current", status["state"])
        self.assertEqual(HELPER_PROTOCOL_VERSION, status["protocolVersion"])
        self.assertFalse(status["updateAvailable"])
        self.assertEqual(self.base, status["installedCommit"])

    def test_server_only_commit_does_not_offer_a_plugin_update(self) -> None:
        tip = self._advance_remote()
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("current", status["state"])
        self.assertFalse(status["updateAvailable"])
        self.assertFalse(status["canApply"])
        self.assertEqual(self.base, status["installedCommit"])
        self.assertEqual(tip, status["availableCommit"])
        self.assertEqual("0.0.1", status["installedVersion"])
        self.assertEqual("0.0.1", status["availableVersion"])

    def test_behind_when_remote_release_version_advances(self) -> None:
        tip = self._advance_remote(version="0.0.2")
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("behind", status["state"])
        self.assertTrue(status["updateAvailable"])
        self.assertTrue(status["canApply"])
        self.assertEqual(self.base, status["installedCommit"])
        self.assertEqual(tip, status["availableCommit"])
        self.assertEqual("0.0.1", status["installedVersion"])
        self.assertEqual("0.0.2", status["availableVersion"])

    def test_invalid_remote_release_version_fails_the_check_closed(self) -> None:
        self._advance_remote(version="01.0.0")
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("check-failed", status["state"])
        self.assertFalse(status["updateAvailable"])
        self.assertFalse(status["canApply"])
        self.assertIn("invalid release version", status["message"])

    def test_locally_newer_release_does_not_offer_a_downgrade(self) -> None:
        manifest = json.loads((self.plugin / "manifest.json").read_text(encoding="utf-8"))
        manifest["version"] = "0.0.2"
        (self.plugin / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self._git("add", "manifest.json")
        self._git("commit", "-m", "local release candidate")
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("current", status["state"])
        self.assertFalse(status["updateAvailable"])
        self.assertEqual("0.0.2", status["installedVersion"])
        self.assertEqual("0.0.1", status["availableVersion"])

    def test_local_candidate_containing_upstream_has_no_update_warning(self) -> None:
        (self.plugin / "candidate.txt").write_text("candidate\n", encoding="utf-8")
        self._git("add", "candidate.txt")
        self._git("commit", "-m", "local candidate")
        candidate = self._rev("HEAD")
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
            applied = apply_update(self.env)
        self.assertEqual("current", status["state"])
        self.assertFalse(status["updateAvailable"])
        self.assertFalse(status["canApply"])
        self.assertEqual("", status["message"])
        self.assertEqual(candidate, status["installedCommit"])
        self.assertEqual(self.base, status["availableCommit"])
        self.assertEqual("ok", applied["status"])
        self.assertEqual(candidate, self._rev("HEAD"))

    def test_divergent_upstream_is_blocked_without_claiming_a_newer_release(self) -> None:
        (self.plugin / "candidate.txt").write_text("candidate\n", encoding="utf-8")
        self._git("add", "candidate.txt")
        self._git("commit", "-m", "local candidate")
        tip = self._advance_remote(version="0.0.2")
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("blocked", status["state"])
        self.assertTrue(status["updateAvailable"])
        self.assertFalse(status["canApply"])
        self.assertEqual(tip, status["availableCommit"])
        self.assertIn("local history", status["message"])
        self.assertNotIn("newer", status["message"])

    def test_blocked_when_dirty(self) -> None:
        (self.plugin / "dirt.txt").write_text("nope\n", encoding="utf-8")
        self._advance_remote(version="0.0.2")
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("blocked", status["state"])
        self.assertTrue(status["updateAvailable"])
        self.assertFalse(status["canApply"])

    def test_dirty_checkout_stays_quiet_for_a_server_only_commit(self) -> None:
        (self.plugin / "dirt.txt").write_text("personal\n", encoding="utf-8")
        self._advance_remote()
        with mock.patch("radar.plugin_update.shutil.which", return_value=None):
            status = inspect_update(self.env)
        self.assertEqual("current", status["state"])
        self.assertFalse(status["updateAvailable"])
        self.assertFalse(status["canApply"])

    def test_apply_invokes_official_updater_only(self) -> None:
        tip = self._advance_remote(version="0.0.2")
        real_run = subprocess.run
        calls: list[list[str]] = []

        def router(command, **kwargs):
            if command and command[0] == "/usr/bin/omarchy-plugin-update":
                calls.append(list(command))
                self._git("fetch", "origin", "HEAD")
                self._git("merge", "--ff-only", "FETCH_HEAD")
                return subprocess.CompletedProcess(
                    command, 0, stdout=f"Updated {PLUGIN_ID}.\n", stderr=""
                )
            return real_run(command, **kwargs)

        with mock.patch(
            "radar.plugin_update.shutil.which",
            return_value="/usr/bin/omarchy-plugin-update",
        ), mock.patch(
            "radar.plugin_update.subprocess.run",
            side_effect=router,
        ):
            result = apply_update(self.env)

        self.assertEqual([["/usr/bin/omarchy-plugin-update", PLUGIN_ID, "--yes"]], calls)
        self.assertEqual("updated", result["state"])
        self.assertEqual(HELPER_PROTOCOL_VERSION, result["protocolVersion"])
        self.assertEqual(tip, result["installedCommit"])
        self.assertEqual("0.0.2", result["installedVersion"])

    def test_apply_accepts_a_same_version_server_commit_that_lands_during_update(self) -> None:
        release_tip = self._advance_remote(version="0.0.2")
        real_run = subprocess.run

        def router(command, **kwargs):
            if command and command[0] == "/usr/bin/omarchy-plugin-update":
                self._advance_remote()
                self._git("fetch", "origin", "HEAD")
                self._git("merge", "--ff-only", "FETCH_HEAD")
                return subprocess.CompletedProcess(
                    command, 0, stdout=f"Updated {PLUGIN_ID}.\n", stderr=""
                )
            return real_run(command, **kwargs)

        with mock.patch(
            "radar.plugin_update.shutil.which",
            return_value="/usr/bin/omarchy-plugin-update",
        ), mock.patch(
            "radar.plugin_update.subprocess.run",
            side_effect=router,
        ):
            result = apply_update(self.env)

        self.assertEqual("updated", result["state"])
        self.assertEqual("0.0.2", result["installedVersion"])
        self.assertNotEqual(release_tip, result["installedCommit"])


if __name__ == "__main__":
    unittest.main()
