import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui
import "KeyboardNavigation.js" as KeyboardNavigation

Rectangle {
  id: root
  property alias firstButton: barPreferenceButton
  property alias doneButton: preferencesDoneButton
  property var preferences: ({})
  property var sectionVisibility: ({})
  property bool localStateReady: false
  property bool stateMutationPending: false
  property int availableImageCount: 0
  property color secondaryTextColor
  property color scrimColor
  signal closed()
  signal booleanRequested(string name, bool value)
  signal sectionRequested(string section, bool enabled)
  function sectionIsVisible(section, visibility) { return visibility[section] !== false }
  function buttons() {
    var result = [preferencesDoneButton, barPreferenceButton, imagePreferenceButton]
    for (var i = 0; i < sectionPreferenceRows.count; i++) {
      var row = sectionPreferenceRows.itemAt(i)
      if (row) result.push(row.button)
    }
    return result.filter(function(button) { return button.visible && button.enabled })
  }
  function focusEdge(last) {
    var controls = buttons()
    if (controls.length) controls[last ? controls.length - 1 : 0].forceActiveFocus()
  }
  function moveSpatial(horizontal, vertical) {
    var controls = buttons()
    var best = KeyboardNavigation.spatialTarget(controls, root, horizontal, vertical)
    if (best) best.forceActiveFocus()
  }
  Keys.onPressed: function(event) {
    var key = (event.text || "").toLowerCase()
    if (event.key === Qt.Key_Left || event.key === Qt.Key_Right) {
      moveSpatial(event.key === Qt.Key_Left ? -1 : 1, 0); event.accepted = true
    } else if (event.key === Qt.Key_Down || key === "j") {
      moveSpatial(0, 1); event.accepted = true
    } else if (event.key === Qt.Key_Up || key === "k") {
      moveSpatial(0, -1); event.accepted = true
    } else if (event.key === Qt.Key_Home || event.key === Qt.Key_End) {
      focusEdge(event.key === Qt.Key_End); event.accepted = true
    } else if (event.key === Qt.Key_Escape || key === "q") {
      root.closed(); event.accepted = true
    }
  }

          anchors.fill: parent

          z: 20
          color: root.scrimColor
          MouseArea { anchors.fill: parent; onClicked: root.closed() }

          BorderSurface {
            anchors.centerIn: parent
            width: Math.min(parent.width - Style.spacing.panelPadding * 2, Style.space(620))
            height: Math.min(parent.height - Style.spacing.panelPadding * 2, Style.space(560))
            color: Color.popups.background
            radius: Style.cornerRadius
            borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)

            MouseArea { anchors.fill: parent }

            ColumnLayout {
              anchors.fill: parent
              anchors.margins: Style.spacing.panelPadding
              spacing: Style.spacing.panelGap

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "TUNE YOUR RADAR"
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.heading
                  font.bold: true
                }
                RadarButton { id: preferencesDoneButton; label: "Done"; onClicked: root.closed() }
              }

              Text {
                Layout.fillWidth: true
                text: "Arrow keys navigate · Enter toggles · Home/End jump · Esc closes"
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }

              Text {
                Layout.fillWidth: true
                text: "Display preferences stay on this machine and are never sent to the feed or its sources."
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.bodySmall
                wrapMode: Text.WordWrap
              }

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "Top-bar newspaper"
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                }
                RadarButton {
                  id: barPreferenceButton
                  label: root.preferences.barVisible ? "On" : "Off"
                  selected: root.preferences.barVisible
                  onClicked: root.booleanRequested("barVisible", !root.preferences.barVisible)
                }
              }

              RowLayout {
                Layout.fillWidth: true
                Text {
                  Layout.fillWidth: true
                  text: "Story images"
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                }
                RadarButton {
                  id: imagePreferenceButton
                  label: root.preferences.imagesVisible ? "On" : "Off"
                  selected: root.preferences.imagesVisible
                  onClicked: root.booleanRequested("imagesVisible", !root.preferences.imagesVisible)
                }
              }

              Text {
                Layout.fillWidth: true
                text: root.preferences.imagesVisible
                  ? root.availableImageCount > 0
                    ? root.availableImageCount + " validated marketplace images are available in this edition."
                    : "No stories in this edition include a validated image."
                  : "Images are hidden; every story remains available as text."
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }

              Text {
                text: "SECTIONS"
                textFormat: Text.PlainText
                color: Color.popups.text
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                font.bold: true
              }

              Text {
                Layout.fillWidth: true
                text: "Hide a source rail from this machine only. Front Page, For You, and Saved stay reachable. Hidden rails leave the section list, Tab cycle, and number keys, and they no longer keep the newspaper badge active."
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }

              Repeater {
                id: sectionPreferenceRows
                model: [
                  { id: "core", label: "Core" },
                  { id: "plugins", label: "Plugins" },
                  { id: "youtube", label: "YouTube" }
                ]
                RowLayout {
                  required property var modelData
                  property alias button: sectionPreferenceButton
                  Layout.fillWidth: true
                  Text {
                    Layout.fillWidth: true
                    text: modelData.label
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.body
                  }
                  RadarButton {
                    id: sectionPreferenceButton
                    label: root.sectionIsVisible(modelData.id, root.sectionVisibility) ? "On" : "Off"
                    selected: root.sectionIsVisible(modelData.id, root.sectionVisibility)
                    enabled: root.localStateReady && !root.stateMutationPending
                    onClicked: root.sectionRequested(
                      modelData.id,
                      !root.sectionIsVisible(modelData.id, root.sectionVisibility)
                    )
                  }
                }
              }

              Text {
                Layout.fillWidth: true
                text: "For You is built automatically from exact enabled plugin IDs detected on this machine."
                textFormat: Text.PlainText
                color: root.secondaryTextColor
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }
            }
          }
        }
