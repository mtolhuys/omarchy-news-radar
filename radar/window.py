"""Bounded Hyprland integration for Radar's normal application window."""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections.abc import Callable
from typing import Any

from .errors import RadarError

WINDOW_TITLE = "📰 Omarchy News Radar"
WINDOW_CLASS = "org.quickshell"
ADDRESS_PATTERN = re.compile(r"0x[0-9a-fA-F]+")
PROBE_ATTEMPTS = 10
PROBE_DELAY_SECONDS = 0.12
COMMAND_TIMEOUT_SECONDS = 1.0
MAX_RESPONSE_BYTES = 128 * 1024

RunCommand = Callable[..., subprocess.CompletedProcess[str]]
Sleep = Callable[[float], None]


def _run(command: list[str], *, runner: RunCommand) -> subprocess.CompletedProcess[str]:
    result = runner(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RadarError(f"window integration command failed: {command[0]} {command[1]}")
    if len(result.stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise RadarError("Hyprland window response exceeds its bound")
    return result


def activate_window(
    *,
    runner: RunCommand = subprocess.run,
    sleeper: Sleep = time.sleep,
) -> dict[str, Any]:
    """Float and focus only the unique mapped Radar client; leave all others alone."""

    for attempt in range(PROBE_ATTEMPTS):
        result = _run(["hyprctl", "clients", "-j"], runner=runner)
        try:
            clients = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RadarError("Hyprland returned invalid client JSON") from exc
        if not isinstance(clients, list) or not all(isinstance(client, dict) for client in clients):
            raise RadarError("Hyprland client response must be an array of objects")
        matches = [
            client
            for client in clients
            if client.get("title") == WINDOW_TITLE
            and client.get("initialTitle") == WINDOW_TITLE
            and client.get("class") == WINDOW_CLASS
            and client.get("initialClass") == WINDOW_CLASS
            and client.get("mapped") is True
        ]
        if len(matches) > 1:
            raise RadarError("Hyprland Radar client identity is ambiguous")
        if not matches:
            if attempt + 1 < PROBE_ATTEMPTS:
                sleeper(PROBE_DELAY_SECONDS)
            continue
        client = matches[0]
        floating = client.get("floating")
        if floating is not True and floating is not False:
            raise RadarError("Hyprland Radar client has invalid floating state")
        address = client.get("address")
        if not isinstance(address, str) or ADDRESS_PATTERN.fullmatch(address) is None:
            raise RadarError("Hyprland Radar client has invalid address")
        if floating is False:
            lua_action = (
                'hl.dsp.window.float({ window = "address:'
                + address
                + '", action = "toggle" })'
            )
            try:
                _run(["hyprctl", "dispatch", lua_action], runner=runner)
            except RadarError:
                _run(["hyprctl", "dispatch", "togglefloating", f"address:{address}"], runner=runner)
        focus_action = 'hl.dsp.focus({ window = "address:' + address + '" })'
        _run(["hyprctl", "dispatch", focus_action], runner=runner)
        return {
            "protocolVersion": 1,
            "status": "ok",
            "outcome": "floated-and-focused" if floating is False else "focused",
        }
    return {"protocolVersion": 1, "status": "ok", "outcome": "radar-not-mapped"}
