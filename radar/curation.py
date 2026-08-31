"""Restricted reviewed curation overlays."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from .errors import ValidationError
from .io import read_bytes_bounded
from .validation import normalize_text, parse_timestamp, validate_event


def load_curation(directory: Path) -> dict[str, dict[str, Any]]:
    overlays: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            item = json.loads(read_bytes_bounded(path, 32 * 1024).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError(f"curation record {path.name} is invalid JSON") from exc
        if not isinstance(item, dict):
            raise ValidationError("curation record must be an object")
        allowed = {"eventId", "significance", "summary", "lead", "tags", "reviewer", "reviewedAt"}
        if set(item) - allowed:
            raise ValidationError("curation record changes unsupported fields")
        event_id = item.get("eventId")
        if not isinstance(event_id, str) or event_id in overlays:
            raise ValidationError("curation eventId is missing or duplicated")
        significance = item.get("significance", "notable")
        if significance not in {"notable", "critical"}:
            raise ValidationError("curation significance must be notable or critical")
        reviewer = normalize_text(item.get("reviewer"), 120)
        reviewed_at = item.get("reviewedAt")
        parse_timestamp(reviewed_at, "curation.reviewedAt")
        overlay: dict[str, Any] = {
            "significance": significance,
            "lead": item.get("lead") is True,
            "reviewer": reviewer,
            "reviewedAt": reviewed_at,
        }
        if "summary" in item:
            overlay["summary"] = normalize_text(item["summary"], 400)
        if "tags" in item:
            if not isinstance(item["tags"], list) or len(item["tags"]) > 12:
                raise ValidationError("curation tags are invalid")
            overlay["tags"] = sorted({normalize_text(tag, 32).lower() for tag in item["tags"]})
        overlays[event_id] = overlay
    return overlays


def apply_curation(
    events: Iterable[Mapping[str, Any]], overlays: Mapping[str, Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], str | None]:
    result: list[dict[str, Any]] = []
    found: set[str] = set()
    leads: list[str] = []
    for original in events:
        event = deepcopy(dict(original))
        overlay = overlays.get(event["id"])
        if overlay:
            event["classification"]["significance"] = overlay["significance"]
            event["classification"]["curated"] = True
            if "summary" in overlay:
                event["summary"] = overlay["summary"]
            if "tags" in overlay:
                event["classification"]["tags"] = overlay["tags"]
            if overlay.get("lead"):
                leads.append(event["id"])
            found.add(event["id"])
        result.append(validate_event(event))
    missing = set(overlays) - found
    if missing:
        raise ValidationError(f"curation references missing event: {sorted(missing)[0]}")
    if len(leads) > 1:
        raise ValidationError("curation nominates more than one lead")
    return result, leads[0] if leads else None
