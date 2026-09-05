"""Shared client protocol envelope and bounded local input parsing."""

from __future__ import annotations

import json
from typing import Any
from .constants import HELPER_PROTOCOL_VERSION
from .errors import ValidationError

def response(status: str, **values: Any) -> dict[str, Any]:
    return {"protocolVersion": HELPER_PROTOCOL_VERSION, "status": status, **values}


def _parse_installed_plugin_ids(installed_json: str) -> list[str]:
    if len(installed_json) > 256 * 1024:
        raise ValidationError("installed plugin IDs exceed their bound")
    try:
        installed_raw = json.loads(installed_json)
    except json.JSONDecodeError as exc:
        raise ValidationError("installed plugin IDs are invalid JSON") from exc
    if not isinstance(installed_raw, list) or len(installed_raw) > 5000:
        raise ValidationError("installed plugin IDs are invalid")
    installed: list[str] = []
    for item in installed_raw:
        if not isinstance(item, str) or not 1 <= len(item) <= 160:
            raise ValidationError("installed plugin ID is invalid")
        installed.append(item)
    return installed
