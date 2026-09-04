"""Shared public bounds and fixed runtime identities."""

from __future__ import annotations

PLUGIN_ID = "io.github.mtolhuys.news-radar"
BUILD_ID = "news-radar-0.4.15"
FEED_SCHEMA_VERSION = 2
STATE_SCHEMA_VERSION = 11
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
# Published ledger retention: keep at most MAX_EVENTS, prefer the last
# RETENTION_DAYS, and never crowd out protected Core/YouTube types with
# marketplace verification noise (see retain_events).
RETENTION_DAYS = 30
PROTECTED_EVENT_TYPES = frozenset(
    {
        "omarchy-released",
        "omarchy-news",
        "youtube-video",
    }
)
# Higher score is dropped first when the ledger is over budget.
EVENT_TRIM_PRIORITY = {
    "plugin-verification-changed": 100,
    "plugin-retired": 80,
    "plugin-released": 60,
    "plugin-added": 40,
    "community-link": 20,
}
MAX_SAVED = 250
# Retained only to validate and safely migrate state v2-v7. Interests are not
# part of the current state or projection contract.
MAX_LEGACY_INTERESTS = 12
MAX_DIAGNOSTIC_BYTES = 64 * 1024
UPDATE_CHECK_MAX_BYTES = 1024
FEED_HTTP_MAX_BYTES = 4096
FUTURE_SKEW_SECONDS = 300
# Front Page news slots, spent on distinct topic clusters first (D049).
NEWS_FRONT_PAGE_QUOTA = 3

EVENT_TYPES = frozenset(
    {
        "omarchy-released",
        "omarchy-news",
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
    {
        "omarchy-releases",
        "omarchy-news",
        "marketplace",
        "marketplace-engagement",
        "community",
        "youtube",
    }
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
# Front Page, For You and Saved are the always-reachable projections. Only the
# fixed source rails may be hidden locally for display (D050).
OPTIONAL_CLIENT_SECTIONS = (
    "core",
    "plugins",
    "youtube",
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
