import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    Layout.fillWidth: true
    implicitHeight: mainCol.implicitHeight + 32
    radius: 12
    color: "#1c2027"
    border.color: edgepadController.encoderEnabled ? "#3daee9" : "#2a303c"
    border.width: 1

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // Header Row
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Rectangle {
                width: 36
                height: 36
                radius: 8
                color: edgepadController.encoderEnabled ? "#2980b9" : "#34495e"
                Text {
                    anchors.centerIn: parent
                    text: "🎛️"
                    font.pixelSize: 18
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                RowLayout {
                    spacing: 8
                    Text {
                        text: "Distance-Based Rotary Encoder Behavior"
                        font.bold: true
                        font.pixelSize: 15
                        color: "#ffffff"
                    }
                    Rectangle {
                        visible: edgepadController.encoderEnabled
                        implicitWidth: encBadge.implicitWidth + 8
                        implicitHeight: 18
                        radius: 4
                        color: "#27ae60"
                        Text {
                            id: encBadge
                            anchors.centerIn: parent
                            text: "Active (Discrete Ticks)"
                            color: "#ffffff"
                            font.bold: true
                            font.pixelSize: 9
                        }
                    }
                }
                Text {
                    text: "Continuous edge swipes emit discrete keyboard events proportional to travel distance (rotary encoder mode)"
                    font.pixelSize: 12
                    color: "#95a5a6"
                }
            }

            Button {
                text: "Restore Defaults"
                flat: true
                onClicked: edgepadController.restoreEncoderDefaults()
            }

            Switch {
                id: enableSwitch
                checked: edgepadController.encoderEnabled
                onToggled: edgepadController.setEncoderEnabled(checked)
            }
        }

        // Expanded Configuration Controls (visible when enabled)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 14
            visible: edgepadController.encoderEnabled

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#282d37"
            }

            // Slider Controls Grid
            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 16
                rowSpacing: 12

                // 1. Step Size
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 88
                    radius: 8
                    color: "#16181f"
                    border.color: "#252a36"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Step Size (Distance / Tick)"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#ffffff"
                                Layout.fillWidth: true
                            }
                            Text {
                                text: Math.round(edgepadController.encoderStepSize) + " units"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#3daee9"
                            }
                        }

                        Text {
                            text: "Units per discrete key press (shorter = more sensitive)"
                            font.pixelSize: 10
                            color: "#7f8c8d"
                        }

                        Slider {
                            Layout.fillWidth: true
                            from: 10
                            to: 200
                            stepSize: 5
                            value: edgepadController.encoderStepSize
                            onMoved: edgepadController.setEncoderStepSize(value)
                        }
                    }
                }

                // 2. Dead Zone
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 88
                    radius: 8
                    color: "#16181f"
                    border.color: "#252a36"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Dead Zone (Jitter Filter)"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#ffffff"
                                Layout.fillWidth: true
                            }
                            Text {
                                text: Math.round(edgepadController.encoderDeadZone) + " units"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#3daee9"
                            }
                        }

                        Text {
                            text: "Initial displacement required before ticks start accumulating"
                            font.pixelSize: 10
                            color: "#7f8c8d"
                        }

                        Slider {
                            Layout.fillWidth: true
                            from: 0
                            to: 50
                            stepSize: 2
                            value: edgepadController.encoderDeadZone
                            onMoved: edgepadController.setEncoderDeadZone(value)
                        }
                    }
                }

                // 3. Repeat Interval
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 88
                    radius: 8
                    color: "#16181f"
                    border.color: "#252a36"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Key Repeat Interval"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#ffffff"
                                Layout.fillWidth: true
                            }
                            Text {
                                text: edgepadController.encoderRepeatIntervalMs + " ms"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#3daee9"
                            }
                        }

                        Text {
                            text: "Spacing between consecutive key presses (5 - 100 ms)"
                            font.pixelSize: 10
                            color: "#7f8c8d"
                        }

                        Slider {
                            Layout.fillWidth: true
                            from: 5
                            to: 100
                            stepSize: 5
                            value: edgepadController.encoderRepeatIntervalMs
                            onMoved: edgepadController.setEncoderRepeatIntervalMs(Math.round(value))
                        }
                    }
                }
            }

            // Live Diagnostic View Box
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 76
                radius: 8
                color: "#12141a"
                border.color: edgepadController.encoderLiveTicks > 0 ? "#3daee9" : "#222733"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 16

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: "Live Diagnostic Monitor"
                            font.bold: true
                            font.pixelSize: 12
                            color: "#ffffff"
                        }
                        Text {
                            text: "Real-time displacement and tick counts"
                            font.pixelSize: 10
                            color: "#7f8c8d"
                        }
                    }

                    Rectangle {
                        width: 1
                        Layout.fillHeight: true
                        color: "#282d37"
                    }

                    // Active Edge HUD
                    ColumnLayout {
                        Layout.preferredWidth: 85
                        spacing: 2
                        Text {
                            text: "Active Edge"
                            font.pixelSize: 10
                            color: "#95a5a6"
                        }
                        Text {
                            text: edgepadController.encoderLiveEdge !== "None" ? edgepadController.encoderLiveEdge : "—"
                            font.bold: true
                            font.pixelSize: 13
                            color: edgepadController.encoderLiveEdge !== "None" ? "#3daee9" : "#7f8c8d"
                        }
                    }

                    // Swipe Direction HUD
                    ColumnLayout {
                        Layout.preferredWidth: 90
                        spacing: 2
                        Text {
                            text: "Direction"
                            font.pixelSize: 10
                            color: "#95a5a6"
                        }
                        RowLayout {
                            spacing: 4
                            Text {
                                text: {
                                    if (edgepadController.encoderLiveDirection === "Up") return "▲ UP"
                                    if (edgepadController.encoderLiveDirection === "Down") return "▼ DOWN"
                                    return "— IDLE"
                                }
                                font.bold: true
                                font.pixelSize: 13
                                color: {
                                    if (edgepadController.encoderLiveDirection === "Up") return "#27ae60"
                                    if (edgepadController.encoderLiveDirection === "Down") return "#e67e22"
                                    return "#7f8c8d"
                                }
                            }
                        }
                    }

                    // Incremental Movement HUD
                    ColumnLayout {
                        Layout.preferredWidth: 100
                        spacing: 2
                        Text {
                            text: "Delta / Tick"
                            font.pixelSize: 10
                            color: "#95a5a6"
                        }
                        Text {
                            text: edgepadController.encoderLiveIncremental > 0 ? (Math.round(edgepadController.encoderLiveIncremental) + " units") : "—"
                            font.bold: true
                            font.pixelSize: 13
                            color: "#ffffff"
                        }
                    }

                    // Accumulated Distance HUD
                    ColumnLayout {
                        Layout.preferredWidth: 115
                        spacing: 2
                        Text {
                            text: "Accumulated"
                            font.pixelSize: 10
                            color: "#95a5a6"
                        }
                        Text {
                            text: Math.round(edgepadController.encoderLiveDistance) + " units"
                            font.bold: true
                            font.pixelSize: 13
                            color: "#ffffff"
                        }
                    }

                    // Generated Tick Count HUD
                    ColumnLayout {
                        Layout.preferredWidth: 95
                        spacing: 2
                        Text {
                            text: "Key Events"
                            font.pixelSize: 10
                            color: "#95a5a6"
                        }
                        Text {
                            text: edgepadController.encoderLiveTicks + " ticks"
                            font.bold: true
                            font.pixelSize: 13
                            color: edgepadController.encoderLiveTicks > 0 ? "#3daee9" : "#ffffff"
                        }
                    }

                    // Last Key Emitted HUD
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "Last Key Emitted"
                            font.pixelSize: 10
                            color: "#95a5a6"
                        }
                        Text {
                            text: edgepadController.encoderLiveKey || "None"
                            font.bold: true
                            font.pixelSize: 12
                            color: edgepadController.encoderLiveKey ? "#2ecc71" : "#7f8c8d"
                            elide: Text.ElideRight
                        }
                    }

                    Button {
                        text: "Reset"
                        flat: true
                        onClicked: edgepadController.resetEncoderDiagnostics()
                    }
                }
            }
        }
    }
}
