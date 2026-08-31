import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
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

  readonly property string runtimeBuildIdentity: "news-radar-0.1.0+panel-3"
  readonly property string helperPath: manifest && manifest.__sourceDir
    ? String(manifest.__sourceDir) + "/bin/news-radar-client" : ""
  readonly property string pluginId: manifest && manifest.id
    ? String(manifest.id) : "io.github.mtolhuys.news-radar"

  property bool opened: false
  property string sessionIdentity: ""
  property string sessionThrough: ""
  property var cachedFeed: null
  property var userState: ({
    schemaVersion: 2,
    seenThrough: "1970-01-01T00:00:00Z",
    saved: ({}),
    preferences: ({ barVisible: true, imagesVisible: true, interests: [] })
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
  readonly property int availableImageCount: countEditionImages(cachedFeed)
  readonly property bool anyHelperRunning: readProc.running || refreshProc.running || projectProc.running
    || installedProc.running || stateProc.running || openSourceProc.running

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
      selectedIsNew: selectedStory ? selectedStory.isNew === true : false,
      storyCount: stories.length,
      status: feedStatus,
      editionMode: editionMode,
      availableImageCount: availableImageCount,
      refreshing: refreshing,
      helperRunning: anyHelperRunning,
      searchFocused: searchField.activeFocus,
      sessionThrough: sessionThrough,
      preferencesOpen: preferencesOpen
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
    sessionIdentity = String(Date.now()) + "-" + String(Math.random()).slice(2)
    sessionThrough = ""
    feedStatus = "Loading cache"
    statusDetail = "Reading the last-known-good local edition."
    opened = true
    preferencesOpen = false
    selectedIndex = 0
    startProcess(readProc, ["read"])
    startProcess(installedProc, ["installed"])
    Qt.callLater(function() { if (root.opened) navigationFocus.forceActiveFocus() })
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
    refreshing = false
  }

  function close() {
    persistSeen()
    opened = false
    preferencesOpen = false
    stopOwnedProcesses()
  }

  function dismiss() {
    if (shell && typeof shell.hide === "function") shell.hide(pluginId)
    else close()
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
      "--query", searchField.text
    ])
  }

  function handleProjection(raw) {
    var result = RadarModel.parseResponse(raw)
    if (result.status === "ok" || result.status === "first-use") {
      stories = result.events || []
      counts = result.counts || ({})
      selectedIndex = stories.length ? Math.min(Math.max(0, selectedIndex), stories.length - 1) : -1
    } else {
      stories = []
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

  function moveSelection(delta) {
    if (!stories.length) return
    selectedIndex = Math.max(0, Math.min(stories.length - 1, selectedIndex + delta))
    storyList.positionViewAtIndex(selectedIndex, ListView.Contain)
  }

  function openSelected() {
    if (!selectedStory) return
    startProcess(openSourceProc, ["open-source", "--url", String(selectedStory.source.url)])
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

  Timer {
    id: searchTimer
    interval: 160
    repeat: false
    onTriggered: root.requestProjection()
  }

  PanelWindow {
    id: panelWindow
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "omarchy-news-radar"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

    Rectangle {
      anchors.fill: parent
      color: Qt.rgba(Color.background.r, Color.background.g, Color.background.b, 0.74)
      MouseArea { anchors.fill: parent; onClicked: root.dismiss() }
    }

    FocusScope {
      id: keySurface
      anchors.centerIn: parent
      width: Math.max(Style.space(320), Math.min(panelWindow.width - Style.gapsOut * 2, Style.space(1120)))
      height: Math.max(Style.space(420), Math.min(panelWindow.height - Style.gapsOut * 2, Style.space(720)))
      focus: true

      readonly property bool narrow: width < Style.space(860)

      Item {
        id: navigationFocus
        anchors.fill: parent
        focus: true

        Keys.onPressed: function(event) {
          if (root.preferencesOpen) {
            if (event.key === Qt.Key_Escape) {
              root.preferencesOpen = false
              navigationFocus.forceActiveFocus()
              event.accepted = true
            }
            return
          }
          if (event.key === Qt.Key_Escape || (event.text || "").toLowerCase() === "q") {
            root.dismiss(); event.accepted = true; return
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
            root.selectedIndex = root.stories.length - 1; event.accepted = true; return
          }
          var numeric = Number(event.text)
          if (numeric >= 1 && numeric <= 6) {
            root.selectSection(numeric - 1); event.accepted = true
          }
        }
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

            ColumnLayout {
              Layout.fillWidth: true
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
                text: "1–6 sections\nj/k stories\no source\ns save\nr refresh"
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
      }
    }
  }

  Component.onDestruction: stopOwnedProcesses()
}
