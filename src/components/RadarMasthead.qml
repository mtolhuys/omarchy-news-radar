import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// Title, native window controls, maintenance notices, and search.
ColumnLayout {
  id: root
  required property var session
  required property var actions
  required property var maintenance
  required property var window
  property bool narrow: false
  property string brandLogoPath: ""
  property color secondaryTextColor
  signal closeRequested()
  signal navigationRequested()
  signal queryEdited()
  spacing: Style.spacing.panelGap
  property alias search: searchFieldControl
  property alias tuneButton: tuneButtonControl
  property alias refreshButton: refreshButtonControl
  property alias maximizeButton: maximizeButtonControl
  property alias closeButton: closeButtonControl
  property alias noCacheNotice: noCacheNoticeControl
  property alias shortcutNotice: shortcutNoticeControl
  property alias shortcutButton: shortcutMigrationButtonControl
  GridLayout {
    Layout.fillWidth: true
    columns: root.narrow ? 1 : 2
    columnSpacing: Style.spacing.controlGap
    rowSpacing: Style.spacing.sm

    RowLayout {
      Layout.fillWidth: true
      spacing: Style.spacing.controlGap

      Item {
        Layout.fillWidth: true
        implicitHeight: titleStack.implicitHeight

        RowLayout {
          id: titleStack
          anchors.fill: parent
          spacing: Style.spacing.md

          Image {
            Layout.preferredWidth: Style.font.displayLarge
            Layout.preferredHeight: Style.font.displayLarge
            source: root.brandLogoPath
            sourceSize.width: Style.font.displayLarge * 2
            sourceSize.height: Style.font.displayLarge * 2
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
            Accessible.ignored: true
          }

          Text {
            Layout.fillWidth: true
            text: "NEWS RADAR"
            textFormat: Text.PlainText
            color: Color.popups.text
            font.family: Style.font.family
            font.pixelSize: Style.font.display
            font.bold: true
            font.letterSpacing: Style.spaceReal(1)
            verticalAlignment: Text.AlignVCenter
            Accessible.role: Accessible.Heading
            Accessible.name: "Omarchy News Radar"
          }
        }

        MouseArea {
          anchors.fill: parent
          acceptedButtons: Qt.LeftButton
          cursorShape: Qt.SizeAllCursor
          onPressed: root.window.startSystemMove()
          onDoubleClicked: root.window.maximized = !root.window.maximized
        }
      }
    }

    RowLayout {
      Layout.fillWidth: root.narrow
      Layout.alignment: root.narrow ? Qt.AlignLeft : Qt.AlignRight
      spacing: Style.spacing.controlGap

      RadarButton {
        id: refreshButtonControl
        label: session.refreshing ? "Checking…" : "Check for updates"
        iconText: session.refreshing ? "↻" : ""
        iconSpinning: session.refreshing
        tooltipText: "Check the published edition (R)"
        enabled: !session.refreshing
        onClicked: session.refreshFeed()
      }

      RadarButton {
        id: tuneButtonControl
        label: "Tune"
        enabled: session.localStateReady && !actions.stateMutationPending && !actions.preferencesRunning
        onClicked: actions.showPreferences()
      }

      PanelActionButton {
        id: maximizeButtonControl
        iconText: root.window.maximized ? "❐" : "□"
        tooltipText: root.window.maximized ? "Restore" : "Maximize"
        foreground: Color.popups.text
        fontFamily: Style.font.family
        fontSize: Style.font.title
        size: Style.spacing.controlHeight
        bordered: true
        focusable: true
        Accessible.role: Accessible.Button
        Accessible.name: tooltipText
        Accessible.focusable: true
        Accessible.onPressAction: clicked()
        onClicked: {
          root.window.maximized = !root.window.maximized
          root.navigationRequested()
        }
      }

      PanelActionButton {
        id: closeButtonControl
        iconText: "×"
        tooltipText: "Close"
        foreground: Color.popups.text
        fontFamily: Style.font.family
        fontSize: Style.font.title
        size: Style.spacing.controlHeight
        bordered: true
        focusable: true
        Accessible.role: Accessible.Button
        Accessible.name: tooltipText
        Accessible.focusable: true
        Accessible.onPressAction: clicked()
        onClicked: root.closeRequested()
      }
    }
  }

  Text {
    id: noCacheNoticeControl
    Layout.fillWidth: true
    visible: !session.cachedFeed && !session.refreshing && text !== ""
    text: session.statusDetail
    textFormat: Text.PlainText
    color: root.secondaryTextColor
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
    elide: Text.ElideRight
    Accessible.role: Accessible.StaticText
    Accessible.name: text
  }

  BorderSurface {
    id: shortcutNoticeControl
    Layout.fillWidth: true
    Layout.preferredHeight: shortcutNoticeRow.implicitHeight + Style.spacing.controlPaddingY * 2
    visible: maintenance.shortcutState === "needs-update" || maintenance.shortcutState === "updating"
      || maintenance.shortcutState === "updated" || maintenance.shortcutState === "failed"
    color: Style.normalFillFor(Color.popups.text, Color.accent, Color.urgent)
    radius: Style.cornerRadius
    borderSpec: Border.controlSpec(
      maintenance.shortcutState === "failed" ? "focus" : "normal",
      Color.popups.text, Color.accent, Color.urgent)

    RowLayout {
      id: shortcutNoticeRow
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      anchors.leftMargin: Style.spacing.controlPaddingX
      anchors.rightMargin: Style.spacing.controlPaddingX
      spacing: Style.spacing.controlGap

      Text {
        Layout.fillWidth: true
        text: maintenance.shortcutMessage
        textFormat: Text.PlainText
        color: maintenance.shortcutState === "failed" ? Color.urgent : Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.bodySmall
        wrapMode: Text.WordWrap
        Accessible.role: Accessible.StaticText
        Accessible.name: text
      }

      RadarButton {
        id: shortcutMigrationButtonControl
        visible: maintenance.shortcutState === "needs-update" || maintenance.shortcutState === "failed"
        label: maintenance.shortcutState === "failed" ? "Retry shortcut update" : "Update shortcut"
        tooltipText: "Replace only Radar's exact managed toggle binding with summon activation"
        enabled: !maintenance.shortcutRunning
        onClicked: maintenance.migrateShortcut()
      }
    }
  }

  BorderSurface {
    id: pluginUpdateNotice
    Layout.fillWidth: true
    Layout.preferredHeight: pluginUpdateNoticeRow.implicitHeight + Style.spacing.controlPaddingY * 2
    visible: maintenance.pluginUpdateState === "behind" || maintenance.pluginUpdateState === "updating"
      || maintenance.pluginUpdateState === "updated" || maintenance.pluginUpdateState === "failed"
      || maintenance.pluginUpdateState === "blocked"
    color: Style.normalFillFor(Color.popups.text, Color.accent, Color.urgent)
    radius: Style.cornerRadius
    borderSpec: Border.controlSpec(
      maintenance.pluginUpdateState === "failed" ? "focus" : "normal",
      Color.popups.text, Color.accent, Color.urgent)

    RowLayout {
      id: pluginUpdateNoticeRow
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      anchors.leftMargin: Style.spacing.controlPaddingX
      anchors.rightMargin: Style.spacing.controlPaddingX
      spacing: Style.spacing.controlGap

      Text {
        Layout.fillWidth: true
        text: maintenance.pluginUpdateMessage
        textFormat: Text.PlainText
        color: maintenance.pluginUpdateState === "failed" ? Color.urgent : Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.bodySmall
        wrapMode: Text.WordWrap
        Accessible.role: Accessible.StaticText
        Accessible.name: text
      }

      RadarButton {
        id: pluginUpdateButton
        visible: (maintenance.pluginUpdateState === "behind" && maintenance.pluginUpdateCanApply)
          || maintenance.pluginUpdateState === "failed"
        label: maintenance.pluginUpdateState === "failed" ? "Retry update" : "Update plugin"
        tooltipText: "Fast-forward News Radar with Omarchy's official plugin updater"
        enabled: !maintenance.updateRunning && (maintenance.pluginUpdateCanApply || maintenance.pluginUpdateState === "failed")
        onClicked: maintenance.applyPluginUpdate()
      }
    }
  }

  TextField {
    id: searchFieldControl
    Layout.fillWidth: true
    placeholderText: "Search news  /"
    color: Color.popups.text
    placeholderTextColor: root.secondaryTextColor
    selectionColor: Style.selectionFill
    selectedTextColor: Color.popups.text
    font.family: Style.font.family
    font.pixelSize: Style.font.body
    leftPadding: Style.spacing.controlPaddingX
    rightPadding: Style.spacing.controlPaddingX
    topPadding: Style.spacing.inputPaddingY
    bottomPadding: Style.spacing.inputPaddingY
    Accessible.name: "Search news"
    onTextChanged: {
      actions.cancelInitialStoryRead()
      root.queryEdited()
    }
    Keys.onPressed: function(event) {
      if (event.key === Qt.Key_Escape) {
        root.navigationRequested()
        event.accepted = true
      }
    }
    background: BorderSurface {
      color: Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
      radius: Style.cornerRadius
      borderSpec: Border.controlSpec(searchFieldControl.activeFocus ? "focus" : "normal", Color.foreground, Color.accent, Color.urgent)
    }
  }

}
