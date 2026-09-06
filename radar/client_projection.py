"""Local reading projections, bounded insight decoration, and badge counts."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Mapping

from .briefing import feed_membership_digest
from .client_briefing import _briefing_rows, _briefing_status
from .client_common import _parse_installed_plugin_ids, response
from .client_insights import compact_project, insight_projection, load_insights
from .client_presentation import decorate_events
from .client_setup import parse_installed_facts
from .constants import CLIENT_SECTIONS, FEED_URL
from .errors import ValidationError
from .filters import apply_section_filter, filter_options, filter_summary
from .freshness import edition_timing
from .insights import matching_release
from .local_edition import local_edition_metadata
from .model import project_section
from .provenance import project_matches_event_source, release_matches_event_source
from .relevance import event_relevance, is_followed, is_muted
from .sections import SECTION_SOURCE_SUMMARIES, visible_client_sections
from .state import StateLock, event_is_read, feed_cached_at, load_feed, load_state, load_update_check
from .validation import EVENT_ID_RE

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
    respect_mutes: bool = True,
) -> list[dict[str, Any]]:
    if section not in CLIENT_SECTIONS:
        raise ValidationError("unknown projection section")
    if section == "front-page":
        return _briefing_rows(feed, state, query=query, retained_read_ids=retained_read_ids, now=now)
    section_filter = state["preferences"]["sectionFilters"][section]
    scoped = dict(feed)
    scoped["events"] = [
        event
        for event in feed["events"]
        if section == "saved" or not respect_mutes or not is_muted(event, state)
    ]
    projection_section = section
    if section == "for-you":
        scoped["events"] = [event for event in scoped["events"]
                            if (event["entity"]["kind"] == "plugin" and event["entity"]["id"] in installed_plugin_ids)
                            or is_followed(event, state)]
        # Saved's projector is an identity filter without a source boundary.
        projection_section = "saved"
    return apply_section_filter(
        project_section(
            scoped,
            projection_section,
            installed_plugin_ids=installed_plugin_ids,
            saved_ids={event["id"] for event in scoped["events"]} if section == "for-you" else set(state["saved"]),
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
    result: set[str] = set()
    for event in events:
        if "briefingEvents" in event:
            result.update(member["id"] for member in event["briefingEvents"] if member["isUnread"])
        elif not event_is_read(state, event):
            result.add(event["id"])
    return result


def projection_model(
    section: str,
    installed_json: str,
    query: str,
    environment: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
    limit: int = 12,
    retained_read_ids_json: str = "[]",
    installed_facts_json: str = "[]",
    installed_facts_available: bool = True,
) -> dict[str, Any]:
    if len(query) > 100:
        raise ValidationError("projection input exceeds its bound")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise ValidationError("projection limit is outside its bound")
    installed = _parse_installed_plugin_ids(installed_json)
    retained_read_ids = _parse_retained_read_ids(retained_read_ids_json)
    installed_facts = parse_installed_facts(installed_facts_json)
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        feed = load_feed(environment, now=now)
    insights = load_insights(environment, now=now)
    known_names = {}
    for event in (feed or {}).get("events", []):
        known_names.setdefault(event["entity"]["id"], event["entity"]["name"])
    extra = insight_projection(insights, state, installed, installed_facts, query=query,
                               installed_facts_available=installed_facts_available, known_names=known_names)
    context = {
        **extra,
        "state": state,
        "onboardingComplete": state["onboardingComplete"],
        "feedDigest": feed_membership_digest(feed) if feed else "",
        "feedEventCount": len(feed["events"]) if feed else 0,
        "briefing": _briefing_status(feed, state, installed, now=now),
    }
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
            **context,
        )
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
    blocking_mutes: list[dict[str, Any]] = []
    muted_event_count = 0
    if not events and section != "saved":
        unmuted_events = _filtered_section_events(
            feed,
            state,
            section,
            installed,
            query=query,
            retained_read_ids=retained_read_ids,
            now=now,
            respect_mutes=False,
        )
        muted_event_count = len(unmuted_events)
        seen_mutes: set[tuple[str, str]] = set()
        for event in unmuted_events:
            for target in event_relevance(event, state):
                key = (str(target["kind"]), str(target["id"]))
                if target["muted"] and key not in seen_mutes:
                    blocking_mutes.append(target)
                    seen_mutes.add(key)
    total_events = len(events)
    events = events[:limit]
    env = dict(environment or os.environ)
    image_base = FEED_URL
    local = local_edition_metadata(feed, env)
    if env.get("OMARCHY_NEWS_RADAR_TEST_MODE") == "1" and env.get("OMARCHY_NEWS_RADAR_TEST_FEED_URL"):
        image_base = env["OMARCHY_NEWS_RADAR_TEST_FEED_URL"]
    decorated = decorate_events(events, state, local=local, image_base=image_base, env=env)
    project_by_id = {item["id"]: item for item in extra["insights"]["projectDetails"] + extra["mySetup"]}
    insight_projects = {item["id"]: item for item in (insights or {}).get("projects", [])}
    for item in decorated:
        project = project_by_id.get(item["entity"]["id"])
        if project and not project_matches_event_source(item, project):
            project = None
        item["projectInsight"] = compact_project(project) if project else None
        item["relevanceTargets"] = event_relevance(item, state, insight_projects if project else None)
        release = matching_release((project or {}).get("releases", []), item["entity"].get("version"))
        item["releaseInsight"] = release if release and release_matches_event_source(item, project, release) else None
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
        blockingMutes=blocking_mutes,
        mutedEventCount=muted_event_count,
        limit=limit,
        filter=current_filter,
        filterSummary=filter_summary(current_filter),
        sectionSources=SECTION_SOURCE_SUMMARIES[section],
        filterOptions=filter_options(section),
        visibleSections=list(visible_client_sections(state["preferences"]["sectionVisibility"])),
        **context,
    )


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
