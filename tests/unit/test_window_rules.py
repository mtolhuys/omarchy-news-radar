"""Execute ownership callbacks without touching a running compositor.

The ordinary source suite remains Python-only where Lua is unavailable. Plugin
Lab and the maintainer environment have Lua and execute these semantic checks.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest

from radar.window_rules import clear_rule_script, opening_rule_script

GEOMETRY = dict(monitor="DP-1", width=1120, height=720, localX=16, localY=52, maximized=False)
HARNESS = """
local declarations, timers = {}, {}
local named = nil
hl = {}
function hl.window_rule(spec)
  declarations[#declarations + 1] = spec
  if not named or named.expired then
    named = {enabled = true}
    function named:set_enabled(enabled) self.enabled = enabled end
    function named:is_enabled() if not self.expired then return self.enabled end end
  end
  named.enabled = true
  return named
end
function hl.timer(callback, options)
  assert(options.type == "oneshot" and options.timeout == 8000)
  local timer = {enabled = true, callback = callback}
  function timer:set_enabled(enabled) self.enabled = enabled end
  function timer:fire()
    assert(self.enabled and self.callback, "cancelled timers cannot self-release")
    self.enabled = false
    self.callback()
    self.callback = nil
  end
  timers[#timers + 1] = timer
  return timer
end
"""


@unittest.skipUnless(shutil.which("lua"), "Lua callback checks require the Plugin Lab Lua runtime")
class WindowRuleLifecycleTests(unittest.TestCase):
    def check_lua(self, *chunks: str) -> None:
        result = subprocess.run(["lua", "-"], input=HARNESS + "\n" + ";\n".join(chunks),
                                text=True, capture_output=True, timeout=5, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_repeated_open_close_reuses_one_rule_and_timers_release(self) -> None:
        chunks = []
        for index in range(40):
            token = f"{index:032x}"
            chunks.extend([opening_rule_script(GEOMETRY, token), clear_rule_script(token)])
        self.check_lua(*chunks, """
          assert(#declarations == 1, "identical opens must not append effects")
          assert(not named.enabled and omarchy_news_radar_opening_rule == named)
          assert(omarchy_news_radar_opening_token == nil)
          assert(#timers == 40)
          for _, timer in ipairs(timers) do timer:fire(); assert(timer.callback == nil) end
          assert(not named.enabled and omarchy_news_radar_opening_timer == nil)
        """)

    def test_old_expiry_and_close_cannot_disable_new_owner_even_when_handle_reused(self) -> None:
        self.check_lua(
            opening_rule_script(GEOMETRY, "a" * 32),
            opening_rule_script(GEOMETRY, "b" * 32),
            clear_rule_script("a" * 32),
            "assert(named.enabled); timers[1]:fire(); assert(named.enabled)",
            "assert(omarchy_news_radar_opening_timer == timers[2])",
            "timers[2]:fire(); assert(not named.enabled)",
            "assert(omarchy_news_radar_opening_token == nil)",
            "assert(#declarations == 1)",
        )

    def test_changed_geometry_and_expired_handle_are_redeclared(self) -> None:
        self.check_lua(
            opening_rule_script(GEOMETRY, "a" * 32),
            opening_rule_script({**GEOMETRY, "localX": 100}, "b" * 32),
            "assert(#declarations == 2 and declarations[2].move[1] == 100)",
            "timers[1]:fire(); assert(named.enabled)",
            "named.expired = true",
            opening_rule_script({**GEOMETRY, "localX": 100}, "c" * 32),
            "assert(#declarations == 3 and not named.expired)",
            "timers[2]:fire(); assert(named.enabled)",
            "timers[3]:fire(); assert(not named.enabled)",
            "assert(declarations[3].match.initial_title == '^📰 Omarchy News Radar$')",
        )
