import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string status: "stopped" // "running", "stopped", "starting", "error", "not_installed"
    property int customFontSize: 11

    readonly property color statusColor: {
        switch (root.status) {
            case "running": return "#27ae60"; // Breeze Emerald Green
            case "starting": return "#f39c12"; // Breeze Amber
            case "error": return "#e74c3c"; // Breeze Crimson
            case "not_installed": return "#95a5a6"; // Gray
            case "stopped":
            default: return "#7f8c8d"; // Slate Gray
        }
    }

    readonly property string statusText: {
        switch (root.status) {
            case "running": return "Active & Running";
            case "starting": return "Starting...";
            case "error": return "Error / Failed";
            case "not_installed": return "Service Not Installed";
            case "stopped":
            default: return "Service Stopped";
        }
    }

    implicitWidth: contentRow.implicitWidth + 16
    implicitHeight: 24
    radius: 12
    color: Qt.rgba(statusColor.r, statusColor.g, statusColor.b, 0.15)
    border.color: Qt.rgba(statusColor.r, statusColor.g, statusColor.b, 0.4)
    border.width: 1

    RowLayout {
        id: contentRow
        anchors.centerIn: parent
        spacing: 6

        Rectangle {
            width: 8
            height: 8
            radius: 4
            color: root.statusColor

            SequentialAnimation on opacity {
                running: root.status === "running" || root.status === "starting"
                loops: Animation.Infinite
                NumberAnimation { from: 1.0; to: 0.4; duration: 800; easing.type: Easing.InOutQuad }
                NumberAnimation { from: 0.4; to: 1.0; duration: 800; easing.type: Easing.InOutQuad }
            }
        }

        Text {
            text: root.statusText
            color: root.statusColor
            font.bold: true
            font.pixelSize: root.customFontSize
        }
    }
}
