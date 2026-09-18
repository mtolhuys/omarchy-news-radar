"""Atomic per-event, section, bookmark, and reader preference actions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .client_briefing import _filtered_briefing_members
from .client_common import _parse_installed_plugin_ids, response
from .client_projection import _filtered_section_events
from .client_setup_news import load_reading_feed
from .constants import CLIENT_SECTIONS
from .errors import ValidationError
from .model import event_from_saved_record
from .sections import visible_client_sections
from .state import (StateLock, event_is_read, load_feed, load_state, save_state,
                    set_event_read, set_events_read, toggle_saved, update_preferences,
                    update_section_filter)
from .validation import EVENT_ID_RE


def _actionable_events(
    feed: Mapping[str, Any] | None,
    state: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return strict events that local reading/bookmark actions may mutate.

    Feed retention can remove a story while its bounded saved record remains.
    Saved projection already restores that story for reading; actions must use
    the same trusted local record instead of treating the visible row as stale.
    The presentation-only marker is removed before state validation.
    """

    events = {
        str(item["id"]): dict(item)
        for item in (feed or {}).get("events", [])
    }
    for event_id, record in state["saved"].items():
        if event_id in events:
            continue
        restored = event_from_saved_record(event_id, record)
        restored.pop("isArchivedSave", None)
        events[event_id] = restored
    return events


def toggle_saved_state(event_id: str, environment: Mapping[str, str] | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        feed = load_reading_feed(environment, now=now)
        live_event_ids = {item["id"] for item in (feed or {}).get("events", [])}
        event = _actionable_events(feed, state).get(event_id)
        if event is None:
            if feed is None:
                raise ValidationError("cannot save an event without a valid cached feed")
            raise ValidationError("event is not present in the validated cache or saved items")
        updated, saved = toggle_saved(state, event, now=now)
        if not saved and event_id not in live_event_ids:
            # Once an archived bookmark is removed it has no remaining reader
            # surface. Drop only its now-unreachable explicit read override.
            updated = {
                **updated,
                "readOverrides": {
                    key: value
                    for key, value in updated["readOverrides"].items()
                    if key != event_id
                },
            }
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

    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        feed = load_reading_feed(environment, now=now)
        events_by_id = _actionable_events(feed, state)
        if feed is None and event_id not in events_by_id:
            raise ValidationError("cannot change reading state without a valid cached feed")
        event = events_by_id.get(event_id)
        if event is None:
            return response(
                "stale-event",
                message="The story changed during refresh; the current edition was left unchanged.",
                state=state,
            )
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
    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        feed = load_reading_feed(environment, now=now)
        if feed is None:
            raise ValidationError("cannot change reading state without a valid cached feed")
        actionable_events = _actionable_events(feed, state)
        current_event_ids = set(actionable_events)
        section_events = _filtered_section_events(
            feed,
            state,
            section,
            installed,
            now=now,
        )
        if section == "front-page":
            # Briefings intentionally remain based on the bounded rolling feed.
            briefing_feed = load_feed(environment, now=now)
            section_events = _filtered_briefing_members(briefing_feed, state, now=now)
        unread_events = [
            actionable_events[event["id"]]
            for event in section_events
            if not event_is_read(state, event)
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
