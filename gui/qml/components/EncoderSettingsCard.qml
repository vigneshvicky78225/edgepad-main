import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    readonly property bool liveEncoderActive: Boolean(edgepadController && edgepadController.encoderEnabled)
    readonly property int liveTicks: edgepadController ? (edgepadController.encoderLiveTicks || 0) : 0
    readonly property string liveEdge: edgepadController ? (edgepadController.encoderLiveEdge || "None") : "None"
    readonly property string liveDirection: edgepadController ? (edgepadController.encoderLiveDirection || "") : ""
    readonly property real liveIncremental: edgepadController ? (edgepadController.encoderLiveIncremental || 0.0) : 0.0
    readonly property real liveDistance: edgepadController ? (edgepadController.encoderLiveDistance || 0.0) : 0.0
    readonly property string liveKey: edgepadController ? (edgepadController.encoderLiveKey || "") : ""

    property bool showTelemetry: false

    Layout.fillWidth: true
    implicitHeight: mainCol.implicitHeight + 28
    radius: 10
    color: "#1c2027"
    border.color: liveEncoderActive ? "#3daee9" : "#2a303c"
    border.width: 1

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        // Header Row
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: "Distance-Based Rotary Encoder"
                font.bold: true
                font.pixelSize: 15
                color: "#ffffff"
                Layout.fillWidth: true
            }

            Button {
                text: "Restore Defaults"
                flat: true
                onClicked: if (edgepadController) edgepadController.restoreEncoderDefaults()
            }

            Switch {
                id: enableSwitch
                checked: Boolean(edgepadController && edgepadController.encoderEnabled)
                onToggled: if (edgepadController) edgepadController.setEncoderEnabled(checked)
            }
        }

        // Expanded Configuration Controls
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 12
            visible: liveEncoderActive

            // Slider Controls Grid
            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 760 ? 3 : (root.width > 500 ? 2 : 1)
                columnSpacing: 14
                rowSpacing: 10

                // 1. Step Size
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 74
                    radius: 8
                    color: "#16181f"
                    border.color: "#252a36"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Step Size"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#ffffff"
                                Layout.fillWidth: true
                            }
                            Text {
                                text: Math.round(edgepadController ? (edgepadController.encoderStepSize || 50) : 50) + " units"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#3daee9"
                            }
                        }

                        Slider {
                            Layout.fillWidth: true
                            from: 10
                            to: 200
                            stepSize: 5
                            value: edgepadController ? (edgepadController.encoderStepSize || 50) : 50
                            onMoved: if (edgepadController) edgepadController.setEncoderStepSize(value)
                        }
                    }
                }

                // 2. Dead Zone
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 74
                    radius: 8
                    color: "#16181f"
                    border.color: "#252a36"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Dead Zone"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#ffffff"
                                Layout.fillWidth: true
                            }
                            Text {
                                text: Math.round(edgepadController ? (edgepadController.encoderDeadZone || 10) : 10) + " units"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#3daee9"
                            }
                        }

                        Slider {
                            Layout.fillWidth: true
                            from: 0
                            to: 50
                            stepSize: 2
                            value: edgepadController ? (edgepadController.encoderDeadZone || 10) : 10
                            onMoved: if (edgepadController) edgepadController.setEncoderDeadZone(value)
                        }
                    }
                }

                // 3. Repeat Interval
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 74
                    radius: 8
                    color: "#16181f"
                    border.color: "#252a36"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Repeat Interval"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#ffffff"
                                Layout.fillWidth: true
                            }
                            Text {
                                text: Math.round(edgepadController ? (edgepadController.encoderRepeatIntervalMs || 20) : 20) + " ms"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#3daee9"
                            }
                        }

                        Slider {
                            Layout.fillWidth: true
                            from: 5
                            to: 100
                            stepSize: 5
                            value: edgepadController ? (edgepadController.encoderRepeatIntervalMs || 20) : 20
                            onMoved: if (edgepadController) edgepadController.setEncoderRepeatIntervalMs(value)
                        }
                    }
                }
            }

            // Collapsible Live Telemetry HUD for debugging/tuning
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: root.showTelemetry ? "Hide Encoder Telemetry" : "Show Encoder Telemetry"
                    flat: true
                    onClicked: root.showTelemetry = !root.showTelemetry
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: telemetryRow.implicitHeight + 16
                radius: 8
                color: "#13161c"
                border.color: "#28303f"
                border.width: 1
                visible: root.showTelemetry

                RowLayout {
                    id: telemetryRow
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    ColumnLayout {
                        spacing: 1
                        Text { text: "Edge"; font.pixelSize: 10; color: "#95a5a6" }
                        Text { text: liveEdge; font.bold: true; font.pixelSize: 12; color: "#3daee9" }
                    }

                    ColumnLayout {
                        spacing: 1
                        Text { text: "Direction"; font.pixelSize: 10; color: "#95a5a6" }
                        Text { text: liveDirection || "Idle"; font.bold: true; font.pixelSize: 12; color: "#2ecc71" }
                    }

                    ColumnLayout {
                        spacing: 1
                        Text { text: "Distance"; font.pixelSize: 10; color: "#95a5a6" }
                        Text { text: Math.round(liveDistance) + " px"; font.bold: true; font.pixelSize: 12; color: "#ffffff" }
                    }

                    ColumnLayout {
                        spacing: 1
                        Text { text: "Ticks"; font.pixelSize: 10; color: "#95a5a6" }
                        Text { text: liveTicks + " ticks"; font.bold: true; font.pixelSize: 12; color: "#f39c12" }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text { text: "Last Key"; font.pixelSize: 10; color: "#95a5a6" }
                        Text { text: liveKey || "None"; font.bold: true; font.pixelSize: 12; color: "#38bdf8" }
                    }

                    Button {
                        text: "Reset"
                        flat: true
                        onClicked: if (edgepadController) edgepadController.resetEncoderDiagnostics()
                    }
                }
            }
        }
    }
}
