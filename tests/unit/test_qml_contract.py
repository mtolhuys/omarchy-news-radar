from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class QmlContractTests(unittest.TestCase):
    def test_manifest_is_panel_only_and_entry_exists(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(["panel"], manifest["kinds"])
        self.assertNotIn("keepLoaded", manifest)
        self.assertNotIn("barWidget", manifest)
        self.assertTrue((ROOT / manifest["entryPoints"]["panel"]).is_file())

    def test_panel_uses_plain_text_and_structural_process_arguments(self) -> None:
        qml = (ROOT / "src/Panel.qml").read_text(encoding="utf-8")
        self.assertIn("function open(payloadJson)", qml)
        self.assertIn("function close()", qml)
        self.assertIn("function runtimeIdentity()", qml)
        self.assertIn("command = [helperPath].concat(argumentsList)", qml)
        self.assertIn("textFormat: Text.PlainText", qml)
        self.assertNotIn("Text.RichText", qml)
        self.assertNotIn("Qt.openUrlExternally", qml)
        self.assertNotIn("bar-widget", qml)
        self.assertNotIn("shell -c", qml)

    def test_complete_keyboard_and_visible_state_labels_exist(self) -> None:
        qml = (ROOT / "src/Panel.qml").read_text(encoding="utf-8")
        for key in (
            "Qt.Key_Escape",
            "Qt.Key_Down",
            "Qt.Key_Up",
            "Qt.Key_Return",
            "Qt.Key_Home",
            "Qt.Key_End",
            'event.text === "/"',
            'toLowerCase() === "s"',
            'toLowerCase() === "r"',
        ):
            self.assertIn(key, qml)
        for state in ("First use", "Cached", "Refreshing", "Current", "Offline", "Source partial", "Invalid feed", "No cache and failed"):
            self.assertIn(state, qml)


if __name__ == "__main__":
    unittest.main()
