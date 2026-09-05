import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "../Model.js" as RadarModel

// Source-list rendering and controls; selection/scrolling live in StoryViewport.
Item {
  id: root
  property alias readButton: narrowReadButtonControl
  property alias narrowUnreadButton: narrowHeaderUnreadButtonControl
  property alias unreadButton: headerUnreadButtonControl
  property alias narrowMarkAllReadButton: narrowMarkAllReadButtonControl
  property alias markAllReadButton: markAllReadButtonControl
  property alias narrowSettingsButton: narrowSettingsButtonControl
  property alias settingsButton: settingsButtonControl
  property alias loadMoreButton: loadMoreButtonControl
  property alias list: storyListControl
  required property var session
  required property var actions
  required property var viewport
  property bool narrow: false
  readonly property bool readerLayout: currentSection === "core" || currentSection === "front-page"
  property string recoveryLabel: "Front Page"
  signal recoveryRequested()
  property bool briefingVisible: false
  property var currentProfile: ({})
  property var currentFilter: ({})
  property string currentSection: "front-page"
  property int pageSize: 12
  property real availableHeight: height
  property color secondaryTextColor
  property string summaryText: ""
  property string emptyMessage: ""
  signal settingsRequested()
  signal loadMoreRequested()
  signal contextRequested()
  signal groupSourceRequested(var event)
  signal navigationRequested(int direction)
  signal navigationFocusRequested()
  function sectionIcon(icon) {
    return ({newspaper: "", spark: "", core: "", plugins: "", youtube: "", saved: ""})[icon] || ""
  }
  clip: true

  Rectangle {
    anchors.fill: parent
    color: Color.popups.background
  }

  ColumnLayout {
    anchors.fill: parent
    spacing: Style.spacing.md

  ColumnLayout {
    Layout.fillWidth: true
    spacing: Style.spacing.sm

    RowLayout {
      visible: !root.narrow || !root.briefingVisible
      Layout.fillWidth: true
      spacing: Style.spacing.controlGap

      Text {
        text: root.sectionIcon(root.currentProfile.icon)
        textFormat: Text.PlainText
        color: Color.accent
        font.family: Style.font.family
        font.pixelSize: Style.font.iconLarge
        Accessible.ignored: true
      }

      Text {
        Layout.fillWidth: true
        text: root.currentProfile.name.toUpperCase()
        textFormat: Text.PlainText
        color: Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.heading
        font.bold: true
        elide: Text.ElideRight
        maximumLineCount: 1
        wrapMode: Text.NoWrap
        clip: true
        Accessible.role: Accessible.Heading
        Accessible.name: text
      }

      RowLayout {
        spacing: Style.spacing.controlGap
        visible: !root.narrow

      RadarButton {
        id: headerUnreadButtonControl
        label: root.currentFilter.unreadOnly ? "Unread only" : "All"
        selected: root.currentFilter.unreadOnly
        tooltipText: root.currentFilter.unreadOnly
          ? "Show all stories in this section (F)"
          : "Show unread stories only (F)"
        enabled: !actions.stateMutationPending
        onClicked: actions.updateFilter("unreadOnly", !root.currentFilter.unreadOnly)
      }

      RadarButton {
        id: markAllReadButtonControl
        visible: !root.briefingVisible && root.viewport.stories.length > 0
        label: actions.bulkReadInFlight ? "Marking read…" : "Mark all as read"
        tooltipText: "Mark every unread story matching this section's Settings as read (A)"
        enabled: Number(session.unreadCounts[root.currentSection] || 0) > 0
          && !session.refreshing && !session.projecting
          && !actions.stateMutationPending && !actions.readMutationPending
        onClicked: actions.markCurrentSectionRead()
      }

      RadarButton {
        id: settingsButtonControl
        label: "⚙ Settings"
        selected: session.filterSummary !== "No extra filters"
        enabled: !actions.stateMutationPending
        onClicked: root.settingsRequested()
      }
      }
    }

    RowLayout {
      visible: root.narrow && !!root.viewport.selectedStory
      Layout.fillWidth: true
      spacing: Style.spacing.controlGap

      RadarButton {
        id: narrowHeaderUnreadButtonControl
        label: root.currentFilter.unreadOnly ? "Unread only" : "All"
        selected: root.currentFilter.unreadOnly
        enabled: !actions.stateMutationPending
        onClicked: actions.updateFilter("unreadOnly", !root.currentFilter.unreadOnly)
      }
      RadarButton {
        id: narrowMarkAllReadButtonControl
        visible: !root.briefingVisible && root.viewport.stories.length > 0
        label: actions.bulkReadInFlight ? "Marking read…" : "Mark all as read"
        enabled: Number(session.unreadCounts[root.currentSection] || 0) > 0
          && !session.refreshing && !session.projecting
          && !actions.stateMutationPending && !actions.readMutationPending
        onClicked: actions.markCurrentSectionRead()
      }
      RadarButton {
        id: narrowSettingsButtonControl
        label: "⚙ Settings"
        selected: session.filterSummary !== "No extra filters"
        enabled: !actions.stateMutationPending
        onClicked: root.settingsRequested()
      }
    }
  }

  Text {
    Layout.fillWidth: true
    visible: !root.narrow || !root.briefingVisible
      || session.filterSummary !== "No extra filters" || session.retainedReadStories > 0
    text: root.summaryText
    textFormat: Text.PlainText
    color: root.secondaryTextColor
    font.family: Style.font.family
    font.pixelSize: Style.font.caption
    elide: Text.ElideRight
    Accessible.role: Accessible.StaticText
    Accessible.name: text
  }

  Flow {
    visible: root.narrow && !!root.viewport.selectedStory
    Layout.fillWidth: true
    Layout.preferredHeight: visible ? childrenRect.height : 0
    spacing: Style.spacing.controlGap

    RadarButton {
      id: narrowReadButtonControl
      label: root.viewport.selectedStory && root.viewport.selectedStory.isUnread ? "Mark read" : "Mark unread"
      selected: !!root.viewport.selectedStory && !root.viewport.selectedStory.isUnread
      enabled: !!root.viewport.selectedStory && !actions.readMutationPending && !actions.bulkReadInFlight
      onClicked: actions.toggleSelectedRead()
    }
    RadarButton {
      label: root.viewport.selectedStory && root.viewport.selectedStory.isSaved ? "Unsave" : "Save"
      enabled: !!root.viewport.selectedStory
      onClicked: actions.toggleSaved()
    }
    RadarButton {
      label: "Plugin page"
      enabled: !!root.viewport.selectedStory && !!root.viewport.selectedStory.marketplaceUrl
      onClicked: actions.openMarketplacePage()
    }
    RadarButton {
      label: "Context & follows"
      enabled: !!root.viewport.selectedStory
      onClicked: root.contextRequested()
    }
    RadarButton {
      label: "Open source"
      enabled: !!root.viewport.selectedStory
      onClicked: actions.openSelected()
    }
  }

  ListView {
    id: storyListControl
    Layout.fillWidth: true
    Layout.fillHeight: true
    model: root.viewport.model
    spacing: root.readerLayout ? Style.space(4) : Style.spacing.sm
    // Keep the immediately adjacent screen instantiated. Keyboard
    // navigation can then animate to real row geometry after
    // pagination instead of asking ListView to estimate a
    // virtualized delegate's position.
    cacheBuffer: height
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    header: BriefingGroup {
      id: narrowBriefingGroup
      visible: root.narrow && root.briefingVisible && !!root.viewport.selectedStory
      width: storyListControl.width
      height: visible ? implicitHeight : 0
      maximumHistoryHeight: Math.min(Style.space(160), root.availableHeight * 0.25)
      story: root.viewport.selectedStory
      busy: session.briefingBusy || session.refreshing
      onReadRequested: function(groupId) { session.runBriefingAction("mark-briefing-group-read", groupId) }
      onSourceRequested: function(event) { root.groupSourceRequested(event) }
      onNavigationRequested: function(direction) { root.navigationRequested(direction) }
    }

    delegate: StoryRow {
      required property var payload
      required property int index
      width: storyListControl.width
      story: payload
      selected: index === root.viewport.selectedIndex
      // Narrow layout hides the reading pane, so treat selection as an
      // accordion: collapse every row, expand only the selected one.
      quiet: root.narrow
        ? index !== root.viewport.selectedIndex
        : RadarModel.usesQuietCard(root.currentSection, payload)
      lead: !root.narrow
        && root.currentSection === "front-page"
        && index === 0
      onActivated: root.viewport.selectStory(index, true)
    }

    ColumnLayout {
      anchors.centerIn: parent
      visible: root.viewport.stories.length === 0
      width: Math.min(parent.width - Style.spacing.panelPadding * 2, Style.space(580))
      spacing: Style.spacing.panelGap
      Text {
        Layout.fillWidth: true
        text: root.emptyMessage
        textFormat: Text.PlainText
        color: root.secondaryTextColor
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        Accessible.role: Accessible.StaticText
        Accessible.name: text
      }
      RadarButton {
        Layout.alignment: Qt.AlignHCenter
        label: root.recoveryLabel
        enabled: !session.refreshing && !actions.stateMutationPending
        onClicked: root.recoveryRequested()
      }
    }
  }

  Item {
    // A finite briefing has no next page; reserve this space only
    // for the browsable sections that can load more stories.
    visible: root.viewport.stories.length > 0 && !root.briefingVisible
    Layout.fillWidth: true
    Layout.preferredHeight: visible ? Style.space(54) : 0

    RadarButton {
      id: loadMoreButtonControl
      anchors.centerIn: parent
      visible: session.hasMoreStories
      iconText: "↓"
      label: activeFocus
        ? "Press Enter to load " + Math.min(root.pageSize, Math.max(0, session.totalStories - root.viewport.stories.length)) + " more"
        : "Load more (" + Math.max(0, session.totalStories - root.viewport.stories.length) + " remaining)"
      tooltipText: "Down to focus · Enter to load the next page"
      onClicked: {
        root.loadMoreRequested()
        root.navigationFocusRequested()
      }
    }

    Text {
      anchors.centerIn: parent
      visible: !session.hasMoreStories
      text: "All " + session.totalStories + " stories loaded"
      textFormat: Text.PlainText
      color: root.secondaryTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }
  }
}

}
