"""Bounded normalization for official anonymous marketplace aggregates."""

from __future__ import annotations

import re
from typing import Any

from ..errors import ValidationError

ENGAGEMENT_URL = "https://api.omarchyplugins.com/v1/stats"
PLUGIN_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,159})$")
MAX_PLUGINS = 5000
MAX_METRIC_VALUE = 9_007_199_254_740_991


def _count(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= MAX_METRIC_VALUE:
        raise ValidationError(f"marketplace engagement {name} is invalid")
    return value


def parse_engagement(payload: Any) -> dict[str, dict[str, int]]:
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
        raise ValidationError("marketplace engagement schemaVersion is unsupported")
    raw_plugins = payload.get("plugins")
    if not isinstance(raw_plugins, dict) or len(raw_plugins) > MAX_PLUGINS:
        raise ValidationError("marketplace engagement plugins are invalid")
    plugins: dict[str, dict[str, int]] = {}
    for plugin_id, raw in raw_plugins.items():
        if not isinstance(plugin_id, str) or not PLUGIN_ID_RE.fullmatch(plugin_id):
            raise ValidationError("marketplace engagement plugin id is invalid")
        if not isinstance(raw, dict):
            raise ValidationError("marketplace engagement record is invalid")
        plugins[plugin_id] = {
            "views": _count(raw.get("views"), "views"),
            "copies": _count(raw.get("copies"), "copies"),
            "hearts": _count(raw.get("hearts"), "hearts"),
        }
    return dict(sorted(plugins.items()))
