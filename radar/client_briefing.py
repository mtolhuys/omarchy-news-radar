"""Durable finite briefing selection, exact reading actions, and projection."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Mapping

from .briefing import BRIEFING_REASON_LABELS, briefing_id, briefing_members, compose_briefing, feed_membership_digest
from .client_common import _parse_installed_plugin_ids, response
from .errors import ValidationError
from .filters import apply_section_filter
from .model import event_sort_key
from .relevance import is_followed, is_muted
from .state import StateLock, event_is_read, load_feed, load_state, save_state, set_events_read
from .validation import EVENT_ID_RE

def _briefing_candidates(
    feed: Mapping[str, Any], state: Mapping[str, Any], *, now: datetime | None = None,
) -> list[dict[str, Any]]:
    ordered = sorted(feed["events"], key=event_sort_key)
    latest_release = next((event["id"] for event in ordered if event["type"] == "omarchy-released"), None)
    eligible = apply_section_filter(
        [event for event in ordered if event["classification"]["section"] != "youtube"
         and (event["type"] != "omarchy-released" or event["id"] == latest_release
              or event["classification"]["significance"] in {"notable", "critical"})],
        state["preferences"]["sectionFilters"]["front-page"],
        read_through=state["readThrough"], read_overrides=state["readOverrides"], now=now,
    )
    return [event for event in eligible if not event_is_read(state, event) and not is_muted(event, state)]


def ensure_briefing(
    installed_json: str, environment: Mapping[str, str] | None = None, *,
    now: datetime | None = None, replace: bool = False,
) -> dict[str, Any]:
    """Initialize once after local plugin discovery, or explicitly replace it."""

    installed = _parse_installed_plugin_ids(installed_json)
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        feed = load_feed(environment, now=now)
        if feed is None:
            return response("first-use", state=state)
        if state["briefing"] is None or replace:
            candidates = _briefing_candidates(feed, state, now=now)
            alternative = None
            if replace and state["briefing"] is not None:
                previous_ids = {
                    event_id for group in state["briefing"]["groups"] for event_id in group["eventIds"]
                }
                alternative = compose_briefing(
                    [event for event in candidates if event["id"] not in previous_ids],
                    generated_at=feed["generatedAt"], installed_plugin_ids=installed,
                    followed_event_ids=[event["id"] for event in candidates if is_followed(event, state)],
                )
            # An explicit next selection must make progress even when a
            # higher-priority item in the previous brief remains unread.
            # Keep only the current snapshot, not a growing exclusion history.
            state["briefing"] = alternative if alternative and alternative["groups"] else compose_briefing(
                candidates,
                generated_at=feed["generatedAt"], installed_plugin_ids=installed,
                followed_event_ids=[event["id"] for event in candidates if is_followed(event, state)],
            )
            state = save_state(state, environment)
    return response("ok", state=state, briefing=_briefing_status(feed, state, installed, now=now))


def complete_onboarding(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Keep the backlog available after the explicit browse choice."""

    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        state["onboardingComplete"] = True
        state = save_state(state, environment)
    return response("ok", state=state)


def start_from_today(
    feed_digest: str, environment: Mapping[str, str] | None = None, *, now: datetime | None = None,
) -> dict[str, Any]:
    """Read only the explicitly shown first-use backlog; never advance a clock."""

    _validate_digest(feed_digest, "feed digest")
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        if state["onboardingComplete"]:
            return response("onboarding-complete", state=state)
        feed = load_feed(environment, now=now)
        if feed is None or feed_membership_digest(feed) != feed_digest:
            return response(
                "stale-edition", state=state,
                message="New stories arrived. Review the current edition before choosing Start from today again.",
            )
        # Preserve an explicit unread override. The new-user operation changes
        # only ordinary backlog state; bookmarks and local choices stay intact.
        backlog = [event for event in feed["events"] if state["readOverrides"].get(event["id"]) is not False]
        marked = sum(not event_is_read(state, event) for event in backlog)
        state = set_events_read(state, backlog, True, current_event_ids={event["id"] for event in feed["events"]})
        state["onboardingComplete"] = True
        state["briefing"] = {"generatedAt": feed["generatedAt"], "groups": []}
        state = save_state(state, environment)
    return response("ok", state=state, markedRead=marked)


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValidationError(f"{label} is invalid")


def mark_briefing_read(
    snapshot_id: str, environment: Mapping[str, str] | None = None, *,
    group_event_id: str | None = None, now: datetime | None = None,
) -> dict[str, Any]:
    """Read only source events named by the explicitly activated snapshot."""

    _validate_digest(snapshot_id, "briefing ID")
    if group_event_id is not None and not EVENT_ID_RE.fullmatch(group_event_id):
        raise ValidationError("briefing group event ID is invalid")
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        snapshot = state["briefing"]
        if snapshot is None or briefing_id(snapshot) != snapshot_id:
            return response("stale-briefing", state=state, message="The briefing changed; review it before marking it read.")
        feed = load_feed(environment, now=now)
        if feed is None:
            raise ValidationError("cannot change reading state without a valid cached feed")
        if group_event_id is not None:
            selected = [group for group in snapshot["groups"] if group["eventIds"][0] == group_event_id]
            if not selected:
                return response("stale-briefing", state=state, message="The group is no longer in this briefing.")
            snapshot = {**snapshot, "groups": selected}
        members = briefing_members(snapshot, feed["events"])
        unread = [event for event in members if not event_is_read(state, event)]
        state = set_events_read(state, unread, True, current_event_ids={event["id"] for event in feed["events"]})
        state = save_state(state, environment)
    return response("ok", state=state, markedRead=len(unread))


def _filtered_briefing_members(
    feed: Mapping[str, Any], state: Mapping[str, Any], *, now: datetime | None = None,
) -> list[dict[str, Any]]:
    return apply_section_filter(
        briefing_members(state["briefing"], feed["events"]),
        state["preferences"]["sectionFilters"]["front-page"],
        read_through=state["readThrough"], read_overrides=state["readOverrides"], now=now,
    )


def _briefing_status(
    feed: Mapping[str, Any] | None, state: Mapping[str, Any], installed: list[str], *,
    now: datetime | None = None,
) -> dict[str, Any]:
    snapshot = state["briefing"]
    groups = snapshot["groups"] if snapshot else []
    by_id = {event["id"]: event for event in feed["events"]} if feed else {}
    snapshot_ids = {event_id for group in groups for event_id in group["eventIds"]}
    remaining = sum(
        any(event_id in by_id and not event_is_read(state, by_id[event_id]) for event_id in group["eventIds"])
        for group in groups
    )
    unread = sum(event_id in by_id and not event_is_read(state, by_id[event_id]) for event_id in snapshot_ids)
    expired = len(snapshot_ids - by_id.keys())
    other_brief = compose_briefing(
        [event for event in _briefing_candidates(feed, state, now=now) if event["id"] not in snapshot_ids],
        generated_at=feed["generatedAt"], installed_plugin_ids=installed,
        followed_event_ids=[event["id"] for event in feed["events"] if is_followed(event, state)],
    ) if feed else None
    available = sum(len(group["eventIds"]) for group in other_brief["groups"]) if other_brief else 0
    return {
        "id": briefing_id(snapshot) if snapshot else "",
        "initialized": snapshot is not None,
        "generatedAt": snapshot["generatedAt"] if snapshot else "",
        "total": len(groups), "remaining": remaining, "unreadEvents": unread,
        "complete": snapshot is not None and remaining == 0 and expired == 0,
        "expiredEvents": expired, "availableUnread": available,
        "hasNewStories": available > 0,
    }


def _briefing_rows(
    feed: Mapping[str, Any], state: Mapping[str, Any], *, query: str = "",
    retained_read_ids: list[str] | None = None, now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Project stable representatives while retaining each original source link."""

    snapshot = state["briefing"]
    if snapshot is None:
        return []
    by_id = {event["id"]: event for event in feed["events"]}
    section_filter = state["preferences"]["sectionFilters"]["front-page"]
    retained = set(retained_read_ids or ())
    completed_snapshot = bool(snapshot["groups"]) and all(
        event_id in by_id and event_is_read(state, by_id[event_id])
        for group in snapshot["groups"]
        for event_id in group["eventIds"]
    )
    needle = " ".join(query.lower().split())
    result: list[dict[str, Any]] = []
    for group in snapshot["groups"]:
        members = [by_id[event_id] for event_id in group["eventIds"] if event_id in by_id]
        matching = apply_section_filter(
            members, {**section_filter, "unreadOnly": False},
            read_through=state["readThrough"], read_overrides=state["readOverrides"], now=now,
        )
        if not matching:
            continue
        if (section_filter["unreadOnly"] and not completed_snapshot
                and all(event_is_read(state, event) for event in matching)
                and not any(event["id"] in retained for event in matching)):
            continue
        if needle and not any(
            needle in " ".join([event["title"], event["summary"], event["entity"]["name"], " ".join(event["classification"]["tags"])]).lower()
            for event in matching
        ):
            continue
        representative = dict(matching[0])
        representative.update({
            "briefingGroupId": group["eventIds"][0],
            "briefingReason": group["reason"],
            "briefingReasonLabel": BRIEFING_REASON_LABELS[group["reason"]],
            "briefingEventCount": len(members),
            "briefingUnreadCount": sum(not event_is_read(state, event) for event in members),
            "briefingEvents": [{
                "id": event["id"], "title": event["title"], "occurredAt": event["occurredAt"],
                "source": dict(event["source"]), "isUnread": not event_is_read(state, event),
            } for event in members],
        })
        result.append(representative)
    return result
