import QtQuick
import Quickshell
import qs.Commons
import qs.Ui

BarIconButton {
  id: root
  moduleName: "azterisk.games"

  readonly property var gamesService: bar?.shell?.serviceFor("azterisk.games")

  property bool popupOpen: false

  function close() {
    root.popupOpen = false
  }

  active: gamesService ? gamesService.isSyncing : false
  text: "󰊴"
  tooltipText: "Games Library (" + (gamesService ? gamesService.gameCount : 0) + " games)\nLeft-click: Open Games Menu\nRight-click: Quick Controls & Rescan"

  onPressed: function(button) {
    if (button === Qt.RightButton) {
      root.popupOpen = !root.popupOpen
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
    contentWidth: gamesPopup.fittedContentWidth(Style.space(340))
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
        spacing: Style.space(14)

        // Header Row
        Row {
          width: parent.width
          spacing: Style.space(10)

          Text {
            text: "󰊴"
            color: Color.accent
            font.family: Style.font.family
            font.pixelSize: Style.font.title
            anchors.verticalCenter: parent.verticalCenter
          }

          Column {
            width: parent.width - Style.space(50)
            anchors.verticalCenter: parent.verticalCenter

            Text {
              text: "Games Library"
              color: Color.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.subtitle
              font.bold: true
            }

            Text {
              text: (gamesService ? gamesService.gameCount : 0) + " games discovered across sources"
              color: Qt.darker(Color.foreground, 1.3)
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
          }
        }

        PanelSeparator { strength: 0.2 }

        // Action Buttons
        Column {
          width: parent.width
          spacing: Style.space(8)

          Row {
            width: parent.width
            spacing: Style.space(8)

            Button {
              width: (parent.width - Style.space(8)) / 2
              text: "Open Menu"
              iconText: "󰊴"
              onClicked: {
                root.close()
                Quickshell.execDetached("omarchy-menu", ["summon", "games"])
              }
            }

            Button {
              width: (parent.width - Style.space(8)) / 2
              text: gamesService && gamesService.isSyncing ? "Syncing..." : "Rescan"
              iconText: ""
              enabled: !(gamesService && gamesService.isSyncing)
              onClicked: {
                if (gamesService) gamesService.sync()
              }
            }
          }

          Button {
            width: parent.width
            text: "Configure Sources & Paths"
            iconText: ""
            onClicked: {
              root.close()
              Quickshell.execDetached("omarchy-games", ["config"])
            }
          }
        }
      }
    }
  }
}
