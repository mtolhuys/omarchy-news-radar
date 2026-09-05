import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui

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

              Flickable {
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
                      label: "All types"
                      selected: (root.currentFilter.types || []).length === 0
                      onClicked: root.filterRequested("types", [])
                    }

                    Repeater {
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
