from __future__ import annotations

import json
import subprocess
import unittest

from radar.errors import RadarError
from radar.window import ensure_window_floating


class FakeRunner:
    def __init__(self, responses: list[subprocess.CompletedProcess[str]]) -> None:
        self.responses = responses
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        return self.responses.pop(0)


def completed(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, stdout, "")


def client(*, title: str = "📰 Omarchy News Radar", floating: bool = False, address: str = "0x1") -> dict[str, object]:
    return {
        "title": title,
        "initialTitle": title,
        "class": "org.quickshell",
        "initialClass": "org.quickshell",
        "mapped": True,
        "floating": floating,
        "address": address,
    }


class WindowIntegrationTests(unittest.TestCase):
    def test_exact_tiled_client_is_floated_by_validated_address(self) -> None:
        runner = FakeRunner(
            [
                completed(json.dumps([client(title="Terminal")])),
                completed(json.dumps([client(address="0xA02f")])),
                completed("ok\n"),
            ]
        )
        delays: list[float] = []
        result = ensure_window_floating(runner=runner, sleeper=delays.append)
        self.assertEqual("float-requested", result["outcome"])
        self.assertEqual([0.12], delays)
        self.assertEqual(
            [
                "hyprctl",
                "dispatch",
                'hl.dsp.window.float({ window = "address:0xA02f", action = "toggle" })',
            ],
            runner.commands[-1],
        )

    def test_already_floating_and_unrelated_clients_are_not_toggled(self) -> None:
        floating = FakeRunner(
            [completed(json.dumps([client(floating=True)]))]
        )
        self.assertEqual("already-floating", ensure_window_floating(runner=floating, sleeper=lambda _: None)["outcome"])
        self.assertEqual(1, len(floating.commands))

        unrelated = FakeRunner(
            [completed(json.dumps([client(title="Terminal")])) for _ in range(10)]
        )
        self.assertEqual("radar-not-mapped", ensure_window_floating(runner=unrelated, sleeper=lambda _: None)["outcome"])
        self.assertEqual(10, len(unrelated.commands))

    def test_invalid_address_is_refused(self) -> None:
        runner = FakeRunner(
            [completed(json.dumps([client(address="$(bad)")]))]
        )
        with self.assertRaisesRegex(RadarError, "invalid address"):
            ensure_window_floating(runner=runner, sleeper=lambda _: None)
        self.assertEqual(1, len(runner.commands))

    def test_ambiguous_identity_is_refused(self) -> None:
        runner = FakeRunner([completed(json.dumps([client(address="0x1"), client(address="0x2")]))])
        with self.assertRaisesRegex(RadarError, "ambiguous"):
            ensure_window_floating(runner=runner, sleeper=lambda _: None)
        self.assertEqual(1, len(runner.commands))

    def test_legacy_dispatch_is_a_bounded_compatibility_fallback(self) -> None:
        runner = FakeRunner(
            [
                completed(json.dumps([client(address="0x55")])),
                subprocess.CompletedProcess([], 1, "", "unsupported"),
                completed("ok\n"),
            ]
        )
        result = ensure_window_floating(runner=runner, sleeper=lambda _: None)
        self.assertEqual("float-requested", result["outcome"])
        self.assertEqual(
            ["hyprctl", "dispatch", "togglefloating", "address:0x55"],
            runner.commands[-1],
        )


if __name__ == "__main__":
    unittest.main()
