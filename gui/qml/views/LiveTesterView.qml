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

        // Page Header
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: "Live Gesture Tester & Diagnostic Pad"
                    font.bold: true
                    font.pixelSize: 22
                    color: "#ffffff"
                }
                Text {
                    text: "Verify edge detection and key event emission in real time without affecting desktop state"
                    font.pixelSize: 13
                    color: "#95a5a6"
                }
            }

            // Test Mode Switch Pill
            Rectangle {
                implicitWidth: testModeRow.implicitWidth + 16
                implicitHeight: 36
                radius: 18
                color: edgepadController.testMode ? "#27ae60" : "#2c3e50"
                border.color: "#3daee9"
                border.width: 1

                RowLayout {
                    id: testModeRow
                    anchors.centerIn: parent
                    spacing: 8
                    Text {
                        text: "Test Mode (Safe Simulation)"
                        font.bold: true
                        font.pixelSize: 11
                        color: "#ffffff"
                    }
                    Switch {
                        checked: edgepadController.testMode
                        onToggled: edgepadController.setTestMode(checked)
                    }
                }
            }
        }

        // Live Recognition Display Pad
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            // Visual Touchpad Canvas
            Rectangle {
                Layout.preferredWidth: 460
                Layout.preferredHeight: 320
                radius: 12
                color: "#1a1d24"
                border.color: edgepadController.lastGesture.event ? "#3daee9" : "#2f3542"
                border.width: 2

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Interactive Touchpad Visualizer"
                            font.bold: true
                            font.pixelSize: 13
                            color: "#ffffff"
                            Layout.fillWidth: true
                        }
                        Text {
                            text: edgepadController.connectedToIpc ? "🟢 IPC Connected" : "⚪ IPC Offline (Polling)"
                            font.pixelSize: 11
                            color: edgepadController.connectedToIpc ? "#27ae60" : "#7f8c8d"
                        }
                    }

                    TouchpadCanvas {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        edgeWidthFraction: edgepadController.edgeSettings.edge_width || 0.12
                        activeEdge: edgepadController.lastGesture.zone || ""
                        activeDirection: edgepadController.lastGesture.direction || ""
                        xMax: edgepadController.selectedDeviceDetails.x_max || 2905
                        yMax: edgepadController.selectedDeviceDetails.y_max || 1766
                    }
                }
            }

            // Live Recognition Data Card
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 320
                radius: 12
                color: "#21252d"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Text {
                        text: "Real-Time Recognition Telemetry"
                        font.bold: true
                        font.pixelSize: 15
                        color: "#ffffff"
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: 10
                        columnSpacing: 16

                        Text { text: "Detected Edge Zone:"; color: "#bdc3c7"; font.pixelSize: 12 }
                        Text {
                            text: (edgepadController.lastGesture.zone || "None").toUpperCase()
                            color: "#3daee9"
                            font.bold: true
                            font.pixelSize: 13
                        }

                        Text { text: "Swipe Direction:"; color: "#bdc3c7"; font.pixelSize: 12 }
                        Text {
                            text: (edgepadController.lastGesture.direction || "None").toUpperCase()
                            color: "#3daee9"
                            font.bold: true
                            font.pixelSize: 13
                        }

                        Text { text: "Recognized Action:"; color: "#bdc3c7"; font.pixelSize: 12 }
                        Text {
                            text: edgepadController.lastGesture.key ||
                                  (edgepadController.lastGesture.action ? JSON.stringify(edgepadController.lastGesture.action) : "None")
                            color: "#ffffff"
                            font.bold: true
                            font.pixelSize: 13
                        }

                        Text { text: "Action Status:"; color: "#bdc3c7"; font.pixelSize: 12 }
                        Text {
                            text: {
                                if (!edgepadController.lastGesture.event) return "Idle"
                                return edgepadController.lastGesture.success ? "✓ Emitted Successfully" : "✗ Execution Failed"
                            }
                            color: edgepadController.lastGesture.success ? "#27ae60" : "#e74c3c"
                            font.bold: true
                            font.pixelSize: 12
                        }

                        Text { text: "Mode:"; color: "#bdc3c7"; font.pixelSize: 12 }
                        Text {
                            text: edgepadController.lastGesture.test_mode ? "Simulated Action (Safe)" : "Physical Key Event"
                            color: edgepadController.lastGesture.test_mode ? "#f39c12" : "#27ae60"
                            font.pixelSize: 12
                        }

                        Text { text: "Timestamp:"; color: "#bdc3c7"; font.pixelSize: 12 }
                        Text {
                            text: edgepadController.lastGesture.time || "N/A"
                            color: "#95a5a6"
                            font.pixelSize: 12
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Quick test buttons
                    Text {
                        text: "Safe Key Test Triggers:"
                        font.bold: true
                        font.pixelSize: 11
                        color: "#95a5a6"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                            text: "Brightness +"
                            Layout.fillWidth: true
                            onClicked: edgepadController.testKeyAction("KEY_BRIGHTNESSUP")
                        }
                        Button {
                            text: "Brightness -"
                            Layout.fillWidth: true
                            onClicked: edgepadController.testKeyAction("KEY_BRIGHTNESSDOWN")
                        }
                        Button {
                            text: "Volume +"
                            Layout.fillWidth: true
                            onClicked: edgepadController.testKeyAction("KEY_VOLUMEUP")
                        }
                        Button {
                            text: "Volume -"
                            Layout.fillWidth: true
                            onClicked: edgepadController.testKeyAction("KEY_VOLUMEDOWN")
                        }
                    }
                }
            }
        }
    }
}
