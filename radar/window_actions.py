"""Explicit maximize actions against Radar's confirmed compositor state."""

from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any

from .errors import RadarError
from .window import RunCommand, Sleep, WINDOW_CLASS, WINDOW_TITLE, _run

ADDRESS = re.compile(r"0x[0-9a-fA-F]{1,16}")
CONFIRM_ATTEMPTS = 6
CONFIRM_DELAY_SECONDS = 0.08


def _client(runner: RunCommand) -> dict[str, Any]:
    response = _run(["hyprctl", "clients", "-j"], runner=runner)
    try:
        clients = json.loads(response.stdout)
    except (ValueError, RecursionError) as exc:
        raise RadarError("Hyprland returned invalid client JSON") from exc
    if not isinstance(clients, list) or not all(isinstance(item, dict) for item in clients):
        raise RadarError("Hyprland client response must be an array of objects")
    matches = [item for item in clients if item.get("mapped") is True
               and item.get("class") == item.get("initialClass") == WINDOW_CLASS
               and item.get("title") == item.get("initialTitle") == WINDOW_TITLE]
    if len(matches) != 1:
        raise RadarError("Hyprland Radar client is not mapped" if not matches else "Hyprland Radar client identity is ambiguous")
    client = matches[0]
    address = client.get("address")
    if not isinstance(address, str) or not ADDRESS.fullmatch(address) or int(address, 16) == 0:
        raise RadarError("Hyprland Radar client has invalid address")
    for key in ("fullscreen", "fullscreenClient"):
        if type(client.get(key)) is not int or client[key] not in (0, 1, 2):
            raise RadarError("Hyprland Radar client has invalid fullscreen state")
    if type(client.get("floating")) is not bool:
        raise RadarError("Hyprland Radar client has invalid floating state")
    return client


def _result(client: dict[str, Any], outcome: str) -> dict[str, Any]:
    return {
        "protocolVersion": 1, "status": "ok", "outcome": outcome,
        "address": client["address"], "mapped": True, "floating": client["floating"],
        "maximized": client["fullscreen"] == 1, "fullscreen": client["fullscreen"] == 2,
        "fullscreenInternal": client["fullscreen"], "fullscreenClient": client["fullscreenClient"],
    }


def window_state(*, runner: RunCommand = subprocess.run) -> dict[str, Any]:
    """Read actual internal/client modes, independent of Qt's CSD state hint."""
    return _result(_client(runner), "window-state")


def _maximize_script(client: dict[str, Any], desired: int) -> str:
    # All substitutions are constants or validated scalars. Recheck identity and
    # observed state in the same Lua turn as dispatch: a stale address must never
    # fall back to the active window. No globals, timers or rules are created.
    title = json.dumps(WINDOW_TITLE, ensure_ascii=False)
    klass = json.dumps(WINDOW_CLASS)
    address = json.dumps(client["address"].lower())
    floating = "true" if client["floating"] else "false"
    return (
        "local target = nil; local count = 0; "
        "for _, w in ipairs(hl.get_windows()) do "
        f"if w.mapped and w.class == {klass} and w.initial_class == {klass} "
        f"and w.title == {title} and w.initial_title == {title} then "
        "target = w; count = count + 1 end end; "
        f"if count ~= 1 or target.address ~= {address} "
        f"or target.fullscreen ~= {client['fullscreen']} "
        f"or target.fullscreen_client ~= {client['fullscreenClient']} "
        f"or target.floating ~= {floating} or target.group ~= nil then "
        'error("Radar window changed before maximize action") end; '
        "local result = hl.dispatch(hl.dsp.window.fullscreen_state({"
        f'internal = {desired}, client = {desired}, action = "set", '
        "layout_aware = true, window = target })); "
        'if type(result) ~= "table" or result.ok ~= true then '
        'error("Radar maximize action was rejected") end'
    )


def toggle_window_maximized(
    *, runner: RunCommand = subprocess.run, sleeper: Sleep = time.sleep,
) -> dict[str, Any]:
    """Toggle only normal/maximized modes; explicit fullscreen remains intact."""
    before = _client(runner)
    if 2 in (before["fullscreen"], before["fullscreenClient"]):
        return _result(before, "fullscreen-preserved")
    if before.get("grouped"):
        raise RadarError("Grouped Radar windows cannot be maximized independently")
    desired = 0 if before["fullscreen"] == 1 else 1
    response = _run(["hyprctl", "eval", _maximize_script(before, desired)], runner=runner)
    # v0.56.2 eval returns exactly 'ok' after a successful no-value evaluation.
    # Warnings and unsupported-eval replies can otherwise have a zero exit code.
    if response.stdout.strip() != "ok":
        raise RadarError("Hyprland did not confirm the maximize action")
    for attempt in range(CONFIRM_ATTEMPTS):
        after = _client(runner)
        if after["address"].lower() != before["address"].lower() or after["floating"] != before["floating"]:
            raise RadarError("Radar window changed while confirming maximize action")
        if after["fullscreen"] == after["fullscreenClient"] == desired:
            return _result(after, "maximized" if desired else "restored")
        if 2 in (after["fullscreen"], after["fullscreenClient"]):
            raise RadarError("Radar entered fullscreen while confirming maximize action")
        if attempt + 1 < CONFIRM_ATTEMPTS:
            sleeper(CONFIRM_DELAY_SECONDS)
    # Never issue a second dispatch or an automatic inverse after uncertainty:
    # an intervening user action belongs to the user.
    raise RadarError("Radar maximize state was not confirmed")
