import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
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
  property bool fitPending: false
  property int fitMinimumWidth: 0
  property int fitMinimumHeight: 0
  readonly property var compositorMonitor: window.screen ? Hyprland.monitorFor(window.screen) : null
  readonly property string workareaSignature: {
    var data = compositorMonitor ? compositorMonitor.lastIpcObject : null
    return data ? JSON.stringify([data.id, data.x, data.y, data.width, data.height,
      data.scale, data.transform, data.reserved]) : ""
  }
  property string openingToken: ""
  property string phase: "closed"
  property string status: "idle"
  readonly property bool busy: prepare.running || activate.running || cleanup.running || remember.running || fit.running || fitPending
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
    fitDelay.stop()
    fit.running = false
    fitPending = false
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
    fitDelay.stop()
    fit.running = false
    fitPending = false
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

  // Reconcile accessibility and display changes with the current frame, not
  // a stale saved placement. Ordinary user moves/resizes never trigger a fit.
  function scheduleFit() {
    if (!requested || !window.visible || closing) return
    fitPending = true
    var screen = window.screen
    if (screen) {
      fittedMinimumWidth = Math.max(64, Math.min(fittedMinimumWidth, screen.width))
      fittedMinimumHeight = Math.max(64, Math.min(fittedMinimumHeight, screen.height))
    }
    geometryDelay.stop()
    fitDelay.restart()
  }

  function refreshWorkarea() {
    if (requested && window.visible && !closing) Hyprland.refreshMonitors()
  }

  onWorkareaSignatureChanged: scheduleFit()
  onMinimumWidthChanged: scheduleFit()
  onMinimumHeightChanged: scheduleFit()
  onContentReadyChanged: revealIfReady()
  Timer {
    id: fitDelay
    interval: 250
    onTriggered: {
      if (!root.requested || !root.window.visible || root.closing) return
      if (fit.running || root.phase !== "visible") { restart(); return }
      root.fitPending = false
      root.fitMinimumWidth = root.minimumWidth
      root.fitMinimumHeight = root.minimumHeight
      root.launch(fit, ["fit-window", "--minimum-width", String(root.fitMinimumWidth),
        "--minimum-height", String(root.fitMinimumHeight)])
    }
  }
  Connections {
    target: Quickshell
    function onScreensChanged() { root.refreshWorkarea() }
  }
  Connections {
    target: root.window.screen
    function onGeometryChanged() { root.refreshWorkarea() }
    function onPhysicalPixelDensityChanged() { root.refreshWorkarea() }
  }
  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!event) return
      // A layer can change the reserved workarea, but most layer activity
      // changes nothing. Refresh the native monitor cache; only a different
      // geometry signature above schedules the bounded fitting helper.
      if (["configreloaded", "openlayer", "closelayer", "monitoradded", "monitorremoved"].indexOf(String(event.name)) >= 0)
        root.refreshWorkarea()
    }
  }

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
    onTriggered: if (!root.closing && root.requested && !remember.running && !fit.running && !root.fitPending)
      root.launch(remember, ["remember-window"])
  }
  Connections {
    target: root.window
    function onWidthChanged() { root.scheduleRemember() }
    function onHeightChanged() { root.scheduleRemember() }
    function onWindowTransformChanged() { root.scheduleRemember() }
    function onScreenChanged() { root.scheduleRemember(); root.scheduleFit() }
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
  Process {
    id: fit
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (!root.requested || !root.window.visible || root.closing) return
        if (root.fitMinimumWidth !== root.minimumWidth || root.fitMinimumHeight !== root.minimumHeight) {
          root.scheduleFit()
          return
        }
        var result = RadarModel.parseResponse(text)
        var geometry = result.geometry
        if (result.status === "ok" && geometry) {
          var minimumLowered = geometry.minimumWidth < root.fittedMinimumWidth
            || geometry.minimumHeight < root.fittedMinimumHeight
          root.fittedMinimumWidth = geometry.minimumWidth
          root.fittedMinimumHeight = geometry.minimumHeight
          root.status = result.outcome
          // The compositor may have constrained this resize by the previous
          // minimum. Retry once after lowering it; unchanged minima converge.
          if (result.outcome === "refitted" && minimumLowered) root.scheduleFit()
        }
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
