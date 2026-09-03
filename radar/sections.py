"""User-facing summaries for the fixed section source boundaries."""

from __future__ import annotations

from typing import Any, Mapping

from .constants import CLIENT_SECTIONS, OPTIONAL_CLIENT_SECTIONS

# Membership remains editorially fixed. These strings let Settings disclose the
# source scope behind each canonical section.
SECTION_SOURCE_SUMMARIES = {
    "front-page": "Official Omarchy releases and Omarchy News \u00b7 Omarchy Plugin Marketplace \u00b7 repository-reviewed community links",
    "for-you": "The same fixed sources, narrowed locally by exact enabled plugin IDs",
    "core": "Official Omarchy GitHub releases and Omarchy News RSS",
    "plugins": "Omarchy Plugin Marketplace and linked public repositories",
    "youtube": "Omarchy-related YouTube videos collected through the YouTube Data API",
    "saved": "Stories you saved locally from the fixed sources above",
}

# Front Page, For You and Saved always stay reachable so a local display
# choice can never hide the edition, the installed-plugin view, or a bookmark.
SECTION_VISIBILITY_LABELS = {
    "core": "Core",
    "plugins": "Plugins",
    "youtube": "YouTube",
}


def default_section_visibility() -> dict[str, bool]:
    """Every hideable rail starts visible; hiding is an explicit local choice."""

    return {section: True for section in OPTIONAL_CLIENT_SECTIONS}


def visible_client_sections(visibility: Mapping[str, Any] | None) -> tuple[str, ...]:
    """Return the canonical section order with locally hidden rails removed."""

    hidden = {
        section
        for section in OPTIONAL_CLIENT_SECTIONS
        if visibility is not None and visibility.get(section) is False
    }
    return tuple(section for section in CLIENT_SECTIONS if section not in hidden)
