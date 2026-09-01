from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from radar.constants import CLIENT_SECTIONS
from radar.filters import SECTION_EVENT_TYPES
from radar.sections import SECTION_SOURCE_SUMMARIES

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
        self.assertIn("property bool localStateReady: false", qml)
        self.assertIn("if (!localStateReady || stateMutationPending || preferencesProc.running) return", qml)
        self.assertIn('startProcess(preferencesProc, ["read"])', qml)
        self.assertIn("enabled: root.localStateReady && !root.stateMutationPending && !preferencesProc.running", qml)
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
        self.assertNotIn("BUILT-IN SECTION RULE", qml)
        self.assertIn("METRICS", qml)
        self.assertIn("MetricStrip", qml)
        self.assertIn("PanelActionButton", qml)
        self.assertNotIn('iconText: "−"', qml)
        self.assertNotIn("panelWindow.minimized", qml)
        self.assertIn('iconText: panelWindow.maximized ? "❐" : "□"', qml)
        self.assertIn('iconText: "×"', qml)
        self.assertIn('label: "Plugin page"', qml)
        self.assertIn("function pluginPageGeometry()", qml)
        self.assertIn("function readStateGeometry()", qml)
        self.assertIn("function restoreStoryViewport()", qml)
        self.assertIn("storyList.positionViewAtEnd()", qml)
        self.assertIn("function storyViewportState()", qml)
        self.assertIn("function storyNeedsTopAnchor(index)", qml)
        self.assertIn("function animateStoryPosition(index, alignAtTop, initialContentY)", qml)
        self.assertIn("top + row.height >= storyList.height - 0.5", qml)
        self.assertIn("if (anchorAtTop) root.storyViewportAnchorIndex = nextIndex", qml)
        self.assertIn("storyList.positionViewAtIndex(anchorIndex, ListView.Beginning)", qml)
        self.assertIn("Math.min(row.y, maximumContentY)", qml)
        self.assertNotIn("currentIndex: root.selectedIndex", qml)
        self.assertIn('property: "contentY"', qml)
        self.assertIn("duration: 140", qml)
        self.assertIn("function loadMore() {\n    if (!hasMoreStories) return", qml)
        self.assertIn("loadMoreButton.forceActiveFocus(Qt.TabFocusReason)", qml)
        self.assertIn("loadMoreFocused: loadMoreButton.activeFocus", qml)
        self.assertIn("loadMoreLabel: loadMoreButton.label", qml)
        self.assertIn('"Press Enter to load "', qml)
        self.assertIn('tooltipText: "Down to focus · Enter to load the next page"', qml)
        self.assertIn('iconText: root.refreshing ? "↻" : ""', qml)
        self.assertIn("iconSpinning: root.refreshing", qml)
        self.assertIn('label: root.refreshing ? "Checking…" : "Check for updates"', qml)
        self.assertIn('tooltipText: "Check the published edition (R)"', qml)
        self.assertIn('"set-read", "--event-id"', qml)
        self.assertIn('"mark-section-read"', qml)
        self.assertIn('result.status === "stale-event"', qml)
        self.assertIn('label: root.bulkReadInFlight ? "Marking read…" : "Mark all as read"', qml)
        self.assertIn("function markAllReadGeometry()", qml)
        self.assertIn("matching this section's Settings", qml)
        self.assertIn('label: root.selectedStory && root.selectedStory.isUnread ? "Mark read" : "Mark unread"', qml)
        self.assertNotIn("mark-seen", qml)
        self.assertNotIn("metricSources", qml)
        self.assertIn("SECTION SETTINGS", qml)
        self.assertIn('label: "⚙ Settings"', qml)
        self.assertNotIn('label: "⚙ Filters"', qml)
        self.assertIn("function settingsGeometry()", qml)
        self.assertIn("function refreshGeometry()", qml)
        self.assertIn("sectionSettingsOpen", qml)
        self.assertIn("SOURCES · FIXED FOR THIS SECTION", qml)
        self.assertNotIn("set-section-profile", qml)
        self.assertNotIn("sectionNameField", qml)
        self.assertNotIn("sectionIconSparkButton", qml)
        self.assertNotIn("sectionToneAccentButton", qml)
        self.assertNotIn("BACKGROUND · THEME-DERIVED", qml)
        self.assertNotIn("display name", qml)
        self.assertNotIn("Reset name", qml)
        self.assertNotIn("Local-only ·", qml)
        self.assertNotIn("Apply interests", qml)
        self.assertNotIn("interestField", qml)
        self.assertNotIn("--interests-json", qml)
        self.assertIn("if (opened && panelWindow.visible) {", qml)
        self.assertIn('startProcess(windowProc, ["activate-window"])', qml)
        self.assertNotIn("panelWindow.requestActivate()", qml)
        self.assertIn("function dismiss() {", qml)
        self.assertIn('root.close()\n    if (shell && typeof shell.hide === "function") shell.hide(pluginId)', qml)
        self.assertIn("function emptyStateMessage()", qml)
        self.assertNotIn('id: "community"', qml)
        self.assertNotIn('currentSection === "community"', qml)
        self.assertIn("1–5 sections", qml)
        self.assertIn("KEYBOARD  Tab/Shift+Tab sections", qml)
        self.assertNotIn("Color.muted", qml)
        self.assertIn('readonly property string compositorWindowTitle: "📰 Omarchy News Radar"', qml)
        button = (ROOT / "src/components/RadarButton.qml").read_text(encoding="utf-8")
        self.assertIn("preventStealing: true", button)
        self.assertIn("onClicked: root.clicked()", button)
        self.assertIn("RotationAnimation on rotation", button)
        self.assertIn('property string tooltipText: ""', button)
        self.assertIn("PanelToolTip", button)

    def test_every_section_boundary_uses_the_same_canonical_five_ids(self) -> None:
        expected = list(CLIENT_SECTIONS)
        qml = (ROOT / "src/Panel.qml").read_text(encoding="utf-8")
        qml_navigation = re.findall(r'Object\.assign\(\{ id: "([a-z-]+)" \}', qml)

        self.assertEqual(expected, qml_navigation)
        self.assertEqual(set(expected), set(SECTION_SOURCE_SUMMARIES))
        self.assertEqual(set(expected), set(SECTION_EVENT_TYPES))

        story = (ROOT / "src/components/StoryRow.qml").read_text(encoding="utf-8")
        self.assertIn("secondaryTextColor: selected", story)
        self.assertIn("Color.popups.text", story)
        self.assertIn("textFormat: Text.PlainText", story)
        self.assertIn("MetricStrip", story)
        self.assertIn("● UNREAD", story)
        self.assertIn("✓ READ", story)
        self.assertIn("story.isUnread", story)
        self.assertNotIn("Color.muted", story)
        self.assertNotIn("signal hovered", story)
        self.assertNotIn("onHovered:", qml)

        section = (ROOT / "src/components/SectionButton.qml").read_text(encoding="utf-8")
        self.assertIn("property string icon", section)
        self.assertIn("property string tone", section)
        self.assertIn("Color.accent", section)
        self.assertIn("Color.foreground", section)
        self.assertIn("Style.font.iconLarge", section)
        self.assertIn("id: iconText", section)
        self.assertIn("property int unreadCount", section)
        self.assertNotIn("Color.muted", section)

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
            'toLowerCase() === "u"',
            'toLowerCase() === "r"',
        ):
            self.assertIn(key, qml)
        for state in ("First use", "Cached", "Checking", "Updated", "No newer edition", "Publisher stale", "Offline", "Source partial", "Invalid feed", "No cache and failed"):
            self.assertIn(state, qml)


if __name__ == "__main__":
    unittest.main()
