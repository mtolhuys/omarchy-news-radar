"""Pure local section-filter rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from .constants import CLIENT_SECTIONS
from .validation import parse_timestamp, validate_section_filter

SECTION_EVENT_TYPES = {
    "front-page": (
        "omarchy-released",
        "omarchy-news",
        "plugin-added",
        "plugin-released",
        "plugin-retired",
        "plugin-verification-changed",
        "community-link",
    ),
    "for-you": (
        "omarchy-released",
        "omarchy-news",
        "plugin-added",
        "plugin-released",
        "plugin-retired",
        "plugin-verification-changed",
        "community-link",
    ),
    "core": ("omarchy-released", "omarchy-news"),
    "plugins": (
        "plugin-added",
        "plugin-released",
        "plugin-retired",
        "plugin-verification-changed",
    ),
    "youtube": ("youtube-video",),
    "saved": (
        "omarchy-released",
        "omarchy-news",
        "plugin-added",
        "plugin-released",
        "plugin-retired",
        "plugin-verification-changed",
        "community-link",
        "youtube-video",
    ),
}

TYPE_LABELS = {
    "omarchy-released": "Omarchy releases",
    "omarchy-news": "Omarchy News",
    "plugin-added": "New plugins",
    "plugin-released": "Plugin releases",
    "plugin-retired": "Retirements",
    "plugin-verification-changed": "Verification changes",
    "community-link": "Community links",
    "youtube-video": "YouTube videos",
}


def default_section_filter() -> dict[str, Any]:
    return {
        "period": "all",
        "significance": "all",
        "unreadOnly": False,
        "imagesOnly": False,
        "types": [],
    }


def default_section_filters() -> dict[str, dict[str, Any]]:
    return {section: default_section_filter() for section in CLIENT_SECTIONS}


def filter_options(section: str) -> list[dict[str, str]]:
    return [
        {"id": event_type, "label": TYPE_LABELS[event_type]}
        for event_type in SECTION_EVENT_TYPES[section]
    ]


def filter_summary(value: Mapping[str, Any]) -> str:
    current = validate_section_filter(value)
    parts: list[str] = []
    period = current["period"]
    if period != "all":
        parts.append({"24h": "Last 24 hours", "7d": "Last 7 days", "30d": "Last 30 days"}[period])
    if current["significance"] == "notable":
        parts.append("Notable + critical")
    elif current["significance"] == "critical":
        parts.append("Critical only")
    if current["unreadOnly"]:
        parts.append("Unread only")
    if current["imagesOnly"]:
        parts.append("With images")
    if current["types"]:
        parts.append(f"{len(current['types'])} story type{'s' if len(current['types']) != 1 else ''}")
    return " · ".join(parts) if parts else "No extra filters"


def apply_section_filter(
    events: Iterable[Mapping[str, Any]],
    value: Mapping[str, Any],
    *,
    read_through: str,
    read_overrides: Mapping[str, bool],
    retained_read_ids: Iterable[str] = (),
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    current = validate_section_filter(value)
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    period_delta = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }.get(current["period"])
    allowed_types = set(current["types"])
    retained = set(retained_read_ids)
    result: list[dict[str, Any]] = []
    for raw in events:
        event = dict(raw)
        if period_delta is not None and parse_timestamp(event["occurredAt"]) < clock - period_delta:
            continue
        significance = event["classification"]["significance"]
        if current["significance"] == "notable" and significance not in {"notable", "critical"}:
            continue
        if current["significance"] == "critical" and significance != "critical":
            continue
        is_read = read_overrides.get(event["id"], event["occurredAt"] <= read_through)
        if current["unreadOnly"] and is_read and event["id"] not in retained:
            continue
        if current["imagesOnly"] and not isinstance(event.get("image"), dict):
            continue
        if allowed_types and event["type"] not in allowed_types:
            continue
        result.append(event)
    return result
