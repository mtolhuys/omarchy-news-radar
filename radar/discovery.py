"""Automatic, dated discovery cards from validated news, never authored articles."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .constants import FEED_MAX_BYTES, FEED_URL
from .errors import StorageError, ValidationError
from .io import atomic_write_json, read_json_bounded, refuse_symlink
from .insights import matching_release
from .model import event_sort_key
from .provenance import project_matches_event_source, release_matches_event_source
from .relevance import event_relevance, is_muted
from .state import cache_root
from .validation import validate_feed

DISCOVERY_TYPES = frozenset({"plugin-added", "plugin-released", "omarchy-released"})
CACHE_NAME = "discovery-edition.json"
CARD_LIMIT = 6


def discovery_edition(feed: Mapping[str, Any] | None, environment: Mapping[str, str] | None, *, now: datetime | None = None) -> tuple[Mapping[str, Any] | None, bool, str]:
    """Called under StateLock; retain public facts, without private selection state.

    Quiet editions keep the last usable facts. Cache failures never hide a valid
    current edition, and invalid/symlinked snapshots never become display input.
    """
    path = cache_root(environment) / CACHE_NAME
    previous = None
    warning = ""
    try:
        refuse_symlink(cache_root(environment))
        previous = validate_feed(read_json_bounded(path, FEED_MAX_BYTES), now=now, public_only=True)
    except FileNotFoundError:
        pass
    except (OSError, StorageError, ValidationError):
        warning = "The previous discovery edition could not be loaded."
    current = [event for event in (feed or {}).get("events", []) if event["type"] in DISCOVERY_TYPES]
    if current:
        edition = {**feed, "events": current}
        # Polling and metrics do not invent new stories or a new activity date.
        if previous != edition:
            try:
                atomic_write_json(path, edition)
            except (OSError, StorageError):
                warning = "Discoveries are available, but could not be retained for offline reading."
        return edition, False, warning
    return previous, previous is not None, warning


def automatic_discoveries(edition: Mapping[str, Any] | None, current_feed: Mapping[str, Any] | None,
                          state: Mapping[str, Any], projects: list[dict[str, Any]], *, query: str = "",
                          retained: bool = False, warning: str = "") -> dict[str, Any]:
    """Newest distinct projects per lane; read state and engagement never rank them."""
    by_id = {project["id"]: project for project in projects}
    retired = {event["entity"]["id"] for event in (current_feed or {}).get("events", []) if event["type"] == "plugin-retired"}
    needle = " ".join(query.casefold().split())
    additions: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for event in sorted((edition or {}).get("events", []), key=event_sort_key):
        if event["type"] not in DISCOVERY_TYPES or event["entity"]["id"] in retired or is_muted(event, state):
            continue
        rail = "plugins" if event["entity"]["kind"] == "plugin" else "core"
        if not state["preferences"]["sectionVisibility"][rail]:
            continue
        if needle and needle not in " ".join([event["title"], event["summary"], event["entity"]["name"]]).casefold():
            continue
        lane = additions if event["type"] == "plugin-added" else changes
        key = ("added" if lane is additions else "changed", event["entity"]["id"])
        if len(lane) >= CARD_LIMIT or key in seen:
            continue
        seen.add(key)
        reason = "Added to the marketplace" if lane is additions else "Version update" if rail == "plugins" else "Omarchy release"
        project = by_id.get(event["entity"]["id"])
        if project and not project_matches_event_source(event, project):
            project = None
        release = matching_release((project or {}).get("releases", []), event["entity"].get("version"))
        releases = [release] if release and release_matches_event_source(event, project, release) else []
        image = event.get("image", {})
        lane.append({
            "id": "activity:" + event["id"], "eventId": event["id"], "kind": "activity",
            "title": event["title"], "summary": event["summary"], "body": event["summary"],
            "occurredAt": event["occurredAt"], "discoveredAt": event["discoveredAt"],
            "comparisonLabel": reason + " · " + event["occurredAt"][:10],
            "selectionReason": reason + ". Selected automatically by event date; one entry per project in this section.",
            "source": event["source"], "sourceLinks": [],
            "shareUrl": FEED_URL.rsplit("/", 1)[0] + "/stories/" + event["id"] + "/",
            "imageUrl": image.get("sourceUrl", "") if state["preferences"]["imagesVisible"] else "",
            "projects": [{key: value for key, value in project.items() if key not in {"releases", "newerReleases", "image"}}] if project else [],
            "releases": releases, "relevanceTargets": event_relevance(event, state),
        })
    dates = [item["occurredAt"] for item in additions + changes]
    latest = max(dates) if dates else ""
    status = ("Showing the last available discovery edition. " if retained else "")
    status += "Latest source activity: " + latest[:10] + ". Updates automatically; reading does not remove these stories." if latest else "No matching discovery activity is available yet."
    if warning:
        status += " " + warning
    return {"recentAdditions": additions, "recentChanges": changes, "activityDate": latest,
            "discoveryStatus": status, "retainedDiscoveries": retained,
            # Old consumer fields are empty; authored collections are never surfaced.
            "featuredCollections": [], "discoveries": [], "featuredCollectionCount": 0, "discoveryCount": len(additions)}
