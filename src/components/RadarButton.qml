import QtQuick
import qs.Commons
import qs.Ui

FocusScope {
  id: root

  property string label: ""
  property bool selected: false
  property bool danger: false
  signal clicked()

  implicitWidth: labelText.implicitWidth + Style.spacing.controlPaddingX * 2
  implicitHeight: Math.max(Style.spacing.controlHeight, labelText.implicitHeight + Style.spacing.controlPaddingY * 2)
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

    Text {
      id: labelText
      anchors.centerIn: parent
      text: root.label
      color: root.danger ? Color.urgent : Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      font.bold: root.selected
    }
  }

  HoverHandler { id: hover }
  TapHandler { onTapped: root.clicked() }
  Keys.onReturnPressed: root.clicked()
  Keys.onEnterPressed: root.clicked()
  Keys.onSpacePressed: root.clicked()
}
