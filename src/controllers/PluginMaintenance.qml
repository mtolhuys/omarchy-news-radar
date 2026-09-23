import QtQuick
import Quickshell.Io
import "../Model.js" as RadarModel

// Explicit shortcut migration and a notify-only release check (D074).
Item {
  id: root
  property string shortcutAction: ""

  property string shortcutState: "unknown"

  property string pluginUpdateState: "unknown"

  property string pluginUpdateMessage: ""


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

  // Checking only. Radar never installs a release: the repository's default
  // branch is mutable, and installing it would run code outside the exact
  // snapshot the marketplace verified (D074).
  function inspectPluginUpdate() {
    if (!helperPath || updateProc.running) return
    startProcess(updateProc, ["update-status"])
  }

  function handlePluginUpdate(raw) {
    var result = RadarModel.parseResponse(raw)
    var state = String(result.state || "")
    var message = String(result.message || "")
    if (state === "behind" && result.updateAvailable === true) {
      pluginUpdateState = "behind"
      pluginUpdateMessage = message || "A newer News Radar is available through the Omarchy plugin marketplace."
    } else if (state === "check-failed") {
      // Stay quiet on transient network blips; keep any existing notice.
      if (pluginUpdateState !== "behind") {
        pluginUpdateState = "unknown"
        pluginUpdateMessage = ""
      }
    } else {
      pluginUpdateState = "current"
      pluginUpdateMessage = ""
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
