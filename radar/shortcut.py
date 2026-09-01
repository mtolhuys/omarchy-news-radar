"""Explicit, reversible ownership of Radar's conflict-free shortcut."""

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

CHORD = "SUPER + ALT + N"
MODMASK = 72
RADAR_DESCRIPTION = "Omarchy News Radar"
RADAR_COMMAND = "omarchy-shell shell summon io.github.mtolhuys.news-radar"
LEGACY_RADAR_COMMAND = "omarchy-shell shell toggle io.github.mtolhuys.news-radar"
BEGIN = "-- BEGIN OMARCHY NEWS RADAR MANAGED SHORTCUT"
END = "-- END OMARCHY NEWS RADAR MANAGED SHORTCUT"
MANAGED_BLOCK = (
    f"\n{BEGIN}\n"
    f'o.bind("{CHORD}", "{RADAR_DESCRIPTION}", "{RADAR_COMMAND}")\n'
    f"{END}\n"
)
LEGACY_MANAGED_BLOCK = (
    f"\n{BEGIN}\n"
    f'o.bind("{CHORD}", "{RADAR_DESCRIPTION}", "{LEGACY_RADAR_COMMAND}")\n'
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


def _bindings_path(environment: Mapping[str, str]) -> Path:
    home = environment.get("HOME")
    if not home:
        raise ShortcutError("HOME must be set")
    config_root = Path(environment.get("XDG_CONFIG_HOME", str(Path(home) / ".config")))
    return config_root / "hypr" / "bindings.lua"


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
        compact = re.sub(r"\s+", "", code).upper()
        if "SUPER+ALT+N" in compact or "ALT+SUPER+N" in compact:
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
    raw_modmask = item.get("modmask")
    if not isinstance(raw_modmask, (int, str)) or isinstance(raw_modmask, bool):
        return False
    try:
        modmask = int(raw_modmask)
    except (TypeError, ValueError):
        return False
    return key == "N" and modmask == MODMASK


def inspect(environment: Mapping[str, str] | None = None) -> ShortcutStatus:
    env = dict(environment or os.environ)
    bindings_file = _bindings_path(env)
    personal = _read_text(bindings_file)
    live = tuple(item for item in _live_bindings() if _is_chord(item))
    begin_count = personal.count(BEGIN)
    end_count = personal.count(END)
    block_count = personal.count(MANAGED_BLOCK)
    legacy_block_count = personal.count(LEGACY_MANAGED_BLOCK)
    mentions = _active_personal_mentions(personal)
    if block_count == 1 and begin_count == 1 and end_count == 1 and len(live) == 1:
        item = live[0]
        # Omarchy compiles o.bind commands into a Lua dispatcher; hyprctl then
        # exposes a numeric runtime handle rather than the source command.
        # The exact owned source block proves the command, while the live
        # description and chord prove the compiled action is singular.
        if str(item.get("description") or "") == RADAR_DESCRIPTION:
            return ShortcutStatus("owned", bindings_file, live, "Radar owns the exact managed shortcut block.")
        return ShortcutStatus("ambiguous", bindings_file, live, "The managed block exists but the live action differs; no mutation is safe.")
    if legacy_block_count == 1 and begin_count == 1 and end_count == 1 and len(live) == 1:
        item = live[0]
        if str(item.get("description") or "") == RADAR_DESCRIPTION:
            return ShortcutStatus(
                "owned-legacy",
                bindings_file,
                live,
                "Radar owns the exact legacy toggle shortcut; run install to complete its summon migration.",
            )
        return ShortcutStatus("ambiguous", bindings_file, live, "The legacy managed block exists but the live action differs; no mutation is safe.")
    if begin_count or end_count:
        return ShortcutStatus("ambiguous", bindings_file, live, "A partial or edited Radar managed block exists; restore it manually.")
    if len(live) > 1:
        return ShortcutStatus("ambiguous", bindings_file, live, "More than one live action uses Super+Alt+N.")
    if mentions:
        return ShortcutStatus("personal-conflict", bindings_file, live, "Personal bindings mention Super+Alt+N; Radar will not replace them.")
    if not live:
        return ShortcutStatus("free", bindings_file, live, "Super+Alt+N is free; Radar may add its managed binding.")
    return ShortcutStatus("personal-conflict", bindings_file, live, "Super+Alt+N already has a live action; Radar will not replace it.")


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
    if radar:
        if len(matches) != 1 or str(matches[0].get("description") or "") != RADAR_DESCRIPTION:
            raise ShortcutError("live shortcut validation did not find exactly one Radar action")
    elif matches:
        raise ShortcutError("live shortcut validation did not release Super+Alt+N")


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


def install(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    if os.geteuid() == 0:
        raise ShortcutError("shortcut setup refuses to run as root")
    status = inspect(environment)
    if status.classification == "owned":
        return {"status": "unchanged", **status.public()}
    if status.classification not in {"free", "owned-legacy"}:
        raise ShortcutError(status.message)

    info = _owned_regular_file(status.bindings_file)
    original = status.bindings_file.read_bytes()
    backup = _backup(status.bindings_file, original)
    if status.classification == "owned-legacy":
        original_text = original.decode("utf-8")
        if original_text.count(LEGACY_MANAGED_BLOCK) != 1:
            raise ShortcutError("legacy managed block is edited or ambiguous; migration refused")
        candidate = original_text.replace(LEGACY_MANAGED_BLOCK, MANAGED_BLOCK, 1).encode("utf-8")
    else:
        candidate = original + MANAGED_BLOCK.encode("utf-8")
    try:
        _atomic_preserving(status.bindings_file, candidate, info.st_mode)
        _reload_expect(radar=True)
    except Exception as exc:
        _atomic_preserving(status.bindings_file, original, info.st_mode)
        try:
            _reload_expect(radar=status.classification == "owned-legacy")
        except ShortcutError as recovery:
            raise ShortcutError(f"shortcut installation failed and recovery validation failed: {recovery}") from exc
        raise ShortcutError("shortcut installation failed; original bindings were restored") from exc
    return {
        "status": "migrated" if status.classification == "owned-legacy" else "installed",
        **inspect(environment).public(),
        "backup": str(backup),
    }


def remove(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    if os.geteuid() == 0:
        raise ShortcutError("shortcut setup refuses to run as root")
    status = inspect(environment)
    if status.classification == "free":
        return {"status": "unchanged", **status.public()}
    if status.classification not in {"owned", "owned-legacy"}:
        raise ShortcutError("Radar does not own one exact unmodified managed block; removal refused")
    info = _owned_regular_file(status.bindings_file)
    original = status.bindings_file.read_bytes()
    text = original.decode("utf-8")
    managed_block = LEGACY_MANAGED_BLOCK if status.classification == "owned-legacy" else MANAGED_BLOCK
    if text.count(managed_block) != 1:
        raise ShortcutError("managed block is edited or ambiguous; removal refused")
    candidate_text = text.replace(managed_block, "", 1)
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
    return {"status": "removed", **inspect(environment).public(), "releasedBinding": CHORD, "backup": str(backup)}
