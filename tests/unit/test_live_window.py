from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from radar.cli import client_main
from radar.errors import RadarError
from radar.window import fit_window
from tests.unit.test_window_geometry import Runner, monitor


def client(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "title": "📰 Omarchy News Radar", "initialTitle": "📰 Omarchy News Radar",
        "class": "org.quickshell", "initialClass": "org.quickshell", "mapped": True,
        "address": "0xA07", "floating": True, "monitor": 0,
        "at": [-2048, 40], "size": [950, 640], "fullscreen": 0, "fullscreenClient": 0,
    }
    value.update(changes)
    return value


class LiveWindowTests(unittest.TestCase):
    def test_valid_user_placement_is_an_exact_noop_even_next_to_workarea_edge(self) -> None:
        runner = Runner([client()], [monitor()])
        result = fit_window(minimum_width=720, minimum_height=480, runner=runner)
        self.assertEqual("unchanged", result["outcome"])
        self.assertEqual((-2048, 40, 950, 640), tuple(result["geometry"][k] for k in ("x", "y", "width", "height")))
        self.assertEqual(2, len(runner.commands))

    def test_live_font_growth_clamps_size_and_position_using_current_monitor(self) -> None:
        runner = Runner([client(at=[556, 52], size=[724, 740])],
                        [monitor(width=1280, height=800, scale=1, x=0, reserved=[0, 52, 0, 0])], "ok", "ok")
        result = fit_window(minimum_width=1440, minimum_height=960, runner=runner)
        self.assertEqual("refitted", result["outcome"])
        self.assertEqual((16, 68, 1248, 716, 1248, 716),
                         tuple(result["geometry"][k] for k in ("x", "y", "width", "height", "minimumWidth", "minimumHeight")))
        self.assertEqual([
            ["hyprctl", "dispatch", 'hl.dsp.window.resize({ window = "address:0xA07", x = 1248, y = 716 })'],
            ["hyprctl", "dispatch", 'hl.dsp.window.move({ window = "address:0xA07", x = 16, y = 68 })'],
        ], runner.commands[2:])

    def test_only_position_changes_when_the_size_already_fits(self) -> None:
        runner = Runner([client(at=[-1200, 700])], [monitor()], "ok")
        result = fit_window(minimum_width=720, minimum_height=480, runner=runner)
        self.assertEqual((950, 640), (result["geometry"]["width"], result["geometry"]["height"]))
        self.assertEqual(3, len(runner.commands))
        self.assertIn("hl.dsp.window.move", runner.commands[-1][-1])

    def test_font_minimum_growth_resizes_without_moving_a_still_valid_origin(self) -> None:
        runner = Runner([client(at=[-2032, 56])], [monitor()], "ok")
        result = fit_window(minimum_width=1200, minimum_height=700, runner=runner)
        self.assertEqual((-2032, 56, 1200, 700),
                         tuple(result["geometry"][k] for k in ("x", "y", "width", "height")))
        self.assertEqual(3, len(runner.commands))
        self.assertIn("hl.dsp.window.resize", runner.commands[-1][-1])

    def test_font_reduction_does_not_shrink_a_large_user_frame(self) -> None:
        runner = Runner([client(at=[-2032, 56], size=[1700, 900])], [monitor()])
        result = fit_window(minimum_width=720, minimum_height=480, runner=runner)
        self.assertEqual("unchanged", result["outcome"])
        self.assertEqual((1700, 900), (result["geometry"]["width"], result["geometry"]["height"]))
        self.assertEqual(2, len(runner.commands))

    def test_disconnected_monitor_uses_active_monitor_without_resetting_valid_size(self) -> None:
        runner = Runner([client(monitor=77)],
                        [monitor(focused=False), monitor(id=1, name="HDMI-A-1", x=0, focused=True)], "ok")
        result = fit_window(minimum_width=720, minimum_height=480, runner=runner)
        fit = result["geometry"]
        self.assertEqual(("HDMI-A-1", 950, 640), (fit["monitor"], fit["width"], fit["height"]))
        self.assertGreaterEqual(fit["x"], 0)
        self.assertFalse(fit["restored"])
        self.assertEqual(3, len(runner.commands))
        self.assertIn("hl.dsp.window.move", runner.commands[-1][-1])

    def test_maximized_fullscreen_and_tiled_frames_remain_compositor_managed(self) -> None:
        for changes in ({"fullscreen": 1}, {"fullscreen": 2}, {"fullscreenClient": 1},
                        {"fullscreenClient": 2}, {"floating": False}):
            with self.subTest(changes=changes):
                runner = Runner([client(at=[-3000, -20], size=[4000, 2000], **changes)], [monitor()])
                result = fit_window(minimum_width=4000, minimum_height=2000, runner=runner)
                self.assertEqual("compositor-managed", result["outcome"])
                self.assertEqual((-3000, -20, 4000, 2000),
                                 tuple(result["geometry"][k] for k in ("x", "y", "width", "height")))
                self.assertEqual((2016, 1080), (result["geometry"]["minimumWidth"], result["geometry"]["minimumHeight"]))
                self.assertEqual(2, len(runner.commands))

    def test_similar_or_unmapped_windows_cannot_be_selected(self) -> None:
        for changes in ({"title": "Other"}, {"initialTitle": "Other"}, {"class": "Other"},
                        {"initialClass": "Other"}, {"mapped": False}):
            with self.subTest(changes=changes):
                runner = Runner([client(**changes)])
                self.assertEqual("radar-not-mapped", fit_window(minimum_width=720, minimum_height=480, runner=runner)["outcome"])
                self.assertEqual(1, len(runner.commands))

    def test_ambiguous_window_or_monitor_identity_fails_without_dispatch(self) -> None:
        for values in (([client(), client(address="0xB08")],),
                       ([client()], [monitor(), monitor(name="DP-2")])):
            with self.subTest(values=values):
                runner = Runner(*values)
                with self.assertRaisesRegex(RadarError, "ambiguous"):
                    fit_window(minimum_width=720, minimum_height=480, runner=runner)
                self.assertFalse(any("dispatch" in command for command in runner.commands))

    def test_invalid_geometry_and_identity_fields_never_reach_dispatch(self) -> None:
        for changes in ({"address": '0x1\"; bad()'}, {"floating": 1}, {"monitor": True},
                        {"at": [1]}, {"size": [True, 640]}, {"fullscreenClient": "1"}):
            with self.subTest(changes=changes):
                runner = Runner([client(**changes)], [monitor()])
                with self.assertRaises(RadarError):
                    fit_window(minimum_width=720, minimum_height=480, runner=runner)
                self.assertFalse(any("dispatch" in command for command in runner.commands))

    def test_invalid_minimums_fail_before_any_compositor_query(self) -> None:
        for value in (True, 0, 63, 65537, "720"):
            with self.subTest(value=value):
                runner = Runner()
                with self.assertRaises(RadarError):
                    fit_window(minimum_width=value, minimum_height=480, runner=runner)
                self.assertEqual([], runner.commands)

    def test_failed_resize_is_not_reported_as_a_successful_fit(self) -> None:
        runner = Runner([client()], [monitor()], RadarError("resize refused"))
        with self.assertRaisesRegex(RadarError, "resize refused"):
            fit_window(minimum_width=1200, minimum_height=700, runner=runner)
        self.assertEqual(3, len(runner.commands))

    def test_cli_passes_only_typed_minimums_and_returns_fit(self) -> None:
        output = io.StringIO()
        result = {"status": "ok", "outcome": "unchanged", "geometry": {"minimumWidth": 720}}
        with patch("radar.cli.fit_window", return_value=result) as fitting, \
                patch("radar.cli.require_unprivileged"), contextlib.redirect_stdout(output):
            self.assertEqual(0, client_main(["fit-window", "--minimum-width", "720", "--minimum-height", "480"]))
        fitting.assert_called_once_with(minimum_width=720, minimum_height=480)
        self.assertEqual(result, json.loads(output.getvalue()))


if __name__ == "__main__":
    unittest.main()
