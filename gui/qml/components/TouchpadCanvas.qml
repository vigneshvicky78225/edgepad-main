import QtQuick
import QtQuick.Controls

Item {
    id: root

    property real edgeWidthFraction: 0.12 // e.g. 0.12 = 12%
    property int xMin: 0
    property int xMax: 2905
    property int yMin: 0
    property int yMax: 1766
    property string activeEdge: "" // "left", "right", "top", "bottom", or ""
    property string activeDirection: "" // "up", "down", "left", "right"

    implicitWidth: 420
    implicitHeight: 270

    Rectangle {
        id: padBody
        anchors.fill: parent
        anchors.margins: 8
        radius: 14
        color: "#1e222b" // Sleek dark surface
        border.color: "#3daee9" // KDE Breeze blue
        border.width: 2
        clip: true

        // Grid pattern background
        Canvas {
            anchors.fill: parent
            opacity: 0.15
            onPaint: {
                var ctx = getContext("2d");
                ctx.strokeStyle = "#ffffff";
                ctx.lineWidth = 1;
                var step = 20;
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

        // Left Edge Zone
        Rectangle {
            id: leftZone
            x: 0
            y: 0
            width: padBody.width * root.edgeWidthFraction
            height: padBody.height
            color: root.activeEdge === "left" ? "#3daee9" : "#2980b9"
            opacity: root.activeEdge === "left" ? 0.75 : 0.35
            border.color: "#3daee9"
            border.width: 1

            Behavior on opacity {
                NumberAnimation { duration: 200 }
            }

            Column {
                anchors.centerIn: parent
                spacing: 4
                Text {
                    text: "LEFT\nEDGE"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    text: Math.round(root.edgeWidthFraction * 100) + "%"
                    color: "#b0d5f5"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        // Right Edge Zone
        Rectangle {
            id: rightZone
            x: padBody.width * (1.0 - root.edgeWidthFraction)
            y: 0
            width: padBody.width * root.edgeWidthFraction
            height: padBody.height
            color: root.activeEdge === "right" ? "#3daee9" : "#2980b9"
            opacity: root.activeEdge === "right" ? 0.75 : 0.35
            border.color: "#3daee9"
            border.width: 1

            Behavior on opacity {
                NumberAnimation { duration: 200 }
            }

            Column {
                anchors.centerIn: parent
                spacing: 4
                Text {
                    text: "RIGHT\nEDGE"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    text: Math.round(root.edgeWidthFraction * 100) + "%"
                    color: "#b0d5f5"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        // Center Area (Normal Pointer & Scrolling)
        Rectangle {
            anchors.left: leftZone.right
            anchors.right: rightZone.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            color: "transparent"

            Column {
                anchors.centerIn: parent
                spacing: 6

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 32
                    height: 32
                    radius: 16
                    color: "#2c3e50"
                    border.color: "#7f8c8d"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "✋"
                        font.pixelSize: 16
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Normal Touchpad Area"
                    color: "#ecf0f1"
                    font.bold: true
                    font.pixelSize: 12
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Pointer Motion • Taps • 2-Finger Scroll"
                    color: "#95a5a6"
                    font.pixelSize: 10
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Hardware Coordinates: [0.." + root.xMax + "] × [0.." + root.yMax + "]"
                    color: "#7f8c8d"
                    font.pixelSize: 9
                }
            }
        }

        // Bottom Touchpad Click Button line
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: 1
            height: 24
            color: "#34495e"
        }
    }
}
