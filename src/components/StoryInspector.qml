import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui
import "../Model.js" as RadarModel

// The reader renders one prepared story and emits deliberate user actions.
// It does not launch processes or own cache, selection, or reading mutations.
Item {
  id: root
  property var selectedStory: null
  property bool briefingVisible: false
  property bool briefingBusy: false
  property bool refreshing: false
  property bool readMutationPending: false
  property bool bulkReadInFlight: false
  property bool inspectorFactsOpen: false
  property color secondaryTextColor: Color.popups.text
  property color quietTextColor: Color.popups.text
  readonly property bool inspectorArticleMode: RadarModel.isReaderArticle(selectedStory)
  readonly property bool inspectorYouTube: !!selectedStory && selectedStory.type === "youtube-video"
  readonly property bool inspectorHasMetrics: !!selectedStory && !!selectedStory.metricItems && selectedStory.metricItems.length > 0
  property alias group: inspectorBriefingGroup
  property alias readButton: readStateButton
  property alias pluginButton: pluginPageButton
  property alias contentY: inspectorScroll.contentY
  signal groupReadRequested(string groupId)
  signal groupSourceRequested(var event)
  signal navigationRequested(int direction)
  signal readToggleRequested()
  signal saveToggleRequested()
  signal marketplaceRequested()
  signal contextRequested()
  signal sourceRequested()
  signal articleLinkRequested(string link)
  signal factsToggled()
  clip: true

  function inspectorMetaLine() {
    if (!selectedStory) return ""
    var date = RadarModel.humanDate(String(selectedStory.occurredAt || ""))
    var source = selectedStory.source && selectedStory.source.label
      ? String(selectedStory.source.label) : ""
    if (date && source) return date + " · " + source
    return date || source
  }

  function inspectorBodySegments() {
    if (!selectedStory) return []
    if (selectedStory.summarySegments && selectedStory.summarySegments.length)
      return selectedStory.summarySegments
    return RadarModel.articleSegments(String(selectedStory.summary || ""))
  }

  function inspectorBodyText() {
    if (!selectedStory)
      return "Story details and the original source appear here."
    if (!inspectorArticleMode)
      return String(selectedStory.summary || "")
    // Pass the live theme accent so RichText anchors follow Omarchy themes
    // instead of Qt's default bright blue.
    return RadarModel.articleBodyHtml(inspectorBodySegments(), Color.accent)
  }

  Rectangle {
    anchors.fill: parent
    color: Color.popups.background
  }

  Flickable {
    id: inspectorScroll
    anchors.fill: parent
    contentWidth: width
    contentHeight: inspector.implicitHeight
    clip: true
  boundsBehavior: Flickable.StopAtBounds
  ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

  Column {
    id: inspector
    width: parent.width
    spacing: Style.spacing.panelGap

    BriefingGroup {
      id: inspectorBriefingGroup
      visible: root.briefingVisible && !!root.selectedStory
      width: parent.width
      height: visible ? implicitHeight : 0
      story: root.selectedStory
      busy: root.briefingBusy || root.refreshing
      onReadRequested: function(groupId) { root.groupReadRequested(groupId) }
      onSourceRequested: function(event) { root.groupSourceRequested(event) }
      onNavigationRequested: function(direction) { root.navigationRequested(direction) }
    }

    BorderSurface {
      visible: !root.inspectorArticleMode && !!root.selectedStory && !!root.selectedStory.imageUrl
      width: parent.width
      height: visible ? Math.round(width * 0.58) : 0
      radius: Style.cornerRadius
      color: Color.background
      borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)
      clip: true

      Image {
        anchors.fill: parent
        source: root.selectedStory && root.selectedStory.imageUrl ? root.selectedStory.imageUrl : ""
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectCrop
        sourceSize.width: 720
        sourceSize.height: 720
      }
    }

    Text {
      visible: !root.inspectorArticleMode && !!root.selectedStory && !!root.selectedStory.imageUrl
      width: parent.width
      text: visible ? "IMAGE  " + root.selectedStory.image.credit : ""
      textFormat: Text.PlainText
      color: root.secondaryTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      wrapMode: Text.WordWrap
    }

    Text {
      width: parent.width
      text: root.selectedStory ? root.selectedStory.title : "Select a story"
      textFormat: Text.PlainText
      color: Color.popups.text
      font.family: Style.font.family
      font.pixelSize: Style.font.heading
      font.bold: true
      wrapMode: Text.WordWrap
      Accessible.role: Accessible.Heading
      Accessible.name: text
    }

    Text {
      id: inspectorMeta
      visible: root.inspectorArticleMode && !!root.selectedStory
      width: parent.width
      text: visible ? root.inspectorMetaLine() : ""
      textFormat: Text.PlainText
      color: root.secondaryTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      wrapMode: Text.WordWrap
      Accessible.role: Accessible.StaticText
      Accessible.name: text
    }

    Rectangle {
      id: inspectorReadDivider
      visible: root.inspectorArticleMode && !!root.selectedStory
      width: parent.width
      height: Style.spacing.hairline
      color: Color.popups.border
    }

    MetricStrip {
      visible: root.inspectorYouTube && root.inspectorHasMetrics
      width: parent.width
      metrics: visible ? root.selectedStory.metricItems : []
      foreground: Color.popups.text
    }

    Text {
      id: inspectorBody
      width: parent.width
      text: root.inspectorBodyText()
      textFormat: root.inspectorArticleMode ? Text.RichText : Text.PlainText
      color: Color.popups.text
      linkColor: Color.accent
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      lineHeight: 1.28
      wrapMode: Text.WordWrap
      Accessible.role: Accessible.StaticText
      Accessible.name: root.inspectorArticleMode
        ? RadarModel.articlePlainText(root.inspectorBodySegments())
        : text
      onLinkActivated: function(link) { root.articleLinkRequested(link) }

      HoverHandler {
        enabled: inspectorBody.hoveredLink && inspectorBody.hoveredLink.length > 0
        cursorShape: Qt.PointingHandCursor
      }
    }

    Flow {
      id: inspectorActions
      width: parent.width
      spacing: Style.spacing.controlGap
      RadarButton {
        id: readStateButton
        label: root.selectedStory && root.selectedStory.isUnread ? "Mark read" : "Mark unread"
        selected: !!root.selectedStory && !root.selectedStory.isUnread
        enabled: !!root.selectedStory && !root.readMutationPending && !root.bulkReadInFlight
        onClicked: root.readToggleRequested()
      }
      RadarButton {
        label: root.selectedStory && root.selectedStory.isSaved ? "Unsave" : "Save"
        enabled: !!root.selectedStory
        onClicked: root.saveToggleRequested()
      }
      RadarButton {
        id: pluginPageButton
        visible: !!root.selectedStory && !!root.selectedStory.marketplaceUrl
        label: "Plugin page"
        enabled: visible
        onClicked: root.marketplaceRequested()
      }
      RadarButton {
        label: "Context & follows"
        enabled: !!root.selectedStory
        onClicked: root.contextRequested()
      }
      RadarButton {
        label: "Original source"
        enabled: !!root.selectedStory
        onClicked: root.sourceRequested()
      }
    }

    FocusScope {
      id: inspectorFactsToggle
      visible: !!root.selectedStory
      width: parent.width
      implicitHeight: Math.max(Style.space(18), inspectorFactsLabel.implicitHeight + Style.space(2))
      activeFocusOnTab: true
      Accessible.role: Accessible.Button
      Accessible.name: inspectorFactsLabel.text
      Accessible.focusable: true
      Accessible.onPressAction: root.factsToggled()

      Text {
        id: inspectorFactsLabel
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        text: root.inspectorFactsOpen ? "Details ▾" : "Details"
        textFormat: Text.PlainText
        color: inspectorFactsHover.hovered || parent.activeFocus
          ? root.secondaryTextColor
          : root.quietTextColor
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
      }

      HoverHandler { id: inspectorFactsHover }
      PanelToolTip {
        visible: inspectorFactsHover.hovered
        text: root.inspectorFactsOpen
          ? "Hide type, trust, audit, and source URL"
          : "Show type, trust, audit, and source URL"
        fontFamily: Style.font.family
      }
      MouseArea {
        anchors.fill: parent
        preventStealing: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.factsToggled()
      }
      Keys.onReturnPressed: root.factsToggled()
      Keys.onEnterPressed: root.factsToggled()
      Keys.onSpacePressed: root.factsToggled()
    }

    Rectangle {
      id: inspectorFactsDivider
      visible: !!root.selectedStory && root.inspectorFactsOpen
      width: parent.width
      height: Style.spacing.hairline
      color: Color.popups.border
    }

    Text {
      visible: root.inspectorFactsOpen && !root.inspectorYouTube && root.inspectorHasMetrics
      width: parent.width
      text: "METRICS"
      textFormat: Text.PlainText
      color: root.quietTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }

    MetricStrip {
      visible: root.inspectorFactsOpen && !root.inspectorYouTube && root.inspectorHasMetrics
      width: parent.width
      metrics: visible ? root.selectedStory.metricItems : []
      foreground: root.quietTextColor
      compact: true
    }

    Text {
      visible: root.inspectorFactsOpen && !!root.selectedStory && !!root.selectedStory.metricsObservedAt
      width: parent.width
      text: visible ? "OBSERVED  " + root.selectedStory.metricsObservedAt : ""
      textFormat: Text.PlainText
      color: root.quietTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      wrapMode: Text.WordWrap
      Accessible.role: Accessible.StaticText
      Accessible.name: text
    }

    Text {
      visible: root.inspectorFactsOpen && !!root.selectedStory && !!root.selectedStory.metricsCaveat
      width: parent.width
      text: visible ? root.selectedStory.metricsCaveat : ""
      textFormat: Text.PlainText
      color: root.quietTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      wrapMode: Text.WordWrap
    }

    Text {
      id: inspectorMetadata
      visible: root.inspectorFactsOpen && !!root.selectedStory
      width: parent.width
      text: root.selectedStory
        ? "TYPE  " + root.selectedStory.type + "\nDATE  " + root.selectedStory.occurredAt
          + "\nTRUST  " + root.selectedStory.trust.marketplace
          + "\nAUDIT  " + (root.selectedStory.trust.securityAudit ? "authoritative audit declared" : "not claimed")
          + "\nCOMPAT  " + root.selectedStory.compatibility.basis
        : ""
      textFormat: Text.PlainText
      color: root.quietTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      wrapMode: Text.WordWrap
      Accessible.role: Accessible.StaticText
      Accessible.name: text
    }

    Text {
      visible: root.inspectorFactsOpen && !!root.selectedStory
      width: parent.width
      text: root.selectedStory ? root.selectedStory.source.label + "\n" + root.selectedStory.source.url : ""
      textFormat: Text.PlainText
      color: root.quietTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      wrapMode: Text.WrapAnywhere
    }

  }
}
}
