"""Manual validation for every public feed and state boundary."""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from .constants import (
    CHANNELS,
    CLIENT_SECTIONS,
    COMPATIBILITY_BASIS,
    EVENT_TYPES,
    FILTER_PERIODS,
    FILTER_SIGNIFICANCE,
    FUTURE_SKEW_SECONDS,
    MARKETPLACE_TRUST,
    METRIC_IDS,
    MAX_EVENTS,
    MAX_READ_OVERRIDES,
    MAX_SAVED,
    FEED_SCHEMA_VERSION,
    MAX_LEGACY_INTERESTS,
    SECTIONS,
    SIGNIFICANCE,
    SOURCE_IDS,
    SOURCE_REASON_CODES,
    SOURCE_STATUSES,
    STATE_SCHEMA_VERSION,
)
from .errors import ValidationError
LEGACY_SECTION_ICON_IDS = frozenset(
    {"newspaper", "spark", "core", "plugins", "community", "saved"}
)
LEGACY_SECTION_TONES = frozenset({"clear", "soft", "accent", "ink"})

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
EVENT_ID_RE = re.compile(r"^evt_[0-9a-f]{24}$")
ENTITY_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._:+-]{0,159})$")
TAG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,31})$")
INTEREST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9 -]{0,30}[a-z0-9])?$")
IMAGE_PATH_RE = re.compile(r"^assets/images/[0-9a-f]{64}\.(?:jpg|png|webp)$")
IMAGE_SOURCE_PATH_RE = re.compile(r"^/assets/img/plugins/[A-Za-z0-9._-]+\.(?:webp|png|jpg|jpeg)$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be an object")
    return value


def require_exact_keys(value: Mapping[str, Any], expected: Iterable[str], name: str) -> None:
    """Reject missing and unknown object members at a schema boundary."""

    if set(value) != set(expected):
        raise ValidationError(f"{name} has an unknown or incomplete shape")


def require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{name} must be an array")
    return value


def require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be a boolean")
    return value


def require_string(value: Any, name: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string")
    if not minimum <= len(value) <= maximum:
        raise ValidationError(f"{name} must contain {minimum} to {maximum} characters")
    return value


def normalize_text(value: Any, maximum: int, *, minimum: int = 1) -> str:
    if not isinstance(value, str):
        raise ValidationError("display text must be a string")
    normalized = unicodedata.normalize("NFC", value)
    normalized = CONTROL_RE.sub(" ", normalized)
    normalized = " ".join(normalized.split())
    if not minimum <= len(normalized) <= maximum:
        raise ValidationError(f"display text must contain {minimum} to {maximum} characters")
    return normalized


def parse_timestamp(value: Any, name: str = "timestamp") -> datetime:
    require_string(value, name, 20, 20)
    if not TIMESTAMP_RE.fullmatch(value):
        raise ValidationError(f"{name} must be canonical UTC RFC 3339")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValidationError(f"{name} is not a real timestamp") from exc
    return parsed


def format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValidationError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_https_url(value: Any, name: str = "URL") -> str:
    url = require_string(value, name, 1, 2048)
    if CONTROL_RE.search(url):
        raise ValidationError(f"{name} contains control characters")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValidationError(f"{name} must be a credential-free HTTPS URL")
    if parsed.port not in (None, 443):
        raise ValidationError(f"{name} uses an unsupported port")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or "." not in hostname:
        raise ValidationError(f"{name} must use a public hostname")
    try:
        address = ipaddress.ip_address(hostname.strip("[]"))
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValidationError(f"{name} must not use a private host literal")
    return url


def validate_tags(value: Any) -> list[str]:
    tags = require_list(value, "classification.tags")
    if len(tags) > 12:
        raise ValidationError("classification.tags exceeds 12 entries")
    result: list[str] = []
    for raw in tags:
        tag = require_string(raw, "tag", 1, 32)
        if not TAG_RE.fullmatch(tag) or tag in result:
            raise ValidationError("tags must be unique normalized lowercase values")
        result.append(tag)
    return result


def validate_image(value: Any, *, public_only: bool) -> dict[str, Any]:
    _ = public_only  # public feeds now accept allowlisted sourceUrl as well as legacy path
    image = require_mapping(value, "event.image")
    locator = "path" if "path" in image else "sourceUrl"
    require_exact_keys(
        image,
        {"alt", "credit", "width", "height", locator},
        "event.image",
    )
    alt = normalize_text(image.get("alt"), 180)
    credit = normalize_text(image.get("credit"), 120)
    width = image.get("width")
    height = image.get("height")
    if not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 4096:
        raise ValidationError("event.image.width is invalid")
    if not isinstance(height, int) or isinstance(height, bool) or not 1 <= height <= 4096:
        raise ValidationError("event.image.height is invalid")
    if width * height > 12_000_000:
        raise ValidationError("event.image pixel count exceeds its bound")
    normalized = {"alt": alt, "credit": credit, "width": width, "height": height}
    if "path" in image:
        # Legacy mirrored assets (older editions / local caches). New publications use sourceUrl.
        path = require_string(image["path"], "event.image.path", 1, 128)
        if not IMAGE_PATH_RE.fullmatch(path):
            raise ValidationError("event.image.path is not a content-addressed feed asset")
        normalized["path"] = path
        return normalized
    source_url = validate_https_url(image.get("sourceUrl"), "event.image.sourceUrl")
    parsed = urlsplit(source_url)
    if (
        parsed.netloc.lower() != "plugins.omarchy.org"
        or not IMAGE_SOURCE_PATH_RE.fullmatch(parsed.path)
        or parsed.query
        or parsed.fragment
    ):
        raise ValidationError("event.image.sourceUrl is outside the marketplace image path boundary")
    normalized["sourceUrl"] = source_url
    return normalized


def validate_metrics(value: Any) -> list[dict[str, Any]]:
    metrics = require_list(value, "event.metrics")
    if len(metrics) > len(METRIC_IDS):
        raise ValidationError("event.metrics exceeds its bound")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in metrics:
        metric = require_mapping(raw, "event metric")
        require_exact_keys(
            metric,
            {"id", "value", "observedAt", "sourceUrl"},
            "event metric",
        )
        metric_id = require_string(metric.get("id"), "event metric id", 1, 48)
        count = metric.get("value")
        if metric_id not in METRIC_IDS or metric_id in seen:
            raise ValidationError("event metric id is invalid or duplicated")
        if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= 9_007_199_254_740_991:
            raise ValidationError("event metric value is invalid")
        observed_at = require_string(metric.get("observedAt"), "event metric observedAt", 20, 20)
        parse_timestamp(observed_at, "event metric observedAt")
        normalized.append(
            {
                "id": metric_id,
                "value": count,
                "observedAt": observed_at,
                "sourceUrl": validate_https_url(metric.get("sourceUrl"), "event metric sourceUrl"),
            }
        )
        seen.add(metric_id)
    if normalized != sorted(normalized, key=lambda item: item["id"]):
        raise ValidationError("event metrics are not in canonical order")
    return normalized


def validate_event(value: Any, *, public_only: bool = False) -> dict[str, Any]:
    event = require_mapping(value, "event")
    event_id = require_string(event.get("id"), "event.id", 28, 28)
    if not EVENT_ID_RE.fullmatch(event_id):
        raise ValidationError("event.id is invalid")
    event_type = require_string(event.get("type"), "event.type", 1, 64)
    if event_type not in EVENT_TYPES:
        raise ValidationError("event.type is unsupported")
    occurred_at = require_string(event.get("occurredAt"), "event.occurredAt", 20, 20)
    discovered_at = require_string(event.get("discoveredAt"), "event.discoveredAt", 20, 20)
    occurred = parse_timestamp(occurred_at, "event.occurredAt")
    discovered = parse_timestamp(discovered_at, "event.discoveredAt")
    if occurred > discovered + timedelta(seconds=FUTURE_SKEW_SECONDS):
        raise ValidationError("event occurs after discovery")

    source = require_mapping(event.get("source"), "event.source")
    require_exact_keys(source, {"label", "url"}, "event.source")
    entity = require_mapping(event.get("entity"), "event.entity")
    classification = require_mapping(event.get("classification"), "event.classification")
    trust = require_mapping(event.get("trust"), "event.trust")
    compatibility = require_mapping(event.get("compatibility"), "event.compatibility")

    entity_kind = require_string(entity.get("kind"), "entity.kind", 1, 32)
    if entity_kind not in {"omarchy", "plugin", "community"}:
        raise ValidationError("entity.kind is unsupported")
    entity_id = require_string(entity.get("id"), "entity.id", 1, 160)
    if not ENTITY_ID_RE.fullmatch(entity_id):
        raise ValidationError("entity.id is invalid")
    section = require_string(classification.get("section"), "classification.section", 1, 16)
    significance = require_string(classification.get("significance"), "classification.significance", 1, 16)
    marketplace = require_string(trust.get("marketplace"), "trust.marketplace", 1, 32)
    basis = require_string(compatibility.get("basis"), "compatibility.basis", 1, 32)
    if section not in SECTIONS or significance not in SIGNIFICANCE:
        raise ValidationError("event classification is unsupported")
    if marketplace not in MARKETPLACE_TRUST or basis not in COMPATIBILITY_BASIS:
        raise ValidationError("event trust or compatibility is unsupported")
    channels = require_list(compatibility.get("channels"), "compatibility.channels")
    if len(channels) > 8 or len(set(channels)) != len(channels) or any(channel not in CHANNELS for channel in channels):
        raise ValidationError("compatibility.channels is invalid")

    normalized: dict[str, Any] = {
        "id": event_id,
        "type": event_type,
        "occurredAt": occurred_at,
        "discoveredAt": discovered_at,
        "title": normalize_text(event.get("title"), 160),
        "summary": normalize_text(event.get("summary"), 400),
        "source": {
            "label": normalize_text(source.get("label"), 60),
            "url": validate_https_url(source.get("url"), "source.url"),
        },
        "entity": {
            "kind": entity_kind,
            "id": entity_id,
            "name": normalize_text(entity.get("name"), 120),
        },
        "classification": {
            "section": section,
            "significance": significance,
            "curated": require_bool(classification.get("curated"), "classification.curated"),
            "tags": validate_tags(classification.get("tags")),
        },
        "trust": {
            "marketplace": marketplace,
            "securityAudit": require_bool(trust.get("securityAudit"), "trust.securityAudit"),
        },
        "compatibility": {"channels": list(channels), "basis": basis},
    }
    for key in ("repository", "version"):
        if key in entity:
            normalized["entity"][key] = (
                validate_https_url(entity[key], "entity.repository")
                if key == "repository"
                else require_string(entity[key], "entity.version", 1, 80)
            )
    if normalized["trust"]["securityAudit"] and marketplace == "unverified":
        raise ValidationError("unverified marketplace data cannot assert a security audit")
    if "correctedAt" in event:
        normalized["correctedAt"] = require_string(event["correctedAt"], "event.correctedAt", 20, 20)
        parse_timestamp(normalized["correctedAt"], "event.correctedAt")
    if "image" in event:
        normalized["image"] = validate_image(event["image"], public_only=public_only)
    if "metrics" in event:
        normalized["metrics"] = validate_metrics(event["metrics"])
    return normalized


def _event_sort_key(event: Mapping[str, Any]) -> tuple[float, float, str]:
    occurred = parse_timestamp(event["occurredAt"]).timestamp()
    discovered = parse_timestamp(event["discoveredAt"]).timestamp()
    return (-occurred, -discovered, str(event["id"]))


def validate_feed(value: Any, *, now: datetime | None = None, public_only: bool = False) -> dict[str, Any]:
    feed = require_mapping(value, "feed")
    if feed.get("schemaVersion") != FEED_SCHEMA_VERSION:
        raise ValidationError("unsupported feed schemaVersion")
    generated_at = require_string(feed.get("generatedAt"), "generatedAt", 20, 20)
    generated = parse_timestamp(generated_at, "generatedAt")
    comparison = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if generated > comparison + timedelta(seconds=FUTURE_SKEW_SECONDS):
        raise ValidationError("feed generation time is materially in the future")
    published_at: str | None = None
    if "publishedAt" in feed:
        published_at = require_string(feed.get("publishedAt"), "publishedAt", 20, 20)
        published = parse_timestamp(published_at, "publishedAt")
        if published < generated:
            raise ValidationError("feed publication time predates collection")
        if published > comparison + timedelta(seconds=FUTURE_SKEW_SECONDS):
            raise ValidationError("feed publication time is materially in the future")
    window = require_mapping(feed.get("window"), "window")
    require_exact_keys(window, {"from", "through"}, "window")
    from_text = require_string(window.get("from"), "window.from", 20, 20)
    through_text = require_string(window.get("through"), "window.through", 20, 20)
    if parse_timestamp(from_text, "window.from") > parse_timestamp(through_text, "window.through"):
        raise ValidationError("feed window is inverted")

    sources_raw = require_list(feed.get("sources"), "sources")
    sources: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for raw in sources_raw:
        source = require_mapping(raw, "source health")
        source_keys = {"id", "status", "checkedAt", "sourceUrl"}
        if "reason" in source:
            source_keys.add("reason")
        require_exact_keys(source, source_keys, "source health")
        source_id = require_string(source.get("id"), "source.id", 1, 64)
        status = require_string(source.get("status"), "source.status", 1, 32)
        if source_id not in SOURCE_IDS or source_id in source_ids or status not in SOURCE_STATUSES:
            raise ValidationError("source health identity or status is invalid")
        checked_at = require_string(source.get("checkedAt"), "source.checkedAt", 20, 20)
        parse_timestamp(checked_at, "source.checkedAt")
        item = {
            "id": source_id,
            "status": status,
            "checkedAt": checked_at,
            "sourceUrl": validate_https_url(source.get("sourceUrl"), "source.sourceUrl"),
        }
        if "reason" in source:
            reason = require_string(source["reason"], "source.reason", 1, 32)
            if reason not in SOURCE_REASON_CODES or status != "failed":
                raise ValidationError("source reason is invalid")
            item["reason"] = reason
        sources.append(item)
        source_ids.add(source_id)

    events_raw = require_list(feed.get("events"), "events")
    if len(events_raw) > MAX_EVENTS:
        raise ValidationError("feed exceeds event bound")
    events = [validate_event(event, public_only=public_only) for event in events_raw]
    ids = [event["id"] for event in events]
    if len(set(ids)) != len(ids):
        raise ValidationError("feed contains duplicate event IDs")
    if events != sorted(events, key=_event_sort_key):
        raise ValidationError("feed events are not in canonical order")

    normalized = {
        "schemaVersion": FEED_SCHEMA_VERSION,
        "generatedAt": generated_at,
        "window": {"from": from_text, "through": through_text},
        "sources": sources,
        "events": events,
    }
    if published_at is not None:
        normalized["publishedAt"] = published_at
    if "leadEventId" in feed:
        lead = require_string(feed["leadEventId"], "leadEventId", 28, 28)
        if lead not in ids:
            raise ValidationError("leadEventId does not reference an event")
        normalized["leadEventId"] = lead
    return normalized


def validate_saved_record(value: Any, event_id: str) -> dict[str, Any]:
    record = require_mapping(value, "saved record")
    require_exact_keys(
        record,
        {"savedAt", "title", "sourceUrl", "occurredAt", "type"},
        "saved record",
    )
    if not EVENT_ID_RE.fullmatch(event_id):
        raise ValidationError("saved event ID is invalid")
    saved_at = require_string(record.get("savedAt"), "savedAt", 20, 20)
    occurred_at = require_string(record.get("occurredAt"), "occurredAt", 20, 20)
    parse_timestamp(saved_at, "savedAt")
    parse_timestamp(occurred_at, "occurredAt")
    event_type = require_string(record.get("type"), "type", 1, 64)
    if event_type not in EVENT_TYPES:
        raise ValidationError("saved event type is unsupported")
    return {
        "savedAt": saved_at,
        "title": normalize_text(record.get("title"), 160),
        "sourceUrl": validate_https_url(record.get("sourceUrl"), "sourceUrl"),
        "occurredAt": occurred_at,
        "type": event_type,
    }


def validate_section_filter(value: Any) -> dict[str, Any]:
    current = require_mapping(value, "section filter")
    require_exact_keys(
        current,
        {"period", "significance", "unreadOnly", "imagesOnly", "types"},
        "section filter",
    )
    period = require_string(current.get("period"), "section filter period", 1, 8)
    significance = require_string(current.get("significance"), "section filter significance", 1, 16)
    if period not in FILTER_PERIODS or significance not in FILTER_SIGNIFICANCE:
        raise ValidationError("section filter enum is unsupported")
    types_raw = require_list(current.get("types"), "section filter types")
    if len(types_raw) > len(EVENT_TYPES):
        raise ValidationError("section filter types exceed their bound")
    types: list[str] = []
    for raw in types_raw:
        event_type = require_string(raw, "section filter type", 1, 64)
        if event_type not in EVENT_TYPES or event_type in types:
            raise ValidationError("section filter types are invalid")
        types.append(event_type)
    if types != sorted(types):
        raise ValidationError("section filter types are not canonical")
    return {
        "period": period,
        "significance": significance,
        "unreadOnly": require_bool(current.get("unreadOnly"), "section filter unreadOnly"),
        "imagesOnly": require_bool(current.get("imagesOnly"), "section filter imagesOnly"),
        "types": types,
    }


def validate_section_profile(value: Any) -> dict[str, str]:
    current = require_mapping(value, "section profile")
    if set(current) != {"name"}:
        raise ValidationError("section profile must contain exactly name")
    name = normalize_text(current.get("name"), 32)
    return {"name": name}


def migrate_section_profile_v4(value: Any) -> dict[str, str]:
    """Validate a v4 profile and retain only its harmless display name."""

    current = require_mapping(value, "state v4 section profile")
    if set(current) != {"name", "icon", "tone"}:
        raise ValidationError("state v4 section profile has an unknown shape")
    name = normalize_text(current.get("name"), 32)
    icon = require_string(current.get("icon"), "section profile icon", 1, 24)
    tone = require_string(current.get("tone"), "section profile tone", 1, 16)
    if icon not in LEGACY_SECTION_ICON_IDS:
        raise ValidationError("section profile icon is unsupported")
    if tone not in LEGACY_SECTION_TONES:
        raise ValidationError("section profile tone is unsupported")
    return {"name": name}


def validate_legacy_interests(value: Any) -> list[str]:
    """Validate the removed v2-v7 interest field before discarding it."""

    interests_raw = require_list(value, "preferences.interests")
    if len(interests_raw) > MAX_LEGACY_INTERESTS:
        raise ValidationError("preferences.interests exceeds its bound")
    interests: list[str] = []
    for raw in interests_raw:
        interest = require_string(raw, "interest", 1, 32).lower()
        interest = " ".join(interest.split())
        if not INTEREST_RE.fullmatch(interest) or interest in interests:
            raise ValidationError("interests must be unique normalized words or phrases")
        interests.append(interest)
    return interests


def validate_state(value: Any) -> dict[str, Any]:
    state = require_mapping(value, "state")
    require_exact_keys(
        state,
        {"schemaVersion", "readThrough", "readOverrides", "saved", "preferences"},
        "state",
    )
    if state.get("schemaVersion") != STATE_SCHEMA_VERSION:
        raise ValidationError("unsupported state schemaVersion")
    read_through = require_string(state.get("readThrough"), "readThrough", 20, 20)
    parse_timestamp(read_through, "readThrough")
    overrides_raw = require_mapping(state.get("readOverrides"), "readOverrides")
    if len(overrides_raw) > MAX_READ_OVERRIDES:
        raise ValidationError("read overrides exceed item bound")
    read_overrides: dict[str, bool] = {}
    for event_id, raw in sorted(overrides_raw.items()):
        if not EVENT_ID_RE.fullmatch(event_id):
            raise ValidationError("read override event ID is invalid")
        read_overrides[event_id] = require_bool(raw, "read override")
    saved_raw = require_mapping(state.get("saved"), "saved")
    if len(saved_raw) > MAX_SAVED:
        raise ValidationError("saved state exceeds item bound")
    saved = {event_id: validate_saved_record(record, event_id) for event_id, record in sorted(saved_raw.items())}
    preferences = require_mapping(state.get("preferences"), "preferences")
    require_exact_keys(
        preferences,
        {"barVisible", "imagesVisible", "sectionFilters"},
        "preferences",
    )
    bar_visible = require_bool(preferences.get("barVisible"), "preferences.barVisible")
    images_visible = require_bool(preferences.get("imagesVisible"), "preferences.imagesVisible")
    filters_raw = require_mapping(preferences.get("sectionFilters"), "preferences.sectionFilters")
    if set(filters_raw) != set(CLIENT_SECTIONS):
        raise ValidationError("preferences.sectionFilters must define every section")
    section_filters = {
        section: validate_section_filter(filters_raw[section])
        for section in CLIENT_SECTIONS
    }
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "readThrough": read_through,
        "readOverrides": read_overrides,
        "saved": saved,
        "preferences": {
            "barVisible": bar_visible,
            "imagesVisible": images_visible,
            "sectionFilters": section_filters,
        },
    }


def require_unique(values: Iterable[str], name: str) -> None:
    items = list(values)
    if len(items) != len(set(items)):
        raise ValidationError(f"{name} must be unique")
