"""Shared public bounds and fixed runtime identities."""

from __future__ import annotations

PLUGIN_ID = "io.github.mtolhuys.news-radar"
BUILD_ID = "news-radar-0.1.0"
SCHEMA_VERSION = 1
HELPER_PROTOCOL_VERSION = 1

FEED_URL = "https://mtolhuys.github.io/omarchy-news-radar/events.json"
FEED_ORIGIN = "https://mtolhuys.github.io"
FEED_MAX_BYTES = 2 * 1024 * 1024
CATALOG_MAX_BYTES = 8 * 1024 * 1024
GITHUB_MAX_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 500
MAX_SAVED = 250
MAX_DIAGNOSTIC_BYTES = 64 * 1024
FUTURE_SKEW_SECONDS = 300

EVENT_TYPES = frozenset(
    {
        "omarchy-released",
        "plugin-added",
        "plugin-released",
        "plugin-retired",
        "plugin-verification-changed",
        "community-link",
    }
)
SECTIONS = frozenset({"core", "plugins", "community"})
SIGNIFICANCE = frozenset({"routine", "notable", "critical"})
MARKETPLACE_TRUST = frozenset(
    {"verified", "reviewed", "unverified", "unknown", "not-applicable"}
)
COMPATIBILITY_BASIS = frozenset({"declared", "inferred-from-source", "unknown"})
CHANNELS = frozenset({"quattro", "stable", "development"})
SOURCE_IDS = frozenset({"omarchy-releases", "marketplace", "community"})
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
