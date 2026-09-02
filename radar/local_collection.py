"""Durable source continuity for explicit owner-run local editions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .collector import load_snapshot, validate_snapshot
from .io import atomic_write_json, read_json_bounded
from .state import cache_root
from .validation import parse_timestamp

LOCAL_SOURCE_SNAPSHOT_MAX_BYTES = 16 * 1024 * 1024


def local_source_snapshot_path(
    environment: Mapping[str, str] | None = None,
) -> Path:
    return cache_root(environment) / "local-source-snapshot.json"


def _source_time(snapshot: Mapping[str, Any]) -> float:
    marketplace = snapshot.get("sources", {}).get("marketplace")
    if not isinstance(marketplace, Mapping):
        return 0.0
    generated_at = marketplace.get("generatedAt")
    if not isinstance(generated_at, str):
        return 0.0
    return parse_timestamp(generated_at, "marketplace generatedAt").timestamp()


def prepare_local_source_snapshot(
    tracked: Path,
    destination: Path,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Stage the newest validated tracked/private baseline for one collection."""

    tracked_snapshot = load_snapshot(tracked)
    selected = tracked_snapshot
    source = "tracked"
    private_path = local_source_snapshot_path(environment)
    if private_path.exists():
        private_snapshot = validate_snapshot(
            read_json_bounded(private_path, LOCAL_SOURCE_SNAPSHOT_MAX_BYTES)
        )
        if _source_time(private_snapshot) >= _source_time(tracked_snapshot):
            selected = private_snapshot
            source = "private"
    atomic_write_json(destination, selected)
    return {"source": source, "events": len(selected["events"])}


def commit_local_source_snapshot(
    source: Path,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Adopt a collected baseline only after its matching edition was imported."""

    snapshot = validate_snapshot(
        read_json_bounded(source, LOCAL_SOURCE_SNAPSHOT_MAX_BYTES)
    )
    atomic_write_json(local_source_snapshot_path(environment), snapshot)
    return {"events": len(snapshot["events"])}
