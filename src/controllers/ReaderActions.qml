import QtQuick
import Quickshell.Io
import "../Model.js" as RadarModel

// Local read/save/preferences writes and their explicit interaction guards.
Item {
  id: root
  property var pendingReadChanges: ({})

  property var unreadSessionRetainedIds: ({})

  property bool initialStoryReadPending: false

  property string initialStoryReadEventId: ""

  property int initialStoryReadGeneration: -1

  property int panelOpenGeneration: 0

  readonly property int initialStoryReadDelayMs: 650

  property bool readChangeInFlight: false

  property bool bulkReadInFlight: false

  readonly property bool readMutationPending: readChangeInFlight
    || Object.keys(pendingReadChanges).length > 0

  required property var session
  required property string helperPath
  property var selectedStory: null
  property string currentSection: "front-page"
  property var currentFilter: ({ types: [] })
  property var sectionVisibility: ({})
  property bool opened: false
  property bool windowVisible: false
  property bool preferencesOpen: false
  property bool sectionSettingsOpen: false
  property bool overviewVisible: false
  property var detailItem: null
  property bool briefingVisible: false
  readonly property bool stateMutationPending: stateProc.running || bulkReadInFlight || session.briefingRunning
  readonly property bool preferencesRunning: preferencesProc.running
  readonly property bool busy: preferencesProc.running || stateProc.running || readingProc.running || openSourceProc.running
  signal preferencesReady()
  signal stateAccepted()
  signal filterChanging()

  function begin() {
    panelOpenGeneration++
    unreadSessionRetainedIds = ({})
    initialStoryReadPending = true
    initialStoryReadEventId = ""
    initialStoryReadGeneration = -1
    initialStoryReadTimer.stop()
  }
  function stop() {
    panelOpenGeneration++
    cancelInitialStoryRead()
    flushReadChanges()
    preferencesProc.running = false
    stateProc.running = false
    openSourceProc.running = false
    bulkReadInFlight = false
  }
  Timer {
    id: initialStoryReadTimer
    interval: root.initialStoryReadDelayMs
    repeat: false
    onTriggered: root.commitInitialStoryRead()
  }

  function startProcess(process, argumentsList) {
    if (!helperPath) {
      session.feedStatus = "Failed"
      session.statusDetail = "The bundled client helper path is unavailable."
      return
    }
    if (process.running) process.running = false
    process.command = [helperPath].concat(argumentsList)
    Qt.callLater(function() {
      if (root.opened || process === stateProc || process === readingProc || process === openSourceProc)
        process.running = true
    })
  }

  function scheduleInitialStoryRead() {
    if (!initialStoryReadPending || !opened || !windowVisible || !selectedStory
        || session.onboardingVisible || overviewVisible || detailItem || session.briefingRunning)
      return
    var eventId = String(selectedStory.id || "")
    if (!eventId) return
    // Automatic opening projections may replace the selected candidate. Keep
    // the one-shot armed and restart its dwell until one candidate stays
    // stable; generation plus event ID exclude later sessions and selections.
    initialStoryReadEventId = eventId
    initialStoryReadGeneration = panelOpenGeneration
    initialStoryReadTimer.restart()
  }

  function cancelInitialStoryRead() {
    initialStoryReadTimer.stop()
    initialStoryReadPending = false
    initialStoryReadEventId = ""
    initialStoryReadGeneration = -1
  }

  function commitInitialStoryRead() {
    var eventId = initialStoryReadEventId
    var generation = initialStoryReadGeneration
    if (!initialStoryReadPending) return
    if (generation !== panelOpenGeneration || !opened || !windowVisible) {
      cancelInitialStoryRead()
      return
    }
    if (preferencesOpen || sectionSettingsOpen || session.onboardingVisible || overviewVisible || detailItem) {
      cancelInitialStoryRead()
      return
    }
    if (session.projecting || session.pendingProjection) {
      initialStoryReadTimer.restart()
      return
    }
    if (!eventId || !selectedStory || String(selectedStory.id || "") !== eventId) {
      initialStoryReadEventId = ""
      initialStoryReadGeneration = -1
      scheduleInitialStoryRead()
      return
    }
    initialStoryReadPending = false
    initialStoryReadEventId = ""
    initialStoryReadGeneration = -1
    if (selectedStory.isUnread === true)
      queueStoryRead(selectedStory, true)
  }

  function queueStoryRead(story, read) {
    if (!story || !story.id || bulkReadInFlight || session.onboardingVisible || session.briefingRunning) return
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
    cancelInitialStoryRead()
    queueStoryRead(selectedStory, selectedStory.isUnread === true)
  }

  function openSelected() {
    if (!selectedStory) return
    cancelInitialStoryRead()
    queueStoryRead(selectedStory, true)
    openUrl(String(selectedStory.source.url))
  }

  function openMarketplacePage() {
    if (!selectedStory || !selectedStory.marketplaceUrl) return
    cancelInitialStoryRead()
    queueStoryRead(selectedStory, true)
    openUrl(String(selectedStory.marketplaceUrl))
  }

  function setRelevance(kind, identity, mode) {
    if (stateMutationPending) return
    startProcess(stateProc, ["set-relevance", "--kind", kind, "--id", identity, "--mode", mode])
  }

  function openUrl(url) {
    startProcess(openSourceProc, ["open-source", "--url", String(url)])
  }

  function openArticleLink(url) {
    var href = RadarModel.acceptedHttpsUrl(String(url || ""))
    if (!href) return
    openUrl(href)
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

  function setSectionVisibility(sectionId, visible) {
    if (stateMutationPending) return
    if (sectionId !== "core" && sectionId !== "plugins" && sectionId !== "youtube")
      return
    var next = {
      core: sectionVisibility.core !== false,
      plugins: sectionVisibility.plugins !== false,
      youtube: sectionVisibility.youtube !== false
    }
    next[sectionId] = visible === true
    startProcess(stateProc, [
      "set-preferences",
      "--section-visibility-json",
      JSON.stringify(next)
    ])
  }

  function showPreferences() {
    if (!session.localStateReady || stateMutationPending || preferencesProc.running) return
    cancelInitialStoryRead()
    startProcess(preferencesProc, ["read"])
  }

  function updateFilter(name, value) {
    if (stateMutationPending) return
    cancelInitialStoryRead()
    var next = {
      period: currentFilter.period,
      significance: currentFilter.significance,
      unreadOnly: currentFilter.unreadOnly,
      imagesOnly: currentFilter.imagesOnly,
      types: (currentFilter.types || []).slice()
    }
    next[name] = value
    unreadSessionRetainedIds = ({})
    filterChanging()
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
    cancelInitialStoryRead()
    filterChanging()
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
    if (!selectedStory) return
    if (briefingVisible) {
      session.runBriefingAction("mark-briefing-read")
      return
    }
    if (!helperPath || session.refreshing || session.projecting
        || stateMutationPending || readMutationPending
        || Number(session.unreadCounts[currentSection] || 0) <= 0) return
    cancelInitialStoryRead()
    bulkReadInFlight = true
    startProcess(stateProc, [
      "mark-section-read",
      "--section", currentSection,
      "--installed-json", JSON.stringify(session.installedPluginIds)
    ])
  }

  Process {
    id: preferencesProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (!root.opened || !result.state) return
        session.userState = result.state
        root.preferencesReady()
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
          session.userState = result.state || session.userState
          root.stateAccepted()
          if (result.markedRead !== undefined) {
            var marked = Number(result.markedRead || 0)
            session.statusDetail = marked > 0
              ? "Marked " + marked + " stor" + (marked === 1 ? "y" : "ies") + " read in this section."
              : "This filtered section has no unread stories."
          }
          session.requestProjection()
        } else {
          session.feedStatus = "Failed"
          session.statusDetail = result.message || "Local state could not be changed."
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
          session.userState = result.state || session.userState
          if (root.opened) session.requestProjection("preserve")
        } else if (result.status === "stale-event") {
          session.userState = result.state || session.userState
          if (root.opened) session.requestProjection("preserve")
        } else if (root.opened) {
          session.feedStatus = "Failed"
          session.statusDetail = result.message || "Reading state could not be changed."
        }
      }
    }
    onExited: function() {
      root.readChangeInFlight = false
      Qt.callLater(root.flushReadChanges)
    }
  }

  Process { id: openSourceProc; stdout: StdioCollector { waitForEnd: true } }
}
