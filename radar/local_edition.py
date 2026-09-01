"""Validated import and lookup for an owner-built local static edition."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .constants import FEED_MAX_BYTES
from .errors import StorageError, ValidationError
from .images import MAX_IMAGE_BYTES, inspect_raster
from .io import (
    atomic_write,
    atomic_write_json,
    canonical_json_bytes,
    ensure_private_directory,
    read_bytes_bounded,
    read_json_bounded,
    refuse_symlink,
)
from .state import cache_root, save_feed
from .validation import validate_feed

LOCAL_EDITION_SCHEMA_VERSION = 1
BUILD_INFO_PATTERN = re.compile(
    r"\AsourceRevision=([0-9a-f]{40})\neventsSha256=([0-9a-f]{64})\n"
    r"(?:publishedAt=([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)\n)?\Z"
)
CONTENT_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def marker_path(environment: Mapping[str, str] | None = None) -> Path:
    return cache_root(environment) / "local-edition.json"


def _read_build_info(edition: Path) -> tuple[str, str, str | None]:
    try:
        text = read_bytes_bounded(edition / "BUILD-INFO.txt", 512).decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValidationError("local edition build information is not ASCII") from exc
    match = BUILD_INFO_PATTERN.fullmatch(text)
    if match is None:
        raise ValidationError("local edition build information is invalid")
    return match.group(1), match.group(2), match.group(3)


def _validate_edition_root(edition: Path) -> Path:
    if not edition.is_absolute():
        raise ValidationError("local edition directory must be absolute")
    refuse_symlink(edition)
    try:
        info = edition.stat()
    except OSError as exc:
        raise StorageError("cannot inspect local edition directory") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise StorageError("local edition directory is not an owned directory")
    return edition


def import_local_edition(
    edition: Path,
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate a complete generated edition before updating private cache."""

    root = _validate_edition_root(edition)
    clock = now or datetime.now(timezone.utc)
    raw = read_json_bounded(root / "events.json", FEED_MAX_BYTES)
    feed = validate_feed(raw, now=clock, public_only=True)
    canonical = canonical_json_bytes(feed)
    revision, declared_digest, declared_publication = _read_build_info(root)
    actual_digest = hashlib.sha256(canonical).hexdigest()
    if declared_digest != actual_digest:
        raise ValidationError("local edition feed digest does not match its build information")
    if declared_publication is not None and declared_publication != feed.get("publishedAt"):
        raise ValidationError("local edition publication time does not match its build information")

    private_cache = cache_root(environment)
    ensure_private_directory(private_cache)
    ensure_private_directory(private_cache / "assets")
    ensure_private_directory(private_cache / "assets" / "images")
    imported_images: list[str] = []
    for event in feed["events"]:
        image = event.get("image")
        if not isinstance(image, dict):
            continue
        relative = str(image["path"])
        source = root / relative
        refuse_symlink(source.parent.parent)
        refuse_symlink(source.parent)
        data = read_bytes_bounded(source, MAX_IMAGE_BYTES)
        extension = source.suffix.removeprefix(".").lower()
        media_type = CONTENT_TYPES.get(extension)
        if media_type is None:
            raise ValidationError("local edition image extension is unsupported")
        info = inspect_raster(data, media_type)
        if info.extension != extension or info.width != image["width"] or info.height != image["height"]:
            raise ValidationError("local edition image metadata does not match its bytes")
        if hashlib.sha256(data).hexdigest() != source.stem:
            raise ValidationError("local edition image digest does not match its path")
        atomic_write(private_cache / relative, data)
        imported_images.append(relative)

    marker = {
        "schemaVersion": LOCAL_EDITION_SCHEMA_VERSION,
        "feedSha256": actual_digest,
        "generatedAt": feed["generatedAt"],
        "sourceRevision": revision,
    }
    # Write the marker first. Until feed.json is atomically replaced its digest
    # cannot match, so readers either see the previous complete edition or the
    # new complete edition, never a half-imported local mode.
    atomic_write_json(marker_path(environment), marker)
    save_feed(feed, environment, now=clock)
    return {
        "feed": feed,
        "events": len(feed["events"]),
        "images": len(imported_images),
        "generatedAt": feed["generatedAt"],
        "sourceRevision": revision,
        "eventsSha256": actual_digest,
    }


def local_edition_metadata(
    feed: Mapping[str, Any] | None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    if feed is None:
        return None
    path = marker_path(environment)
    try:
        value = read_json_bounded(path, 4096)
    except FileNotFoundError:
        return None
    if not isinstance(value, dict) or set(value) != {
        "schemaVersion",
        "feedSha256",
        "generatedAt",
        "sourceRevision",
    }:
        return None
    if value.get("schemaVersion") != LOCAL_EDITION_SCHEMA_VERSION:
        return None
    digest = value.get("feedSha256")
    revision = value.get("sourceRevision")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        return None
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        return None
    if value.get("generatedAt") != feed.get("generatedAt"):
        return None
    if hashlib.sha256(canonical_json_bytes(dict(feed))).hexdigest() != digest:
        return None
    return dict(value)


def local_image_url(
    relative: str,
    environment: Mapping[str, str] | None = None,
) -> str | None:
    candidate = cache_root(environment) / relative
    refuse_symlink(candidate)
    try:
        info = candidate.stat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise StorageError("cannot inspect cached local edition image") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or not 1 <= info.st_size <= MAX_IMAGE_BYTES:
        raise StorageError("cached local edition image is not an owned bounded file")
    return candidate.absolute().as_uri()
