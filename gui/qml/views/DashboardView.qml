import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root

    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Header Title & Intro
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: "Dashboard Overview"
                    font.bold: true
                    font.pixelSize: 22
                    color: "#ffffff"
                }

                Text {
                    text: "Monitor edge gesture engine, touchpad status, and active mappings"
                    font.pixelSize: 13
                    color: "#95a5a6"
                }
            }

            StatusBadge {
                status: edgepadController.daemonStatus
            }
        }

        // Top Status Cards Grid
        GridLayout {
            Layout.fillWidth: true
            columns: 3
            rowSpacing: 14
            columnSpacing: 14

            // Card 1: Master Enable / Service State
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 140
                radius: 10
                color: "#21252d"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Master Enable"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#ffffff"
                            Layout.fillWidth: true
                        }
                        Switch {
                            checked: edgepadController.masterEnabled
                            onToggled: edgepadController.setMasterEnabled(checked)
                        }
                    }

                    Text {
                        text: edgepadController.masterEnabled ? "Edge gestures are globally active" : "Gestures globally paused"
                        color: edgepadController.masterEnabled ? "#27ae60" : "#e74c3c"
                        font.pixelSize: 11
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                            text: edgepadController.daemonStatus === "running" ? "Restart Engine" : "Start Engine"
                            highlighted: true
                            onClicked: {
                                if (edgepadController.daemonStatus === "running") {
                                    edgepadController.restartService()
                                } else {
                                    edgepadController.startService()
                                }
                            }
                        }

                        Button {
                            text: "Stop"
                            enabled: edgepadController.daemonStatus === "running"
                            onClicked: edgepadController.stopService()
                        }
                    }
                }
            }

            // Card 2: Touchpad Hardware
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 140
                radius: 10
                color: "#21252d"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text {
                        text: "Selected Touchpad"
                        font.bold: true
                        font.pixelSize: 14
                        color: "#ffffff"
                    }

                    Text {
                        text: edgepadController.selectedDeviceDetails.name || "Default Touchpad"
                        font.bold: true
                        font.pixelSize: 12
                        color: "#3daee9"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Text {
                        text: "Node: " + (edgepadController.selectedDeviceDetails.path || "auto") +
                              " (" + (edgepadController.selectedDeviceDetails.id || "093a:3848") + ")"
                        color: "#bdc3c7"
                        font.pixelSize: 11
                    }

                    Text {
                        text: "Axis: " + (edgepadController.selectedDeviceDetails.x_range || "0..2905") +
                              " × " + (edgepadController.selectedDeviceDetails.y_range || "0..1766")
                        color: "#7f8c8d"
                        font.pixelSize: 10
                    }

                    Item { Layout.fillHeight: true }

                    Button {
                        text: "Configure Touchpad Zones →"
                        flat: true
                        Layout.alignment: Qt.AlignRight
                        onClicked: navStack.currentIndex = 2 // Edge Zones
                    }
                }
            }

            // Card 3: Start At Login & Presets
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 140
                radius: 10
                color: "#21252d"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Start at Login"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#ffffff"
                            Layout.fillWidth: true
                        }
                        Switch {
                            checked: edgepadController.startAtLogin
                            onToggled: edgepadController.setStartAtLogin(checked)
                        }
                    }

                    Text {
                        text: "Active Gestures: " + edgepadController.gestureRules.length + " configured"
                        color: "#bdc3c7"
                        font.pixelSize: 12
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                            text: "Apply Default Preset"
                            onClicked: edgepadController.applyDefaultPreset()
                        }

                        Button {
                            text: "Live Tester →"
                            highlighted: true
                            onClicked: navStack.currentIndex = 4 // Live Tester
                        }
                    }
                }
            }
        }

        // Real-Time Gesture Activity Banner
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 90
            radius: 10
            color: "#1a1e26"
            border.color: edgepadController.lastGesture.event ? "#3daee9" : "#2f3542"
            border.width: edgepadController.lastGesture.event ? 2 : 1

            Behavior on border.color {
                ColorAnimation { duration: 300 }
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                Rectangle {
                    width: 44
                    height: 44
                    radius: 22
                    color: edgepadController.lastGesture.event ? "#3daee9" : "#2c3e50"

                    Text {
                        anchors.centerIn: parent
                        text: "⚡"
                        font.pixelSize: 20
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    Text {
                        text: "Last Detected Touchpad Activity"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    Text {
                        text: {
                            if (!edgepadController.lastGesture.event) {
                                return "Waiting for touchpad edge gesture... (Perform a swipe on left or right edge)"
                            }
                            var g = edgepadController.lastGesture
                            var edge = (g.zone || "unknown").toUpperCase()
                            var dir = (g.direction || "unknown").toUpperCase()
                            var act = g.key || (g.action ? JSON.stringify(g.action) : "None")
                            var mode = g.test_mode ? " [Simulated/Test Mode]" : ""
                            return "Edge: " + edge + " | Direction: " + dir + " | Emitted Action: " + act + mode + " at " + (g.time || "")
                        }
                        color: edgepadController.lastGesture.event ? "#3daee9" : "#7f8c8d"
                        font.pixelSize: 12
                    }
                }

                Button {
                    text: "Open Live Tester"
                    onClicked: navStack.currentIndex = 4
                }
            }
        }

        // Default Mappings Summary Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 180
            radius: 10
            color: "#21252d"
            border.color: "#2f3542"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Core Physical Keyboard Mappings"
                        font.bold: true
                        font.pixelSize: 15
                        color: "#ffffff"
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "Edit Gestures →"
                        flat: true
                        onClicked: navStack.currentIndex = 1 // Gestures
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    rowSpacing: 10
                    columnSpacing: 20

                    // Left Edge Gestures
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 80
                        radius: 8
                        color: "#1a1d24"
                        border.color: "#2c3e50"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4
                            Text { text: "LEFT EDGE (Display Brightness)"; font.bold: true; font.pixelSize: 11; color: "#f39c12" }
                            Text { text: "↑ Swipe Up   → Emits KEY_BRIGHTNESSUP (Code 225)"; font.pixelSize: 11; color: "#ecf0f1" }
                            Text { text: "↓ Swipe Down → Emits KEY_BRIGHTNESSDOWN (Code 224)"; font.pixelSize: 11; color: "#ecf0f1" }
                        }
                    }

                    // Right Edge Gestures
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 80
                        radius: 8
                        color: "#1a1d24"
                        border.color: "#2c3e50"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4
                            Text { text: "RIGHT EDGE (Audio Volume)"; font.bold: true; font.pixelSize: 11; color: "#27ae60" }
                            Text { text: "↑ Swipe Up   → Emits KEY_VOLUMEUP (Code 115)"; font.pixelSize: 11; color: "#ecf0f1" }
                            Text { text: "↓ Swipe Down → Emits KEY_VOLUMEDOWN (Code 114)"; font.pixelSize: 11; color: "#ecf0f1" }
                        }
                    }
                }
            }
        }
    }
}
