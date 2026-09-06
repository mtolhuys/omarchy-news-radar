import QtQuick
import QtQuick.Layouts
import qs.Commons

GridLayout {
  id: root
  property var briefing: ({})
  property bool busy: false
  property string message: ""
  property alias newButton: nextBriefing
  property alias finishButton: finish
  readonly property bool canPrepare: !briefing.initialized || briefing.hasNewStories
    || briefing.expiredEvents > 0
  signal newRequested()
  signal refreshRequested()
  signal finishRequested()
  signal navigationRequested(int direction)
  columns: 1
  columnSpacing: Style.spacing.panelGap
  rowSpacing: Style.spacing.sm

  function controlTargets() {
    return [finish, nextBriefing].filter(function(item) { return item.visible && item.enabled })
  }

  ColumnLayout {
    Layout.fillWidth: true
    spacing: Style.spacing.labelGap
    Text {
      Layout.fillWidth: true
      text: root.briefing.initialized && root.briefing.complete
        ? "You’re caught up with this briefing."
        : "Your briefing"
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
      Layout.fillWidth: true
      text: root.message || (root.briefing.initialized
        ? (root.briefing.total > 0
          ? root.briefing.remaining + " of " + root.briefing.total + " items left. "
          : "No unread stories were selected. ")
          + (root.briefing.hasNewStories
            ? "More stories are available for a new briefing."
            : "A new briefing will be available when unread stories arrive. Explore any section whenever you like.")
          + (root.briefing.expiredEvents > 0
            ? " " + root.briefing.expiredEvents + " earlier updates have left the live edition."
            : "")
        : "Preparing a short selection from your cached news…")
      textFormat: Text.PlainText
      color: root.message ? Color.urgent : Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      wrapMode: Text.WordWrap
      Accessible.role: Accessible.StaticText
      Accessible.name: text
    }
  }
  Flow {
    Layout.fillWidth: true
    Layout.preferredHeight: childrenRect.height
    spacing: Style.spacing.controlGap
    RadarButton {
      id: finish
      managesTab: true
      onTabRequested: function(direction) { root.navigationRequested(direction) }
      visible: root.briefing.initialized && root.briefing.remaining > 0
      label: "Mark briefing read"
      tooltipText: "Mark only the updates included in this briefing read (A)"
      enabled: !root.busy
      onClicked: root.finishRequested()
    }
    RadarButton {
      id: nextBriefing
      managesTab: true
      onTabRequested: function(direction) { root.navigationRequested(direction) }
      label: root.canPrepare
        ? (root.briefing.initialized ? "New briefing" : "Prepare briefing")
        : "Check for new stories"
      tooltipText: root.canPrepare
        ? "Choose a new short briefing from unread stories. Skipped stories stay unread."
        : "Refresh the public edition and look for unread briefing candidates."
      enabled: !root.busy
      onClicked: root.canPrepare ? root.newRequested() : root.refreshRequested()
    }
  }
}
