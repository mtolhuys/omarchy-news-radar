"""Reviewed repository-owned community record adapter."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..errors import ValidationError
from ..io import read_bytes_bounded
from ..model import event_id
from ..validation import format_timestamp, normalize_text, parse_timestamp, validate_event, validate_https_url

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
TAG_RE = re.compile(r"<[^>]+>")
MARKUP_RE = re.compile(r"(?m)^\s{0,3}[#>*+-]+\s*|[`*_~]")


def reviewed_text(value: Any, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValidationError("reviewed display text must be a string")
    text = FENCE_RE.sub(" ", value)
    text = IMAGE_RE.sub(" ", text)
    text = LINK_RE.sub(r"\1", text)
    text = TAG_RE.sub(" ", text)
    text = MARKUP_RE.sub("", text)
    return normalize_text(html.unescape(text), maximum)


def community_events(directory: Path, *, discovered_at: datetime) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    record_ids: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(read_bytes_bounded(path, 64 * 1024).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError(f"community record {path.name} is invalid JSON") from exc
        if not isinstance(record, dict):
            raise ValidationError(f"community record {path.name} must be an object")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id or len(record_id) > 120 or record_id in record_ids:
            raise ValidationError("community record id is invalid or duplicated")
        published_at = record.get("publishedAt")
        published = parse_timestamp(published_at, "community.publishedAt")
        if published > discovered_at + timedelta(minutes=5):
            raise ValidationError("community record is materially in the future")
        significance = record.get("significance", "routine")
        if significance not in {"routine", "notable", "critical"}:
            raise ValidationError("community significance is unsupported")
        source_url = validate_https_url(record.get("sourceUrl"), "community.sourceUrl")
        tags_raw = record.get("tags")
        if not isinstance(tags_raw, list):
            raise ValidationError("community tags must be an array")
        if any(not isinstance(tag, str) for tag in tags_raw):
            raise ValidationError("community tags are invalid")
        tags = sorted({tag.strip().lower() for tag in tags_raw})
        if len(tags) != len(tags_raw) or len(tags) > 12 or any(not tag or len(tag) > 32 for tag in tags):
            raise ValidationError("community tags are invalid")
        event = {
            "id": event_id("community-link", "community", record_id, record_id, source_url),
            "type": "community-link",
            "occurredAt": published_at,
            "discoveredAt": format_timestamp(discovered_at),
            "title": reviewed_text(record.get("title"), 160),
            "summary": reviewed_text(record.get("summary"), 400),
            "source": {
                "label": normalize_text(record.get("sourceLabel") or record.get("author") or "Community source", 60),
                "url": source_url,
            },
            "entity": {
                "kind": "community",
                "id": record_id,
                "name": normalize_text(record.get("author") or "Omarchy community", 120),
            },
            "classification": {
                "section": "community",
                "significance": significance,
                "curated": significance != "routine",
                "tags": tags,
            },
            "trust": {"marketplace": "not-applicable", "securityAudit": False},
            "compatibility": {"channels": record.get("channels", []), "basis": "declared" if record.get("channels") else "unknown"},
        }
        events.append(validate_event(event))
        record_ids.add(record_id)
    return events
