"""Finite local briefings over source facts, with stable explicit membership."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from .constants import MAX_BRIEFING_GROUPS
from .model import event_sort_key

BRIEFING_REASON_LABELS = {
    "critical": "Critical source notice",
    "notable": "Reviewed notable story",
    "core": "Official Omarchy change",
    "installed": "Matched an enabled plugin",
    "followed": "Followed on this desktop",
    "discovery": "A discovery from the current edition",
}


def feed_membership_digest(feed: Mapping[str, Any]) -> str:
    """Bind a first-use choice to exact event membership, not publisher clocks."""

    identities = sorted(event["id"] for event in feed["events"])
    return hashlib.sha256("\n".join(identities).encode("ascii")).hexdigest()


def briefing_id(briefing: Mapping[str, Any]) -> str:
    serialized = json.dumps(briefing, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compose_briefing(
    events: Iterable[Mapping[str, Any]],
    *,
    generated_at: str,
    installed_plugin_ids: Iterable[str] = (),
    followed_event_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Choose at most five unread groups without generating an impact claim.

    Callers supply unread events surviving the persistent Front Page filters.
    A selected plugin retains every eligible occurrence from this snapshot;
    only the representative is read through ordinary selection. Verification
    changes alone never consume a routine briefing slot.
    """

    ordered = sorted(
        (
            deepcopy(dict(event))
            for event in events
            if event["classification"]["section"] != "youtube"
        ),
        key=event_sort_key,
    )
    installed = set(installed_plugin_ids)
    followed = set(followed_event_ids)
    groups: list[dict[str, Any]] = []
    chosen: set[str] = set()
    chosen_plugins: set[str] = set()

    def add(candidates: Iterable[Mapping[str, Any]], reason: str, *, slots: int, cap: int) -> None:
        added = 0
        for event in candidates:
            if len(groups) >= cap or added >= slots:
                break
            entity = event["entity"]
            plugin_id = entity["id"] if entity["kind"] == "plugin" else None
            if event["id"] in chosen or plugin_id in chosen_plugins:
                continue
            members = [event["id"]]
            if plugin_id is not None:
                members.extend(
                    item["id"] for item in ordered
                    if item["entity"]["kind"] == "plugin"
                    and item["entity"]["id"] == plugin_id
                    and item["id"] != event["id"]
                )
                chosen_plugins.add(plugin_id)
            groups.append({"eventIds": members, "reason": reason})
            chosen.update(members)
            added += 1

    discoveries = [
        event for event in ordered
        if event["type"] in {"plugin-added", "community-link"}
        and not (event["entity"]["kind"] == "plugin" and event["entity"]["id"] in installed)
    ]
    # Authoritative critical notices may use the whole finite brief. Otherwise
    # leave one place for a new listing or reviewed community link when present.
    add((event for event in ordered if event["classification"]["significance"] == "critical"),
        "critical", slots=MAX_BRIEFING_GROUPS, cap=MAX_BRIEFING_GROUPS)
    main_cap = MAX_BRIEFING_GROUPS - bool(discoveries)
    add((event for event in ordered if event["classification"]["significance"] == "notable"),
        "notable", slots=MAX_BRIEFING_GROUPS, cap=main_cap)
    add((event for event in ordered if event["type"] == "omarchy-released"),
        "core", slots=1, cap=main_cap)
    add((event for event in ordered if event["type"] == "omarchy-news"),
        "core", slots=1, cap=main_cap)
    add((event for event in ordered if event["entity"]["kind"] == "plugin"
         and event["entity"]["id"] in installed and event["type"] != "plugin-verification-changed"),
        "installed", slots=2, cap=main_cap)
    add((event for event in ordered if event["id"] in followed and event["type"] != "plugin-verification-changed"),
        "followed", slots=2, cap=main_cap)
    add(discoveries, "discovery", slots=1, cap=MAX_BRIEFING_GROUPS)
    return {"generatedAt": generated_at, "groups": groups}


def briefing_members(
    briefing: Mapping[str, Any] | None,
    events: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve only the snapshot's exact IDs, never substitute a newer story."""

    by_id = {event["id"]: event for event in events}
    return [
        deepcopy(dict(by_id[event_id]))
        for group in (briefing or {}).get("groups", [])
        for event_id in group["eventIds"]
        if event_id in by_id
    ]
