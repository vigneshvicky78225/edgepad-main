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
        anchors.margins: 24
        spacing: 20

        // Page Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: "Hitbox Calibration"
                font.bold: true
                font.pixelSize: 22
                color: "#ffffff"
                Layout.fillWidth: true
            }

            Button {
                text: "Restore Defaults"
                flat: true
                onClicked: {
                    edgepadController.restoreHitboxDefaults()
                    syncFromController()
                }
            }

            Button {
                text: "Apply Hitbox Calibration"
                highlighted: true
                onClicked: {
                    syncToController()
                    edgepadController.applyHitboxCalibration()
                }
            }
        }

        // Responsive Main Layout: Visualizer on Left (or Top) and Hitbox Calibration Sliders on Right (or Bottom)
        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 880 ? 2 : 1
            rowSpacing: 16
            columnSpacing: 16
            Layout.alignment: Qt.AlignTop

            // Left Column: Interactive Visualizer & Clean Coordinates Card
            ColumnLayout {
                Layout.fillWidth: root.width <= 880
                Layout.preferredWidth: root.width > 880 ? 440 : -1
                Layout.maximumWidth: root.width <= 880 ? 540 : -1
                Layout.alignment: Qt.AlignTop | (root.width <= 880 ? Qt.AlignHCenter : Qt.AlignLeft)
                spacing: 16

                // Interactive Touchpad Visualizer Card
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: padCardCol.implicitHeight + 32
                    radius: 14
                    color: "#1b1f28"
                    border.color: "#28303f"
                    border.width: 1

                    ColumnLayout {
                        id: padCardCol
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Interactive Hitbox Canvas"
                                font.bold: true
                                font.pixelSize: 14
                                color: "#ffffff"
                                Layout.fillWidth: true
                            }
                            Rectangle {
                                implicitWidth: resText.implicitWidth + 10
                                implicitHeight: 20
                                radius: 10
                                color: "#131720"
                                border.color: "#2a3242"
                                border.width: 1
                                Text {
                                    id: resText
                                    anchors.centerIn: parent
                                    text: Math.max(1, ((edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.x_max) || 2905) - ((edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.x_min) || 0)) + " × " + Math.max(1, ((edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.y_max) || 1766) - ((edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.y_min) || 0)) + " units"
                                    color: "#94a3b8"
                                    font.pixelSize: 10
                                    font.family: "monospace"
                                }
                            }
                        }

                        // Canvas Container
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 280
                            radius: 10
                            color: "#13161d"
                            border.color: "#222733"
                            border.width: 1
                            clip: true

                            TouchpadCanvas {
                                id: touchpadDiagram
                                anchors.fill: parent
                                anchors.margins: 12
                                leftEdgeWidthFraction: leftSlider.value / 100.0
                                rightEdgeWidthFraction: rightSlider.value / 100.0
                                topEdgeHeightFraction: topSlider.value / 100.0
                                bottomEdgeHeightFraction: bottomSlider.value / 100.0
                                cornerWidthFraction: cornerWidthSlider.value / 100.0
                                cornerHeightFraction: cornerHeightSlider.value / 100.0
                                xMin: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.x_min) || 0
                                xMax: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.x_max) || 2905
                                yMin: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.y_min) || 0
                                yMax: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.y_max) || 1766
                            }
                        }

                        // Canvas Legend Pills
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Layout.alignment: Qt.AlignHCenter

                            RowLayout {
                                spacing: 6
                                Rectangle { width: 10; height: 10; radius: 5; color: "#3daee9" }
                                Text { text: "Edge Zones"; color: "#cbd5e1"; font.pixelSize: 11 }
                            }

                            RowLayout {
                                spacing: 6
                                Rectangle { width: 10; height: 10; radius: 5; color: "#af7ac5" }
                                Text { text: "Corner Hitboxes"; color: "#cbd5e1"; font.pixelSize: 11 }
                            }

                            RowLayout {
                                spacing: 6
                                Rectangle { width: 10; height: 10; radius: 5; color: "#475569" }
                                Text { text: "Center Pointer"; color: "#cbd5e1"; font.pixelSize: 11 }
                            }
                        }
                    }
                }

                // Calculated Hardware Boundaries Card
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: coordCardCol.implicitHeight + 28
                    radius: 14
                    color: "#1b1f28"
                    border.color: "#28303f"
                    border.width: 1

                    ColumnLayout {
                        id: coordCardCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        readonly property int xMinVal: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.x_min) || 0
                        readonly property int xMaxVal: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.x_max) || 2905
                        readonly property int yMinVal: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.y_min) || 0
                        readonly property int yMaxVal: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.y_max) || 1766
                        readonly property int rawW: Math.max(1, xMaxVal - xMinVal)
                        readonly property int rawH: Math.max(1, yMaxVal - yMinVal)

                        property bool showDetails: false

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Hardware Range Inspector"
                                font.bold: true
                                font.pixelSize: 13
                                color: "#ffffff"
                                Layout.fillWidth: true
                            }
                            Button {
                                text: coordCardCol.showDetails ? "Hide Normalization" : "Detailed Normalization"
                                flat: true
                                onClicked: coordCardCol.showDetails = !coordCardCol.showDetails
                            }
                        }

                        // Compact 2x2 Grid of Boundaries
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: 8
                            columnSpacing: 10

                            // Left Edge Box
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 46
                                radius: 8
                                color: "#131720"
                                border.color: "#252e3d"
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 2
                                    RowLayout {
                                        Text { text: "Left Edge"; color: "#3daee9"; font.bold: true; font.pixelSize: 11; Layout.fillWidth: true }
                                        Text { text: leftSlider.value + "%"; color: "#94a3b8"; font.pixelSize: 11 }
                                    }
                                    Text {
                                        text: "X: " + coordCardCol.xMinVal + " → " + Math.round(coordCardCol.xMinVal + coordCardCol.rawW * (leftSlider.value / 100.0)) + " px"
                                        color: "#f1f5f9"
                                        font.pixelSize: 11
                                        font.family: "monospace"
                                    }
                                }
                            }

                            // Right Edge Box
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 46
                                radius: 8
                                color: "#131720"
                                border.color: "#252e3d"
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 2
                                    RowLayout {
                                        Text { text: "Right Edge"; color: "#3daee9"; font.bold: true; font.pixelSize: 11; Layout.fillWidth: true }
                                        Text { text: rightSlider.value + "%"; color: "#94a3b8"; font.pixelSize: 11 }
                                    }
                                    Text {
                                        text: "X: " + Math.round(coordCardCol.xMaxVal - coordCardCol.rawW * (rightSlider.value / 100.0)) + " → " + coordCardCol.xMaxVal + " px"
                                        color: "#f1f5f9"
                                        font.pixelSize: 11
                                        font.family: "monospace"
                                    }
                                }
                            }

                            // Top Edge Box
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 46
                                radius: 8
                                color: "#131720"
                                border.color: "#252e3d"
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 2
                                    RowLayout {
                                        Text { text: "Top Edge"; color: "#3daee9"; font.bold: true; font.pixelSize: 11; Layout.fillWidth: true }
                                        Text { text: topSlider.value + "%"; color: "#94a3b8"; font.pixelSize: 11 }
                                    }
                                    Text {
                                        text: "Y: " + coordCardCol.yMinVal + " → " + Math.round(coordCardCol.yMinVal + coordCardCol.rawH * (topSlider.value / 100.0)) + " px"
                                        color: "#f1f5f9"
                                        font.pixelSize: 11
                                        font.family: "monospace"
                                    }
                                }
                            }

                            // Bottom Edge Box
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 46
                                radius: 8
                                color: "#131720"
                                border.color: "#252e3d"
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 2
                                    RowLayout {
                                        Text { text: "Bottom Edge"; color: "#3daee9"; font.bold: true; font.pixelSize: 11; Layout.fillWidth: true }
                                        Text { text: bottomSlider.value + "%"; color: "#94a3b8"; font.pixelSize: 11 }
                                    }
                                    Text {
                                        text: "Y: " + Math.round(coordCardCol.yMaxVal - coordCardCol.rawH * (bottomSlider.value / 100.0)) + " → " + coordCardCol.yMaxVal + " px"
                                        color: "#f1f5f9"
                                        font.pixelSize: 11
                                        font.family: "monospace"
                                    }
                                }
                            }
                        }

                        // Corners Summary Box
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 46
                            radius: 8
                            color: "#181424"
                            border.color: "#3a264a"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10
                                Text { text: "Corner Hitboxes (4):"; color: "#af7ac5"; font.bold: true; font.pixelSize: 11 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: Math.round(coordCardCol.rawW * (cornerWidthSlider.value / 100.0)) + " × " + Math.round(coordCardCol.rawH * (cornerHeightSlider.value / 100.0)) + " px (" + cornerWidthSlider.value + "% × " + cornerHeightSlider.value + "%)"
                                    color: "#f1f5f9"
                                    font.pixelSize: 11
                                    font.family: "monospace"
                                }
                            }
                        }

                        // Optional Detailed Normalization breakdown
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: coordCardCol.showDetails
                            spacing: 4

                            Rectangle { Layout.fillWidth: true; height: 1; color: "#252e3d" }
                            Text {
                                text: "Normalized Values (0.0000 .. 1.0000):"
                                color: "#94a3b8"
                                font.pixelSize: 10
                                font.bold: true
                            }
                            Text {
                                text: "Left: 0.0000 .. " + (leftSlider.value / 100.0).toFixed(4) + " | Right: " + (1.0 - rightSlider.value / 100.0).toFixed(4) + " .. 1.0000"
                                color: "#cbd5e1"
                                font.pixelSize: 10
                                font.family: "monospace"
                            }
                            Text {
                                text: "Top: 0.0000 .. " + (topSlider.value / 100.0).toFixed(4) + " | Bottom: " + (1.0 - bottomSlider.value / 100.0).toFixed(4) + " .. 1.0000"
                                color: "#cbd5e1"
                                font.pixelSize: 10
                                font.family: "monospace"
                            }
                        }
                    }
                }
            }

            // Right Column: Independent Sliders & Grouped Controls
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 16

                // Card A: 4 Edge Detection Hitboxes
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: edgesCol.implicitHeight + 36
                    radius: 14
                    color: "#1b1f28"
                    border.color: "#28303f"
                    border.width: 1

                    ColumnLayout {
                        id: edgesCol
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 14

                        // Header with Presets
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: "Edge Hitbox Zones"
                                    font.bold: true
                                    font.pixelSize: 15
                                    color: "#ffffff"
                                }
                                Text {
                                    text: "Swipe and continuous rotary gesture zones around touchpad perimeter"
                                    color: "#94a3b8"
                                    font.pixelSize: 11
                                }
                            }

                            // Quick Presets Row
                            RowLayout {
                                spacing: 6
                                Button {
                                    text: "Compact (8%)"
                                    flat: true
                                    onClicked: {
                                        leftSlider.value = 8
                                        rightSlider.value = 8
                                        topSlider.value = 8
                                        bottomSlider.value = 8
                                        syncToController()
                                    }
                                }
                                Button {
                                    text: "Standard (12%)"
                                    flat: true
                                    onClicked: {
                                        leftSlider.value = 12
                                        rightSlider.value = 12
                                        topSlider.value = 12
                                        bottomSlider.value = 12
                                        syncToController()
                                    }
                                }
                                Button {
                                    text: "Wide (16%)"
                                    flat: true
                                    onClicked: {
                                        leftSlider.value = 16
                                        rightSlider.value = 16
                                        topSlider.value = 16
                                        bottomSlider.value = 16
                                        syncToController()
                                    }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#252e3d" }

                        // 1. Left Edge Slider Row
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                RowLayout {
                                    spacing: 6
                                    Rectangle { width: 8; height: 8; radius: 4; color: "#3daee9" }
                                    Text { text: "Left Edge Width"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: leftValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#182736"
                                    border.color: "#3daee9"
                                    border.width: 1
                                    Text {
                                        id: leftValText
                                        anchors.centerIn: parent
                                        text: leftSlider.value + "% (" + (leftSlider.value / 100.0).toFixed(2) + ")"
                                        color: "#38bdf8"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: leftSlider
                                Layout.fillWidth: true
                                from: 1
                                to: 45
                                stepSize: 1
                                value: 12
                                onMoved: {
                                    touchpadDiagram.activeZone = "left"
                                    syncToController()
                                }
                            }
                        }

                        // 2. Right Edge Slider Row
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                RowLayout {
                                    spacing: 6
                                    Rectangle { width: 8; height: 8; radius: 4; color: "#3daee9" }
                                    Text { text: "Right Edge Width"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: rightValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#182736"
                                    border.color: "#3daee9"
                                    border.width: 1
                                    Text {
                                        id: rightValText
                                        anchors.centerIn: parent
                                        text: rightSlider.value + "% (" + (rightSlider.value / 100.0).toFixed(2) + ")"
                                        color: "#38bdf8"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: rightSlider
                                Layout.fillWidth: true
                                from: 1
                                to: 45
                                stepSize: 1
                                value: 12
                                onMoved: {
                                    touchpadDiagram.activeZone = "right"
                                    syncToController()
                                }
                            }
                        }

                        // 3. Top Edge Slider Row
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                RowLayout {
                                    spacing: 6
                                    Rectangle { width: 8; height: 8; radius: 4; color: "#3daee9" }
                                    Text { text: "Top Edge Height"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: topValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#182736"
                                    border.color: "#3daee9"
                                    border.width: 1
                                    Text {
                                        id: topValText
                                        anchors.centerIn: parent
                                        text: topSlider.value + "% (" + (topSlider.value / 100.0).toFixed(2) + ")"
                                        color: "#38bdf8"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: topSlider
                                Layout.fillWidth: true
                                from: 1
                                to: 45
                                stepSize: 1
                                value: 12
                                onMoved: {
                                    touchpadDiagram.activeZone = "top"
                                    syncToController()
                                }
                            }
                        }

                        // 4. Bottom Edge Slider Row
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                RowLayout {
                                    spacing: 6
                                    Rectangle { width: 8; height: 8; radius: 4; color: "#3daee9" }
                                    Text { text: "Bottom Edge Height"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: bottomValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#182736"
                                    border.color: "#3daee9"
                                    border.width: 1
                                    Text {
                                        id: bottomValText
                                        anchors.centerIn: parent
                                        text: bottomSlider.value + "% (" + (bottomSlider.value / 100.0).toFixed(2) + ")"
                                        color: "#38bdf8"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: bottomSlider
                                Layout.fillWidth: true
                                from: 1
                                to: 45
                                stepSize: 1
                                value: 12
                                onMoved: {
                                    touchpadDiagram.activeZone = "bottom"
                                    syncToController()
                                }
                            }
                        }
                    }
                }

                // Card B: Corner Double-Tap Hitboxes
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: cornersCol.implicitHeight + 36
                    radius: 14
                    color: "#1b1f28"
                    border.color: "#28303f"
                    border.width: 1

                    ColumnLayout {
                        id: cornersCol
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: "Corner Hitboxes"
                                    font.bold: true
                                    font.pixelSize: 15
                                    color: "#af7ac5"
                                }
                                Text {
                                    text: "Priority double-tap shortcut hitboxes at the 4 physical touchpad corners"
                                    color: "#94a3b8"
                                    font.pixelSize: 11
                                }
                            }

                            RowLayout {
                                spacing: 6
                                Button {
                                    text: "Small (10%)"
                                    flat: true
                                    onClicked: {
                                        cornerWidthSlider.value = 10
                                        cornerHeightSlider.value = 10
                                        syncToController()
                                    }
                                }
                                Button {
                                    text: "Standard (15%)"
                                    flat: true
                                    onClicked: {
                                        cornerWidthSlider.value = 15
                                        cornerHeightSlider.value = 15
                                        syncToController()
                                    }
                                }
                                Button {
                                    text: "Large (20%)"
                                    flat: true
                                    onClicked: {
                                        cornerWidthSlider.value = 20
                                        cornerHeightSlider.value = 20
                                        syncToController()
                                    }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#252e3d" }

                        // Corner Width Slider
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                RowLayout {
                                    spacing: 6
                                    Rectangle { width: 8; height: 8; radius: 4; color: "#af7ac5" }
                                    Text { text: "Corner Width (Horizontal)"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: cwValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#271b36"
                                    border.color: "#af7ac5"
                                    border.width: 1
                                    Text {
                                        id: cwValText
                                        anchors.centerIn: parent
                                        text: cornerWidthSlider.value + "% (" + (cornerWidthSlider.value / 100.0).toFixed(2) + ")"
                                        color: "#d8b4fe"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: cornerWidthSlider
                                Layout.fillWidth: true
                                from: 5
                                to: 35
                                stepSize: 1
                                value: 15
                                onMoved: {
                                    touchpadDiagram.activeZone = "top-left"
                                    syncToController()
                                }
                            }
                        }

                        // Corner Height Slider
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                RowLayout {
                                    spacing: 6
                                    Rectangle { width: 8; height: 8; radius: 4; color: "#af7ac5" }
                                    Text { text: "Corner Height (Vertical)"; color: "#f1f5f9"; font.pixelSize: 13; font.bold: true }
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: chValText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#271b36"
                                    border.color: "#af7ac5"
                                    border.width: 1
                                    Text {
                                        id: chValText
                                        anchors.centerIn: parent
                                        text: cornerHeightSlider.value + "% (" + (cornerHeightSlider.value / 100.0).toFixed(2) + ")"
                                        color: "#d8b4fe"
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Slider {
                                id: cornerHeightSlider
                                Layout.fillWidth: true
                                from: 5
                                to: 35
                                stepSize: 1
                                value: 15
                                onMoved: {
                                    touchpadDiagram.activeZone = "top-left"
                                    syncToController()
                                }
                            }
                        }
                    }
                }

                // Card C: Protection Guarantee Note
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: shieldRow.implicitHeight + 20
                    radius: 10
                    color: "#131a24"
                    border.color: "#223547"
                    border.width: 1

                    RowLayout {
                        id: shieldRow
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        Text {
                            text: "🛡️"
                            font.pixelSize: 18
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: "Strict Edge Confinement Protection"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#38bdf8"
                            }
                            Text {
                                text: "Touches that drift into the center touchpad area are instantly cancelled. Normal pointer navigation and scrolling remain 100% uninhibited."
                                font.pixelSize: 11
                                color: "#94a3b8"
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }
    }

    function syncFromController() {
        if (!edgepadController) return;
        var hb = edgepadController.hitboxSettings || {};
        leftSlider.value = Math.round((hb.left_edge_width !== undefined ? hb.left_edge_width : (hb.edge_width || 0.12)) * 100);
        rightSlider.value = Math.round((hb.right_edge_width !== undefined ? hb.right_edge_width : (hb.edge_width || 0.12)) * 100);
        topSlider.value = Math.round((hb.top_edge_height !== undefined ? hb.top_edge_height : (hb.edge_width || 0.12)) * 100);
        bottomSlider.value = Math.round((hb.bottom_edge_height !== undefined ? hb.bottom_edge_height : (hb.edge_width || 0.12)) * 100);
        cornerWidthSlider.value = Math.round((hb.corner_width !== undefined ? hb.corner_width : 0.15) * 100);
        cornerHeightSlider.value = Math.round((hb.corner_height !== undefined ? hb.corner_height : 0.15) * 100);
    }

    function syncToController() {
        if (!edgepadController) return;
        edgepadController.updateHitboxSettings(
            leftSlider.value / 100.0,
            rightSlider.value / 100.0,
            topSlider.value / 100.0,
            bottomSlider.value / 100.0,
            cornerWidthSlider.value / 100.0,
            cornerHeightSlider.value / 100.0
        );
    }

    Component.onCompleted: {
        syncFromController();
    }

    Connections {
        target: edgepadController
        function onHitboxSettingsChanged() {
            syncFromController();
        }
    }
}
