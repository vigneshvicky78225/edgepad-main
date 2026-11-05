import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root

    contentWidth: availableWidth
    clip: true

    FileDialog {
        id: exportReportDialog
        title: "Export Diagnostics Report"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Markdown files (*.md)", "All files (*)"]
        defaultSuffix: "md"
        onAccepted: {
            if (edgepadController) {
                var localPath = selectedFile.toString().replace(/^file:\/\//, "")
                edgepadController.exportDiagnostics(localPath)
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Page Header
        RowLayout {
            Layout.fillWidth: true

            Text {
                text: "Diagnostics"
                font.bold: true
                font.pixelSize: 20
                color: "#ffffff"
                Layout.fillWidth: true
            }

            Button {
                text: "Refresh"
                icon.name: "view-refresh"
                onClicked: if (edgepadController) edgepadController.refreshAll()
            }

            Button {
                text: "Export Report"
                icon.name: "document-save"
                highlighted: true
                onClicked: exportReportDialog.open()
            }
        }

        // Doctor Health Checks Summary Cards
        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 750 ? 4 : (root.width > 480 ? 2 : 1)
            rowSpacing: 10
            columnSpacing: 14

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 56
                radius: 8
                color: "#1e2b37"
                border.color: "#27ae60"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 10
                    Text { text: "✓"; color: "#27ae60"; font.bold: true; font.pixelSize: 20 }
                    Text {
                        text: ((edgepadController && edgepadController.doctorReport && edgepadController.doctorReport.summary) ? (edgepadController.doctorReport.summary.ok !== undefined ? edgepadController.doctorReport.summary.ok : edgepadController.doctorReport.summary.pass) : "0") + " Passed"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 14
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 56
                radius: 8
                color: "#1e2637"
                border.color: "#2980b9"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 10
                    Text { text: "ℹ"; color: "#2980b9"; font.bold: true; font.pixelSize: 20 }
                    Text {
                        text: ((edgepadController && edgepadController.doctorReport && edgepadController.doctorReport.summary) ? (edgepadController.doctorReport.summary.info || 0) : "0") + " Info"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 14
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 56
                radius: 8
                color: "#2b251e"
                border.color: "#f39c12"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 10
                    Text { text: "⚠"; color: "#f39c12"; font.bold: true; font.pixelSize: 20 }
                    Text {
                        text: ((edgepadController && edgepadController.doctorReport && edgepadController.doctorReport.summary) ? edgepadController.doctorReport.summary.warn : "0") + " Warnings"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 14
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 56
                radius: 8
                color: "#2b1e1e"
                border.color: "#e74c3c"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 10
                    Text { text: "✗"; color: "#e74c3c"; font.bold: true; font.pixelSize: 20 }
                    Text {
                        text: ((edgepadController && edgepadController.doctorReport && edgepadController.doctorReport.summary) ? edgepadController.doctorReport.summary.fail : "0") + " Failures"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 14
                    }
                }
            }
        }

        // Doctor Checks Detail Table
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 240
            radius: 10
            color: "#1b1f28"
            border.color: "#28303f"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                Text {
                    text: "Health Checks"
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
                        model: (edgepadController && edgepadController.doctorReport && edgepadController.doctorReport.items) ? edgepadController.doctorReport.items : []
                        spacing: 6

                        delegate: Rectangle {
                            width: doctorList.width
                            height: 36
                            radius: 6
                            color: "#15181e"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 10

                                Rectangle {
                                    implicitWidth: 54
                                    implicitHeight: 20
                                    radius: 3
                                    color: {
                                        if (modelData.level === "ok" || modelData.level === "pass") return "#27ae60"
                                        if (modelData.level === "info") return "#2980b9"
                                        if (modelData.level === "warn") return "#d35400"
                                        return "#c0392b"
                                    }
                                    Text {
                                        anchors.centerIn: parent
                                        text: {
                                            if (modelData.level === "ok" || modelData.level === "pass") return "PASS"
                                            return (modelData.level || "INFO").toUpperCase()
                                        }
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
                                    color: "#94a3b8"
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
            color: "#1b1f28"
            border.color: "#28303f"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Service Logs"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "Refresh Logs"
                        icon.name: "view-refresh"
                        onClicked: if (edgepadController) edgepadController.refreshLogs()
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    TextArea {
                        readOnly: true
                        text: (edgepadController && edgepadController.serviceLogs) ? edgepadController.serviceLogs : "No recent journal logs found for edgepad.service."
                        font.family: "monospace"
                        font.pixelSize: 11
                        color: "#94a3b8"
                        background: Rectangle { color: "#12151b"; radius: 6 }
                        selectByMouse: true
                    }
                }
            }
        }
    }
}

