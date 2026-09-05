import QtQuick
import Quickshell
import Quickshell.Io
import "../Model.js" as RadarModel

// The window maps only after placement and a local reading model are ready.
// Network refresh never participates in this gate. All compositor work and
// cancellation live here, separate from section and reading-state decisions.
Item {
  id: root
  required property var window
  required property string helperPath
  property bool contentReady: false
  property int preferredWidth: 1120
  property int preferredHeight: 720
  property int minimumWidth: 720
  property int minimumHeight: 480
  property int fittedMinimumWidth: minimumWidth
  property int fittedMinimumHeight: minimumHeight
  property bool requested: false
  property bool preparationReady: false
  property bool recoveryReady: false
  property bool closing: false
  property string openingToken: ""
  property string phase: "closed"
  property string status: "idle"
  readonly property bool busy: prepare.running || activate.running || cleanup.running || remember.running
  signal revealed()
  signal closeReady()
  signal compositorClosed()

  function launch(process, argumentsList) {
    process.running = false
    process.command = [helperPath].concat(argumentsList)
    process.running = true
  }

  function clearOpeningRule() {
    if (!openingToken) return
    var token = openingToken
    openingToken = ""
    launch(cleanup, ["finish-window-opening", "--token", token])
  }

  function begin() {
    if (requested && window.visible) {
      closing = false
      phase = "visible"
      launch(activate, ["activate-window"])
      return
    }
    clearOpeningRule()
    requested = true
    closing = false
    preparationReady = false
    recoveryReady = false
    phase = "preparing"
    status = "preparing"
    readyDeadline.restart()
    launch(prepare, ["prepare-window", "--width", String(preferredWidth),
      "--height", String(preferredHeight), "--minimum-width", String(minimumWidth),
      "--minimum-height", String(minimumHeight)])
  }

  function revealIfReady() {
    if (!requested || closing || window.visible || !preparationReady || (!contentReady && !recoveryReady)) return
    Qt.callLater(function() {
      if (!root.requested || root.closing || root.window.visible) return
      readyDeadline.stop()
      root.phase = "mapping"
      root.window.visible = true
      root.launch(activate, ["activate-window"])
      root.revealed()
    })
  }


  function requestClose() {
    if (closing) return
    closing = true
    readyDeadline.stop()
    geometryDelay.stop()
    phase = "closing"
    if (window.visible) {
      closeDeadline.restart()
      launch(remember, ["remember-window"])
    } else closeReady()
  }

  function stop() {
    requested = false
    closing = false
    readyDeadline.stop()
    closeDeadline.stop()
    geometryDelay.stop()
    prepare.running = false
    activate.running = false
    remember.running = false
    clearOpeningRule()
    phase = "closed"
    window.visible = false
  }

  function scheduleRemember() {
    if (requested && window.visible && phase === "visible" && !closing) geometryDelay.restart()
  }

  onContentReadyChanged: revealIfReady()
  Timer {
    id: readyDeadline
    interval: 2500
    onTriggered: {
      root.recoveryReady = true
      if (!root.preparationReady) {
        prepare.running = false
        root.preparationReady = true
        root.status = "Opening with default placement"
        root.clearOpeningRule()
      }
      root.revealIfReady()
    }
  }
  Timer {
    id: closeDeadline
    interval: 1200
    onTriggered: if (root.closing) root.closeReady()
  }
  Timer {
    id: geometryDelay
    interval: 250
    onTriggered: if (!root.closing && root.requested && !remember.running)
      root.launch(remember, ["remember-window"])
  }
  Connections {
    target: root.window
    function onWidthChanged() { root.scheduleRemember() }
    function onHeightChanged() { root.scheduleRemember() }
    function onWindowTransformChanged() { root.scheduleRemember() }
    function onScreenChanged() { root.scheduleRemember() }
    function onMaximizedChanged() { root.scheduleRemember() }
    function onVisibleChanged() {
      if (!root.window.visible && root.requested && !root.closing) root.compositorClosed()
    }
  }
  Process {
    id: prepare
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (!root.requested || root.closing) return
        var result = RadarModel.parseResponse(text)
        root.openingToken = String(result.openingToken || "")
        var fit = result.geometry
        if (result.status === "ok" && fit) {
          var screen = Quickshell.screens.filter(function(candidate) { return candidate.name === fit.monitor })
          if (screen.length === 1) root.window.screen = screen[0]
          root.fittedMinimumWidth = fit.minimumWidth
          root.fittedMinimumHeight = fit.minimumHeight
          root.window.implicitWidth = fit.width
          root.window.implicitHeight = fit.height
          root.window.maximized = fit.maximized === true
          root.status = "prepared"
        } else root.status = result.message || "Opening with default placement"
        root.preparationReady = true
        root.revealIfReady()
      }
    }
    onExited: function() {
      if (root.requested && !root.preparationReady) {
        root.preparationReady = true
        root.status = "Opening with default placement"
        root.revealIfReady()
      }
    }
  }
  Process {
    id: activate
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (!root.requested || root.closing) return
        var result = RadarModel.parseResponse(text)
        root.status = result.status === "ok" ? String(result.outcome || "ready") : String(result.message || "Window focus unavailable")
        root.phase = "visible"
        root.clearOpeningRule()
        root.scheduleRemember()
      }
    }
  }
  Process { id: cleanup; stdout: StdioCollector { waitForEnd: true } }
  Process {
    id: remember
    stdout: StdioCollector { waitForEnd: true }
    onExited: function() {
      if (root.closing) {
        closeDeadline.stop()
        root.closeReady()
      }
    }
  }
}
