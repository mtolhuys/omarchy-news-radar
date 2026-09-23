from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from radar.constants import HELPER_PROTOCOL_VERSION, PLUGIN_ID
import radar.plugin_update as plugin_update
from radar.plugin_update import inspect_update


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

    # The only git subcommands the check may run against the installed plugin.
    # Fetching happens in a throwaway repository outside it (D074).
    READ_ONLY_PLUGIN_GIT = {"rev-parse", "cat-file", "show", "remote"}

    def _snapshot_plugin(self) -> dict[str, str]:
        """Every file under the installed plugin, including .git, by content."""

        import hashlib

        return {
            str(path.relative_to(self.plugin)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.plugin.rglob("*"))
            if path.is_file()
        }

    def _inspect_recording(self) -> tuple[dict, list[list[str]]]:
        real_run = subprocess.run
        calls: list[list[str]] = []

        def record(command, **kwargs):
            calls.append(list(command))
            return real_run(command, **kwargs)

        with mock.patch("radar.plugin_update.subprocess.run", side_effect=record):
            status = inspect_update(self.env)
        return status, calls

    def _assert_plugin_untouched(self, calls: list[list[str]], before: dict[str, str]) -> None:
        for command in calls:
            self.assertEqual("git", command[0], f"the check may run git only: {command}")
            if command[1:3] == ["-C", str(self.plugin)]:
                self.assertIn(
                    command[3], self.READ_ONLY_PLUGIN_GIT,
                    f"only read-only git may run inside the installed plugin: {command}",
                )
            self.assertNotIn(
                str(self.plugin), " ".join(command[3:]) if command[1] == "-C" else " ".join(command[1:]),
                f"no command may target the installed plugin as a destination: {command}",
            )
        self.assertEqual(before, self._snapshot_plugin(), "nothing inside the installed plugin may change")
        self.assertFalse((self.plugin / ".git" / "FETCH_HEAD").exists())

    def test_current_when_tip_matches(self) -> None:
        status = inspect_update(self.env)
        self.assertEqual("current", status["state"])
        self.assertEqual(HELPER_PROTOCOL_VERSION, status["protocolVersion"])
        self.assertFalse(status["updateAvailable"])
        self.assertFalse(status["canApply"])
        self.assertEqual(self.base, status["installedCommit"])

    def test_server_only_commit_does_not_offer_a_plugin_update(self) -> None:
        tip = self._advance_remote()
        status = inspect_update(self.env)
        self.assertEqual("current", status["state"])
        self.assertFalse(status["updateAvailable"])
        self.assertFalse(status["canApply"])
        self.assertEqual(self.base, status["installedCommit"])
        self.assertEqual(tip, status["availableCommit"])
        self.assertEqual("0.0.1", status["installedVersion"])
        self.assertEqual("0.0.1", status["availableVersion"])

    def test_a_newer_release_is_reported_and_never_installed(self) -> None:
        """The marketplace blocker at ba3482402cf7 (D074).

        The default branch is mutable, so installing whatever it names would run
        code outside the exact snapshot the marketplace verified. The check may
        report a newer release; it must never move the installed checkout.
        """

        tip = self._advance_remote(version="0.0.2")
        before = self._snapshot_plugin()
        status, calls = self._inspect_recording()

        self.assertEqual("behind", status["state"])
        self.assertTrue(status["updateAvailable"])
        self.assertFalse(status["canApply"], "notify-only: nothing may be applied")
        self.assertEqual(tip, status["availableCommit"])
        self.assertEqual("0.0.2", status["availableVersion"])
        self.assertIn("marketplace", status["message"])
        self.assertNotIn("updater", status)
        self.assertEqual(self.base, self._rev("HEAD"))
        self._assert_plugin_untouched(calls, before)

    def test_the_helper_exposes_no_install_entry_point(self) -> None:
        from radar.cli import client_main

        self.assertFalse(hasattr(plugin_update, "apply_update"))
        self.assertFalse(hasattr(plugin_update, "UPDATER_NAME"))
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit) as refused:
            client_main(["update-apply"])
        self.assertNotEqual(0, refused.exception.code)

    def test_can_apply_is_false_for_every_checkout_shape(self) -> None:
        """Dirty, divergent or clean, Radar reports and never installs."""

        self._advance_remote(version="0.0.2")
        (self.plugin / "dirt.txt").write_text("personal\n", encoding="utf-8")
        dirty = inspect_update(self.env)
        self.assertEqual("behind", dirty["state"])
        self.assertFalse(dirty["canApply"])
        (self.plugin / "dirt.txt").unlink()

        (self.plugin / "candidate.txt").write_text("candidate\n", encoding="utf-8")
        self._git("add", "candidate.txt")
        self._git("commit", "-m", "local candidate")
        divergent_head = self._rev("HEAD")
        before = self._snapshot_plugin()
        divergent, calls = self._inspect_recording()
        self.assertEqual("behind", divergent["state"])
        self.assertFalse(divergent["canApply"])
        self.assertEqual(divergent_head, self._rev("HEAD"))
        self._assert_plugin_untouched(calls, before)

    def test_the_remote_is_fetched_outside_the_installed_plugin(self) -> None:
        """Nothing is written inside the installed plugin, not even FETCH_HEAD."""

        self._advance_remote(version="0.0.2")
        before = self._snapshot_plugin()
        status, calls = self._inspect_recording()

        self.assertEqual("behind", status["state"])
        fetches = [command for command in calls if "fetch" in command]
        self.assertEqual(1, len(fetches))
        self.assertNotEqual(str(self.plugin), fetches[0][2], "the fetch must not run in the plugin")
        self.assertIn("--depth=1", fetches[0])
        self._assert_plugin_untouched(calls, before)

    def test_an_unsafe_origin_address_is_refused_before_any_fetch(self) -> None:
        """The origin URL becomes a git argument, so option- and command-shaped
        addresses are refused rather than passed on."""

        for hostile in (
            "--upload-pack=touch /tmp/radar-pwned",
            "ext::sh -c touch% /tmp/radar-pwned",
            "fd::7",
            "https://example.com/repo\n--upload-pack=x",
        ):
            with self.subTest(hostile):
                # git's own CLI refuses to set these, so write the config the
                # way a hostile process would.
                config = self.plugin / ".git" / "config"
                lines = config.read_text(encoding="utf-8").splitlines()
                lines = [
                    "\turl = " + hostile.replace("\n", "\\n") if line.strip().startswith("url =") else line
                    for line in lines
                ]
                config.write_text("\n".join(lines) + "\n", encoding="utf-8")
                status, calls = self._inspect_recording()
                self.assertEqual("blocked", status["state"])
                self.assertFalse(status["canApply"])
                self.assertEqual([], [command for command in calls if "fetch" in command])
        self.assertFalse(Path("/tmp/radar-pwned").exists())

    def test_invalid_remote_release_version_fails_the_check_closed(self) -> None:
        self._advance_remote(version="01.0.0")
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
        status = inspect_update(self.env)
        self.assertEqual("current", status["state"])
        self.assertFalse(status["updateAvailable"])
        self.assertFalse(status["canApply"])
        self.assertEqual("", status["message"])
        self.assertEqual(candidate, status["installedCommit"])
        self.assertEqual(self.base, status["availableCommit"])
        self.assertEqual(candidate, self._rev("HEAD"))


if __name__ == "__main__":
    unittest.main()
