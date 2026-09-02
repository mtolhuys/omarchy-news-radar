import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as RadarModel
import "components"

Item {
  id: root

  property string omarchyPath: Quickshell.env("OMARCHY_PATH")
  property var shell: null
  property var manifest: null
  property var pluginRegistry: null

  readonly property string runtimeBuildIdentity: "news-radar-0.2.1+identity-1"
  readonly property string helperPath: manifest && manifest.__sourceDir
    ? String(manifest.__sourceDir) + "/bin/news-radar-client" : ""
  readonly property string shortcutHelperPath: manifest && manifest.__sourceDir
    ? String(manifest.__sourceDir) + "/bin/news-radar-shortcut" : ""
  readonly property string cacheBase: Quickshell.env("XDG_CACHE_HOME")
    || (Quickshell.env("HOME") + "/.cache")
  readonly property string pluginId: manifest && manifest.id
    ? String(manifest.id) : "io.github.mtolhuys.news-radar"

  property bool opened: false
  property bool closingFromHost: false
  readonly property string compositorWindowTitle: "📰 Omarchy News Radar"
  readonly property color secondaryTextColor: Qt.rgba(
    Color.popups.text.r, Color.popups.text.g, Color.popups.text.b, 0.72)
  property var cachedFeed: null
  property var userState: ({
    schemaVersion: 9,
    readThrough: "1970-01-01T00:00:00Z",
    readOverrides: ({}),
    saved: ({}),
    preferences: ({
      barVisible: true,
      imagesVisible: true,
      sectionFilters: ({})
    })
  })
  property var installedPluginIds: []
  property var stories: []
  property var counts: ({})
  property var unreadCounts: ({})
  property var pendingReadChanges: ({})
  property var unreadSessionRetainedIds: ({})
  property bool readChangeInFlight: false
  property bool bulkReadInFlight: false
  property int sectionIndex: 0
  property int selectedIndex: 0
  property int storyViewportAnchorIndex: 0
  property string feedStatus: "First use"
  property string statusDetail: "No validated cache yet. Radar will check the published edition."
  property string sourceHealth: "No validated source status"
  property string generatedAt: ""
  property var editionTiming: ({})
  property string editionMode: "published"
  property bool refreshing: false
  property bool pendingProjection: false
  property string activeProjectionViewportMode: "reset"
  property string pendingProjectionViewportMode: "reset"
  property int storyViewportRevision: 0
  property bool pendingViewportPreservation: false
  property real pendingViewportContentY: 0
  property int pendingViewportAnchorIndex: -1
  property real pendingViewportAnchorTop: 0
  property int pendingViewportRevision: -1
  property int pendingViewportAttempts: 0
  property int forcedTopAnchorIndex: -1
  property bool localStateReady: false
  property bool preferencesOpen: false
  property bool sectionSettingsOpen: false
  property string shortcutAction: ""
  property string shortcutState: "unknown"
  property string shortcutMessage: ""
  property string windowIntegrationStatus: "idle"
  property int totalStories: 0
  property int retainedReadStories: 0
  property bool hasMoreStories: false
  property string filterSummary: "No extra filters"
  property string sectionSources: ""
  property var filterOptions: []
  property int pageSize: 12
  property var sectionLimits: ({
    "front-page": 12,
    "for-you": 12,
    "core": 12,
    "plugins": 12,
    "saved": 12
  })

  NumberAnimation {
    id: storyScrollAnimation
    target: storyList
    property: "contentY"
    duration: 140
    easing.type: Easing.OutCubic
    onStopped: root.applyPendingViewportPreservation()
  }

  Timer {
    id: viewportPreservationTimer
    interval: 16
    repeat: true
    onTriggered: root.applyPendingViewportPreservation()
  }

  readonly property var preferences: userState && userState.preferences
    ? userState.preferences : ({ barVisible: true, imagesVisible: true, sectionFilters: ({}) })

  readonly property var sections: [
    Object.assign({ id: "front-page" }, root.defaultSectionProfile("front-page")),
    Object.assign({ id: "for-you" }, root.defaultSectionProfile("for-you")),
    Object.assign({ id: "core" }, root.defaultSectionProfile("core")),
    Object.assign({ id: "plugins" }, root.defaultSectionProfile("plugins")),
    Object.assign({ id: "saved" }, root.defaultSectionProfile("saved"))
  ]
  readonly property string currentSection: sections[sectionIndex].id
  readonly property var currentProfile: sections[sectionIndex]
  readonly property var selectedStory: selectedIndex >= 0 && selectedIndex < stories.length
    ? stories[selectedIndex] : null
  readonly property var currentFilter: preferences.sectionFilters
    && preferences.sectionFilters[currentSection]
      ? preferences.sectionFilters[currentSection]
      : ({ period: "all", significance: "all", unreadOnly: false, imagesOnly: false, types: [] })
  readonly property int availableImageCount: countEditionImages(cachedFeed)
  readonly property bool readMutationPending: readChangeInFlight
    || Object.keys(pendingReadChanges).length > 0
  readonly property bool stateMutationPending: stateProc.running || bulkReadInFlight
  readonly property bool anyHelperRunning: readProc.running || cacheSyncProc.running
    || refreshProc.running || projectProc.running
    || installedProc.running || preferencesProc.running || stateMutationPending || readMutationPending
    || openSourceProc.running || windowProc.running || shortcutProc.running

  function runtimeIdentity() {
    return runtimeBuildIdentity
  }

  function emptyStateMessage() {
    if (searchField.text)
      return "No stories match the current filter. Clear search to recover."
    if (!cachedFeed)
      return "No cached edition is available yet. Retry when online."
    if (filterSummary !== "No extra filters")
      return "No stories match this section's local settings. Reset its filters or choose another section."
    return "This section is empty in the current bounded edition."
  }

  function sectionSummaryText() {
    var parts = []
    if (filterSummary !== "No extra filters") parts.push(filterSummary)
    if (retainedReadStories > 0)
      parts.push(retainedReadStories + " just read shown until this view changes")
    parts.push(totalStories + " stories")
    parts.push(Number(unreadCounts[currentSection] || 0) + " unread")
    return parts.join(" · ")
  }

  function debugState() {
    return JSON.stringify({
      build: runtimeBuildIdentity,
      opened: opened,
      section: currentSection,
      selectedIndex: selectedIndex,
      selectedId: selectedStory ? selectedStory.id : "",
      selectedTitle: selectedStory ? selectedStory.title : "",
      selectedHasImage: selectedStory ? !!selectedStory.imageUrl : false,
      selectedMetricIds: selectedStory && selectedStory.metricItems
        ? selectedStory.metricItems.map(function(metric) { return metric.id }) : [],
      selectedMarketplaceUrl: selectedStory ? String(selectedStory.marketplaceUrl || "") : "",
      selectedIsUnread: selectedStory ? selectedStory.isUnread === true : false,
      storyCount: stories.length,
      status: feedStatus,
      editionMode: editionMode,
      publisherStale: editionTiming.publisherStale === true,
      timing: editionTiming,
      statusDetail: statusDetail,
      noCacheNoticeVisible: noCacheNotice.visible,
      availableImageCount: availableImageCount,
      refreshing: refreshing,
      refreshIndicatorVisible: refreshButton.iconSpinning,
      refreshTooltipVisible: refreshButton.tooltipVisible,
      helperRunning: anyHelperRunning,
      localStateReady: localStateReady,
      barVisiblePreference: preferences.barVisible !== false,
      searchFocused: searchField.activeFocus,
      unreadCount: Number(root.unreadCounts[currentSection] || 0),
      bulkReadInFlight: bulkReadInFlight,
      preferencesOpen: preferencesOpen,
      sectionSettingsOpen: sectionSettingsOpen,
      totalStories: totalStories,
      hasMoreStories: hasMoreStories,
      loadMoreFocused: loadMoreButton.activeFocus,
      loadMoreLabel: loadMoreButton.label,
      sectionLimit: Number(sectionLimits[currentSection] || pageSize),
      pendingProjection: pendingProjection,
      projecting: projectProc.running,
      filterSummary: filterSummary,
      retainedReadStories: retainedReadStories,
      sectionName: currentProfile.name,
      sectionSources: sectionSources,
      windowVisible: panelWindow.visible,
      windowWidth: panelWindow.width,
      windowHeight: panelWindow.height,
      maximized: panelWindow.maximized,
      windowIntegrationStatus: windowIntegrationStatus,
      shortcutState: shortcutState,
      shortcutMessage: shortcutMessage,
      emptyStateMessage: emptyStateMessage()
    })
  }

  function itemGeometry(item, visible) {
    if (!item) return JSON.stringify({ visible: false })
    var point = item.mapToItem(null, 0, 0)
    return JSON.stringify({
      x: point.x,
      y: point.y,
      width: item.width,
      height: item.height,
      visible: visible === undefined ? item.visible : visible
    })
  }

  function maximizeGeometry() { return itemGeometry(maximizeButton, maximizeButton.visible) }
  function closeGeometry() { return itemGeometry(closeButton, closeButton.visible) }
  function settingsGeometry() { return itemGeometry(settingsButton, settingsButton.visible) }
  function markAllReadGeometry() { return itemGeometry(markAllReadButton, markAllReadButton.visible) }
  function refreshGeometry() { return itemGeometry(refreshButton, refreshButton.visible) }
  function loadMoreGeometry() {
    return itemGeometry(loadMoreButton, loadMoreButton.visible)
  }
  function filterUnreadGeometry() { return itemGeometry(unreadFilterButton, unreadFilterButton.visible) }
  function filterResetGeometry() { return itemGeometry(filterResetButton, filterResetButton.visible) }
  function pluginPageGeometry() { return itemGeometry(pluginPageButton, pluginPageButton.visible) }
  function readStateGeometry() {
    return keySurface.narrow
      ? itemGeometry(narrowReadButton, narrowReadButton.visible)
      : itemGeometry(readStateButton, readStateButton.visible)
  }
  function tuneNewspaperGeometry() {
    return itemGeometry(barPreferenceButton, preferencesOpen && barPreferenceButton.visible)
  }
  function shortcutMigrationGeometry() {
    return itemGeometry(shortcutMigrationButton, shortcutNotice.visible && shortcutMigrationButton.visible)
  }

  function storyViewportState() {
    var row = selectedIndex >= 0 ? storyList.itemAtIndex(selectedIndex) : null
    var anchorRow = storyViewportAnchorIndex >= 0
      ? storyList.itemAtIndex(storyViewportAnchorIndex) : null
    if (!row) {
      return JSON.stringify({
        selectedIndex: selectedIndex,
        available: false,
        fullyVisible: false,
        topAligned: false,
        viewportHeight: storyList.height,
        contentY: storyList.contentY,
        contentHeight: storyList.contentHeight,
        listCount: storyList.count,
        anchorIndex: storyViewportAnchorIndex,
        scrolling: storyScrollAnimation.running
      })
    }
    var top = row.y - storyList.contentY
    var bottom = top + row.height
    var anchorTop = anchorRow ? anchorRow.y - storyList.contentY : 0
    var anchorBottom = anchorRow ? anchorTop + anchorRow.height : 0
    return JSON.stringify({
      selectedIndex: selectedIndex,
      available: true,
      fullyVisible: top >= -0.5 && bottom <= storyList.height + 0.5,
      topAligned: Math.abs(top) <= 1,
      top: top,
      bottom: bottom,
      viewportHeight: storyList.height,
      contentY: storyList.contentY,
      contentHeight: storyList.contentHeight,
      anchorIndex: storyViewportAnchorIndex,
      anchorAvailable: !!anchorRow,
      anchorTop: anchorTop,
      anchorFullyVisible: !!anchorRow
        && anchorTop >= -0.5 && anchorBottom <= storyList.height + 0.5,
      anchorTopAligned: !!anchorRow && Math.abs(anchorTop) <= 1,
      scrolling: storyScrollAnimation.running
    })
  }

  function startProcess(process, argumentsList) {
    if (!helperPath) {
      feedStatus = "Failed"
      statusDetail = "The bundled client helper path is unavailable."
      return
    }
    if (process.running) process.running = false
    process.command = [helperPath].concat(argumentsList)
    Qt.callLater(function() {
      if (root.opened || process === stateProc || process === readingProc || process === openSourceProc)
        process.running = true
    })
  }

  function runShortcutHelper(action) {
    if (!shortcutHelperPath || shortcutProc.running) return
    shortcutAction = action
    shortcutProc.command = [shortcutHelperPath, action]
    shortcutProc.running = true
  }

  function inspectShortcut() {
    runShortcutHelper("status")
  }

  function migrateShortcut() {
    shortcutState = "updating"
    shortcutMessage = "Updating the exact Radar-owned shortcut…"
    runShortcutHelper("install")
  }

  function countEditionImages(feed) {
    if (!feed || !Array.isArray(feed.events)) return 0
    var count = 0
    for (var index = 0; index < feed.events.length; index++)
      if (feed.events[index] && feed.events[index].image) count++
    return count
  }

  function defaultSectionProfile(section) {
    var values = {
      "front-page": { name: "Front Page", icon: "newspaper", tone: "clear" },
      "for-you": { name: "For You", icon: "spark", tone: "clear" },
      "core": { name: "Core", icon: "core", tone: "clear" },
      "plugins": { name: "Plugins", icon: "plugins", tone: "clear" },
      "saved": { name: "Saved", icon: "saved", tone: "clear" }
    }
    return values[section]
  }

  function sectionIcon(iconId) {
    var icons = {
      newspaper: "",
      spark: "",
      core: "",
      plugins: "",
      saved: ""
    }
    return icons[iconId] || ""
  }

  function open(payloadJson) {
    closingFromHost = false
    if (opened && panelWindow.visible) {
      panelWindow.visible = true
      windowIntegrationStatus = "waiting"
      startProcess(windowProc, ["activate-window"])
      Qt.callLater(function() {
        navigationFocus.forceActiveFocus()
      })
      return
    }
    opened = true
    panelWindow.visible = true
    windowIntegrationStatus = "waiting"
    startProcess(windowProc, ["activate-window"])
    feedStatus = "Loading cache"
    statusDetail = "Reading the last-known-good local edition."
    localStateReady = false
    preferencesOpen = false
    sectionSettingsOpen = false
    selectedIndex = 0
    storyViewportAnchorIndex = 0
    unreadSessionRetainedIds = ({})
    startProcess(readProc, ["read"])
    startProcess(installedProc, ["installed"])
    inspectShortcut()
    Qt.callLater(function() {
      if (root.opened) {
        navigationFocus.forceActiveFocus()
      }
    })
  }

  function stopOwnedProcesses() {
    searchTimer.stop()
    readProc.running = false
    cacheSyncProc.running = false
    refreshProc.running = false
    projectProc.running = false
    installedProc.running = false
    preferencesProc.running = false
    stateProc.running = false
    openSourceProc.running = false
    windowProc.running = false
    shortcutProc.running = false
    refreshing = false
    bulkReadInFlight = false
  }

  function close() {
    closingFromHost = true
    flushReadChanges()
    viewportPreservationTimer.stop()
    pendingViewportPreservation = false
    pendingViewportAttempts = 0
    forcedTopAnchorIndex = -1
    opened = false
    preferencesOpen = false
    sectionSettingsOpen = false
    stopOwnedProcesses()
    panelWindow.visible = false
    closingFromHost = false
  }

  function dismiss() {
    root.close()
    if (shell && typeof shell.hide === "function") shell.hide(pluginId)
  }

  function handleEscape() {
    if (sectionSettingsOpen) {
      sectionSettingsOpen = false
      navigationFocus.forceActiveFocus()
    } else if (preferencesOpen) {
      preferencesOpen = false
      navigationFocus.forceActiveFocus()
    } else if (searchField.activeFocus) {
      navigationFocus.forceActiveFocus()
    } else dismiss()
  }

  function handleRead(raw) {
    var result = RadarModel.parseResponse(raw)
    userState = result.state || userState
    localStateReady = true
    editionMode = String(result.editionMode || "published")
    editionTiming = result.timing || ({})
    if (result.feed) {
      cachedFeed = result.feed
      generatedAt = String(result.feed.generatedAt || "")
      sourceHealth = RadarModel.sourceHealth(result.feed)
      feedStatus = "Cached"
      statusDetail = "Showing the validated local edition while Radar checks the published edition."
    } else {
      cachedFeed = null
      feedStatus = "First use"
      statusDetail = result.quarantine
        ? "Corrupt local state was quarantined. No validated edition is cached."
        : "No validated edition is cached yet."
    }
    requestProjection()
    refreshFeed()
  }

  function syncCachedEdition() {
    if (!opened || refreshing || readProc.running || cacheSyncProc.running) return
    startProcess(cacheSyncProc, ["read"])
  }

  function handleCacheSync(raw) {
    var result = RadarModel.parseResponse(raw)
    if (!opened || !result.feed) return
    var nextGeneratedAt = String(result.feed.generatedAt || "")
    if (nextGeneratedAt === generatedAt) return
    userState = result.state || userState
    cachedFeed = result.feed
    generatedAt = nextGeneratedAt
    editionMode = String(result.editionMode || "published")
    editionTiming = result.timing || editionTiming
    sourceHealth = RadarModel.sourceHealth(result.feed)
    feedStatus = sourceHealth.indexOf("Partial") === 0 ? "Source partial" : "Updated"
    statusDetail = "Adopted a newer validated edition fetched in the background."
    requestProjection("preserve")
  }

  function handleRefresh(raw) {
    var result = RadarModel.parseResponse(raw)
    refreshing = false
    editionMode = String(result.editionMode || editionMode)
    editionTiming = result.timing || editionTiming
    if (result.feed) {
      cachedFeed = result.feed
      generatedAt = String(result.feed.generatedAt || "")
      sourceHealth = RadarModel.sourceHealth(result.feed)
      requestProjection("preserve")
    }
    if (result.status === "local-current") {
      feedStatus = "Local live edition"
      statusDetail = result.message || "No newer published edition; the owner-built edition remains selected."
    } else if (result.status === "stale-publication") {
      feedStatus = "Publisher stale"
      statusDetail = result.message || "Publisher lag: the public edition is older than the documented threshold."
    } else if (result.status === "updated" || result.status === "no-change") {
      feedStatus = sourceHealth.indexOf("Partial") === 0
        ? "Source partial"
        : (result.status === "updated" ? "Updated" : "No newer edition")
      statusDetail = result.message || "The published edition check completed."
    } else if (result.status === "invalid-feed") {
      feedStatus = "Invalid feed"
      statusDetail = result.message || (result.cachePreserved
        ? "Radar rejected the candidate and preserved the last-known-good edition."
        : "Radar rejected the candidate. Retry after the feed is repaired.")
    } else {
      feedStatus = result.feed ? "Offline" : "No cache and failed"
      statusDetail = result.message || (result.feed
        ? "The update check failed; the last-known-good edition remains readable."
        : "The update check failed and no validated cache exists. Retry when online.")
    }
  }

  function handleInstalled(raw) {
    var result = RadarModel.parseResponse(raw)
    installedPluginIds = result.status === "ok" && Array.isArray(result.pluginIds)
      ? result.pluginIds : []
    requestProjection("preserve")
  }

  function requestProjection(viewportMode) {
    if (!opened) return
    var requestedMode = viewportMode === "preserve" ? "preserve" : "reset"
    if (requestedMode === "reset") forcedTopAnchorIndex = -1
    if (projectProc.running) {
      if (!pendingProjection || requestedMode === "reset")
        pendingProjectionViewportMode = requestedMode
      pendingProjection = true
      return
    }
    pendingProjection = false
    activeProjectionViewportMode = requestedMode
    startProcess(projectProc, [
      "project",
      "--section", currentSection,
      "--installed-json", JSON.stringify(installedPluginIds),
      "--query", searchField.text,
      "--limit", String(Number(sectionLimits[currentSection] || pageSize)),
      "--retained-read-ids-json", JSON.stringify(Object.keys(unreadSessionRetainedIds).sort())
    ])
  }

  function restoreStoryViewport(revision) {
    if (revision !== undefined && revision !== storyViewportRevision) return
    if (!stories.length || selectedIndex < 0) return
    storyScrollAnimation.stop()
    if (hasMoreStories && selectedIndex === stories.length - 1)
      storyList.positionViewAtEnd()
    else {
      var anchorIndex = Math.max(
        0,
        Math.min(selectedIndex, storyViewportAnchorIndex)
      )
      storyViewportAnchorIndex = anchorIndex
      storyList.positionViewAtIndex(anchorIndex, ListView.Beginning)
    }
  }

  function queueViewportPreservation(contentY, anchorIndex, anchorTop, revision) {
    pendingViewportPreservation = true
    pendingViewportContentY = contentY
    pendingViewportAnchorIndex = anchorIndex
    pendingViewportAnchorTop = forcedTopAnchorIndex === anchorIndex ? 0 : anchorTop
    pendingViewportRevision = revision
    pendingViewportAttempts = 24
    viewportPreservationTimer.start()
    // Correct the model-replacement offset in this turn so the retained row
    // never flashes at its provisional delegate position. The timer then
    // keeps the same anchor stable across subsequent rendered frames.
    applyPendingViewportPreservation()
  }

  function applyPendingViewportPreservation() {
    if (!pendingViewportPreservation) return
    if (pendingViewportRevision !== storyViewportRevision) {
      pendingViewportPreservation = false
      pendingViewportAttempts = 0
      viewportPreservationTimer.stop()
      return
    }
    if (storyScrollAnimation.running) return
    var targetContentY = pendingViewportContentY
    var anchorRow = pendingViewportAnchorIndex >= 0
      ? storyList.itemAtIndex(pendingViewportAnchorIndex) : null
    if (pendingViewportAnchorIndex >= 0 && !anchorRow && pendingViewportAttempts > 0) {
      pendingViewportAttempts--
      storyList.positionViewAtIndex(pendingViewportAnchorIndex, ListView.Beginning)
      return
    }
    if (anchorRow) targetContentY = anchorRow.y - pendingViewportAnchorTop
    var maximumContentY = storyList.originY
      + Math.max(0, storyList.contentHeight - storyList.height)
    storyList.contentY = Math.max(
      storyList.originY,
      Math.min(targetContentY, maximumContentY)
    )
    if (anchorRow && pendingViewportAttempts > 0) {
      pendingViewportAttempts--
      return
    }
    pendingViewportPreservation = false
    pendingViewportAttempts = 0
    viewportPreservationTimer.stop()
  }

  function storyIndexById(eventId) {
    if (!eventId) return -1
    for (var index = 0; index < stories.length; index++) {
      if (stories[index] && String(stories[index].id) === eventId) return index
    }
    return -1
  }

  function handleProjection(raw) {
    var result = RadarModel.parseResponse(raw)
    if (result.status === "ok" || result.status === "first-use") {
      var preserveViewport = activeProjectionViewportMode === "preserve"
      var resumeTopAlignment = preserveViewport && storyScrollAnimation.running
      if (resumeTopAlignment) storyScrollAnimation.stop()
      var preservedContentY = storyList.contentY
      var preservedSelectedId = selectedStory && selectedStory.id
        ? String(selectedStory.id) : ""
      var preservedAnchorId = storyViewportAnchorIndex >= 0
          && storyViewportAnchorIndex < stories.length
          && stories[storyViewportAnchorIndex]
        ? String(stories[storyViewportAnchorIndex].id) : ""
      var preservedAnchorRow = storyViewportAnchorIndex >= 0
        ? storyList.itemAtIndex(storyViewportAnchorIndex) : null
      var preservedAnchorTop = preservedAnchorRow
        ? preservedAnchorRow.y - storyList.contentY : 0
      var preservedAnchor = storyViewportAnchorIndex
      stories = result.events || []
      counts = result.counts || ({})
      unreadCounts = result.unreadCounts || ({})
      totalStories = Number(result.totalEvents || 0)
      retainedReadStories = Number(result.retainedReadCount || 0)
      hasMoreStories = result.hasMore === true
      filterSummary = String(result.filterSummary || "No extra filters")
      sectionSources = String(result.sectionSources || "")
      filterOptions = result.filterOptions || []
      var preservedSelectedIndex = preserveViewport
        ? storyIndexById(preservedSelectedId) : -1
      var preservedAnchorIndex = preserveViewport
        ? storyIndexById(preservedAnchorId) : -1
      selectedIndex = stories.length
        ? (preservedSelectedIndex >= 0
          ? preservedSelectedIndex
          : Math.min(Math.max(0, selectedIndex), stories.length - 1))
        : -1
      storyViewportAnchorIndex = stories.length
        ? Math.min(
          Math.max(0, preservedAnchorIndex >= 0 ? preservedAnchorIndex : preservedAnchor),
          selectedIndex
        )
        : -1
      if (forcedTopAnchorIndex === storyViewportAnchorIndex)
        preservedAnchorTop = 0
      if (preserveViewport) {
        // Replacing a ListView model may reset contentY while delegates settle.
        // Keep the reader at the exact live visual anchor. If a read-state
        // projection completed during a keyboard scroll, stop the obsolete
        // animation target, restore the current on-screen position against
        // the replacement delegates, then continue toward the new row's top.
        storyList.contentY = preservedContentY
        var preservedRevision = storyViewportRevision
        if (resumeTopAlignment) {
          var resumeAnchorIndex = storyViewportAnchorIndex
          Qt.callLater(function() {
            if (preservedRevision !== root.storyViewportRevision) return
            var resumeRow = storyList.itemAtIndex(resumeAnchorIndex)
            if (resumeRow) {
              var resumeMaximumY = storyList.originY
                + Math.max(0, storyList.contentHeight - storyList.height)
              storyList.contentY = Math.max(
                storyList.originY,
                Math.min(resumeRow.y - preservedAnchorTop, resumeMaximumY)
              )
            }
            root.animateStoryPosition(
              resumeAnchorIndex,
              true,
              storyList.contentY
            )
          })
        } else {
          queueViewportPreservation(
            preservedContentY,
            storyViewportAnchorIndex,
            preservedAnchorTop,
            preservedRevision
          )
        }
      } else {
        storyViewportRevision++
        var restoreRevision = storyViewportRevision
        Qt.callLater(function() { root.restoreStoryViewport(restoreRevision) })
      }
    } else {
      stories = []
      totalStories = 0
      retainedReadStories = 0
      hasMoreStories = false
      selectedIndex = -1
      storyViewportAnchorIndex = -1
      feedStatus = "Failed"
      statusDetail = result.message || "The local reading model could not be built."
    }
  }

  function refreshFeed() {
    if (refreshing || !opened) return
    refreshing = true
    feedStatus = cachedFeed ? "Checking" : "First use"
    statusDetail = cachedFeed
      ? "Checking the published static edition; cached stories remain readable."
      : "Fetching the first bounded edition."
    startProcess(refreshProc, ["refresh"])
  }

  function selectSection(index) {
    if (index < 0 || index >= sections.length) return
    navigationFocus.forceActiveFocus()
    sectionIndex = index
    selectedIndex = 0
    storyViewportAnchorIndex = 0
    unreadSessionRetainedIds = ({})
    requestProjection()
  }

  function cycleSection(delta) {
    var next = (sectionIndex + delta) % sections.length
    if (next < 0) next += sections.length
    selectSection(next)
  }

  function resetSectionLimit(section) {
    var limits = Object.assign({}, sectionLimits)
    limits[section] = pageSize
    sectionLimits = limits
  }

  function loadMore() {
    if (!hasMoreStories) return
    storyViewportRevision++
    storyScrollAnimation.stop()
    var limits = Object.assign({}, sectionLimits)
    limits[currentSection] = Math.min(500, Number(limits[currentSection] || pageSize) + pageSize)
    sectionLimits = limits
    requestProjection("preserve")
  }

  function moveSelection(delta) {
    if (!stories.length) return
    if (loadMoreButton.activeFocus) {
      if (delta < 0) {
        // The final story remains selected while Load more owns focus. Returning
        // focus must not reposition or re-read that unchanged selection.
        navigationFocus.forceActiveFocus()
      }
      return
    }
    if (delta > 0 && selectedIndex === stories.length - 1 && hasMoreStories) {
      loadMoreButton.forceActiveFocus(Qt.TabFocusReason)
      storyList.positionViewAtEnd()
      return
    }
    storyViewportRevision++
    storyScrollAnimation.stop()
    var viewportRevision = storyViewportRevision
    var nextIndex = Math.max(0, Math.min(stories.length - 1, selectedIndex + delta))
    forcedTopAnchorIndex = -1
    if (delta < 0) {
      var previousRow = storyList.itemAtIndex(nextIndex)
      var previousAboveViewport = !previousRow
        || previousRow.y - storyList.contentY < -0.5
      if (previousAboveViewport) {
        // Key repeat can outrun an eased scroll and leave the highlight above
        // the clip. Move the viewport first so selection is never invisible.
        storyList.positionViewAtIndex(nextIndex, ListView.Beginning)
        storyViewportAnchorIndex = nextIndex
      }
      selectStory(nextIndex, true)
      if (previousAboveViewport) {
        Qt.callLater(function() {
          if (root.selectedIndex === nextIndex
              && root.storyViewportRevision === viewportRevision)
            storyList.positionViewAtIndex(nextIndex, ListView.Beginning)
        })
      }
      return
    }
    var nextRowBeforeSelection = storyList.itemAtIndex(nextIndex)
    if (delta > 0 && !nextRowBeforeSelection) {
      // The first row revealed by pagination can still be virtualized just
      // outside the clip. Do not ask an animation to target geometry that Qt
      // has not created: select the canonical index and place it directly at
      // the top. Its read-state projection then preserves this real anchor.
      selectStory(nextIndex, true)
      storyViewportAnchorIndex = nextIndex
      forcedTopAnchorIndex = nextIndex
      storyList.positionViewAtIndex(nextIndex, ListView.Beginning)
      queueViewportPreservation(
        storyList.contentY,
        nextIndex,
        0,
        viewportRevision
      )
      return
    }
    var initialContentY = storyList.contentY
    var currentRow = delta > 0 ? storyList.itemAtIndex(selectedIndex) : null
    var fallbackNextTop = currentRow
      ? currentRow.y + currentRow.height + storyList.spacing : -1
    selectStory(nextIndex, true)
    Qt.callLater(function() {
      if (root.selectedIndex !== nextIndex
          || root.storyViewportRevision !== viewportRevision) return
      var anchorAtTop = storyNeedsTopAnchor(nextIndex)
      if (anchorAtTop) root.storyViewportAnchorIndex = nextIndex
      animateStoryPosition(nextIndex, anchorAtTop, initialContentY, fallbackNextTop)
    })
  }

  function storyNeedsTopAnchor(index) {
    var row = storyList.itemAtIndex(index)
    if (!row) {
      storyList.positionViewAtIndex(index, ListView.Contain)
      row = storyList.itemAtIndex(index)
    }
    if (!row) return true
    var top = row.y - storyList.contentY
    return top < -0.5 || top + row.height >= storyList.height - 0.5
  }

  function animateStoryPosition(index, alignAtTop, initialContentY, fallbackTargetY) {
    storyScrollAnimation.stop()
    var targetContentY = initialContentY
    if (alignAtTop) {
      storyList.positionViewAtIndex(index, ListView.Beginning)
      targetContentY = storyList.contentY
      var row = storyList.itemAtIndex(index)
      if (row) {
        var maximumContentY = storyList.originY
          + Math.max(0, storyList.contentHeight - storyList.height)
        targetContentY = Math.max(
          storyList.originY,
          Math.min(row.y, maximumContentY)
        )
      } else if (fallbackTargetY !== undefined && fallbackTargetY >= 0) {
        var fallbackMaximumY = storyList.originY
          + Math.max(0, storyList.contentHeight - storyList.height)
        targetContentY = Math.max(
          storyList.originY,
          Math.min(fallbackTargetY, fallbackMaximumY)
        )
      }
    }
    storyList.contentY = initialContentY
    if (Math.abs(targetContentY - initialContentY) <= 0.5) {
      storyList.contentY = targetContentY
      return
    }
    storyScrollAnimation.from = initialContentY
    storyScrollAnimation.to = targetContentY
    storyScrollAnimation.start()
  }

  function selectStory(index, markRead) {
    if (index < 0 || index >= stories.length) return
    selectedIndex = index
    if (markRead) queueStoryRead(stories[index], true)
  }

  function queueStoryRead(story, read) {
    if (!story || !story.id || bulkReadInFlight) return
    var retained = Object.assign({}, unreadSessionRetainedIds)
    if (currentFilter.unreadOnly === true && read === true)
      retained[String(story.id)] = true
    else if (read !== true)
      delete retained[String(story.id)]
    unreadSessionRetainedIds = retained
    var changes = Object.assign({}, pendingReadChanges)
    changes[String(story.id)] = read === true
    pendingReadChanges = changes
    flushReadChanges()
  }

  function flushReadChanges() {
    if (!helperPath || readChangeInFlight) return
    var ids = Object.keys(pendingReadChanges).sort()
    if (!ids.length) return
    var eventId = ids[0]
    var read = pendingReadChanges[eventId] === true
    var remaining = Object.assign({}, pendingReadChanges)
    delete remaining[eventId]
    pendingReadChanges = remaining
    readChangeInFlight = true
    startProcess(readingProc, ["set-read", "--event-id", eventId, "--read", read ? "true" : "false"])
  }

  function toggleSelectedRead() {
    if (!selectedStory || readMutationPending || bulkReadInFlight) return
    queueStoryRead(selectedStory, selectedStory.isUnread === true)
  }

  function openSelected() {
    if (!selectedStory) return
    queueStoryRead(selectedStory, true)
    openUrl(String(selectedStory.source.url))
  }

  function openMarketplacePage() {
    if (!selectedStory || !selectedStory.marketplaceUrl) return
    queueStoryRead(selectedStory, true)
    openUrl(String(selectedStory.marketplaceUrl))
  }

  function openUrl(url) {
    startProcess(openSourceProc, ["open-source", "--url", String(url)])
  }

  function toggleSaved() {
    if (!selectedStory || stateMutationPending) return
    startProcess(stateProc, ["toggle-saved", "--event-id", String(selectedStory.id)])
  }

  function setBooleanPreference(name, value) {
    if (stateMutationPending) return
    var argument = name === "barVisible" ? "--bar-visible" : "--images-visible"
    startProcess(stateProc, ["set-preferences", argument, value ? "true" : "false"])
  }

  function showPreferences() {
    if (!localStateReady || stateMutationPending || preferencesProc.running) return
    startProcess(preferencesProc, ["read"])
  }

  function showSectionSettings() {
    sectionSettingsOpen = true
    Qt.callLater(function() { filterDoneButton.forceActiveFocus() })
  }

  function updateFilter(name, value) {
    if (stateMutationPending) return
    var next = {
      period: currentFilter.period,
      significance: currentFilter.significance,
      unreadOnly: currentFilter.unreadOnly,
      imagesOnly: currentFilter.imagesOnly,
      types: (currentFilter.types || []).slice()
    }
    next[name] = value
    unreadSessionRetainedIds = ({})
    resetSectionLimit(currentSection)
    startProcess(stateProc, [
      "set-section-filter",
      "--section", currentSection,
      "--filter-json", JSON.stringify(next)
    ])
  }

  function toggleFilterType(typeId) {
    var types = (currentFilter.types || []).slice()
    var at = types.indexOf(typeId)
    if (at === -1) types.push(typeId)
    else types.splice(at, 1)
    types.sort()
    updateFilter("types", types)
  }

  function resetFilter() {
    if (stateMutationPending) return
    resetSectionLimit(currentSection)
    unreadSessionRetainedIds = ({})
    startProcess(stateProc, [
      "set-section-filter",
      "--section", currentSection,
      "--filter-json", JSON.stringify({
        period: "all",
        significance: "all",
        unreadOnly: false,
        imagesOnly: false,
        types: []
      })
    ])
  }

  function markCurrentSectionRead() {
    if (!helperPath || refreshing || projectProc.running
        || stateMutationPending || readMutationPending
        || Number(unreadCounts[currentSection] || 0) <= 0) return
    bulkReadInFlight = true
    startProcess(stateProc, [
      "mark-section-read",
      "--section", currentSection,
      "--installed-json", JSON.stringify(installedPluginIds)
    ])
  }

  Process {
    id: readProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleRead(text) }
  }

  Process {
    id: cacheSyncProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleCacheSync(text) }
  }

  Process {
    id: refreshProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleRefresh(text) }
    onExited: function(exitCode) {
      if (root.refreshing && exitCode !== 0) root.refreshing = false
    }
  }

  Process {
    id: installedProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleInstalled(text) }
  }

  Process {
    id: preferencesProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (!root.opened || !result.state) return
        root.userState = result.state
        root.preferencesOpen = true
        Qt.callLater(function() { barPreferenceButton.forceActiveFocus() })
      }
    }
  }

  Process {
    id: projectProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleProjection(text) }
    onRunningChanged: function() {
      if (running) return
      if (root.pendingProjection) {
        var viewportMode = root.pendingProjectionViewportMode
        root.pendingProjection = false
        root.pendingProjectionViewportMode = "reset"
        Qt.callLater(function() { root.requestProjection(viewportMode) })
      }
    }
  }

  Process {
    id: stateProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (result.status === "ok") {
          root.userState = result.state || root.userState
          if (result.markedRead !== undefined) {
            var marked = Number(result.markedRead || 0)
            root.statusDetail = marked > 0
              ? "Marked " + marked + " stor" + (marked === 1 ? "y" : "ies") + " read in this section."
              : "This filtered section has no unread stories."
          }
          root.requestProjection()
        } else {
          root.feedStatus = "Failed"
          root.statusDetail = result.message || "Local state could not be changed."
        }
      }
    }
    onExited: root.bulkReadInFlight = false
  }

  Process {
    id: readingProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (result.status === "ok") {
          root.userState = result.state || root.userState
          if (root.opened) root.requestProjection("preserve")
        } else if (result.status === "stale-event") {
          root.userState = result.state || root.userState
          if (root.opened) root.requestProjection("preserve")
        } else if (root.opened) {
          root.feedStatus = "Failed"
          root.statusDetail = result.message || "Reading state could not be changed."
        }
      }
    }
    onExited: function() {
      root.readChangeInFlight = false
      Qt.callLater(root.flushReadChanges)
    }
  }

  Process { id: openSourceProc; stdout: StdioCollector { waitForEnd: true } }

  Process {
    id: windowProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        root.windowIntegrationStatus = result.status === "ok"
          ? String(result.outcome || "ok")
          : String(result.message || result.status || "failed")
      }
    }
  }

  Process {
    id: shortcutProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (result.classification === "owned-legacy") {
          root.shortcutState = "needs-update"
          root.shortcutMessage = "Your Radar-owned Super+Alt+N shortcut still uses the old close-on-repeat action."
        } else if (root.shortcutAction === "install" && result.status === "migrated") {
          root.shortcutState = "updated"
          root.shortcutMessage = "Super+Alt+N now raises Radar without closing it."
        } else {
          root.shortcutState = "current"
          root.shortcutMessage = ""
        }
      }
    }
    onExited: function(exitCode) {
      if (exitCode !== 0 && root.shortcutAction === "install") {
        root.shortcutState = "failed"
        root.shortcutMessage = "Shortcut update was refused because the binding is no longer an exact Radar-owned block."
      }
    }
  }

  Timer {
    id: searchTimer
    interval: 160
    repeat: false
    onTriggered: {
      root.unreadSessionRetainedIds = ({})
      root.requestProjection()
    }
  }

  FileView {
    id: feedWatcher
    path: root.cacheBase + "/omarchy-news-radar/feed.json"
    watchChanges: true
    printErrors: false
    onFileChanged: {
      reload()
      root.syncCachedEdition()
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
    minimumSize: Qt.size(
      screen && screen.width > 0
        ? Math.min(Style.space(720), screen.width - Style.gapsOut * 2)
        : Style.space(720),
      screen && screen.height > 0
        ? Math.min(Style.space(480), screen.height - Style.gapsOut * 2)
        : Style.space(480)
    )

    onVisibleChanged: {
      if (!visible && root.opened && !root.closingFromHost) root.dismiss()
    }

    FocusScope {
      id: keySurface
      anchors.fill: parent
      focus: true
      Keys.onEscapePressed: root.handleEscape()
      Keys.onPressed: function(event) {
        if (root.sectionSettingsOpen || root.preferencesOpen) return
        if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
          var backwards = event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier)
          root.cycleSection(backwards ? -1 : 1)
          event.accepted = true
          return
        }
        if (event.key === Qt.Key_Escape || (event.text || "").toLowerCase() === "q") {
          root.handleEscape(); event.accepted = true; return
        }
        if (event.key === Qt.Key_Down || (event.text || "").toLowerCase() === "j") {
          root.moveSelection(1); event.accepted = true; return
        }
        if (event.key === Qt.Key_Up || (event.text || "").toLowerCase() === "k") {
          root.moveSelection(-1); event.accepted = true; return
        }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || (event.text || "").toLowerCase() === "o") {
          root.openSelected(); event.accepted = true; return
        }
        if ((event.text || "").toLowerCase() === "s") {
          root.toggleSaved(); event.accepted = true; return
        }
        if ((event.text || "").toLowerCase() === "u") {
          root.toggleSelectedRead(); event.accepted = true; return
        }
        if ((event.text || "").toLowerCase() === "r") {
          root.refreshFeed(); event.accepted = true; return
        }
        if (event.text === "/") {
          searchField.forceActiveFocus(); event.accepted = true; return
        }
        if (event.key === Qt.Key_Home) {
          if (root.stories.length) {
            root.storyViewportRevision++
            storyScrollAnimation.stop()
            var homeViewportRevision = root.storyViewportRevision
            var initialContentY = storyList.contentY
            root.selectStory(0, true)
            root.storyViewportAnchorIndex = 0
            Qt.callLater(function() {
              if (root.selectedIndex === 0
                  && root.storyViewportRevision === homeViewportRevision)
                root.animateStoryPosition(0, true, initialContentY)
            })
          } else root.selectedIndex = -1
          event.accepted = true; return
        }
        if (event.key === Qt.Key_End) {
          root.storyViewportRevision++
          storyScrollAnimation.stop()
          if (root.stories.length) {
            root.selectStory(root.stories.length - 1, true)
            root.storyViewportAnchorIndex = root.selectedIndex
          }
          else root.selectedIndex = -1
          storyList.positionViewAtEnd()
          Qt.callLater(function() {
            var footer = storyList.footerItem
            storyList.contentY = Math.max(
              storyList.originY,
              footer ? footer.y + footer.height - storyList.height
                : storyList.contentHeight - storyList.height
            )
          })
          event.accepted = true
          return
        }
        var numeric = Number(event.text)
        if (numeric >= 1 && numeric <= root.sections.length) {
          root.selectSection(numeric - 1); event.accepted = true
        }
      }

      readonly property bool narrow: width < Style.space(860)

      Item {
        id: navigationFocus
        anchors.fill: parent
        focus: true
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

          GridLayout {
            Layout.fillWidth: true
            columns: keySurface.narrow ? 1 : 2
            columnSpacing: Style.spacing.controlGap
            rowSpacing: Style.spacing.sm

            RowLayout {
              Layout.fillWidth: true
              spacing: Style.spacing.controlGap

              Image {
                Layout.preferredWidth: Style.space(42)
                Layout.preferredHeight: Style.space(42)
                source: Qt.resolvedUrl("../assets/io.github.mtolhuys.news-radar.svg")
                sourceSize: Qt.size(Style.space(84), Style.space(84))
                fillMode: Image.PreserveAspectFit
                mipmap: true
                Accessible.role: Accessible.Graphic
                Accessible.name: "Omarchy News Radar newspaper mark"
              }

              Item {
                Layout.fillWidth: true
                implicitHeight: titleStack.implicitHeight

                Text {
                  id: titleStack
                  anchors.fill: parent
                  text: "OMARCHY NEWS RADAR"
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.display
                  font.bold: true
                  font.letterSpacing: Style.spaceReal(1)
                  verticalAlignment: Text.AlignVCenter
                  Accessible.role: Accessible.Heading
                  Accessible.name: text
                }

                MouseArea {
                  anchors.fill: parent
                  acceptedButtons: Qt.LeftButton
                  cursorShape: Qt.SizeAllCursor
                  onPressed: panelWindow.startSystemMove()
                  onDoubleClicked: panelWindow.maximized = !panelWindow.maximized
                }
              }
            }

            RowLayout {
              Layout.fillWidth: keySurface.narrow
              Layout.alignment: keySurface.narrow ? Qt.AlignLeft : Qt.AlignRight
              spacing: Style.spacing.controlGap

              RadarButton {
                id: refreshButton
                label: root.refreshing ? "Checking…" : "Check for updates"
                iconText: root.refreshing ? "↻" : ""
                iconSpinning: root.refreshing
                tooltipText: "Check the published edition (R)"
                enabled: !root.refreshing
                onClicked: root.refreshFeed()
              }

              RadarButton {
                label: "Tune"
                enabled: root.localStateReady && !root.stateMutationPending && !preferencesProc.running
                onClicked: root.showPreferences()
              }

              PanelActionButton {
                id: maximizeButton
                iconText: panelWindow.maximized ? "❐" : "□"
                tooltipText: panelWindow.maximized ? "Restore" : "Maximize"
                foreground: Color.popups.text
                fontFamily: Style.font.family
                fontSize: Style.font.title
                size: Style.spacing.controlHeight
                bordered: true
                focusable: true
                Accessible.role: Accessible.Button
                Accessible.name: tooltipText
                Accessible.focusable: true
                Accessible.onPressAction: clicked()
                onClicked: {
                  panelWindow.maximized = !panelWindow.maximized
                  navigationFocus.forceActiveFocus()
                }
              }

              PanelActionButton {
                id: closeButton
                iconText: "×"
                tooltipText: "Close"
                foreground: Color.popups.text
                fontFamily: Style.font.family
                fontSize: Style.font.title
                size: Style.spacing.controlHeight
                bordered: true
                focusable: true
                Accessible.role: Accessible.Button
                Accessible.name: tooltipText
                Accessible.focusable: true
                Accessible.onPressAction: clicked()
                onClicked: root.dismiss()
              }
            }
          }

          Text {
            id: noCacheNotice
            Layout.fillWidth: true
            visible: !root.cachedFeed && !root.refreshing && text !== ""
            text: root.statusDetail
            textFormat: Text.PlainText
            color: root.secondaryTextColor
            font.family: Style.font.family
            font.pixelSize: Style.font.bodySmall
            elide: Text.ElideRight
            Accessible.role: Accessible.StaticText
            Accessible.name: text
          }

          BorderSurface {
            id: shortcutNotice
            Layout.fillWidth: true
            Layout.preferredHeight: shortcutNoticeRow.implicitHeight + Style.spacing.controlPaddingY * 2
            visible: root.shortcutState === "needs-update" || root.shortcutState === "updating"
              || root.shortcutState === "updated" || root.shortcutState === "failed"
            color: Style.normalFillFor(Color.popups.text, Color.accent, Color.urgent)
            radius: Style.cornerRadius
            borderSpec: Border.controlSpec(
              root.shortcutState === "failed" ? "focus" : "normal",
              Color.popups.text, Color.accent, Color.urgent)

            RowLayout {
              id: shortcutNoticeRow
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              anchors.leftMargin: Style.spacing.controlPaddingX
              anchors.rightMargin: Style.spacing.controlPaddingX
              spacing: Style.spacing.controlGap

              Text {
                Layout.fillWidth: true
                text: root.shortcutMessage
                textFormat: Text.PlainText
                color: root.shortcutState === "failed" ? Color.urgent : Color.popups.text
                font.family: Style.font.family
                font.pixelSize: Style.font.bodySmall
                wrapMode: Text.WordWrap
                Accessible.role: Accessible.StaticText
                Accessible.name: text
              }

              RadarButton {
                id: shortcutMigrationButton
                visible: root.shortcutState === "needs-update" || root.shortcutState === "failed"
                label: root.shortcutState === "failed" ? "Retry shortcut update" : "Update shortcut"
                tooltipText: "Replace only Radar's exact managed toggle binding with summon activation"
                enabled: !shortcutProc.running
                onClicked: root.migrateShortcut()
              }
            }
          }

          TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search news  /"
            color: Color.popups.text
            placeholderTextColor: root.secondaryTextColor
            selectionColor: Style.selectionFill
            selectedTextColor: Color.popups.text
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            leftPadding: Style.spacing.controlPaddingX
            rightPadding: Style.spacing.controlPaddingX
            topPadding: Style.spacing.inputPaddingY
            bottomPadding: Style.spacing.inputPaddingY
            Accessible.name: "Search news"
            onTextChanged: searchTimer.restart()
            Keys.onPressed: function(event) {
              if (event.key === Qt.Key_Escape) {
                navigationFocus.forceActiveFocus()
                event.accepted = true
              }
            }
            background: BorderSurface {
              color: Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
              radius: Style.cornerRadius
              borderSpec: Border.controlSpec(searchField.activeFocus ? "focus" : "normal", Color.foreground, Color.accent, Color.urgent)
            }
          }

          RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.spacing.panelGap

            ColumnLayout {
              Layout.preferredWidth: keySurface.narrow ? card.width * 0.24 : card.width * 0.16
              Layout.fillHeight: true
              spacing: Style.spacing.sm

              Text {
                text: "SECTIONS"
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                font.bold: true
              }

              Repeater {
                model: root.sections
                SectionButton {
                  required property var modelData
                  required property int index
                  Layout.fillWidth: true
                  label: modelData.name
                  icon: root.sectionIcon(modelData.icon)
                  tone: modelData.tone
                  count: Number(root.counts[modelData.id] || 0)
                  unreadCount: Number(root.unreadCounts[modelData.id] || 0)
                  selected: root.sectionIndex === index
                  onClicked: root.selectSection(index)
                }
              }

              Item { Layout.fillHeight: true }
            }

            Rectangle {
              Layout.preferredWidth: Style.spacing.hairline
              Layout.fillHeight: true
              color: Color.popups.border
            }

            ColumnLayout {
              Layout.fillWidth: true
              Layout.fillHeight: true
              Layout.preferredWidth: keySurface.narrow ? card.width * 0.7 : card.width * 0.46
              spacing: Style.spacing.md

              GridLayout {
                Layout.fillWidth: true
                columns: keySurface.narrow ? 1 : 2
                columnSpacing: Style.spacing.controlGap
                rowSpacing: Style.spacing.sm

                RowLayout {
                  Layout.fillWidth: true

                  Text {
                    text: root.sectionIcon(root.currentProfile.icon)
                    textFormat: Text.PlainText
                    color: Color.accent
                    font.family: Style.font.family
                    font.pixelSize: Style.font.iconLarge
                    Accessible.ignored: true
                  }

                  Text {
                    Layout.fillWidth: true
                    text: root.currentProfile.name.toUpperCase()
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.heading
                    font.bold: true
                    Accessible.role: Accessible.Heading
                    Accessible.name: text
                  }
                }

                RowLayout {
                  Layout.fillWidth: keySurface.narrow
                  Layout.alignment: keySurface.narrow ? Qt.AlignLeft : Qt.AlignRight
                  spacing: Style.spacing.controlGap

                  RadarButton {
                    id: markAllReadButton
                    label: root.bulkReadInFlight ? "Marking read…" : "Mark all as read"
                    tooltipText: "Mark every unread story matching this section's Settings as read"
                    enabled: Number(root.unreadCounts[root.currentSection] || 0) > 0
                      && !root.refreshing && !projectProc.running
                      && !root.stateMutationPending && !root.readMutationPending
                    onClicked: root.markCurrentSectionRead()
                  }

                  RadarButton {
                    id: settingsButton
                    label: "⚙ Settings"
                    selected: root.filterSummary !== "No extra filters"
                    enabled: !root.stateMutationPending
                    onClicked: root.showSectionSettings()
                  }
                }
              }

              Text {
                Layout.fillWidth: true
                text: root.sectionSummaryText()
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                elide: Text.ElideRight
                Accessible.role: Accessible.StaticText
                Accessible.name: text
              }

              Flow {
                visible: keySurface.narrow
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? childrenRect.height : 0
                spacing: Style.spacing.controlGap

                RadarButton {
                  id: narrowReadButton
                  label: root.selectedStory && root.selectedStory.isUnread ? "Mark read" : "Mark unread"
                  selected: !!root.selectedStory && !root.selectedStory.isUnread
                  enabled: !!root.selectedStory && !root.readMutationPending && !root.bulkReadInFlight
                  onClicked: root.toggleSelectedRead()
                }
                RadarButton {
                  label: root.selectedStory && root.selectedStory.isSaved ? "Unsave" : "Save"
                  enabled: !!root.selectedStory
                  onClicked: root.toggleSaved()
                }
                RadarButton {
                  label: "Plugin page"
                  enabled: !!root.selectedStory && !!root.selectedStory.marketplaceUrl
                  onClicked: root.openMarketplacePage()
                }
                RadarButton {
                  label: "Open source"
                  enabled: !!root.selectedStory
                  onClicked: root.openSelected()
                }
              }

              ListView {
                id: storyList
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: root.stories
                spacing: Style.spacing.sm
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                delegate: StoryRow {
                  required property var modelData
                  required property int index
                  width: storyList.width
                  story: modelData
                  selected: index === root.selectedIndex
                  lead: root.currentSection === "front-page" && index === 0
                  onActivated: root.selectStory(index, true)
                }

                Text {
                  anchors.centerIn: parent
                  visible: root.stories.length === 0
                  width: parent.width - Style.spacing.panelPadding * 2
                  text: root.emptyStateMessage()
                  textFormat: Text.PlainText
                  color: root.secondaryTextColor
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  horizontalAlignment: Text.AlignHCenter
                  wrapMode: Text.WordWrap
                  Accessible.role: Accessible.StaticText
                  Accessible.name: text
                }
              }

              Item {
                visible: root.stories.length > 0
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? Style.space(54) : 0

                RadarButton {
                  id: loadMoreButton
                  anchors.centerIn: parent
                  visible: root.hasMoreStories
                  iconText: "↓"
                  label: activeFocus
                    ? "Press Enter to load " + Math.min(root.pageSize, Math.max(0, root.totalStories - root.stories.length)) + " more"
                    : "Load more (" + Math.max(0, root.totalStories - root.stories.length) + " remaining)"
                  tooltipText: "Down to focus · Enter to load the next page"
                  onClicked: {
                    root.loadMore()
                    navigationFocus.forceActiveFocus()
                  }
                }

                Text {
                  anchors.centerIn: parent
                  visible: !root.hasMoreStories
                  text: "All " + root.totalStories + " stories loaded"
                  textFormat: Text.PlainText
                  color: root.secondaryTextColor
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                }
              }
            }

            Rectangle {
              visible: !keySurface.narrow
              Layout.preferredWidth: Style.spacing.hairline
              Layout.fillHeight: true
              color: Color.popups.border
            }

            Flickable {
              visible: !keySurface.narrow
              Layout.fillHeight: true
              Layout.preferredWidth: card.width * 0.29
              contentWidth: width
              contentHeight: inspector.implicitHeight
              clip: true
              boundsBehavior: Flickable.StopAtBounds
              ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

              Column {
                id: inspector
                width: parent.width
                spacing: Style.spacing.panelGap

                BorderSurface {
                  visible: !!root.selectedStory && !!root.selectedStory.imageUrl
                  width: parent.width
                  height: visible ? Math.round(width * 0.58) : 0
                  radius: Style.cornerRadius
                  color: Color.background
                  borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)
                  clip: true

                  Image {
                    anchors.fill: parent
                    source: root.selectedStory && root.selectedStory.imageUrl ? root.selectedStory.imageUrl : ""
                    asynchronous: true
                    cache: true
                    fillMode: Image.PreserveAspectCrop
                    sourceSize.width: 720
                    sourceSize.height: 720
                  }
                }

                Text {
                  visible: !!root.selectedStory && !!root.selectedStory.imageUrl
                  width: parent.width
                  text: visible ? "IMAGE  " + root.selectedStory.image.credit : ""
                  textFormat: Text.PlainText
                  color: root.secondaryTextColor
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  wrapMode: Text.WordWrap
                }

                Text {
                  width: parent.width
                  text: root.selectedStory ? root.selectedStory.title : "Select a story"
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.heading
                  font.bold: true
                  wrapMode: Text.WordWrap
                  Accessible.role: Accessible.Heading
                  Accessible.name: text
                }

                Text {
                  visible: !!root.selectedStory && !!root.selectedStory.metricItems
                    && root.selectedStory.metricItems.length > 0
                  width: parent.width
                  text: "METRICS"
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.bodySmall
                  font.bold: true
                }

                MetricStrip {
                  visible: !!root.selectedStory && !!root.selectedStory.metricItems
                    && root.selectedStory.metricItems.length > 0
                  width: parent.width
                  metrics: visible ? root.selectedStory.metricItems : []
                  foreground: Color.popups.text
                }

                Text {
                  visible: !!root.selectedStory && !!root.selectedStory.metricsObservedAt
                  width: parent.width
                  text: visible ? "OBSERVED  " + root.selectedStory.metricsObservedAt : ""
                  textFormat: Text.PlainText
                  color: root.secondaryTextColor
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  wrapMode: Text.WordWrap
                  Accessible.role: Accessible.StaticText
                  Accessible.name: text
                }

                Text {
                  visible: !!root.selectedStory && !!root.selectedStory.metricsCaveat
                  width: parent.width
                  text: visible ? root.selectedStory.metricsCaveat : ""
                  textFormat: Text.PlainText
                  color: root.secondaryTextColor
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  wrapMode: Text.WordWrap
                }

                Text {
                  width: parent.width
                  text: root.selectedStory ? root.selectedStory.summary : "Story details and the original source appear here."
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  wrapMode: Text.WordWrap
                }

                Text {
                  width: parent.width
                  text: root.selectedStory
                    ? "TYPE  " + root.selectedStory.type + "\nDATE  " + root.selectedStory.occurredAt
                      + "\nTRUST  " + root.selectedStory.trust.marketplace
                      + "\nAUDIT  " + (root.selectedStory.trust.securityAudit ? "authoritative audit declared" : "not claimed")
                      + "\nCOMPAT  " + root.selectedStory.compatibility.basis
                    : ""
                  textFormat: Text.PlainText
                  color: root.secondaryTextColor
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  wrapMode: Text.WrapAnywhere
                  Accessible.role: Accessible.StaticText
                  Accessible.name: text
                }

                Text {
                  width: parent.width
                  text: root.selectedStory ? root.selectedStory.source.label + "\n" + root.selectedStory.source.url : ""
                  textFormat: Text.PlainText
                  color: Color.accent
                  font.family: Style.font.family
                  font.pixelSize: Style.font.bodySmall
                  wrapMode: Text.WrapAnywhere
                }

                Flow {
                  width: parent.width
                  spacing: Style.spacing.controlGap
                  RadarButton {
                    id: readStateButton
                    label: root.selectedStory && root.selectedStory.isUnread ? "Mark read" : "Mark unread"
                    selected: !!root.selectedStory && !root.selectedStory.isUnread
                    enabled: !!root.selectedStory && !root.readMutationPending && !root.bulkReadInFlight
                    onClicked: root.toggleSelectedRead()
                  }
                  RadarButton {
                    label: root.selectedStory && root.selectedStory.isSaved ? "Unsave" : "Save"
                    enabled: !!root.selectedStory
                    onClicked: root.toggleSaved()
                  }
                  RadarButton {
                    id: pluginPageButton
                    visible: !!root.selectedStory && !!root.selectedStory.marketplaceUrl
                    label: "Plugin page"
                    enabled: visible
                    onClicked: root.openMarketplacePage()
                  }
                  RadarButton {
                    label: "Original source"
                    enabled: !!root.selectedStory
                    onClicked: root.openSelected()
                  }
                }
              }
            }
          }

        }

        Rectangle {
          anchors.fill: parent
          visible: root.preferencesOpen
          z: 20
          color: Qt.rgba(Color.background.r, Color.background.g, Color.background.b, 0.82)
          MouseArea { anchors.fill: parent; onClicked: root.preferencesOpen = false }

          BorderSurface {
            anchors.centerIn: parent
            width: Math.min(parent.width - Style.spacing.panelPadding * 2, Style.space(620))
            height: Math.min(parent.height - Style.spacing.panelPadding * 2, Style.space(390))
            color: Color.popups.background
            radius: Style.cornerRadius
            borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)

            MouseArea { anchors.fill: parent }

            ColumnLayout {
              anchors.fill: parent
              anchors.margins: Style.spacing.panelPadding
              spacing: Style.spacing.panelGap

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "TUNE YOUR RADAR"
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.heading
                  font.bold: true
                }
                RadarButton { label: "Done"; onClicked: root.preferencesOpen = false }
              }

              Text {
                Layout.fillWidth: true
                text: "Display preferences stay on this machine and are never sent to the feed or its sources."
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.bodySmall
                wrapMode: Text.WordWrap
              }

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "Top-bar newspaper"
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                }
                RadarButton {
                  id: barPreferenceButton
                  label: root.preferences.barVisible ? "On" : "Off"
                  selected: root.preferences.barVisible
                  onClicked: root.setBooleanPreference("barVisible", !root.preferences.barVisible)
                }
              }

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "Story images"
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                }
                RadarButton {
                  label: root.preferences.imagesVisible ? "On" : "Off"
                  selected: root.preferences.imagesVisible
                  onClicked: root.setBooleanPreference("imagesVisible", !root.preferences.imagesVisible)
                }
              }

              Text {
                Layout.fillWidth: true
                text: root.preferences.imagesVisible
                  ? root.availableImageCount > 0
                    ? root.availableImageCount + " validated marketplace images are available in this edition."
                    : "No stories in this edition include a validated image."
                  : "Images are hidden; every story remains available as text."
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }

              Text {
                Layout.fillWidth: true
                text: "For You is built automatically from exact enabled plugin IDs detected on this machine."
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }
            }
          }
        }

        Rectangle {
          anchors.fill: parent
          visible: root.sectionSettingsOpen
          z: 21
          color: Qt.rgba(Color.background.r, Color.background.g, Color.background.b, 0.82)
          MouseArea { anchors.fill: parent; onClicked: root.sectionSettingsOpen = false }

          BorderSurface {
            anchors.centerIn: parent
            width: Math.min(parent.width - Style.spacing.panelPadding * 2, Style.space(760))
            height: Math.min(parent.height - Style.spacing.panelPadding * 2, Style.space(680))
            color: Color.popups.background
            radius: Style.cornerRadius
            borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)

            MouseArea { anchors.fill: parent }

            ColumnLayout {
              anchors.fill: parent
              anchors.margins: Style.spacing.panelPadding
              spacing: Style.spacing.panelGap

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "⚙ " + root.currentProfile.name.toUpperCase() + " · SECTION SETTINGS"
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.heading
                  font.bold: true
                }
                RadarButton {
                  id: filterDoneButton
                  label: "Done"
                  onClicked: {
                    root.sectionSettingsOpen = false
                    navigationFocus.forceActiveFocus()
                  }
                }
              }

              Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: sectionSettingsContent.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                ColumnLayout {
                  id: sectionSettingsContent
                  width: parent.width
                  spacing: Style.spacing.panelGap

                  Text {
                    Layout.fillWidth: true
                    text: "SOURCES · FIXED FOR THIS SECTION\n" + root.sectionSources
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                  }

                  Text {
                    text: "TIME WINDOW"
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    font.bold: true
                  }

                  RowLayout {
                    spacing: Style.spacing.controlGap
                    Repeater {
                      model: [
                        { id: "all", label: "Any time" },
                        { id: "24h", label: "24 hours" },
                        { id: "7d", label: "7 days" },
                        { id: "30d", label: "30 days" }
                      ]
                      RadarButton {
                        required property var modelData
                        label: modelData.label
                        selected: root.currentFilter.period === modelData.id
                        onClicked: root.updateFilter("period", modelData.id)
                      }
                    }
                  }

                  Text {
                    text: "SIGNIFICANCE"
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    font.bold: true
                  }

                  RowLayout {
                    spacing: Style.spacing.controlGap
                    Repeater {
                      model: [
                        { id: "all", label: "All" },
                        { id: "notable", label: "Notable + critical" },
                        { id: "critical", label: "Critical only" }
                      ]
                      RadarButton {
                        required property var modelData
                        label: modelData.label
                        selected: root.currentFilter.significance === modelData.id
                        onClicked: root.updateFilter("significance", modelData.id)
                      }
                    }
                  }

                  RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.spacing.controlGap
                    RadarButton {
                      id: unreadFilterButton
                      label: "Unread only"
                      selected: root.currentFilter.unreadOnly
                      onClicked: root.updateFilter("unreadOnly", !root.currentFilter.unreadOnly)
                    }
                    RadarButton {
                      label: "With images"
                      selected: root.currentFilter.imagesOnly
                      onClicked: root.updateFilter("imagesOnly", !root.currentFilter.imagesOnly)
                    }
                  }

                  Text {
                    text: "STORY TYPES"
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    font.bold: true
                  }

                  Flow {
                    Layout.fillWidth: true
                    Layout.preferredHeight: childrenRect.height
                    spacing: Style.spacing.controlGap

                    RadarButton {
                      label: "All types"
                      selected: (root.currentFilter.types || []).length === 0
                      onClicked: root.updateFilter("types", [])
                    }

                    Repeater {
                      model: root.filterOptions
                      RadarButton {
                        required property var modelData
                        label: modelData.label
                        selected: (root.currentFilter.types || []).indexOf(modelData.id) !== -1
                        onClicked: root.toggleFilterType(modelData.id)
                      }
                    }
                  }

                  Item { Layout.fillHeight: true }

                  RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    RadarButton {
                      id: filterResetButton
                      label: "Reset section"
                      onClicked: root.resetFilter()
                    }
                  }
                }
              }
            }
          }
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
