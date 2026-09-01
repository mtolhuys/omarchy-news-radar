import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as RadarModel

BarWidget {
  id: root
  moduleName: "io.github.mtolhuys.news-radar"

  readonly property var widgetMetadata: bar && bar.barWidgetRegistry
    ? bar.barWidgetRegistry.metadataFor(moduleName) : null
  readonly property string helperPath: widgetMetadata && widgetMetadata.sourceDir
    ? String(widgetMetadata.sourceDir) + "/bin/news-radar-client" : ""
  readonly property string stateBase: Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")
  readonly property string cacheBase: Quickshell.env("XDG_CACHE_HOME") || (Quickshell.env("HOME") + "/.cache")
  readonly property int refreshMinimumAgeSeconds: 15 * 60
  // Start collapsed until the validated local preference arrives. This avoids
  // a one-frame flash for users who previously hid the indicator; state defaults
  // to visible on first use.
  property bool barVisible: false
  property int unread: 0
  property string health: "empty"
  readonly property string healthLabel: health === "publisher-stale" ? "publisher stale"
    : health === "source-stale" ? "source stale"
    : health === "partial" ? "source partial"
    : health === "current" ? "publication healthy" : "no cached edition"

  visible: barVisible
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function runHelper(process, argumentsList) {
    if (!helperPath || process.running) return
    process.command = [helperPath].concat(argumentsList)
    process.running = true
  }

  function updateIndicator() {
    runHelper(indicatorProc, ["indicator"])
  }

  function refreshIfDue() {
    if (barVisible) runHelper(refreshProc, [
      "refresh-if-due", "--minimum-age", String(refreshMinimumAgeSeconds)
    ])
  }

  function scheduleRefresh(result) {
    if (!barVisible) {
      refreshTimer.stop()
      return
    }
    var seconds = Number(result && result.nextCheckInSeconds
      ? result.nextCheckInSeconds : refreshMinimumAgeSeconds)
    if (!isFinite(seconds)) seconds = refreshMinimumAgeSeconds
    refreshTimer.interval = Math.round(
      Math.max(5, Math.min(refreshMinimumAgeSeconds, seconds)) * 1000
    )
    refreshTimer.restart()
  }

  function hideIndicator() {
    runHelper(preferenceProc, ["set-preferences", "--bar-visible", "false"])
  }

  onHelperPathChanged: {
    if (!helperPath) return
    updateIndicator()
    refreshTimer.interval = 1800
    refreshTimer.restart()
  }

  Component.onCompleted: {
    updateIndicator()
    refreshTimer.start()
  }

  onBarVisibleChanged: {
    if (barVisible) {
      refreshTimer.interval = 1800
      refreshTimer.restart()
    } else refreshTimer.stop()
  }

  Process {
    id: indicatorProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (result.status === "ok" || result.status === "first-use") {
          root.unread = Math.max(0, Number(result.unread || 0))
          root.health = String(result.health || "empty")
          root.barVisible = result.barVisible !== false
        }
      }
    }
  }

  Process {
    id: preferenceProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (result.status === "ok" && result.state && result.state.preferences)
          root.barVisible = result.state.preferences.barVisible !== false
      }
    }
  }

  Process {
    id: refreshProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.scheduleRefresh(RadarModel.parseResponse(text))
    }
    onExited: function() { root.updateIndicator() }
  }

  FileView {
    id: stateWatcher
    path: root.stateBase + "/omarchy-news-radar/state.json"
    watchChanges: true
    printErrors: false
    onFileChanged: {
      reload()
      root.updateIndicator()
    }
  }

  FileView {
    id: feedWatcher
    path: root.cacheBase + "/omarchy-news-radar/feed.json"
    watchChanges: true
    printErrors: false
    onFileChanged: {
      reload()
      root.updateIndicator()
    }
  }

  Timer {
    id: refreshTimer
    interval: 1800
    onTriggered: root.refreshIfDue()
  }

  Timer {
    interval: 30000
    repeat: true
    running: true
    onTriggered: root.updateIndicator()
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    iconComponent: newspaperIcon
    active: root.unread > 0
    activeColor: Color.accent
    tooltipText: root.unread > 0
      ? root.unread + " unread · " + root.healthLabel + " · left activate · right hide · middle check for updates"
      : "News Radar · " + root.healthLabel + " · left activate · right hide · middle check for updates"

    onPressed: function(pressedButton) {
      if (pressedButton === Qt.RightButton) root.hideIndicator()
      else if (pressedButton === Qt.MiddleButton) root.runHelper(refreshProc, ["refresh"])
      else if (root.bar) root.bar.run("omarchy-shell shell summon io.github.mtolhuys.news-radar")
    }

    Rectangle {
      visible: root.health !== "empty"
      anchors.right: parent.right
      anchors.bottom: parent.bottom
      anchors.rightMargin: Style.space(4)
      anchors.bottomMargin: Style.space(4)
      width: Style.space(5)
      height: width
      radius: width / 2
      color: root.health === "current" ? Color.accent : Color.urgent
      border.width: 1
      border.color: Color.background
    }

    Rectangle {
      visible: root.unread > 0
      anchors.right: parent.right
      anchors.top: parent.top
      anchors.rightMargin: Style.space(1)
      anchors.topMargin: Style.space(1)
      width: Math.max(Style.space(10), unreadLabel.implicitWidth + Style.space(4))
      height: Style.space(10)
      radius: height / 2
      color: Color.urgent

      Text {
        id: unreadLabel
        anchors.centerIn: parent
        text: root.unread > 99 ? "99+" : String(root.unread)
        color: Color.background
        font.family: Style.font.family
        font.pixelSize: Style.space(6)
        font.bold: true
      }
    }
  }

  Component {
    id: newspaperIcon
    Item {
      Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: 1
        color: "transparent"
        border.width: 1
        border.color: button.active ? button.activeColor : button.foreground
      }
      Rectangle {
        x: 3; y: 4; width: 4; height: 4
        color: button.active ? button.activeColor : button.foreground
      }
      Repeater {
        model: [4, 7, 10]
        Rectangle {
          required property int modelData
          x: 9; y: modelData; width: 5; height: 1
          color: button.active ? button.activeColor : button.foreground
        }
      }
      Repeater {
        model: [10, 13]
        Rectangle {
          required property int modelData
          x: 3; y: modelData; width: 11; height: 1
          color: button.active ? button.activeColor : button.foreground
        }
      }
    }
  }
}
