import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui

BorderSurface {
  id: root
  property bool busy: false
  property bool canStart: false
  property int storyCount: 0
  property string message: ""
  property real maximumHeight: Style.space(600)
  property alias startButton: startToday
  property alias browseButton: browse
  signal startTodayRequested()
  signal browseRequested()

  implicitHeight: Math.min(maximumHeight,
    copy.implicitHeight + choices.childrenRect.height + Style.spacing.panelGap + Style.spacing.panelPadding * 2)
  color: Color.popups.background
  radius: Style.cornerRadius
  borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)

  function focusChoice() {
    if (visible && !busy && browse.enabled) browse.forceActiveFocus()
  }
  function cycleChoice() {
    if (busy) return
    if (browse.activeFocus && startToday.enabled) startToday.forceActiveFocus()
    else focusChoice()
  }

  onBusyChanged: if (!busy && visible) Qt.callLater(focusChoice)
  onVisibleChanged: if (visible) Qt.callLater(focusChoice)
  Keys.onPressed: function(event) {
    var direction = event.key === Qt.Key_PageDown || event.key === Qt.Key_Down ? 1
      : event.key === Qt.Key_PageUp || event.key === Qt.Key_Up ? -1 : 0
    if (!direction) return
    body.contentY = Math.max(0, Math.min(body.contentHeight - body.height,
      body.contentY + direction * body.height * 0.75))
    event.accepted = true
  }

  ColumnLayout {
    id: content
    anchors.fill: parent
    anchors.margins: Style.spacing.panelPadding
    spacing: Style.spacing.panelGap

    Flickable {
      id: body
      Layout.fillWidth: true
      Layout.fillHeight: true
      contentWidth: width
      contentHeight: copy.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

      ColumnLayout {
        id: copy
        width: body.width - Style.space(12)
        spacing: Style.spacing.panelGap
        Text {
          Layout.fillWidth: true
          text: "Welcome to your Radar"
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.heading
          font.bold: true
          wrapMode: Text.WordWrap
          Accessible.role: Accessible.Heading
        }
        Text {
          Layout.fillWidth: true
          text: "Start with a short briefing, then explore the sections whenever you like."
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          wrapMode: Text.WordWrap
        }
        Text {
          Layout.fillWidth: true
          text: "Start from today marks this edition of " + root.storyCount + " stories read. Your saved stories and items explicitly marked unread are kept. Everything stays available to browse."
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }
        Text {
          Layout.fillWidth: true
          visible: root.message !== ""
          text: root.message
          textFormat: Text.PlainText
          color: Color.urgent
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
          Accessible.role: Accessible.AlertMessage
          Accessible.name: text
        }
      }
    }
    Flow {
      id: choices
      Layout.fillWidth: true
      Layout.preferredHeight: childrenRect.height
      spacing: Style.spacing.controlGap
      RadarButton {
        id: startToday
        managesTab: true
        onTabRequested: root.cycleChoice()
        label: root.busy ? "Please wait…" : "Start from today"
        enabled: !root.busy && root.canStart
        onClicked: root.startTodayRequested()
      }
      RadarButton {
        id: browse
        managesTab: true
        onTabRequested: root.cycleChoice()
        label: "Browse current stories"
        enabled: !root.busy
        onClicked: root.browseRequested()
      }
    }
  }
}
