import QtQuick
import Quickshell.Io
import "../Model.js" as RadarModel

// Explicit compatibility migration and the official plugin updater.
Item {
  id: root
  property string shortcutAction: ""

  property string shortcutState: "unknown"

  property string pluginUpdateState: "unknown"

  property string pluginUpdateMessage: ""

  property bool pluginUpdateCanApply: false

  property string shortcutMessage: ""

  required property string helperPath
  required property string shortcutHelperPath
  property bool opened: false
  readonly property bool shortcutRunning: shortcutProc.running
  readonly property bool updateRunning: updateProc.running
  readonly property bool busy: shortcutRunning || updateRunning
  function startProcess(process, argumentsList) {
    process.running = false
    process.command = [helperPath].concat(argumentsList)
    Qt.callLater(function() { if (root.opened) process.running = true })
  }
  function stop() { shortcutProc.running = false; updateProc.running = false }
  function runShortcutHelper(action) {
    if (!shortcutHelperPath || shortcutProc.running) return
    shortcutAction = action
    shortcutProc.command = [shortcutHelperPath, action]
    shortcutProc.running = true
  }

  function inspectPluginUpdate() {
    if (!helperPath || updateProc.running) return
    if (pluginUpdateState === "updating") return
    startProcess(updateProc, ["update-status"])
  }

  function applyPluginUpdate() {
    if (!helperPath || updateProc.running) return
    if (!pluginUpdateCanApply && pluginUpdateState !== "failed") return
    pluginUpdateState = "updating"
    pluginUpdateMessage = "Updating News Radar…"
    startProcess(updateProc, ["update-apply"])
  }

  function handlePluginUpdate(raw) {
    var result = RadarModel.parseResponse(raw)
    var state = String(result.state || "")
    var message = String(result.message || "")
    pluginUpdateCanApply = result.canApply === true
    if (state === "behind" && result.updateAvailable === true) {
      pluginUpdateState = "behind"
      pluginUpdateMessage = message || "A newer News Radar is available."
      pluginUpdateCanApply = result.canApply === true
    } else if (state === "updated") {
      pluginUpdateState = "updated"
      pluginUpdateMessage = message || "News Radar updated. The panel will reload with the new version."
      pluginUpdateCanApply = false
    } else if (state === "failed" || result.status === "failed") {
      pluginUpdateState = "failed"
      pluginUpdateMessage = message || "News Radar update failed."
      pluginUpdateCanApply = true
    } else if (state === "blocked" && result.updateAvailable === true) {
      pluginUpdateState = "blocked"
      pluginUpdateMessage = message || "A newer News Radar exists, but this checkout cannot update automatically."
      pluginUpdateCanApply = false
    } else if (state === "check-failed") {
      // Stay quiet on transient network blips; keep any existing behind notice.
      if (pluginUpdateState !== "behind" && pluginUpdateState !== "failed" && pluginUpdateState !== "updating") {
        pluginUpdateState = "unknown"
        pluginUpdateMessage = ""
        pluginUpdateCanApply = false
      }
    } else {
      pluginUpdateState = "current"
      pluginUpdateMessage = ""
      pluginUpdateCanApply = false
    }
  }

  function inspectShortcut() {
    runShortcutHelper("status")
  }

  function migrateShortcut() {
    shortcutState = "updating"
    shortcutMessage = "Updating the exact Radar-owned shortcut…"
    runShortcutHelper("install")
  }

  Process {
    id: updateProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.handlePluginUpdate(text)
    }
    onExited: function(exitCode) {
      if (exitCode !== 0 && root.pluginUpdateState === "updating") {
        root.pluginUpdateState = "failed"
        root.pluginUpdateMessage = "News Radar update failed."
        root.pluginUpdateCanApply = true
      }
    }
  }

  Process {
    id: shortcutProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var result = RadarModel.parseResponse(text)
        if (result.classification === "owned-legacy") {
          root.shortcutState = "needs-update"
          root.shortcutMessage = "Your Radar-owned Super+Alt+N shortcut still uses the old close-on-repeat action."
        } else if (root.shortcutAction === "install" && result.status === "migrated") {
          root.shortcutState = "updated"
          root.shortcutMessage = "Super+Alt+N now raises Radar without closing it."
        } else {
          root.shortcutState = "current"
          root.shortcutMessage = ""
        }
      }
    }
    onExited: function(exitCode) {
      if (exitCode !== 0 && root.shortcutAction === "install") {
        root.shortcutState = "failed"
        root.shortcutMessage = "Shortcut update was refused because the binding is no longer an exact Radar-owned block."
      }
    }
  }

}
