"""Explicit, reversible ownership of the audited default Editor chord."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .errors import ShortcutError

CHORD = "SUPER + SHIFT + N"
DEFAULT_LINE = 'o.bind("SUPER + SHIFT + N", "Editor", { omarchy = "editor" })'
RADAR_DESCRIPTION = "Omarchy News Radar"
RADAR_COMMAND = "omarchy-shell shell toggle io.github.mtolhuys.news-radar"
BEGIN = "-- BEGIN OMARCHY NEWS RADAR MANAGED SHORTCUT"
END = "-- END OMARCHY NEWS RADAR MANAGED SHORTCUT"
MANAGED_BLOCK = (
    f"\n{BEGIN}\n"
    f'hl.unbind("{CHORD}")\n'
    f'o.bind("{CHORD}", "{RADAR_DESCRIPTION}", "{RADAR_COMMAND}")\n'
    f"{END}\n"
)


@dataclass(frozen=True)
class ShortcutStatus:
    classification: str
    bindings_file: Path
    live_matches: tuple[Mapping[str, Any], ...]
    message: str

    def public(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "binding": CHORD,
            "bindingsFile": str(self.bindings_file),
            "liveActions": [
                {
                    "description": str(item.get("description") or ""),
                    "dispatcher": str(item.get("dispatcher") or ""),
                    "arg": str(item.get("arg") or ""),
                }
                for item in self.live_matches
            ],
            "message": self.message,
        }


def _paths(environment: Mapping[str, str]) -> tuple[Path, Path]:
    home = environment.get("HOME")
    omarchy = environment.get("OMARCHY_PATH")
    if not home or not omarchy:
        raise ShortcutError("HOME and OMARCHY_PATH must be set")
    config_root = Path(environment.get("XDG_CONFIG_HOME", str(Path(home) / ".config")))
    return config_root / "hypr" / "bindings.lua", Path(omarchy) / "default" / "hypr" / "bindings" / "applications.lua"


def _owned_regular_file(path: Path) -> os.stat_result:
    if path.is_symlink():
        raise ShortcutError(f"refusing symlinked configuration: {path}")
    try:
        info = path.stat()
    except FileNotFoundError as exc:
        raise ShortcutError(f"binding file does not exist: {path}") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ShortcutError(f"binding file is not an owned regular file: {path}")
    return info


def _read_text(path: Path, maximum: int = 1024 * 1024, *, require_owner: bool = True) -> str:
    if path.is_symlink():
        raise ShortcutError(f"refusing symlinked source: {path}")
    try:
        info = path.stat()
    except FileNotFoundError as exc:
        raise ShortcutError(f"required file does not exist: {path}") from exc
    if not stat.S_ISREG(info.st_mode) or (require_owner and info.st_uid != os.getuid()):
        raise ShortcutError(f"file is not an acceptable regular file: {path}")
    if info.st_size > maximum:
        raise ShortcutError(f"binding file exceeds {maximum} bytes: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ShortcutError(f"cannot read UTF-8 configuration: {path}") from exc


def _active_personal_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    for line in text.splitlines():
        code = line.split("--", 1)[0]
        compact = re.sub(r"\s+", " ", code).strip().upper()
        if "SUPER + SHIFT + N" in compact or "SUPER+SHIFT+N" in compact:
            mentions.append(line)
    return mentions


def _hyprctl(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["hyprctl", *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ShortcutError("hyprctl could not inspect the live session") from exc


def _live_bindings() -> list[Mapping[str, Any]]:
    completed = _hyprctl(["binds", "-j"])
    if completed.returncode != 0 or len(completed.stdout) > 2 * 1024 * 1024:
        raise ShortcutError("hyprctl binds -j failed or exceeded its bound")
    try:
        values = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ShortcutError("hyprctl binds -j returned invalid JSON") from exc
    if not isinstance(values, list):
        raise ShortcutError("hyprctl binds -j returned an unexpected shape")
    return [item for item in values if isinstance(item, dict)]


def _is_chord(item: Mapping[str, Any]) -> bool:
    key = str(item.get("key") or "").upper()
    try:
        modmask = int(item.get("modmask"))
    except (TypeError, ValueError):
        return False
    return key == "N" and modmask == 65


def inspect(environment: Mapping[str, str] | None = None) -> ShortcutStatus:
    env = dict(environment or os.environ)
    bindings_file, default_source = _paths(env)
    personal = _read_text(bindings_file)
    default = _read_text(default_source, require_owner=False)
    live = tuple(item for item in _live_bindings() if _is_chord(item))
    begin_count = personal.count(BEGIN)
    end_count = personal.count(END)
    block_count = personal.count(MANAGED_BLOCK)
    mentions = _active_personal_mentions(personal)
    default_exact = sum(1 for line in default.splitlines() if line.strip() == DEFAULT_LINE) == 1

    if block_count == 1 and begin_count == 1 and end_count == 1 and len(live) == 1:
        item = live[0]
        # Omarchy compiles o.bind commands into a Lua dispatcher; hyprctl then
        # exposes a numeric runtime handle rather than the source command.
        # The exact owned source block proves the command, while the live
        # description and chord prove the compiled action is singular.
        if str(item.get("description") or "") == RADAR_DESCRIPTION:
            return ShortcutStatus("owned", bindings_file, live, "Radar owns the exact managed shortcut block.")
        return ShortcutStatus("ambiguous", bindings_file, live, "The managed block exists but the live action differs; no mutation is safe.")
    if begin_count or end_count:
        return ShortcutStatus("ambiguous", bindings_file, live, "A partial or edited Radar managed block exists; restore it manually.")
    if len(live) > 1:
        return ShortcutStatus("ambiguous", bindings_file, live, "More than one live action uses Super+Shift+N.")
    if mentions:
        return ShortcutStatus("personal-conflict", bindings_file, live, "Personal bindings mention Super+Shift+N; Radar will not replace them.")
    if not live:
        return ShortcutStatus("free", bindings_file, live, "Super+Shift+N is free; Radar may add its managed binding.")
    item = live[0]
    if default_exact and str(item.get("description") or "") == "Editor":
        return ShortcutStatus("default-editor", bindings_file, live, "The exact Omarchy Editor default is live; explicit replacement authorization is required.")
    return ShortcutStatus("personal-conflict", bindings_file, live, "Super+Shift+N has a non-default live action; Radar will not replace it.")


def _atomic_preserving(path: Path, data: bytes, mode: int) -> None:
    _owned_regular_file(path)
    descriptor = -1
    temporary = ""
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.news-radar.", dir=path.parent)
        os.fchmod(descriptor, stat.S_IMODE(mode))
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
        raise ShortcutError("could not write bindings atomically") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _reload_expect(*, radar: bool) -> None:
    reload_result = _hyprctl(["reload"])
    if reload_result.returncode != 0:
        raise ShortcutError("Hyprland reload failed")
    errors = _hyprctl(["configerrors"])
    if errors.returncode != 0 or errors.stdout.strip():
        raise ShortcutError("Hyprland reported configuration errors")
    matches = [item for item in _live_bindings() if _is_chord(item)]
    expected = RADAR_DESCRIPTION if radar else "Editor"
    if len(matches) != 1 or str(matches[0].get("description") or "") != expected:
        raise ShortcutError(f"live shortcut validation did not restore exactly one {expected} action")


def _backup(path: Path, original: bytes) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.news-radar-backup-{stamp}")
    index = 1
    while backup.exists() and index < 100:
        backup = path.with_name(f"{path.name}.news-radar-backup-{stamp}-{index}")
        index += 1
    if backup.exists():
        raise ShortcutError("could not allocate a unique private backup")
    descriptor = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, original)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return backup


def install(*, replace_default_editor: bool, environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    if os.geteuid() == 0:
        raise ShortcutError("shortcut setup refuses to run as root")
    status = inspect(environment)
    if status.classification == "owned":
        return {"status": "unchanged", **status.public()}
    if status.classification == "default-editor" and not replace_default_editor:
        return {
            "status": "authorization-required",
            **status.public(),
            "authorizationCommand": "news-radar-shortcut install --replace-default-editor",
            "displacedAction": "Editor",
        }
    if status.classification not in {"free", "default-editor"}:
        raise ShortcutError(status.message)
    if replace_default_editor and status.classification != "default-editor":
        raise ShortcutError("--replace-default-editor applies only to the exact live Editor default")

    info = _owned_regular_file(status.bindings_file)
    original = status.bindings_file.read_bytes()
    backup = _backup(status.bindings_file, original)
    candidate = original + MANAGED_BLOCK.encode("utf-8")
    try:
        _atomic_preserving(status.bindings_file, candidate, info.st_mode)
        _reload_expect(radar=True)
    except Exception as exc:
        _atomic_preserving(status.bindings_file, original, info.st_mode)
        try:
            _reload_expect(radar=False)
        except ShortcutError as recovery:
            raise ShortcutError(f"shortcut installation failed and recovery validation failed: {recovery}") from exc
        raise ShortcutError("shortcut installation failed; original bindings were restored") from exc
    return {
        "status": "installed",
        **inspect(environment).public(),
        "displacedAction": "Editor" if status.classification == "default-editor" else None,
        "backup": str(backup),
    }


def remove(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    if os.geteuid() == 0:
        raise ShortcutError("shortcut setup refuses to run as root")
    status = inspect(environment)
    if status.classification == "default-editor":
        return {"status": "unchanged", **status.public()}
    if status.classification != "owned":
        raise ShortcutError("Radar does not own one exact unmodified managed block; removal refused")
    info = _owned_regular_file(status.bindings_file)
    original = status.bindings_file.read_bytes()
    text = original.decode("utf-8")
    if text.count(MANAGED_BLOCK) != 1:
        raise ShortcutError("managed block is edited or ambiguous; removal refused")
    candidate_text = text.replace(MANAGED_BLOCK, "", 1)
    backup = _backup(status.bindings_file, original)
    try:
        _atomic_preserving(status.bindings_file, candidate_text.encode("utf-8"), info.st_mode)
        _reload_expect(radar=False)
    except Exception as exc:
        _atomic_preserving(status.bindings_file, original, info.st_mode)
        try:
            _reload_expect(radar=True)
        except ShortcutError as recovery:
            raise ShortcutError(f"shortcut removal failed and recovery validation failed: {recovery}") from exc
        raise ShortcutError("shortcut removal failed; managed block was restored") from exc
    return {"status": "removed", **inspect(environment).public(), "restoredAction": "Editor", "backup": str(backup)}
