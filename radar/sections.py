"""Fixed section identities with local-only presentation defaults."""

from __future__ import annotations

from typing import Any

from .constants import CLIENT_SECTIONS

SECTION_ICON_IDS = frozenset(
    {"newspaper", "spark", "core", "plugins", "community", "saved"}
)
SECTION_TONES = frozenset({"clear", "soft", "accent", "ink"})

DEFAULT_SECTION_PROFILES: dict[str, dict[str, str]] = {
    "front-page": {"name": "Front Page", "icon": "newspaper", "tone": "clear"},
    "for-you": {"name": "For You", "icon": "spark", "tone": "clear"},
    "core": {"name": "Core", "icon": "core", "tone": "clear"},
    "plugins": {"name": "Plugins", "icon": "plugins", "tone": "clear"},
    "community": {"name": "Community", "icon": "community", "tone": "clear"},
    "saved": {"name": "Saved", "icon": "saved", "tone": "clear"},
}

# Membership remains editorially fixed. These strings are shown in the section
# settings so local appearance changes cannot be mistaken for source changes.
SECTION_SOURCE_SUMMARIES = {
    "front-page": "Official Omarchy releases · Omarchy Plugin Marketplace · repository-reviewed community links",
    "for-you": "The same fixed sources, narrowed locally by enabled plugin IDs and private interests",
    "core": "Official Omarchy GitHub releases",
    "plugins": "Omarchy Plugin Marketplace and linked public repositories",
    "community": "Repository-reviewed community links",
    "saved": "Stories you saved locally from the fixed sources above",
}


def default_section_profiles() -> dict[str, dict[str, Any]]:
    """Return independent profile objects in canonical section order."""

    return {section: dict(DEFAULT_SECTION_PROFILES[section]) for section in CLIENT_SECTIONS}
