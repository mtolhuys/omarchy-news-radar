"""Honest, timezone-safe timing for published and locally cached editions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .validation import format_timestamp, parse_timestamp

PUBLICATION_STALE_SECONDS = 90 * 60
PAGES_CACHE_MAX_SECONDS = 10 * 60


def age_label(seconds: int) -> str:
    """Return a compact human age without hiding the underlying UTC fields."""

    bounded = max(0, int(seconds))
    if bounded < 60:
        return "less than a minute"
    minutes = bounded // 60
    if minutes < 60:
        return f"{minutes} minute" + ("" if minutes == 1 else "s")
    hours, remaining_minutes = divmod(minutes, 60)
    label = f"{hours} hour" + ("" if hours == 1 else "s")
    if remaining_minutes:
        label += f" {remaining_minutes} minute" + ("" if remaining_minutes == 1 else "s")
    return label


def edition_timing(
    feed: Mapping[str, Any],
    *,
    now: datetime,
    cached_at: datetime | None = None,
) -> dict[str, Any]:
    """Separate source checks, collection, artifact publication, and local cache time."""

    clock = now.astimezone(timezone.utc)
    collected_at = str(feed["generatedAt"])
    published_inferred = "publishedAt" not in feed
    published_at = str(feed.get("publishedAt", collected_at))
    published = parse_timestamp(published_at, "publishedAt")
    publication_age = max(0, int((clock - published).total_seconds()))
    checked_values = {
        str(source["id"]): str(source["checkedAt"])
        for source in feed.get("sources", [])
        if isinstance(source, Mapping) and "id" in source and "checkedAt" in source
    }
    checked_times = [parse_timestamp(value, "source.checkedAt") for value in checked_values.values()]
    result: dict[str, Any] = {
        "checkedAt": format_timestamp(clock),
        "sourceCheckedAt": dict(sorted(checked_values.items())),
        "latestSourceCheckedAt": format_timestamp(max(checked_times)) if checked_times else "",
        "oldestSourceCheckedAt": format_timestamp(min(checked_times)) if checked_times else "",
        "collectedAt": collected_at,
        "publishedAt": published_at,
        "publishedAtInferred": published_inferred,
        "publicationAgeSeconds": publication_age,
        "publicationAgeLabel": age_label(publication_age),
        "publisherStale": publication_age > PUBLICATION_STALE_SECONDS,
        "staleAfterSeconds": PUBLICATION_STALE_SECONDS,
        "pagesCacheMaxSeconds": PAGES_CACHE_MAX_SECONDS,
    }
    if cached_at is not None:
        cached = cached_at.astimezone(timezone.utc)
        cache_age = max(0, int((clock - cached).total_seconds()))
        result.update(
            {
                "cachedAt": format_timestamp(cached),
                "clientCacheAgeSeconds": cache_age,
                "clientCacheAgeLabel": age_label(cache_age),
            }
        )
    return result


def update_message(
    status: str,
    *,
    timing: Mapping[str, Any] | None,
    new_stories: int = 0,
    local_edition: bool = False,
) -> str:
    """Describe what checking the published static edition actually accomplished."""

    publication_age = str((timing or {}).get("publicationAgeLabel") or "an unknown age")
    if status == "updated":
        noun = "story" if new_stories == 1 else "stories"
        return f"Adopted {new_stories} new {noun} · published {publication_age} ago."
    if status == "no-change":
        return f"No newer edition · published {publication_age} ago."
    if status == "local-current":
        return f"No newer published edition · the local live edition remains selected · public edition published {publication_age} ago."
    if status == "stale-publication":
        suffix = " The newer local live edition remains selected." if local_edition else " The last-known-good edition remains readable."
        return f"Publisher lag: the public edition was published {publication_age} ago.{suffix}"
    if status == "offline":
        if timing:
            cache_age = str(timing.get("clientCacheAgeLabel") or "an unknown age")
            return f"Update check failed · cached locally {cache_age} ago · edition published {publication_age} ago."
        return "Update check failed · no validated local cache is available."
    if status == "invalid-feed":
        if timing:
            cache_age = str(timing.get("clientCacheAgeLabel") or "an unknown age")
            return f"Invalid published edition rejected · cached locally {cache_age} ago · prior edition published {publication_age} ago."
        return "Invalid published edition rejected · no validated local cache is available."
    return "The published edition check did not return a recognized result."
