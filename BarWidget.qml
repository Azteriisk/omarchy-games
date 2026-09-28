import QtQuick
import Quickshell
import qs.Commons
import qs.Ui

BarIconButton {
  id: root
  property string moduleName: "azterisk.games"

  readonly property var gamesService: bar?.shell?.serviceFor("azterisk.games")

  property bool popupOpen: false

  function close() {
    root.popupOpen = false
  }

  property var settings: null
  function setting(name, fallback) {
    var value = settings ? settings[name] : undefined
    return value === undefined || value === null ? fallback : value
  }

  readonly property bool hideWhenDisconnected: setting("hideWhenDisconnected", true) === true

  visible: !hideWhenDisconnected || (gamesService && (gamesService.controllerConnected || gamesService.playspaceActive || gamesService.isSyncing))
  active: (gamesService && gamesService.playspaceActive) || (gamesService && gamesService.isSyncing)
  text: "󰊴"
  tooltipText: (gamesService && gamesService.playspaceActive ? "🎮 Playspace ACTIVE (" + gamesService.playspaceTitle + ")\n" : "") +
               "Games Library (" + (gamesService ? gamesService.gameCount : 0) + " games)\n" +
               "Controller: " + (gamesService && gamesService.controllerConnected ? (gamesService.controllerName + (gamesService.controllerSlot ? " [" + gamesService.controllerSlot + "]" : "")) : "None") + "\n" +
               (gamesService && gamesService.tabletConflict ? "⚠️ Drawing tablet conflict detected!\n" : "") +
               "Left-click: Open Games Menu\nRight-click: Playspace & Controller Controls"

  onPressed: function(button) {
    if (button === Qt.RightButton) {
      root.popupOpen = !root.popupOpen
      if (gamesService) {
        gamesService.refreshController()
        gamesService.refreshPlayspace()
      }
    } else {
      Quickshell.execDetached("omarchy-menu", ["summon", "games"])
    }
  }

  PopupCard {
    id: gamesPopup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    margin: Style.space(12)
    padding: Style.space(20)
    contentWidth: gamesPopup.fittedContentWidth(Style.space(360))
    contentHeight: gamesPopup.fittedContentHeight(contentWrapper.implicitHeight)

    Item {
      id: contentWrapper
      anchors.fill: parent
      anchors.margins: Style.space(6)
      implicitHeight: contentColumn.implicitHeight + Style.space(12)

      Column {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(12)

        // Header Row
        Row {
          width: parent.width
          spacing: Style.space(10)

          Text {
            text: "󰊴"
            color: gamesService && gamesService.playspaceActive ? "#52b052" : Color.accent
            font.family: Style.font.family
            font.pixelSize: Style.font.title
            anchors.verticalCenter: parent.verticalCenter
          }

          Column {
            width: parent.width - Style.space(50)
            anchors.verticalCenter: parent.verticalCenter

            Text {
              text: "Games & Playspace"
              color: Color.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.subtitle
              font.bold: true
            }

            Text {
              text: (gamesService ? gamesService.gameCount : 0) + " games · " +
                    (gamesService && gamesService.controllerConnected ? gamesService.controllerName : "No controller")
              color: Qt.darker(Color.foreground, 1.3)
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
          }
        }

        PanelSeparator { strength: 0.2 }

        // Section 1: Active Playspace (Game Mode)
        Column {
          width: parent.width
          spacing: Style.space(6)

          Item {
            width: parent.width
            height: playspaceTitleRow.implicitHeight

            Row {
              id: playspaceTitleRow
              anchors.left: parent.left
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(8)

              Text {
                text: "🎮"
                font.pixelSize: Style.font.body
                anchors.verticalCenter: parent.verticalCenter
              }

              Text {
                text: "Active Playspace"
                color: Color.foreground
                font.family: Style.font.family
                font.pixelSize: Style.font.body
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
              }
            }

            Text {
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              text: gamesService && gamesService.playspaceActive ? "LOCKED" : "IDLE"
              color: gamesService && gamesService.playspaceActive ? "#52b052" : Qt.darker(Color.foreground, 1.4)
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.bold: true
            }
          }

          Text {
            width: parent.width
            text: gamesService && gamesService.playspaceActive ?
                  "Bound to: " + gamesService.playspaceTitle :
                  "Locks cursor & focus to current game. Press Super+Ctrl+G to escape."
            color: Qt.darker(Color.foreground, 1.3)
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            wrapMode: Text.Wrap
          }

          Button {
            width: parent.width
            text: gamesService && gamesService.playspaceActive ? "Disengage Playspace (Escape)" : "Engage Active Playspace"
            iconText: gamesService && gamesService.playspaceActive ? "" : ""
            onClicked: {
              if (gamesService) gamesService.togglePlayspace()
            }
          }
        }

        PanelSeparator { strength: 0.2 }

        // Section 2: Controller Steward
        Column {
          width: parent.width
          spacing: Style.space(6)

          Item {
            width: parent.width
            height: controllerTitleRow.implicitHeight

            Row {
              id: controllerTitleRow
              anchors.left: parent.left
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(8)

              Text {
                text: "🕹️"
                font.pixelSize: Style.font.body
                anchors.verticalCenter: parent.verticalCenter
              }

              Text {
                text: "Controller Steward"
                color: Color.foreground
                font.family: Style.font.family
                font.pixelSize: Style.font.body
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
              }
            }

            Text {
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              text: gamesService && gamesService.controllerConnected ? (gamesService.tabletConflict ? "Slot Conflict" : "Slot OK") : "Disconnected"
              color: gamesService && gamesService.controllerConnected ? (gamesService.tabletConflict ? "#e5c07b" : "#52b052") : "#e06c75"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.bold: true
            }
          }

          Text {
            width: parent.width
            text: gamesService && gamesService.controllerConnected ?
                  gamesService.controllerName + (gamesService.controllerSlot ? " (" + gamesService.controllerSlot + ")" : "") :
                  "No gamepad connected. Drawing tablets isolated."
            color: Qt.darker(Color.foreground, 1.3)
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            wrapMode: Text.Wrap
          }

          Row {
            width: parent.width
            spacing: Style.space(8)

            Button {
              width: (parent.width - Style.space(8)) / 2
              text: "Test Inputs"
              iconText: "󰊴"
              enabled: gamesService && gamesService.controllerConnected
              onClicked: {
                root.close()
                if (gamesService) gamesService.testController()
              }
            }

            Button {
              width: (parent.width - Style.space(8)) / 2
              text: "Fix Tablet Slot"
              iconText: ""
              onClicked: {
                root.close()
                if (gamesService) gamesService.fixController()
              }
            }
          }
        }

        PanelSeparator { strength: 0.2 }

        // Section 3: Xbox Streaming & Library
        Column {
          width: parent.width
          spacing: Style.space(6)

          Row {
            width: parent.width
            spacing: Style.space(8)

            Button {
              width: (parent.width - Style.space(8)) / 2
              text: "Stream Xbox"
              iconText: "󰊴"
              onClicked: {
                root.close()
                if (gamesService) gamesService.streamXbox()
              }
            }

            Button {
              width: (parent.width - Style.space(8)) / 2
              text: gamesService && gamesService.isSyncing ? "Syncing..." : "Rescan Library"
              iconText: ""
              enabled: !(gamesService && gamesService.isSyncing)
              onClicked: {
                if (gamesService) gamesService.sync()
              }
            }
          }

          Button {
            width: parent.width
            text: "Open Games Menu (SUPER+ALT+SPACE)"
            iconText: "󰍜"
            onClicked: {
              root.close()
              Quickshell.execDetached("omarchy-menu", ["summon", "games"])
            }
          }
        }
      }
    }
  }
}
