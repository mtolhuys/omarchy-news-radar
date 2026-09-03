from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from radar.constants import PLUGIN_ID
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

    def _advance_remote(self) -> str:
        work = Path(self.temporary.name) / "work"
        if work.exists():
            subprocess.run(["rm", "-rf", str(work)], check=True)
        subprocess.run(["git", "clone", str(self.remote), str(work)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(work), "config", "user.email", "radar@example.com"], check=True)
        subprocess.run(["git", "-C", str(work), "config", "user.name", "Radar"], check=True)
        (work / "extra.txt").write_text("next\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(work), "add", "extra.txt"], check=True, capture_output=True)
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
        self.assertFalse(status["updateAvailable"])
        self.assertEqual(self.base, status["installedCommit"])

    def test_behind_when_remote_advances(self) -> None:
        tip = self._advance_remote()
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("behind", status["state"])
        self.assertTrue(status["updateAvailable"])
        self.assertTrue(status["canApply"])
        self.assertEqual(self.base, status["installedCommit"])
        self.assertEqual(tip, status["availableCommit"])

    def test_blocked_when_dirty(self) -> None:
        (self.plugin / "dirt.txt").write_text("nope\n", encoding="utf-8")
        with mock.patch("radar.plugin_update.shutil.which", return_value="/usr/bin/omarchy-plugin-update"):
            status = inspect_update(self.env)
        self.assertEqual("blocked", status["state"])
        self.assertFalse(status["canApply"])

    def test_apply_invokes_official_updater_only(self) -> None:
        tip = self._advance_remote()
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
        self.assertEqual(tip, result["installedCommit"])


if __name__ == "__main__":
    unittest.main()
