import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property alias selectedTab: sectionTabs.currentIndex
    property int editingSwipeIndex: -1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        // Top Action Bar
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: "Edge Gestures"
                font.bold: true
                font.pixelSize: 22
                color: "#ffffff"
                Layout.fillWidth: true
            }

            Button {
                text: "+ Add Swipe Rule"
                highlighted: true
                onClicked: {
                    root.editingSwipeIndex = -1
                    swipeEditorDialog.openNew()
                }
            }
        }

        // Section Selector Tabs
        TabBar {
            id: sectionTabs
            Layout.fillWidth: true
            background: Rectangle {
                color: "#1a1d24"
                radius: 8
                border.color: "#282d37"
                border.width: 1
            }

            TabButton {
                text: "⚡ Edge Swipes (" + (edgepadController && edgepadController.swipeRules ? edgepadController.swipeRules.length : 0) + ")"
                font.bold: true
            }

            TabButton {
                text: "🎛️ Rotary Encoder & Sliders"
                font.bold: true
            }
        }

        // Tab Content Views
        StackLayout {
            id: contentStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: sectionTabs.currentIndex

            // ==========================================
            // TAB 1: DIRECTIONAL SWIPES SECTION
            // ==========================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12

                // Edge Swipe Margin Setting Card
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 52
                    radius: 10
                    color: "#1b1f28"
                    border.color: "#28303f"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        spacing: 14

                        Text {
                            text: "Edge Swipe Margin:"
                            font.bold: true
                            font.pixelSize: 13
                            color: "#ffffff"
                        }

                        Slider {
                            id: edgeMarginSlider
                            Layout.fillWidth: true
                            from: 4
                            to: 25
                            stepSize: 1
                            value: Math.round(((edgepadController && edgepadController.edgeSwipeWidth) ? edgepadController.edgeSwipeWidth : 0.12) * 100)
                            onMoved: {
                                if (edgepadController) {
                                    edgepadController.setEdgeSwipeWidth(value / 100.0)
                                }
                            }
                        }

                        Rectangle {
                            implicitWidth: edgeMarginValText.implicitWidth + 14
                            implicitHeight: 22
                            radius: 11
                            color: "#182736"
                            border.color: "#3daee9"
                            border.width: 1

                            Text {
                                id: edgeMarginValText
                                anchors.centerIn: parent
                                text: edgeMarginSlider.value + "%"
                                color: "#38bdf8"
                                font.bold: true
                                font.pixelSize: 11
                            }
                        }
                    }
                }

                ListView {
                    id: swipeListView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: (edgepadController && edgepadController.swipeRules) ? edgepadController.swipeRules : []
                    spacing: 10
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        active: true
                    }

                    delegate: Rectangle {
                        id: swipeCard
                        width: swipeListView.width
                        height: 80
                        radius: 10
                        color: modelData.enabled ? "#21252d" : "#1a1d24"
                        border.color: modelData.enabled ? "#2f3542" : "#242830"
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: 14

                            Switch {
                                checked: modelData.enabled
                                onToggled: edgepadController.toggleGestureRule(modelData.originalIndex, checked)
                            }

                            Rectangle {
                                width: 44
                                height: 44
                                radius: 8
                                color: {
                                    if (modelData.edge === "left") return "#d35400"
                                    if (modelData.edge === "right") return "#27ae60"
                                    return "#2980b9"
                                }

                                Column {
                                    anchors.centerIn: parent
                                    spacing: 1
                                    Text {
                                        text: {
                                            if (modelData.direction === "up") return "▲"
                                            if (modelData.direction === "down") return "▼"
                                            if (modelData.direction === "left") return "◀"
                                            return "▶"
                                        }
                                        color: "#ffffff"
                                        font.bold: true
                                        font.pixelSize: 14
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                    Text {
                                        text: (modelData.edge || "edge").toUpperCase()
                                        color: "#ffffff"
                                        font.bold: true
                                        font.pixelSize: 8
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Text {
                                    text: modelData.name || (modelData.edge + " swipe " + modelData.direction)
                                    font.bold: true
                                    font.pixelSize: 14
                                    color: modelData.enabled ? "#ffffff" : "#7f8c8d"
                                }

                                RowLayout {
                                    spacing: 8
                                    Rectangle {
                                        implicitWidth: swipeEdgeLabel.implicitWidth + 10
                                        implicitHeight: 20
                                        radius: 4
                                        color: "#2c3e50"
                                        Text {
                                            id: swipeEdgeLabel
                                            anchors.centerIn: parent
                                            text: (modelData.edge || "left").toUpperCase() + " EDGE • SWIPE " + (modelData.direction || "up").toUpperCase()
                                            color: "#3daee9"
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }

                                    Rectangle {
                                        implicitWidth: swipeActLabel.implicitWidth + 10
                                        implicitHeight: 20
                                        radius: 4
                                        color: "#1e2b37"
                                        border.color: "#3daee9"
                                        border.width: 1
                                        Text {
                                            id: swipeActLabel
                                            anchors.centerIn: parent
                                            text: {
                                                var act = modelData.action || {}
                                                if (act.type === "shortcut" || (modelData.keys && modelData.keys.length > 0)) {
                                                    var kList = modelData.keys || act.keys || []
                                                    return "Shortcut: " + edgepadController.formatShortcut(kList)
                                                }
                                                if (act.type === "key") {
                                                    var rep = (act.repeat && act.repeat > 1) ? (" (×" + act.repeat + ")") : ""
                                                    var friendly = edgepadController ? edgepadController.friendlyKeyName(act.key || "") : (act.key || "UNKNOWN")
                                                    return "Key: " + friendly + rep
                                                }
                                                if (act.type === "command") {
                                                    return "Command: " + (act.argv ? act.argv.join(" ") : "")
                                                }
                                                return "Action: Log Event"
                                            }
                                            color: "#ecf0f1"
                                            font.pixelSize: 10
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                spacing: 6

                                Button {
                                    text: "Test Action"
                                    flat: true
                                    onClicked: edgepadController.testGestureAction(modelData)
                                }

                                Button {
                                    text: "Edit"
                                    onClicked: {
                                        root.editingSwipeIndex = modelData.originalIndex
                                        swipeEditorDialog.openEdit(modelData, modelData.originalIndex)
                                    }
                                }

                                Button {
                                    text: "Duplicate"
                                    onClicked: edgepadController.duplicateGestureRule(modelData.originalIndex)
                                }

                                Button {
                                    text: "Delete"
                                    onClicked: edgepadController.removeGestureRule(modelData.originalIndex)
                                }
                            }
                        }
                    }
                }
            }

            // ==========================================
            // TAB 2: ROTARY ENCODER SETTINGS
            // ==========================================
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true

                ColumnLayout {
                    width: parent.width
                    spacing: 14

                    EncoderSettingsCard {
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }

    // ==============================================================
    // SWIPE GESTURE EDITOR DIALOG
    // ==============================================================
    Dialog {
        id: swipeEditorDialog
        title: root.editingSwipeIndex >= 0 ? "Edit Swipe Gesture" : "Add New Swipe Gesture"
        standardButtons: Dialog.Save | Dialog.Cancel
        modal: true
        width: 540
        height: 560
        anchors.centerIn: parent

        property int targetOriginalIndex: -1
        property var recordedShortcutKeys: ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_RIGHT"]
        property string recordedShortcutDisplay: "Ctrl + Alt + Right"
        property string selectedKeyName: "KEY_BRIGHTNESSUP"

        function openNew() {
            root.editingSwipeIndex = -1
            targetOriginalIndex = -1
            swipeNameField.text = "New Swipe Gesture"
            swipeEdgeCombo.currentIndex = 0
            swipeDirectionCombo.currentIndex = 0
            swipeActionTypeCombo.currentIndex = 0
            recordedShortcutKeys = ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_RIGHT"]
            recordedShortcutDisplay = "Ctrl + Alt + Right"
            selectedKeyName = "KEY_BRIGHTNESSUP"
            swipeKeyDisplayButton.text = "KEY_BRIGHTNESSUP"
            swipeRepeatSpin.value = 1
            swipeCommandField.text = ""
            swipeEditorDialog.open()
        }

        function openEdit(rule, origIndex) {
            root.editingSwipeIndex = origIndex
            targetOriginalIndex = origIndex
            swipeNameField.text = rule.name || ""
            swipeEdgeCombo.currentIndex = ["left", "right", "top", "bottom"].indexOf(rule.edge || "left")
            if (swipeEdgeCombo.currentIndex === -1) swipeEdgeCombo.currentIndex = 0
            swipeDirectionCombo.currentIndex = ["up", "down", "left", "right"].indexOf(rule.direction || "up")
            if (swipeDirectionCombo.currentIndex === -1) swipeDirectionCombo.currentIndex = 0

            var act = rule.action || {}
            if (act.type === "shortcut" || (rule.keys && rule.keys.length > 0)) {
                swipeActionTypeCombo.currentIndex = 0
                recordedShortcutKeys = rule.keys || act.keys || ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_RIGHT"]
                recordedShortcutDisplay = edgepadController.formatShortcut(recordedShortcutKeys)
            } else if (act.type === "key") {
                swipeActionTypeCombo.currentIndex = 1
                selectedKeyName = act.key || "KEY_BRIGHTNESSUP"
                swipeKeyDisplayButton.text = selectedKeyName
                swipeRepeatSpin.value = act.repeat || 1
            } else if (act.type === "command") {
                swipeActionTypeCombo.currentIndex = 2
                swipeCommandField.text = act.argv ? act.argv.join(" ") : ""
            } else {
                swipeActionTypeCombo.currentIndex = 3
            }
            swipeEditorDialog.open()
        }

        onAccepted: {
            var actionObj = {}
            var ruleKeys = []
            if (swipeActionTypeCombo.currentIndex === 0) {
                actionObj = {
                    "type": "shortcut",
                    "keys": recordedShortcutKeys
                }
                ruleKeys = recordedShortcutKeys
            } else if (swipeActionTypeCombo.currentIndex === 1) {
                actionObj = {
                    "type": "key",
                    "key": selectedKeyName,
                    "repeat": swipeRepeatSpin.value
                }
            } else if (swipeActionTypeCombo.currentIndex === 2) {
                var argv = swipeCommandField.text.trim().split(" ")
                actionObj = {
                    "type": "command",
                    "argv": argv
                }
            } else {
                actionObj = { "type": "log" }
            }

            var newRule = {
                "name": swipeNameField.text.trim(),
                "enabled": true,
                "edge": swipeEdgeCombo.currentText.toLowerCase(),
                "direction": swipeDirectionCombo.currentText.toLowerCase(),
                "fingers": 1,
                "action": actionObj
            }
            if (ruleKeys.length > 0) {
                newRule["keys"] = ruleKeys
            }

            if (root.editingSwipeIndex >= 0) {
                edgepadController.updateGestureRule(root.editingSwipeIndex, newRule)
            } else {
                edgepadController.addGestureRule(newRule)
            }
        }

        contentItem: ScrollView {
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: 12

            TextField {
                id: swipeNameField
                Layout.fillWidth: true
                placeholderText: "Gesture Name (e.g. Next Desktop, Volume Up)"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "Touchpad Edge:"; color: "#bdc3c7"; font.pixelSize: 11 }
                    ComboBox {
                        id: swipeEdgeCombo
                        Layout.fillWidth: true
                        model: ["Left", "Right", "Top", "Bottom"]
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "Swipe Direction:"; color: "#bdc3c7"; font.pixelSize: 11 }
                    ComboBox {
                        id: swipeDirectionCombo
                        Layout.fillWidth: true
                        model: ["Up", "Down", "Left", "Right"]
                    }
                }
            }

            Text { text: "Action Type:"; color: "#bdc3c7"; font.pixelSize: 11 }
            ComboBox {
                id: swipeActionTypeCombo
                Layout.fillWidth: true
                model: [
                    "Keyboard Shortcut Combination (Recorded)",
                    "Single Keyboard Key Event",
                    "Shell Command",
                    "Log Event Only"
                ]
            }

            // ==========================================
            // OPTION 0: KEYBOARD SHORTCUT COMBINATION
            // ==========================================
            ColumnLayout {
                Layout.fillWidth: true
                visible: swipeActionTypeCombo.currentIndex === 0
                spacing: 8

                Text { text: "Assigned Shortcut:"; color: "#bdc3c7"; font.pixelSize: 11 }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 52
                    radius: 8
                    color: "#13171f"
                    border.color: "#3daee9"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10

                        Text {
                            text: "⌨️"
                            font.pixelSize: 16
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            Text {
                                text: swipeEditorDialog.recordedShortcutDisplay
                                font.bold: true
                                font.pixelSize: 14
                                color: "#ffffff"
                            }
                            Text {
                                text: "[" + swipeEditorDialog.recordedShortcutKeys.join(", ") + "]"
                                font.pixelSize: 9
                                color: "#38bdf8"
                                font.family: "Monospace"
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }

                        Button {
                            text: "🔴 Record Shortcut"
                            highlighted: true
                            onClicked: {
                                edgepadController.startShortcutRecording("swipe")
                                swipeShortcutRecordDialog.open()
                            }
                        }

                        Button {
                            text: "Test"
                            onClicked: edgepadController.testGestureAction({
                                "edge": swipeEdgeCombo.currentText.toLowerCase(),
                                "direction": swipeDirectionCombo.currentText.toLowerCase(),
                                "action": {
                                    "type": "shortcut",
                                    "keys": swipeEditorDialog.recordedShortcutKeys
                                },
                                "name": swipeNameField.text
                            })
                        }
                    }
                }

                // Quick Presets for Edge Swipes
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text { text: "Quick Swipe Presets:"; color: "#94a3b8"; font.pixelSize: 10; font.bold: true }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 6

                        SwipePresetChip {
                            label: "Next Desktop (Ctrl+Alt+Right)"
                            keys: ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_RIGHT"]
                        }
                        SwipePresetChip {
                            label: "Prev Desktop (Ctrl+Alt+Left)"
                            keys: ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_LEFT"]
                        }
                        SwipePresetChip {
                            label: "Switch Window (Alt+Tab)"
                            keys: ["KEY_LEFTALT", "KEY_TAB"]
                        }
                        SwipePresetChip {
                            label: "Close Window (Alt+F4)"
                            keys: ["KEY_LEFTALT", "KEY_F4"]
                        }
                        SwipePresetChip {
                            label: "Show Desktop (Super+D)"
                            keys: ["KEY_LEFTMETA", "KEY_D"]
                        }
                        SwipePresetChip {
                            label: "Maximize (Super+Up)"
                            keys: ["KEY_LEFTMETA", "KEY_UP"]
                        }
                    }
                }
            }

            // ==========================================
            // OPTION 1: SINGLE KEY EVENT
            // ==========================================
            ColumnLayout {
                Layout.fillWidth: true
                visible: swipeActionTypeCombo.currentIndex === 1
                spacing: 6

                Text { text: "Select Keyboard Event:"; color: "#bdc3c7"; font.pixelSize: 11 }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        id: swipeKeyDisplayButton
                        text: swipeEditorDialog.selectedKeyName
                        highlighted: true
                        Layout.fillWidth: true
                        onClicked: {
                            keySelectorDialog.currentKey = swipeEditorDialog.selectedKeyName
                            keySelectorDialog.knownKeysList = edgepadController.knownKeys
                            keySelectorDialog.callerType = "swipe"
                            keySelectorDialog.open()
                        }
                    }

                    Button {
                        text: "Test Key"
                        onClicked: edgepadController.testKeyAction(swipeEditorDialog.selectedKeyName)
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Repeat Count:"; color: "#bdc3c7"; font.pixelSize: 11; Layout.fillWidth: true }
                    SpinBox {
                        id: swipeRepeatSpin
                        from: 1
                        to: 10
                        value: 1
                    }
                }
            }

            // ==========================================
            // OPTION 2: SHELL COMMAND
            // ==========================================
            ColumnLayout {
                Layout.fillWidth: true
                visible: swipeActionTypeCombo.currentIndex === 2
                spacing: 4

                Text { text: "Command & Arguments:"; color: "#bdc3c7"; font.pixelSize: 11 }
                TextField {
                    id: swipeCommandField
                    Layout.fillWidth: true
                    placeholderText: "e.g. brightnessctl set +5%"
                }
            }
        }
    }

        component SwipePresetChip: Button {
            property var keys: []
            property string label: ""
            text: label
            font.pixelSize: 10
            onClicked: {
                swipeEditorDialog.recordedShortcutKeys = keys
                swipeEditorDialog.recordedShortcutDisplay = edgepadController.formatShortcut(keys)
            }
        }
    }

    // ==============================================================
    // SWIPE SHORTCUT RECORDING MODAL DIALOG
    // ==============================================================
    Dialog {
        id: swipeShortcutRecordDialog
        title: "Record Swipe Gesture Shortcut"
        modal: true
        width: 520
        anchors.centerIn: parent

        background: Rectangle {
            color: "#1e222b"
            radius: 12
            border.color: "#3daee9"
            border.width: 2
        }

        onOpened: {
            swipeRecorderKeyHandler.forceActiveFocus()
        }

        onClosed: {
            if (edgepadController.isRecording) {
                edgepadController.cancelShortcutRecording()
            }
        }

        contentItem: FocusScope {
            id: swipeRecorderKeyHandler
            focus: true

            Keys.onShortcutOverride: function(event) {
                event.accepted = true
                edgepadController.processRecordedKey(event.key, event.modifiers, event.text)
            }

            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Escape && event.modifiers === Qt.NoModifier) {
                    edgepadController.cancelShortcutRecording()
                    swipeShortcutRecordDialog.close()
                    event.accepted = true
                    return
                }
                if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && event.modifiers === Qt.NoModifier) {
                    if (edgepadController.recordedKeys.length > 0) {
                        edgepadController.confirmRecordedShortcut()
                        swipeShortcutRecordDialog.close()
                        event.accepted = true
                        return
                    }
                }
                event.accepted = true
                edgepadController.processRecordedKey(event.key, event.modifiers, event.text)
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 16

                // Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Rectangle {
                        width: 32
                        height: 32
                        radius: 8
                        color: "#3daee9"
                        Text {
                            anchors.centerIn: parent
                            text: "⌨️"
                            font.pixelSize: 18
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "Recording Shortcut for Swipe Gesture"
                            font.bold: true
                            font.pixelSize: 15
                            color: "#ffffff"
                        }
                        Text {
                            text: "Press any key combination (e.g. Ctrl + Alt + Right, Alt + F4, Super + D)"
                            font.pixelSize: 11
                            color: "#94a3b8"
                        }
                    }
                }

                // Live Captured Combination Box
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 80
                    radius: 10
                    color: "#13171f"
                    border.color: (edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0) ? "#22c55e" : "#ef4444"
                    border.width: 2

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 6

                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            spacing: 6
                            Rectangle {
                                width: 10
                                height: 10
                                radius: 5
                                color: "#ef4444"
                                SequentialAnimation on opacity {
                                    loops: Animation.Infinite
                                    NumberAnimation { from: 1.0; to: 0.2; duration: 600 }
                                    NumberAnimation { from: 0.2; to: 1.0; duration: 600 }
                                }
                            }
                            Text {
                                text: (edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0) ? "Combination Captured" : "Listening for keystrokes..."
                                font.bold: true
                                font.pixelSize: 11
                                color: (edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0) ? "#4ade80" : "#f87171"
                            }
                        }

                        Text {
                            text: edgepadController ? edgepadController.recordedShortcutDisplay : ""
                            font.bold: true
                            font.pixelSize: 18
                            color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            visible: Boolean(edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0)
                            text: "[" + (edgepadController && edgepadController.recordedKeys ? edgepadController.recordedKeys.join(", ") : "") + "]"
                            font.pixelSize: 10
                            color: "#38bdf8"
                            font.family: "Monospace"
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }

                // Dialog Action Buttons: Clear, Cancel, Confirm & Save
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Button {
                        text: "Clear"
                        enabled: Boolean(edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0)
                        onClicked: edgepadController.clearRecordedShortcut()
                    }

                    Item { Layout.fillWidth: true }

                    Button {
                        text: "Cancel"
                        onClicked: {
                            edgepadController.cancelShortcutRecording()
                            swipeShortcutRecordDialog.close()
                        }
                    }

                    Button {
                        text: "Confirm & Save"
                        highlighted: true
                        enabled: Boolean(edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0)
                        onClicked: {
                            edgepadController.confirmRecordedShortcut()
                            swipeShortcutRecordDialog.close()
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: edgepadController
        function onSwipeShortcutRecorded(keys, display) {
            swipeEditorDialog.recordedShortcutKeys = keys
            swipeEditorDialog.recordedShortcutDisplay = display
        }
        function onHitboxSettingsChanged() {
            if (edgepadController && edgepadController.edgeSwipeWidth && !edgeMarginSlider.pressed) {
                edgeMarginSlider.value = Math.round(edgepadController.edgeSwipeWidth * 100)
            }
        }
    }

    KeySelectorDialog {
        id: keySelectorDialog
        property string callerType: "swipe"

        onKeySelected: function(keyName, keyCode) {
            swipeEditorDialog.selectedKeyName = keyName
            swipeKeyDisplayButton.text = keyName
        }
    }
}
