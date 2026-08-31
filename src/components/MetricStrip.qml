import QtQuick
import qs.Commons
import qs.Ui

Flow {
  id: root

  property var metrics: []
  property color foreground: Color.popups.text
  property bool compact: false

  spacing: compact ? Style.spacing.labelGap : Style.spacing.sm

  function iconFor(metricId) {
    switch (metricId) {
      case "marketplace-views": return "󰈈"
      case "marketplace-hearts": return "󰋑"
      case "marketplace-copies": return "󰆏"
      case "repository-stars": return "󰓎"
      case "release-asset-downloads": return "󰇚"
    }
    return "•"
  }

  Repeater {
    model: root.metrics || []

    BorderSurface {
      required property var modelData

      implicitWidth: metricContent.implicitWidth + (root.compact ? Style.spacing.xs : Style.spacing.sm) * 2
      implicitHeight: metricContent.implicitHeight + (root.compact ? 0 : Style.spacing.xs * 2)
      radius: Style.cornerRadius
      color: root.compact
        ? "transparent"
        : Style.normalFillFor(root.foreground, Color.accent, Color.urgent)
      borderSpec: root.compact
        ? Border.none()
        : Border.controlSpec("normal", root.foreground, Color.accent, Color.urgent)

      Accessible.role: Accessible.StaticText
      Accessible.name: modelData.label + " " + modelData.valueText

      Row {
        id: metricContent
        anchors.centerIn: parent
        spacing: Style.spacing.xs

        Text {
          anchors.verticalCenter: parent.verticalCenter
          text: root.iconFor(modelData.id)
          textFormat: Text.PlainText
          color: Color.accent
          font.family: Style.font.family
          font.pixelSize: root.compact ? Style.font.caption : Style.font.icon
          font.bold: true
        }

        Text {
          anchors.verticalCenter: parent.verticalCenter
          text: modelData.valueText
          textFormat: Text.PlainText
          color: root.foreground
          font.family: Style.font.family
          font.pixelSize: root.compact ? Style.font.caption : Style.font.bodySmall
          font.bold: true
        }
      }

      HoverHandler { id: metricHover }
      PanelToolTip {
        visible: metricHover.hovered
        text: modelData.label
        fontFamily: Style.font.family
      }
    }
  }
}
