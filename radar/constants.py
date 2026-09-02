"""Shared public bounds and fixed runtime identities."""

from __future__ import annotations

PLUGIN_ID = "io.github.mtolhuys.news-radar"
BUILD_ID = "news-radar-0.4.2"
FEED_SCHEMA_VERSION = 2
STATE_SCHEMA_VERSION = 10
HELPER_PROTOCOL_VERSION = 1

FEED_URL = "https://mtolhuijs.nl/news-radar/events.json"
FEED_ORIGIN = "https://mtolhuijs.nl"
MARKETPLACE_IMAGE_ORIGIN = "https://plugins.omarchy.org"
YOUTUBE_IMAGE_ORIGIN = "https://i.ytimg.com"
FEED_MAX_BYTES = 2 * 1024 * 1024
CATALOG_MAX_BYTES = 8 * 1024 * 1024
GITHUB_MAX_BYTES = 4 * 1024 * 1024
ENGAGEMENT_MAX_BYTES = 2 * 1024 * 1024
MAX_EVENTS = 500
MAX_READ_OVERRIDES = MAX_EVENTS
MAX_SAVED = 250
# Retained only to validate and safely migrate state v2-v7. Interests are not
# part of the current state or projection contract.
MAX_LEGACY_INTERESTS = 12
MAX_DIAGNOSTIC_BYTES = 64 * 1024
UPDATE_CHECK_MAX_BYTES = 1024
FUTURE_SKEW_SECONDS = 300

EVENT_TYPES = frozenset(
    {
        "omarchy-released",
        "plugin-added",
        "plugin-released",
        "plugin-retired",
        "plugin-verification-changed",
        "community-link",
        "youtube-video",
    }
)
SECTIONS = frozenset({"core", "plugins", "community", "youtube"})
SIGNIFICANCE = frozenset({"routine", "notable", "critical"})
MARKETPLACE_TRUST = frozenset(
    {"verified", "reviewed", "unverified", "unknown", "not-applicable"}
)
COMPATIBILITY_BASIS = frozenset({"declared", "inferred-from-source", "unknown"})
CHANNELS = frozenset({"quattro", "stable", "development"})
SOURCE_IDS = frozenset(
    {"omarchy-releases", "marketplace", "marketplace-engagement", "community", "youtube"}
)
SOURCE_STATUSES = frozenset({"current", "not-modified", "stale", "failed"})
SOURCE_REASON_CODES = frozenset(
    {
        "timeout",
        "rate-limited",
        "http-error",
        "too-large",
        "invalid-json",
        "schema-mismatch",
        "validation-failed",
        "network-error",
    }
)

CLIENT_SECTIONS = (
    "front-page",
    "for-you",
    "core",
    "plugins",
    "youtube",
    "saved",
)
V9_CLIENT_SECTIONS = (
    "front-page",
    "for-you",
    "core",
    "plugins",
    "saved",
)
FILTER_PERIODS = frozenset({"all", "24h", "7d", "30d"})
FILTER_SIGNIFICANCE = frozenset({"all", "notable", "critical"})
METRIC_IDS = frozenset(
    {
        "marketplace-views",
        "marketplace-hearts",
        "marketplace-copies",
        "repository-stars",
        "release-asset-downloads",
        "youtube-views",
        "youtube-likes",
    }
)
