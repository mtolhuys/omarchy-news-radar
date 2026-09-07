"""Compatibility facade for the versioned QML client API.

Feed transport, finite briefings, projections, and state actions have separate
owners below. Existing integrations can continue importing from radar.client.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Mapping

from .client_common import response, _parse_installed_plugin_ids
from .client_feed import (CLIENT_USER_AGENT, FeedFetch, read_model, refresh, refresh_if_due,
                          _fetch_feed, _fetch_feed_url, _test_feed)
from .client_briefing import (complete_onboarding, ensure_briefing, start_from_today,
                              mark_briefing_read, _briefing_candidates, _briefing_status,
                              _briefing_rows, _filtered_briefing_members)
from .client_projection import (indicator_model, projection_model, _filtered_section_events,
                                _persistent_section_events, _unread_event_ids)
from .client_reading import (toggle_saved_state, set_event_read_state, mark_section_read_state,
                             set_preferences, set_section_filter)
from .client_insights import insights_model, refresh_insights, set_relevance
from .client_setup import installed_plugins
from .client_setup_news import refresh_setup_news
from .errors import RadarError, StorageError
from .state import StateLock, purge
from .validation import validate_https_url


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
