from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from radar.errors import RadarError
from radar.window import finish_window_opening, prepare_window, remember_window
from radar.window_geometry import monitor_workareas, opening_geometry


def monitor(**changes: object) -> dict[str, object]:
    value: dict[str, object] = dict(id=0, name="DP-1", width=2560, height=1440,
                                  scale=1.25, x=-2048, y=0, reserved=[0, 40, 0, 0], focused=True)
    value.update(changes)
    return value


class Runner:
    def __init__(self, *values: object) -> None:
        self.values = list(values)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        assert kwargs["timeout"] == 1.0
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return subprocess.CompletedProcess(command, 0, json.dumps(value) if value != "ok" else "ok", "")


class WindowGeometryTests(unittest.TestCase):
    def test_default_fit_uses_logical_workarea_and_active_monitor(self) -> None:
        monitors = monitor_workareas([monitor(focused=False), monitor(id=1, name="HDMI-A-1", x=0, focused=True)])
        fit = opening_geometry(monitors, None, width=1120, height=720, minimum_width=720, minimum_height=480)
        self.assertEqual("HDMI-A-1", fit["monitor"])
        self.assertEqual((464, 236), (fit["x"], fit["y"]))
        self.assertEqual((1120, 720), (fit["width"], fit["height"]))

    def test_saved_monitor_geometry_clamps_after_resolution_changes(self) -> None:
        saved = dict(monitor="DP-1", x=-3000, y=1400, width=4000, height=2400, maximized=False)
        fit = opening_geometry(monitor_workareas([monitor()]), saved,
                               width=1120, height=720, minimum_width=720, minimum_height=480)
        self.assertEqual((-2032, 56, 2016, 1080), (fit["x"], fit["y"], fit["width"], fit["height"]))
        self.assertEqual((16, 56), (fit["localX"], fit["localY"]))
        self.assertTrue(fit["restored"])

    def test_missing_saved_monitor_returns_to_active_monitor_with_default_size(self) -> None:
        saved = dict(monitor="old-output", x=9000, y=4000, width=4000, height=2000, maximized=True)
        fit = opening_geometry(monitor_workareas([monitor()]), saved,
                               width=1120, height=720, minimum_width=720, minimum_height=480)
        self.assertEqual((1120, 720), (fit["width"], fit["height"]))
        self.assertFalse(fit["restored"])
        self.assertFalse(fit["maximized"])

    def test_rotation_and_large_text_minimum_stay_inside_workarea(self) -> None:
        fit = opening_geometry(monitor_workareas([monitor(transform=1)]), None,
                               width=2240, height=1440, minimum_width=1440, minimum_height=960)
        self.assertEqual(1120, fit["width"])
        self.assertEqual(1120, fit["minimumWidth"])
        self.assertLessEqual(fit["height"], 1976)

    def test_smallest_usable_monitor_does_not_shrink_below_saved_geometry_bound(self) -> None:
        fit = opening_geometry(monitor_workareas([monitor(width=64, height=64, scale=1, x=0, reserved=[0, 0, 0, 0])]), None,
                               width=1120, height=720, minimum_width=720, minimum_height=480)
        self.assertEqual((64, 64, 64, 64), tuple(fit[key] for key in ("width", "height", "minimumWidth", "minimumHeight")))

    def test_untrusted_monitor_fields_never_reach_lua(self) -> None:
        for change in ({"name": 'DP-1"; bad()'}, {"scale": float("nan")}, {"width": True},
                       {"reserved": [-1, 0, 0, 0]}, {"reserved": [0, 9999, 0, 0]}):
            with self.subTest(change=change), self.assertRaises(RadarError):
                monitor_workareas([monitor(**change)])

    def test_pre_map_rule_is_named_exact_and_has_its_own_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            runner = Runner([monitor()], "ok")
            result = prepare_window(width=1120, height=720, minimum_width=720, minimum_height=480,
                                    environment={"XDG_STATE_HOME": d}, runner=runner)
        self.assertEqual("prepared", result["outcome"])
        script = runner.commands[-1][-1]
        self.assertEqual(["hyprctl", "eval"], runner.commands[-1][:2])
        self.assertIn('name = "omarchy-news-radar-opening"', script)
        self.assertIn('initial_class = "^org[.]quickshell$"', script)
        self.assertIn('initial_title = "^📰 Omarchy News Radar$"', script)
        self.assertIn('float = true, no_anim = true, monitor = "DP-1"', script)
        self.assertIn('timeout = 8000, type = "oneshot"', script)
        self.assertIn('== owned_rule', script)
        self.assertFalse(any("dispatch" in command for command in runner.commands))

    def test_failed_preparation_attempts_only_owned_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            runner = Runner([monitor()], RadarError("rule failed"), "ok")
            with self.assertRaisesRegex(RadarError, "rule failed"):
                prepare_window(width=1120, height=720, minimum_width=720, minimum_height=480,
                               environment={"XDG_STATE_HOME": d}, runner=runner)
        self.assertIn('omarchy_news_radar_opening_rule:set_enabled(false)', runner.commands[-1][-1])
        self.assertNotIn('hl.window_rule', runner.commands[-1][-1])

    def test_remember_is_exact_private_and_preserves_normal_geometry_when_maximized(self) -> None:
        record = {"title": "📰 Omarchy News Radar", "initialTitle": "📰 Omarchy News Radar",
                  "class": "org.quickshell", "initialClass": "org.quickshell", "mapped": True,
                  "monitor": 0, "at": [-1800, 160], "size": [950, 640], "fullscreen": 0}
        with tempfile.TemporaryDirectory() as d:
            environment = {"XDG_STATE_HOME": d}
            remember_window(environment=environment, runner=Runner([record], [monitor()]))
            path = Path(d)/"omarchy-news-radar/window.json"
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            self.assertEqual([950, 640], [json.loads(path.read_text())[key] for key in ("width", "height")])
            maximized = {**record, "fullscreen": 1, "size": [2048, 1112]}
            result = remember_window(environment=environment, runner=Runner([maximized], [monitor()]))
            self.assertEqual((950, 640, True), tuple(result["geometry"][key] for key in ("width", "height", "maximized")))
            runner = Runner([{**record, "title": "Other shell window"}])
            self.assertEqual("radar-not-mapped", remember_window(environment=environment, runner=runner)["outcome"])
            self.assertEqual(1, len(runner.commands))

    def test_cleanup_does_not_touch_other_rules_or_configuration(self) -> None:
        runner = Runner("ok")
        finish_window_opening(token="a" * 32, runner=runner)
        self.assertEqual(1, len(runner.commands))
        self.assertTrue(runner.commands[0][-1].startswith('if omarchy_news_radar_opening_token == "' + "a" * 32 + '" then'))
        self.assertNotIn("reload", runner.commands[0][-1])
        self.assertNotIn("hl.config", runner.commands[0][-1])

    def test_delayed_old_cleanup_cannot_address_the_next_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as d, patch("radar.window.secrets.token_hex", side_effect=["a" * 32, "b" * 32]):
            runner = Runner([monitor()], "ok", [monitor()], "ok", "ok")
            first = prepare_window(width=1120, height=720, minimum_width=720, minimum_height=480,
                                   environment={"XDG_STATE_HOME": d}, runner=runner)
            second = prepare_window(width=1120, height=720, minimum_width=720, minimum_height=480,
                                    environment={"XDG_STATE_HOME": d}, runner=runner)
            finish_window_opening(token=first["openingToken"], runner=runner)
        self.assertNotEqual(first["openingToken"], second["openingToken"])
        replacement = runner.commands[3][-1]
        late_cleanup = runner.commands[4][-1]
        self.assertIn('omarchy_news_radar_opening_token = "' + second["openingToken"] + '"', replacement)
        self.assertTrue(late_cleanup.startswith('if omarchy_news_radar_opening_token == "' + first["openingToken"] + '" then'))
        self.assertNotIn(second["openingToken"], late_cleanup)
        self.assertTrue(late_cleanup.endswith(" end"))

    def test_missing_or_invalid_ownership_never_issues_unconditional_cleanup(self) -> None:
        runner = Runner()
        self.assertEqual("opening-rule-not-owned", finish_window_opening(runner=runner)["outcome"])
        for token in ("", "wrong", '"; evil()', 1):
            with self.subTest(token=token), self.assertRaises(RadarError):
                finish_window_opening(token=token, runner=runner)
        self.assertEqual([], runner.commands)


if __name__ == "__main__":
    unittest.main()
