.pragma library
import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "droidplay-hermes"
  ipcTarget: "droidplay-hermes"
  manageIpc: false

  property QtObject bar: null
  property var settings: ({})
  property var anchorItem: null
  property var hostWidget: null
  property string adapterCommand: String((settings && settings.droidplayCommand) || "droidplay-adapter")
  readonly property int refreshSeconds: Math.max(10, parseInt(String((settings && settings.refreshSeconds) || 15), 10) || 15)
  readonly property int hermesTimeoutSeconds: Math.max(10, parseInt(String((settings && settings.hermesTimeoutSeconds) || 45), 10) || 45)

  property string status: "unknown"
  property string service: "unknown"
  property string receiver: ""
  property string lastError: ""
  property string lastQuestion: ""
  property string lastAnswer: ""
  property bool checking: false
  property bool asking: false
  property string label: "DroidPlay · unknown"
  property string _statusOutput: ""
  property string _statusError: ""

  function refresh() {
    if (statusProcess.running) return
    _statusOutput = ""
    _statusError = ""
    checking = true
    statusProcess.command = [adapterCommand, "status"]
    statusProcess.running = true
  }

  function applyStatus(raw) {
    var result
    try { result = JSON.parse(String(raw || "")) } catch (error) {
      lastError = "Adapter returned invalid JSON"
      status = "unknown"
      service = "unknown"
      label = "DroidPlay · unknown"
      return
    }
    status = String(result.status || "unknown")
    service = String(result.service || "unknown")
    receiver = String(result.receiver || "")
    lastError = String(result.error || "")
    label = status === "ready" || status === "running"
      ? "DroidPlay · " + (receiver || "ready")
      : "DroidPlay · " + status
  }

  function askHermes() {
    if (asking || !String(lastQuestion).trim()) return
    asking = true
    lastError = ""
  }

  IpcHandler {
    target: root.ipcTarget
    function refresh(): void { root.refresh() }
    function status(): string { return root.status }
    function askHermes(): void { root.askHermes() }
    function open(): void { root.open() }
    function close(): void { root.close() }
    function toggle(): void { root.toggle() }
  }

  Timer {
    id: refreshTimer
    interval: root.refreshSeconds * 1000
    repeat: true
    running: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  Process {
    id: statusProcess
    running: false
    command: []
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root._statusOutput = text }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: root._statusError = text }
    onExited: function(exitCode) {
      root.checking = false
      if (exitCode === 0) root.applyStatus(root._statusOutput)
      else {
        root.status = "error"
        root.service = "unknown"
        root.lastError = String(root._statusError || root._statusOutput || "DroidPlay adapter failed").trim().slice(0, 240)
        root.label = "DroidPlay · error"
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root
    bar: root.bar
    open: root.opened
    centerOnBar: true
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(420))
    contentHeight: panel.fittedContentHeight(column.implicitHeight, Style.space(500))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onReturnRequested: root.refresh()
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onTextKey: function(text) {
        if (text === "r" || text === "R") root.refresh()
      }
    }

    Flickable {
      anchors.fill: parent
      contentWidth: width
      contentHeight: column.implicitHeight
      clip: true
      Column {
        id: column
        width: parent.width
        spacing: Style.space(12)

        PanelHero {
          width: parent.width
          title: "DroidPlay"
          meta: root.checking ? "Checking…" : (root.lastError || "Status and strategy help")
          foreground: root.bar ? root.bar.foreground : Color.foreground
          fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
        }

        Text {
          width: parent.width
          text: "Status: " + root.status + "\nService: " + root.service + (root.receiver ? "\nReceiver: " + root.receiver : "")
          color: root.lastError ? Color.urgent : (root.bar ? root.bar.foreground : Color.foreground)
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.body
          wrapMode: Text.WordWrap
        }

        Text {
          width: parent.width
          visible: root.lastError !== ""
          text: root.lastError
          color: Color.urgent
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }

        TextField {
          id: questionField
          width: parent.width
          placeholderText: "What should I play or improve?"
          onAccepted: {
            root.lastQuestion = text
            root.askHermes()
          }
        }

        Button {
          width: parent.width
          text: root.asking ? "Ask Hermes in terminal" : "Ask Hermes"
          enabled: !root.asking && questionField.text.trim() !== ""
          onClicked: {
            root.lastQuestion = questionField.text
            root.askHermes()
          }
        }

        Text {
          width: parent.width
          visible: root.lastAnswer !== ""
          text: root.lastAnswer
          color: root.bar ? root.bar.foreground : Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }

        Button {
          width: parent.width
          text: "Refresh status"
          onClicked: root.refresh()
        }
      }
    }
  }
}
