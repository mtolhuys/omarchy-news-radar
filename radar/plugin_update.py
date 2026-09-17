"""Detect released Omarchy News Radar updates via the official updater.

Repository commits are not releases: the same tree also contains the Forge
collector and documentation. Availability is therefore based on the bounded,
strict versions in the installed and fetched manifests. Apply always shells
out to `omarchy-plugin-update <PLUGIN_ID> --yes`, which validates and rescans.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .constants import HELPER_PROTOCOL_VERSION, PLUGIN_ID
from .errors import RadarError

UPDATER_NAME = "omarchy-plugin-update"
DEFAULT_PLUGINS_DIR = Path(".config/omarchy/plugins")
MANIFEST_MAX_BYTES = 64 * 1024
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


def _resolve_updater() -> str:
    path = shutil.which(UPDATER_NAME)
    if not path:
        raise RadarError(f"{UPDATER_NAME} is not available on PATH")
    return path


def _is_git_checkout(plugin_dir: Path) -> bool:
    return plugin_dir.is_dir() and not plugin_dir.is_symlink() and (plugin_dir / ".git").exists()


def _dirty(plugin_dir: Path) -> bool:
    result = _run_git(plugin_dir, "status", "--porcelain", "--untracked-files=normal")
    return bool(result.stdout.strip())


def _rev_parse(plugin_dir: Path, ref: str) -> str:
    result = _run_git(plugin_dir, "rev-parse", "--verify", ref)
    return result.stdout.strip()


def _can_fast_forward(plugin_dir: Path, current: str, remote: str) -> bool:
    """True when remote is a descendant of current (ff-only merge would succeed)."""
    merge_base = _run_git(plugin_dir, "merge-base", current, remote, check=False)
    if merge_base.returncode != 0:
        return False
    return merge_base.stdout.strip() == current


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
        "updater": UPDATER_NAME,
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

    fetch = _run_git(plugin_dir, "fetch", "--quiet", "origin", "HEAD", check=False)
    if fetch.returncode != 0:
        detail = (fetch.stderr or fetch.stdout or "fetch failed").strip()
        payload["state"] = "check-failed"
        payload["message"] = f"Could not check for updates ({detail})."
        return payload

    try:
        available = _rev_parse(plugin_dir, "FETCH_HEAD")
    except subprocess.CalledProcessError:
        payload["state"] = "check-failed"
        payload["message"] = "Update check could not resolve the remote tip."
        return payload
    payload["availableCommit"] = available
    try:
        available_version, available_key = _manifest_version(plugin_dir, available)
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

    payload["updateAvailable"] = True
    try:
        _resolve_updater()
    except RadarError as exc:
        payload["state"] = "blocked"
        payload["message"] = str(exc)
        return payload

    if _dirty(plugin_dir):
        payload["state"] = "blocked"
        payload["message"] = "Installed plugin has local changes; update is blocked until it is clean."
        return payload

    if not _can_fast_forward(plugin_dir, installed, available):
        payload["state"] = "blocked"
        payload["message"] = (
            f"News Radar {available_version} is available, but this checkout has local history. "
            "Automatic update is unavailable."
        )
        return payload

    payload["state"] = "behind"
    payload["canApply"] = True
    payload["message"] = f"News Radar {available_version} is available."
    return payload


def apply_update(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Re-check, then run the official Omarchy updater for this plugin only."""

    status = inspect_update(environment)
    if not status.get("canApply"):
        return {
            "protocolVersion": HELPER_PROTOCOL_VERSION,
            "status": "failed" if status.get("state") in {"blocked", "check-failed", "unavailable"} else "ok",
            "state": status.get("state") or "unavailable",
            "pluginId": PLUGIN_ID,
            "updateAvailable": bool(status.get("updateAvailable")),
            "canApply": False,
            "message": status.get("message")
            or "No applyable News Radar update is available.",
            "installedCommit": status.get("installedCommit") or "",
            "availableCommit": status.get("availableCommit") or "",
            "installedVersion": status.get("installedVersion") or "",
            "availableVersion": status.get("availableVersion") or "",
            "updater": UPDATER_NAME,
        }

    updater = _resolve_updater()
    before = str(status.get("installedCommit") or "")
    expected = str(status.get("availableCommit") or "")
    before_version = str(status.get("installedVersion") or "")
    expected_version = str(status.get("availableVersion") or "")
    expected_key = tuple(int(part) for part in expected_version.split("."))
    completed = subprocess.run(
        [updater, PLUGIN_ID, "--yes"],
        capture_output=True,
        text=True,
        env=dict(environment or os.environ),
    )
    detail = (completed.stdout or completed.stderr or "").strip()

    plugin_dir = plugin_install_dir(environment)
    after = ""
    try:
        after = _rev_parse(plugin_dir, "HEAD")
    except (OSError, subprocess.CalledProcessError):
        after = ""

    if completed.returncode != 0:
        return {
            "protocolVersion": HELPER_PROTOCOL_VERSION,
            "status": "failed",
            "state": "failed",
            "pluginId": PLUGIN_ID,
            "updateAvailable": True,
            "canApply": True,
            "message": detail or "Official plugin update failed.",
            "installedCommit": after or before,
            "availableCommit": expected,
            "installedVersion": before_version,
            "availableVersion": expected_version,
            "updater": UPDATER_NAME,
        }

    after_version = ""
    after_key: tuple[int, int, int] | None = None
    if after:
        try:
            after_version, after_key = _manifest_version(plugin_dir, after)
        except RadarError:
            pass
    if after_key is None or after_key < expected_key:
        # A server-only commit may land between inspection and apply. Reaching
        # the expected release version is the invariant, not one transient SHA.
        return {
            "protocolVersion": HELPER_PROTOCOL_VERSION,
            "status": "failed",
            "state": "failed",
            "pluginId": PLUGIN_ID,
            "updateAvailable": True,
            "canApply": True,
            "message": detail or "Updater finished without reaching the expected commit.",
            "installedCommit": after,
            "availableCommit": expected,
            "installedVersion": after_version,
            "availableVersion": expected_version,
            "updater": UPDATER_NAME,
        }

    return {
        "protocolVersion": HELPER_PROTOCOL_VERSION,
        "status": "ok",
        "state": "updated",
        "pluginId": PLUGIN_ID,
        "updateAvailable": False,
        "canApply": False,
        "message": "News Radar updated. The panel will reload with the new version.",
        "installedCommit": after or expected,
        "availableCommit": expected,
        "installedVersion": after_version or expected_version,
        "availableVersion": expected_version,
        "updater": UPDATER_NAME,
        "detail": detail,
    }
