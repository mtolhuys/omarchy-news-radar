import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Ui
import "Model.js" as RadarModel
import "components"
import "controllers"

Item {
  id: root

  property string omarchyPath: Quickshell.env("OMARCHY_PATH")
  property var shell: null
  property var manifest: null
  property var pluginRegistry: null

  readonly property string runtimeBuildIdentity: "news-radar-0.5.0+identity-2"
  readonly property string helperPath: manifest && manifest.__sourceDir
    ? String(manifest.__sourceDir) + "/bin/news-radar-client" : ""
  readonly property string shortcutHelperPath: manifest && manifest.__sourceDir
    ? String(manifest.__sourceDir) + "/bin/news-radar-shortcut" : ""
  readonly property string brandLogoPath: manifest && manifest.__sourceDir
    ? String(manifest.__sourceDir) + "/assets/omarchy-logo.svg" : ""
  readonly property string cacheBase: Quickshell.env("XDG_CACHE_HOME")
    || (Quickshell.env("HOME") + "/.cache")
  readonly property string pluginId: manifest && manifest.id
    ? String(manifest.id) : "io.github.mtolhuys.news-radar"

  property bool opened: false
  property bool closingFromHost: false
  readonly property string compositorWindowTitle: "📰 Omarchy News Radar"
  // Matte-Black-tuned alphas read as ghostly on light popup surfaces (e.g. Lupine).
  // Floor secondary/quiet by popup-background luminance; keep dark near prior values.
  readonly property bool popupBgIsLight: (
    0.2126 * Color.popups.background.r
    + 0.7152 * Color.popups.background.g
    + 0.0722 * Color.popups.background.b) > 0.5
  readonly property color secondaryTextColor: Qt.rgba(
    Color.popups.text.r, Color.popups.text.g, Color.popups.text.b,
    popupBgIsLight ? 0.82 : 0.72)
  readonly property color quietTextColor: Qt.rgba(
    Color.popups.text.r, Color.popups.text.g, Color.popups.text.b,
    popupBgIsLight ? 0.64 : 0.52)
  // Dim with foreground so light themes get a real wash (not white-on-white).
  readonly property color modalScrimColor: Qt.rgba(
    Color.foreground.r, Color.foreground.g, Color.foreground.b,
    popupBgIsLight ? 0.22 : 0.45)
  property bool homeMode: true
  property bool setupMode: true
  property var detailItem: null
  property var detailParents: []
  readonly property bool homeVisible: sectionNavigation.currentSection === "front-page" && homeMode
  readonly property bool setupVisible: sectionNavigation.currentSection === "for-you" && setupMode
  readonly property bool overviewVisible: homeVisible || setupVisible
  property bool briefingControlsMode: false
  readonly property bool briefingVisible: sectionNavigation.currentSection === "front-page" && !!feedSession.cachedFeed
  property bool preferencesOpen: false
  property bool sectionSettingsOpen: false
  // Session-only; start collapsed so the rail stays quiet. Opening it is an
  // explicit reader choice and is remembered until this panel instance closes.
  property bool keysLegendOpen: false
  readonly property string windowIntegrationStatus: windowController.status

  readonly property bool inspectorYouTube: !!storyViewportController.selectedStory
    && String(storyViewportController.selectedStory.type || "") === "youtube-video"
  readonly property bool inspectorHasMetrics: !!storyViewportController.selectedStory
    && !!storyViewportController.selectedStory.metricItems
    && storyViewportController.selectedStory.metricItems.length > 0
  readonly property bool readerLayout: sectionNavigation.currentSection === "core" || sectionNavigation.currentSection === "front-page"
  readonly property bool inspectorArticleMode: RadarModel.isReaderArticle(storyViewportController.selectedStory)
  property bool inspectorFactsOpen: false
  readonly property bool anyHelperRunning: feedSession.busy || readerActions.busy || readerActions.readMutationPending
    || windowController.busy || pluginMaintenance.busy

  Connections {
    target: feedSession
    function onOnboardingVisibleChanged() {
      if (feedSession.onboardingVisible) {
        readerActions.cancelInitialStoryRead()
        Qt.callLater(function() { if (feedSession.onboardingVisible) welcomeCard.focusChoice() })
      }
    }
  }

  function storyViewportState() { return storyViewportController.storyViewportState() }

  function debugState() { return diagnostics.debugState() }
  function itemGeometry(item, visible) { return diagnostics.itemGeometry(item, visible) }
  function sectionRailGeometry() { return diagnostics.sectionRailGeometry() }
  function maximizeGeometry() { return diagnostics.maximizeGeometry() }
  function closeGeometry() { return diagnostics.closeGeometry() }
  function settingsGeometry() { return diagnostics.settingsGeometry() }
  function markAllReadGeometry() { return diagnostics.markAllReadGeometry() }
  function headerUnreadGeometry() { return diagnostics.headerUnreadGeometry() }
  function keysLegendGeometry() { return diagnostics.keysLegendGeometry() }
  function refreshGeometry() { return diagnostics.refreshGeometry() }
  function loadMoreGeometry() { return diagnostics.loadMoreGeometry() }
  function filterUnreadGeometry() { return diagnostics.filterUnreadGeometry() }
  function filterImagesGeometry() { return diagnostics.filterImagesGeometry() }
  function filterResetGeometry() { return diagnostics.filterResetGeometry() }
  function pluginPageGeometry() { return diagnostics.pluginPageGeometry() }
  function readStateGeometry() { return diagnostics.readStateGeometry() }
  function tuneGeometry() { return itemGeometry(masthead.tuneButton, masthead.tuneButton.visible) }
  function tuneNewspaperGeometry() { return diagnostics.tuneNewspaperGeometry() }
  function shortcutMigrationGeometry() { return diagnostics.shortcutMigrationGeometry() }
  function startTodayGeometry() { return diagnostics.startTodayGeometry() }
  function browseStoriesGeometry() { return diagnostics.browseStoriesGeometry() }
  function newBriefingGeometry() { return diagnostics.newBriefingGeometry() }
  function finishBriefingGeometry() { return diagnostics.finishBriefingGeometry() }
  function homeCardGeometry() { return diagnostics.homeCardGeometry() }
  function groupReadGeometry() { return diagnostics.groupReadGeometry() }
  function setupNewsGeometry() { return itemGeometry(setupNewsButton, setupNewsButton.visible) }

  function runtimeIdentity() {
    return runtimeBuildIdentity
  }

  function emptyStateMessage() {
    if (masthead.search.text)
      return "No stories match the current filter. Clear search to recover."
    if (!feedSession.cachedFeed)
      return "No cached edition is available yet. Retry when online."
    if (briefingVisible && feedSession.briefing.initialized !== true)
      return feedSession.briefingMessage || "Preparing your briefing…"
    if (briefingVisible && feedSession.briefing.complete === true)
      return "Your briefing is complete. Browse the other sections whenever you like."
    if (feedSession.filterSummary !== "No extra filters")
      return "No stories match this section's local settings. Reset its filters or choose another section."
    if (sectionNavigation.currentSection === "saved")
      return "Your saved stories will appear here. Save a story to keep it for later."
    return "There are no stories in this section of the current edition."
  }

  function emptyRecoveryLabel() {
    if (!feedSession.cachedFeed) return "Check for updates"
    if (masthead.search.text) return "Clear search"
    if (feedSession.filterSummary !== "No extra filters") return "Reset section filters"
    return "Explore Front Page"
  }
  function recoverEmptyView() {
    if (!feedSession.cachedFeed) feedSession.refreshFeed()
    else if (masthead.search.text) masthead.search.text = ""
    else if (feedSession.filterSummary !== "No extra filters") readerActions.resetFilter()
    else sectionNavigation.selectSection(sectionNavigation.sectionIndexFor("front-page"))
  }

  function sectionSummaryText() {
    var parts = []
    if (feedSession.filterSummary !== "No extra filters") parts.push(feedSession.filterSummary)
    if (feedSession.retainedReadStories > 0)
      parts.push(feedSession.retainedReadStories + " just read shown until this view changes")
    parts.push(feedSession.totalStories + (briefingVisible ? " briefing items" : " stories"))
    parts.push(Number(feedSession.unreadCounts[sectionNavigation.currentSection] || 0) + (briefingVisible ? " updates unread" : " unread"))
    return parts.join(" · ")
  }

  function sectionIcon(iconId) {
    var icons = {
      newspaper: "",
      spark: "",
      core: "",
      plugins: "",
      youtube: "",
      saved: ""
    }
    return icons[iconId] || ""
  }

  function open(payloadJson) {
    closingFromHost = false
    if (opened) {
      windowController.begin()
      return
    }
    opened = true
    preferencesOpen = false
    sectionSettingsOpen = false
    storyViewportController.selectedIndex = 0
    storyViewportController.storyViewportAnchorIndex = 0
    readerActions.begin()
    feedSession.begin()
    pluginMaintenance.inspectShortcut()
    pluginMaintenance.inspectPluginUpdate()
    windowController.begin()
  }

  function stopOwnedProcesses() {
    searchTimer.stop()
    pluginMaintenance.stop()
    feedSession.stop()
    readerActions.stop()
  }

  function close() {
    closingFromHost = true
    storyViewportController.preservationTimer.stop()
    storyViewportController.pendingViewportPreservation = false
    storyViewportController.pendingViewportAttempts = 0
    storyViewportController.forcedTopAnchorIndex = -1
    opened = false
    preferencesOpen = false
    sectionSettingsOpen = false
    stopOwnedProcesses()
    windowController.stop()
    closingFromHost = false
  }

  function dismiss() {
    readerActions.cancelInitialStoryRead()
    windowController.requestClose()
  }

  function finishClosing() {
    root.close()
    if (shell && typeof shell.hide === "function") shell.hide(pluginId)
  }

  function handleEscape() {
    if (detailItem) {
      closeInsight()
    } else if (sectionSettingsOpen) {
      sectionSettingsOpen = false
      navigationFocus.forceActiveFocus()
    } else if (preferencesOpen) {
      preferencesOpen = false
      navigationFocus.forceActiveFocus()
    } else if (masthead.search.activeFocus) {
      navigationFocus.forceActiveFocus()
    } else dismiss()
  }

  function openBriefingEvent(event) {
    if (!event || !event.source) return
    readerActions.cancelInitialStoryRead()
    readerActions.queueStoryRead(event, true)
    readerActions.openUrl(String(event.source.url))
  }

  function overviewTools() {
    return [backHomeButton, setupButton, setupNewsButton, relevanceButton]
      .filter(function(item) { return item.visible && item.enabled })
  }

  function focusBriefingControl(direction) {
    var group = keySurface.narrow ? readerList.group : inspectorView.group
    var groupTargets = group && group.visible ? group.controlTargets() : []
    var targets = (overviewVisible ? discoveryView.controlTargets() : briefingNotice.controlTargets().concat(groupTargets)).concat(overviewTools())
    if (!targets.length) {
      briefingControlsMode = false
      navigationFocus.forceActiveFocus()
      return
    }
    var current = -1
    for (var i = 0; i < targets.length; i++) {
      if (targets[i].activeFocus) current = i
    }
    var next = current < 0 ? (direction < 0 ? targets.length - 1 : 0)
      : (current + direction + targets.length) % targets.length
    if (groupTargets.indexOf(targets[next]) >= 0) {
      storyViewportController.pendingViewportPreservation = false
      storyViewportController.storyViewportRevision++
      storyViewportController.animation.stop()
      if (keySurface.narrow) readerList.revealGroup()
      else inspectorView.contentY = 0
    }
    targets[next].forceActiveFocus()
    if (overviewVisible && overviewTools().indexOf(targets[next]) < 0) discoveryView.revealControl(targets[next])
  }

  function handleProjection(result, viewportMode) {
    if (detailItem) updateInsightDetail(result.events || [])
    sectionNavigation.ensureVisibleSection()
    storyViewportController.applyProjection(result, viewportMode)
    readerActions.scheduleInitialStoryRead()
  }

  function activateSection(preserveInitialCandidate) {
    if (preserveInitialCandidate !== true) readerActions.cancelInitialStoryRead()
    navigationFocus.forceActiveFocus()
    Qt.callLater(sectionRail.revealSelected)
    homeMode = true
    setupMode = true
    discoveryView.resetRoute()
    detailItem = null
    detailParents = []
    inspectorFactsOpen = false
    storyViewportController.selectedIndex = 0
    storyViewportController.storyViewportAnchorIndex = 0
    readerActions.unreadSessionRetainedIds = ({})
    feedSession.requestProjection()
  }

  function loadMore() {
    if (!feedSession.hasMoreStories) return
    readerActions.cancelInitialStoryRead()
    storyViewportController.storyViewportRevision++
    storyViewportController.animation.stop()
    sectionNavigation.extendLimit()
    feedSession.requestProjection("preserve")
  }

  function showInsight(item) {
    if (!item) return
    readerActions.cancelInitialStoryRead()
    if (detailItem) detailParents = detailParents.concat([detailItem])
    var full = (feedSession.insightsModel.projectDetails || []).concat(feedSession.setupModel, feedSession.insightsModel.projects || []).filter(function(project) { return project.id === item.id })
    detailItem = full.length ? full[0] : item
    Qt.callLater(function() { insightDetail.focusFirst() })
  }

  function updateInsightDetail(events) {
    if (detailItem.id === "radar-local-relevance") {
      detailItem = Object.assign({}, detailItem, { relevanceTargets: relevanceChoices() })
      return
    }
    var matches = (feedSession.insightsModel.projectDetails || []).concat(feedSession.setupModel, feedSession.insightsModel.projects || [], feedSession.insightsModel.collections || [], events)
      .filter(function(item) { return item.id === root.detailItem.id })
    if (matches.length) detailItem = matches[0]
    else detailItem = Object.assign({}, detailItem, {
      relevanceTargets: (detailItem.relevanceTargets || []).map(function(target) {
        var status = feedSession.relevanceControls.filter(function(value) { return value.kind === target.kind && value.id === target.id })
        return status.length ? status[0] : Object.assign({}, target, { followed: false, muted: false })
      })
    })
  }

  function closeInsight() {
    if (detailParents.length) {
      detailItem = detailParents[detailParents.length - 1]
      detailParents = detailParents.slice(0, -1)
    } else {
      detailItem = null
      navigationFocus.forceActiveFocus()
    }
  }

  function relevanceChoices() {
    var projects = (feedSession.insightsModel.projectDetails || []).concat(feedSession.setupModel)
    return feedSession.relevanceControls.map(function(target) {
      var project = target.kind === "plugin" ? projects.filter(function(item) { return item.id === target.id }) : []
      return project.length ? Object.assign({}, target, { label: project[0].name }) : target
    })
  }

  function manageRelevance() {
    showInsight({ id: "radar-local-relevance", name: "Following & muted",
      description: "These choices stay on this computer. Clear a choice to return to the normal selection. Your current briefing and saved stories remain available.",
      relevanceTargets: relevanceChoices() })
  }

  function openBriefingStory(index) {
    readerActions.cancelInitialStoryRead()
    homeMode = false
    storyViewportController.selectStory(index, true)
    Qt.callLater(function() { navigationFocus.forceActiveFocus(); storyViewportController.restoreStoryViewport() })
  }

  function showSectionSettings() {
    readerActions.cancelInitialStoryRead()
    sectionSettingsOpen = true
    Qt.callLater(function() { sectionSettings.doneButton.forceActiveFocus() })
  }

  SectionNavigation {
    id: sectionNavigation
    session: feedSession
    onSectionSelected: function(preserveInitialCandidate) { root.activateSection(preserveInitialCandidate) }
  }

  PanelDiagnostics {
    id: diagnostics
    panel: root
    sectionsModel: sectionNavigation
    session: feedSession
    actions: readerActions
    storyViewport: storyViewportController
    maintenance: pluginMaintenance
    windowLifecycle: windowController
    views: ({ keySurface: keySurface, readerList: readerList, inspectorView: inspectorView,
      discoveryView: discoveryView, briefingNotice: briefingNotice, sectionRail: sectionRail,
      panelWindow: panelWindow, masthead: masthead, preferencesDialog: preferencesDialog,
      sectionSettings: sectionSettings, welcomeCard: welcomeCard, insightDetail: insightDetail })
  }

  PluginMaintenance {
    id: pluginMaintenance
    helperPath: root.helperPath
    shortcutHelperPath: root.shortcutHelperPath
    opened: root.opened
  }

  ReaderActions {
    id: readerActions
    session: feedSession
    helperPath: root.helperPath
    selectedStory: storyViewportController.selectedStory
    currentSection: sectionNavigation.currentSection
    currentFilter: sectionNavigation.currentFilter
    sectionVisibility: sectionNavigation.sectionVisibility
    opened: root.opened
    windowVisible: panelWindow.visible
    preferencesOpen: root.preferencesOpen
    sectionSettingsOpen: root.sectionSettingsOpen
    overviewVisible: root.overviewVisible
    detailItem: root.detailItem
    briefingVisible: root.briefingVisible
    onPreferencesReady: {
      root.preferencesOpen = true
      Qt.callLater(function() { preferencesDialog.firstButton.forceActiveFocus() })
    }
    onStateAccepted: sectionNavigation.ensureVisibleSection()
    onFilterChanging: sectionNavigation.resetSectionLimit(sectionNavigation.currentSection)
  }

  FeedSession {
    id: feedSession
    helperPath: root.helperPath
    cacheBase: root.cacheBase
    opened: root.opened
    currentSection: sectionNavigation.currentSection
    query: masthead.search.text
    limit: Number(sectionNavigation.sectionLimits[sectionNavigation.currentSection] || sectionNavigation.pageSize)
    retainedReadIds: Object.keys(readerActions.unreadSessionRetainedIds).sort()
    stateMutationPending: readerActions.stateMutationPending
    readMutationPending: readerActions.readMutationPending
    onProjectionRequested: function(mode) { if (mode === "reset") storyViewportController.forcedTopAnchorIndex = -1 }
    onProjectionReady: function(result, mode) { root.handleProjection(result, mode) }
    onProjectionFailed: storyViewportController.clear()
    onStateAccepted: sectionNavigation.ensureVisibleSection()
    onInteractionRequested: readerActions.cancelInitialStoryRead()
    onRefreshChecked: pluginMaintenance.inspectPluginUpdate()
    onBriefingFinished: function(reset) {
      if (reset) {
        storyViewportController.selectedIndex = 0
        masthead.search.text = ""
        readerActions.unreadSessionRetainedIds = ({})
      }
      Qt.callLater(function() {
        if (feedSession.onboardingVisible) welcomeCard.focusChoice()
        else { root.briefingControlsMode = false; navigationFocus.forceActiveFocus() }
      })
    }
  }

  StoryViewport {
    id: storyViewportController
    storyList: readerList.list
    loadMoreButton: readerList.loadMoreButton
    hasMoreStories: feedSession.hasMoreStories
    onSelected: function(markRead) {
      if (markRead) readerActions.cancelInitialStoryRead()
      root.inspectorFactsOpen = false
      if (markRead) readerActions.queueStoryRead(storyViewportController.selectedStory, true)
    }
    onNavigationRequested: navigationFocus.forceActiveFocus()
  }

  WindowLifecycle {
    id: windowController
    window: panelWindow
    helperPath: root.helperPath
    preferredWidth: Style.space(1120)
    preferredHeight: Style.space(720)
    minimumWidth: Style.space(720)
    minimumHeight: Style.space(480)
    contentReady: feedSession.localStateReady && feedSession.installedPluginsReady
      && !feedSession.reading && !feedSession.projecting && !feedSession.pendingProjection
      && !feedSession.briefingRunning && (!feedSession.cachedFeed || feedSession.onboardingVisible || feedSession.briefing.initialized)
    onRevealed: {
      if (feedSession.onboardingVisible) welcomeCard.focusChoice()
      else navigationFocus.forceActiveFocus()
      readerActions.scheduleInitialStoryRead()
    }
    onCloseReady: root.finishClosing()
    onCompositorClosed: root.finishClosing()
  }

  Timer {
    id: searchTimer
    interval: 160
    repeat: false
    onTriggered: {
      readerActions.cancelInitialStoryRead()
      readerActions.unreadSessionRetainedIds = ({})
      feedSession.requestProjection()
    }
  }

  FloatingWindow {
    id: panelWindow
    visible: false
    title: root.compositorWindowTitle
    color: Color.popups.background
    implicitWidth: screen && screen.width > 0
      ? Math.min(Style.space(1120), screen.width - Style.gapsOut * 2)
      : Style.space(1120)
    implicitHeight: screen && screen.height > 0
      ? Math.min(Style.space(720), screen.height - Style.gapsOut * 2)
      : Style.space(720)
    minimumSize: Qt.size(windowController.fittedMinimumWidth, windowController.fittedMinimumHeight)

    FocusScope {
      id: keySurface
      anchors.fill: parent
      focus: true
      Keys.onEscapePressed: root.handleEscape()
      Keys.onPressed: function(event) {
        if (feedSession.onboardingVisible) {
          if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
            welcomeCard.cycleChoice()
            event.accepted = true
          } else if (event.key === Qt.Key_Escape || (event.text || "").toLowerCase() === "q") {
            root.handleEscape()
            event.accepted = true
          }
          return
        }
        if (root.sectionSettingsOpen || root.preferencesOpen || root.detailItem) return
        if (event.key === Qt.Key_F6 && (root.briefingVisible || root.overviewVisible || sectionNavigation.currentSection === "for-you")) {
          readerActions.cancelInitialStoryRead()
          root.briefingControlsMode = !root.briefingControlsMode
          if (root.briefingControlsMode) root.focusBriefingControl(1)
          else navigationFocus.forceActiveFocus()
          event.accepted = true
          return
        }
        if (root.briefingControlsMode) {
          if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
            root.focusBriefingControl(event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier) ? -1 : 1)
            event.accepted = true
          } else if (event.key === Qt.Key_Escape || (event.text || "").toLowerCase() === "q") {
            root.handleEscape()
            event.accepted = true
          }
          return
        }
        if (root.overviewVisible) {
          var overviewKey = (event.text || "").toLowerCase()
          if (event.key === Qt.Key_Down || overviewKey === "j") {
            discoveryView.moveSelection(1); event.accepted = true; return
          }
          if (event.key === Qt.Key_Up || overviewKey === "k") {
            discoveryView.moveSelection(-1); event.accepted = true; return
          }
          if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || overviewKey === "o") {
            discoveryView.activateSelected(); event.accepted = true; return
          }
          if (event.key === Qt.Key_Home || event.key === Qt.Key_End) {
            discoveryView.moveSelection(event.key === Qt.Key_Home ? -100000 : 100000)
            event.accepted = true; return
          }
          if (overviewKey === "s" || overviewKey === "u") { event.accepted = true; return }
        }
        if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
          var backwards = event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier)
          sectionNavigation.cycleSection(backwards ? -1 : 1)
          event.accepted = true
          return
        }
        if (event.key === Qt.Key_Escape || (event.text || "").toLowerCase() === "q") {
          root.handleEscape(); event.accepted = true; return
        }
        if (event.key === Qt.Key_Down || (event.text || "").toLowerCase() === "j") {
          storyViewportController.moveSelection(1); event.accepted = true; return
        }
        if (event.key === Qt.Key_Up || (event.text || "").toLowerCase() === "k") {
          storyViewportController.moveSelection(-1); event.accepted = true; return
        }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || (event.text || "").toLowerCase() === "o") {
          readerActions.openSelected(); event.accepted = true; return
        }
        if ((event.text || "").toLowerCase() === "s") {
          readerActions.toggleSaved(); event.accepted = true; return
        }
        if ((event.text || "").toLowerCase() === "u") {
          readerActions.toggleSelectedRead(); event.accepted = true; return
        }
        if ((event.text || "").toLowerCase() === "f") {
          if (masthead.search.activeFocus) return
          readerActions.updateFilter("unreadOnly", !sectionNavigation.currentFilter.unreadOnly)
          event.accepted = true; return
        }
        if ((event.text || "").toLowerCase() === "a") {
          if (masthead.search.activeFocus) return
          readerActions.markCurrentSectionRead()
          event.accepted = true; return
        }
        if ((event.text || "") === "?") {
          if (masthead.search.activeFocus) return
          root.keysLegendOpen = !root.keysLegendOpen
          event.accepted = true; return
        }
        if ((event.text || "").toLowerCase() === "r") {
          feedSession.refreshFeed(); event.accepted = true; return
        }
        if (event.text === "/") {
          masthead.search.forceActiveFocus(); event.accepted = true; return
        }
        if (event.key === Qt.Key_Home) {
          if (storyViewportController.stories.length) {
            storyViewportController.storyViewportRevision++
            storyViewportController.animation.stop()
            var homeViewportRevision = storyViewportController.storyViewportRevision
            var initialContentY = readerList.list.contentY
            storyViewportController.selectStory(0, true)
            storyViewportController.storyViewportAnchorIndex = 0
            Qt.callLater(function() {
              if (storyViewportController.selectedIndex === 0
                  && storyViewportController.storyViewportRevision === homeViewportRevision)
                storyViewportController.animateStoryPosition(0, true, initialContentY)
            })
          } else storyViewportController.selectedIndex = -1
          event.accepted = true; return
        }
        if (event.key === Qt.Key_End) {
          storyViewportController.storyViewportRevision++
          storyViewportController.animation.stop()
          if (storyViewportController.stories.length) {
            storyViewportController.selectStory(storyViewportController.stories.length - 1, true)
            storyViewportController.storyViewportAnchorIndex = storyViewportController.selectedIndex
          }
          else storyViewportController.selectedIndex = -1
          readerList.list.positionViewAtEnd()
          Qt.callLater(function() {
            var footer = readerList.list.footerItem
            readerList.list.contentY = Math.max(
              readerList.list.originY,
              footer ? footer.y + footer.height - readerList.list.height
                : readerList.list.contentHeight - readerList.list.height
            )
          })
          event.accepted = true
          return
        }
        var numeric = Number(event.text)
        if (numeric >= 1 && numeric <= sectionNavigation.sections.length) {
          sectionNavigation.selectSection(numeric - 1); event.accepted = true
        }
      }

      readonly property bool narrow: width < Style.space(860)

      Item {
        id: navigationFocus
        anchors.fill: parent
        focus: true
        onActiveFocusChanged: if (activeFocus) root.briefingControlsMode = false
      }

      BorderSurface {
        id: card
        anchors.fill: parent
        color: Color.popups.background
        radius: Style.cornerRadius
        borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)

        ColumnLayout {
          anchors.fill: parent
          anchors.margins: Style.spacing.panelPadding
          spacing: Style.spacing.panelGap

          RadarMasthead {
            id: masthead
            Layout.fillWidth: true
            session: feedSession
            actions: readerActions
            maintenance: pluginMaintenance
            window: panelWindow
            narrow: keySurface.narrow
            brandLogoPath: root.brandLogoPath
            secondaryTextColor: root.secondaryTextColor
            onCloseRequested: root.dismiss()
            onNavigationRequested: navigationFocus.forceActiveFocus()
            onQueryEdited: searchTimer.restart()
          }

          Flow {
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? childrenRect.height : 0
            visible: !feedSession.onboardingVisible && (sectionNavigation.currentSection === "front-page" || sectionNavigation.currentSection === "for-you")
            spacing: Style.spacing.controlGap
            RadarButton {
              visible: sectionNavigation.currentSection === "front-page" && !root.homeVisible
              id: backHomeButton
              managesTab: true
              onTabRequested: function(direction) { root.focusBriefingControl(direction) }
              label: "← Front Page"
              onClicked: { readerActions.cancelInitialStoryRead(); root.homeMode = true; navigationFocus.forceActiveFocus() }
            }
            RadarButton {
              visible: sectionNavigation.currentSection === "for-you"
              id: setupButton
              managesTab: true
              onTabRequested: function(direction) { root.focusBriefingControl(direction) }
              label: "My setup"
              selected: root.setupVisible
              onClicked: { readerActions.cancelInitialStoryRead(); root.setupMode = true; navigationFocus.forceActiveFocus() }
            }
            RadarButton {
              visible: sectionNavigation.currentSection === "for-you"
              id: setupNewsButton
              managesTab: true
              onTabRequested: function(direction) { root.focusBriefingControl(direction) }
              label: "News for you"
              selected: !root.setupVisible
              onClicked: { readerActions.cancelInitialStoryRead(); root.setupMode = false; navigationFocus.forceActiveFocus() }
            }
            RadarButton {
              id: relevanceButton
              managesTab: true
              onTabRequested: function(direction) { root.focusBriefingControl(direction) }
              label: "Following & muted"
              onClicked: root.manageRelevance()
            }
          }

          BriefingNotice {
            id: briefingNotice
            Layout.fillWidth: true
            visible: root.briefingVisible && !feedSession.onboardingVisible && !root.homeVisible
            briefing: feedSession.briefing
            busy: feedSession.briefingBusy || feedSession.refreshing || !feedSession.installedPluginsReady
            message: feedSession.briefingMessage
            onNewRequested: feedSession.runBriefingAction("new-briefing")
            onFinishRequested: feedSession.runBriefingAction("mark-briefing-read")
            onNavigationRequested: function(direction) { root.focusBriefingControl(direction) }
          }

          RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.spacing.panelGap

            SectionRail {
              id: sectionRail
              Layout.preferredWidth: keySurface.narrow ? card.width * 0.22 : card.width * 0.16
              Layout.minimumWidth: Style.space(200)
              Layout.maximumWidth: keySurface.narrow ? card.width * 0.30 : Style.space(228)
              Layout.fillHeight: true
              Layout.minimumHeight: 0
              sections: sectionNavigation.sections
              counts: feedSession.counts
              unreadCounts: feedSession.unreadCounts
              currentIndex: sectionNavigation.sectionIndex
              keysOpen: root.keysLegendOpen
              secondaryTextColor: root.secondaryTextColor
              quietTextColor: root.quietTextColor
              onSectionRequested: function(index) { sectionNavigation.selectSection(index) }
              onKeysToggled: root.keysLegendOpen = !root.keysLegendOpen
            }

            Rectangle {
              Layout.preferredWidth: Style.spacing.hairline
              Layout.fillHeight: true
              color: Color.popups.border
            }

            DiscoveryView {
              id: discoveryView
              visible: root.overviewVisible
              Layout.fillWidth: true
              Layout.fillHeight: true
              Layout.minimumWidth: Style.space(220)
              setupMode: root.setupVisible
              searching: masthead.search.text !== ""
              home: feedSession.homeModel
              setup: feedSession.setupModel
              stories: storyViewportController.stories
              briefing: feedSession.briefing
              insights: feedSession.insightsModel
              busy: feedSession.briefingBusy || feedSession.refreshing || !feedSession.installedPluginsReady
              imagesVisible: feedSession.preferences.imagesVisible !== false
              message: feedSession.briefingMessage
              onStoryRequested: function(index) { root.openBriefingStory(index) }
              onDetailRequested: function(item) { root.showInsight(item) }
              onBrowseRequested: {
                if (root.setupVisible) root.setupMode = false
                else sectionNavigation.selectSection(sectionNavigation.sectionIndexFor("plugins"))
                navigationFocus.forceActiveFocus()
              }
              onNewRequested: feedSession.runBriefingAction("new-briefing")
              onFinishRequested: feedSession.runBriefingAction("mark-briefing-read")
              onNavigationRequested: function(direction) { root.focusBriefingControl(direction) }
            }

            ReaderList {
              id: readerList
              visible: !root.overviewVisible
              Layout.fillWidth: true
              Layout.fillHeight: true
              Layout.preferredWidth: keySurface.narrow ? card.width * 0.72 : card.width * 0.30
              Layout.minimumWidth: Style.space(220)
              session: feedSession
              actions: readerActions
              viewport: storyViewportController
              narrow: keySurface.narrow
              briefingVisible: root.briefingVisible
              currentProfile: sectionNavigation.currentProfile
              currentFilter: sectionNavigation.currentFilter
              currentSection: sectionNavigation.currentSection
              pageSize: sectionNavigation.pageSize
              availableHeight: card.height
              secondaryTextColor: root.secondaryTextColor
              summaryText: root.sectionSummaryText()
              emptyMessage: root.emptyStateMessage()
              recoveryLabel: root.emptyRecoveryLabel()
              onRecoveryRequested: root.recoverEmptyView()
              onSettingsRequested: root.showSectionSettings()
              onLoadMoreRequested: root.loadMore()
              onContextRequested: root.showInsight(storyViewportController.selectedStory.projectInsight || storyViewportController.selectedStory)
              onGroupSourceRequested: function(event) { root.openBriefingEvent(event) }
              onNavigationRequested: function(direction) { root.focusBriefingControl(direction) }
              onNavigationFocusRequested: navigationFocus.forceActiveFocus()
            }

            Rectangle {
              visible: !keySurface.narrow && !root.overviewVisible && !!storyViewportController.selectedStory
              Layout.preferredWidth: Style.spacing.hairline
              Layout.fillHeight: true
              color: Color.popups.border
            }

            StoryInspector {
              id: inspectorView
              visible: !keySurface.narrow && !root.overviewVisible && !!storyViewportController.selectedStory
              Layout.fillWidth: true
              Layout.fillHeight: true
              Layout.preferredWidth: keySurface.narrow ? card.width * 0.44 : card.width * 0.54
              Layout.minimumWidth: Style.space(240)
              selectedStory: storyViewportController.selectedStory
              briefingVisible: root.briefingVisible
              briefingBusy: feedSession.briefingBusy
              refreshing: feedSession.refreshing
              readMutationPending: readerActions.readMutationPending
              bulkReadInFlight: readerActions.bulkReadInFlight
              inspectorFactsOpen: root.inspectorFactsOpen
              secondaryTextColor: root.secondaryTextColor
              quietTextColor: root.quietTextColor
              onGroupReadRequested: function(groupId) { feedSession.runBriefingAction("mark-briefing-group-read", groupId) }
              onGroupSourceRequested: function(event) { root.openBriefingEvent(event) }
              onNavigationRequested: function(direction) { root.focusBriefingControl(direction) }
              onReadToggleRequested: readerActions.toggleSelectedRead()
              onSaveToggleRequested: readerActions.toggleSaved()
              onMarketplaceRequested: readerActions.openMarketplacePage()
              onContextRequested: root.showInsight(storyViewportController.selectedStory.projectInsight || storyViewportController.selectedStory)
              onSourceRequested: readerActions.openSelected()
              onArticleLinkRequested: function(link) { readerActions.openArticleLink(link) }
              onFactsToggled: root.inspectorFactsOpen = !root.inspectorFactsOpen
            }

          }

        }

        Rectangle {
          anchors.fill: parent
          visible: root.detailItem !== null
          z: 35
          color: root.modalScrimColor
          MouseArea { anchors.fill: parent }
          InsightDetail {
            id: insightDetail
            anchors.fill: parent
            anchors.margins: Style.spacing.panelPadding
            visible: root.detailItem !== null
            item: root.detailItem
            busy: readerActions.stateMutationPending
            imagesVisible: feedSession.preferences.imagesVisible !== false
            hasParent: root.detailParents.length > 0
            onClosed: root.closeInsight()
            onSourceRequested: function(url) { readerActions.openUrl(url) }
            onProjectRequested: function(project) { root.showInsight(project) }
            onRelevanceRequested: function(kind, targetId, mode) { readerActions.setRelevance(kind, targetId, mode) }
          }
        }

        Rectangle {
          anchors.fill: parent
          visible: feedSession.onboardingVisible
          z: 40
          color: root.modalScrimColor
          MouseArea { anchors.fill: parent }

          WelcomeCard {
            id: welcomeCard
            anchors.centerIn: parent
            width: Math.min(parent.width - Style.spacing.panelPadding * 2, Style.space(660))
            busy: feedSession.briefingBusy || feedSession.refreshing
            canStart: feedSession.displayedFeedDigest !== ""
            maximumHeight: parent.height - Style.spacing.panelPadding * 2
            storyCount: feedSession.displayedFeedEventCount
            message: feedSession.briefingMessage
            onStartTodayRequested: feedSession.runBriefingAction("start-from-today")
            onBrowseRequested: feedSession.runBriefingAction("complete-onboarding")
          }
        }

        PreferencesDialog {
          id: preferencesDialog
          anchors.fill: parent
          visible: root.preferencesOpen
          preferences: feedSession.preferences
          sectionVisibility: sectionNavigation.sectionVisibility
          localStateReady: feedSession.localStateReady
          stateMutationPending: readerActions.stateMutationPending
          availableImageCount: feedSession.availableImageCount
          secondaryTextColor: root.secondaryTextColor
          scrimColor: root.modalScrimColor
          onClosed: { root.preferencesOpen = false; navigationFocus.forceActiveFocus() }
          onBooleanRequested: function(name, value) { readerActions.setBooleanPreference(name, value) }
          onSectionRequested: function(section, enabled) { readerActions.setSectionVisibility(section, enabled) }
        }

        SectionSettings {
          id: sectionSettings
          anchors.fill: parent
          visible: root.sectionSettingsOpen
          currentProfile: sectionNavigation.currentProfile
          currentFilter: sectionNavigation.currentFilter
          currentSection: sectionNavigation.currentSection
          sectionSources: feedSession.sectionSources
          filterOptions: feedSession.filterOptions
          scrimColor: root.modalScrimColor
          onClosed: { root.sectionSettingsOpen = false; navigationFocus.forceActiveFocus() }
          onFilterRequested: function(name, value) { readerActions.updateFilter(name, value) }
          onTypeRequested: function(typeId) { readerActions.toggleFilterType(typeId) }
          onResetRequested: readerActions.resetFilter()
        }
      }

      MouseArea {
        visible: !panelWindow.maximized
        z: 100
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Style.space(6)
        cursorShape: Qt.SizeVerCursor
        onPressed: panelWindow.startSystemResize(Qt.TopEdge)
      }
      MouseArea {
        visible: !panelWindow.maximized
        z: 100
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: Style.space(6)
        cursorShape: Qt.SizeVerCursor
        onPressed: panelWindow.startSystemResize(Qt.BottomEdge)
      }
      MouseArea {
        visible: !panelWindow.maximized
        z: 100
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: Style.space(6)
        cursorShape: Qt.SizeHorCursor
        onPressed: panelWindow.startSystemResize(Qt.LeftEdge)
      }
      MouseArea {
        visible: !panelWindow.maximized
        z: 100
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: Style.space(6)
        cursorShape: Qt.SizeHorCursor
        onPressed: panelWindow.startSystemResize(Qt.RightEdge)
      }
    }
  }

  Component.onDestruction: stopOwnedProcesses()
}
