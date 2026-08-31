"""Local XDG cache/state ownership and deterministic state transitions."""

from __future__ import annotations

import os
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .constants import FEED_MAX_BYTES, MAX_SAVED, STATE_SCHEMA_VERSION
from .errors import StorageError, ValidationError
from .io import atomic_write_json, ensure_private_directory, read_json_bounded, refuse_symlink
from .validation import (
    format_timestamp,
    migrate_section_profile_v4,
    parse_timestamp,
    validate_feed,
    validate_state,
)
from .filters import default_section_filters
from .sections import default_section_profiles

EPOCH = "1970-01-01T00:00:00Z"


def cache_root(environment: Mapping[str, str] | None = None) -> Path:
    env = environment or os.environ
    base = env.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / "omarchy-news-radar"
    return Path(env.get("HOME", str(Path.home()))) / ".cache" / "omarchy-news-radar"


def state_root(environment: Mapping[str, str] | None = None) -> Path:
    env = environment or os.environ
    base = env.get("XDG_STATE_HOME")
    if base:
        return Path(base) / "omarchy-news-radar"
    return Path(env.get("HOME", str(Path.home()))) / ".local" / "state" / "omarchy-news-radar"


def default_state() -> dict[str, Any]:
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "seenThrough": EPOCH,
        "saved": {},
        "preferences": {
            "barVisible": True,
            "imagesVisible": True,
            "interests": [],
            "sectionFilters": default_section_filters(),
            "sectionProfiles": default_section_profiles(),
        },
    }


def feed_path(environment: Mapping[str, str] | None = None) -> Path:
    return cache_root(environment) / "feed.json"


def user_state_path(environment: Mapping[str, str] | None = None) -> Path:
    return state_root(environment) / "state.json"


def diagnostic_path(environment: Mapping[str, str] | None = None) -> Path:
    return state_root(environment) / "diagnostics.log"


def load_feed(environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any] | None:
    refuse_symlink(cache_root(environment))
    path = feed_path(environment)
    try:
        raw = read_json_bounded(path, FEED_MAX_BYTES)
    except FileNotFoundError:
        return None
    return validate_feed(raw, now=now, public_only=True)


def save_feed(feed: Mapping[str, Any], environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    validated = validate_feed(dict(feed), now=now, public_only=True)
    atomic_write_json(feed_path(environment), validated)
    return validated


def _quarantine(path: Path) -> Path:
    refuse_symlink(path)
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = path.with_name(f"{path.name}.corrupt-{suffix}")
    index = 1
    while candidate.exists() and index < 100:
        candidate = path.with_name(f"{path.name}.corrupt-{suffix}-{index}")
        index += 1
    if candidate.exists():
        raise StorageError("too many quarantined state files")
    os.replace(path, candidate)
    return candidate


def load_state(environment: Mapping[str, str] | None = None) -> tuple[dict[str, Any], str | None]:
    refuse_symlink(state_root(environment))
    path = user_state_path(environment)
    try:
        raw = read_json_bounded(path, 512 * 1024)
        if isinstance(raw, dict) and raw.get("schemaVersion") in {1, 2, 3, 4}:
            old_version = raw.get("schemaVersion")
            old_preferences = raw.get("preferences") if old_version in {2, 3, 4} else None
            preferences = default_state()["preferences"]
            if isinstance(old_preferences, dict):
                for key in ("barVisible", "imagesVisible", "interests"):
                    if key in old_preferences:
                        preferences[key] = old_preferences[key]
                if old_version in {3, 4} and "sectionFilters" in old_preferences:
                    preferences["sectionFilters"] = old_preferences["sectionFilters"]
                if old_version == 4:
                    if set(old_preferences) != {
                        "barVisible",
                        "imagesVisible",
                        "interests",
                        "sectionFilters",
                        "sectionProfiles",
                    }:
                        raise ValidationError("state v4 preferences have an unknown shape")
                    old_profiles = old_preferences.get("sectionProfiles")
                    if not isinstance(old_profiles, dict) or set(old_profiles) != set(preferences["sectionProfiles"]):
                        raise ValidationError("state v4 section profiles must define every section")
                    preferences["sectionProfiles"] = {
                        section: migrate_section_profile_v4(old_profiles[section])
                        for section in preferences["sectionProfiles"]
                    }
            raw = {
                "schemaVersion": STATE_SCHEMA_VERSION,
                "seenThrough": raw.get("seenThrough"),
                "saved": raw.get("saved"),
                "preferences": preferences,
            }
            migrated = validate_state(raw)
            atomic_write_json(path, migrated)
            return migrated, None
        return validate_state(raw), None
    except FileNotFoundError:
        return default_state(), None
    except (ValidationError, StorageError):
        if path.exists() and not path.is_symlink():
            quarantined = _quarantine(path)
            state = default_state()
            atomic_write_json(path, state)
            return state, quarantined.name
        raise


def save_state(state: Mapping[str, Any], environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    validated = validate_state(dict(state))
    atomic_write_json(user_state_path(environment), validated)
    return validated


def mark_seen(state: Mapping[str, Any], through: str) -> dict[str, Any]:
    current = validate_state(dict(state))
    candidate = parse_timestamp(through, "through")
    existing = parse_timestamp(current["seenThrough"], "seenThrough")
    if candidate > existing:
        current["seenThrough"] = through
    return current


def saved_record(event: Mapping[str, Any], saved_at: datetime) -> dict[str, Any]:
    return {
        "savedAt": format_timestamp(saved_at),
        "title": event["title"],
        "sourceUrl": event["source"]["url"],
        "occurredAt": event["occurredAt"],
        "type": event["type"],
    }


def toggle_saved(
    state: Mapping[str, Any], event: Mapping[str, Any], *, now: datetime | None = None
) -> tuple[dict[str, Any], bool]:
    current = validate_state(dict(state))
    event_id = str(event["id"])
    if event_id in current["saved"]:
        del current["saved"][event_id]
        return current, False
    if len(current["saved"]) >= MAX_SAVED:
        raise ValidationError("saved item limit reached; remove an item before saving another")
    current["saved"][event_id] = saved_record(event, now or datetime.now(timezone.utc))
    current["saved"] = dict(sorted(current["saved"].items()))
    return validate_state(current), True


def update_preferences(
    state: Mapping[str, Any],
    *,
    bar_visible: bool | None = None,
    images_visible: bool | None = None,
    interests: list[str] | None = None,
) -> dict[str, Any]:
    current = validate_state(dict(state))
    preferences = dict(current["preferences"])
    if bar_visible is not None:
        preferences["barVisible"] = bar_visible
    if images_visible is not None:
        preferences["imagesVisible"] = images_visible
    if interests is not None:
        preferences["interests"] = interests
    current["preferences"] = preferences
    return validate_state(current)


def update_section_filter(
    state: Mapping[str, Any], section: str, value: Mapping[str, Any]
) -> dict[str, Any]:
    current = validate_state(dict(state))
    filters = dict(current["preferences"]["sectionFilters"])
    if section not in filters:
        raise ValidationError("unknown client section")
    filters[section] = dict(value)
    current["preferences"] = {**current["preferences"], "sectionFilters": filters}
    return validate_state(current)


def update_section_profile(
    state: Mapping[str, Any], section: str, value: Mapping[str, Any]
) -> dict[str, Any]:
    current = validate_state(dict(state))
    profiles = dict(current["preferences"]["sectionProfiles"])
    if section not in profiles:
        raise ValidationError("unknown client section")
    profiles[section] = dict(value)
    current["preferences"] = {**current["preferences"], "sectionProfiles": profiles}
    return validate_state(current)


class RefreshLock:
    """A bounded per-user lock that rejects concurrent refresh helpers."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self.path = cache_root(environment) / "refresh.lock"
        self.descriptor: int | None = None

    def __enter__(self) -> "RefreshLock":
        ensure_private_directory(self.path.parent)
        refuse_symlink(self.path)
        try:
            self.descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(self.descriptor, f"{os.getpid()} {int(time.time())}\n".encode("ascii"))
            os.fsync(self.descriptor)
        except FileExistsError as exc:
            raise StorageError("a refresh is already running") from exc
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None
        try:
            refuse_symlink(self.path)
            self.path.unlink()
        except FileNotFoundError:
            pass


def purge(environment: Mapping[str, str] | None = None) -> list[str]:
    removed: list[str] = []
    state_directory = state_root(environment)
    refuse_symlink(cache_root(environment))
    refuse_symlink(state_directory)
    candidates = [
        feed_path(environment),
        cache_root(environment) / "local-edition.json",
        user_state_path(environment),
        diagnostic_path(environment),
    ]
    if state_directory.exists():
        candidates.extend(sorted(state_directory.glob("state.json.corrupt-*")))
    for path in candidates:
        refuse_symlink(path)
        try:
            path.unlink()
            removed.append(path.name)
        except FileNotFoundError:
            pass
    asset_root = cache_root(environment) / "assets"
    refuse_symlink(asset_root)
    image_root = asset_root / "images"
    refuse_symlink(image_root)
    if image_root.exists():
        for path in sorted(image_root.iterdir()):
            refuse_symlink(path)
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise StorageError("cached image directory contains an unowned entry")
            path.unlink()
            removed.append(path.name)
        image_root.rmdir()
        asset_root.rmdir()
    return sorted(removed)
