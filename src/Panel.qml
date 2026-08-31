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

  readonly property string runtimeBuildIdentity: "news-radar-0.1.0+window-1"
  readonly property string helperPath: manifest && manifest.__sourceDir
    ? String(manifest.__sourceDir) + "/bin/news-radar-client" : ""
  readonly property string pluginId: manifest && manifest.id
    ? String(manifest.id) : "io.github.mtolhuys.news-radar"

  property bool opened: false
  property bool closingFromHost: false
  readonly property string compositorWindowTitle: "Omarchy News Radar"
  property string sessionIdentity: ""
  property string sessionThrough: ""
  property var cachedFeed: null
  property var userState: ({
    schemaVersion: 3,
    seenThrough: "1970-01-01T00:00:00Z",
    saved: ({}),
    preferences: ({
      barVisible: true,
      imagesVisible: true,
      interests: [],
      sectionFilters: ({})
    })
  })
  property var installedPluginIds: []
  property var stories: []
  property var counts: ({})
  property int sectionIndex: 0
  property int selectedIndex: 0
  property string feedStatus: "First use"
  property string statusDetail: "No validated cache yet. Radar will try one bounded refresh."
  property string sourceHealth: "No validated source status"
  property string generatedAt: ""
  property string editionMode: "published"
  property bool refreshing: false
  property bool pendingProjection: false
  property bool preferencesOpen: false
  property bool filtersOpen: false
  property string windowIntegrationStatus: "idle"
  property int totalStories: 0
  property bool hasMoreStories: false
  property string filterSummary: "No extra filters"
  property string sectionRule: ""
  property var filterOptions: []
  property int pageSize: 12
  property var sectionLimits: ({
    "front-page": 12,
    "for-you": 12,
    "core": 12,
    "plugins": 12,
    "community": 12,
    "saved": 12
  })

  readonly property var preferences: userState && userState.preferences
    ? userState.preferences : ({ barVisible: true, imagesVisible: true, interests: [] })

  readonly property var sections: [
    { id: "front-page", label: "Front Page" },
    { id: "for-you", label: "For You" },
    { id: "core", label: "Core" },
    { id: "plugins", label: "Plugins" },
    { id: "community", label: "Community" },
    { id: "saved", label: "Saved" }
  ]
  readonly property string currentSection: sections[sectionIndex].id
  readonly property var selectedStory: selectedIndex >= 0 && selectedIndex < stories.length
    ? stories[selectedIndex] : null
  readonly property var currentFilter: preferences.sectionFilters
    && preferences.sectionFilters[currentSection]
      ? preferences.sectionFilters[currentSection]
      : ({ period: "all", significance: "all", unreadOnly: false, imagesOnly: false, types: [] })
  readonly property int availableImageCount: countEditionImages(cachedFeed)
  readonly property bool anyHelperRunning: readProc.running || refreshProc.running || projectProc.running
    || installedProc.running || stateProc.running || openSourceProc.running || windowProc.running

  function runtimeIdentity() {
    return runtimeBuildIdentity
  }

  function debugState() {
    return JSON.stringify({
      build: runtimeBuildIdentity,
      opened: opened,
      section: currentSection,
      selectedIndex: selectedIndex,
      selectedTitle: selectedStory ? selectedStory.title : "",
      selectedHasImage: selectedStory ? !!selectedStory.imageUrl : false,
      selectedMetricsText: selectedStory ? String(selectedStory.metricsText || "") : "",
      selectedIsNew: selectedStory ? selectedStory.isNew === true : false,
      storyCount: stories.length,
      status: feedStatus,
      editionMode: editionMode,
      availableImageCount: availableImageCount,
      refreshing: refreshing,
      helperRunning: anyHelperRunning,
      searchFocused: searchField.activeFocus,
      sessionThrough: sessionThrough,
      preferencesOpen: preferencesOpen,
      filtersOpen: filtersOpen,
      totalStories: totalStories,
      hasMoreStories: hasMoreStories,
      filterSummary: filterSummary,
      windowVisible: panelWindow.visible,
      windowWidth: panelWindow.width,
      windowHeight: panelWindow.height,
      maximized: panelWindow.maximized,
      minimized: panelWindow.minimized,
      windowIntegrationStatus: windowIntegrationStatus
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
  function filterGeometry() { return itemGeometry(filterButton, filterButton.visible) }
  function loadMoreGeometry() {
    return itemGeometry(storyList.footerItem, !!storyList.footerItem && hasMoreStories)
  }
  function filterUnreadGeometry() { return itemGeometry(unreadFilterButton, unreadFilterButton.visible) }
  function filterResetGeometry() { return itemGeometry(filterResetButton, filterResetButton.visible) }

  function tuneNewspaperGeometry() {
    return itemGeometry(barPreferenceButton, preferencesOpen && barPreferenceButton.visible)
  }

  function startProcess(process, argumentsList) {
    if (!helperPath) {
      feedStatus = "Failed"
      statusDetail = "The bundled client helper path is unavailable."
      return
    }
    if (process.running) process.running = false
    process.command = [helperPath].concat(argumentsList)
    Qt.callLater(function() { if (root.opened || process === stateProc || process === openSourceProc) process.running = true })
  }

  function countEditionImages(feed) {
    if (!feed || !Array.isArray(feed.events)) return 0
    var count = 0
    for (var index = 0; index < feed.events.length; index++)
      if (feed.events[index] && feed.events[index].image) count++
    return count
  }

  function open(payloadJson) {
    closingFromHost = false
    sessionIdentity = String(Date.now()) + "-" + String(Math.random()).slice(2)
    sessionThrough = ""
    feedStatus = "Loading cache"
    statusDetail = "Reading the last-known-good local edition."
    opened = true
    windowIntegrationStatus = "waiting"
    preferencesOpen = false
    filtersOpen = false
    panelWindow.visible = true
    selectedIndex = 0
    startProcess(windowProc, ["ensure-window-floating"])
    startProcess(readProc, ["read"])
    startProcess(installedProc, ["installed"])
    Qt.callLater(function() {
      if (root.opened) {
        navigationFocus.forceActiveFocus()
      }
    })
  }

  function persistSeen() {
    if (!helperPath || !sessionThrough) return
    Quickshell.execDetached([helperPath, "mark-seen", "--through", sessionThrough])
  }

  function stopOwnedProcesses() {
    searchTimer.stop()
    readProc.running = false
    refreshProc.running = false
    projectProc.running = false
    installedProc.running = false
    stateProc.running = false
    openSourceProc.running = false
    windowProc.running = false
    refreshing = false
  }

  function close() {
    closingFromHost = true
    persistSeen()
    opened = false
    preferencesOpen = false
    filtersOpen = false
    stopOwnedProcesses()
    panelWindow.visible = false
    closingFromHost = false
  }

  function dismiss() {
    if (shell && typeof shell.hide === "function") shell.hide(pluginId)
    else close()
  }

  function handleEscape() {
    if (filtersOpen) {
      filtersOpen = false
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
    editionMode = String(result.editionMode || "published")
    if (!interestField.activeFocus)
      interestField.text = (userState.preferences && userState.preferences.interests || []).join(", ")
    if (result.feed) {
      cachedFeed = result.feed
      generatedAt = String(result.feed.generatedAt || "")
      sourceHealth = RadarModel.sourceHealth(result.feed)
      sessionThrough = RadarModel.greatestTimestamp(result.feed.events || [])
      feedStatus = "Cached"
      statusDetail = "Showing the validated local edition while Radar refreshes."
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

  function handleRefresh(raw) {
    var result = RadarModel.parseResponse(raw)
    refreshing = false
    editionMode = String(result.editionMode || editionMode)
    if (result.feed) {
      cachedFeed = result.feed
      generatedAt = String(result.feed.generatedAt || "")
      sourceHealth = RadarModel.sourceHealth(result.feed)
      requestProjection()
    }
    if (result.status === "local-current") {
      feedStatus = "Local live edition"
      statusDetail = "Collected from the live official sources by make local-latest. Run it again whenever you want a newer local edition."
    } else if (result.status === "current") {
      feedStatus = sourceHealth.indexOf("Partial") === 0 ? "Source partial" : "Current"
      statusDetail = sourceHealth.indexOf("Partial") === 0
        ? "The valid edition is readable; unavailable sources are named above."
        : "Refresh completed and the validated cache is current."
    } else if (result.status === "invalid-feed") {
      feedStatus = "Invalid feed"
      statusDetail = result.cachePreserved
        ? "Radar rejected the candidate and preserved the last-known-good edition."
        : "Radar rejected the candidate. Retry after the feed is repaired."
    } else {
      feedStatus = result.feed ? "Offline" : "No cache and failed"
      statusDetail = result.feed
        ? "Refresh failed; the last-known-good edition remains readable."
        : "Refresh failed and no validated cache exists. Retry when online."
    }
  }

  function handleInstalled(raw) {
    var result = RadarModel.parseResponse(raw)
    installedPluginIds = result.status === "ok" && Array.isArray(result.pluginIds)
      ? result.pluginIds : []
    requestProjection()
  }

  function requestProjection() {
    if (!opened) return
    if (projectProc.running) {
      pendingProjection = true
      return
    }
    pendingProjection = false
    startProcess(projectProc, [
      "project",
      "--section", currentSection,
      "--installed-json", JSON.stringify(installedPluginIds),
      "--query", searchField.text,
      "--limit", String(Number(sectionLimits[currentSection] || pageSize))
    ])
  }

  function handleProjection(raw) {
    var result = RadarModel.parseResponse(raw)
    if (result.status === "ok" || result.status === "first-use") {
      stories = result.events || []
      counts = result.counts || ({})
      totalStories = Number(result.totalEvents || 0)
      hasMoreStories = result.hasMore === true
      filterSummary = String(result.filterSummary || "No extra filters")
      sectionRule = String(result.sectionRule || "")
      filterOptions = result.filterOptions || []
      selectedIndex = stories.length ? Math.min(Math.max(0, selectedIndex), stories.length - 1) : -1
    } else {
      stories = []
      totalStories = 0
      hasMoreStories = false
      selectedIndex = -1
      feedStatus = "Failed"
      statusDetail = result.message || "The local reading model could not be built."
    }
  }

  function refreshFeed() {
    if (refreshing || !opened) return
    refreshing = true
    feedStatus = cachedFeed ? "Refreshing" : "First use"
    statusDetail = cachedFeed
      ? "The cached edition remains readable during one bounded refresh."
      : "Fetching the first bounded edition."
    startProcess(refreshProc, ["refresh"])
  }

  function selectSection(index) {
    if (index < 0 || index >= sections.length) return
    sectionIndex = index
    selectedIndex = 0
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
    if (!hasMoreStories || projectProc.running) return
    var limits = Object.assign({}, sectionLimits)
    limits[currentSection] = Math.min(500, Number(limits[currentSection] || pageSize) + pageSize)
    sectionLimits = limits
    requestProjection()
  }

  function moveSelection(delta) {
    if (!stories.length) return
    selectedIndex = Math.max(0, Math.min(stories.length - 1, selectedIndex + delta))
    storyList.positionViewAtIndex(selectedIndex, ListView.Contain)
  }

  function openSelected() {
    if (!selectedStory) return
    openUrl(String(selectedStory.source.url))
  }

  function openUrl(url) {
    startProcess(openSourceProc, ["open-source", "--url", String(url)])
  }

  function toggleSaved() {
    if (!selectedStory || stateProc.running) return
    startProcess(stateProc, ["toggle-saved", "--event-id", String(selectedStory.id)])
  }

  function setBooleanPreference(name, value) {
    if (stateProc.running) return
    var argument = name === "barVisible" ? "--bar-visible" : "--images-visible"
    startProcess(stateProc, ["set-preferences", argument, value ? "true" : "false"])
  }

  function normalizedInterests() {
    var raw = interestField.text.split(",")
    var result = []
    for (var index = 0; index < raw.length && result.length < 12; index++) {
      var value = String(raw[index]).toLowerCase().trim().replace(/\s+/g, " ")
      if (value && result.indexOf(value) === -1) result.push(value)
    }
    return result
  }

  function saveInterests() {
    if (stateProc.running) return
    startProcess(stateProc, ["set-preferences", "--interests-json", JSON.stringify(normalizedInterests())])
  }

  function showPreferences() {
    interestField.text = (preferences.interests || []).join(", ")
    preferencesOpen = true
    Qt.callLater(function() { interestField.forceActiveFocus() })
  }

  function showFilters() {
    filtersOpen = true
    Qt.callLater(function() { filterDoneButton.forceActiveFocus() })
  }

  function updateFilter(name, value) {
    if (stateProc.running) return
    var next = {
      period: currentFilter.period,
      significance: currentFilter.significance,
      unreadOnly: currentFilter.unreadOnly,
      imagesOnly: currentFilter.imagesOnly,
      types: (currentFilter.types || []).slice()
    }
    next[name] = value
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
    if (stateProc.running) return
    resetSectionLimit(currentSection)
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

  Process {
    id: readProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleRead(text) }
  }

  Process {
    id: refreshProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleRefresh(text) }
    onExited: if (root.refreshing && exitCode !== 0) root.refreshing = false
  }

  Process {
    id: installedProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleInstalled(text) }
  }

  Process {
    id: projectProc
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.handleProjection(text) }
    onExited: if (root.pendingProjection) Qt.callLater(root.requestProjection)
  }

  Process {
    id: stateProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (result.status === "ok") {
          root.userState = result.state || root.userState
          root.requestProjection()
        } else {
          root.feedStatus = "Failed"
          root.statusDetail = result.message || "Saved state could not be changed."
        }
      }
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

  Timer {
    id: searchTimer
    interval: 160
    repeat: false
    onTriggered: root.requestProjection()
  }

  FloatingWindow {
    id: panelWindow
    visible: false
    title: root.compositorWindowTitle
    color: Color.popups.background
    implicitWidth: Style.space(1120)
    implicitHeight: Style.space(720)
    minimumSize: Qt.size(Style.space(720), Style.space(480))

    onVisibleChanged: {
      if (!visible && root.opened && !root.closingFromHost) root.dismiss()
    }

    FocusScope {
      id: keySurface
      anchors.fill: parent
      focus: true
      Keys.onEscapePressed: root.handleEscape()
      Keys.onPressed: function(event) {
        if (root.filtersOpen || root.preferencesOpen) return
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
        if ((event.text || "").toLowerCase() === "r") {
          root.refreshFeed(); event.accepted = true; return
        }
        if (event.text === "/") {
          searchField.forceActiveFocus(); event.accepted = true; return
        }
        if (event.key === Qt.Key_Home) {
          root.selectedIndex = root.stories.length ? 0 : -1; event.accepted = true; return
        }
        if (event.key === Qt.Key_End) {
          root.selectedIndex = root.stories.length - 1
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
        if (numeric >= 1 && numeric <= 6) {
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

          RowLayout {
            Layout.fillWidth: true
            spacing: Style.spacing.controlGap

            Item {
              Layout.fillWidth: true
              implicitHeight: titleStack.implicitHeight

              ColumnLayout {
                id: titleStack
                anchors.fill: parent
                spacing: Style.spacing.xs

                Text {
                  text: "OMARCHY NEWS RADAR"
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.display
                  font.bold: true
                  font.letterSpacing: Style.spaceReal(1)
                  Accessible.role: Accessible.Heading
                  Accessible.name: text
                }

                Text {
                  Layout.fillWidth: true
                  text: root.feedStatus + " · " + root.sourceHealth
                  textFormat: Text.PlainText
                  color: root.feedStatus === "Offline" || root.feedStatus === "Invalid feed" || root.feedStatus === "Failed"
                    ? Color.urgent : Color.muted
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  elide: Text.ElideRight
                  Accessible.role: Accessible.StaticText
                  Accessible.name: "Refresh status: " + text
                }
              }

              MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                cursorShape: Qt.SizeAllCursor
                onPressed: panelWindow.startSystemMove()
                onDoubleClicked: panelWindow.maximized = !panelWindow.maximized
              }
            }

            RadarButton {
              label: root.refreshing ? "Refreshing…" : "Refresh"
              enabled: !root.refreshing
              onClicked: root.refreshFeed()
            }

            RadarButton {
              label: "Tune"
              onClicked: root.showPreferences()
            }

            RadarButton {
              label: "Minimize"
              onClicked: panelWindow.minimized = true
            }

            RadarButton {
              id: maximizeButton
              label: panelWindow.maximized ? "Restore" : "Maximize"
              onClicked: panelWindow.maximized = !panelWindow.maximized
            }

            RadarButton {
              id: closeButton
              label: "Close"
              onClicked: root.dismiss()
            }
          }

          Text {
            Layout.fillWidth: true
            visible: text !== ""
            text: root.statusDetail
            textFormat: Text.PlainText
            color: Color.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.bodySmall
            elide: Text.ElideRight
            Accessible.role: Accessible.StaticText
            Accessible.name: text
          }

          TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search this validated edition  /"
            color: Color.popups.text
            placeholderTextColor: Color.muted
            selectionColor: Style.selectionFill
            selectedTextColor: Color.popups.text
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            leftPadding: Style.spacing.controlPaddingX
            rightPadding: Style.spacing.controlPaddingX
            topPadding: Style.spacing.inputPaddingY
            bottomPadding: Style.spacing.inputPaddingY
            Accessible.name: "Search the current edition"
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
                color: Color.muted
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
                  label: modelData.label
                  count: Number(root.counts[modelData.id] || 0)
                  selected: root.sectionIndex === index
                  onClicked: root.selectSection(index)
                }
              }

              Item { Layout.fillHeight: true }

              Text {
                Layout.fillWidth: true
                text: "Tab/Shift+Tab sections\n1–6 sections\nj/k stories\no source\ns save\nr refresh"
                textFormat: Text.PlainText
                color: Color.muted
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }
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

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: root.sections[root.sectionIndex].label.toUpperCase()
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.heading
                  font.bold: true
                  Accessible.role: Accessible.Heading
                  Accessible.name: text
                }

                RadarButton {
                  id: filterButton
                  label: "⚙ Filters"
                  selected: root.filterSummary !== "No extra filters"
                  onClicked: root.showFilters()
                }

                RadarButton {
                  visible: keySurface.narrow
                  label: root.selectedStory && root.selectedStory.isSaved ? "Unsave" : "Save"
                  enabled: !!root.selectedStory
                  onClicked: root.toggleSaved()
                }
                RadarButton {
                  visible: keySurface.narrow
                  label: "Open source"
                  enabled: !!root.selectedStory
                  onClicked: root.openSelected()
                }
              }

              Text {
                Layout.fillWidth: true
                text: root.filterSummary + " · " + root.totalStories + " stories"
                textFormat: Text.PlainText
                color: Color.muted
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                elide: Text.ElideRight
                Accessible.role: Accessible.StaticText
                Accessible.name: "Active section filters: " + text
              }

              ListView {
                id: storyList
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: root.stories
                currentIndex: root.selectedIndex
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
                  onHovered: root.selectedIndex = index
                  onActivated: root.selectedIndex = index
                }

                footer: Item {
                  width: storyList.width
                  height: root.stories.length ? Style.space(54) : 0
                  visible: root.stories.length > 0

                  RadarButton {
                    id: loadMoreButton
                    anchors.centerIn: parent
                    visible: root.hasMoreStories
                    label: "Load more (" + Math.max(0, root.totalStories - root.stories.length) + " remaining)"
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
                    color: Color.muted
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                  }
                }

                Text {
                  anchors.centerIn: parent
                  visible: root.stories.length === 0
                  width: parent.width - Style.spacing.panelPadding * 2
                  text: searchField.text
                    ? "No stories match the current filter. Clear search to recover."
                    : root.cachedFeed
                      ? "This section is empty in the current bounded edition."
                      : "No cached edition is available yet. Retry when online."
                  textFormat: Text.PlainText
                  color: Color.muted
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  horizontalAlignment: Text.AlignHCenter
                  wrapMode: Text.WordWrap
                  Accessible.role: Accessible.StaticText
                  Accessible.name: text
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
                  color: Color.muted
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
                  visible: !!root.selectedStory && !!root.selectedStory.metricsText
                  width: parent.width
                  text: visible ? "METRICS\n" + root.selectedStory.metricsText
                    + (root.selectedStory.metricsObservedAt ? "\nOBSERVED  " + root.selectedStory.metricsObservedAt : "") : ""
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.bodySmall
                  font.bold: true
                  wrapMode: Text.WordWrap
                  Accessible.role: Accessible.StaticText
                  Accessible.name: text
                }

                Text {
                  visible: !!root.selectedStory && !!root.selectedStory.metricsCaveat
                  width: parent.width
                  text: visible ? root.selectedStory.metricsCaveat : ""
                  textFormat: Text.PlainText
                  color: Color.muted
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  wrapMode: Text.WordWrap
                }

                Repeater {
                  model: root.selectedStory && root.selectedStory.metricSources
                    ? root.selectedStory.metricSources : []
                  RadarButton {
                    required property var modelData
                    label: "Open " + modelData.label.toLowerCase() + " source"
                    onClicked: root.openUrl(String(modelData.url))
                  }
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
                  color: Color.muted
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

                Row {
                  spacing: Style.spacing.controlGap
                  RadarButton {
                    label: root.selectedStory && root.selectedStory.isSaved ? "Unsave" : "Save"
                    enabled: !!root.selectedStory
                    onClicked: root.toggleSaved()
                  }
                  RadarButton {
                    label: "Open source"
                    enabled: !!root.selectedStory
                    onClicked: root.openSelected()
                  }
                }
              }
            }
          }

          Text {
            Layout.fillWidth: true
            text: (root.generatedAt ? "Edition " + root.generatedAt : "No edition generated")
              + " · v0.1.0 · independent community project"
            textFormat: Text.PlainText
            color: Color.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight
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
                text: "Preferences stay on this machine and are never sent to the feed or its sources."
                textFormat: Text.PlainText
                color: Color.muted
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
                color: Color.muted
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }

              Text {
                Layout.fillWidth: true
                text: "Interests · comma-separated words or phrases"
                color: Color.popups.text
                font.family: Style.font.family
                font.pixelSize: Style.font.bodySmall
              }

              TextField {
                id: interestField
                Layout.fillWidth: true
                placeholderText: "themes, gaming, security, quickshell"
                color: Color.popups.text
                placeholderTextColor: Color.muted
                selectionColor: Style.selectionFill
                selectedTextColor: Color.popups.text
                font.family: Style.font.family
                font.pixelSize: Style.font.body
                Accessible.name: "Private news interests"
                background: BorderSurface {
                  color: Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
                  radius: Style.cornerRadius
                  borderSpec: Border.controlSpec(interestField.activeFocus ? "focus" : "normal", Color.foreground, Color.accent, Color.urgent)
                }
                Keys.onReturnPressed: root.saveInterests()
                Keys.onEnterPressed: root.saveInterests()
                Keys.onEscapePressed: {
                  root.preferencesOpen = false
                  navigationFocus.forceActiveFocus()
                }
              }

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "For You combines these interests with enabled plugin IDs."
                  color: Color.muted
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  wrapMode: Text.WordWrap
                }
                RadarButton { label: "Apply interests"; onClicked: root.saveInterests() }
              }
            }
          }
        }

        Rectangle {
          anchors.fill: parent
          visible: root.filtersOpen
          z: 21
          color: Qt.rgba(Color.background.r, Color.background.g, Color.background.b, 0.82)
          MouseArea { anchors.fill: parent; onClicked: root.filtersOpen = false }

          BorderSurface {
            anchors.centerIn: parent
            width: Math.min(parent.width - Style.spacing.panelPadding * 2, Style.space(760))
            height: Math.min(parent.height - Style.spacing.panelPadding * 2, Style.space(520))
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
                  text: "⚙ " + root.sections[root.sectionIndex].label.toUpperCase() + " FILTERS"
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
                    root.filtersOpen = false
                    navigationFocus.forceActiveFocus()
                  }
                }
              }

              Text {
                Layout.fillWidth: true
                text: "BUILT-IN SECTION RULE\n" + root.sectionRule
                textFormat: Text.PlainText
                color: Color.muted
                font.family: Style.font.family
                font.pixelSize: Style.font.bodySmall
                wrapMode: Text.WordWrap
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
                Text {
                  Layout.fillWidth: true
                  text: "Local-only · " + root.filterSummary
                  textFormat: Text.PlainText
                  color: Color.muted
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  elide: Text.ElideRight
                }
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
