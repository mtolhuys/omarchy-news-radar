"""Fail-closed continuity selection for scheduled publication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .collector import SNAPSHOT_SCHEMA, load_snapshot
from .collector import validate_snapshot
from .errors import ValidationError
from .io import atomic_write_json, read_json_bounded
from .validation import parse_timestamp

PUBLICATION_SNAPSHOT_MAX_BYTES = 16 * 1024 * 1024
TRANSITION_BASELINE_MAX_AGE = timedelta(hours=6)
TRUSTWORTHY_TRANSITION_EVENT_TYPES = frozenset(
    {"omarchy-released", "plugin-added", "community-link"}
)


def migrate_legacy_source_snapshot(source: Path, destination: Path) -> dict[str, Any]:
    """Reset replay-contaminated discovery events while preserving dated facts."""

    raw = read_json_bounded(source, PUBLICATION_SNAPSHOT_MAX_BYTES)
    if not isinstance(raw, Mapping) or raw.get("schemaVersion") != 1:
        raise ValidationError("source snapshot is not legacy publication state")
    events = raw.get("events")
    sources = raw.get("sources")
    if not isinstance(events, list) or not isinstance(sources, Mapping):
        raise ValidationError("legacy publication source state is invalid")
    candidate = validate_snapshot(
        {
            "schemaVersion": SNAPSHOT_SCHEMA,
            "events": [
                event
                for event in events
                if isinstance(event, Mapping)
                and event.get("type") in TRUSTWORTHY_TRANSITION_EVENT_TYPES
            ],
            "sources": dict(sources),
        }
    )
    atomic_write_json(destination, candidate)
    return {
        "events": len(candidate["events"]),
        "removed": len(events) - len(candidate["events"]),
    }


def _marketplace_generated_at(snapshot: Mapping[str, Any]) -> datetime:
    marketplace = snapshot.get("sources", {}).get("marketplace")
    if not isinstance(marketplace, Mapping):
        raise ValidationError("publication source state lacks marketplace continuity")
    value = marketplace.get("generatedAt")
    if not isinstance(value, str):
        raise ValidationError("publication source state lacks marketplace generation time")
    return parse_timestamp(value, "marketplace generatedAt")


def restore_publication_source_snapshot(
    previous: Path,
    tracked: Path,
    destination: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Restore the last deployed state or one bounded schema transition seed."""

    raw_previous = read_json_bounded(previous, PUBLICATION_SNAPSHOT_MAX_BYTES)
    if isinstance(raw_previous, Mapping) and raw_previous.get("schemaVersion") == SNAPSHOT_SCHEMA:
        selected = load_snapshot(previous)
        source = "previous-deployment"
    elif isinstance(raw_previous, Mapping) and raw_previous.get("schemaVersion") == 1:
        # Version 1 was the manually advanced design that caused scheduled
        # runs to replay old diffs. Permit exactly one transition from a fresh,
        # reviewed v2 baseline; every later missing/corrupt v2 state fails.
        selected = load_snapshot(tracked)
        clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        age = clock - _marketplace_generated_at(selected)
        if age < timedelta(0) or age > TRANSITION_BASELINE_MAX_AGE:
            raise ValidationError("tracked publication transition baseline is not fresh")
        source = "tracked-transition"
    else:
        raise ValidationError("previous publication source state is unsupported")
    atomic_write_json(destination, selected)
    return {"source": source, "events": len(selected["events"])}
