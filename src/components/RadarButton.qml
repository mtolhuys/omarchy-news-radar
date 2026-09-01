import QtQuick
import qs.Commons
import qs.Ui

FocusScope {
  id: root

  property string label: ""
  property string iconText: ""
  property bool iconSpinning: false
  property bool selected: false
  property bool danger: false
  signal clicked()

  implicitWidth: buttonContent.implicitWidth + Style.spacing.controlPaddingX * 2
  implicitHeight: Math.max(Style.spacing.controlHeight, buttonContent.implicitHeight + Style.spacing.controlPaddingY * 2)
  activeFocusOnTab: true

  Accessible.role: Accessible.Button
  Accessible.name: label
  Accessible.focusable: true
  Accessible.onPressAction: root.clicked()

  BorderSurface {
    anchors.fill: parent
    radius: Style.cornerRadius
    color: root.selected
      ? Style.selectedFillFor(Color.foreground, Color.accent, Color.urgent)
      : root.activeFocus || hover.hovered
        ? Style.focusFillFor(Color.foreground, Color.accent, Color.urgent)
        : Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
    borderSpec: Border.controlSpec(root.activeFocus ? "focus" : root.selected ? "selected" : "normal", Color.foreground, Color.accent, Color.urgent)

    Row {
      id: buttonContent
      anchors.centerIn: parent
      spacing: Style.spacing.controlGap

      Text {
        visible: root.iconText !== ""
        anchors.verticalCenter: parent.verticalCenter
        text: root.iconText
        textFormat: Text.PlainText
        color: root.danger ? Color.urgent : Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        transformOrigin: Item.Center

        RotationAnimation on rotation {
          from: 0
          to: 360
          duration: 800
          loops: Animation.Infinite
          running: root.iconSpinning && root.visible
        }
      }

      Text {
        id: labelText
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        textFormat: Text.PlainText
        color: root.danger ? Color.urgent : Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.bodySmall
        font.bold: root.selected
      }
    }
  }

  HoverHandler { id: hover }
  MouseArea {
    anchors.fill: parent
    preventStealing: true
    onClicked: root.clicked()
  }
  Keys.onReturnPressed: root.clicked()
  Keys.onEnterPressed: root.clicked()
  Keys.onSpacePressed: root.clicked()
}
