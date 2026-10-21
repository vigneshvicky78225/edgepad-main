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
                    text: "Live Gesture Tester"
                    font.bold: true
                    font.pixelSize: 20
                    color: "#ffffff"
                }
                Text {
                    text: "Simulate and verify gesture detection in real time"
                    font.pixelSize: 12
                    color: "#94a3b8"
                }
            }

            // Test Mode Switch Pill
            Rectangle {
                implicitWidth: testModeRow.implicitWidth + 16
                implicitHeight: 34
                radius: 17
                color: (edgepadController && edgepadController.testMode) ? "#163324" : "#28303f"
                border.color: (edgepadController && edgepadController.testMode) ? "#22c55e" : "#475569"
                border.width: 1

                RowLayout {
                    id: testModeRow
                    anchors.centerIn: parent
                    spacing: 8
                    Text {
                        text: "Safe Simulation Mode"
                        font.bold: true
                        font.pixelSize: 11
                        color: (edgepadController && edgepadController.testMode) ? "#4ade80" : "#cbd5e1"
                    }
                    Switch {
                        checked: Boolean(edgepadController && edgepadController.testMode)
                        onToggled: if (edgepadController) edgepadController.setTestMode(checked)
                    }
                }
            }
        }

        // Responsive Layout: Touchpad Canvas on Left (or Top) and Telemetry Data on Right (or Bottom)
        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 860 ? 2 : 1
            rowSpacing: 16
            columnSpacing: 16

            // Visual Touchpad Canvas
            Rectangle {
                Layout.fillWidth: root.width <= 860
                Layout.preferredWidth: root.width > 860 ? 460 : -1
                Layout.maximumWidth: root.width <= 860 ? 540 : -1
                Layout.alignment: Qt.AlignTop | (root.width <= 860 ? Qt.AlignHCenter : Qt.AlignLeft)
                Layout.preferredHeight: 320
                radius: 12
                color: "#1a1d24"
                border.color: (edgepadController && edgepadController.lastGesture && edgepadController.lastGesture.event) ? "#3daee9" : "#2f3542"
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
                            text: (edgepadController && edgepadController.connectedToIpc) ? "🟢 Connected" : "⚪ Offline"
                            font.pixelSize: 11
                            color: (edgepadController && edgepadController.connectedToIpc) ? "#27ae60" : "#7f8c8d"
                        }
                    }

                    TouchpadCanvas {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        leftEdgeWidthFraction: (edgepadController && edgepadController.hitboxSettings && edgepadController.hitboxSettings.left_edge_width !== undefined) ? edgepadController.hitboxSettings.left_edge_width : 0.12
                        rightEdgeWidthFraction: (edgepadController && edgepadController.hitboxSettings && edgepadController.hitboxSettings.right_edge_width !== undefined) ? edgepadController.hitboxSettings.right_edge_width : 0.12
                        topEdgeHeightFraction: (edgepadController && edgepadController.hitboxSettings && edgepadController.hitboxSettings.top_edge_height !== undefined) ? edgepadController.hitboxSettings.top_edge_height : 0.12
                        bottomEdgeHeightFraction: (edgepadController && edgepadController.hitboxSettings && edgepadController.hitboxSettings.bottom_edge_height !== undefined) ? edgepadController.hitboxSettings.bottom_edge_height : 0.12
                        cornerWidthFraction: (edgepadController && edgepadController.hitboxSettings && edgepadController.hitboxSettings.corner_width !== undefined) ? edgepadController.hitboxSettings.corner_width : 0.15
                        cornerHeightFraction: (edgepadController && edgepadController.hitboxSettings && edgepadController.hitboxSettings.corner_height !== undefined) ? edgepadController.hitboxSettings.corner_height : 0.15
                        activeZone: (edgepadController && edgepadController.lastGesture) ? (edgepadController.lastGesture.zone || "") : ""
                        activeDirection: (edgepadController && edgepadController.lastGesture) ? (edgepadController.lastGesture.direction || "") : ""
                        xMin: (edgepadController && edgepadController.selectedDeviceDetails) ? (edgepadController.selectedDeviceDetails.x_min || 0) : 0
                        xMax: (edgepadController && edgepadController.selectedDeviceDetails) ? (edgepadController.selectedDeviceDetails.x_max || 2905) : 2905
                        yMin: (edgepadController && edgepadController.selectedDeviceDetails) ? (edgepadController.selectedDeviceDetails.y_min || 0) : 0
                        yMax: (edgepadController && edgepadController.selectedDeviceDetails) ? (edgepadController.selectedDeviceDetails.y_max || 1766) : 1766
                    }
                }
            }

            // Live Recognition Data Card
            Rectangle {
                Layout.fillWidth: true
                Layout.minimumHeight: 340
                implicitHeight: telemetryColLayout.implicitHeight + 32
                radius: 12
                color: "#1b1f28"
                border.color: "#28303f"
                border.width: 1

                ColumnLayout {
                    id: telemetryColLayout
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    Text {
                        text: "Real-Time Telemetry"
                        font.bold: true
                        font.pixelSize: 14
                        color: "#ffffff"
                    }

                    GridLayout {
                        id: telemetryGrid
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: 8
                        columnSpacing: 14

                        readonly property var curGesture: (edgepadController && edgepadController.lastGesture) ? edgepadController.lastGesture : {}
                        readonly property var curSettings: (edgepadController && edgepadController.gestureSettings) ? edgepadController.gestureSettings : {}

                        // Hitbox Detection
                        Text { text: "Active Zone:"; color: "#94a3b8"; font.pixelSize: 11 }
                        RowLayout {
                            spacing: 6
                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: (telemetryGrid.curGesture.zone || "").indexOf("corner") !== -1 || (telemetryGrid.curGesture.zone || "").indexOf("-") !== -1 ? "#af7ac5" : "#3daee9"
                            }
                            Text {
                                text: (telemetryGrid.curGesture.zone || "Normal Pointer Area").toUpperCase()
                                color: (telemetryGrid.curGesture.zone || "").indexOf("corner") !== -1 || (telemetryGrid.curGesture.zone || "").indexOf("-") !== -1 ? "#af7ac5" : "#3daee9"
                                font.bold: true
                                font.pixelSize: 12
                            }
                        }

                        // Gesture Recognition
                        Text { text: "Gesture Direction:"; color: "#94a3b8"; font.pixelSize: 11 }
                        Text {
                            text: (telemetryGrid.curGesture.direction || "None").toUpperCase()
                            color: "#4ade80"
                            font.bold: true
                            font.pixelSize: 12
                        }

                        Text { text: "Action Emitted:"; color: "#94a3b8"; font.pixelSize: 11 }
                        Text {
                            text: telemetryGrid.curGesture.key ||
                                  (telemetryGrid.curGesture.action ? JSON.stringify(telemetryGrid.curGesture.action) : "None")
                            color: "#ffffff"
                            font.bold: true
                            font.pixelSize: 12
                        }

                        Text { text: "Event Source:"; color: "#94a3b8"; font.pixelSize: 11 }
                        Text {
                            text: {
                                if (!telemetryGrid.curGesture.event) return "Idle (Awaiting Input)"
                                return telemetryGrid.curGesture.is_simulated ? "Simulated Event" : "Hardware Input"
                            }
                            color: telemetryGrid.curGesture.is_simulated ? "#c084fc" : (telemetryGrid.curGesture.event ? "#38bdf8" : "#64748b")
                            font.bold: true
                            font.pixelSize: 11
                        }

                        Text { text: "Timestamp:"; color: "#94a3b8"; font.pixelSize: 11 }
                        Text {
                            text: telemetryGrid.curGesture.time || "N/A"
                            color: "#94a3b8"
                            font.pixelSize: 11
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Safe Tap Action Triggers (Simulated)
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Simulated Tap Triggers:"
                            font.bold: true
                            font.pixelSize: 11
                            color: "#cbd5e1"
                            Layout.fillWidth: true
                        }
                        Button {
                            text: "Configure Tap Actions →"
                            flat: true
                            onClicked: appWindow.navigateToPage(1)
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                            text: "🧪 ↖ Top-Left 2×"
                            Layout.fillWidth: true
                            onClicked: edgepadController.testGestureAction("top-left", "double-tap", "shortcut", "KEY_LEFTCTRL+KEY_LEFTSHIFT+KEY_M", "Top-Left Double Tap")
                        }
                        Button {
                            text: "🧪 ↗ Top-Right 2×"
                            Layout.fillWidth: true
                            onClicked: edgepadController.testGestureAction("top-right", "double-tap", "shortcut", "KEY_LEFTALT+KEY_F4", "Top-Right Double Tap")
                        }
                        Button {
                            text: "🧪 ↙ Bottom-Left 2×"
                            Layout.fillWidth: true
                            onClicked: edgepadController.testGestureAction("bottom-left", "double-tap", "shortcut", "KEY_LEFTMETA", "Bottom-Left Double Tap")
                        }
                        Button {
                            text: "🧪 ↘ Bottom-Right 2×"
                            Layout.fillWidth: true
                            onClicked: edgepadController.testGestureAction("bottom-right", "double-tap", "shortcut", "KEY_LEFTCTRL+KEY_LEFTALT+KEY_T", "Bottom-Right Double Tap")
                        }
                    }

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

        // Encoder Telemetry & Controls
        EncoderSettingsCard {
            Layout.fillWidth: true
        }
    }
}
