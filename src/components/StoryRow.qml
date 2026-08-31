import QtQuick
import qs.Commons
import qs.Ui

FocusScope {
  id: root

  property var story: null
  property bool selected: false
  property bool lead: false
  signal activated()
  signal hovered()

  readonly property bool hasImage: !!story && !!story.imageUrl
  // A selected surface must never keep the ambient muted token: some themes
  // intentionally make that token close to their selection fill.  Derive all
  // selected text tiers from the popup foreground so the pair stays legible.
  readonly property color primaryTextColor: Color.popups.text
  readonly property color secondaryTextColor: selected
    ? Qt.rgba(Color.popups.text.r, Color.popups.text.g, Color.popups.text.b, 0.78)
    : Color.muted
  readonly property color selectedLabelColor: selected
    ? Color.popups.text
    : story && story.classification.significance === "critical" ? Color.urgent : Color.accent
  implicitHeight: Math.max(
    storyColumn.implicitHeight + Style.spacing.rowPaddingX * 2,
    hasImage ? (lead ? Style.space(118) : Style.space(82)) : 0
  )
  activeFocusOnTab: true

  Accessible.role: Accessible.ListItem
  Accessible.name: story ? story.title + ". " + story.summary : "Story"
  Accessible.selected: selected
  Accessible.focusable: true
  Accessible.onPressAction: root.activated()

  BorderSurface {
    anchors.fill: parent
    radius: Style.cornerRadius
    color: root.selected
      ? Style.selectedFillFor(Color.foreground, Color.accent, Color.urgent)
      : root.activeFocus || hoverHandler.hovered
        ? Style.hoverFillFor(Color.foreground, Color.accent, Color.urgent)
        : "transparent"
    borderSpec: Border.controlSpec(root.activeFocus ? "focus" : root.selected ? "selected" : "normal", Color.foreground, Color.accent, Color.urgent)

    Rectangle {
      visible: root.lead
      anchors.left: parent.left
      anchors.top: parent.top
      anchors.bottom: parent.bottom
      width: Style.spacing.hairline * 2
      color: Color.accent
    }

    Column {
      id: storyColumn
      anchors.left: parent.left
      anchors.right: storyImageBox.visible ? storyImageBox.left : parent.right
      anchors.verticalCenter: parent.verticalCenter
      anchors.leftMargin: Style.spacing.rowPaddingX
      anchors.rightMargin: Style.spacing.rowPaddingX
      spacing: Style.spacing.labelGap

      Text {
        width: parent.width
        text: root.story ? String(root.story.classification.section).toUpperCase() + (root.story.isNew ? " · NEW" : "") : ""
        textFormat: Text.PlainText
        color: root.selectedLabelColor
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.bold: true
        elide: Text.ElideRight
      }

      Text {
        width: parent.width
        text: root.story ? root.story.title : ""
        textFormat: Text.PlainText
        color: root.primaryTextColor
        font.family: Style.font.family
        font.pixelSize: root.lead ? Style.font.heading : Style.font.subtitle
        font.bold: true
        wrapMode: Text.WordWrap
        maximumLineCount: root.lead ? 3 : 2
        elide: Text.ElideRight
      }

      Text {
        width: parent.width
        text: root.story ? root.story.summary : ""
        textFormat: Text.PlainText
        color: root.secondaryTextColor
        font.family: Style.font.family
        font.pixelSize: Style.font.bodySmall
        wrapMode: Text.WordWrap
        maximumLineCount: root.lead ? 4 : 2
        elide: Text.ElideRight
      }

      MetricStrip {
        width: parent.width
        visible: !!root.story && !!root.story.metricItems && root.story.metricItems.length > 0
        metrics: visible ? root.story.metricItems : []
        foreground: root.secondaryTextColor
        compact: true
      }
    }

    BorderSurface {
      id: storyImageBox
      visible: root.hasImage
      anchors.right: parent.right
      anchors.rightMargin: Style.spacing.rowPaddingX
      anchors.verticalCenter: parent.verticalCenter
      width: root.lead ? Style.space(180) : Style.space(104)
      height: root.lead ? Style.space(102) : Style.space(66)
      radius: Style.cornerRadius
      color: Color.background
      borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)
      clip: true

      Image {
        anchors.fill: parent
        source: root.hasImage ? root.story.imageUrl : ""
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectCrop
        sourceSize.width: 360
        sourceSize.height: 360
      }
    }
  }

  HoverHandler {
    id: hoverHandler
    onHoveredChanged: if (hovered) root.hovered()
  }
  TapHandler { onTapped: root.activated() }
  Keys.onReturnPressed: root.activated()
  Keys.onEnterPressed: root.activated()
}
