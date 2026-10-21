import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    // Independent Hitbox Geometry Fractions (0.01 - 0.45)
    property real leftEdgeWidthFraction: 0.12
    property real rightEdgeWidthFraction: 0.12
    property real topEdgeHeightFraction: 0.12
    property real bottomEdgeHeightFraction: 0.12

    // Independent Corner Dimensions (0.05 - 0.35)
    property real cornerWidthFraction: 0.15
    property real cornerHeightFraction: 0.15

    // Backward compatibility property:
    property real edgeWidthFraction: 0.12
    onEdgeWidthFractionChanged: {
        if (Math.abs(leftEdgeWidthFraction - edgeWidthFraction) > 0.001) {
            leftEdgeWidthFraction = edgeWidthFraction;
            rightEdgeWidthFraction = edgeWidthFraction;
            topEdgeHeightFraction = edgeWidthFraction;
            bottomEdgeHeightFraction = edgeWidthFraction;
        }
    }

    // Drift corridor & gesture parameters for overlay
    property real maxDriftFraction: 0.04
    property int maxDriftUnits: 116
    property bool showDriftCorridor: false

    // Hardware axis coordinate boundaries
    property int xMin: 0
    property int xMax: 2905
    property int yMin: 0
    property int yMax: 1766

    // Active detection states for visualizer / tester
    property string activeZone: "" // "top-left", "top-right", "bottom-left", "bottom-right", "left", "right", "top", "bottom", or ""
    property string activeEdge: "" // alias for activeZone
    property string activeDirection: "" // "up", "down", "left", "right", "tap", "double-tap"
    property bool showCoordinateOverlay: true

    readonly property string effectiveZone: {
        var z = activeZone || activeEdge || "";
        return z.toLowerCase().replace("_", "-");
    }

    readonly property int rawWidth: Math.max(1, xMax - xMin)
    readonly property int rawHeight: Math.max(1, yMax - yMin)

    implicitWidth: 460
    implicitHeight: 300

    Rectangle {
        id: padBody
        anchors.fill: parent
        anchors.margins: 6
        radius: 14
        color: "#181b22" // Sleek dark touchpad surface
        border.color: root.effectiveZone !== "" ? "#3daee9" : "#2f3642"
        border.width: 2
        clip: true

        Behavior on border.color {
            ColorAnimation { duration: 150 }
        }

        // Touchpad Surface Grid
        Canvas {
            anchors.fill: parent
            opacity: 0.12
            onPaint: {
                var ctx = getContext("2d");
                ctx.strokeStyle = "#ffffff";
                ctx.lineWidth = 1;
                var step = 24;
                for (var x = step; x < width; x += step) {
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, height);
                    ctx.stroke();
                }
                for (var y = step; y < height; y += step) {
                    ctx.beginPath();
                    ctx.moveTo(0, y);
                    ctx.lineTo(width, y);
                    ctx.stroke();
                }
            }
        }

        // --- Corner Hitboxes (Precedence over Edge Zones for Double-Tap) ---

        // 1. Top-Left Corner
        Rectangle {
            id: topLeftCorner
            x: 0
            y: 0
            width: padBody.width * root.cornerWidthFraction
            height: padBody.height * root.cornerHeightFraction
            color: root.effectiveZone === "top-left" ? "#9b59b6" : "#4a235a"
            opacity: root.effectiveZone === "top-left" ? 0.85 : 0.45
            border.color: "#af7ac5"
            border.width: root.effectiveZone === "top-left" ? 2 : 1
            z: 2

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Column {
                anchors.centerIn: parent
                spacing: 2
                Text {
                    text: "◰ TL"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: Math.round(root.cornerWidthFraction * 100) + "×" + Math.round(root.cornerHeightFraction * 100) + "%"
                    color: "#e8daef"
                    font.pixelSize: 8
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }

        // 2. Top-Right Corner
        Rectangle {
            id: topRightCorner
            x: padBody.width * (1.0 - root.cornerWidthFraction)
            y: 0
            width: padBody.width * root.cornerWidthFraction
            height: padBody.height * root.cornerHeightFraction
            color: root.effectiveZone === "top-right" ? "#9b59b6" : "#4a235a"
            opacity: root.effectiveZone === "top-right" ? 0.85 : 0.45
            border.color: "#af7ac5"
            border.width: root.effectiveZone === "top-right" ? 2 : 1
            z: 2

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Column {
                anchors.centerIn: parent
                spacing: 2
                Text {
                    text: "◳ TR"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: Math.round(root.cornerWidthFraction * 100) + "×" + Math.round(root.cornerHeightFraction * 100) + "%"
                    color: "#e8daef"
                    font.pixelSize: 8
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }

        // 3. Bottom-Left Corner
        Rectangle {
            id: bottomLeftCorner
            x: 0
            y: padBody.height * (1.0 - root.cornerHeightFraction)
            width: padBody.width * root.cornerWidthFraction
            height: padBody.height * root.cornerHeightFraction
            color: root.effectiveZone === "bottom-left" ? "#9b59b6" : "#4a235a"
            opacity: root.effectiveZone === "bottom-left" ? 0.85 : 0.45
            border.color: "#af7ac5"
            border.width: root.effectiveZone === "bottom-left" ? 2 : 1
            z: 2

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Column {
                anchors.centerIn: parent
                spacing: 2
                Text {
                    text: "◱ BL"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: Math.round(root.cornerWidthFraction * 100) + "×" + Math.round(root.cornerHeightFraction * 100) + "%"
                    color: "#e8daef"
                    font.pixelSize: 8
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }

        // 4. Bottom-Right Corner
        Rectangle {
            id: bottomRightCorner
            x: padBody.width * (1.0 - root.cornerWidthFraction)
            y: padBody.height * (1.0 - root.cornerHeightFraction)
            width: padBody.width * root.cornerWidthFraction
            height: padBody.height * root.cornerHeightFraction
            color: root.effectiveZone === "bottom-right" ? "#9b59b6" : "#4a235a"
            opacity: root.effectiveZone === "bottom-right" ? 0.85 : 0.45
            border.color: "#af7ac5"
            border.width: root.effectiveZone === "bottom-right" ? 2 : 1
            z: 2

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Column {
                anchors.centerIn: parent
                spacing: 2
                Text {
                    text: "◲ BR"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: Math.round(root.cornerWidthFraction * 100) + "×" + Math.round(root.cornerHeightFraction * 100) + "%"
                    color: "#e8daef"
                    font.pixelSize: 8
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }

        // --- Edge Hitboxes (Outside Corner Double-Tap Regions) ---

        // Left Edge Zone
        Rectangle {
            id: leftZone
            x: 0
            y: padBody.height * root.cornerHeightFraction
            width: padBody.width * root.leftEdgeWidthFraction
            height: padBody.height * (1.0 - 2 * root.cornerHeightFraction)
            color: root.effectiveZone === "left" ? "#3daee9" : "#2471a3"
            opacity: root.effectiveZone === "left" ? 0.80 : 0.38
            border.color: "#3daee9"
            border.width: root.effectiveZone === "left" ? 2 : 1
            z: 1

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Column {
                anchors.centerIn: parent
                spacing: 3
                Text {
                    text: "LEFT"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: root.effectiveZone === "left" && root.activeDirection ? root.activeDirection.toUpperCase() : Math.round(root.leftEdgeWidthFraction * 100) + "%"
                    color: root.effectiveZone === "left" ? "#ffffff" : "#d4e6f1"
                    font.bold: root.effectiveZone === "left"
                    font.pixelSize: 9
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }

        // Right Edge Zone
        Rectangle {
            id: rightZone
            x: padBody.width * (1.0 - root.rightEdgeWidthFraction)
            y: padBody.height * root.cornerHeightFraction
            width: padBody.width * root.rightEdgeWidthFraction
            height: padBody.height * (1.0 - 2 * root.cornerHeightFraction)
            color: root.effectiveZone === "right" ? "#3daee9" : "#2471a3"
            opacity: root.effectiveZone === "right" ? 0.80 : 0.38
            border.color: "#3daee9"
            border.width: root.effectiveZone === "right" ? 2 : 1
            z: 1

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Column {
                anchors.centerIn: parent
                spacing: 3
                Text {
                    text: "RIGHT"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: root.effectiveZone === "right" && root.activeDirection ? root.activeDirection.toUpperCase() : Math.round(root.rightEdgeWidthFraction * 100) + "%"
                    color: root.effectiveZone === "right" ? "#ffffff" : "#d4e6f1"
                    font.bold: root.effectiveZone === "right"
                    font.pixelSize: 9
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }

        // Top Edge Zone
        Rectangle {
            id: topZone
            x: padBody.width * root.cornerWidthFraction
            y: 0
            width: padBody.width * (1.0 - 2 * root.cornerWidthFraction)
            height: padBody.height * root.topEdgeHeightFraction
            color: root.effectiveZone === "top" ? "#3daee9" : "#2471a3"
            opacity: root.effectiveZone === "top" ? 0.80 : 0.38
            border.color: "#3daee9"
            border.width: root.effectiveZone === "top" ? 2 : 1
            z: 1

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Row {
                anchors.centerIn: parent
                spacing: 6
                Text {
                    text: "TOP EDGE"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                }
                Text {
                    text: root.effectiveZone === "top" && root.activeDirection ? "• " + root.activeDirection.toUpperCase() : "(" + Math.round(root.topEdgeHeightFraction * 100) + "%)"
                    color: root.effectiveZone === "top" ? "#ffffff" : "#d4e6f1"
                    font.bold: root.effectiveZone === "top"
                    font.pixelSize: 9
                }
            }
        }

        // Bottom Edge Zone
        Rectangle {
            id: bottomZone
            x: padBody.width * root.cornerWidthFraction
            y: padBody.height * (1.0 - root.bottomEdgeHeightFraction)
            width: padBody.width * (1.0 - 2 * root.cornerWidthFraction)
            height: padBody.height * root.bottomEdgeHeightFraction
            color: root.effectiveZone === "bottom" ? "#3daee9" : "#2471a3"
            opacity: root.effectiveZone === "bottom" ? 0.80 : 0.38
            border.color: "#3daee9"
            border.width: root.effectiveZone === "bottom" ? 2 : 1
            z: 1

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Row {
                anchors.centerIn: parent
                spacing: 6
                Text {
                    text: "BOTTOM EDGE"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                }
                Text {
                    text: root.effectiveZone === "bottom" && root.activeDirection ? "• " + root.activeDirection.toUpperCase() : "(" + Math.round(root.bottomEdgeHeightFraction * 100) + "%)"
                    color: root.effectiveZone === "bottom" ? "#ffffff" : "#d4e6f1"
                    font.bold: root.effectiveZone === "bottom"
                    font.pixelSize: 9
                }
            }
        }

        // --- Center Area (Normal Pointer & Scrolling) ---
        Rectangle {
            id: centerArea
            anchors.left: leftZone.right
            anchors.right: rightZone.left
            anchors.top: topZone.bottom
            anchors.bottom: bottomZone.top
            color: "transparent"
            z: 0

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 4

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 32
                    height: 32
                    radius: 16
                    color: "#242b35"
                    border.color: "#4a5568"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "✋"
                        font.pixelSize: 16
                    }
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Normal Touchpad Area"
                    color: "#ecf0f1"
                    font.bold: true
                    font.pixelSize: 11
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Pointer Motion • Taps • 2-Finger Scrolling"
                    color: "#95a5a6"
                    font.pixelSize: 9
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    visible: root.showCoordinateOverlay
                    text: "X: [" + root.xMin + ".." + root.xMax + "]  Y: [" + root.yMin + ".." + root.yMax + "]"
                    color: "#7f8c8d"
                    font.pixelSize: 8
                    font.family: "monospace"
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    visible: root.showDriftCorridor
                    spacing: 4
                    Rectangle {
                        width: 7
                        height: 7
                        radius: 2
                        color: "#f39c12"
                    }
                    Text {
                        text: "Drift Corridor: ±" + root.maxDriftUnits + " units (" + (Math.round(root.maxDriftFraction * 1000) / 10) + "%)"
                        color: "#f39c12"
                        font.bold: true
                        font.pixelSize: 9
                    }
                }
            }
        }

        // Left Edge Drift Tolerance Corridor (if enabled)
        Rectangle {
            id: leftDriftCorridor
            visible: root.showDriftCorridor && root.maxDriftFraction > 0
            x: padBody.width * root.leftEdgeWidthFraction
            y: padBody.height * root.cornerHeightFraction
            width: Math.max(3, padBody.width * root.maxDriftFraction)
            height: padBody.height * (1.0 - 2 * root.cornerHeightFraction)
            color: "#f39c12"
            opacity: 0.28
            border.color: "#e67e22"
            border.width: 1
            z: 0

            Behavior on width { NumberAnimation { duration: 120 } }
        }

        // Right Edge Drift Tolerance Corridor (if enabled)
        Rectangle {
            id: rightDriftCorridor
            visible: root.showDriftCorridor && root.maxDriftFraction > 0
            x: padBody.width * (1.0 - root.rightEdgeWidthFraction) - Math.max(3, padBody.width * root.maxDriftFraction)
            y: padBody.height * root.cornerHeightFraction
            width: Math.max(3, padBody.width * root.maxDriftFraction)
            height: padBody.height * (1.0 - 2 * root.cornerHeightFraction)
            color: "#f39c12"
            opacity: 0.28
            border.color: "#e67e22"
            border.width: 1
            z: 0

            Behavior on width { NumberAnimation { duration: 120 } }
        }

        // Bottom Touchpad physical click button divider line
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: 1
            height: 20
            color: "#34495e"
            z: 3
        }
    }
}
