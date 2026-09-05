import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "../Model.js" as RadarModel

// Source-list rendering and controls; selection/scrolling live in StoryViewport.
Item {
  id: root
  readonly property var readButton: toolbar ? toolbar.readButton : null
  readonly property var narrowUnreadButton: toolbar ? toolbar.narrowUnreadButton : null
  readonly property var unreadButton: toolbar ? toolbar.unreadButton : null
  readonly property var narrowMarkAllReadButton: toolbar ? toolbar.narrowMarkAllReadButton : null
  readonly property var markAllReadButton: toolbar ? toolbar.markAllReadButton : null
  readonly property var narrowSettingsButton: toolbar ? toolbar.narrowSettingsButton : null
  readonly property var settingsButton: toolbar ? toolbar.settingsButton : null
  property alias loadMoreButton: loadMoreButtonControl
  property alias list: storyListControl
  readonly property var toolbar: narrow && storyListControl.headerItem ? storyListControl.headerItem.toolbar : wideToolbar
  readonly property var group: storyListControl.headerItem ? storyListControl.headerItem.group : null
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
  function revealGroup() {
    if (group && group.visible) storyListControl.contentY = group.mapToItem(storyListControl.contentItem, 0, 0).y
  }
  clip: true

  Rectangle {
    anchors.fill: parent
    color: Color.popups.background
  }

  ColumnLayout {
    anchors.fill: parent
    spacing: Style.spacing.md

    ReaderToolbar {
      id: wideToolbar
      visible: !root.narrow
      Layout.fillWidth: true
      session: root.session
      actions: root.actions
      viewport: root.viewport
      narrow: root.narrow
      briefingVisible: root.briefingVisible
      currentProfile: root.currentProfile
      currentFilter: root.currentFilter
      currentSection: root.currentSection
      secondaryTextColor: root.secondaryTextColor
      summaryText: root.summaryText
      onSettingsRequested: root.settingsRequested()
      onContextRequested: root.contextRequested()
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

      header: Column {
        width: storyListControl.width
        property alias toolbar: compactToolbar
        property alias group: narrowBriefingGroup
        ReaderToolbar {
          id: compactToolbar
          visible: root.narrow
          width: parent.width
          height: visible ? implicitHeight : 0
          session: root.session
          actions: root.actions
          viewport: root.viewport
          narrow: root.narrow
          briefingVisible: root.briefingVisible
          currentProfile: root.currentProfile
          currentFilter: root.currentFilter
          currentSection: root.currentSection
          secondaryTextColor: root.secondaryTextColor
          summaryText: root.summaryText
          onSettingsRequested: root.settingsRequested()
          onContextRequested: root.contextRequested()
        }
        BriefingGroup {
          id: narrowBriefingGroup
          visible: root.narrow && root.briefingVisible && !!root.viewport.selectedStory
          width: parent.width
          height: visible ? implicitHeight : 0
          maximumHistoryHeight: Math.min(Style.space(160), root.availableHeight * 0.25)
          story: root.viewport.selectedStory
          busy: session.briefingBusy || session.refreshing
          onReadRequested: function(groupId) { session.runBriefingAction("mark-briefing-group-read", groupId) }
          onSourceRequested: function(event) { root.groupSourceRequested(event) }
          onNavigationRequested: function(direction) { root.navigationRequested(direction) }
        }

      }

      delegate: StoryRow {
        required property var payload
        required property int index
        width: storyListControl.width
        story: payload
        selected: index === root.viewport.selectedIndex
        expandedBody: root.narrow && selected
        // Narrow layout hides the reading pane, so treat selection as an
        // accordion: collapse every row, expand only the selected one.
        quiet: root.narrow
          ? index !== root.viewport.selectedIndex
          : RadarModel.usesQuietCard(root.currentSection, payload)
        lead: !root.narrow
          && root.currentSection === "front-page"
          && index === 0
        onActivated: root.viewport.selectStory(index, true)
        onSourceRequested: function(url) { root.actions.openArticleLink(url) }
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
      visible: root.viewport.stories.length > 0 && !root.briefingVisible && (!root.narrow || session.hasMoreStories)
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
