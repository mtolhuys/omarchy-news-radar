"""Local XDG cache/state ownership and deterministic state transitions."""

from __future__ import annotations

import errno
import fcntl
import os
import re
import stat
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .constants import (
    CLIENT_SECTIONS,
    FEED_HTTP_MAX_BYTES,
    FEED_MAX_BYTES,
    FUTURE_SKEW_SECONDS,
    MAX_READ_OVERRIDES,
    MAX_SAVED,
    OPTIONAL_CLIENT_SECTIONS,
    STATE_SCHEMA_VERSION,
    UPDATE_CHECK_MAX_BYTES,
    V9_CLIENT_SECTIONS,
)
from .errors import StorageError, ValidationError
from .io import atomic_write_json, ensure_private_directory, read_json_bounded, refuse_symlink
from .validation import (
    format_timestamp,
    migrate_section_profile_v4,
    parse_timestamp,
    require_exact_keys,
    require_mapping,
    validate_event,
    validate_feed,
    validate_legacy_interests,
    validate_section_filter,
    validate_section_profile,
    validate_section_visibility,
    validate_state,
)
from .filters import default_section_filter, default_section_filters
from .sections import default_section_visibility, visible_client_sections

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
    7: {"barVisible", "imagesVisible", "interests", "sectionFilters", "sectionProfiles"},
    8: {"barVisible", "imagesVisible", "sectionFilters", "sectionProfiles"},
}
MODERN_LEGACY_STATE_KEYS = {"schemaVersion", "readThrough", "readOverrides", "saved", "preferences"}


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
            "sectionFilters": default_section_filters(),
            "sectionVisibility": default_section_visibility(),
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
    path = feed_path(environment)
    atomic_write_json(path, validated)
    if now is not None:
        try:
            timestamp = now.astimezone(timezone.utc).timestamp()
            os.utime(path, (timestamp, timestamp), follow_symlinks=False)
        except OSError:
            # Cache mtime is observability metadata, never a reason to discard
            # an already validated and atomically replaced last-known-good feed.
            pass
    return validated


def feed_cached_at(environment: Mapping[str, str] | None = None) -> datetime | None:
    """Return when this client last adopted its cache, using the owned feed mtime."""

    path = feed_path(environment)
    refuse_symlink(path)
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise StorageError("cached feed is not an owned regular file")
    return datetime.fromtimestamp(info.st_mtime, tz=timezone.utc)


def update_check_path(environment: Mapping[str, str] | None = None) -> Path:
    return cache_root(environment) / "update-check.json"


def feed_http_path(environment: Mapping[str, str] | None = None) -> Path:
    return cache_root(environment) / "feed-http.json"


def save_feed_http(
    url: str,
    etag: str | None,
    last_modified: str | None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Persist only bounded public cache validators for one exact feed URL."""

    value = _validate_feed_http(
        {
            "schemaVersion": 1,
            "url": url,
            "etag": etag,
            "lastModified": last_modified,
        }
    )
    path = feed_http_path(environment)
    if value["etag"] is None and value["lastModified"] is None:
        refuse_symlink(path)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return None
    atomic_write_json(path, value)
    return value


def load_feed_http(
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Read disposable validators; malformed metadata means an unconditional GET."""

    path = feed_http_path(environment)
    try:
        return _validate_feed_http(read_json_bounded(path, FEED_HTTP_MAX_BYTES))
    except FileNotFoundError:
        return None
    except (StorageError, ValidationError):
        return None


def _validate_feed_http(raw: Any) -> dict[str, Any]:
    value = require_mapping(raw, "feed HTTP metadata")
    require_exact_keys(
        value,
        {"schemaVersion", "url", "etag", "lastModified"},
        "feed HTTP metadata",
    )
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1:
        raise ValidationError("feed HTTP metadata schemaVersion is invalid")
    url = value["url"]
    if (
        not isinstance(url, str)
        or not 1 <= len(url) <= 2048
        or any(ord(character) < 32 or ord(character) == 127 for character in url)
    ):
        raise ValidationError("feed HTTP metadata URL is invalid")
    etag = value["etag"]
    if etag is not None and (
        not isinstance(etag, str)
        or len(etag) > 256
        or re.fullmatch(r'(?:W/)?"[\x20-\x21\x23-\x7e]*"', etag) is None
    ):
        raise ValidationError("feed HTTP metadata ETag is invalid")
    last_modified = value["lastModified"]
    if last_modified is not None and (
        not isinstance(last_modified, str)
        or len(last_modified) > 128
        or re.fullmatch(r"[A-Za-z]{3}, \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} GMT", last_modified) is None
    ):
        raise ValidationError("feed HTTP metadata Last-Modified is invalid")
    return dict(value)


def save_update_check(
    outcome: str,
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Record one bounded network-check attempt independently from feed age."""

    if outcome not in {"success", "failed"}:
        raise ValidationError("update-check outcome is invalid")
    value = {
        "schemaVersion": 1,
        "checkedAt": format_timestamp(now or datetime.now(timezone.utc)),
        "outcome": outcome,
    }
    atomic_write_json(update_check_path(environment), value)
    return value


def load_update_check(
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Read ephemeral cadence metadata; malformed owned metadata is simply due."""

    path = update_check_path(environment)
    try:
        raw = read_json_bounded(path, UPDATE_CHECK_MAX_BYTES)
        value = require_mapping(raw, "update-check metadata")
        require_exact_keys(
            value,
            {"schemaVersion", "checkedAt", "outcome"},
            "update-check metadata",
        )
        if (
            type(value["schemaVersion"]) is not int
            or value["schemaVersion"] != 1
            or not isinstance(value["outcome"], str)
            or value["outcome"] not in {"success", "failed"}
        ):
            raise ValidationError("update-check metadata is invalid")
        checked_at = parse_timestamp(value["checkedAt"], "update-check checkedAt")
        clock = now or datetime.now(timezone.utc)
        if checked_at > clock + timedelta(seconds=FUTURE_SKEW_SECONDS):
            raise ValidationError("update-check metadata is from the future")
        return dict(value)
    except FileNotFoundError:
        return None
    except (StorageError, ValidationError):
        return None


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
    """Validate one published legacy shape before converting it to the current schema."""

    old_version = raw.get("schemaVersion")
    if old_version not in {1, 2, 3, 4, 5, 6, 7, 8}:
        raise ValidationError("unsupported legacy state schemaVersion")
    expected_state_keys = (
        MODERN_LEGACY_STATE_KEYS
        if old_version >= 7
        else LEGACY_STATE_KEYS if old_version >= 2 else LEGACY_STATE_KEYS - {"preferences"}
    )
    require_exact_keys(raw, expected_state_keys, f"state v{old_version}")

    preferences = default_state()["preferences"]
    if old_version >= 2:
        old_preferences = require_mapping(raw.get("preferences"), f"state v{old_version} preferences")
        require_exact_keys(
            old_preferences,
            LEGACY_PREFERENCE_KEYS[old_version],
            f"state v{old_version} preferences",
        )
        if old_version <= 7:
            validate_legacy_interests(old_preferences["interests"])
        for key in ("barVisible", "imagesVisible"):
            preferences[key] = old_preferences[key]

        if old_version >= 3:
            old_filters = require_mapping(
                old_preferences.get("sectionFilters"),
                f"state v{old_version} section filters",
            )
            require_exact_keys(
                old_filters,
                V9_CLIENT_SECTIONS if old_version >= 6 else LEGACY_CLIENT_SECTIONS,
                f"state v{old_version} section filters",
            )
            preferences["sectionFilters"] = {
                section: (
                    validate_section_filter(old_filters[section])
                    if section in old_filters
                    else default_section_filter()
                )
                for section in CLIENT_SECTIONS
            }
            preferences["sectionVisibility"] = default_section_visibility()

        if old_version >= 4:
            old_profiles = require_mapping(
                old_preferences.get("sectionProfiles"),
                f"state v{old_version} section profiles",
            )
            require_exact_keys(
                old_profiles,
                V9_CLIENT_SECTIONS if old_version >= 6 else LEGACY_CLIENT_SECTIONS,
                f"state v{old_version} section profiles",
            )
            profile_validator = migrate_section_profile_v4 if old_version == 4 else validate_section_profile
            for section in old_profiles:
                profile_validator(old_profiles[section])

    return validate_state(
        {
            "schemaVersion": STATE_SCHEMA_VERSION,
            "readThrough": raw.get("readThrough") if old_version >= 7 else raw.get("seenThrough"),
            "readOverrides": raw.get("readOverrides") if old_version >= 7 else {},
            "saved": raw.get("saved"),
            "preferences": preferences,
        }
    )


def _migrate_v10_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate state v10 and add the local section-visibility profile for v11."""

    require_exact_keys(raw, MODERN_LEGACY_STATE_KEYS, "state v10")
    preferences = require_mapping(raw.get("preferences"), "state v10 preferences")
    require_exact_keys(
        preferences,
        {"barVisible", "imagesVisible", "sectionFilters"},
        "state v10 preferences",
    )
    old_filters = require_mapping(preferences.get("sectionFilters"), "state v10 section filters")
    require_exact_keys(old_filters, CLIENT_SECTIONS, "state v10 section filters")
    return validate_state(
        {
            "schemaVersion": STATE_SCHEMA_VERSION,
            "readThrough": raw.get("readThrough"),
            "readOverrides": raw.get("readOverrides"),
            "saved": raw.get("saved"),
            "preferences": {
                "barVisible": preferences["barVisible"],
                "imagesVisible": preferences["imagesVisible"],
                "sectionFilters": {
                    section: validate_section_filter(old_filters[section])
                    for section in CLIENT_SECTIONS
                },
                "sectionVisibility": default_section_visibility(),
            },
        }
    )


def _migrate_v9_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate state v9, add YouTube filters, then finish on the current schema."""

    require_exact_keys(
        raw,
        MODERN_LEGACY_STATE_KEYS,
        "state v9",
    )
    preferences = require_mapping(raw.get("preferences"), "state v9 preferences")
    require_exact_keys(
        preferences,
        {"barVisible", "imagesVisible", "sectionFilters"},
        "state v9 preferences",
    )
    old_filters = require_mapping(preferences.get("sectionFilters"), "state v9 section filters")
    require_exact_keys(old_filters, V9_CLIENT_SECTIONS, "state v9 section filters")
    section_filters = {
        section: (
            validate_section_filter(old_filters[section])
            if section in old_filters
            else default_section_filter()
        )
        for section in CLIENT_SECTIONS
    }
    return validate_state(
        {
            "schemaVersion": STATE_SCHEMA_VERSION,
            "readThrough": raw.get("readThrough"),
            "readOverrides": raw.get("readOverrides"),
            "saved": raw.get("saved"),
            "preferences": {
                "barVisible": preferences["barVisible"],
                "imagesVisible": preferences["imagesVisible"],
                "sectionFilters": section_filters,
                "sectionVisibility": default_section_visibility(),
            },
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
        if isinstance(raw, dict) and raw.get("schemaVersion") in {1, 2, 3, 4, 5, 6, 7, 8}:
            migrated = _migrate_legacy_state(raw)
            atomic_write_json(path, migrated)
            return migrated, None
        if isinstance(raw, dict) and raw.get("schemaVersion") == 9:
            migrated = _migrate_v9_state(raw)
            atomic_write_json(path, migrated)
            return migrated, None
        if isinstance(raw, dict) and raw.get("schemaVersion") == 10:
            migrated = _migrate_v10_state(raw)
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

    return set_events_read(
        state,
        [event],
        read,
        current_event_ids=current_event_ids,
    )


def set_events_read(
    state: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    read: bool,
    *,
    current_event_ids: set[str],
) -> dict[str, Any]:
    """Set a bounded event batch atomically against the current validated edition."""

    current = validate_state(dict(state))
    if not isinstance(read, bool):
        raise ValidationError("read state must be a boolean")
    if len(events) > MAX_READ_OVERRIDES:
        raise ValidationError("read event batch exceeds its bound")
    validated_events: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for raw_event in events:
        event = validate_event(dict(raw_event))
        event_id = event["id"]
        if event_id not in current_event_ids:
            raise ValidationError("event is not present in the validated cache")
        if event_id in selected_ids:
            raise ValidationError("read event batch contains a duplicate")
        selected_ids.add(event_id)
        validated_events.append(event)
    overrides = {
        key: value
        for key, value in current["readOverrides"].items()
        if key in current_event_ids
    }
    for event in validated_events:
        event_id = event["id"]
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
    section_visibility: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = validate_state(dict(state))
    preferences = dict(current["preferences"])
    if bar_visible is not None:
        preferences["barVisible"] = bar_visible
    if images_visible is not None:
        preferences["imagesVisible"] = images_visible
    if section_visibility is not None:
        current_visibility = dict(preferences["sectionVisibility"])
        current_visibility.update(section_visibility)
        preferences["sectionVisibility"] = current_visibility
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
        feed_http_path(environment),
        update_check_path(environment),
        cache_root(environment) / "local-edition.json",
        cache_root(environment) / "local-source-snapshot.json",
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
