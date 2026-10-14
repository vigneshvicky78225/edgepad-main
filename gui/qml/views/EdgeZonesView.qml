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
                    text: "Edge Zones & Sensitivity Calibration"
                    font.bold: true
                    font.pixelSize: 22
                    color: "#ffffff"
                }
                Text {
                    text: "Calibrate edge zone widths, minimum swipe travel, and horizontal drift thresholds"
                    font.pixelSize: 13
                    color: "#95a5a6"
                }
            }

            Button {
                text: "Restore Hardware Defaults"
                onClicked: {
                    edgeWidthSlider.value = 12
                    minTravelSlider.value = 250
                    maxDriftSlider.value = 120
                    cooldownSlider.value = 250
                    tapDurationSlider.value = 200
                    tapMovementSlider.value = 50
                    saveSettings()
                }
            }
        }

        // Two-column layout: Touchpad Canvas on Left, Sliders on Right
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            // Left Column: Interactive Touchpad Illustration
            Rectangle {
                Layout.preferredWidth: 440
                Layout.preferredHeight: 380
                radius: 12
                color: "#1a1d24"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    Text {
                        text: "Touchpad Visual Geometry"
                        font.bold: true
                        font.pixelSize: 14
                        color: "#ffffff"
                    }

                    TouchpadCanvas {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        edgeWidthFraction: edgeWidthSlider.value / 100.0
                        xMax: edgepadController.selectedDeviceDetails.x_max || 2905
                        yMax: edgepadController.selectedDeviceDetails.y_max || 1766
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Active Width: " + edgeWidthSlider.value + "% per side"
                            color: "#3daee9"
                            font.bold: true
                            font.pixelSize: 11
                            Layout.fillWidth: true
                        }
                        Text {
                            text: "Center Area: " + (100 - edgeWidthSlider.value * 2) + "% width"
                            color: "#95a5a6"
                            font.pixelSize: 11
                        }
                    }
                }
            }

            // Right Column: Calibration Controls
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 380
                radius: 12
                color: "#21252d"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Text {
                        text: "Calibration Parameters"
                        font.bold: true
                        font.pixelSize: 15
                        color: "#ffffff"
                    }

                    // 1. Edge Zone Width Slider
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Edge Zone Width:"; color: "#ecf0f1"; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: edgeWidthSlider.value + "%"; color: "#3daee9"; font.bold: true; font.pixelSize: 12 }
                        }
                        Slider {
                            id: edgeWidthSlider
                            Layout.fillWidth: true
                            from: 5
                            to: 35
                            stepSize: 1
                            value: Math.round((edgepadController.edgeSettings.edge_width || 0.12) * 100)
                            onMoved: saveSettings()
                        }
                    }

                    // 2. Minimum Swipe Travel Distance
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Minimum Swipe Distance:"; color: "#ecf0f1"; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: minTravelSlider.value + " units"; color: "#3daee9"; font.bold: true; font.pixelSize: 12 }
                        }
                        Slider {
                            id: minTravelSlider
                            Layout.fillWidth: true
                            from: 50
                            to: 800
                            stepSize: 25
                            value: edgepadController.edgeSettings.min_travel || 250
                            onMoved: saveSettings()
                        }
                    }

                    // 3. Max Permitted Horizontal Drift
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Maximum Horizontal Drift:"; color: "#ecf0f1"; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: maxDriftSlider.value + " units"; color: "#3daee9"; font.bold: true; font.pixelSize: 12 }
                        }
                        Slider {
                            id: maxDriftSlider
                            Layout.fillWidth: true
                            from: 20
                            to: 400
                            stepSize: 10
                            value: edgepadController.edgeSettings.max_drift || 120
                            onMoved: saveSettings()
                        }
                    }

                    // 4. Gesture Cooldown Duration
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Gesture Repeat Cooldown:"; color: "#ecf0f1"; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: cooldownSlider.value + " ms"; color: "#3daee9"; font.bold: true; font.pixelSize: 12 }
                        }
                        Slider {
                            id: cooldownSlider
                            Layout.fillWidth: true
                            from: 50
                            to: 1000
                            stepSize: 50
                            value: edgepadController.edgeSettings.cooldown_ms || 250
                            onMoved: saveSettings()
                        }
                    }

                    Item { Layout.fillHeight: true }

                    Button {
                        text: "Save & Apply Calibration"
                        highlighted: true
                        Layout.fillWidth: true
                        onClicked: {
                            saveSettings()
                            edgepadController.saveConfiguration()
                        }
                    }
                }
            }
        }

        // Tap Timing & Advanced Calibration Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 130
            radius: 12
            color: "#21252d"
            border.color: "#2f3542"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10

                Text {
                    text: "Tap Timing & Finger Contact Precision"
                    font.bold: true
                    font.pixelSize: 14
                    color: "#ffffff"
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 24

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Tap Max Duration:"; color: "#ecf0f1"; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: tapDurationSlider.value + " ms"; color: "#3daee9"; font.bold: true; font.pixelSize: 12 }
                        }
                        Slider {
                            id: tapDurationSlider
                            Layout.fillWidth: true
                            from: 50
                            to: 500
                            stepSize: 25
                            value: edgepadController.edgeSettings.tap_max_duration_ms || 200
                            onMoved: saveSettings()
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Tap Movement Limit:"; color: "#ecf0f1"; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: tapMovementSlider.value + " units"; color: "#3daee9"; font.bold: true; font.pixelSize: 12 }
                        }
                        Slider {
                            id: tapMovementSlider
                            Layout.fillWidth: true
                            from: 10
                            to: 200
                            stepSize: 10
                            value: edgepadController.edgeSettings.tap_max_movement || 50
                            onMoved: saveSettings()
                        }
                    }
                }
            }
        }
    }

    function saveSettings() {
        edgepadController.updateEdgeSettings(
            edgeWidthSlider.value / 100.0,
            minTravelSlider.value,
            maxDriftSlider.value,
            cooldownSlider.value,
            tapDurationSlider.value,
            tapMovementSlider.value
        )
    }
}
