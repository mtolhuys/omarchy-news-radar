"""Atomic per-event, section, bookmark, and reader preference actions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .client_briefing import _filtered_briefing_members
from .client_common import _parse_installed_plugin_ids, response
from .client_projection import _filtered_section_events
from .constants import CLIENT_SECTIONS
from .errors import ValidationError
from .sections import visible_client_sections
from .state import (StateLock, event_is_read, load_feed, load_state, save_state,
                    set_event_read, set_events_read, toggle_saved, update_preferences,
                    update_section_filter)
from .validation import EVENT_ID_RE

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

    with StateLock(environment):
        state, _ = load_state(environment, serialized=False)
        feed = load_feed(environment, now=now)
        if feed is None:
            raise ValidationError("cannot change reading state without a valid cached feed")
        events_by_id = {item["id"]: item for item in feed["events"]}
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
        feed = load_feed(environment, now=now)
        if feed is None:
            raise ValidationError("cannot change reading state without a valid cached feed")
        current_event_ids = {item["id"] for item in feed["events"]}
        section_events = _filtered_section_events(
            feed,
            state,
            section,
            installed,
            now=now,
        )
        if section == "front-page":
            section_events = _filtered_briefing_members(feed, state, now=now)
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
