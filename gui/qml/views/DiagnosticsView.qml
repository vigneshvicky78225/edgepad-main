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
                    text: "System Diagnostics & Troubleshooting"
                    font.bold: true
                    font.pixelSize: 22
                    color: "#ffffff"
                }
                Text {
                    text: "Inspect runtime health checks, service errors, and journal logs without the terminal"
                    font.pixelSize: 13
                    color: "#95a5a6"
                }
            }

            Button {
                text: "Refresh Checks"
                onClicked: edgepadController.refreshAll()
            }

            Button {
                text: "Export Diagnostic Report"
                highlighted: true
                onClicked: {
                    var path = "/tmp/edgepad_diagnostics_report.md"
                    edgepadController.exportDiagnostics(path)
                }
            }
        }

        // Doctor Health Checks Summary Cards
        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 70
                radius: 8
                color: "#1e2b37"
                border.color: "#27ae60"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 10
                    Text { text: "✓"; color: "#27ae60"; font.bold: true; font.pixelSize: 22 }
                    ColumnLayout {
                        Text { text: (edgepadController.doctorReport.summary ? edgepadController.doctorReport.summary.ok : "5") + " Passed"; color: "#ffffff"; font.bold: true; font.pixelSize: 14 }
                        Text { text: "Healthy prerequisites"; color: "#95a5a6"; font.pixelSize: 11 }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 70
                radius: 8
                color: "#2b251e"
                border.color: "#f39c12"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 10
                    Text { text: "⚠"; color: "#f39c12"; font.bold: true; font.pixelSize: 22 }
                    ColumnLayout {
                        Text { text: (edgepadController.doctorReport.summary ? edgepadController.doctorReport.summary.warn : "0") + " Warnings"; color: "#ffffff"; font.bold: true; font.pixelSize: 14 }
                        Text { text: "Non-fatal notes"; color: "#95a5a6"; font.pixelSize: 11 }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 70
                radius: 8
                color: "#2b1e1e"
                border.color: "#e74c3c"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 10
                    Text { text: "✗"; color: "#e74c3c"; font.bold: true; font.pixelSize: 22 }
                    ColumnLayout {
                        Text { text: (edgepadController.doctorReport.summary ? edgepadController.doctorReport.summary.fail : "0") + " Failures"; color: "#ffffff"; font.bold: true; font.pixelSize: 14 }
                        Text { text: "Action required"; color: "#95a5a6"; font.pixelSize: 11 }
                    }
                }
            }
        }

        // Doctor Checks Detail Table
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 260
            radius: 10
            color: "#21252d"
            border.color: "#2f3542"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                Text {
                    text: "Health Checks (edgepad doctor)"
                    font.bold: true
                    font.pixelSize: 14
                    color: "#ffffff"
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    ListView {
                        id: doctorList
                        model: edgepadController.doctorReport.items || []
                        spacing: 6

                        delegate: Rectangle {
                            width: doctorList.width
                            height: 38
                            radius: 6
                            color: "#1a1d24"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 10

                                Rectangle {
                                    implicitWidth: 60
                                    implicitHeight: 20
                                    radius: 3
                                    color: {
                                        if (modelData.level === "ok") return "#27ae60"
                                        if (modelData.level === "warn") return "#d35400"
                                        return "#c0392b"
                                    }
                                    Text {
                                        anchors.centerIn: parent
                                        text: (modelData.level || "ok").toUpperCase()
                                        color: "#ffffff"
                                        font.bold: true
                                        font.pixelSize: 10
                                    }
                                }

                                Text {
                                    text: modelData.section + " : " + modelData.name
                                    color: "#ffffff"
                                    font.bold: true
                                    font.pixelSize: 12
                                    Layout.preferredWidth: 160
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: modelData.details
                                    color: "#bdc3c7"
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }

        // Live Service Logs Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 220
            radius: 10
            color: "#1a1d24"
            border.color: "#2f3542"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Recent Service Output (journalctl -u edgepad.service)"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "Fetch Logs"
                        onClicked: edgepadController.refreshLogs()
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    TextArea {
                        readOnly: true
                        text: edgepadController.serviceLogs || "No recent journal logs found for edgepad.service."
                        font.family: "monospace"
                        font.pixelSize: 11
                        color: "#bdc3c7"
                        background: Rectangle { color: "#14171d"; radius: 6 }
                        selectByMouse: true
                    }
                }
            }
        }
    }
}
