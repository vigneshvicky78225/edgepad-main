import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property int editingIndex: -1
    property var editingRule: null

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        // Top Action Bar
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: "Touchpad Edge Gestures"
                    font.bold: true
                    font.pixelSize: 22
                    color: "#ffffff"
                }
                Text {
                    text: "Configure edge swipes and their corresponding physical keyboard events"
                    font.pixelSize: 13
                    color: "#95a5a6"
                }
            }

            Button {
                text: "Apply Default Preset"
                onClicked: edgepadController.applyDefaultPreset()
            }

            Button {
                text: "+ Add Gesture Rule"
                highlighted: true
                onClicked: {
                    root.editingIndex = -1
                    ruleEditorDialog.openNewRule()
                }
            }
        }

        // Rule List
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ListView {
                id: rulesList
                model: edgepadController.gestureRules
                spacing: 10

                delegate: Rectangle {
                    id: ruleCard
                    width: rulesList.width
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
                            onToggled: edgepadController.toggleGestureRule(index, checked)
                        }

                        // Edge & Direction Icon
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

                        // Rule Details
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
                                    implicitWidth: edgeLabel.implicitWidth + 10
                                    implicitHeight: 20
                                    radius: 4
                                    color: "#2c3e50"
                                    Text {
                                        id: edgeLabel
                                        anchors.centerIn: parent
                                        text: (modelData.edge || "left").toUpperCase() + " EDGE • SWIPE " + (modelData.direction || "up").toUpperCase()
                                        color: "#3daee9"
                                        font.pixelSize: 10
                                        font.bold: true
                                    }
                                }

                                Rectangle {
                                    implicitWidth: actionLabel.implicitWidth + 10
                                    implicitHeight: 20
                                    radius: 4
                                    color: "#1e2b37"
                                    border.color: "#3daee9"
                                    border.width: 1
                                    Text {
                                        id: actionLabel
                                        anchors.centerIn: parent
                                        text: {
                                            var act = modelData.action || {}
                                            if (act.type === "key") {
                                                var rep = (act.repeat && act.repeat > 1) ? (" (×" + act.repeat + ")") : ""
                                                return "Key Event: " + (act.key || "UNKNOWN") + rep
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

                        // Action Buttons
                        RowLayout {
                            spacing: 6

                            Button {
                                text: "Test Key"
                                flat: true
                                onClicked: {
                                    var act = modelData.action || {}
                                    if (act.type === "key") {
                                        edgepadController.testKeyAction(act.key)
                                    } else {
                                        edgepadController.testKeyAction("CUSTOM_ACTION")
                                    }
                                }
                            }

                            Button {
                                text: "Edit"
                                onClicked: {
                                    root.editingIndex = index
                                    ruleEditorDialog.openEditRule(modelData)
                                }
                            }

                            Button {
                                text: "Duplicate"
                                onClicked: edgepadController.duplicateGestureRule(index)
                            }

                            Button {
                                text: "Delete"
                                onClicked: edgepadController.removeGestureRule(index)
                            }
                        }
                    }
                }
            }
        }
    }

    // Add / Edit Rule Dialog
    Dialog {
        id: ruleEditorDialog
        title: root.editingIndex >= 0 ? "Edit Gesture Rule" : "Add New Gesture Rule"
        standardButtons: Dialog.Save | Dialog.Cancel
        modal: true
        width: 500
        height: 480
        anchors.centerIn: parent

        property string currentKeyName: "KEY_BRIGHTNESSUP"

        function openNewRule() {
            ruleNameField.text = "New Gesture"
            edgeCombo.currentIndex = 0
            directionCombo.currentIndex = 0
            actionTypeCombo.currentIndex = 0
            ruleEditorDialog.currentKeyName = "KEY_BRIGHTNESSUP"
            keyDisplayButton.text = "KEY_BRIGHTNESSUP"
            repeatSpin.value = 1
            commandField.text = ""
            ruleEditorDialog.open()
        }

        function openEditRule(rule) {
            ruleNameField.text = rule.name || ""
            edgeCombo.currentIndex = ["left", "right", "top", "bottom"].indexOf(rule.edge || "left")
            if (edgeCombo.currentIndex === -1) edgeCombo.currentIndex = 0
            directionCombo.currentIndex = ["up", "down", "left", "right"].indexOf(rule.direction || "up")
            if (directionCombo.currentIndex === -1) directionCombo.currentIndex = 0

            var act = rule.action || {}
            if (act.type === "key") {
                actionTypeCombo.currentIndex = 0
                ruleEditorDialog.currentKeyName = act.key || "KEY_BRIGHTNESSUP"
                keyDisplayButton.text = ruleEditorDialog.currentKeyName
                repeatSpin.value = act.repeat || 1
            } else if (act.type === "command") {
                actionTypeCombo.currentIndex = 1
                commandField.text = act.argv ? act.argv.join(" ") : ""
            } else {
                actionTypeCombo.currentIndex = 2
            }
            ruleEditorDialog.open()
        }

        onAccepted: {
            var actionObj = {}
            if (actionTypeCombo.currentIndex === 0) {
                actionObj = {
                    "type": "key",
                    "key": ruleEditorDialog.currentKeyName,
                    "repeat": repeatSpin.value
                }
            } else if (actionTypeCombo.currentIndex === 1) {
                var argv = commandField.text.trim().split(" ")
                actionObj = {
                    "type": "command",
                    "argv": argv
                }
            } else {
                actionObj = { "type": "log" }
            }

            var newRule = {
                "name": ruleNameField.text.trim(),
                "enabled": true,
                "edge": edgeCombo.currentText.toLowerCase(),
                "direction": directionCombo.currentText.toLowerCase(),
                "fingers": 1,
                "action": actionObj
            }

            if (root.editingIndex >= 0) {
                edgepadController.updateGestureRule(root.editingIndex, newRule)
            } else {
                edgepadController.addGestureRule(newRule)
            }
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            TextField {
                id: ruleNameField
                Layout.fillWidth: true
                placeholderText: "Gesture Name (e.g. Volume Up)"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "Touchpad Edge:"; color: "#bdc3c7"; font.pixelSize: 11 }
                    ComboBox {
                        id: edgeCombo
                        Layout.fillWidth: true
                        model: ["Left", "Right", "Top", "Bottom"]
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "Swipe Direction:"; color: "#bdc3c7"; font.pixelSize: 11 }
                    ComboBox {
                        id: directionCombo
                        Layout.fillWidth: true
                        model: ["Up", "Down", "Left", "Right"]
                    }
                }
            }

            Text { text: "Action Type:"; color: "#bdc3c7"; font.pixelSize: 11 }
            ComboBox {
                id: actionTypeCombo
                Layout.fillWidth: true
                model: ["Physical Keyboard Key Event", "Shell Command", "Log Event Only"]
            }

            // Key selection layout (when Keyboard Key Event is chosen)
            ColumnLayout {
                Layout.fillWidth: true
                visible: actionTypeCombo.currentIndex === 0
                spacing: 6

                Text { text: "Select Keyboard Event:"; color: "#bdc3c7"; font.pixelSize: 11 }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        id: keyDisplayButton
                        text: ruleEditorDialog.currentKeyName
                        highlighted: true
                        Layout.fillWidth: true
                        onClicked: {
                            keySelectorDialog.currentKey = ruleEditorDialog.currentKeyName
                            keySelectorDialog.knownKeysList = edgepadController.knownKeys
                            keySelectorDialog.open()
                        }
                    }

                    Button {
                        text: "Test Key"
                        onClicked: edgepadController.testKeyAction(ruleEditorDialog.currentKeyName)
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Repeat Count:"; color: "#bdc3c7"; font.pixelSize: 11; Layout.fillWidth: true }
                    SpinBox {
                        id: repeatSpin
                        from: 1
                        to: 10
                        value: 1
                    }
                }
            }

            // Command field (when Shell Command is chosen)
            ColumnLayout {
                Layout.fillWidth: true
                visible: actionTypeCombo.currentIndex === 1
                spacing: 4

                Text { text: "Command & Arguments:"; color: "#bdc3c7"; font.pixelSize: 11 }
                TextField {
                    id: commandField
                    Layout.fillWidth: true
                    placeholderText: "e.g. brightnessctl set +5%"
                }
            }
        }
    }

    KeySelectorDialog {
        id: keySelectorDialog
        onKeySelected: function(keyName, keyCode) {
            ruleEditorDialog.currentKeyName = keyName
            keyDisplayButton.text = keyName
        }
    }
}
