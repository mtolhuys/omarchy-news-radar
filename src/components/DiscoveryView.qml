import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons

// A presentation of backend-prepared facts. The finite briefing and discovery
// remain separate: browsing a project never adds an item to the briefing.
Flickable {
  id: root
  property bool setupMode: false
  property var home: ({})
  property var setup: []
  property var stories: []
  property var briefing: ({})
  property var insights: ({})
  property bool busy: false
  property bool imagesVisible: true
  property string message: ""
  property bool searching: false
  property int selectedCard: 0
  property alias notice: briefNotice
  function resetRoute() { selectedCard = 0; contentY = 0 }
  onSetupModeChanged: Qt.callLater(resetRoute)
  onVisibleChanged: if (visible) Qt.callLater(resetRoute)
  signal storyRequested(int index)
  signal detailRequested(var item)
  signal browseRequested()
  signal newRequested()
  signal finishRequested()
  signal navigationRequested(int direction)
  contentWidth: width
  contentHeight: body.implicitHeight
  clip: true
  boundsBehavior: Flickable.StopAtBounds
  ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

  readonly property var groups: setupMode ? [
    { title: "My setup", hint: "Your enabled plugins, installed versions, and published release notes.", items: setup, kind: "project" }
  ] : [
    { title: "", hint: "", items: stories, kind: "story" },
    { title: "Changes for your setup", hint: "Published releases newer than the version installed here.", items: home.setupUpdates || [], kind: "project" },
    { title: "Worth exploring", hint: "Reviewed collections, with the reasons and original sources.", items: home.featuredCollections || [], kind: "collection" },
    { title: "Discover a project", hint: "A few source-linked projects from the current edition.", items: home.discoveries || [], kind: "project" }
  ]

  function cards() {
    var items = []
    for (var i = 0; i < groupsRepeater.count; i++) {
      var section = groupsRepeater.itemAt(i)
      if (section) items = items.concat(section.cards())
    }
    return items
  }

  function controlTargets() {
    var targets = setupMode ? [] : briefNotice.controlTargets()
    return targets.concat(cards(), [browseButton]).filter(function(item) { return item.visible && item.enabled })
  }

  function revealControl(item) {
    if (!item) return
    var top = item.mapToItem(contentItem, 0, 0).y
    if (top < contentY || item.height > height) contentY = top
    else if (top + item.height > contentY + height) contentY = top + item.height - height
    contentY = Math.max(0, Math.min(contentY, contentHeight - height))
  }

  function moveSelection(delta) {
    var choices = cards()
    if (!choices.length) return
    selectedCard = Math.max(0, Math.min(selectedCard + delta, choices.length - 1))
    revealControl(choices[selectedCard])
  }

  function activateSelected() {
    var choices = cards()
    if (choices.length) choices[Math.max(0, Math.min(selectedCard, choices.length - 1))].activated()
  }

  function cardIndex(item) { return cards().indexOf(item) }

  ColumnLayout {
    id: body
    width: root.width - Style.space(12)
    spacing: Style.spacing.lg

    Text {
      Layout.fillWidth: true
      text: root.setupMode ? "Know what is running." : "Around Omarchy"
      textFormat: Text.PlainText
      color: Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.display
      font.bold: true
      wrapMode: Text.WordWrap
    }
    Text {
      Layout.fillWidth: true
      text: root.setupMode
        ? "Release context for this computer. Follow projects or mute their future news in a project's details."
        : "Your short briefing, useful changes, and something new to try."
      textFormat: Text.PlainText
      color: Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      wrapMode: Text.WordWrap
    }
    BriefingNotice {
      id: briefNotice
      visible: !root.setupMode
      Layout.fillWidth: true
      briefing: root.briefing
      busy: root.busy
      message: root.message
      onNewRequested: root.newRequested()
      onFinishRequested: root.finishRequested()
      onNavigationRequested: function(direction) { root.navigationRequested(direction) }
    }
    Repeater {
      id: groupsRepeater
      model: root.groups
      ColumnLayout {
        id: section
        required property var modelData
        Layout.fillWidth: true
        visible: modelData.items.length > 0
        spacing: Style.spacing.sm
        function cards() {
          var result = []
          for (var i = 0; i < cardRepeater.count; i++) {
            var item = cardRepeater.itemAt(i)
            if (item) result.push(item)
          }
          return result
        }
        Text {
          Layout.fillWidth: true
          visible: text !== ""
          text: section.modelData.title
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.heading
          font.bold: true
          wrapMode: Text.WordWrap
        }
        Text {
          Layout.fillWidth: true
          visible: text !== ""
          text: section.modelData.hint
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }
        GridLayout {
          Layout.fillWidth: true
          columns: width >= Style.space(640) ? 2 : 1
          rowSpacing: Style.spacing.sm
          columnSpacing: Style.spacing.sm
          Repeater {
            id: cardRepeater
            model: section.modelData.items
            InsightCard {
              id: entry
              required property var modelData
              required property int index
              readonly property string label: heading
              readonly property string entryKind: section.modelData.kind
              Layout.fillWidth: true
              Layout.alignment: Qt.AlignTop
              heading: String(modelData.title || modelData.name || "")
              detail: String(section.modelData.kind === "story"
                ? modelData.listSummary || modelData.summary || ""
                : modelData.summary || modelData.description || modelData.coverageLabel || "")
              eyebrow: section.modelData.kind === "story"
                ? String(modelData.briefingReasonLabel || "Briefing") + " · " + Number(modelData.briefingEventCount || 1) + (Number(modelData.briefingEventCount || 1) === 1 ? " update" : " updates")
                : String(modelData.comparisonLabel || (section.modelData.kind === "collection" ? "Reviewed collection" : "Project"))
              imageUrl: root.imagesVisible ? String(modelData.imageUrl || "") : ""
              selected: root.cardIndex(entry) === root.selectedCard
              onActivated: {
                root.selectedCard = root.cardIndex(entry)
                if (section.modelData.kind === "story") root.storyRequested(index)
                else root.detailRequested(modelData)
              }
              onActiveFocusChanged: if (activeFocus) {
                root.selectedCard = root.cardIndex(entry)
                root.revealControl(entry)
              }
              Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
                  root.navigationRequested(event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier) ? -1 : 1)
                  event.accepted = true
                }
              }
            }
          }
        }
      }
    }
    Text {
      Layout.fillWidth: true
      visible: root.setupMode && root.setup.length === 0
      text: root.insights.installedFactsAvailable === false
        ? "Installed plugin details are unavailable. Refresh to retry; your news and saved stories are still here."
        : root.searching ? "No enabled plugins match this search."
          : "No enabled third-party plugins are available here yet. Explore the Plugins section to find one."
      textFormat: Text.PlainText
      color: Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      wrapMode: Text.WordWrap
    }
    RadarButton {
      id: browseButton
      label: root.setupMode ? "Read news for your setup" : "Browse all plugins"
      managesTab: true
      onTabRequested: function(direction) { root.navigationRequested(direction) }
      onClicked: root.browseRequested()
    }
  }
}
