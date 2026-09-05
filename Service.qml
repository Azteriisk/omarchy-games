import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root

  // Injected by omarchy-shell when loaded as a service plugin
  property var shell: null

  readonly property string home: Quickshell.env("HOME")
  readonly property string scriptPath: home + "/.config/omarchy/plugins/azterisk.games/scripts/omarchy-games"

  property int gameCount: 0
  property bool isSyncing: false
  property string lastSyncTime: ""
  property var gamesList: []

  signal gamesUpdated()

  function sync() {
    if (syncProcess.running) return
    isSyncing = true
    syncProcess.running = true
  }

  function refreshStats() {
    if (statsProcess.running) return
    statsProcess.running = true
  }

  function launch(gameNameOrId) {
    var cmd = scriptPath + " launch " + JSON.stringify(gameNameOrId)
    Quickshell.execDetached("bash", ["-c", cmd])
  }

  Process {
    id: syncProcess
    command: ["bash", "-c", root.scriptPath + " sync"]
    onExited: function(code) {
      root.isSyncing = false
      root.lastSyncTime = new Date().toLocaleTimeString()
      root.refreshStats()
    }
  }

  Process {
    id: statsProcess
    command: ["bash", "-c", root.scriptPath + " json"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var parsed = JSON.parse(text.trim())
          if (Array.isArray(parsed)) {
            root.gamesList = parsed
            root.gameCount = parsed.length
            root.gamesUpdated()
          }
        } catch(e) {}
      }
    }
  }

  // Initial sync delayed slightly so shell boots up instantly
  Timer {
    id: startupTimer
    interval: 2000
    running: true
    repeat: false
    onTriggered: {
      root.refreshStats()
      // Initial sync
      root.sync()
    }
  }

  // Periodic rescan (every 3 minutes) to pick up new Steam/Lutris installs
  Timer {
    id: periodicTimer
    interval: 180000
    running: true
    repeat: true
    onTriggered: root.sync()
  }
}
