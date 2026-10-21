import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root

    readonly property int rawWidth: Math.max(1, ((edgepadController && edgepadController.selectedDeviceDetails) ? (edgepadController.selectedDeviceDetails.x_max || 2905) : 2905) - ((edgepadController && edgepadController.selectedDeviceDetails) ? (edgepadController.selectedDeviceDetails.x_min || 0) : 0))

    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

        // Page Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            Text {
                text: "Calibration"
                font.bold: true
                font.pixelSize: 20
                color: "#ffffff"
                Layout.fillWidth: true
            }

            RowLayout {
                spacing: 10

                Button {
                    text: "Restore Defaults"
                    icon.name: "edit-undo"
                    flat: true
                    onClicked: {
                        if (edgepadController) {
                            edgepadController.restoreGestureDefaults()
                        }
                        syncFromController()
                    }
                }

                Button {
                    text: "Apply Gesture Calibration"
                    highlighted: true
                    icon.name: "dialog-ok-apply"
                    onClicked: {
                        syncToController()
                        if (edgepadController) {
                            edgepadController.applyGestureCalibration()
                        }
                    }
                }
            }
        }

        // Quick Sensitivity Profile Selector Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: profileRow.implicitHeight + 20
            radius: 12
            color: "#1b1f28"
            border.color: "#28303f"
            border.width: 1

            RowLayout {
                id: profileRow
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Text {
                    text: "Sensitivity Profiles:"
                    font.bold: true
                    font.pixelSize: 13
                    color: "#cbd5e1"
                }

                Button {
                    text: "Agile"
                    flat: true
                    onClicked: {
                        swipeMinSlider.value = 6
                        swipeDriftSlider.value = 5
                        tapMovementSlider.value = 3
                        tapDurationSlider.value = 160
                        doubleTapTimeoutSlider.value = 250
                        encoderStepSlider.value = 35
                        syncToController()
                    }
                }

                Button {
                    text: "Balanced"
                    flat: true
                    onClicked: {
                        swipeMinSlider.value = 8
                        swipeDriftSlider.value = 4
                        tapMovementSlider.value = 4
                        tapDurationSlider.value = 200
                        doubleTapTimeoutSlider.value = 300
                        encoderStepSlider.value = 50
                        syncToController()
                    }
                }

                Button {
                    text: "Firm"
                    flat: true
                    onClicked: {
                        swipeMinSlider.value = 12
                        swipeDriftSlider.value = 3
                        tapMovementSlider.value = 5
                        tapDurationSlider.value = 240
                        doubleTapTimeoutSlider.value = 350
                        encoderStepSlider.value = 75
                        syncToController()
                    }
                }

                Item { Layout.fillWidth: true }
            }
        }

        // Responsive Main Layout: Swipe Dynamics on Left (or Top) and Continuous Edge Encoder on Right (or Bottom)
        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 880 ? 2 : 1
            rowSpacing: 16
            columnSpacing: 16
            Layout.alignment: Qt.AlignTop

            // Left Column: Swipe Dynamics & Tap Detection
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 16

                // Card 1: Swipe Gesture Dynamics
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: swipeCol.implicitHeight + 28
                    radius: 12
                    color: "#1b1f28"
                    border.color: "#28303f"
                    border.width: 1

                    ColumnLayout {
                        id: swipeCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14

                        Text {
                            text: "Swipe Motion Dynamics"
                            font.bold: true
                            font.pixelSize: 15
                            color: "#ffffff"
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#252e3d" }

                        // 1. Swipe Movement Threshold
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Swipe Travel Threshold"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: swipeMinValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#182736"
                                    border.color: "#3daee9"
                                    border.width: 1
                                    Text {
                                        id: swipeMinValText
                                        anchors.centerIn: parent
                                        text: (swipeMinSlider.value / 100.0).toFixed(2) + " (" + Math.round((swipeMinSlider.value / 100.0) * root.rawWidth) + " raw units)"
                                        color: "#38bdf8"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: swipeMinSlider
                                Layout.fillWidth: true
                                from: 2
                                to: 35
                                stepSize: 1
                                value: 8
                                onMoved: syncToController()
                            }
                        }

                        // 2. Directional Drift Tolerance
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Directional Drift Corridor"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: swipeDriftValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#2a2215"
                                    border.color: "#f59e0b"
                                    border.width: 1
                                    Text {
                                        id: swipeDriftValText
                                        anchors.centerIn: parent
                                        text: "±" + (swipeDriftSlider.value / 100.0).toFixed(2) + " (±" + Math.round((swipeDriftSlider.value / 100.0) * root.rawWidth) + " units)"
                                        color: "#fbbf24"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: swipeDriftSlider
                                Layout.fillWidth: true
                                from: 1
                                to: 20
                                stepSize: 1
                                value: 4
                                onMoved: syncToController()
                            }
                        }
                    }
                }

                // Card 2: Tap Detection & Timings
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: tapCol.implicitHeight + 28
                    radius: 12
                    color: "#1b1f28"
                    border.color: "#28303f"
                    border.width: 1

                    ColumnLayout {
                        id: tapCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14

                        Text {
                            text: "Tap Timings"
                            font.bold: true
                            font.pixelSize: 15
                            color: "#ffffff"
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#252e3d" }

                        // 3. Stationary Tap Movement Tolerance
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Stationary Tap Tolerance"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: tapMoveValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#16281e"
                                    border.color: "#22c55e"
                                    border.width: 1
                                    Text {
                                        id: tapMoveValText
                                        anchors.centerIn: parent
                                        text: (tapMovementSlider.value / 100.0).toFixed(2) + " (" + Math.round((tapMovementSlider.value / 100.0) * root.rawWidth) + " raw units)"
                                        color: "#4ade80"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: tapMovementSlider
                                Layout.fillWidth: true
                                from: 1
                                to: 15
                                stepSize: 1
                                value: 4
                                onMoved: syncToController()
                            }
                        }

                        // 4. Max Tap Duration
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Max Tap Duration"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: tapDurValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#16281e"
                                    border.color: "#22c55e"
                                    border.width: 1
                                    Text {
                                        id: tapDurValText
                                        anchors.centerIn: parent
                                        text: tapDurationSlider.value + " ms"
                                        color: "#4ade80"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: tapDurationSlider
                                Layout.fillWidth: true
                                from: 50
                                to: 600
                                stepSize: 25
                                value: 200
                                onMoved: syncToController()
                            }
                        }

                        // 5. Double-Tap Timeout
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Double-Tap Interval"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: dblTapValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#271b36"
                                    border.color: "#af7ac5"
                                    border.width: 1
                                    Text {
                                        id: dblTapValText
                                        anchors.centerIn: parent
                                        text: doubleTapTimeoutSlider.value + " ms"
                                        color: "#d8b4fe"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: doubleTapTimeoutSlider
                                Layout.fillWidth: true
                                from: 100
                                to: 800
                                stepSize: 25
                                value: 300
                                onMoved: syncToController()
                            }
                        }
                    }
                }
            }

            // Right Column: Virtual Rotary Encoder
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                spacing: 16

                // Card 3: Virtual Rotary Encoder
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: encoderCol.implicitHeight + 28
                    radius: 12
                    color: "#1b1f28"
                    border.color: (edgepadController && edgepadController.encoderEnabled) ? "#3daee9" : "#28303f"
                    border.width: 1

                    ColumnLayout {
                        id: encoderCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            RowLayout {
                                spacing: 8
                                Text {
                                    text: "Virtual Rotary Encoder"
                                    font.bold: true
                                    font.pixelSize: 15
                                    color: "#ffffff"
                                }
                                Rectangle {
                                    implicitWidth: encStatusText.implicitWidth + 10
                                    implicitHeight: 18
                                    radius: 9
                                    color: (edgepadController && edgepadController.encoderEnabled) ? "#163324" : "#272e3b"
                                    border.color: (edgepadController && edgepadController.encoderEnabled) ? "#22c55e" : "#475569"
                                    border.width: 1
                                    Text {
                                        id: encStatusText
                                        anchors.centerIn: parent
                                        text: (edgepadController && edgepadController.encoderEnabled) ? "Active" : "Disabled"
                                        color: (edgepadController && edgepadController.encoderEnabled) ? "#4ade80" : "#94a3b8"
                                        font.bold: true
                                        font.pixelSize: 9
                                    }
                                }
                            }

                            Item { Layout.fillWidth: true }

                            Switch {
                                id: encoderEnabledSwitch
                                checked: Boolean(edgepadController && edgepadController.encoderEnabled)
                                onToggled: {
                                    if (edgepadController) {
                                        edgepadController.setEncoderEnabled(checked)
                                    }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#252e3d" }

                        // 6. Encoder Step Size
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Step Size"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: encStepValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#182736"
                                    border.color: "#3daee9"
                                    border.width: 1
                                    Text {
                                        id: encStepValText
                                        anchors.centerIn: parent
                                        text: Math.round(encoderStepSlider.value) + " raw units / tick"
                                        color: "#38bdf8"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: encoderStepSlider
                                Layout.fillWidth: true
                                from: 10
                                to: 250
                                stepSize: 5
                                value: (edgepadController && edgepadController.encoderStepSize) || 50
                                onMoved: {
                                    if (edgepadController) {
                                        edgepadController.setEncoderStepSize(value)
                                    }
                                }
                            }
                        }

                        // 7. Encoder Anti-Jitter / Deadband
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Anti-Jitter Deadband"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: encDeadValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#2a2215"
                                    border.color: "#f59e0b"
                                    border.width: 1
                                    Text {
                                        id: encDeadValText
                                        anchors.centerIn: parent
                                        text: Math.round(encoderDeadZoneSlider.value) + " raw units"
                                        color: "#fbbf24"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: encoderDeadZoneSlider
                                Layout.fillWidth: true
                                from: 0
                                to: 60
                                stepSize: 2
                                value: (edgepadController && edgepadController.encoderDeadZone) || 10
                                onMoved: {
                                    if (edgepadController) {
                                        edgepadController.setEncoderDeadZone(value)
                                    }
                                }
                            }
                        }

                        // 8. Key-Event Rate Limiter
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Repeat Rate Limiter"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: encRepValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#16281e"
                                    border.color: "#22c55e"
                                    border.width: 1
                                    Text {
                                        id: encRepValText
                                        anchors.centerIn: parent
                                        text: Math.round(encoderRepeatSlider.value) + " ms"
                                        color: "#4ade80"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: encoderRepeatSlider
                                Layout.fillWidth: true
                                from: 10
                                to: 150
                                stepSize: 5
                                value: (edgepadController && edgepadController.encoderRepeatIntervalMs) || 20
                                onMoved: {
                                    if (edgepadController) {
                                        edgepadController.setEncoderRepeatIntervalMs(Math.round(value))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    function syncFromController() {
        if (!edgepadController) return;
        var g = edgepadController.gestureSettings || {};
        swipeMinSlider.value = Math.round((g.swipe_min_distance || 0.08) * 100);
        swipeDriftSlider.value = Math.round((g.swipe_max_drift || 0.04) * 100);
        tapMovementSlider.value = Math.round((g.tap_max_movement || 0.04) * 100);
        doubleTapTimeoutSlider.value = g.double_tap_timeout_ms || 300;
        tapDurationSlider.value = g.tap_max_duration_ms || 200;

        encoderEnabledSwitch.checked = Boolean(edgepadController.encoderEnabled);
        encoderStepSlider.value = edgepadController.encoderStepSize || 50;
        encoderDeadZoneSlider.value = edgepadController.encoderDeadZone || 10;
        encoderRepeatSlider.value = edgepadController.encoderRepeatIntervalMs || 20;
    }

    function syncToController() {
        if (!edgepadController) return;
        var g = edgepadController.gestureSettings || {};
        edgepadController.updateGestureSettings(
            swipeMinSlider.value / 100.0,
            swipeDriftSlider.value / 100.0,
            tapMovementSlider.value / 100.0,
            g.tap_min_duration_ms || 40,
            Math.round(tapDurationSlider.value),
            Math.round(doubleTapTimeoutSlider.value),
            g.double_tap_max_distance || 0.08,
            g.cooldown_ms || 250
        );
    }

    Component.onCompleted: {
        syncFromController();
    }

    Connections {
        target: edgepadController
        function onGestureSettingsChanged() {
            syncFromController();
        }
        function onEncoderSettingsChanged() {
            if (!edgepadController) return;
            encoderEnabledSwitch.checked = Boolean(edgepadController.encoderEnabled);
            encoderStepSlider.value = edgepadController.encoderStepSize || 50;
            encoderDeadZoneSlider.value = edgepadController.encoderDeadZone || 10;
            encoderRepeatSlider.value = edgepadController.encoderRepeatIntervalMs || 20;
        }
    }
}
