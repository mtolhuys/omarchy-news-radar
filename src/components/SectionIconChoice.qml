import QtQuick
import qs.Commons
import qs.Ui

FocusScope {
  id: root

  property string iconText: ""
  property string label: ""
  property bool selected: false
  signal clicked()

  implicitWidth: Math.max(Style.space(86), content.implicitWidth + Style.spacing.controlPaddingX * 2)
  implicitHeight: content.implicitHeight + Style.spacing.controlPaddingY * 2
  activeFocusOnTab: true

  Accessible.role: Accessible.RadioButton
  Accessible.name: label + " section icon"
  Accessible.checked: selected
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
      id: content
      anchors.centerIn: parent
      spacing: Style.spacing.controlGap

      Text {
        anchors.verticalCenter: parent.verticalCenter
        text: root.iconText
        textFormat: Text.PlainText
        color: root.selected ? Color.accent : Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.iconLarge
      }

      Text {
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        textFormat: Text.PlainText
        color: Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.bodySmall
        font.bold: root.selected
      }
    }
  }

  HoverHandler { id: hover }
  TapHandler { onTapped: root.clicked() }
  Keys.onReturnPressed: root.clicked()
  Keys.onEnterPressed: root.clicked()
  Keys.onSpacePressed: root.clicked()
}
