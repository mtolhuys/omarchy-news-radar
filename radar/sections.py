"""Fixed section identities with local-only display names."""

from __future__ import annotations

from typing import Any

from .constants import CLIENT_SECTIONS

DEFAULT_SECTION_PROFILES: dict[str, dict[str, str]] = {
    "front-page": {"name": "Front Page"},
    "for-you": {"name": "For You"},
    "core": {"name": "Core"},
    "plugins": {"name": "Plugins"},
    "saved": {"name": "Saved"},
}

# Membership remains editorially fixed. These strings are shown in the section
# settings so a local display-name change cannot be mistaken for source changes.
SECTION_SOURCE_SUMMARIES = {
    "front-page": "Official Omarchy releases · Omarchy Plugin Marketplace · repository-reviewed community links",
    "for-you": "The same fixed sources, narrowed locally by exact enabled plugin IDs",
    "core": "Official Omarchy GitHub releases",
    "plugins": "Omarchy Plugin Marketplace and linked public repositories",
    "saved": "Stories you saved locally from the fixed sources above",
}


def default_section_profiles() -> dict[str, dict[str, Any]]:
    """Return independent profile objects in canonical section order."""

    return {section: dict(DEFAULT_SECTION_PROFILES[section]) for section in CLIENT_SECTIONS}
