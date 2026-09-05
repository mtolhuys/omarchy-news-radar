"""Pure local state defaults and strict migrations from historical schemas."""

from __future__ import annotations

from typing import Any, Mapping
from .constants import CLIENT_SECTIONS, STATE_SCHEMA_VERSION, V9_CLIENT_SECTIONS
from .errors import ValidationError
from .filters import default_section_filter, default_section_filters
from .relevance import default_relevance
from .sections import default_section_visibility
from .validation import (migrate_section_profile_v4, require_exact_keys, require_mapping,
                         validate_legacy_interests, validate_section_filter,
                         validate_section_profile, validate_state)


EPOCH = "1970-01-01T00:00:00Z"


LEGACY_CLIENT_SECTIONS = (
    "front-page",
    "for-you",
    "core",
    "plugins",
    "community",
    "saved",
)


LEGACY_STATE_KEYS = {"schemaVersion", "seenThrough", "saved", "preferences"}


LEGACY_PREFERENCE_KEYS = {
    2: {"barVisible", "imagesVisible", "interests"},
    3: {"barVisible", "imagesVisible", "interests", "sectionFilters"},
    4: {"barVisible", "imagesVisible", "interests", "sectionFilters", "sectionProfiles"},
    5: {"barVisible", "imagesVisible", "interests", "sectionFilters", "sectionProfiles"},
    6: {"barVisible", "imagesVisible", "interests", "sectionFilters", "sectionProfiles"},
    7: {"barVisible", "imagesVisible", "interests", "sectionFilters", "sectionProfiles"},
    8: {"barVisible", "imagesVisible", "sectionFilters", "sectionProfiles"},
}


MODERN_LEGACY_STATE_KEYS = {"schemaVersion", "readThrough", "readOverrides", "saved", "preferences"}


def default_state() -> dict[str, Any]:
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "relevance": default_relevance(),
        "readThrough": EPOCH,
        "readOverrides": {},
        "onboardingComplete": False,
        "briefing": None,
        "saved": {},
        "preferences": {
            "barVisible": True,
            "imagesVisible": True,
            "sectionFilters": default_section_filters(),
            "sectionVisibility": default_section_visibility(),
        },
    }


def _migrate_legacy_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one published legacy shape before converting it to the current schema."""

    old_version = raw.get("schemaVersion")
    if old_version not in {1, 2, 3, 4, 5, 6, 7, 8}:
        raise ValidationError("unsupported legacy state schemaVersion")
    expected_state_keys = (
        MODERN_LEGACY_STATE_KEYS
        if old_version >= 7
        else LEGACY_STATE_KEYS if old_version >= 2 else LEGACY_STATE_KEYS - {"preferences"}
    )
    require_exact_keys(raw, expected_state_keys, f"state v{old_version}")

    preferences = default_state()["preferences"]
    if old_version >= 2:
        old_preferences = require_mapping(raw.get("preferences"), f"state v{old_version} preferences")
        require_exact_keys(
            old_preferences,
            LEGACY_PREFERENCE_KEYS[old_version],
            f"state v{old_version} preferences",
        )
        if old_version <= 7:
            validate_legacy_interests(old_preferences["interests"])
        for key in ("barVisible", "imagesVisible"):
            preferences[key] = old_preferences[key]

        if old_version >= 3:
            old_filters = require_mapping(
                old_preferences.get("sectionFilters"),
                f"state v{old_version} section filters",
            )
            require_exact_keys(
                old_filters,
                V9_CLIENT_SECTIONS if old_version >= 6 else LEGACY_CLIENT_SECTIONS,
                f"state v{old_version} section filters",
            )
            preferences["sectionFilters"] = {
                section: (
                    validate_section_filter(old_filters[section])
                    if section in old_filters
                    else default_section_filter()
                )
                for section in CLIENT_SECTIONS
            }
            preferences["sectionVisibility"] = default_section_visibility()

        if old_version >= 4:
            old_profiles = require_mapping(
                old_preferences.get("sectionProfiles"),
                f"state v{old_version} section profiles",
            )
            require_exact_keys(
                old_profiles,
                V9_CLIENT_SECTIONS if old_version >= 6 else LEGACY_CLIENT_SECTIONS,
                f"state v{old_version} section profiles",
            )
            profile_validator = migrate_section_profile_v4 if old_version == 4 else validate_section_profile
            for section in old_profiles:
                profile_validator(old_profiles[section])

    return validate_state(
        {
            "schemaVersion": STATE_SCHEMA_VERSION,
            "relevance": default_relevance(),
            "onboardingComplete": True,
            "briefing": None,
            "readThrough": raw.get("readThrough") if old_version >= 7 else raw.get("seenThrough"),
            "readOverrides": raw.get("readOverrides") if old_version >= 7 else {},
            "saved": raw.get("saved"),
            "preferences": preferences,
        }
    )


def _migrate_v10_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate state v10 and add the local section-visibility profile for v11."""

    require_exact_keys(raw, MODERN_LEGACY_STATE_KEYS, "state v10")
    preferences = require_mapping(raw.get("preferences"), "state v10 preferences")
    require_exact_keys(
        preferences,
        {"barVisible", "imagesVisible", "sectionFilters"},
        "state v10 preferences",
    )
    old_filters = require_mapping(preferences.get("sectionFilters"), "state v10 section filters")
    require_exact_keys(old_filters, CLIENT_SECTIONS, "state v10 section filters")
    return validate_state(
        {
            "schemaVersion": STATE_SCHEMA_VERSION,
            "relevance": default_relevance(),
            "onboardingComplete": True,
            "briefing": None,
            "readThrough": raw.get("readThrough"),
            "readOverrides": raw.get("readOverrides"),
            "saved": raw.get("saved"),
            "preferences": {
                "barVisible": preferences["barVisible"],
                "imagesVisible": preferences["imagesVisible"],
                "sectionFilters": {
                    section: validate_section_filter(old_filters[section])
                    for section in CLIENT_SECTIONS
                },
                "sectionVisibility": default_section_visibility(),
            },
        }
    )


def _migrate_v9_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate state v9, add YouTube filters, then finish on the current schema."""

    require_exact_keys(
        raw,
        MODERN_LEGACY_STATE_KEYS,
        "state v9",
    )
    preferences = require_mapping(raw.get("preferences"), "state v9 preferences")
    require_exact_keys(
        preferences,
        {"barVisible", "imagesVisible", "sectionFilters"},
        "state v9 preferences",
    )
    old_filters = require_mapping(preferences.get("sectionFilters"), "state v9 section filters")
    require_exact_keys(old_filters, V9_CLIENT_SECTIONS, "state v9 section filters")
    section_filters = {
        section: (
            validate_section_filter(old_filters[section])
            if section in old_filters
            else default_section_filter()
        )
        for section in CLIENT_SECTIONS
    }
    return validate_state(
        {
            "schemaVersion": STATE_SCHEMA_VERSION,
            "relevance": default_relevance(),
            "onboardingComplete": True,
            "briefing": None,
            "readThrough": raw.get("readThrough"),
            "readOverrides": raw.get("readOverrides"),
            "saved": raw.get("saved"),
            "preferences": {
                "barVisible": preferences["barVisible"],
                "imagesVisible": preferences["imagesVisible"],
                "sectionFilters": section_filters,
                "sectionVisibility": default_section_visibility(),
            },
        }
    )


def _migrate_v11_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Existing readers keep every reading fact and skip the new-user choice."""

    require_exact_keys(raw, MODERN_LEGACY_STATE_KEYS, "state v11")
    return validate_state({
        **raw,
        "schemaVersion": STATE_SCHEMA_VERSION,
        "relevance": default_relevance(),
        "onboardingComplete": True,
        "briefing": None,
    })


def _migrate_v12_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    require_exact_keys(raw, MODERN_LEGACY_STATE_KEYS | {"briefing", "onboardingComplete"}, "state v12")
    result = validate_state({**raw, "schemaVersion": STATE_SCHEMA_VERSION, "relevance": default_relevance()})
    if any(group["reason"] == "followed" for group in (result["briefing"] or {}).get("groups", [])):
        raise ValidationError("state v12 cannot contain a followed briefing reason")
    return result
