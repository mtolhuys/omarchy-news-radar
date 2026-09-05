import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

FocusScope {
  id: root
  property string heading: ""
  property string detail: ""
  property string eyebrow: ""
  property string imageUrl: ""
  property bool selected: false
  signal activated()
  implicitHeight: body.implicitHeight + Style.spacing.md * 2
  activeFocusOnTab: false
  Accessible.role: Accessible.Button
  Accessible.name: eyebrow + ". " + heading + ". " + detail
  Accessible.onPressAction: root.activated()

  BorderSurface {
    anchors.fill: parent
    color: root.selected || root.activeFocus || hover.hovered
      ? Style.focusFillFor(Color.foreground, Color.accent, Color.urgent)
      : Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
    borderSpec: Border.controlSpec(root.selected || root.activeFocus ? "focus" : "normal", Color.foreground, Color.accent, Color.urgent)
    radius: Style.cornerRadius
  }
  ColumnLayout {
    id: body
    anchors { left: parent.left; right: parent.right; top: parent.top; margins: Style.spacing.md }
    spacing: Style.spacing.sm
    Image {
      visible: root.imageUrl !== "" && status !== Image.Error
      Layout.fillWidth: true
      Layout.preferredHeight: visible ? Math.min(Style.space(136), width * 0.4) : 0
      source: root.imageUrl
      fillMode: Image.PreserveAspectCrop
      asynchronous: true
      cache: true
      Accessible.ignored: true
    }
    Text {
      Layout.fillWidth: true
      text: root.eyebrow
      textFormat: Text.PlainText
      color: Color.accent
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      wrapMode: Text.WordWrap
    }
    Text {
      Layout.fillWidth: true
      text: root.heading
      textFormat: Text.PlainText
      color: Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.heading
      font.bold: true
      wrapMode: Text.WordWrap
    }
    Text {
      Layout.fillWidth: true
      text: root.detail
      textFormat: Text.PlainText
      color: Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      wrapMode: Text.WordWrap
      maximumLineCount: 4
      elide: Text.ElideRight
    }
  }
  HoverHandler { id: hover }
  TapHandler { onTapped: root.activated() }
  Keys.onReturnPressed: root.activated()
  Keys.onEnterPressed: root.activated()
  Keys.onSpacePressed: root.activated()
}
