"""Pure monitor and saved-window geometry validation for Radar's opening path."""

from __future__ import annotations

import math
import re
from typing import Any

from .errors import RadarError

MONITOR_NAME = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
COORDINATE_LIMIT = 131072


def integer(value: Any, field: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise RadarError(f"invalid window {field}")
    return value


def monitor_workareas(records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list) or not 1 <= len(records) <= 32:
        raise RadarError("invalid Hyprland monitor list")
    monitors = []
    for record in records:
        if not isinstance(record, dict):
            raise RadarError("invalid Hyprland monitor")
        if record.get("disabled") is True:
            continue
        name = record.get("name")
        if not isinstance(name, str) or not MONITOR_NAME.fullmatch(name):
            raise RadarError("invalid Hyprland monitor name")
        scale = record.get("scale")
        if type(scale) not in (float, int) or not math.isfinite(scale) or not 0.25 <= scale <= 8:
            raise RadarError("invalid Hyprland monitor scale")
        width = integer(record.get("width"), "monitor width", 32, 65536)
        height = integer(record.get("height"), "monitor height", 32, 65536)
        transform = integer(record.get("transform", 0), "monitor transform", 0, 7)
        if transform % 2:
            width, height = height, width
        width, height = math.floor(width / scale), math.floor(height / scale)
        x = integer(record.get("x"), "monitor x", -COORDINATE_LIMIT, COORDINATE_LIMIT)
        y = integer(record.get("y"), "monitor y", -COORDINATE_LIMIT, COORDINATE_LIMIT)
        reserved = record.get("reserved", [0, 0, 0, 0])
        if not isinstance(reserved, list) or len(reserved) != 4:
            raise RadarError("invalid Hyprland monitor reserved area")
        left, top, right, bottom = [integer(v, "reserved area", 0, 65536) for v in reserved]
        usable_width, usable_height = width - left - right, height - top - bottom
        if usable_width < 64 or usable_height < 64:
            raise RadarError("Hyprland monitor has no usable window area")
        monitors.append({
            "name": name, "id": integer(record.get("id"), "monitor id", 0, 65536),
            "x": x, "y": y, "left": x + left, "top": y + top,
            "width": usable_width, "height": usable_height,
            "focused": record.get("focused") is True,
        })
    if not monitors or len({m["name"] for m in monitors}) != len(monitors):
        raise RadarError("Hyprland monitor identity is missing or ambiguous")
    return monitors


def validate_placement(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise RadarError("invalid saved window schema")
    name = value.get("monitor")
    if not isinstance(name, str) or not MONITOR_NAME.fullmatch(name):
        raise RadarError("invalid saved window monitor")
    if type(value.get("maximized")) is not bool:
        raise RadarError("invalid saved window maximized state")
    return {
        "schemaVersion": 1, "monitor": name,
        "x": integer(value.get("x"), "x", -COORDINATE_LIMIT, COORDINATE_LIMIT),
        "y": integer(value.get("y"), "y", -COORDINATE_LIMIT, COORDINATE_LIMIT),
        "width": integer(value.get("width"), "width", 64, 65536),
        "height": integer(value.get("height"), "height", 64, 65536),
        "maximized": value["maximized"],
    }


def opening_geometry(
    monitors: list[dict[str, Any]], saved: dict[str, Any] | None, *,
    width: int, height: int, minimum_width: int, minimum_height: int,
) -> dict[str, Any]:
    for name, value in (("width", width), ("height", height), ("minimum width", minimum_width), ("minimum height", minimum_height)):
        integer(value, name, 64, 65536)
    existing = next((m for m in monitors if saved and m["name"] == saved["monitor"]), None)
    monitor = existing or next((m for m in monitors if m["focused"]), monitors[0])
    # Keep a small logical-pixel border clear even with very large type. Saved
    # positions are global coordinates; window-rule moves are monitor-local.
    margin = min(16, monitor["width"] // 16, monitor["height"] // 16,
                 (monitor["width"] - 64) // 2, (monitor["height"] - 64) // 2)
    available_width, available_height = monitor["width"] - margin * 2, monitor["height"] - margin * 2
    target_width = min(available_width, max(minimum_width, saved["width"] if existing else width))
    target_height = min(available_height, max(minimum_height, saved["height"] if existing else height))
    left, top = monitor["left"] + margin, monitor["top"] + margin
    x = saved["x"] if existing else left + (available_width - target_width) // 2
    y = saved["y"] if existing else top + (available_height - target_height) // 2
    x = max(left, min(x, left + available_width - target_width))
    y = max(top, min(y, top + available_height - target_height))
    return {
        "monitor": monitor["name"], "x": x, "y": y,
        "localX": x - monitor["x"], "localY": y - monitor["y"],
        "width": target_width, "height": target_height,
        "minimumWidth": min(minimum_width, available_width),
        "minimumHeight": min(minimum_height, available_height),
        "maximized": bool(saved and existing and saved["maximized"]),
        "restored": existing is not None,
    }
