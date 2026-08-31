"""Strict, reversible XDG application-launcher management."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .constants import PLUGIN_ID
from .errors import LauncherError

DESKTOP_NAME = f"{PLUGIN_ID}.desktop"
ICON_NAME = f"{PLUGIN_ID}.svg"
RECEIPT_SCHEMA_VERSION = 1
MAX_DESKTOP_BYTES = 32 * 1024
MAX_ICON_BYTES = 512 * 1024
MAX_RECEIPT_BYTES = 8 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class LauncherPaths:
    source_desktop: Path
    source_icon: Path
    desktop: Path
    icon: Path
    receipt: Path


def discover_paths(
    *, plugin_root: Path | None = None, environ: Mapping[str, str] | None = None
) -> LauncherPaths:
    values = os.environ if environ is None else environ
    home_text = values.get("HOME", "")
    home = Path(home_text)
    if not home.is_absolute() or home == Path("/"):
        raise LauncherError("HOME must be an absolute non-root user directory")

    data_home = Path(values.get("XDG_DATA_HOME", str(home / ".local/share")))
    state_home = Path(values.get("XDG_STATE_HOME", str(home / ".local/state")))
    if not data_home.is_absolute() or data_home == Path("/"):
        raise LauncherError("XDG_DATA_HOME must be an absolute non-root directory")
    if not state_home.is_absolute() or state_home == Path("/"):
        raise LauncherError("XDG_STATE_HOME must be an absolute non-root directory")

    root = (plugin_root or Path(__file__).resolve().parents[1]).resolve()
    return LauncherPaths(
        source_desktop=root / "share/applications" / DESKTOP_NAME,
        source_icon=root / "assets" / ICON_NAME,
        desktop=data_home / "applications" / DESKTOP_NAME,
        icon=data_home / "icons/hicolor/scalable/apps" / ICON_NAME,
        receipt=state_home / "omarchy-news-radar/launcher.json",
    )


def _read_regular(path: Path, maximum: int, *, require_owner: bool) -> bytes:
    if path.is_symlink():
        raise LauncherError(f"refusing symlinked file: {path}")
    try:
        info = path.stat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise LauncherError(f"cannot inspect file: {path}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise LauncherError(f"not a regular file: {path}")
    if require_owner and info.st_uid != os.getuid():
        raise LauncherError(f"file is not owned by the current user: {path}")
    if info.st_size > maximum:
        raise LauncherError(f"file exceeds {maximum} bytes: {path}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise LauncherError(f"cannot read file: {path}") from exc
    if len(data) > maximum:
        raise LauncherError(f"file exceeds {maximum} bytes: {path}")
    return data


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _current_digest(path: Path, maximum: int) -> str | None:
    try:
        return _digest(_read_regular(path, maximum, require_owner=True))
    except FileNotFoundError:
        return None


def _validate_source_desktop(data: bytes) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LauncherError("launcher template is not UTF-8") from exc
    required = {
        "[Desktop Entry]",
        "Type=Application",
        "Name=Omarchy News Radar",
        f"Exec=omarchy-shell shell summon {PLUGIN_ID}",
        f"Icon={PLUGIN_ID}",
        "Terminal=false",
        "X-Omarchy-News-Radar-Managed=true",
    }
    lines = set(text.splitlines())
    missing = sorted(required - lines)
    if missing or "\x00" in text:
        raise LauncherError("launcher template does not match the audited application contract")


def _validate_source_icon(data: bytes) -> None:
    prefix = data.lstrip()[:256].lower()
    if b"<svg" not in prefix or b"<script" in data.lower():
        raise LauncherError("launcher icon is not the audited static SVG asset")


def _ensure_target_directory(path: Path, mode: int) -> None:
    try:
        path.mkdir(mode=mode, parents=True, exist_ok=True)
    except OSError as exc:
        raise LauncherError(f"cannot create launcher directory: {path}") from exc
    if path.is_symlink():
        raise LauncherError(f"refusing symlinked launcher directory: {path}")
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise LauncherError(f"launcher directory is not owned by the current user: {path}")


def _atomic_replace(path: Path, data: bytes, mode: int, *, directory_mode: int = 0o755) -> None:
    _ensure_target_directory(path.parent, directory_mode)
    if path.is_symlink():
        raise LauncherError(f"refusing symlinked launcher target: {path}")
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise LauncherError(f"launcher target is not an owned regular file: {path}")

    descriptor = -1
    temporary = ""
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = ""
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise LauncherError(f"cannot atomically write launcher file: {path}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _receipt_bytes(receipt: dict[str, object]) -> bytes:
    return (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _read_receipt(paths: LauncherPaths) -> dict[str, object] | None:
    try:
        raw = _read_regular(paths.receipt, MAX_RECEIPT_BYTES, require_owner=True)
    except FileNotFoundError:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LauncherError("launcher ownership receipt is invalid; refusing mutation") from exc
    if not isinstance(value, dict) or set(value) != {"desktop", "icon", "schemaVersion"}:
        raise LauncherError("launcher ownership receipt has an unknown shape")
    if value.get("schemaVersion") != RECEIPT_SCHEMA_VERSION:
        raise LauncherError("launcher ownership receipt has an unsupported version")
    for key, target in (("desktop", paths.desktop), ("icon", paths.icon)):
        entry = value.get(key)
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise LauncherError(f"launcher ownership receipt has an invalid {key} entry")
        if entry.get("path") != str(target) or not SHA256_RE.fullmatch(str(entry.get("sha256", ""))):
            raise LauncherError(f"launcher ownership receipt does not match the current {key} target")
    return value


def _new_receipt(paths: LauncherPaths, desktop_digest: str, icon_digest: str) -> dict[str, object]:
    return {
        "schemaVersion": RECEIPT_SCHEMA_VERSION,
        "desktop": {"path": str(paths.desktop), "sha256": desktop_digest},
        "icon": {"path": str(paths.icon), "sha256": icon_digest},
    }


def inspect(paths: LauncherPaths | None = None) -> dict[str, object]:
    selected = paths or discover_paths()
    receipt = _read_receipt(selected)
    desktop_digest = _current_digest(selected.desktop, MAX_DESKTOP_BYTES)
    icon_digest = _current_digest(selected.icon, MAX_ICON_BYTES)
    if receipt is None:
        state = "absent" if desktop_digest is None and icon_digest is None else "unmanaged"
    else:
        desktop_match = desktop_digest == receipt["desktop"]["sha256"]  # type: ignore[index]
        icon_match = icon_digest == receipt["icon"]["sha256"]  # type: ignore[index]
        state = "installed" if desktop_match and icon_match else "modified"
    return {
        "status": "ok",
        "state": state,
        "installed": state == "installed",
        "desktop": str(selected.desktop),
        "icon": str(selected.icon),
    }


def install(paths: LauncherPaths | None = None) -> dict[str, object]:
    selected = paths or discover_paths()
    desktop_data = _read_regular(selected.source_desktop, MAX_DESKTOP_BYTES, require_owner=False)
    icon_data = _read_regular(selected.source_icon, MAX_ICON_BYTES, require_owner=False)
    _validate_source_desktop(desktop_data)
    _validate_source_icon(icon_data)
    desktop_digest = _digest(desktop_data)
    icon_digest = _digest(icon_data)
    receipt = _read_receipt(selected)

    current = {
        "desktop": _current_digest(selected.desktop, MAX_DESKTOP_BYTES),
        "icon": _current_digest(selected.icon, MAX_ICON_BYTES),
    }
    desired = {"desktop": desktop_digest, "icon": icon_digest}
    if receipt is None:
        for key in ("desktop", "icon"):
            if current[key] is not None and current[key] != desired[key]:
                raise LauncherError(f"an unmanaged or modified {key} target already exists; refusing overwrite")
    else:
        for key in ("desktop", "icon"):
            owned_digest = receipt[key]["sha256"]  # type: ignore[index]
            if current[key] is not None and current[key] != owned_digest:
                raise LauncherError(f"the managed {key} target was modified; refusing overwrite")

    # The icon lands first, so the visible desktop entry never references a
    # missing icon. Each replacement and the final receipt are atomic.
    _atomic_replace(selected.icon, icon_data, 0o644)
    _atomic_replace(selected.desktop, desktop_data, 0o644)
    _atomic_replace(
        selected.receipt,
        _receipt_bytes(_new_receipt(selected, desktop_digest, icon_digest)),
        0o600,
        directory_mode=0o700,
    )
    return {"status": "ok", "state": "installed", "desktop": str(selected.desktop)}


def remove(paths: LauncherPaths | None = None) -> dict[str, object]:
    selected = paths or discover_paths()
    receipt = _read_receipt(selected)
    if receipt is None:
        if not selected.desktop.exists() and not selected.icon.exists():
            return {"status": "ok", "state": "absent", "removed": []}
        raise LauncherError("launcher files exist without an ownership receipt; refusing removal")

    removed: list[str] = []
    preserved: list[str] = []
    for key, target, maximum in (
        ("desktop", selected.desktop, MAX_DESKTOP_BYTES),
        ("icon", selected.icon, MAX_ICON_BYTES),
    ):
        current = _current_digest(target, maximum)
        if current is None:
            continue
        if current != receipt[key]["sha256"]:  # type: ignore[index]
            preserved.append(key)
            continue
        try:
            target.unlink()
        except OSError as exc:
            raise LauncherError(f"cannot remove managed launcher file: {target}") from exc
        removed.append(key)

    try:
        selected.receipt.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise LauncherError("cannot remove launcher ownership receipt") from exc
    return {
        "status": "ok",
        "state": "preserved-modified" if preserved else "absent",
        "removed": removed,
        "preserved": preserved,
    }
