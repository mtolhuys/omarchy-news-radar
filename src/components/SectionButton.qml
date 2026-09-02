import QtQuick
import qs.Commons
import qs.Ui

FocusScope {
  id: root

  property string label: ""
  property string icon: ""
  property string tone: "clear"
  property int count: 0
  property int unreadCount: 0
  property bool selected: false
  signal clicked()

  readonly property bool popupBgIsLight: (
    0.2126 * Color.popups.background.r
    + 0.7152 * Color.popups.background.g
    + 0.0722 * Color.popups.background.b) > 0.5

  function toneFill() {
    // Light-only local bump; do not override Omarchy shell.toml alphas.
    var accentA = root.popupBgIsLight ? 0.18 : 0.14
    var inkA = root.popupBgIsLight ? 0.14 : 0.11
    if (root.tone === "soft")
      return Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
    if (root.tone === "accent")
      return Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, accentA)
    if (root.tone === "ink")
      return Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, inkA)
    return "transparent"
  }

  implicitHeight: Math.max(Style.spacing.controlHeight, iconText.implicitHeight + Style.spacing.controlPaddingY * 2)
  activeFocusOnTab: true

  Accessible.role: Accessible.RadioButton
  Accessible.name: label + ", " + count + " stories, " + unreadCount + " unread"
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
        : root.toneFill()
    borderSpec: Border.controlSpec(root.activeFocus ? "focus" : root.selected ? "selected" : "normal", Color.foreground, Color.accent, Color.urgent)

    Text {
      id: iconText
      anchors.left: parent.left
      anchors.leftMargin: Style.spacing.controlPaddingX
      anchors.verticalCenter: parent.verticalCenter
      text: root.icon
      textFormat: Text.PlainText
      color: root.selected || root.activeFocus || hover.hovered ? Color.accent : Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.iconLarge
      width: Style.font.iconLarge + Style.spacing.controlGap
      horizontalAlignment: Text.AlignHCenter
    }

    Text {
      id: labelText
      anchors.left: iconText.right
      anchors.leftMargin: Style.spacing.controlGap
      anchors.verticalCenter: parent.verticalCenter
      text: root.label
      textFormat: Text.PlainText
      color: Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      font.bold: root.selected
      elide: Text.ElideRight
      width: parent.width - anchors.leftMargin - iconText.width - countText.width - Style.spacing.controlPaddingX * 3
    }

    Text {
      id: countText
      anchors.right: parent.right
      anchors.rightMargin: Style.spacing.controlPaddingX
      anchors.verticalCenter: parent.verticalCenter
      text: root.unreadCount > 0 ? "● " + String(root.unreadCount) : String(root.count)
      textFormat: Text.PlainText
      color: root.unreadCount > 0
        ? Color.accent
        : root.selected
        ? Qt.rgba(Color.popups.text.r, Color.popups.text.g, Color.popups.text.b,
                  root.popupBgIsLight ? 0.88 : 0.78)
        : Qt.rgba(Color.popups.text.r, Color.popups.text.g, Color.popups.text.b,
                  root.popupBgIsLight ? 0.82 : 0.72)
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
