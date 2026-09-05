import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui
import "../Model.js" as RadarModel

ColumnLayout {
  id: root
  property var story: null
  property bool busy: false
  property bool expanded: false
  property real maximumHistoryHeight: Style.space(220)
  readonly property string groupId: story ? String(story.briefingGroupId || "") : ""
  property alias readButton: markGroup
  readonly property int historyIndex: history.currentIndex
  signal readRequested(string groupId)
  signal sourceRequested(var event)
  signal navigationRequested(int direction)
  spacing: Style.spacing.sm

  function controlTargets() {
    return [toggleHistory, markGroup, history].filter(function(item) { return item.visible && item.enabled })
  }

  onGroupIdChanged: {
    expanded = false
    history.currentIndex = 0
  }

  Text {
    Layout.fillWidth: true
    text: root.story ? String(root.story.briefingReasonLabel || "") : ""
    textFormat: Text.PlainText
    color: Color.accent
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
    wrapMode: Text.WordWrap
  }
  Flow {
    Layout.fillWidth: true
    Layout.preferredHeight: childrenRect.height
    spacing: Style.spacing.controlGap
    RadarButton {
      id: toggleHistory
      managesTab: true
      onTabRequested: function(direction) { root.navigationRequested(direction) }
      visible: !!root.story && root.story.briefingEventCount > 1
      label: (root.expanded ? "Hide " : "Show ")
        + (root.story ? root.story.briefingEventCount : 0) + " updates"
      onClicked: root.expanded = !root.expanded
    }
    RadarButton {
      id: markGroup
      managesTab: true
      onTabRequested: function(direction) { root.navigationRequested(direction) }
      visible: !!root.story && root.story.briefingEventCount > 1
      label: "Mark group read"
      tooltipText: "Mark these source-linked updates read; other stories stay unread"
      enabled: !root.busy && !!root.story && root.story.briefingUnreadCount > 0
      onClicked: root.readRequested(String(root.story.briefingGroupId))
    }
  }
  Text {
    Layout.fillWidth: true
    visible: !!root.story && root.story.briefingEventCount > 1
    text: root.story ? root.story.briefingUnreadCount + " updates unread in this group" : ""
    textFormat: Text.PlainText
    color: Color.popups.text
    font.family: Style.font.family
    font.pixelSize: Style.font.caption
    wrapMode: Text.WordWrap
  }
  ListView {
    id: history
    readonly property string label: "Update history"
    visible: root.expanded && !!root.story && root.story.briefingEventCount > 1
    Layout.fillWidth: true
    Layout.preferredHeight: visible ? Math.min(root.maximumHistoryHeight, count * Style.space(96)) : 0
    model: visible ? root.story.briefingEvents : []
    clip: true
    activeFocusOnTab: true
    currentIndex: 0
    keyNavigationEnabled: false
    spacing: Style.spacing.sm
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    Accessible.role: Accessible.List
    Accessible.name: "Updates in this group. Up and Down select an update; Enter opens its original source."
    Accessible.focusable: true
    onActiveFocusChanged: if (activeFocus && count > 0) {
      currentIndex = Math.max(0, Math.min(currentIndex, count - 1))
      positionViewAtIndex(currentIndex, ListView.Contain)
    }
    Keys.onPressed: function(event) {
      if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
        root.navigationRequested(event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier) ? -1 : 1)
        event.accepted = true
        return
      }
      if (!count) return
      if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
        root.sourceRequested(model[currentIndex])
        event.accepted = true
        return
      }
      var next = currentIndex
      if (event.key === Qt.Key_Down) next++
      else if (event.key === Qt.Key_Up) next--
      else if (event.key === Qt.Key_Home) next = 0
      else if (event.key === Qt.Key_End) next = count - 1
      else return
      currentIndex = Math.max(0, Math.min(next, count - 1))
      positionViewAtIndex(currentIndex, ListView.Contain)
      event.accepted = true
    }
    delegate: BorderSurface {
      id: historyRow
      required property var modelData
      required property int index
      width: history.width - Style.space(12)
      height: rowContent.implicitHeight + Style.spacing.sm * 2
      readonly property bool focused: history.activeFocus && history.currentIndex === index
      color: focused ? Style.focusFillFor(Color.foreground, Color.accent, Color.urgent) : "transparent"
      borderSpec: Border.controlSpec(focused ? "focus" : "normal", Color.foreground, Color.accent, Color.urgent)
      radius: Style.cornerRadius
      Accessible.role: Accessible.ListItem
      Accessible.name: modelData.title + (modelData.isUnread ? ". Unread" : ". Read")
      Accessible.selected: history.currentIndex === index
      ColumnLayout {
        id: rowContent
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Style.spacing.sm
        spacing: Style.spacing.labelGap
        Text {
          Layout.fillWidth: true
          text: historyRow.modelData.title
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }
        RowLayout {
          Layout.fillWidth: true
          Text {
            Layout.fillWidth: true
            text: RadarModel.humanDate(historyRow.modelData.occurredAt) + (historyRow.modelData.isUnread ? " · Unread" : " · Read")
            textFormat: Text.PlainText
            color: Color.popups.text
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            wrapMode: Text.WordWrap
          }
          RadarButton {
            label: "Source"
            activeFocusOnTab: false
            managesTab: true
            onTabRequested: function(direction) { root.navigationRequested(direction) }
            onClicked: root.sourceRequested(historyRow.modelData)
          }
        }
      }
    }
  }
}
