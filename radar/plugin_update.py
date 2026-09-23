"""Notice released Omarchy News Radar updates without ever installing them.

Repository commits are not releases: the same tree also contains the Forge
collector and documentation. Availability is therefore based on the bounded,
strict versions in the installed and fetched manifests.

This module only reports. It never runs an updater, moves the installed
checkout, or executes fetched code, and it writes nothing inside the installed
plugin: the remote tip is fetched into a throwaway repository outside it, and
the installed checkout is only read. The marketplace verifies one exact commit;
the repository's default branch is mutable, so installing whatever it names
would run code outside that reviewed snapshot (D074). A newer release is
installed through Omarchy's plugin marketplace once that release is verified.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .constants import HELPER_PROTOCOL_VERSION, PLUGIN_ID
from .errors import RadarError

DEFAULT_PLUGINS_DIR = Path(".config/omarchy/plugins")
MANIFEST_MAX_BYTES = 64 * 1024
FETCH_TIMEOUT_SECONDS = 30
REMOTE_URL_MAX = 2048
# The origin URL becomes a git argument. A leading "-" would be read as an
# option, and transports such as ext:: run commands, so only plain repository
# addresses are accepted.
REMOTE_URL_RE = re.compile(
    r"^(?:https://[A-Za-z0-9][^\s]*"
    r"|ssh://[A-Za-z0-9][^\s]*"
    r"|file:///[^\s]*"
    r"|/[^\s]*"
    r"|[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9.-]*:[^\s]+)$"
)
VERSION_RE = re.compile(
    r"^(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$"
)


def _plugins_dir(environment: Mapping[str, str] | None = None) -> Path:
    env = environment or os.environ
    home = Path(env.get("HOME", "")).expanduser()
    if not home.is_absolute() or home == Path("/"):
        raise RadarError("HOME must be an absolute non-root user directory")
    return home / DEFAULT_PLUGINS_DIR


def plugin_install_dir(environment: Mapping[str, str] | None = None) -> Path:
    return _plugins_dir(environment) / PLUGIN_ID


def _run_git(plugin_dir: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(plugin_dir), *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


def _origin_url(plugin_dir: Path) -> str:
    """Read the installed checkout's origin, accepting only a plain address."""

    result = _run_git(plugin_dir, "remote", "get-url", "origin", check=False)
    url = result.stdout.strip() if result.returncode == 0 else ""
    if (
        not url
        or len(url) > REMOTE_URL_MAX
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in url)
        or "::" in url
        or not REMOTE_URL_RE.fullmatch(url)
    ):
        raise RadarError("origin is not a supported repository address")
    return url


def _fetch_remote_tip(url: str, scratch: Path) -> str:
    """Fetch only the remote tip into a throwaway bare repository.

    Nothing lands in the installed plugin's own repository: no objects, no
    FETCH_HEAD, and none of its local configuration or hooks apply to the fetch.
    """

    subprocess.run(
        ["git", "init", "--quiet", "--bare", str(scratch)],
        check=True,
        capture_output=True,
        text=True,
    )
    environment = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    subprocess.run(
        ["git", "-C", str(scratch), "fetch", "--quiet", "--depth=1", url, "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
        timeout=FETCH_TIMEOUT_SECONDS,
    )
    return _rev_parse(scratch, "FETCH_HEAD")


def _is_git_checkout(plugin_dir: Path) -> bool:
    return plugin_dir.is_dir() and not plugin_dir.is_symlink() and (plugin_dir / ".git").exists()


def _rev_parse(plugin_dir: Path, ref: str) -> str:
    result = _run_git(plugin_dir, "rev-parse", "--verify", ref)
    return result.stdout.strip()


def _manifest_version(plugin_dir: Path, ref: str) -> tuple[str, tuple[int, int, int]]:
    """Read one committed, bounded plugin identity without checking it out."""

    object_name = f"{ref}:manifest.json"
    size = _run_git(plugin_dir, "cat-file", "-s", object_name, check=False)
    if size.returncode != 0:
        raise RadarError("manifest.json is missing")
    try:
        byte_count = int(size.stdout.strip())
    except ValueError as exc:
        raise RadarError("manifest.json has an invalid Git object size") from exc
    if not 1 <= byte_count <= MANIFEST_MAX_BYTES:
        raise RadarError("manifest.json exceeds its byte bound")
    try:
        shown = _run_git(plugin_dir, "show", object_name, check=False)
    except UnicodeDecodeError as exc:
        raise RadarError("manifest.json is not valid UTF-8") from exc
    if shown.returncode != 0 or len(shown.stdout.encode("utf-8")) > MANIFEST_MAX_BYTES:
        raise RadarError("manifest.json cannot be read safely")
    try:
        manifest = json.loads(shown.stdout)
    except json.JSONDecodeError as exc:
        raise RadarError("manifest.json is not valid JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("id") != PLUGIN_ID:
        raise RadarError("manifest.json has the wrong plugin identity")
    version = manifest.get("version")
    match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
    if match is None:
        raise RadarError("manifest.json has an invalid release version")
    return version, tuple(int(part) for part in match.groups())


def inspect_update(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return a protocol payload describing whether an update is available."""

    plugin_dir = plugin_install_dir(environment)
    payload: dict[str, Any] = {
        "protocolVersion": HELPER_PROTOCOL_VERSION,
        "status": "ok",
        "pluginId": PLUGIN_ID,
        "state": "unavailable",
        "updateAvailable": False,
        "canApply": False,
        "message": "",
        "installedCommit": "",
        "availableCommit": "",
        "installedVersion": "",
        "availableVersion": "",
    }

    if not plugin_dir.exists():
        payload["message"] = "News Radar is not installed under the Omarchy plugins directory."
        return payload
    if plugin_dir.is_symlink():
        payload["state"] = "blocked"
        payload["message"] = "Installed plugin path is a symlink; refusing to inspect it."
        return payload
    if not _is_git_checkout(plugin_dir):
        payload["message"] = "Installed plugin is not a Git checkout, so there is nothing to pull."
        return payload

    try:
        installed = _rev_parse(plugin_dir, "HEAD")
    except subprocess.CalledProcessError:
        payload["state"] = "blocked"
        payload["message"] = "Installed plugin checkout has no readable HEAD."
        return payload
    payload["installedCommit"] = installed
    try:
        installed_version, installed_key = _manifest_version(plugin_dir, installed)
    except RadarError as exc:
        payload["state"] = "blocked"
        payload["message"] = f"Installed plugin {exc}."
        return payload
    payload["installedVersion"] = installed_version

    try:
        origin = _origin_url(plugin_dir)
    except RadarError as exc:
        payload["state"] = "blocked"
        payload["message"] = f"Installed plugin {exc}."
        return payload

    # The remote tip is fetched and read in a throwaway repository outside the
    # installed plugin, which this check only ever reads.
    with tempfile.TemporaryDirectory(prefix="news-radar-update-check-") as scratch_name:
        scratch = Path(scratch_name) / "remote.git"
        try:
            available = _fetch_remote_tip(origin, scratch)
        except subprocess.TimeoutExpired:
            payload["state"] = "check-failed"
            payload["message"] = "Could not check for updates (the remote did not answer in time)."
            return payload
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "fetch failed").strip()
            payload["state"] = "check-failed"
            payload["message"] = f"Could not check for updates ({detail})."
            return payload
        payload["availableCommit"] = available
        try:
            available_version, available_key = _manifest_version(scratch, available)
        except RadarError as exc:
            payload["state"] = "check-failed"
            payload["message"] = f"Fetched plugin {exc}."
            return payload
    payload["availableVersion"] = available_version

    # Collector, documentation and other server-owned commits are deliberately
    # invisible to clients until the manifest declares a newer release.
    if available_key <= installed_key:
        payload["state"] = "current"
        payload["message"] = ""
        return payload

    # Notify only. `canApply` stays false on every path, so even an older panel
    # paired with this helper can never offer to install unverified code.
    payload["updateAvailable"] = True
    payload["state"] = "behind"
    payload["message"] = (
        f"News Radar {available_version} is available. Install it through the "
        "Omarchy plugin marketplace once that release is verified there."
    )
    return payload
