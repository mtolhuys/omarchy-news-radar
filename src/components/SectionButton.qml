import QtQuick
import qs.Commons
import qs.Ui

FocusScope {
  id: root

  property string label: ""
  property int count: 0
  property bool selected: false
  signal clicked()

  implicitHeight: Math.max(Style.spacing.controlHeight, labelText.implicitHeight + Style.spacing.controlPaddingY * 2)
  activeFocusOnTab: true

  Accessible.role: Accessible.RadioButton
  Accessible.name: label + ", " + count + " stories"
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
        : "transparent"
    borderSpec: Border.controlSpec(root.activeFocus ? "focus" : root.selected ? "selected" : "normal", Color.foreground, Color.accent, Color.urgent)

    Text {
      id: labelText
      anchors.left: parent.left
      anchors.leftMargin: Style.spacing.controlPaddingX
      anchors.verticalCenter: parent.verticalCenter
      text: root.label
      color: Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      font.bold: root.selected
      elide: Text.ElideRight
      width: parent.width - countText.width - Style.spacing.controlPaddingX * 3
    }

    Text {
      id: countText
      anchors.right: parent.right
      anchors.rightMargin: Style.spacing.controlPaddingX
      anchors.verticalCenter: parent.verticalCenter
      text: String(root.count)
      color: root.selected ? Color.accent : Color.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }
  }

  HoverHandler { id: hover }
  TapHandler { onTapped: root.clicked() }
  Keys.onReturnPressed: root.clicked()
  Keys.onEnterPressed: root.clicked()
  Keys.onSpacePressed: root.clicked()
}
