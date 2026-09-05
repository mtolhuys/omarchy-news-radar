import QtQuick
import Quickshell.Io
import "../Model.js" as RadarModel

// Validated edition snapshots and their asynchronous helper transactions.
Item {
  id: root
  property var cachedFeed: null

  property var userState: ({
    schemaVersion: 13,
    onboardingComplete: false,
    briefing: null,
    readThrough: "1970-01-01T00:00:00Z",
    readOverrides: ({}),
    saved: ({}),
    preferences: ({
      barVisible: true,
      imagesVisible: true,
      sectionFilters: ({}),
      sectionVisibility: ({ core: true, plugins: true, youtube: true })
    })
  })

  property var installedPluginIds: []

  property var installedPluginFacts: []
  property bool installedFactsAvailable: false

  property var homeModel: ({ featuredCollections: [], discoveries: [], setupUpdates: [] })

  property var setupModel: []

  property var insightsModel: ({ status: "missing", projects: [], collections: [] })

  property var relevanceControls: []

  property bool installedPluginsReady: false

  property var briefing: ({ initialized: false, total: 0, remaining: 0, complete: false })

  property string displayedFeedDigest: ""

  property int displayedFeedEventCount: 0

  property string briefingAction: ""

  property string briefingMessage: ""

  property bool briefingEnsureAttempted: false

  readonly property bool onboardingVisible: localStateReady && !!cachedFeed
    && userState.onboardingComplete === false

  readonly property bool briefingBusy: briefingProc.running || stateMutationPending
    || readMutationPending || projectProc.running

  property var counts: ({})

  property var unreadCounts: ({})

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

  property bool localStateReady: false

  property int totalStories: 0

  property int retainedReadStories: 0

  property bool hasMoreStories: false

  property string filterSummary: "No extra filters"

  property string sectionSources: ""

  property var filterOptions: []

  readonly property var preferences: userState && userState.preferences
    ? userState.preferences : ({
      barVisible: true,
      imagesVisible: true,
      sectionFilters: ({}),
      sectionVisibility: ({ core: true, plugins: true, youtube: true })
    })

  readonly property int availableImageCount: countEditionImages(cachedFeed)

  required property string helperPath
  required property string cacheBase
  property bool opened: false
  property string currentSection: "front-page"
  property string query: ""
  property int limit: 12
  property var retainedReadIds: []
  property bool stateMutationPending: false
  property bool readMutationPending: false
  readonly property bool projecting: projectProc.running
  readonly property bool reading: readProc.running
  readonly property bool briefingRunning: briefingProc.running
  readonly property bool busy: readProc.running || cacheSyncProc.running || refreshProc.running
    || projectProc.running || installedProc.running || briefingProc.running || insightsProc.running
  signal projectionRequested(string mode)
  signal projectionReady(var result, string mode)
  signal projectionFailed()
  signal stateAccepted()
  signal interactionRequested()
  signal briefingFinished(bool reset)
  signal refreshChecked()

  function startProcess(process, argumentsList) {
    if (!helperPath) {
      feedStatus = "Failed"
      statusDetail = "The bundled client helper path is unavailable."
      return
    }
    process.running = false
    process.command = [helperPath].concat(argumentsList)
    Qt.callLater(function() { if (root.opened) process.running = true })
  }
  function begin() {
    feedStatus = "Loading cache"
    statusDetail = "Reading the last-known-good local edition."
    localStateReady = false
    installedPluginsReady = false
    briefingEnsureAttempted = false
    briefingMessage = ""
    startProcess(readProc, ["read"])
    startProcess(installedProc, ["installed"])
    startProcess(insightsProc, ["insights-refresh"])
  }
  function stop() {
    readProc.running = false
    cacheSyncProc.running = false
    refreshProc.running = false
    projectProc.running = false
    installedProc.running = false
    briefingProc.running = false
    insightsProc.running = false
    refreshing = false
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
    ensureBriefing()
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
      ensureBriefing()
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
      if (result.status !== "failed" && result.status !== "offline" && result.status !== "invalid-feed")
      refreshChecked()
  }

  function handleInstalled(raw) {
    var result = RadarModel.parseResponse(raw)
    installedPluginIds = result.status === "ok" && Array.isArray(result.pluginIds)
      ? result.pluginIds : []
    installedPluginFacts = result.status === "ok" && Array.isArray(result.plugins) ? result.plugins : []
    installedFactsAvailable = result.status === "ok" && result.factsAvailable === true
    installedPluginsReady = true
    ensureBriefing()
    requestProjection("preserve")
  }

  function ensureBriefing() {
    if (!opened || !localStateReady || !cachedFeed || !installedPluginsReady
        || briefingProc.running || briefingEnsureAttempted || userState.briefing) return
    briefingEnsureAttempted = true
    briefingAction = "ensure-briefing"
    startProcess(briefingProc, ["ensure-briefing", "--installed-json", JSON.stringify(installedPluginIds)])
  }

  function runBriefingAction(action, eventId) {
    if (!opened || briefingBusy || refreshing || !cachedFeed) return
    interactionRequested()
    briefingMessage = ""
    var argumentsList = [action]
    if (action === "new-briefing" || action === "ensure-briefing")
      argumentsList.push("--installed-json", JSON.stringify(installedPluginIds))
    else if (action === "start-from-today") {
      if (!displayedFeedDigest) return
      argumentsList.push("--feed-digest", displayedFeedDigest)
    } else if (action === "mark-briefing-read" || action === "mark-briefing-group-read") {
      if (!briefing.id) return
      argumentsList.push("--briefing-id", String(briefing.id))
      if (action === "mark-briefing-group-read") argumentsList.push("--event-id", String(eventId))
    }
    briefingAction = action
    startProcess(briefingProc, argumentsList)
  }

  function handleBriefingAction(raw) {
    var result = RadarModel.parseResponse(raw)
    if (!opened) return
    userState = result.state || userState
    if (result.status === "ok" || result.status === "onboarding-complete") {
      briefingMessage = ""
      var reset = briefingAction === "new-briefing" || briefingAction === "start-from-today"
      briefingFinished(reset)
      requestProjection(briefingAction === "new-briefing" ? "reset" : "preserve")
    } else {
      briefingMessage = result.message || "The briefing could not be changed. Please try again."
      requestProjection("preserve")
    }
  }

  function requestProjection(viewportMode) {
    if (!opened) return
    var requestedMode = viewportMode === "preserve" ? "preserve" : "reset"
    projectionRequested(requestedMode)

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
      "--installed-facts-json", JSON.stringify(installedPluginFacts),
      "--installed-facts-status", installedFactsAvailable ? "available" : "unavailable",
      "--query", query,
      "--limit", String(limit),
      "--retained-read-ids-json", JSON.stringify(retainedReadIds)
    ])
  }

  function refreshFeed() {
    if (refreshing || !opened) return
    refreshing = true
    feedStatus = cachedFeed ? "Checking" : "First use"
    statusDetail = cachedFeed
      ? "Checking the published static edition; cached stories remain readable."
      : "Fetching the first bounded edition."
    startProcess(refreshProc, ["refresh"])
    if (!insightsProc.running) startProcess(insightsProc, ["insights-refresh"])
  }

  function countEditionImages(feed) {
    if (!feed || !Array.isArray(feed.events)) return 0
    var count = 0
    for (var index = 0; index < feed.events.length; index++)
      if (feed.events[index] && feed.events[index].image) count++
    return count
  }

  Process {
    id: briefingProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleBriefingAction(text) }
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
    id: insightsProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (root.opened) root.requestProjection("preserve")
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

  function handleProjection(raw) {
    var result = RadarModel.parseResponse(raw)
    if (result.status === "ok" || result.status === "first-use") {
      userState = result.state || userState
      briefing = result.briefing || briefing
      homeModel = result.home || homeModel
      setupModel = result.mySetup || []
      insightsModel = result.insights || insightsModel
      relevanceControls = result.relevanceControls || []
      displayedFeedDigest = String(result.feedDigest || "")
      displayedFeedEventCount = Number(result.feedEventCount || 0)
      counts = result.counts || ({})
      unreadCounts = result.unreadCounts || ({})
      totalStories = Number(result.totalEvents || 0)
      retainedReadStories = Number(result.retainedReadCount || 0)
      hasMoreStories = result.hasMore === true
      filterSummary = String(result.filterSummary || "No extra filters")
      sectionSources = String(result.sectionSources || "")
      filterOptions = result.filterOptions || []
      stateAccepted()
      projectionReady(result, activeProjectionViewportMode)
    } else {
      totalStories = 0
      retainedReadStories = 0
      hasMoreStories = false
      feedStatus = "Failed"
      statusDetail = result.message || "The local reading model could not be built."
      projectionFailed()
    }
  }
}
