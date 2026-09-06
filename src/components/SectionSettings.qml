import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui
import "KeyboardNavigation.js" as KeyboardNavigation

Rectangle {
  id: root
  property alias resetButton: filterResetButton
  property alias imagesButton: imagesFilterButton
  property alias unreadButton: unreadFilterButton
  property alias doneButton: filterDoneButton
  property var currentProfile: ({})
  property var currentFilter: ({ types: [] })
  property string currentSection: "front-page"
  property string sectionSources: ""
  property var filterOptions: []
  property color scrimColor
  signal closed()
  signal filterRequested(string name, var value)
  signal typeRequested(string typeId)
  signal resetRequested()
  function buttons() {
    var result = [filterDoneButton]
    for (var i = 0; i < periodButtons.count; i++) result.push(periodButtons.itemAt(i))
    for (var j = 0; j < significanceButtons.count; j++) result.push(significanceButtons.itemAt(j))
    result = result.concat([unreadFilterButton, imagesFilterButton, allTypesButton])
    for (var k = 0; k < typeButtons.count; k++) result.push(typeButtons.itemAt(k))
    result.push(filterResetButton)
    return result.filter(function(button) { return button && button.visible && button.enabled })
  }
  function reveal(control) {
    if (!control || control === filterDoneButton) return
    var top = control.mapToItem(sectionSettingsContent, 0, 0).y
    if (top < settingsScroll.contentY) settingsScroll.contentY = top
    else if (top + control.height > settingsScroll.contentY + settingsScroll.height)
      settingsScroll.contentY = top + control.height - settingsScroll.height
  }
  function focusEdge(last) {
    var controls = buttons()
    if (!controls.length) return
    var control = controls[last ? controls.length - 1 : 0]
    control.forceActiveFocus()
    reveal(control)
  }
  function moveSpatial(horizontal, vertical) {
    var controls = buttons()
    var best = KeyboardNavigation.spatialTarget(controls, root, horizontal, vertical)
    if (!best) return
    best.forceActiveFocus()
    reveal(best)
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
    } else if (event.key === Qt.Key_PageDown || event.key === Qt.Key_PageUp) {
      var direction = event.key === Qt.Key_PageDown ? 1 : -1
      settingsScroll.contentY = Math.max(0, Math.min(
        settingsScroll.contentY + direction * settingsScroll.height * 0.7,
        Math.max(0, settingsScroll.contentHeight - settingsScroll.height)))
      event.accepted = true
    } else if (event.key === Qt.Key_Escape || key === "q") {
      root.closed(); event.accepted = true
    }
  }

          anchors.fill: parent

          z: 21
          color: root.scrimColor
          MouseArea { anchors.fill: parent; onClicked: root.closed() }

          BorderSurface {
            anchors.centerIn: parent
            width: Math.min(parent.width - Style.spacing.panelPadding * 2, Style.space(760))
            height: Math.min(parent.height - Style.spacing.panelPadding * 2, Style.space(680))
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
                  text: "⚙ " + root.currentProfile.name.toUpperCase() + " · SECTION SETTINGS"
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.heading
                  font.bold: true
                }
                RadarButton {
                  id: filterDoneButton
                  label: "Done"
                  onClicked: {
                    root.closed()

                  }
                }
              }

              Text {
                Layout.fillWidth: true
                text: "Arrow keys navigate · Enter applies · Home/End jump · PgUp/PgDn scroll · Esc closes"
                textFormat: Text.PlainText
                color: Color.popups.text
                opacity: 0.72
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                wrapMode: Text.WordWrap
              }

              Flickable {
                id: settingsScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: sectionSettingsContent.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                ColumnLayout {
                  id: sectionSettingsContent
                  width: parent.width
                  spacing: Style.spacing.panelGap

                  Text {
                    Layout.fillWidth: true
                    text: "SOURCES · FIXED FOR THIS SECTION\n" + root.sectionSources
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                  }

                  Text {
                    text: root.currentSection === "youtube" ? "TIME RANGE" : "TIME WINDOW"
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    font.bold: true
                  }

                  RowLayout {
                    spacing: Style.spacing.controlGap
                    Repeater {
                      id: periodButtons
                      model: [
                        { id: "all", label: "Any time" },
                        { id: "24h", label: "24 hours" },
                        { id: "7d", label: "7 days" },
                        { id: "30d", label: "30 days" }
                      ]
                      RadarButton {
                        required property var modelData
                        label: modelData.label
                        selected: root.currentFilter.period === modelData.id
                        onClicked: root.filterRequested("period", modelData.id)
                      }
                    }
                  }

                  Text {
                    text: "SIGNIFICANCE"
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    font.bold: true
                  }

                  RowLayout {
                    spacing: Style.spacing.controlGap
                    Repeater {
                      id: significanceButtons
                      model: [
                        { id: "all", label: "All" },
                        { id: "notable", label: "Notable + critical" },
                        { id: "critical", label: "Critical only" }
                      ]
                      RadarButton {
                        required property var modelData
                        label: modelData.label
                        selected: root.currentFilter.significance === modelData.id
                        onClicked: root.filterRequested("significance", modelData.id)
                      }
                    }
                  }

                  RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.spacing.controlGap
                    RadarButton {
                      id: unreadFilterButton
                      label: "Unread only"
                      selected: root.currentFilter.unreadOnly
                      onClicked: root.filterRequested("unreadOnly", !root.currentFilter.unreadOnly)
                    }
                    RadarButton {
                      id: imagesFilterButton
                      label: "With images"
                      selected: root.currentFilter.imagesOnly
                      onClicked: root.filterRequested("imagesOnly", !root.currentFilter.imagesOnly)
                    }
                  }

                  Text {
                    text: "STORY TYPES"
                    textFormat: Text.PlainText
                    color: Color.popups.text
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    font.bold: true
                  }

                  Flow {
                    Layout.fillWidth: true
                    Layout.preferredHeight: childrenRect.height
                    spacing: Style.spacing.controlGap

                    RadarButton {
                      id: allTypesButton
                      label: "All types"
                      selected: (root.currentFilter.types || []).length === 0
                      onClicked: root.filterRequested("types", [])
                    }

                    Repeater {
                      id: typeButtons
                      model: root.filterOptions
                      RadarButton {
                        required property var modelData
                        label: modelData.label
                        selected: (root.currentFilter.types || []).indexOf(modelData.id) !== -1
                        onClicked: root.typeRequested(modelData.id)
                      }
                    }
                  }

                  Item { Layout.fillHeight: true }

                  RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    RadarButton {
                      id: filterResetButton
                      label: "Reset section"
                      onClicked: root.resetRequested()
                    }
                  }
                }
              }
            }
          }
        }
