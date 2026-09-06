import QtQuick
import QtQuick.Layouts
import qs.Commons

// Reading actions stay fixed beside a wide reader; in the compact reader they
// scroll with the article so enlarged text cannot consume its whole viewport.
ColumnLayout {
  id: root
  required property var session
  required property var actions
  required property var viewport
  property bool narrow: false
  property bool briefingVisible: false
  property var currentProfile: ({})
  property var currentFilter: ({})
  property string currentSection: "front-page"
  property color secondaryTextColor
  property string summaryText: ""
  signal settingsRequested()
  signal contextRequested()
  property alias readButton: narrowReadButtonControl
  property alias narrowUnreadButton: narrowHeaderUnreadButtonControl
  property alias unreadButton: headerUnreadButtonControl
  property alias narrowMarkAllReadButton: narrowMarkAllReadButtonControl
  property alias markAllReadButton: markAllReadButtonControl
  property alias narrowSettingsButton: narrowSettingsButtonControl
  property alias settingsButton: settingsButtonControl
  spacing: Style.spacing.md
  function sectionIcon(icon) {
    return ({newspaper: "", spark: "", core: "", plugins: "", youtube: "", saved: ""})[icon] || ""
  }
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

    }

    Flow {
      Layout.fillWidth: true
      Layout.preferredHeight: visible ? childrenRect.height : 0
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
        tooltipText: "Open settings for this section (,)"
        selected: session.filterSummary !== "No extra filters"
        enabled: !actions.stateMutationPending
        onClicked: root.settingsRequested()
      }
    }

    Flow {
      Layout.preferredHeight: visible ? childrenRect.height : 0
      visible: root.narrow
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
        tooltipText: "Open settings for this section (,)"
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
    wrapMode: Text.WordWrap
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

}
