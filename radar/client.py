"""Small versioned interface consumed by QML."""

from __future__ import annotations

import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode, urljoin, urlsplit

from .constants import CLIENT_SECTIONS, FEED_MAX_BYTES, FEED_ORIGIN, FEED_URL, HELPER_PROTOCOL_VERSION, MARKETPLACE_IMAGE_ORIGIN, YOUTUBE_IMAGE_ORIGIN
from .errors import FetchError, RadarError, StorageError, ValidationError
from .filters import apply_section_filter, filter_options, filter_summary
from .freshness import edition_timing, update_message
from .sections import SECTION_SOURCE_SUMMARIES, visible_client_sections
from .http import FetchPolicy, decode_json, fetch_bytes
from .io import read_json_bounded
from .local_edition import local_edition_metadata, local_image_url
from .model import project_section
from .reading import article_segments, list_summary
from .state import (
    RefreshLock,
    StateLock,
    event_is_read,
    feed_cached_at,
    load_feed,
    load_state,
    load_update_check,
    purge,
    save_feed,
    save_state,
    save_update_check,
    set_event_read,
    set_events_read,
    toggle_saved,
    update_preferences,
    update_section_filter,
)
from .validation import EVENT_ID_RE, parse_timestamp, validate_feed, validate_https_url

MARKETPLACE_PLUGIN_PAGE = "https://plugins.omarchy.org/plugin.html"


def response(status: str, **values: Any) -> dict[str, Any]:
    return {"protocolVersion": HELPER_PROTOCOL_VERSION, "status": status, **values}


def read_model(environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    clock = now or datetime.now(timezone.utc)
    feed = load_feed(environment, now=clock)
    state, quarantined = load_state(environment)
    if feed is None:
        return response("first-use", feed=None, state=state, quarantine=quarantined)
    local = local_edition_metadata(feed, environment)
    return response(
        "cached",
        feed=feed,
        state=state,
        quarantine=quarantined,
        editionMode="local" if local else "published",
        localEdition=local,
        timing=edition_timing(feed, now=clock, cached_at=feed_cached_at(environment)),
    )


def _test_feed(environment: Mapping[str, str]) -> dict[str, Any] | None:
    if environment.get("OMARCHY_NEWS_RADAR_TEST_MODE") != "1":
        return None
    path = environment.get("OMARCHY_NEWS_RADAR_TEST_FEED")
    url = environment.get("OMARCHY_NEWS_RADAR_TEST_FEED_URL")
    if path and url:
        raise ValidationError("test feed path and URL are mutually exclusive")
    if path:
        return read_json_bounded(Path(path), FEED_MAX_BYTES)
    if url:
        try:
            timeout = float(environment.get("OMARCHY_NEWS_RADAR_TEST_TIMEOUT_SECONDS", "1"))
        except ValueError as exc:
            raise ValidationError("test timeout is invalid") from exc
        if not 0.05 <= timeout <= 5.0:
            raise ValidationError("test timeout is outside its bound")
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        data, _, _ = fetch_bytes(
            url,
            policy=FetchPolicy(
                FEED_MAX_BYTES,
                timeout,
                frozenset({origin}),
                allow_loopback_http=True,
            ),
            headers={"Accept": "application/json", "User-Agent": "omarchy-news-radar-client/0.1"},
        )
        return decode_json(data, label="test feed")
    raise ValidationError("test mode requires an explicit fixture path or loopback URL")


def _fetch_feed(*, timeout: float = 12.0) -> dict[str, Any]:
    """Fetch production feed with a fixed URL and closed redirect origin."""

    policy = FetchPolicy(FEED_MAX_BYTES, timeout, frozenset({FEED_ORIGIN}))
    data, _, _ = fetch_bytes(
        FEED_URL,
        policy=policy,
        headers={"Accept": "application/json", "User-Agent": "omarchy-news-radar-client/0.1"},
    )
    return decode_json(data, label="feed")

def _youtube_event_count(feed: Mapping[str, Any] | None) -> int:
    if not isinstance(feed, Mapping):
        return 0
    events = feed.get("events")
    if not isinstance(events, list):
        return 0
    return sum(1 for event in events if isinstance(event, Mapping) and event.get("type") == "youtube-video")


def _should_adopt_published_for_youtube(
    cached: Mapping[str, Any] | None,
    validated: Mapping[str, Any],
    *,
    local_edition: bool,
) -> bool:
    """Adopt an older published edition when a local live edition lacks YouTube.

    D029 still refuses ordinary published downgrades. This narrow exception only
    applies while a digest-matched local edition has zero youtube-video events
    and the validated published candidate has at least one, so Check for updates
    can fill the YouTube section from Forge without waiting for generatedAt.
    """
    if not local_edition or cached is None:
        return False
    return _youtube_event_count(cached) == 0 and _youtube_event_count(validated) > 0


def refresh(environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    env = dict(environment or os.environ)
    clock = now or datetime.now(timezone.utc)
    cached = load_feed(env, now=clock)
    local = local_edition_metadata(cached, env)
    try:
        with RefreshLock(env):
            try:
                save_update_check("failed", env, now=clock)
            except (RadarError, OSError):
                pass
            candidate = _test_feed(env)
            if candidate is None:
                candidate = _fetch_feed()
            validated = validate_feed(candidate, now=clock, public_only=True)
            published_timing = edition_timing(validated, now=clock)
            candidate_is_newer = cached is None or (
                parse_timestamp(validated["generatedAt"])
                > parse_timestamp(cached["generatedAt"])
            )
            adopt_for_youtube = _should_adopt_published_for_youtube(
                cached,
                validated,
                local_edition=local is not None,
            )
            if candidate_is_newer or adopt_for_youtube:
                previous_ids = {event["id"] for event in cached["events"]} if cached else set()
                new_stories = sum(event["id"] not in previous_ids for event in validated["events"])
                selected = save_feed(validated, env, now=clock)
                edition_mode = "published"
                local = None
                edition_changed = True
                cache_preserved = False
            else:
                selected = cached or validated
                edition_mode = "local" if local is not None else "published"
                new_stories = 0
                edition_changed = False
                cache_preserved = cached is not None

            if published_timing["publisherStale"]:
                status = "stale-publication"
            elif edition_changed:
                status = "updated"
            elif local is not None:
                status = "local-current"
            else:
                status = "no-change"
            selected_timing = edition_timing(
                selected,
                now=clock,
                cached_at=feed_cached_at(env),
            )
            try:
                save_update_check("success", env, now=clock)
            except (RadarError, OSError):
                pass
        return response(
            status,
            feed=selected,
            cachePreserved=cache_preserved,
            editionMode=edition_mode,
            localEdition=local,
            publishedGeneratedAt=validated["generatedAt"],
            newStories=new_stories,
            editionChanged=edition_changed,
            timing=selected_timing,
            publishedTiming=published_timing,
            message=update_message(
                status,
                timing=published_timing,
                new_stories=new_stories,
                local_edition=edition_mode == "local",
            ),
        )
    except (RadarError, OSError) as exc:
        reason = exc.reason if isinstance(exc, FetchError) else "validation-failed" if isinstance(exc, ValidationError) else "local-error"
        invalid_candidate = isinstance(exc, ValidationError) or (
            isinstance(exc, FetchError) and exc.reason in {"invalid-json", "too-large"}
        )
        status = "invalid-feed" if invalid_candidate else "offline"
        cache_timing = (
            edition_timing(cached, now=clock, cached_at=feed_cached_at(env))
            if cached is not None
            else None
        )
        return response(
            status,
            reason=reason,
            detail=str(exc),
            feed=cached,
            cachePreserved=cached is not None,
            editionMode="local" if local is not None else "published",
            localEdition=local,
            newStories=0,
            editionChanged=False,
            timing=cache_timing,
            message=update_message(status, timing=cache_timing, local_edition=local is not None),
        )


def toggle_saved_state(event_id: str, environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    feed = load_feed(environment, now=now)
    if feed is None:
        raise ValidationError("cannot save an event without a valid cached feed")
    event = next((item for item in feed["events"] if item["id"] == event_id), None)
    if event is None:
        raise ValidationError("event is not present in the validated cache")
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        updated, saved = toggle_saved(state, event, now=now)
        save_state(updated, environment)
    return response("ok", saved=saved, state=updated)


def set_event_read_state(
    event_id: str,
    read: bool,
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Persist one explicit story state against the validated current edition."""

    feed = load_feed(environment, now=now)
    if feed is None:
        raise ValidationError("cannot change reading state without a valid cached feed")
    events_by_id = {item["id"]: item for item in feed["events"]}
    event = events_by_id.get(event_id)
    if event is None:
        state, _ = load_state(environment)
        return response(
            "stale-event",
            message="The story changed during refresh; the current edition was left unchanged.",
            state=state,
        )
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        updated = set_event_read(
            state,
            event,
            read,
            current_event_ids=set(events_by_id),
        )
        saved = save_state(updated, environment)
    return response("ok", read=event_is_read(saved, event), state=saved)


def mark_section_read_state(
    section: str,
    installed_json: str,
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Atomically mark unread stories in one persistently filtered section read."""

    installed = _parse_installed_plugin_ids(installed_json)
    if section not in CLIENT_SECTIONS:
        raise ValidationError("unknown projection section")
    feed = load_feed(environment, now=now)
    if feed is None:
        raise ValidationError("cannot change reading state without a valid cached feed")
    current_event_ids = {item["id"] for item in feed["events"]}
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        section_events = _filtered_section_events(
            feed,
            state,
            section,
            installed,
            now=now,
        )
        unread_events = [
            event for event in section_events if not event_is_read(state, event)
        ]
        updated = set_events_read(
            state,
            unread_events,
            True,
            current_event_ids=current_event_ids,
        )
        saved = save_state(updated, environment)
    return response(
        "ok",
        section=section,
        markedRead=len(unread_events),
        state=saved,
    )


def set_preferences(
    *,
    bar_visible: bool | None = None,
    images_visible: bool | None = None,
    section_visibility: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        updated = update_preferences(
            state,
            bar_visible=bar_visible,
            images_visible=images_visible,
            section_visibility=section_visibility,
        )
        saved = save_state(updated, environment)
    return response(
        "ok",
        state=saved,
        visibleSections=list(visible_client_sections(saved["preferences"]["sectionVisibility"])),
    )


def set_section_filter(
    section: str,
    value: Mapping[str, Any],
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Persist one strictly validated, local-only section filter."""

    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        updated = update_section_filter(state, section, value)
        saved = save_state(updated, environment)
    return response("ok", state=saved)


def indicator_model(
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
    installed_json: str = "[]",
) -> dict[str, Any]:
    clock = now or datetime.now(timezone.utc)
    feed = load_feed(environment, now=clock)
    state, quarantined = load_state(environment)
    preferences = state["preferences"]
    update_check = load_update_check(environment, now=clock)
    if feed is None:
        return response(
            "first-use",
            unread=0,
            health="empty",
            barVisible=preferences["barVisible"],
            quarantine=quarantined,
            lastUpdateCheck=update_check,
            visibleSections=list(visible_client_sections(preferences["sectionVisibility"])),
        )
    installed = _parse_installed_plugin_ids(installed_json)
    section_events = _persistent_section_events(
        feed,
        state,
        installed,
        now=clock,
    )
    unread_ids = {
        event_id
        for events in section_events.values()
        for event_id in _unread_event_ids(state, events)
    }
    timing = edition_timing(feed, now=clock, cached_at=feed_cached_at(environment))
    health = "partial" if any(source["status"] == "failed" for source in feed["sources"]) else "publisher-stale" if timing["publisherStale"] else "source-stale" if any(source["status"] == "stale" for source in feed["sources"]) else "current"
    return response(
        "ok",
        unread=len(unread_ids),
        health=health,
        generatedAt=feed["generatedAt"],
        barVisible=preferences["barVisible"],
        quarantine=quarantined,
        publisherStale=timing["publisherStale"],
        timing=timing,
        lastUpdateCheck=update_check,
        visibleSections=list(visible_client_sections(preferences["sectionVisibility"])),
    )


def refresh_if_due(
    minimum_age: int,
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not 300 <= minimum_age <= 86400:
        raise ValidationError("minimum refresh age is outside its bound")
    clock = now or datetime.now(timezone.utc)
    cached = load_feed(environment, now=clock)
    update_check = load_update_check(environment, now=clock)
    checked_at = (
        parse_timestamp(update_check["checkedAt"])
        if update_check
        else feed_cached_at(environment)
    )
    due_after = (
        min(minimum_age, 300)
        if update_check and update_check["outcome"] == "failed"
        else minimum_age
    )
    if checked_at is not None:
        age = max(0.0, (clock - checked_at).total_seconds())
        if age < due_after:
            return response(
                "not-due",
                feed=cached,
                cachePreserved=cached is not None,
                timing=edition_timing(cached, now=clock, cached_at=feed_cached_at(environment))
                if cached is not None else None,
                nextCheckInSeconds=max(1, math.ceil(due_after - age)),
                lastUpdateCheck=update_check,
            )
    result = refresh(environment, now=clock)
    result["nextCheckInSeconds"] = (
        min(minimum_age, 300)
        if result["status"] in {"offline", "invalid-feed"}
        else minimum_age
    )
    return result


def installed_plugins() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["omarchy-shell", "shell", "listPlugins"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return response("unavailable", pluginIds=[])
    if completed.returncode != 0 or len(completed.stdout) > 1024 * 1024:
        return response("unavailable", pluginIds=[])
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return response("unavailable", pluginIds=[])
    if isinstance(payload, list):
        values = payload
    elif isinstance(payload, dict) and isinstance(payload.get("plugins"), list):
        values = payload["plugins"]
    else:
        return response("unavailable", pluginIds=[])
    if len(values) > 5000:
        return response("unavailable", pluginIds=[])
    ids = [
        item["id"]
        for item in values
        if isinstance(item, dict)
        and item.get("enabled") is True
        and isinstance(item.get("id"), str)
        and 1 <= len(item["id"]) <= 160
    ]
    return response("ok", pluginIds=sorted(set(ids))[:500])


def _parse_installed_plugin_ids(installed_json: str) -> list[str]:
    if len(installed_json) > 256 * 1024:
        raise ValidationError("installed plugin IDs exceed their bound")
    try:
        installed_raw = json.loads(installed_json)
    except json.JSONDecodeError as exc:
        raise ValidationError("installed plugin IDs are invalid JSON") from exc
    if not isinstance(installed_raw, list) or len(installed_raw) > 5000:
        raise ValidationError("installed plugin IDs are invalid")
    installed: list[str] = []
    for item in installed_raw:
        if not isinstance(item, str) or not 1 <= len(item) <= 160:
            raise ValidationError("installed plugin ID is invalid")
        installed.append(item)
    return installed


def _parse_retained_read_ids(retained_read_ids_json: str) -> list[str]:
    if len(retained_read_ids_json) > 16 * 1024:
        raise ValidationError("retained read IDs exceed their bound")
    try:
        retained_raw = json.loads(retained_read_ids_json)
    except json.JSONDecodeError as exc:
        raise ValidationError("retained read IDs are invalid JSON") from exc
    if not isinstance(retained_raw, list) or len(retained_raw) > 500:
        raise ValidationError("retained read IDs are invalid")
    retained: list[str] = []
    for item in retained_raw:
        if not isinstance(item, str) or not EVENT_ID_RE.fullmatch(item):
            raise ValidationError("retained read ID is invalid")
        retained.append(item)
    return sorted(set(retained))


def _filtered_section_events(
    feed: Mapping[str, Any],
    state: Mapping[str, Any],
    section: str,
    installed_plugin_ids: list[str],
    *,
    query: str = "",
    retained_read_ids: list[str] | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    if section not in CLIENT_SECTIONS:
        raise ValidationError("unknown projection section")
    section_filter = state["preferences"]["sectionFilters"][section]
    return apply_section_filter(
        project_section(
            feed,
            section,
            installed_plugin_ids=installed_plugin_ids,
            saved_ids=set(state["saved"]),
            query=query,
        ),
        section_filter,
        read_through=state["readThrough"],
        read_overrides=state["readOverrides"],
        retained_read_ids=retained_read_ids or (),
        now=now,
    )


def _persistent_section_events(
    feed: Mapping[str, Any],
    state: Mapping[str, Any],
    installed_plugin_ids: list[str],
    *,
    now: datetime | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Project every locally visible section through its persisted filter once.

    A rail hidden in Tune is not a reachable destination, so it contributes no
    count and cannot keep the top-bar newspaper active (D044/D050). Saved keeps
    every bookmark, including stories from a hidden rail.
    """

    return {
        section: _filtered_section_events(
            feed,
            state,
            section,
            installed_plugin_ids,
            now=now,
        )
        for section in visible_client_sections(state["preferences"]["sectionVisibility"])
    }


def _unread_event_ids(
    state: Mapping[str, Any], events: list[dict[str, Any]]
) -> set[str]:
    return {
        event["id"] for event in events if not event_is_read(state, event)
    }


def projection_model(
    section: str,
    installed_json: str,
    query: str,
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
    limit: int = 12,
    retained_read_ids_json: str = "[]",
) -> dict[str, Any]:
    if len(query) > 100:
        raise ValidationError("projection input exceeds its bound")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise ValidationError("projection limit is outside its bound")
    installed = _parse_installed_plugin_ids(installed_json)
    retained_read_ids = _parse_retained_read_ids(retained_read_ids_json)
    feed = load_feed(environment, now=now)
    state, _ = load_state(environment)
    names = CLIENT_SECTIONS
    if section not in names:
        raise ValidationError("unknown projection section")
    filters = state["preferences"]["sectionFilters"]
    current_filter = filters[section]
    if feed is None:
        return response(
            "first-use",
            section=section,
            events=[],
            counts={name: 0 for name in names},
            unreadCounts={name: 0 for name in names},
            totalEvents=0,
            hasMore=False,
            limit=limit,
            filter=current_filter,
            filterSummary=filter_summary(current_filter),
            sectionSources=SECTION_SOURCE_SUMMARIES[section],
            filterOptions=filter_options(section),
            visibleSections=list(visible_client_sections(state["preferences"]["sectionVisibility"])),
        )
    saved_ids = set(state["saved"])
    section_events = _persistent_section_events(feed, state, installed, now=now)
    # Hidden rails report zero instead of disappearing, so the response shape
    # stays stable for every client build.
    counts = {name: len(section_events.get(name, ())) for name in names}
    unread_counts = {
        name: len(_unread_event_ids(state, section_events.get(name, [])))
        for name in names
    }
    events = _filtered_section_events(
        feed,
        state,
        section,
        installed,
        query=query,
        retained_read_ids=retained_read_ids,
        now=now,
    )
    total_events = len(events)
    events = events[:limit]
    env = dict(environment or os.environ)
    image_base = FEED_URL
    local = local_edition_metadata(feed, env)
    if env.get("OMARCHY_NEWS_RADAR_TEST_MODE") == "1" and env.get("OMARCHY_NEWS_RADAR_TEST_FEED_URL"):
        image_base = env["OMARCHY_NEWS_RADAR_TEST_FEED_URL"]
    decorated: list[dict[str, Any]] = []
    metric_labels = {
        "marketplace-views": "Views",
        "marketplace-hearts": "Hearts",
        "marketplace-copies": "Command copies",
        "repository-stars": "Repository stars",
        "release-asset-downloads": "Release asset downloads",
        "youtube-views": "Views",
        "youtube-likes": "Likes",
    }
    metric_order = tuple(metric_labels)
    for event in events:
        item = dict(event)
        item["isUnread"] = not event_is_read(state, item)
        item["isSaved"] = item["id"] in saved_ids
        # Cards stay scannable. The inspector keeps the full 0.4.14 body.
        item["listSummary"] = list_summary(item.get("summary"), item.get("title", ""))
        item["summarySegments"] = article_segments(item.get("summary"))
        image = item.get("image")
        # Verification flips reused marketplace marketing art; hide it in the
        # reader even for historical feed rows that still carry image metadata.
        if item.get("type") == "plugin-verification-changed":
            image = None
        if state["preferences"]["imagesVisible"] and isinstance(image, dict):
            source_url = image.get("sourceUrl")
            if isinstance(source_url, str) and (
                source_url.startswith(MARKETPLACE_IMAGE_ORIGIN + "/")
                or source_url.startswith(YOUTUBE_IMAGE_ORIGIN + "/")
            ):
                item["imageUrl"] = source_url
            elif "path" in image:
                # Legacy mirrored editions / local private caches.
                if local is not None:
                    cached_url = local_image_url(str(image["path"]), env)
                    if cached_url:
                        item["imageUrl"] = cached_url
                else:
                    item["imageUrl"] = urljoin(image_base, image["path"])
        entity = item.get("entity")
        if isinstance(entity, dict) and entity.get("kind") == "plugin":
            item["marketplaceUrl"] = validate_https_url(
                f"{MARKETPLACE_PLUGIN_PAGE}?{urlencode({'id': entity['id']})}",
                "plugin marketplace URL",
            )
        metrics = item.get("metrics", [])
        if isinstance(metrics, list) and metrics:
            by_id = {
                metric["id"]: metric
                for metric in metrics
                if isinstance(metric, dict) and metric.get("id") in metric_labels
            }
            ordered = [by_id[metric_id] for metric_id in metric_order if metric_id in by_id]
            item["metricItems"] = [
                {
                    "id": metric["id"],
                    "label": metric_labels[metric["id"]],
                    "valueText": f"{metric['value']:,}",
                }
                for metric in ordered
            ]
            item["metricsObservedAt"] = max(metric["observedAt"] for metric in ordered)
            if any(metric["id"].startswith("marketplace-") for metric in ordered):
                item["metricsCaveat"] = (
                    "Marketplace views, hearts, and command copies are anonymous aggregate "
                    "interactions—not installs, downloads, unique people, rankings, votes, "
                    "or security signals."
                )
        # The feed retains metric provenance for audits. The presentation model
        # intentionally exposes only inert display facts, never raw aggregate
        # endpoint links that are not useful reading destinations.
        item.pop("metrics", None)
        decorated.append(item)
    return response(
        "ok",
        section=section,
        events=decorated,
        counts=counts,
        unreadCounts=unread_counts,
        readThrough=state["readThrough"],
        totalEvents=total_events,
        hasMore=total_events > len(decorated),
        retainedReadCount=sum(
            item["id"] in retained_read_ids and not item["isUnread"]
            for item in decorated
        ),
        limit=limit,
        filter=current_filter,
        filterSummary=filter_summary(current_filter),
        sectionSources=SECTION_SOURCE_SUMMARIES[section],
        filterOptions=filter_options(section),
        visibleSections=list(visible_client_sections(state["preferences"]["sectionVisibility"])),
    )


def open_source(url: str) -> dict[str, Any]:
    validated = validate_https_url(url, "source URL")
    completed = subprocess.Popen(
        ["uwsm-app", "--", "xdg-open", validated],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return response("ok", pid=completed.pid)


def purge_state(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    with StateLock(environment):
        removed = purge(environment)
    return response("ok", removed=removed)


def require_unprivileged() -> None:
    if os.geteuid() == 0:
        raise StorageError("news-radar-client refuses to run as root")
