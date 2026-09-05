"""Transient opening-rule ownership within Hyprland's persistent Lua state."""

from __future__ import annotations

import json
from typing import Any

OPENING_RULE = "omarchy_news_radar_opening_rule"
OPENING_SPEC = "omarchy_news_radar_opening_spec"
OPENING_TIMER = "omarchy_news_radar_opening_timer"
OPENING_TOKEN = "omarchy_news_radar_opening_token"
RULE_TIMEOUT_MS = 8000


def clear_rule_script(token: str | None = None) -> str:
    # Keep the disabled handle for reuse. Hyprland merges named declarations,
    # appending effects even when the declaration is identical. Its one-shot
    # timers release their callback only after firing; cancelling would retain
    # each callback until a config reload. Old callbacks must instead fire inert.
    cleanup = (
        f"if {OPENING_RULE} then {OPENING_RULE}:set_enabled(false) end; "
        f"{OPENING_TIMER} = nil; {OPENING_TOKEN} = nil"
    )
    if token is None:
        return cleanup
    return f'if {OPENING_TOKEN} == "{token}" then {cleanup} end'


def opening_rule_script(geometry: dict[str, Any], token: str) -> str:
    """Use only geometry/token scalars already validated by the window helper."""
    declaration = (
        '{ name = "omarchy-news-radar-opening", '
        'match = { class = "^org[.]quickshell$", title = "^📰 Omarchy News Radar$", '
        'initial_class = "^org[.]quickshell$", initial_title = "^📰 Omarchy News Radar$" }, '
        f'float = true, no_anim = true, monitor = "{geometry["monitor"]}", '
        f'size = {{ {geometry["width"]}, {geometry["height"]} }}, '
        f'move = {{ {geometry["localX"]}, {geometry["localY"]} }}, '
        f'maximize = {str(geometry["maximized"]).lower()} }}'
    )
    # Fingerprint the complete declaration so a changed geometry or rule
    # contract cannot accidentally reuse an earlier spec after plugin reload.
    spec = json.dumps(declaration, ensure_ascii=False)
    return (
        clear_rule_script() + "; "
        f'{OPENING_TOKEN} = "{token}"; '
        f'if not {OPENING_RULE} or {OPENING_RULE}:is_enabled() == nil '
        f'or {OPENING_SPEC} ~= {spec} then '
        f'{OPENING_RULE} = hl.window_rule({declaration}); {OPENING_SPEC} = {spec} end; '
        f'{OPENING_RULE}:set_enabled(true); '
        f'assert({OPENING_RULE}:is_enabled() == true, "Radar opening rule was not enabled"); '
        f'local owned_rule = {OPENING_RULE}; local owned_token = {OPENING_TOKEN}; '
        f'{OPENING_TIMER} = hl.timer(function() '
        f'if {OPENING_TOKEN} == owned_token and {OPENING_RULE} == owned_rule then '
        f'owned_rule:set_enabled(false); {OPENING_TIMER} = nil; {OPENING_TOKEN} = nil end '
        f'end, {{ timeout = {RULE_TIMEOUT_MS}, type = "oneshot" }})'
    )
