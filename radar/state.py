"""Local XDG cache/state ownership and deterministic state transitions."""

from __future__ import annotations

import errno
import fcntl
import os
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .constants import (
    CLIENT_SECTIONS,
    FEED_MAX_BYTES,
    MAX_READ_OVERRIDES,
    MAX_SAVED,
    STATE_SCHEMA_VERSION,
)
from .errors import StorageError, ValidationError
from .io import atomic_write_json, ensure_private_directory, read_json_bounded, refuse_symlink
from .validation import (
    format_timestamp,
    migrate_section_profile_v4,
    require_exact_keys,
    require_mapping,
    validate_feed,
    validate_section_filter,
    validate_section_profile,
    validate_state,
)
from .filters import default_section_filters
from .sections import default_section_profiles

EPOCH = "1970-01-01T00:00:00Z"
LEGACY_CLIENT_SECTIONS = (
    "front-page",
    "for-you",
    "core",
    "plugins",
    "community",
    "saved",
)
LEGACY_STATE_KEYS = {"schemaVersion", "seenThrough", "saved", "preferences"}
LEGACY_PREFERENCE_KEYS = {
    2: {"barVisible", "imagesVisible", "interests"},
    3: {"barVisible", "imagesVisible", "interests", "sectionFilters"},
    4: {"barVisible", "imagesVisible", "interests", "sectionFilters", "sectionProfiles"},
    5: {"barVisible", "imagesVisible", "interests", "sectionFilters", "sectionProfiles"},
    6: {"barVisible", "imagesVisible", "interests", "sectionFilters", "sectionProfiles"},
}


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
        "readThrough": EPOCH,
        "readOverrides": {},
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


def _migrate_legacy_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one published legacy shape before converting it to v7."""

    old_version = raw.get("schemaVersion")
    if old_version not in {1, 2, 3, 4, 5, 6}:
        raise ValidationError("unsupported legacy state schemaVersion")
    expected_state_keys = LEGACY_STATE_KEYS if old_version >= 2 else LEGACY_STATE_KEYS - {"preferences"}
    require_exact_keys(raw, expected_state_keys, f"state v{old_version}")

    preferences = default_state()["preferences"]
    if old_version >= 2:
        old_preferences = require_mapping(raw.get("preferences"), f"state v{old_version} preferences")
        require_exact_keys(
            old_preferences,
            LEGACY_PREFERENCE_KEYS[old_version],
            f"state v{old_version} preferences",
        )
        for key in ("barVisible", "imagesVisible", "interests"):
            preferences[key] = old_preferences[key]

        if old_version >= 3:
            old_filters = require_mapping(
                old_preferences.get("sectionFilters"),
                f"state v{old_version} section filters",
            )
            require_exact_keys(
                old_filters,
                CLIENT_SECTIONS if old_version == 6 else LEGACY_CLIENT_SECTIONS,
                f"state v{old_version} section filters",
            )
            preferences["sectionFilters"] = {
                section: validate_section_filter(old_filters[section])
                for section in preferences["sectionFilters"]
            }

        if old_version >= 4:
            old_profiles = require_mapping(
                old_preferences.get("sectionProfiles"),
                f"state v{old_version} section profiles",
            )
            require_exact_keys(
                old_profiles,
                CLIENT_SECTIONS if old_version == 6 else LEGACY_CLIENT_SECTIONS,
                f"state v{old_version} section profiles",
            )
            profile_validator = migrate_section_profile_v4 if old_version == 4 else validate_section_profile
            preferences["sectionProfiles"] = {
                section: profile_validator(old_profiles[section])
                for section in preferences["sectionProfiles"]
            }

    return validate_state(
        {
            "schemaVersion": STATE_SCHEMA_VERSION,
            "readThrough": raw.get("seenThrough"),
            "readOverrides": {},
            "saved": raw.get("saved"),
            "preferences": preferences,
        }
    )


def load_state(
    environment: Mapping[str, str] | None = None,
    *,
    serialized: bool = True,
) -> tuple[dict[str, Any], str | None]:
    if serialized:
        with StateLock(environment):
            return load_state(environment, serialized=False)
    refuse_symlink(state_root(environment))
    path = user_state_path(environment)
    try:
        raw = read_json_bounded(path, 512 * 1024)
        if isinstance(raw, dict) and raw.get("schemaVersion") in {1, 2, 3, 4, 5, 6}:
            migrated = _migrate_legacy_state(raw)
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


def event_is_read(state: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
    """Return the durable local reading state for one validated cached event."""

    override = state["readOverrides"].get(event["id"])
    if override is not None:
        return bool(override)
    return event["occurredAt"] <= state["readThrough"]


def set_event_read(
    state: Mapping[str, Any],
    event: Mapping[str, Any],
    read: bool,
    *,
    current_event_ids: set[str],
) -> dict[str, Any]:
    """Set one event explicitly while pruning overrides outside the current edition."""

    current = validate_state(dict(state))
    if not isinstance(read, bool):
        raise ValidationError("read state must be a boolean")
    event_id = str(event["id"])
    if event_id not in current_event_ids:
        raise ValidationError("event is not present in the validated cache")
    overrides = {
        key: value
        for key, value in current["readOverrides"].items()
        if key in current_event_ids
    }
    default_read = event["occurredAt"] <= current["readThrough"]
    if read == default_read:
        overrides.pop(event_id, None)
    else:
        overrides[event_id] = read
    if len(overrides) > MAX_READ_OVERRIDES:
        raise ValidationError("read override limit reached")
    current["readOverrides"] = dict(sorted(overrides.items()))
    return validate_state(current)


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


class _OwnedFileLock:
    """Crash-safe per-user serialization for one private state transition."""

    def __init__(
        self,
        path: Path,
        *,
        label: str,
        contention_message: str,
        nonblocking: bool,
    ) -> None:
        self.path = path
        self.label = label
        self.contention_message = contention_message
        self.nonblocking = nonblocking
        self.descriptor: int | None = None

    def __enter__(self) -> "_OwnedFileLock":
        ensure_private_directory(self.path.parent)
        refuse_symlink(self.path)
        flags = os.O_CREAT | os.O_RDWR
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            self.descriptor = os.open(self.path, flags, 0o600)
            info = os.fstat(self.descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise OSError(f"{self.label} lock is not an owned regular file")
            os.fchmod(self.descriptor, 0o600)
            try:
                operation = fcntl.LOCK_EX | (fcntl.LOCK_NB if self.nonblocking else 0)
                fcntl.flock(self.descriptor, operation)
            except OSError as exc:
                if exc.errno in {errno.EACCES, errno.EAGAIN}:
                    os.close(self.descriptor)
                    self.descriptor = None
                    raise StorageError(self.contention_message) from exc
                raise

            payload = f"{os.getpid()} {int(time.time())}\n".encode("ascii")
            os.ftruncate(self.descriptor, 0)
            if os.write(self.descriptor, payload) != len(payload):
                raise OSError(f"short {self.label}-lock write")
            os.fsync(self.descriptor)
        except StorageError:
            raise
        except OSError as exc:
            if self.descriptor is not None:
                os.close(self.descriptor)
                self.descriptor = None
            raise StorageError(f"cannot create {self.label} lock") from exc
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None


class RefreshLock(_OwnedFileLock):
    """Reject concurrent refresh helpers without leaving a stale lock."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        super().__init__(
            cache_root(environment) / "refresh.lock",
            label="refresh",
            contention_message="a refresh is already running",
            nonblocking=True,
        )


class StateLock(_OwnedFileLock):
    """Serialize cross-process state read/modify/write transitions."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        super().__init__(
            state_root(environment) / "state.lock",
            label="state",
            contention_message="local state is already being changed",
            nonblocking=False,
        )


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
