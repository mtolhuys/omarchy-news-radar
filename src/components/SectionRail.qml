import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// Navigation owns its scroll and focus mechanics. Section identity and counts
// are supplied by the reader; this view never edits local reading state.
Flickable {
  id: root
  property var sections: []
  property var counts: ({})
  property var unreadCounts: ({})
  property int currentIndex: 0
  property bool keysOpen: false
  property color secondaryTextColor: Color.popups.text
  property color quietTextColor: Color.popups.text
  signal sectionRequested(int index)
  signal keysToggled()

  function iconFor(name) {
    return ({ newspaper: "", spark: "", core: "", plugins: "", youtube: "", saved: "" })[name] || ""
  }

  function itemGeometry(item) {
    if (!item) return { visible: false }
    var point = item.mapToItem(null, 0, 0)
    return { x: point.x, y: point.y, width: item.width, height: item.height, visible: item.visible }
  }

  function keysGeometry() { return JSON.stringify(itemGeometry(keysLegendToggle)) }

  function geometry() {
    var viewport = itemGeometry(root)
    var selected = itemGeometry(sectionButtons.itemAt(currentIndex))
    var badges = {}
    for (var index = 0; index < sectionButtons.count; index++) {
      var button = sectionButtons.itemAt(index)
      if (button) badges[sections[index].id] = Number(button.badgeText)
    }
    return JSON.stringify({
      badges: badges, viewport: viewport, contentHeight: contentHeight, contentY: contentY, selected: selected,
      selectedFullyVisible: selected.visible === true
        && selected.x >= viewport.x - 1 && selected.y >= viewport.y - 1
        && selected.x + selected.width <= viewport.x + viewport.width + 1
        && selected.y + selected.height <= viewport.y + viewport.height + 1
    })
  }

  contentWidth: width
  contentHeight: Math.max(height, railContents.implicitHeight)
  clip: true
  boundsBehavior: Flickable.StopAtBounds
  flickableDirection: Flickable.VerticalFlick
  ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

  function revealItem(item) {
    if (!item || height <= 0) return
    var top = item.mapToItem(contentItem, 0, 0).y
    var bottom = top + item.height
    var next = contentY
    if (top < next || item.height > height) next = top
    else if (bottom > next + height) next = bottom - height
    contentY = Math.max(0, Math.min(next, contentHeight - height))
  }

  function revealSelected() {
    revealItem(sectionButtons.itemAt(root.currentIndex))
  }

  onHeightChanged: Qt.callLater(revealSelected)
  onContentHeightChanged: contentY = Math.max(0, Math.min(contentY, contentHeight - height))

  Connections {
    target: root
    function onKeysOpenChanged() {
      if (root.keysOpen) Qt.callLater(function() { root.revealItem(keysLegend) })
    }
  }

  ColumnLayout {
    id: railContents
    width: root.width
    height: root.contentHeight
    spacing: Style.spacing.sm

    Text {
      text: "SECTIONS · UNREAD"
      textFormat: Text.PlainText
      color: root.secondaryTextColor
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      font.bold: true
    }

    Repeater {
      id: sectionButtons
      model: root.sections
      onItemAdded: Qt.callLater(root.revealSelected)
      SectionButton {
        id: sectionButton
        required property var modelData
        required property int index
        Layout.fillWidth: true
        label: modelData.name
        icon: root.iconFor(modelData.icon)
        tone: modelData.tone
        count: Number(root.counts[modelData.id] || 0)
        unreadCount: Number(root.unreadCounts[modelData.id] || 0)
        selected: root.currentIndex === index
        onClicked: root.sectionRequested(index)
        onActiveFocusChanged: if (activeFocus) root.revealItem(sectionButton)
        onSelectedChanged: if (selected) Qt.callLater(root.revealSelected)
        onYChanged: if (selected) Qt.callLater(root.revealSelected)
        onHeightChanged: if (selected) Qt.callLater(root.revealSelected)
      }
    }

    Item { Layout.fillHeight: true }

    ColumnLayout {
      id: keysLegend
      Layout.fillWidth: true
      spacing: Style.space(4)

      FocusScope {
        id: keysLegendToggle
        Layout.fillWidth: true
        implicitHeight: Math.max(Style.space(18), keysToggleLabel.implicitHeight + Style.space(2))
        activeFocusOnTab: true
        onActiveFocusChanged: if (activeFocus) root.revealItem(keysLegendToggle)
        Accessible.role: Accessible.Button
        Accessible.name: keysToggleLabel.text
        Accessible.focusable: true
        Accessible.onPressAction: root.keysToggled()

        Text {
          id: keysToggleLabel
          anchors.left: parent.left
          anchors.verticalCenter: parent.verticalCenter
          text: root.keysOpen ? "Keys ▾" : "Keys · ?"
          textFormat: Text.PlainText
          color: keysToggleHover.hovered || parent.activeFocus
            ? root.secondaryTextColor
            : root.quietTextColor
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          font.bold: false
        }

        HoverHandler { id: keysToggleHover }
        PanelToolTip {
          visible: keysToggleHover.hovered
          text: root.keysOpen
            ? "Hide keyboard shortcuts (?)"
            : "Show keyboard shortcuts (?)"
          fontFamily: Style.font.family
        }
        MouseArea {
          anchors.fill: parent
          preventStealing: true
          cursorShape: Qt.PointingHandCursor
          onClicked: root.keysToggled()
        }
        Keys.onReturnPressed: root.keysToggled()
        Keys.onEnterPressed: root.keysToggled()
        Keys.onSpacePressed: root.keysToggled()
      }

      Flow {
        id: keysLegendBody
        visible: root.keysOpen
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? childrenRect.height : 0
        spacing: Style.space(4)
        Accessible.role: Accessible.StaticText
        Accessible.name: "Keyboard shortcuts"

        Repeater {
          model: [
            { keys: "Esc/q", action: "close" },
            { keys: "j/k", action: "move" },
            { keys: "↵/o", action: "open" },
            { keys: "s", action: "save" },
            { keys: "u", action: "read" },
            { keys: "a", action: "all-read" },
            { keys: "F6", action: "briefing controls" },
            { keys: "f", action: "unread" },
            { keys: "/", action: "search" },
            { keys: "r", action: "refresh" },
            { keys: "t", action: "tune" },
            { keys: ",", action: "section settings" },
            { keys: "Tab", action: "sections" },
            { keys: "1–" + root.sections.length, action: "jump" },
            { keys: "Home/End", action: "edges" },
            { keys: "PgUp/Dn", action: "scroll" },
            { keys: "?", action: "keys" }
          ]
          Row {
            required property var modelData
            required property int index
            spacing: Style.space(4)

            Text {
              id: keycapText
              anchors.verticalCenter: parent.verticalCenter
              text: modelData.keys
              textFormat: Text.PlainText
              color: root.secondaryTextColor
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.bold: false
            }

            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: modelData.action + (index < 14 ? " ·" : "")
              textFormat: Text.PlainText
              color: root.quietTextColor
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
          }
        }
      }
    }
  }
}
