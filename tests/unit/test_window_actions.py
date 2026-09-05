from __future__ import annotations

import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

from radar.cli import client_main
from radar.errors import RadarError
from radar.window import MAX_RESPONSE_BYTES, WINDOW_CLASS, WINDOW_TITLE
from radar.window_actions import CONFIRM_ATTEMPTS, toggle_window_maximized, window_state


def client(**changes: object) -> dict[str, object]:
    return {"title": WINDOW_TITLE, "initialTitle": WINDOW_TITLE, "class": WINDOW_CLASS,
            "initialClass": WINDOW_CLASS, "mapped": True, "floating": True,
            "address": "0x123a", "fullscreen": 0, "fullscreenClient": 0, "grouped": [], **changes}


class Runner:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.commands: list[list[str]] = []
        self.options: list[dict[str, object]] = []

    def __call__(self, command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        self.options.append(options)
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, subprocess.CompletedProcess):
            return value
        return subprocess.CompletedProcess(command, 0, value if isinstance(value, str) else json.dumps(value), "")


class WindowActionTests(unittest.TestCase):
    def test_status_uses_actual_internal_mode_and_never_dispatches(self) -> None:
        for internal, external in ((0, 0), (0, 1), (1, 1), (2, 2)):
            with self.subTest(internal=internal, external=external):
                runner = Runner([client(fullscreen=internal, fullscreenClient=external)])
                result = window_state(runner=runner)
                self.assertEqual(internal == 1, result["maximized"])
                self.assertEqual(internal == 2, result["fullscreen"])
                self.assertEqual((internal, external), (result["fullscreenInternal"], result["fullscreenClient"]))
                self.assertEqual([["hyprctl", "clients", "-j"]], runner.commands)

    def test_toggle_ignores_client_maximize_hint_and_confirms_compositor_result(self) -> None:
        runner = Runner([client(fullscreenClient=1)], "ok\n", [client(fullscreen=1, fullscreenClient=1)])
        result = toggle_window_maximized(runner=runner)
        self.assertEqual("maximized", result["outcome"])
        script = runner.commands[1][2]
        self.assertIn('internal = 1, client = 1, action = "set"', script)
        self.assertIn("window = target", script)
        self.assertIn('target.address ~= "0x123a"', script)
        self.assertIn("count ~= 1", script)
        self.assertIn("target.fullscreen_client ~= 1", script)
        self.assertIn("target.group ~= nil", script)
        self.assertNotIn("hl.dsp.focus", script)
        self.assertNotIn("hl.dsp.window.float(", script)
        self.assertTrue(all(item["timeout"] == 1.0 and item["check"] is False for item in runner.options))

    def test_restore_is_explicit_zero_and_preserves_floating_state(self) -> None:
        runner = Runner([client(fullscreen=1, fullscreenClient=1, floating=False)], "ok",
                        [client(floating=False)])
        result = toggle_window_maximized(runner=runner)
        self.assertEqual("restored", result["outcome"])
        self.assertFalse(result["floating"])
        self.assertIn('internal = 0, client = 0, action = "set"', runner.commands[1][2])

    def test_explicit_internal_or_client_fullscreen_is_preserved(self) -> None:
        for internal, external in ((2, 2), (2, 0), (0, 2), (1, 2)):
            with self.subTest(internal=internal, external=external):
                runner = Runner([client(fullscreen=internal, fullscreenClient=external)])
                self.assertEqual("fullscreen-preserved", toggle_window_maximized(runner=runner)["outcome"])
                self.assertEqual(1, len(runner.commands))

    def test_missing_ambiguous_and_nonexact_identities_never_dispatch(self) -> None:
        cases = [[], [client(), client(address="0x124")]]
        for key, value in (("title", "other"), ("initialTitle", "other"), ("class", "other"),
                           ("initialClass", "other"), ("mapped", False), ("mapped", 1)):
            cases.append([client(**{key: value})])
        for clients in cases:
            with self.subTest(clients=clients):
                runner = Runner(clients)
                with self.assertRaises(RadarError):
                    toggle_window_maximized(runner=runner)
                self.assertEqual(1, len(runner.commands))

    def test_invalid_client_data_fails_before_dispatch(self) -> None:
        for key, value in (("address", "0x0"), ("address", "0x1;bad"), ("address", "0x" + "a" * 17),
                           ("fullscreen", True), ("fullscreen", 3), ("fullscreenClient", None),
                           ("fullscreenClient", "1"), ("floating", 1), ("grouped", ["0x22"])):
            with self.subTest(key=key, value=value):
                runner = Runner([client(**{key: value})])
                with self.assertRaises(RadarError):
                    toggle_window_maximized(runner=runner)
                self.assertEqual(1, len(runner.commands))

    def test_invalid_or_oversized_response_is_rejected(self) -> None:
        for value in ("{", "[null]", "{}", "x" * (MAX_RESPONSE_BYTES + 1)):
            with self.subTest(value=value[:15]):
                with self.assertRaises(RadarError):
                    window_state(runner=Runner(value))

    def test_dispatch_rejection_and_zero_exit_error_do_not_retry_mutation(self) -> None:
        for reply in ("", "error: stale identity", "warning: action failed",
                      "eval is only supported with the lua config manager",
                      subprocess.CompletedProcess([], 7, "error: changed", "")):
            with self.subTest(reply=reply):
                runner = Runner([client()], reply)
                with self.assertRaises(RadarError):
                    toggle_window_maximized(runner=runner)
                self.assertEqual(2, len(runner.commands))

    def test_delayed_confirmation_reads_again_without_second_dispatch(self) -> None:
        runner = Runner([client()], "ok", [client()], [client(fullscreen=1, fullscreenClient=1)])
        sleeps: list[float] = []
        result = toggle_window_maximized(runner=runner, sleeper=sleeps.append)
        self.assertEqual("maximized", result["outcome"])
        self.assertEqual([0.08], sleeps)
        self.assertEqual(1, sum(command[1] == "eval" for command in runner.commands))

    def test_unconfirmed_state_is_bounded_and_never_automatically_reversed(self) -> None:
        runner = Runner([client()], "ok", *([[client()]] * CONFIRM_ATTEMPTS))
        sleeps: list[float] = []
        with self.assertRaisesRegex(RadarError, "not confirmed"):
            toggle_window_maximized(runner=runner, sleeper=sleeps.append)
        self.assertEqual(CONFIRM_ATTEMPTS - 1, len(sleeps))
        self.assertEqual(CONFIRM_ATTEMPTS + 2, len(runner.commands))

    def test_disappeared_replaced_ambiguous_and_concurrently_changed_window_fail(self) -> None:
        for after in ([], [client(address="0x999")], [client(), client(address="0x999")],
                      [client(floating=False)], [client(fullscreen=2, fullscreenClient=2)]):
            with self.subTest(after=after):
                runner = Runner([client()], "ok", after)
                with self.assertRaises(RadarError):
                    toggle_window_maximized(runner=runner)
                self.assertEqual(3, len(runner.commands))

    def test_timeout_after_dispatch_is_not_retried(self) -> None:
        runner = Runner([client()], subprocess.TimeoutExpired(["hyprctl", "eval"], 1.0))
        with self.assertRaises(subprocess.TimeoutExpired):
            toggle_window_maximized(runner=runner)
        self.assertEqual(2, len(runner.commands))

    def test_cli_commands_return_structured_results_and_errors(self) -> None:
        for command, name in (("window-state", "window_state"), ("toggle-window-maximized", "toggle_window_maximized")):
            with self.subTest(command=command), patch("radar.cli.require_unprivileged"):
                output = io.StringIO()
                with patch("radar.cli." + name, return_value={"status": "ok", "maximized": True}) as action:
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(0, client_main([command]))
                    action.assert_called_once_with()
                    self.assertTrue(json.loads(output.getvalue())["maximized"])
                with patch("radar.cli." + name, side_effect=RadarError("not mapped")):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(2, client_main([command]))
                    self.assertEqual("failed", json.loads(output.getvalue())["status"])


if __name__ == "__main__":
    unittest.main()
