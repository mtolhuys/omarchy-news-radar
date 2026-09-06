import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui
import "../Model.js" as RadarModel

// Detail is a source-linked reading surface, never an installer. All comparison
// labels, release selection and relevance targets arrive from Python.
FocusScope {
  id: root
  property var item: null
  property bool busy: false
  property bool imagesVisible: true
  property bool hasParent: false
  property string pendingFocusKey: ""
  property string displayedIdentity: ""
  readonly property real contentY: scroll.contentY
  readonly property real readingWidth: body.width
  readonly property real heroWidth: hero.visible ? hero.width : 0
  readonly property int relevanceColumns: relevanceGrid.columns
  signal closed()
  signal sourceRequested(string url)
  signal projectRequested(var project)
  signal relevanceRequested(string kind, string targetId, string mode)
  readonly property var releases: item ? (item.comparisonState === "behind" ? item.newerReleases || [] : item.releases || []) : []
  readonly property var targets: item ? item.relevanceTargets || [] : []
  readonly property var projects: item ? item.projects || [] : []

  function scopeLabel(target) {
    if (target.kind === "plugin") return root.item && root.item.id === target.id
      ? "This project" : String(target.label || "Project")
    if (target.kind === "creator") return "More from " + String(target.id || "").replace(/^github:/, "@")
    var names = { marketplace: "Marketplace news", "omarchy-releases": "Omarchy releases",
      "omarchy-news": "Omarchy news", youtube: "YouTube videos", community: "Community links" }
    return names[target.id] || String(target.label || "This source")
  }
  function scopeHint(target) {
    if (target.kind === "plugin") return "Follow or mute future news about this project."
    if (target.kind === "creator") return "Applies to every covered project from this creator."
    return "Applies to all news from this source, including other projects."
  }

  function changeRelevance(kind, identity, mode, key) {
    pendingFocusKey = key
    relevanceRequested(kind, identity, mode)
  }
  onItemChanged: {
    var identity = item ? String(item.kind || "detail") + ":" + String(item.id || "") : ""
    if (identity !== displayedIdentity) {
      displayedIdentity = identity
      pendingFocusKey = ""
      scroll.contentY = 0
      // Reading a different project starts at its heading; preference updates
      // within the same project retain the reader's scroll and control focus.
      Qt.callLater(function() { if (root.displayedIdentity === identity) scroll.contentY = 0 })
      return
    }
    if (!pendingFocusKey) return
    Qt.callLater(function() {
      var target = root.buttons().filter(function(button) { return button.controlId === root.pendingFocusKey })
      if (target.length) { target[0].forceActiveFocus(); root.pendingFocusKey = "" }
    })
  }
  function additionalChanges(release) {
    var summary = String(release.summary || "").replace(/\s+/g, " ").toLowerCase()
    return (release.changes || []).filter(function(change) {
      return summary.indexOf(String(change.text || "").replace(/\s+/g, " ").toLowerCase()) < 0
    })
  }
  function focusFirst() { closeButton.forceActiveFocus() }
  function buttons() {
    var result = [closeButton, sourceButton]
    for (var sourceIndex = 0; sourceIndex < sourceRows.count; sourceIndex++) {
      var source = sourceRows.itemAt(sourceIndex)
      if (source) result.push(source)
    }
    result.push(shareButton)
    for (var j = 0; j < projectRows.count; j++) {
      var project = projectRows.itemAt(j)
      if (project) result.push(project)
    }
    for (var k = 0; k < releaseRows.count; k++) {
      var release = releaseRows.itemAt(k)
      if (release) result.push(release.sourceButton)
    }
    for (var i = 0; i < relevanceRows.count; i++) {
      var row = relevanceRows.itemAt(i)
      if (row) result = result.concat(row.buttons())
    }
    return result.filter(function(button) { return button.visible && button.enabled })
  }
  function navigate(direction) {
    var controls = buttons()
    if (!controls.length) return
    var active = controls.findIndex(function(button) { return button.activeFocus })
    var next = controls[(active + direction + controls.length) % controls.length]
    next.forceActiveFocus()
    if (next !== closeButton) {
      var top = next.mapToItem(body, 0, 0).y
      if (top < scroll.contentY || next.height > scroll.height) scroll.contentY = top
      else if (top + next.height > scroll.contentY + scroll.height) scroll.contentY = top + next.height - scroll.height
    }
  }
  onVisibleChanged: if (visible) Qt.callLater(focusFirst)
  Keys.onEscapePressed: root.closed()
  Keys.onPressed: function(event) {
    if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
      navigate(event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier) ? -1 : 1)
      event.accepted = true
    } else if (event.key === Qt.Key_PageDown || event.key === Qt.Key_Down) {
      scroll.contentY = Math.min(Math.max(0, scroll.contentHeight - scroll.height), scroll.contentY + scroll.height * 0.7)
      event.accepted = true
    } else if (event.key === Qt.Key_PageUp || event.key === Qt.Key_Up) {
      scroll.contentY = Math.max(0, scroll.contentY - scroll.height * 0.7)
      event.accepted = true
    }
  }

  BorderSurface {
    anchors.fill: parent
    color: Color.popups.background
    borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)
    radius: Style.cornerRadius
  }
  ColumnLayout {
    anchors.fill: parent
    anchors.margins: Style.spacing.panelPadding
    spacing: Style.spacing.md
    RadarButton {
      id: closeButton
      label: root.hasParent ? "← Back to collection" : "← Back"
      managesTab: true
      onTabRequested: function(direction) { root.navigate(direction) }
      onClicked: root.closed()
    }
    Flickable {
      id: scroll
      Layout.fillWidth: true
      Layout.fillHeight: true
      contentWidth: width
      contentHeight: body.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
      ColumnLayout {
        id: body
        width: Math.min(Math.max(0, scroll.width - Style.space(12)), Style.space(920))
        x: Math.max(0, (scroll.width - width - Style.space(12)) / 2)
        spacing: Style.spacing.md
        Text {
          Layout.fillWidth: true
          text: root.item ? String(root.item.title || root.item.name || "") : ""
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.display
          font.bold: true
          wrapMode: Text.WordWrap
        }
        Text {
          Layout.fillWidth: true
          visible: text !== ""
          text: root.item ? String(root.item.comparisonLabel || root.item.coverageLabel || "") : ""
          textFormat: Text.PlainText
          color: Color.accent
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          wrapMode: Text.WordWrap
        }
        Text {
          Layout.fillWidth: true
          visible: !!root.item && !!root.item.installedVersion
          text: root.item ? "Installed " + String(root.item.installedVersion || "unknown") + " · Published " + String(root.item.publishedVersion || "unknown") : ""
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }
        Image {
          id: hero
          Layout.preferredWidth: Math.min(body.width, Style.space(640))
          Layout.maximumWidth: Style.space(640)
          Layout.alignment: Qt.AlignHCenter
          visible: root.imagesVisible && source.toString() !== "" && status !== Image.Error
          Layout.preferredHeight: visible ? Math.min(Style.space(260), width * 0.5) : 0
          source: root.imagesVisible && root.item ? String(root.item.imageUrl || "") : ""
          fillMode: Image.PreserveAspectFit
          asynchronous: true
          Accessible.ignored: true
        }
        Text {
          Layout.fillWidth: true
          text: root.item ? String(root.item.body || root.item.description || root.item.summary || "") : ""
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          wrapMode: Text.WordWrap
        }
        Text {
          Layout.fillWidth: true
          visible: !!root.item && !!root.item.reviewedAt
          text: visible ? "Reviewed " + RadarModel.humanDate(root.item.reviewedAt) : ""
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
        }
        Flow {
          Layout.fillWidth: true
          Layout.preferredHeight: childrenRect.height
          spacing: Style.spacing.controlGap
          RadarButton {
            id: sourceButton
            label: root.item && root.item.kind ? "Open project source" : "Open original source"
            visible: !!root.item && !!root.item.source && !!root.item.source.url
            managesTab: true
            onTabRequested: function(direction) { root.navigate(direction) }
            onClicked: root.sourceRequested(String(root.item.source.url))
          }
          Repeater {
            id: sourceRows
            model: root.item ? (root.item.sourceLinks || []).filter(function(source) { return !root.item.source || source.url !== root.item.source.url }) : []
            RadarButton {
              required property var modelData
              label: modelData.label || "Original source"
              managesTab: true
              onTabRequested: function(direction) { root.navigate(direction) }
              onClicked: root.sourceRequested(String(modelData.url))
            }
          }
          RadarButton {
            id: shareButton
            label: "Open share page"
            visible: !!root.item && !!root.item.shareUrl
            managesTab: true
            onTabRequested: function(direction) { root.navigate(direction) }
            onClicked: root.sourceRequested(String(root.item.shareUrl))
          }
        }
        Text {
          Layout.fillWidth: true
          visible: root.projects.length > 0
          text: "Included projects"
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.heading
          font.bold: true
          wrapMode: Text.WordWrap
        }
        GridLayout {
          id: projectGrid
          Layout.fillWidth: true
          columns: width >= Style.space(640) ? 2 : 1
          rowSpacing: Style.spacing.sm
          columnSpacing: Style.spacing.sm
          Repeater {
            id: projectRows
            model: root.projects
            InsightCard {
              required property var modelData
              required property int index
              readonly property string label: heading
              Layout.fillWidth: true
              Layout.fillHeight: true
              Layout.columnSpan: projectGrid.columns === 2 && root.projects.length % 2 === 1
                && index === root.projects.length - 1 ? 2 : 1
              heading: String(modelData.name || modelData.title || "")
              detail: String(modelData.summary || modelData.description || modelData.coverageLabel || "")
              eyebrow: String(modelData.comparisonLabel || "Project")
              imageUrl: root.imagesVisible ? String(modelData.imageUrl || "") : ""
              onActivated: root.projectRequested(modelData)
              Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
                  root.navigate(event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier) ? -1 : 1)
                  event.accepted = true
                }
              }
            }
          }
        }
        Text {
          Layout.fillWidth: true
          visible: root.releases.length > 0
          text: root.item && root.item.comparisonState === "behind" ? "Since your installed version" : "Published release notes"
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.heading
          font.bold: true
          wrapMode: Text.WordWrap
        }
        Repeater {
          id: releaseRows
          model: root.releases
          Item {
            required property var modelData
            property alias sourceButton: releaseSourceButton
            Layout.fillWidth: true
            implicitHeight: releaseBody.implicitHeight + Style.spacing.md * 2
            BorderSurface {
              anchors.fill: parent
              color: Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
              borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)
              radius: Style.cornerRadius
            }
            ColumnLayout {
              id: releaseBody
              anchors.fill: parent
              anchors.margins: Style.spacing.md
              spacing: Style.spacing.sm
              Text {
                Layout.fillWidth: true
                text: modelData.version + (modelData.title !== modelData.version ? " · " + modelData.title : "")
                textFormat: Text.PlainText
                color: Color.accent
                font.family: Style.font.family
                font.pixelSize: Style.font.heading
                wrapMode: Text.WordWrap
              }
              Text {
                Layout.fillWidth: true
                text: RadarModel.humanDate(modelData.publishedAt)
                textFormat: Text.PlainText
                color: Color.popups.text
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
              }
              Text {
                Layout.fillWidth: true
                text: modelData.summary
                textFormat: Text.PlainText
                color: Color.popups.text
                font.family: Style.font.family
                font.pixelSize: Style.font.body
                wrapMode: Text.WordWrap
              }
              Repeater {
                model: root.additionalChanges(modelData)
                Text {
                  required property var modelData
                  Layout.fillWidth: true
                  text: "• " + modelData.text
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  wrapMode: Text.WordWrap
                }
              }
              RadarButton {
                id: releaseSourceButton
                label: "Original release notes"
                managesTab: true
                onTabRequested: function(direction) { root.navigate(direction) }
                onClicked: root.sourceRequested(modelData.sourceUrl)
              }
            }
          }
        }
        Item {
          Layout.fillWidth: true
          visible: !!root.item && (root.item.kind === "plugin" || root.item.kind === "omarchy") && root.releases.length === 0
          implicitHeight: visible ? noReleaseText.implicitHeight + Style.spacing.md * 2 : 0
          BorderSurface {
            anchors.fill: parent
            color: Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
            borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)
            radius: Style.cornerRadius
          }
          Text {
            id: noReleaseText
            anchors.fill: parent
            anchors.margins: Style.spacing.md
            text: "No documented release notes are available for this project in the current edition."
            textFormat: Text.PlainText
            color: Color.popups.text
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            wrapMode: Text.WordWrap
          }
        }
        Text {
          Layout.fillWidth: true
          visible: root.targets.length > 0 && !!root.item && root.item.id !== "radar-local-relevance"
          text: "Shape your future news"
          textFormat: Text.PlainText
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.heading
          font.bold: true
          wrapMode: Text.WordWrap
        }
        GridLayout {
          id: relevanceGrid
          Layout.fillWidth: true
          columns: width >= Style.space(640) ? 2 : 1
          rowSpacing: Style.spacing.sm
          columnSpacing: Style.spacing.sm
          Repeater {
            id: relevanceRows
            model: root.targets
            Item {
              required property var modelData
              required property int index
              Layout.fillWidth: true
              Layout.fillHeight: true
              Layout.columnSpan: relevanceGrid.columns === 2 && root.targets.length % 2 === 1
                && index === root.targets.length - 1 ? 2 : 1
              implicitHeight: relevanceBody.implicitHeight + Style.spacing.md * 2
              function buttons() { return [followButton, muteButton] }
              BorderSurface {
                anchors.fill: parent
                color: Style.normalFillFor(Color.foreground, Color.accent, Color.urgent)
                borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Style.spacing.hairline)
                radius: Style.cornerRadius
              }
              ColumnLayout {
                id: relevanceBody
                anchors.fill: parent
                anchors.margins: Style.spacing.md
                spacing: Style.spacing.sm
                Text {
                  Layout.fillWidth: true
                  text: root.scopeLabel(modelData)
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  font.bold: true
                  wrapMode: Text.WordWrap
                }
                Text {
                  Layout.fillWidth: true
                  text: root.scopeHint(modelData)
                  textFormat: Text.PlainText
                  color: Color.popups.text
                  font.family: Style.font.family
                  font.pixelSize: Style.font.bodySmall
                  wrapMode: Text.WordWrap
                }
                Flow {
                  Layout.fillWidth: true
                  Layout.preferredHeight: childrenRect.height
                  spacing: Style.spacing.controlGap
                  RadarButton {
                    id: followButton
                    property string controlId: modelData.kind + ":" + modelData.id + ":follow"
                    label: modelData.followed ? "Following · Clear" : "Follow"
                    selected: modelData.followed === true
                    enabled: !root.busy
                    managesTab: true
                    onTabRequested: function(direction) { root.navigate(direction) }
                    onClicked: root.changeRelevance(modelData.kind, modelData.id, modelData.followed ? "clear" : "follow", controlId)
                  }
                  RadarButton {
                    id: muteButton
                    property string controlId: modelData.kind + ":" + modelData.id + ":mute"
                    label: modelData.muted ? "Muted · Clear" : "Mute future news"
                    selected: modelData.muted === true
                    enabled: !root.busy
                    managesTab: true
                    onTabRequested: function(direction) { root.navigate(direction) }
                    onClicked: root.changeRelevance(modelData.kind, modelData.id, modelData.muted ? "clear" : "mute", controlId)
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
