"""Generic marketplace activity companion for private setup projections."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .constants import RETENTION_DAYS
from .errors import ValidationError
from .io import canonical_json_bytes
from .model import event_sort_key
from .sources.marketplace import listing_event
from .validation import (
    ENTITY_ID_RE,
    format_timestamp,
    normalize_article_summary,
    normalize_text,
    parse_timestamp,
    require_bool,
    require_exact_keys,
    require_list,
    require_mapping,
    require_string,
    validate_event,
    validate_https_url,
    validate_image,
    validate_tags,
)

SETUP_NEWS_SCHEMA_VERSION = 1
# The validated marketplace snapshot already permits 5,000 records. Keep the
# companion bounded while leaving enough room for every public field and image
# reference at that documented maximum; publication must never truncate exact
# setup matches merely to satisfy a smaller transport bound.
SETUP_NEWS_MAX_BYTES = 8 * 1024 * 1024
MAX_SETUP_NEWS_PLUGINS = 5_000
MAX_SETUP_NEWS_EVENTS = 500
SETUP_EVENT_TYPES = frozenset({"plugin-released", "plugin-retired"})


def _plugin(value: Any) -> dict[str, Any]:
    item = require_mapping(value, "setup news plugin")
    required = {
        "id", "name", "description", "repository", "sourceUrl", "addedAt",
        "listingDated", "verification", "retired", "tags",
    }
    optional = {"version", "image"}
    if not required <= set(item) or set(item) - required - optional:
        raise ValidationError("setup news plugin has an unknown or incomplete shape")
    identity = require_string(item["id"], "setup news plugin ID", 1, 160)
    if not ENTITY_ID_RE.fullmatch(identity):
        raise ValidationError("setup news plugin ID is invalid")
    added_at = require_string(item["addedAt"], "setup news addedAt", 20, 20)
    parse_timestamp(added_at, "setup news addedAt")
    verification = require_string(item["verification"], "setup news verification", 1, 32)
    if verification not in {"verified", "reviewed", "unverified", "unknown"}:
        raise ValidationError("setup news verification is invalid")
    result: dict[str, Any] = {
        "id": identity,
        "name": normalize_text(item["name"], 120),
        "description": normalize_article_summary(item["description"], 400),
        "repository": validate_https_url(item["repository"], "setup news repository"),
        "sourceUrl": validate_https_url(item["sourceUrl"], "setup news source URL"),
        "addedAt": added_at,
        "listingDated": require_bool(item["listingDated"], "setup news listingDated"),
        "verification": verification,
        "retired": require_bool(item["retired"], "setup news retired"),
        "tags": validate_tags(item["tags"]),
    }
    if "version" in item:
        result["version"] = require_string(item["version"], "setup news version", 1, 80)
    if "image" in item:
        result["image"] = validate_image(item["image"], public_only=True)
        if "sourceUrl" not in result["image"]:
            raise ValidationError("setup news image requires an allowlisted source URL")
    return result


def validate_setup_news(
    value: Any, *, now: datetime | None = None
) -> dict[str, Any]:
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    envelope = require_mapping(value, "setup news")
    require_exact_keys(
        envelope,
        {"schemaVersion", "publishedAt", "plugins", "events"},
        "setup news",
    )
    if envelope["schemaVersion"] != SETUP_NEWS_SCHEMA_VERSION:
        raise ValidationError("unsupported setup news schemaVersion")
    published_at = require_string(envelope["publishedAt"], "setup news publishedAt", 20, 20)
    if parse_timestamp(published_at, "setup news publishedAt") > clock + timedelta(minutes=5):
        raise ValidationError("setup news publication time is materially in the future")
    raw_plugins = require_list(envelope["plugins"], "setup news plugins")
    if len(raw_plugins) > MAX_SETUP_NEWS_PLUGINS:
        raise ValidationError("setup news plugins exceed their bound")
    plugins = [_plugin(item) for item in raw_plugins]
    plugin_ids = [item["id"] for item in plugins]
    if len(set(plugin_ids)) != len(plugin_ids) or plugin_ids != sorted(plugin_ids):
        raise ValidationError("setup news plugin IDs must be unique and canonical")
    raw_events = require_list(envelope["events"], "setup news events")
    if len(raw_events) > MAX_SETUP_NEWS_EVENTS:
        raise ValidationError("setup news events exceed their bound")
    events = [validate_event(item, public_only=True) for item in raw_events]
    if any(
        item["type"] not in SETUP_EVENT_TYPES or item["entity"]["kind"] != "plugin"
        for item in events
    ):
        raise ValidationError("setup news contains an unsupported event")
    event_ids = [item["id"] for item in events]
    if len(set(event_ids)) != len(event_ids) or events != sorted(events, key=event_sort_key):
        raise ValidationError("setup news events are duplicated or not canonical")
    result = {
        "schemaVersion": SETUP_NEWS_SCHEMA_VERSION,
        "publishedAt": published_at,
        "plugins": plugins,
        "events": events,
    }
    if len(canonical_json_bytes(result)) > SETUP_NEWS_MAX_BYTES:
        raise ValidationError("setup news exceeds its byte bound")
    return result


def build_setup_news(
    snapshot: Mapping[str, Any], *, published_at: datetime
) -> dict[str, Any]:
    """Rebuild recent listings from the full catalog, outside feed capacity."""

    clock = published_at.astimezone(timezone.utc).replace(microsecond=0)
    cutoff = clock - timedelta(days=RETENTION_DAYS)
    catalog = snapshot.get("sources", {}).get("marketplace", {}).get("plugins", {})
    plugins: list[dict[str, Any]] = []
    if isinstance(catalog, Mapping):
        for identity, raw in sorted(catalog.items()):
            if (
                not isinstance(identity, str)
                or not isinstance(raw, Mapping)
                or not raw.get("listingDated")
                or raw.get("retired")
                or parse_timestamp(raw.get("addedAt"), "marketplace addedAt") < cutoff
            ):
                continue
            item: dict[str, Any] = {
                "id": identity,
                "name": raw["name"],
                "description": raw["description"],
                "repository": raw["repository"],
                "sourceUrl": raw["sourceUrl"],
                "addedAt": raw["addedAt"],
                "listingDated": True,
                "verification": raw["verification"],
                "retired": False,
                "tags": raw["tags"],
            }
            if raw.get("version"):
                item["version"] = raw["version"]
            if raw.get("preview"):
                item["image"] = {
                    **raw["preview"],
                    "alt": f"{raw['name']} plugin preview",
                    "credit": "Omarchy Plugin Marketplace",
                }
            plugins.append(item)
    events = [
        dict(item)
        for item in snapshot.get("events", [])
        if item.get("type") in SETUP_EVENT_TYPES
        and item.get("entity", {}).get("kind") == "plugin"
        and parse_timestamp(item["occurredAt"]) >= cutoff
    ]
    return validate_setup_news(
        {
            "schemaVersion": SETUP_NEWS_SCHEMA_VERSION,
            "publishedAt": format_timestamp(clock),
            "plugins": plugins,
            "events": sorted(events, key=event_sort_key),
        },
        now=clock,
    )


def setup_news_events(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    published = parse_timestamp(value["publishedAt"], "setup news publishedAt")
    additions = [
        listing_event(
            item["id"],
            {
                "name": item["name"],
                "description": item["description"],
                "version": item.get("version", ""),
                "repository": item["repository"],
                "sourceUrl": item["sourceUrl"],
                "tags": item["tags"],
                "verification": item["verification"],
                "preview": item.get("image"),
            },
            discovered_at=published,
            occurred_at=item["addedAt"],
            validated_input=True,
        )
        for item in value["plugins"]
    ]
    merged = {item["id"]: item for item in additions}
    merged.update({item["id"]: dict(item) for item in value["events"]})
    return sorted(merged.values(), key=event_sort_key)
