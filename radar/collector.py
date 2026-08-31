"""Transactional orchestration for normalized sources and feed candidates."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .curation import apply_curation, load_curation
from .errors import ValidationError
from .errors import FetchError
from .http import FetchPolicy, decode_json, fetch_bytes
from .io import atomic_write_json, canonical_json_bytes, read_json_bounded
from .model import canonical_events, make_feed
from .sources import community_events, diff_marketplace, diff_releases, parse_marketplace, parse_releases
from .sources.marketplace import CATALOG_URL
from .sources.omarchy_releases import API_URL, PUBLIC_URL
from .validation import format_timestamp, parse_timestamp

SNAPSHOT_SCHEMA = 1


@dataclass(frozen=True)
class FixtureInputs:
    releases: Path
    marketplace: Path
    community: Path
    curation: Path


def empty_snapshot() -> dict[str, Any]:
    return {"schemaVersion": SNAPSHOT_SCHEMA, "events": [], "sources": {}}


def validate_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schemaVersion") != SNAPSHOT_SCHEMA:
        raise ValidationError("source snapshot is invalid")
    sources = value.get("sources")
    events = value.get("events", [])
    if not isinstance(sources, dict) or not isinstance(events, list):
        raise ValidationError("source snapshot is invalid")
    normalized_events = canonical_events(events)
    if normalized_events != events:
        raise ValidationError("source snapshot events are not canonical")
    return {
        "schemaVersion": SNAPSHOT_SCHEMA,
        "events": normalized_events,
        "sources": dict(sources),
    }


def load_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_snapshot()
    return validate_snapshot(read_json_bounded(path, 16 * 1024 * 1024))


def collect_from_fixtures(
    inputs: FixtureInputs,
    *,
    previous_snapshot: Mapping[str, Any] | None,
    now: datetime,
    bootstrap_marketplace: bool,
    failed_sources: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Collect one deterministic edition without network access."""

    clock = now.astimezone(timezone.utc).replace(microsecond=0)
    window_from = clock - timedelta(days=90)
    previous = validate_snapshot(dict(previous_snapshot or empty_snapshot()))
    previous_sources = previous.get("sources", {})
    if not isinstance(previous_sources, dict):
        raise ValidationError("source snapshot sources are invalid")
    failed = dict(failed_sources or {})
    next_sources = dict(previous_sources)
    events: list[dict[str, Any]] = []
    health: list[dict[str, Any]] = []
    checked_at = format_timestamp(clock)

    if "omarchy-releases" in failed:
        health.append({"id": "omarchy-releases", "status": "failed", "checkedAt": checked_at, "sourceUrl": PUBLIC_URL, "reason": failed["omarchy-releases"]})
    else:
        releases_payload = read_json_bounded(inputs.releases, 4 * 1024 * 1024)
        releases = parse_releases(releases_payload)
        old_releases = previous_sources.get("omarchy-releases", {}).get("releases", {}) if isinstance(previous_sources.get("omarchy-releases"), dict) else {}
        events.extend(diff_releases(old_releases, releases, discovered_at=clock, window_from=window_from))
        next_sources["omarchy-releases"] = {"releases": releases}
        health.append({"id": "omarchy-releases", "status": "current", "checkedAt": checked_at, "sourceUrl": PUBLIC_URL})

    if "marketplace" in failed:
        health.append({"id": "marketplace", "status": "failed", "checkedAt": checked_at, "sourceUrl": CATALOG_URL, "reason": failed["marketplace"]})
    else:
        marketplace_payload = read_json_bounded(inputs.marketplace, 8 * 1024 * 1024)
        marketplace = parse_marketplace(marketplace_payload)
        old_marketplace = previous_sources.get("marketplace") if isinstance(previous_sources.get("marketplace"), dict) else None
        marketplace_events, marketplace_snapshot = diff_marketplace(
            old_marketplace,
            marketplace,
            discovered_at=clock,
            bootstrap=bootstrap_marketplace,
            bootstrap_window_from=clock - timedelta(days=14),
        )
        events.extend(marketplace_events)
        next_sources["marketplace"] = marketplace_snapshot
        health.append({"id": "marketplace", "status": "current", "checkedAt": checked_at, "sourceUrl": CATALOG_URL})

    if "community" in failed:
        health.append({"id": "community", "status": "failed", "checkedAt": checked_at, "sourceUrl": "https://github.com/mtolhuys/omarchy-news-radar/tree/main/content/community", "reason": failed["community"]})
    else:
        community = community_events(inputs.community, discovered_at=clock)
        events.extend(event for event in community if datetime.strptime(event["occurredAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) >= window_from)
        next_sources["community"] = {"recordIds": sorted(event["entity"]["id"] for event in community)}
        health.append({"id": "community", "status": "current", "checkedAt": checked_at, "sourceUrl": "https://github.com/mtolhuys/omarchy-news-radar/tree/main/content/community"})

    retained_events = {
        event["id"]: event
        for event in previous["events"]
        if parse_timestamp(event["occurredAt"]) >= window_from
    }
    retained_events.update({event["id"]: event for event in events})
    base_events = canonical_events(retained_events.values())
    overlays = load_curation(inputs.curation)
    curated_events, lead = apply_curation(base_events, overlays)
    feed = make_feed(
        generated_at=clock,
        window_from=window_from,
        sources=health,
        events=curated_events,
        lead_event_id=lead,
    )
    snapshot = {
        "schemaVersion": SNAPSHOT_SCHEMA,
        "events": base_events,
        "sources": dict(sorted(next_sources.items())),
    }
    return feed, snapshot


def save_snapshot(path: Path, snapshot: Mapping[str, Any]) -> None:
    atomic_write_json(path, validate_snapshot(dict(snapshot)), mode=0o600)


def collect_production(
    *,
    previous_snapshot: Mapping[str, Any],
    community_directory: Path,
    curation_directory: Path,
    now: datetime,
    bootstrap_marketplace: bool,
    github_token: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch only the two allowlisted machine sources, then collect transactionally."""

    failures: dict[str, str] = {}
    release_payload: list[Any] = []
    release_bytes = b"[]"
    catalog_bytes = b'{"generatedAt":"1970-01-01T00:00:00Z","stateSchemaVersion":2,"plugins":[]}'
    try:
        headers = {"X-GitHub-Api-Version": "2022-11-28"}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"
        for page in range(1, 4):
            page_bytes, _, _ = fetch_bytes(
                API_URL + f"?per_page=100&page={page}",
                policy=FetchPolicy(4 * 1024 * 1024, 20.0, frozenset({"https://api.github.com"})),
                headers=headers,
            )
            page_payload = decode_json(page_bytes, label="GitHub releases")
            if not isinstance(page_payload, list) or len(page_payload) > 100:
                raise ValidationError("GitHub releases page is invalid")
            release_payload.extend(page_payload)
            if len(page_payload) < 100:
                break
        else:
            raise ValidationError("GitHub releases pagination bound exceeded")
        parse_releases(release_payload)
        release_bytes = canonical_json_bytes(release_payload)
    except FetchError as exc:
        failures["omarchy-releases"] = exc.reason
    except ValidationError:
        failures["omarchy-releases"] = "schema-mismatch"

    try:
        catalog_bytes, _, _ = fetch_bytes(
            CATALOG_URL,
            policy=FetchPolicy(
                8 * 1024 * 1024,
                30.0,
                frozenset({"https://raw.githubusercontent.com"}),
            ),
        )
        parse_marketplace(decode_json(catalog_bytes, label="marketplace catalog"))
    except FetchError as exc:
        failures["marketplace"] = exc.reason
    except ValidationError:
        failures["marketplace"] = "schema-mismatch"

    with tempfile.TemporaryDirectory(prefix="omarchy-news-radar-collect-") as temporary:
        root = Path(temporary)
        releases_path = root / "releases.json"
        marketplace_path = root / "catalog.json"
        releases_path.write_bytes(release_bytes)
        marketplace_path.write_bytes(catalog_bytes)
        return collect_from_fixtures(
            FixtureInputs(
                releases=releases_path,
                marketplace=marketplace_path,
                community=community_directory,
                curation=curation_directory,
            ),
            previous_snapshot=previous_snapshot,
            now=now,
            bootstrap_marketplace=bootstrap_marketplace,
            failed_sources=failures,
        )
