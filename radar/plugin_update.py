"""Detect and apply Omarchy News Radar plugin updates via the official updater.

Radar never implements its own fetch/merge path. Status mirrors the same
checks `omarchy-plugin-update` uses (clean git checkout, fetch origin HEAD,
compare HEAD to FETCH_HEAD, fast-forwardability). Apply always shells out to
`omarchy-plugin-update <PLUGIN_ID> --yes`, which validates and rescans.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .constants import PLUGIN_ID
from .errors import RadarError

PROTOCOL_VERSION = 1
UPDATER_NAME = "omarchy-plugin-update"
DEFAULT_PLUGINS_DIR = Path(".config/omarchy/plugins")


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


def inspect_update(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return a protocol payload describing whether an update is available."""

    plugin_dir = plugin_install_dir(environment)
    payload: dict[str, Any] = {
        "protocolVersion": PROTOCOL_VERSION,
        "status": "ok",
        "pluginId": PLUGIN_ID,
        "state": "unavailable",
        "updateAvailable": False,
        "canApply": False,
        "message": "",
        "installedCommit": "",
        "availableCommit": "",
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
        _resolve_updater()
    except RadarError as exc:
        payload["state"] = "blocked"
        payload["message"] = str(exc)
        return payload

    try:
        installed = _rev_parse(plugin_dir, "HEAD")
    except subprocess.CalledProcessError:
        payload["state"] = "blocked"
        payload["message"] = "Installed plugin checkout has no readable HEAD."
        return payload
    payload["installedCommit"] = installed

    if _dirty(plugin_dir):
        payload["state"] = "blocked"
        payload["message"] = "Installed plugin has local changes; update is blocked until it is clean."
        return payload

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

    if available == installed:
        payload["state"] = "current"
        payload["message"] = ""
        return payload

    if not _can_fast_forward(plugin_dir, installed, available):
        payload["state"] = "blocked"
        payload["updateAvailable"] = True
        payload["message"] = (
            "A newer News Radar exists, but this checkout cannot fast-forward "
            "(local commits or divergent history)."
        )
        return payload

    payload["state"] = "behind"
    payload["updateAvailable"] = True
    payload["canApply"] = True
    payload["message"] = "A newer News Radar is available."
    return payload


def apply_update(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Re-check, then run the official Omarchy updater for this plugin only."""

    status = inspect_update(environment)
    if not status.get("canApply"):
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "status": "failed" if status.get("state") in {"blocked", "check-failed", "unavailable"} else "ok",
            "state": status.get("state") or "unavailable",
            "pluginId": PLUGIN_ID,
            "updateAvailable": bool(status.get("updateAvailable")),
            "canApply": False,
            "message": status.get("message")
            or "No applyable News Radar update is available.",
            "installedCommit": status.get("installedCommit") or "",
            "availableCommit": status.get("availableCommit") or "",
            "updater": UPDATER_NAME,
        }

    updater = _resolve_updater()
    before = str(status.get("installedCommit") or "")
    expected = str(status.get("availableCommit") or "")
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
            "protocolVersion": PROTOCOL_VERSION,
            "status": "failed",
            "state": "failed",
            "pluginId": PLUGIN_ID,
            "updateAvailable": True,
            "canApply": True,
            "message": detail or "Official plugin update failed.",
            "installedCommit": after or before,
            "availableCommit": expected,
            "updater": UPDATER_NAME,
        }

    if after and expected and after != expected:
        # Updater reported success but tip did not move as expected — still surface truth.
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "status": "failed",
            "state": "failed",
            "pluginId": PLUGIN_ID,
            "updateAvailable": after != expected,
            "canApply": after != expected,
            "message": detail or "Updater finished without reaching the expected commit.",
            "installedCommit": after,
            "availableCommit": expected,
            "updater": UPDATER_NAME,
        }

    return {
        "protocolVersion": PROTOCOL_VERSION,
        "status": "ok",
        "state": "updated",
        "pluginId": PLUGIN_ID,
        "updateAvailable": False,
        "canApply": False,
        "message": "News Radar updated. The panel will reload with the new version.",
        "installedCommit": after or expected,
        "availableCommit": expected,
        "updater": UPDATER_NAME,
        "detail": detail,
    }
