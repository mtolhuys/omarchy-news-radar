from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from radar.constants import CLIENT_SECTIONS
from radar.filters import SECTION_EVENT_TYPES
from radar.sections import SECTION_SOURCE_SUMMARIES
from scripts.validate_repo import property_signal_collisions

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
        icon = (ROOT / manifest["icon"]).read_text(encoding="utf-8")
        self.assertIn("#9ece6a", icon)
        self.assertIn("#ffad24", icon)
        self.assertIn('translate(64 64) scale(.075) translate(-600 -600)', icon)
        self.assertIn('circle cx="64" cy="64" r="19"', icon)
        brand_logo = (ROOT / "assets/omarchy-logo.svg").read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 1200 1200"', brand_logo)
        self.assertIn("#9ece6a", brand_logo)
        self.assertIn("m1200 1200h-480v-80h400v-1040", brand_logo)
        self.assertTrue((ROOT / "assets/readme-banner.svg").is_file())
        marketplace_preview = (ROOT / "preview.png").read_bytes()
        self.assertEqual(b"\x89PNG\r\n\x1a\n", marketplace_preview[:8])
        self.assertEqual(
            (1200, 675),
            (
                int.from_bytes(marketplace_preview[16:20], "big"),
                int.from_bytes(marketplace_preview[20:24], "big"),
            ),
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("(assets/readme-banner.svg)", readme)
        self.assertIn("(preview.png)", readme)
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
        self.assertIn('path: root.cacheBase + "/omarchy-news-radar/feed.json"', widget)
        self.assertIn("readonly property int refreshMinimumAgeSeconds: 5 * 60", widget)
        self.assertIn("function scheduleRefresh(result)", widget)
        self.assertIn("readonly property int initialRefreshDelayMs: 1800", widget)
        self.assertIn("readonly property int refreshFloorSeconds: 5", widget)
        self.assertIn("if (!refreshProc.running)", widget)
        self.assertNotIn("refreshTimer.interval = 1800", widget)
        self.assertIn("nextCheckInSeconds", widget)
        self.assertIn('Qt.resolvedUrl("../")', widget)
        self.assertIn('decodeURIComponent(url.substring(7))', widget)
        self.assertIn('root.pluginDir + "/bin/news-radar-client"', widget)
        self.assertIn('root.pluginDir + "/bin/news-radar-shortcut"', widget)
        self.assertNotIn("bar.barWidgetRegistry", widget)
        self.assertIn('shortcutMigrationProc.command = [shortcutHelperPath, "migrate-owned-legacy"]', widget)
        self.assertIn("property bool componentReady: false", widget)
        self.assertIn("property bool shortcutMigrationAttempted: false", widget)
        self.assertIn("property bool indicatorUpdatePending: false", widget)
        self.assertIn('runHelper(installedProc, ["installed"])', widget)
        self.assertIn('"indicator", "--installed-json", JSON.stringify(pluginIds)', widget)
        self.assertIn("onExited: function() { root.startIndicatorUpdate() }", widget)
        self.assertNotIn("installedPluginsReady", widget)

    def test_components_do_not_redeclare_property_change_signals(self) -> None:
        # qmllint accepts this collision, but QQmlComponent refuses to load it.
        self.assertEqual({"searchChanged"}, property_signal_collisions(
            "Item { property alias search: field; signal searchChanged(); TextInput { id: field } }"))
        self.assertEqual(set(), property_signal_collisions(
            "Item { property alias search: field; signal queryEdited(); TextInput { id: field } }"))
        for path in (ROOT / "src").rglob("*.qml"):
            self.assertFalse(property_signal_collisions(path.read_text(encoding="utf-8")), path.name)

    def test_panel_uses_plain_text_and_structural_process_arguments(self) -> None:
        sources = {path.relative_to(ROOT / "src").as_posix(): path.read_text(encoding="utf-8")
                   for path in (ROOT / "src").rglob("*.qml")}
        qml = "\n".join(sources.values())
        panel = sources["Panel.qml"]
        body = sources["components/ArticleBody.qml"]
        actions = sources["controllers/ReaderActions.qml"]
        session = sources["controllers/FeedSession.qml"]
        viewport = sources["controllers/StoryViewport.qml"]
        rail = sources["components/SectionRail.qml"]
        for required in ("function open(payloadJson)", "function close()", "function runtimeIdentity()"):
            self.assertIn(required, panel)
        # The only rich-text surface renders locally escaped article segments.
        self.assertEqual(1, qml.count("Text.RichText"))
        for required in ("textFormat: root.articleMode ? Text.RichText : Text.PlainText",
                         "RadarModel.articleBodyHtml", "linkColor: Color.accent", "onLinkActivated"):
            self.assertIn(required, body)
        self.assertIn("RadarModel.acceptedHttpsUrl", actions)
        for forbidden in ("Qt.openUrlExternally", "shell -c", "bash -c", "Color.muted", "mark-seen"):
            self.assertNotIn(forbidden, qml)
        for source in (actions, session, sources["controllers/PluginMaintenance.qml"],
                       sources["controllers/WindowLifecycle.qml"]):
            self.assertIn("command = [helperPath].concat(argumentsList)", source)
        self.assertIn('"--retained-read-ids-json"', session)
        self.assertIn('"--installed-facts-json"', session)
        self.assertIn('"--installed-facts-status"', session)
        self.assertIn('result.status === "stale-event"', actions)
        self.assertIn("blockingMutes = result.blockingMutes || []", session)
        self.assertIn('if (feedSession.blockingMutes.length > 0) return "Review mutes"', panel)
        self.assertIn("root.recoverEmptyView(); event.accepted = true; return", panel)
        self.assertIn('"set-read", "--event-id"', actions)
        self.assertIn('"mark-section-read"', actions)
        self.assertIn('"--section-visibility-json"', actions)
        # Display preferences are re-read at activation, rather than stale toggles.
        self.assertIn('startProcess(preferencesProc, ["read"])', actions)
        self.assertIn("session.localStateReady || stateMutationPending || preferencesProc.running", actions)
        self.assertIn("onPreferencesReady:", panel)
        # Model payloads and the live viewport anchor remain stable across read writes.
        for invariant in ("preservedSelectedId", "preservedAnchorId", "preservedAnchorTop",
                          "pendingViewportRevision !== storyViewportRevision", "pendingViewportAttempts = 24",
                          "JSON.stringify(previousStories[retainedIndex])",
                          "renderedStoryModel.setProperty", "forcedTopAnchorIndex",
                          "loadMoreButton.forceActiveFocus(Qt.TabFocusReason)"):
            self.assertIn(invariant, viewport)
        for required in ("Flickable", "function revealSelected()", "id: keysLegend", "quietTextColor"):
            self.assertIn(required, rail)
        self.assertIn("Qt.callLater(sectionRail.revealSelected)", panel)
        # Normal window behavior and explicit maintenance stay separate from reader state.
        self.assertIn("FloatingWindow", panel)
        self.assertNotIn("PanelWindow", panel)
        self.assertIn("startSystemResize", panel)
        self.assertIn("minimumSize:", panel)
        self.assertIn('"update-status"', sources["controllers/PluginMaintenance.qml"])
        self.assertIn('"update-apply"', sources["controllers/PluginMaintenance.qml"])
        self.assertIn('result.classification === "owned-legacy"', sources["controllers/PluginMaintenance.qml"])
        self.assertIn('text: "NEWS RADAR"', sources["components/RadarMasthead.qml"])
        self.assertIn("TUNE YOUR RADAR", sources["components/PreferencesDialog.qml"])
        self.assertIn("Open Radar settings (T)", sources["components/RadarMasthead.qml"])
        self.assertIn('{ keys: "t", action: "tune" }', sources["components/SectionRail.qml"])
        self.assertIn('{ keys: ",", action: "section settings" }', sources["components/SectionRail.qml"])
        self.assertEqual(2, sources["components/ReaderToolbar.qml"].count("Open settings for this section (,)"))
        for dialog in (sources["components/PreferencesDialog.qml"], sources["components/SectionSettings.qml"]):
            self.assertIn("function moveSpatial(horizontal, vertical)", dialog)
            self.assertIn("function focusEdge(last)", dialog)
            self.assertIn("Qt.Key_Home", dialog)
            self.assertIn("Qt.Key_End", dialog)
        self.assertIn("SOURCES · FIXED FOR THIS SECTION", sources["components/SectionSettings.qml"])
        self.assertIn("preventStealing: true", sources["components/RadarButton.qml"])
        self.assertIn("managesTab", sources["components/RadarButton.qml"])

    def test_panel_reads_only_the_first_story_presented_by_a_fresh_open(self) -> None:
        panel = (ROOT / "src/Panel.qml").read_text(encoding="utf-8")
        actions = (ROOT / "src/controllers/ReaderActions.qml").read_text(encoding="utf-8")
        lifecycle = (ROOT / "src/controllers/WindowLifecycle.qml").read_text(encoding="utf-8")
        opened = panel[panel.index("function open(payloadJson)"):panel.index("function stopOwnedProcesses()")]
        repeated = opened[opened.index("if (opened)"):opened.index("opened = true")]
        self.assertIn("windowController.begin()", repeated)
        self.assertNotIn("forceActiveFocus", repeated)
        self.assertNotIn("readerActions.begin()", repeated)
        self.assertIn("readerActions.begin()", opened)
        self.assertNotIn("panelWindow.visible = true", opened)
        begin = actions[actions.index("function begin()"):actions.index("function stop()")]
        self.assertIn("panelOpenGeneration++", begin)
        self.assertIn("initialStoryReadPending = true", begin)
        self.assertIn("initialStoryReadTimer.stop()", begin)
        stop = actions[actions.index("function stop()"):actions.index("  Timer {")]
        self.assertIn("panelOpenGeneration++", stop)
        self.assertIn("cancelInitialStoryRead()", stop)
        schedule = actions[actions.index("function scheduleInitialStoryRead()"):actions.index("function cancelInitialStoryRead()")]
        for guard in ("!initialStoryReadPending", "!opened", "!windowVisible", "!selectedStory",
                      "session.onboardingVisible", "overviewVisible", "detailItem", "session.briefingRunning"):
            self.assertIn(guard, schedule)
        self.assertIn("initialStoryReadGeneration = panelOpenGeneration", schedule)
        self.assertIn("initialStoryReadEventId = eventId", schedule)
        self.assertIn("initialStoryReadTimer.restart()", schedule)
        commit = actions[actions.index("function commitInitialStoryRead()"):actions.index("function queueStoryRead(")]
        for guard in ("generation !== panelOpenGeneration", "session.projecting || session.pendingProjection",
                      'String(selectedStory.id || "") !== eventId', "preferencesOpen", "sectionSettingsOpen",
                      "session.onboardingVisible", "overviewVisible", "detailItem"):
            self.assertIn(guard, commit)
        self.assertLess(commit.rindex("initialStoryReadPending = false"), commit.index("queueStoryRead(selectedStory, true)"))
        self.assertIn("readonly property int initialStoryReadDelayMs: 650", actions)
        self.assertIn("onSelected: function(markRead)", panel)
        self.assertIn("if (markRead) readerActions.cancelInitialStoryRead()", panel)
        self.assertIn("if (markRead) readerActions.queueStoryRead(storyViewportController.selectedStory, true)", panel)
        self.assertIn("!preparationReady || (!contentReady && !recoveryReady)", lifecycle)
        self.assertIn("interval: 2500", lifecycle)
        self.assertIn('["prepare-window"', lifecycle)
        self.assertIn('["finish-window-opening", "--token", token]', lifecycle)
        self.assertIn('["remember-window"]', lifecycle)
        self.assertIn('event.name === "activewindow"', lifecycle)
        self.assertIn("property bool focusConfirmed: false", lifecycle)
        self.assertIn('root.trace("yield-focus"', lifecycle)
        self.assertIn("root.requestClose()", lifecycle)

    def test_empty_readers_hide_inspection_and_offer_one_recovery_action(self) -> None:
        panel = (ROOT / "src/Panel.qml").read_text(encoding="utf-8")
        reader = (ROOT / "src/components/ReaderList.qml").read_text(encoding="utf-8")
        actions = (ROOT / "src/controllers/ReaderActions.qml").read_text(encoding="utf-8")
        self.assertEqual(2, panel.count("visible: !keySurface.narrow && !root.overviewVisible && !!storyViewportController.selectedStory"))
        self.assertIn("visible: root.narrow && !!root.viewport.selectedStory",
                      (ROOT / "src/components/ReaderToolbar.qml").read_text(encoding="utf-8"))
        self.assertIn("root.recoveryLabel", reader)
        for label in ("Clear search", "Reset section filters", "Explore Front Page", "Your saved stories will appear here"):
            self.assertIn(label, panel)
        for function in ("toggleSelectedRead", "openSelected", "openMarketplacePage", "toggleSaved"):
            body = actions[actions.index("function " + function + "()") :]
            body = body[:body.index("\n  }")]
            self.assertIn("if (!selectedStory", body)

    def test_compact_selection_uses_the_same_untruncated_body_and_link_path_as_inspector(self) -> None:
        reader = (ROOT / "src/components/ReaderList.qml").read_text(encoding="utf-8")
        row = (ROOT / "src/components/StoryRow.qml").read_text(encoding="utf-8")
        inspector = (ROOT / "src/components/StoryInspector.qml").read_text(encoding="utf-8")
        body = (ROOT / "src/components/ArticleBody.qml").read_text(encoding="utf-8")
        self.assertIn("expandedBody: root.narrow && selected", reader)
        self.assertIn("root.actions.openArticleLink(url)", reader)
        self.assertIn("ArticleBody {", row)
        self.assertIn("ArticleBody {", inspector)
        self.assertIn("visible: !root.quiet && !root.expandedBody", row)
        self.assertIn("root.expandedBody ? Text.ElideNone", row)
        self.assertNotIn("listSummary", body)
        self.assertNotIn("maximumLineCount", body)
        self.assertNotIn("elide:", body)
        self.assertIn("story.summarySegments", body)
        self.assertIn('String(story.summary || "")', body)
        self.assertIn("root.articleLinkRequested(url)", inspector)

    def test_every_section_boundary_uses_the_same_canonical_five_ids(self) -> None:
        expected = list(CLIENT_SECTIONS)
        qml = (ROOT / "src/Panel.qml").read_text(encoding="utf-8")
        navigation = (ROOT / "src/controllers/SectionNavigation.qml").read_text(encoding="utf-8")
        qml_navigation = re.findall(r'Object\.assign\(\{ id: "([a-z-]+)" \}', navigation)

        self.assertEqual(expected, qml_navigation)
        self.assertEqual(set(expected), set(SECTION_SOURCE_SUMMARIES))
        self.assertEqual(set(expected), set(SECTION_EVENT_TYPES))

        story = (ROOT / "src/components/StoryRow.qml").read_text(encoding="utf-8")
        self.assertIn("secondaryTextColor: selected", story)
        self.assertIn("Color.popups.text", story)
        self.assertIn("textFormat: Text.PlainText", story)
        self.assertIn("property bool quiet: false", story)
        self.assertIn("RadarModel.humanDate", story)
        self.assertIn("visible: !root.quiet", story)
        self.assertIn("visible: root.quiet", story)
        self.assertIn("MetricStrip", story)
        self.assertIn("● UNREAD", story)
        self.assertIn("✓ READ", story)
        self.assertIn("story.isUnread", story)
        self.assertIn("readonly property string cardSummary", story)
        self.assertIn("readonly property string cardDate", story)
        self.assertIn("story.listSummary || story.summary", story)
        self.assertIn("text: root.cardSummary", story)
        self.assertNotIn("Color.muted", story)
        model_js = (ROOT / "src/Model.js").read_text(encoding="utf-8")
        self.assertIn("function humanDate", model_js)
        self.assertIn("function isReaderArticle", model_js)
        self.assertIn("function usesQuietCard", model_js)
        self.assertIn("function articleSegments", model_js)
        self.assertIn("function articleBodyHtml", model_js)
        self.assertIn("<br/><br/>", model_js)
        self.assertIn("function acceptedHttpsUrl", model_js)
        self.assertIn('type === "omarchy-news"', model_js)
        self.assertIn('id === "core"', model_js)
        self.assertIn('id === "front-page"', model_js)
        self.assertNotIn("signal hovered", story)
        self.assertNotIn("onHovered:", qml)
        self.assertIn("item[\"listSummary\"] = list_summary", (ROOT / "radar/client_presentation.py").read_text(encoding="utf-8"))
        self.assertIn("ArticleBody {", (ROOT / "src/components/StoryInspector.qml").read_text(encoding="utf-8"))
        self.assertIn('item["summarySegments"] = article_segments', (ROOT / "radar/client_presentation.py").read_text(encoding="utf-8"))

        section = (ROOT / "src/components/SectionButton.qml").read_text(encoding="utf-8")
        self.assertIn("property string icon", section)
        self.assertIn("property string tone", section)
        self.assertIn("Color.accent", section)
        self.assertIn("Color.foreground", section)
        self.assertIn("Style.font.iconLarge", section)
        self.assertIn("id: iconText", section)
        self.assertIn("property int unreadCount", section)
        self.assertIn('text: String(root.unreadCount)', section)
        self.assertIn('root.unreadCount + " unread"', section)
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
            "Qt.Key_Left",
            "Qt.Key_Right",
            "Qt.Key_Return",
            "Qt.Key_Home",
            "Qt.Key_End",
            "Qt.Key_Tab",
            "Qt.Key_Backtab",
            "Keys.onEscapePressed",
            'event.text === "/"',
            'toLowerCase() === "s"',
            'toLowerCase() === "u"',
            'toLowerCase() === "f"',
            'toLowerCase() === "a"',
            '=== "?"',
            'toLowerCase() === "r"',
            'toLowerCase() === "t"',
            'event.text || "") === ","',
        ):
            self.assertIn(key, qml)
        discovery = (ROOT / "src/components/DiscoveryView.qml").read_text(encoding="utf-8")
        detail = (ROOT / "src/components/InsightDetail.qml").read_text(encoding="utf-8")
        notice = (ROOT / "src/components/BriefingNotice.qml").read_text(encoding="utf-8")
        self.assertIn("function moveSelectionHorizontal(direction)", discovery)
        self.assertIn("property bool footerSelected", discovery)
        self.assertIn("browseButton.forceActiveFocus()", discovery)
        self.assertIn("function hasVisibleGroupBefore(groupIndex)", discovery)
        self.assertIn("Layout.fillHeight: true", discovery)
        self.assertIn("Layout.columnSpan: cardGrid.columns === 2", discovery)
        self.assertIn("Style.space(920)", detail)
        self.assertIn('text: "Included projects"', detail)
        self.assertIn("id: projectGrid", detail)
        self.assertIn("id: relevanceGrid", detail)
        self.assertIn("Layout.columnSpan: relevanceGrid.columns === 2", detail)
        self.assertIn("function moveSpatial(horizontal, vertical)", detail)
        self.assertIn("Arrow keys navigate · Enter activates · PgUp/PgDn scroll · Esc goes back", detail)
        for key in ("Qt.Key_Left", "Qt.Key_Right", "Qt.Key_Down", "Qt.Key_Up", "Qt.Key_Home", "Qt.Key_End"):
            self.assertIn(key, detail)
        self.assertEqual(1, notice.count("columns: 1"))
        self.assertIn("readonly property bool canPrepare:", notice)
        self.assertIn('"Check for new stories"', notice)
        self.assertIn('"Load new briefing"', notice)
        self.assertIn('"This finished edition stays here until you replace it. "', notice)
        self.assertIn("root.canPrepare ? root.newRequested() : root.refreshRequested()", notice)
        self.assertIn("A new briefing will be available when unread stories arrive.", notice)
        session = (ROOT / "src/controllers/FeedSession.qml").read_text(encoding="utf-8")
        for state in ("First use", "Cached", "Checking", "Updated", "No newer edition", "Publisher stale", "Offline", "Source partial", "Invalid feed", "No cache and failed"):
            self.assertIn(state, session)


if __name__ == "__main__":
    unittest.main()
