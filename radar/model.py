"""Deterministic event identities and local projections."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .constants import FEED_SCHEMA_VERSION, MAX_EVENTS, NEWS_FRONT_PAGE_QUOTA
from .errors import ValidationError
from .topics import diversify_by_topic
from .validation import format_timestamp, parse_timestamp, validate_event, validate_feed


def event_id(
    event_type: str,
    entity_kind: str,
    entity_id: str,
    occurrence_key: str,
    source_url: str,
) -> str:
    canonical = "\n".join(
        ("feed-v1", event_type, entity_kind, entity_id, occurrence_key, source_url)
    )
    return "evt_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def event_sort_key(event: Mapping[str, Any]) -> tuple[float, float, str]:
    return (
        -parse_timestamp(event["occurredAt"]).timestamp(),
        -parse_timestamp(event["discoveredAt"]).timestamp(),
        str(event["id"]),
    )


def canonical_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    validated = [validate_event(dict(event)) for event in events]
    ordered = sorted(validated, key=event_sort_key)
    if len(ordered) > MAX_EVENTS:
        ordered = ordered[:MAX_EVENTS]
    if len({event["id"] for event in ordered}) != len(ordered):
        raise ValidationError("event IDs collide")
    return ordered


def make_feed(
    *,
    generated_at: datetime,
    window_from: datetime,
    sources: Iterable[Mapping[str, Any]],
    events: Iterable[Mapping[str, Any]],
    lead_event_id: str | None = None,
) -> dict[str, Any]:
    ordered = canonical_events(events)
    through = generated_at.astimezone(timezone.utc)
    value: dict[str, Any] = {
        "schemaVersion": FEED_SCHEMA_VERSION,
        "generatedAt": format_timestamp(through),
        "window": {
            "from": format_timestamp(window_from),
            "through": format_timestamp(through),
        },
        "sources": [dict(item) for item in sorted(sources, key=lambda item: str(item["id"]))],
        "events": ordered,
    }
    if lead_event_id:
        value["leadEventId"] = lead_event_id
    return validate_feed(value, now=through)


def project_section(
    feed: Mapping[str, Any],
    section: str,
    *,
    installed_plugin_ids: Iterable[str] = (),
    saved_ids: Iterable[str] = (),
    query: str = "",
) -> list[dict[str, Any]]:
    events = [deepcopy(event) for event in feed.get("events", [])]
    installed = set(installed_plugin_ids)
    saved = set(saved_ids)
    if section in {"core", "plugins", "youtube"}:
        events = [event for event in events if event["classification"]["section"] == section]
        if section == "youtube":
            from .sources.youtube import rank_youtube_events

            events = rank_youtube_events(events)
    elif section == "for-you":
        events = [
            event
            for event in events
            if event["entity"]["kind"] == "plugin" and event["entity"]["id"] in installed
        ]
    elif section == "saved":
        events = [event for event in events if event["id"] in saved]
    elif section == "front-page":
        events = front_page(events, installed_plugin_ids=installed)
    else:
        raise ValidationError("unknown client section")
    needle = " ".join(query.lower().split())
    if needle:
        events = [
            event
            for event in events
            if needle
            in " ".join(
                [
                    event["title"],
                    event["summary"],
                    event["entity"]["name"],
                    " ".join(event["classification"]["tags"]),
                ]
            ).lower()
        ]
    return events


def front_page(
    events: Iterable[Mapping[str, Any]], *, installed_plugin_ids: Iterable[str] = ()
) -> list[dict[str, Any]]:
    """Compose a finite deterministic edition without popularity signals."""

    # YouTube stays in its own rail (D045); it never fills Front Page in MVP.
    ordered = [
        event
        for event in canonical_events(events)
        if event["classification"]["section"] != "youtube" and event["type"] != "youtube-video"
    ]
    installed = set(installed_plugin_ids)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def add(items: Iterable[dict[str, Any]], maximum: int | None = None) -> None:
        count = 0
        for item in items:
            if item["id"] in selected_ids:
                continue
            selected.append(item)
            selected_ids.add(item["id"])
            count += 1
            if maximum is not None and count >= maximum:
                break

    add(event for event in ordered if event["classification"]["significance"] == "critical")
    add(event for event in ordered if event["classification"]["significance"] == "notable")
    add((event for event in ordered if event["type"] == "omarchy-released"), maximum=1)
    # Official news stays routine (D008/D048). Give Core announcements a small
    # Front Page quota instead of marking every RSS item notable, and spend
    # that quota on distinct topics so one same-cycle story (a Foundation
    # announcement plus its patronage follow-ups) cannot take every slot
    # (D049). Core keeps every news item; only this quota is diversified.
    add(
        diversify_by_topic(
            [
                event
                for event in ordered
                if event["type"] == "omarchy-news" and event["id"] not in selected_ids
            ],
            NEWS_FRONT_PAGE_QUOTA,
        )
    )
    add(
        (
            event
            for event in ordered
            if event["entity"]["kind"] == "plugin" and event["entity"]["id"] in installed
        ),
        maximum=3,
    )
    # The newest official release was already selected above. Do not fill the
    # front page with older core releases merely to satisfy a source quota.
    for section in ("plugins", "community"):
        add(
            (event for event in ordered if event["classification"]["section"] == section),
            maximum=3,
        )
    add(
        (
            event
            for event in ordered
            if event["type"] not in {"omarchy-released", "omarchy-news"}
        ),
        maximum=max(0, 18 - len(selected)),
    )
    return selected[:18]

def greatest_event_timestamp(events: Iterable[Mapping[str, Any]]) -> str | None:
    values = [str(event["occurredAt"]) for event in events]
    return max(values, key=lambda value: parse_timestamp(value)) if values else None


def source_health_label(sources: Iterable[Mapping[str, Any]]) -> str:
    items = list(sources)
    failed = [item for item in items if item.get("status") == "failed"]
    stale = [item for item in items if item.get("status") == "stale"]
    if failed:
        return "Partial — " + ", ".join(str(item["id"]) for item in failed)
    if stale:
        return "Stale — " + ", ".join(str(item["id"]) for item in stale)
    return "All available sources current"
