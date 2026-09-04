"""Transactional orchestration for normalized sources and feed candidates."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .curation import apply_curation, load_curation
from .errors import ValidationError
from .errors import FetchError
from .constants import ENGAGEMENT_MAX_BYTES, GITHUB_MAX_BYTES, MAX_EVENTS
from .http import FetchPolicy, decode_json, fetch_bytes
from .io import atomic_write_json, canonical_json_bytes, read_json_bounded
from .metrics import enrich_event_metrics
from .model import canonical_events, event_sort_key, make_feed
from .sources import (
    community_events,
    diff_marketplace,
    diff_news,
    diff_releases,
    enrich_plugin_descriptions,
    parse_engagement,
    parse_marketplace,
    enrich_omarchy_news,
    parse_news_rss,
    parse_releases,
    parse_search_video_ids,
    parse_videos,
    should_refresh_youtube,
    youtube_events,
)
from .sources.marketplace import CATALOG_URL
from .sources.marketplace_engagement import ENGAGEMENT_URL
from .sources.omarchy_news import MAX_RSS_BYTES, PUBLIC_URL as NEWS_PUBLIC_URL, RSS_ORIGIN, RSS_URL
from .sources.omarchy_releases import API_URL, PUBLIC_URL
from .sources.youtube import (
    API_ORIGIN as YOUTUBE_API_ORIGIN,
    MAX_SECTION_EVENTS,
    PUBLIC_URL as YOUTUBE_PUBLIC_URL,
    SEARCH_QUERIES,
    rank_youtube_events,
    relevance_languages_for_search,
    search_url,
    videos_url,
)
from .validation import format_timestamp, parse_timestamp, validate_event

SNAPSHOT_SCHEMA = 2


@dataclass(frozen=True)
class FixtureInputs:
    releases: Path
    marketplace: Path
    community: Path
    curation: Path
    engagement: Path | None = None
    youtube: Path | None = None
    omarchy_news: Path | None = None


def empty_snapshot() -> dict[str, Any]:
    return {"schemaVersion": SNAPSHOT_SCHEMA, "events": [], "sources": {}}


def validate_snapshot(value: Any) -> dict[str, Any]:
    """Validate persisted continuity without applying age-based retention."""

    if not isinstance(value, dict) or value.get("schemaVersion") != SNAPSHOT_SCHEMA:
        raise ValidationError("source snapshot is invalid")
    sources = value.get("sources")
    events = value.get("events", [])
    if not isinstance(sources, dict) or not isinstance(events, list):
        raise ValidationError("source snapshot is invalid")
    if len(events) > MAX_EVENTS:
        raise ValidationError("source snapshot exceeds event bound")
    normalized_events = [validate_event(event) for event in events]
    event_ids = [event["id"] for event in normalized_events]
    if len(set(event_ids)) != len(event_ids):
        raise ValidationError("source snapshot contains duplicate event IDs")
    if normalized_events != sorted(normalized_events, key=event_sort_key):
        raise ValidationError("source snapshot events are not in canonical order")
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
    news_items_for_enrich: dict[str, dict[str, Any]] | None = None
    health: list[dict[str, Any]] = []
    checked_at = format_timestamp(clock)
    releases: dict[str, dict[str, Any]] | None = None
    marketplace: dict[str, Any] | None = None
    engagement: dict[str, dict[str, int]] | None = None

    if "omarchy-releases" in failed:
        health.append({"id": "omarchy-releases", "status": "failed", "checkedAt": checked_at, "sourceUrl": PUBLIC_URL, "reason": failed["omarchy-releases"]})
    else:
        releases_payload = read_json_bounded(inputs.releases, 4 * 1024 * 1024)
        releases = parse_releases(releases_payload)
        old_releases = previous_sources.get("omarchy-releases", {}).get("releases", {}) if isinstance(previous_sources.get("omarchy-releases"), dict) else {}
        events.extend(diff_releases(old_releases, releases, discovered_at=clock, window_from=window_from))
        next_sources["omarchy-releases"] = {"releases": releases}
        health.append({"id": "omarchy-releases", "status": "current", "checkedAt": checked_at, "sourceUrl": PUBLIC_URL})

    if "omarchy-news" in failed:
        health.append(
            {
                "id": "omarchy-news",
                "status": "failed",
                "checkedAt": checked_at,
                "sourceUrl": NEWS_PUBLIC_URL,
                "reason": failed["omarchy-news"],
            }
        )
    elif inputs.omarchy_news is None:
        previous_news = previous_sources.get("omarchy-news")
        if isinstance(previous_news, dict):
            next_sources["omarchy-news"] = previous_news
            old_news = previous_news.get("items", {})
            if isinstance(old_news, dict) and old_news:
                # Rematerialize from the cached baseline even on not-modified,
                # so Core news evicted from the ledger can return without
                # waiting for the next RSS body change.
                events.extend(
                    diff_news(old_news, old_news, discovered_at=clock, window_from=window_from)
                )
                news_items_for_enrich = dict(old_news)
            health.append(
                {
                    "id": "omarchy-news",
                    "status": "not-modified",
                    "checkedAt": checked_at,
                    "sourceUrl": NEWS_PUBLIC_URL,
                }
            )
    else:
        news_bytes = inputs.omarchy_news.read_bytes()
        news_items = parse_news_rss(news_bytes)
        old_news = (
            previous_sources.get("omarchy-news", {}).get("items", {})
            if isinstance(previous_sources.get("omarchy-news"), dict)
            else {}
        )
        if not isinstance(old_news, dict):
            old_news = {}
        events.extend(diff_news(old_news, news_items, discovered_at=clock, window_from=window_from))
        news_items_for_enrich = news_items
        next_sources["omarchy-news"] = {"items": news_items, "checkedAt": checked_at}
        health.append(
            {
                "id": "omarchy-news",
                "status": "current",
                "checkedAt": checked_at,
                "sourceUrl": NEWS_PUBLIC_URL,
            }
        )

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

    if inputs.engagement is not None:
        if "marketplace-engagement" in failed:
            health.append({"id": "marketplace-engagement", "status": "failed", "checkedAt": checked_at, "sourceUrl": ENGAGEMENT_URL, "reason": failed["marketplace-engagement"]})
        else:
            engagement_payload = read_json_bounded(inputs.engagement, ENGAGEMENT_MAX_BYTES)
            engagement = parse_engagement(engagement_payload)
            next_sources["marketplace-engagement"] = {
                "schemaVersion": 1,
                "pluginCount": len(engagement),
            }
            health.append({"id": "marketplace-engagement", "status": "current", "checkedAt": checked_at, "sourceUrl": ENGAGEMENT_URL})

    if "community" in failed:
        health.append({"id": "community", "status": "failed", "checkedAt": checked_at, "sourceUrl": "https://github.com/mtolhuys/omarchy-news-radar/tree/main/content/community", "reason": failed["community"]})
    else:
        community = community_events(inputs.community, discovered_at=clock)
        events.extend(event for event in community if datetime.strptime(event["occurredAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) >= window_from)
        next_sources["community"] = {"recordIds": sorted(event["entity"]["id"] for event in community)}
        health.append({"id": "community", "status": "current", "checkedAt": checked_at, "sourceUrl": "https://github.com/mtolhuys/omarchy-news-radar/tree/main/content/community"})

    youtube_success = False
    previous_youtube = previous_sources.get("youtube") if isinstance(previous_sources.get("youtube"), dict) else None
    if "youtube" in failed:
        health.append(
            {
                "id": "youtube",
                "status": "failed",
                "checkedAt": checked_at,
                "sourceUrl": YOUTUBE_PUBLIC_URL,
                "reason": failed["youtube"],
            }
        )
    elif inputs.youtube is None:
        # Absent fixture keeps the source out of CI editions unless a prior
        # snapshot already carries YouTube continuity.
        if previous_youtube is not None:
            next_sources["youtube"] = previous_youtube
            health.append(
                {
                    "id": "youtube",
                    "status": "not-modified",
                    "checkedAt": checked_at,
                    "sourceUrl": YOUTUBE_PUBLIC_URL,
                }
            )
    else:
        youtube_payload = read_json_bounded(inputs.youtube, GITHUB_MAX_BYTES)
        if not isinstance(youtube_payload, dict) or not isinstance(youtube_payload.get("videos"), list):
            raise ValidationError("YouTube fixture payload is invalid")
        video_records = youtube_payload["videos"]
        fresh_events = youtube_events(video_records, discovered_at=clock, observed_at=checked_at)
        events.extend(
            event
            for event in fresh_events
            if parse_timestamp(event["occurredAt"]) >= window_from
        )
        next_sources["youtube"] = {
            "checkedAt": checked_at,
            "videoIds": [event["entity"]["id"] for event in fresh_events],
        }
        health.append(
            {
                "id": "youtube",
                "status": "current",
                "checkedAt": checked_at,
                "sourceUrl": YOUTUBE_PUBLIC_URL,
            }
        )
        youtube_success = True

    retained_events = {
        event["id"]: event
        for event in previous["events"]
        if parse_timestamp(event["occurredAt"]) >= window_from
    }
    # A stale source baseline may rediscover the same deterministic event. Its
    # first observed timestamps remain authoritative for non-YouTube rows.
    # Fresh YouTube rows overwrite so views/likes refresh, and we never wipe
    # the whole lane on a thin refresh (that previously left Core YouTube at 2).
    for event in events:
        if event.get("type") == "youtube-video":
            retained_events[event["id"]] = event
        else:
            retained_events.setdefault(event["id"], event)

    if youtube_success:
        youtube_rows = [
            event
            for event in retained_events.values()
            if event.get("type") == "youtube-video"
            or (event.get("classification") or {}).get("section") == "youtube"
        ]
        kept_ids = {event["id"] for event in rank_youtube_events(youtube_rows)[:MAX_SECTION_EVENTS]}
        retained_events = {
            event_id: event
            for event_id, event in retained_events.items()
            if event.get("type") != "youtube-video"
            and (event.get("classification") or {}).get("section") != "youtube"
            or event_id in kept_ids
        }
        next_sources["youtube"] = {
            "checkedAt": checked_at,
            "videoIds": [
                str((event.get("entity") or {}).get("id"))
                for event in rank_youtube_events(
                    [
                        event
                        for event in retained_events.values()
                        if event.get("type") == "youtube-video"
                    ]
                )
                if (event.get("entity") or {}).get("id")
            ],
        }

    base_events = canonical_events(
        enrich_event_metrics(
            enrich_omarchy_news(
                enrich_plugin_descriptions(retained_events.values(), marketplace),
                news_items_for_enrich,
            ),
            observed_at=checked_at,
            marketplace=marketplace,
            engagement=engagement,
            releases=releases,
        ),
        now=clock,
    )
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
    youtube_api_key: str | None = None,
    youtube_preferred_languages: Sequence[str] | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch allowlisted machine sources, then collect transactionally."""

    failures: dict[str, str] = {}
    release_payload: list[Any] = []
    release_bytes = b"[]"
    catalog_bytes = b'{"generatedAt":"1970-01-01T00:00:00Z","stateSchemaVersion":2,"plugins":[]}'
    engagement_bytes = b'{"schemaVersion":1,"plugins":{}}'
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

    try:
        engagement_bytes, _, _ = fetch_bytes(
            ENGAGEMENT_URL,
            policy=FetchPolicy(
                ENGAGEMENT_MAX_BYTES,
                20.0,
                frozenset({"https://api.omarchyplugins.com"}),
            ),
            headers={"Accept": "application/json", "User-Agent": "omarchy-news-radar-collector/0.1"},
        )
        parse_engagement(decode_json(engagement_bytes, label="marketplace engagement"))
    except FetchError as exc:
        failures["marketplace-engagement"] = exc.reason
    except ValidationError:
        failures["marketplace-engagement"] = "schema-mismatch"

    news_bytes: bytes | None = None
    try:
        fetched_news, _, _ = fetch_bytes(
            RSS_URL,
            policy=FetchPolicy(MAX_RSS_BYTES, 20.0, frozenset({RSS_ORIGIN})),
            headers={
                "Accept": "application/rss+xml, application/xml, text/xml",
                "User-Agent": "omarchy-news-radar-collector/0.4",
            },
        )
        parse_news_rss(fetched_news)
        news_bytes = bytes(fetched_news)
    except FetchError as exc:
        failures["omarchy-news"] = exc.reason
    except ValidationError:
        failures["omarchy-news"] = "schema-mismatch"

    youtube_bytes: bytes | None = None
    previous_sources = previous_snapshot.get("sources", {}) if isinstance(previous_snapshot, Mapping) else {}
    previous_youtube = previous_sources.get("youtube") if isinstance(previous_sources, Mapping) else None
    if not youtube_api_key:
        failures["youtube"] = "validation-failed"
    elif not should_refresh_youtube(previous_youtube if isinstance(previous_youtube, Mapping) else None, now=now):
        # Keep prior YouTube continuity inside the cadence window.
        pass
    else:
        try:
            video_ids: list[str] = []
            seen_ids: set[str] = set()
            policy = FetchPolicy(GITHUB_MAX_BYTES, 20.0, frozenset({YOUTUBE_API_ORIGIN}))
            for relevance_language in relevance_languages_for_search(
                youtube_preferred_languages
            ):
                for query in SEARCH_QUERIES:
                    page_bytes, _, _ = fetch_bytes(
                        search_url(
                            query=query,
                            api_key=youtube_api_key,
                            relevance_language=relevance_language,
                        ),
                        policy=policy,
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "omarchy-news-radar-collector/0.4",
                        },
                    )
                    for video_id in parse_search_video_ids(
                        decode_json(page_bytes, label="YouTube search")
                    ):
                        if video_id not in seen_ids:
                            seen_ids.add(video_id)
                            video_ids.append(video_id)
            videos: list[dict[str, Any]] = []
            for offset in range(0, len(video_ids), 50):
                chunk = video_ids[offset : offset + 50]
                if not chunk:
                    break
                page_bytes, _, _ = fetch_bytes(
                    videos_url(video_ids=chunk, api_key=youtube_api_key),
                    policy=policy,
                    headers={"Accept": "application/json", "User-Agent": "omarchy-news-radar-collector/0.4"},
                )
                videos.extend(parse_videos(decode_json(page_bytes, label="YouTube videos")))
            youtube_bytes = canonical_json_bytes({"videos": videos})
        except FetchError as exc:
            failures["youtube"] = exc.reason
        except ValidationError:
            failures["youtube"] = "schema-mismatch"

    with tempfile.TemporaryDirectory(prefix="omarchy-news-radar-collect-") as temporary:
        root = Path(temporary)
        releases_path = root / "releases.json"
        marketplace_path = root / "catalog.json"
        engagement_path = root / "engagement.json"
        youtube_path = root / "youtube.json" if youtube_bytes is not None else None
        news_path = root / "omarchy-news.xml" if news_bytes is not None else None
        releases_path.write_bytes(release_bytes)
        marketplace_path.write_bytes(catalog_bytes)
        engagement_path.write_bytes(engagement_bytes)
        if youtube_path is not None and youtube_bytes is not None:
            youtube_path.write_bytes(youtube_bytes)
        if news_path is not None and news_bytes is not None:
            news_path.write_bytes(news_bytes)
        return collect_from_fixtures(
            FixtureInputs(
                releases=releases_path,
                marketplace=marketplace_path,
                community=community_directory,
                curation=curation_directory,
                engagement=engagement_path,
                youtube=youtube_path,
                omarchy_news=news_path,
            ),
            previous_snapshot=previous_snapshot,
            now=now,
            bootstrap_marketplace=bootstrap_marketplace,
            failed_sources=failures,
        )
