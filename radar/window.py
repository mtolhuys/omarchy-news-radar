"""Bounded Hyprland integration for Radar's normal application window."""

from __future__ import annotations

import json
import re
import secrets
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


# This named rule exists only across first mapping. The compositor owns its
# expiry too, so killing the shell cannot leave an active placement rule.
OPENING_RULE = "omarchy_news_radar_opening_rule"
OPENING_TIMER = "omarchy_news_radar_opening_timer"
OPENING_TOKEN = "omarchy_news_radar_opening_token"
OPENING_TOKEN_RE = re.compile(r"[0-9a-f]{32}")
RULE_TIMEOUT_MS = 8000


def _clear_rule_script(token: str | None = None) -> str:
    cleanup = (
        f"if {OPENING_TIMER} then {OPENING_TIMER}:set_enabled(false) end; {OPENING_TIMER} = nil; "
        f"if {OPENING_RULE} then {OPENING_RULE}:set_enabled(false) end; {OPENING_RULE} = nil; "
        f"{OPENING_TOKEN} = nil"
    )
    if token is None:
        # Only a new preparation can retire a previous Radar-owned rule.
        return cleanup
    return f'if {OPENING_TOKEN} == "{token}" then {cleanup} end'


def _json_command(command: list[str], *, runner: RunCommand) -> Any:
    result = _run(command, runner=runner)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RadarError("Hyprland returned invalid window JSON") from exc


def _window_placement(environment: Any = None) -> dict[str, Any] | None:
    from .errors import ValidationError
    from .io import read_json_bounded, refuse_symlink
    from .state import state_root
    from .window_geometry import validate_placement

    directory = state_root(environment)
    refuse_symlink(directory)
    try:
        value = read_json_bounded(directory / "window.json", 4096)
    except FileNotFoundError:
        return None
    except ValidationError:
        return None
    try:
        return validate_placement(value)
    except RadarError:
        # A stale or malformed preference is a reason to choose a fresh fit,
        # never a reason to make news unavailable.
        return None


def prepare_window(
    *, width: int, height: int, minimum_width: int, minimum_height: int,
    environment: Any = None, runner: RunCommand = subprocess.run,
) -> dict[str, Any]:
    """Apply an expiring exact-identity rule before QML makes its toplevel visible."""
    from .window_geometry import monitor_workareas, opening_geometry

    monitors = monitor_workareas(_json_command(["hyprctl", "monitors", "-j"], runner=runner))
    geometry = opening_geometry(monitors, _window_placement(environment), width=width, height=height,
                                minimum_width=minimum_width, minimum_height=minimum_height)
    # Every interpolated value is either a source constant or a validated
    # integer/connector. No feed text, user expression, shell or generic rule.
    token = secrets.token_hex(16)
    script = (
        _clear_rule_script() + "; "
        f'{OPENING_TOKEN} = "{token}"; '
        f'{OPENING_RULE} = hl.window_rule({{ name = "omarchy-news-radar-opening", '
        'match = { class = "^org[.]quickshell$", title = "^📰 Omarchy News Radar$", '
        'initial_class = "^org[.]quickshell$", initial_title = "^📰 Omarchy News Radar$" }, '
        f'float = true, no_anim = true, monitor = "{geometry["monitor"]}", '
        f'size = {{ {geometry["width"]}, {geometry["height"]} }}, '
        f'move = {{ {geometry["localX"]}, {geometry["localY"]} }}, '
        f'maximize = {str(geometry["maximized"]).lower()} }}); '
        f'local owned_rule = {OPENING_RULE}; local owned_token = {OPENING_TOKEN}; '
        f'{OPENING_TIMER} = hl.timer(function() '
        f'if {OPENING_TOKEN} == owned_token and {OPENING_RULE} == owned_rule then '
        f'owned_rule:set_enabled(false); {OPENING_RULE} = nil; {OPENING_TIMER} = nil; {OPENING_TOKEN} = nil end '
        f'end, {{ timeout = {RULE_TIMEOUT_MS}, type = "oneshot" }})'
    )
    try:
        _run(["hyprctl", "eval", script], runner=runner)
    except (RadarError, OSError, subprocess.SubprocessError):
        try:
            finish_window_opening(token=token, runner=runner)
        except (RadarError, OSError, subprocess.SubprocessError):
            pass
        raise
    return {"protocolVersion": 1, "status": "ok", "outcome": "prepared", "geometry": geometry, "openingToken": token}


def finish_window_opening(*, token: str | None = None, runner: RunCommand = subprocess.run) -> dict[str, Any]:
    """A late close/cancel may clear only its own opening generation."""
    if token is None:
        return {"protocolVersion": 1, "status": "ok", "outcome": "opening-rule-not-owned"}
    if not isinstance(token, str) or not OPENING_TOKEN_RE.fullmatch(token):
        raise RadarError("invalid opening ownership token")
    _run(["hyprctl", "eval", _clear_rule_script(token)], runner=runner)
    return {"protocolVersion": 1, "status": "ok", "outcome": "opening-rule-cleared"}


def remember_window(*, environment: Any = None, runner: RunCommand = subprocess.run) -> dict[str, Any]:
    """Capture the one exact mapped Radar window without changing compositor state."""
    from .io import atomic_write_json
    from .state import state_root
    from .window_geometry import monitor_workareas, validate_placement

    clients = _json_command(["hyprctl", "clients", "-j"], runner=runner)
    if not isinstance(clients, list) or not all(isinstance(c, dict) for c in clients):
        raise RadarError("invalid Hyprland client list")
    matches = [c for c in clients if c.get("title") == WINDOW_TITLE and c.get("initialTitle") == WINDOW_TITLE
               and c.get("class") == WINDOW_CLASS and c.get("initialClass") == WINDOW_CLASS and c.get("mapped") is True]
    if len(matches) > 1:
        raise RadarError("Hyprland Radar client identity is ambiguous")
    if not matches:
        return {"protocolVersion": 1, "status": "ok", "outcome": "radar-not-mapped"}
    client = matches[0]
    monitors = monitor_workareas(_json_command(["hyprctl", "monitors", "-j"], runner=runner))
    monitor = next((m for m in monitors if m["id"] == client.get("monitor")), None)
    if monitor is None:
        raise RadarError("Radar window monitor is unavailable")
    saved = _window_placement(environment)
    maximized = client.get("fullscreen") in (1, 2) or client.get("fullscreenClient") in (1, 2)
    at, size = client.get("at"), client.get("size")
    if not isinstance(at, list) or len(at) != 2 or not isinstance(size, list) or len(size) != 2:
        raise RadarError("invalid Radar client geometry")
    value = validate_placement({
        "schemaVersion": 1, "monitor": monitor["name"], "maximized": maximized,
        "x": saved["x"] if maximized and saved else at[0],
        "y": saved["y"] if maximized and saved else at[1],
        "width": saved["width"] if maximized and saved else size[0],
        "height": saved["height"] if maximized and saved else size[1],
    })
    if value != saved:
        atomic_write_json(state_root(environment) / "window.json", value)
    return {"protocolVersion": 1, "status": "ok", "outcome": "remembered", "geometry": value}
