from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class QmlContractTests(unittest.TestCase):
    def test_manifest_pairs_panel_with_optional_collapsible_bar_widget(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(["panel", "bar-widget"], manifest["kinds"])
        self.assertNotIn("keepLoaded", manifest)
        self.assertTrue((ROOT / manifest["entryPoints"]["panel"]).is_file())
        self.assertTrue((ROOT / manifest["entryPoints"]["barWidget"]).is_file())
        self.assertEqual("right", manifest["barWidget"]["defaultSection"])
        self.assertEqual("assets/io.github.mtolhuys.news-radar.svg", manifest["icon"])
        self.assertTrue((ROOT / manifest["icon"]).is_file())
        self.assertEqual(
            {"appId": "org.quickshell", "title": "📰 Omarchy News Radar"},
            manifest["windowIdentity"],
        )

        widget = (ROOT / "src/BarWidget.qml").read_text(encoding="utf-8")
        self.assertIn("visible: barVisible", widget)
        self.assertIn("implicitWidth: button.implicitWidth", widget)
        self.assertIn('"--bar-visible", "false"', widget)
        self.assertIn("Qt.RightButton", widget)
        self.assertIn("refresh-if-due", widget)

    def test_panel_uses_plain_text_and_structural_process_arguments(self) -> None:
        qml = (ROOT / "src/Panel.qml").read_text(encoding="utf-8")
        self.assertIn("function open(payloadJson)", qml)
        self.assertIn("function close()", qml)
        self.assertIn("function runtimeIdentity()", qml)
        self.assertIn("command = [helperPath].concat(argumentsList)", qml)
        self.assertIn("textFormat: Text.PlainText", qml)
        self.assertNotIn("Text.RichText", qml)
        self.assertNotIn("Qt.openUrlExternally", qml)
        self.assertNotIn("shell -c", qml)
        self.assertIn("TUNE YOUR RADAR", qml)
        self.assertIn("Story images", qml)
        self.assertIn("Top-bar newspaper", qml)
        self.assertIn("function tuneNewspaperGeometry()", qml)
        self.assertIn("No stories in this edition include a validated image.", qml)
        self.assertIn("Local live edition", qml)
        self.assertIn('Qt.resolvedUrl("../assets/io.github.mtolhuys.news-radar.svg")', qml)
        self.assertIn("FloatingWindow", qml)
        self.assertNotIn("PanelWindow", qml)
        self.assertIn("minimumSize:", qml)
        self.assertIn("screen.width - Style.gapsOut * 2", qml)
        self.assertIn("screen.height - Style.gapsOut * 2", qml)
        self.assertGreaterEqual(qml.count("columns: keySurface.narrow ? 1 : 2"), 2)
        self.assertIn("panelWindow.maximized", qml)
        self.assertIn("startSystemResize", qml)
        self.assertIn("Load more", qml)
        self.assertIn("BUILT-IN SECTION RULE", qml)
        self.assertIn("METRICS", qml)
        self.assertIn("MetricStrip", qml)
        self.assertIn("PanelActionButton", qml)
        self.assertNotIn('iconText: "−"', qml)
        self.assertNotIn("panelWindow.minimized", qml)
        self.assertIn('iconText: panelWindow.maximized ? "❐" : "□"', qml)
        self.assertIn('iconText: "×"', qml)
        self.assertIn('label: "Plugin page"', qml)
        self.assertIn("function pluginPageGeometry()", qml)
        self.assertNotIn("metricSources", qml)
        self.assertIn("SECTION SETTINGS", qml)
        self.assertIn('label: "⚙ Settings"', qml)
        self.assertNotIn('label: "⚙ Filters"', qml)
        self.assertIn("function settingsGeometry()", qml)
        self.assertIn("sectionSettingsOpen", qml)
        self.assertIn("SOURCES · FIXED FOR THIS SECTION", qml)
        self.assertIn("set-section-profile", qml)
        self.assertIn("sectionNameField", qml)
        self.assertIn("sectionIconSparkButton", qml)
        self.assertIn("sectionToneAccentButton", qml)
        self.assertIn("Reset appearance", qml)
        self.assertIn('startProcess(windowProc, ["ensure-window-floating"])', qml)
        self.assertIn("function emptyStateMessage()", qml)
        self.assertIn("No reviewed community stories are in this edition yet.", qml)
        self.assertIn('readonly property string compositorWindowTitle: "📰 Omarchy News Radar"', qml)

        story = (ROOT / "src/components/StoryRow.qml").read_text(encoding="utf-8")
        self.assertIn("secondaryTextColor: selected", story)
        self.assertIn("Color.popups.text", story)
        self.assertIn("textFormat: Text.PlainText", story)
        self.assertIn("MetricStrip", story)

        section = (ROOT / "src/components/SectionButton.qml").read_text(encoding="utf-8")
        self.assertIn("property string icon", section)
        self.assertIn("property string tone", section)
        self.assertIn("Color.accent", section)
        self.assertIn("Color.foreground", section)
        self.assertIn("Style.font.iconLarge", section)
        self.assertIn("id: iconText", section)

        icon_choice = (ROOT / "src/components/SectionIconChoice.qml").read_text(encoding="utf-8")
        self.assertIn("Style.font.iconLarge", icon_choice)
        self.assertIn("Accessible.RadioButton", icon_choice)

        metrics = (ROOT / "src/components/MetricStrip.qml").read_text(encoding="utf-8")
        for metric_id in (
            "marketplace-views",
            "marketplace-hearts",
            "marketplace-copies",
            "repository-stars",
            "release-asset-downloads",
        ):
            self.assertIn(metric_id, metrics)
        self.assertIn("Color.accent", metrics)
        self.assertIn("Accessible.name", metrics)

    def test_complete_keyboard_and_visible_state_labels_exist(self) -> None:
        qml = (ROOT / "src/Panel.qml").read_text(encoding="utf-8")
        for key in (
            "Qt.Key_Escape",
            "Qt.Key_Down",
            "Qt.Key_Up",
            "Qt.Key_Return",
            "Qt.Key_Home",
            "Qt.Key_End",
            "Qt.Key_Tab",
            "Qt.Key_Backtab",
            "Keys.onEscapePressed",
            'event.text === "/"',
            'toLowerCase() === "s"',
            'toLowerCase() === "r"',
        ):
            self.assertIn(key, qml)
        for state in ("First use", "Cached", "Refreshing", "Current", "Offline", "Source partial", "Invalid feed", "No cache and failed"):
            self.assertIn(state, qml)


if __name__ == "__main__":
    unittest.main()
