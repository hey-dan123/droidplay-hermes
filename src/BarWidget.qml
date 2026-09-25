.pragma library
import QtQuick

BarWidget {
  id: root
  moduleName: "droidplay-hermes"

  property var panel: panelLoader.item
  readonly property bool opened: panel ? panel.opened === true : false

  function injectPanel() {
    var target = panelLoader.item
    if (!target) return
    if ("bar" in target) target.bar = root.bar
    if ("settings" in target) target.settings = root.settings
    if ("anchorItem" in target) target.anchorItem = button
    if ("hostWidget" in target) target.hostWidget = root
  }

  function refresh() {
    if (panel && panel.refresh) panel.refresh()
  }

  function togglePanel() {
    if (panel && panel.toggle) panel.toggle()
  }

  function open() {
    if (panel && panel.openFromHotkey) panel.openFromHotkey()
  }

  function close() {
    if (panel && panel.close) panel.close()
  }

  readonly property bool popoutSwitchClosing: panel ? panel.popoutSwitchClosing === true : false

  function closeForPopoutSwitch() {
    if (panel && panel.closeForPopoutSwitch) panel.closeForPopoutSwitch()
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  onBarChanged: injectPanel()
  onSettingsChanged: injectPanel()

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: panelLoader.item ? panelLoader.item.label : "DroidPlay…"
    slotSize: Style.bar.statusSlot
    tooltipText: ""
    onPressed: function(buttonCode) {
      if (!root.bar) return
      if (buttonCode === Qt.MiddleButton) root.refresh()
      else root.togglePanel()
    }
  }
}
