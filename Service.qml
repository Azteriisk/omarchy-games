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

  // Controller Steward state
  property bool controllerConnected: false
  property string controllerName: "No controller detected"
  property string controllerSlot: ""
  property bool tabletConflict: false

  // Playspace state
  property bool playspaceActive: false
  property string playspaceTitle: ""

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

  function refreshController() {
    if (controllerProcess.running) return
    controllerProcess.running = true
  }

  function refreshPlayspace() {
    if (playspaceProcess.running) return
    playspaceProcess.running = true
  }

  function togglePlayspace() {
    Quickshell.execDetached("bash", ["-c", root.scriptPath + " playspace toggle"])
    refreshTimer.restart()
  }

  function testController() {
    Quickshell.execDetached("omarchy-launch-tui", ["omarchy-games controller test"])
  }

  function fixController() {
    Quickshell.execDetached("bash", ["-c", root.scriptPath + " controller fix"])
    refreshController()
  }

  function streamXbox(target) {
    var cmd = root.scriptPath + " stream xbox"
    if (target) {
      cmd += " " + JSON.stringify(target)
    }
    Quickshell.execDetached("bash", ["-c", cmd])
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

  Process {
    id: controllerProcess
    command: ["bash", "-c", root.scriptPath + " controller json"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var parsed = JSON.parse(text.trim())
          root.controllerConnected = !!parsed.connected
          root.controllerName = parsed.primary_name || "No controller detected"
          root.controllerSlot = parsed.primary_js || ""
          root.tabletConflict = !!parsed.tablet_conflict
        } catch(e) {}
      }
    }
  }

  Process {
    id: playspaceProcess
    command: ["bash", "-c", root.scriptPath + " playspace status"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var parsed = JSON.parse(text.trim())
          root.playspaceActive = !!parsed.active
          root.playspaceTitle = parsed.title || ""
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
      root.refreshController()
      root.refreshPlayspace()
      root.sync()
    }
  }

  // Periodic polling for controller & playspace updates
  Timer {
    id: pollTimer
    interval: 4000
    running: true
    repeat: true
    onTriggered: {
      root.refreshController()
      root.refreshPlayspace()
    }
  }

  // Quick refresh timer for immediate responses to toggles
  Timer {
    id: refreshTimer
    interval: 600
    repeat: false
    onTriggered: {
      root.refreshPlayspace()
      root.refreshController()
    }
  }

  // Periodic rescan (every 5 minutes) to pick up new Steam/Lutris installs
  Timer {
    id: periodicTimer
    interval: 300000
    running: true
    repeat: true
    onTriggered: root.sync()
  }
}
