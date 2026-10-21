import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root

    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Application Header Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: appHeaderRow.implicitHeight + 28
            radius: 10
            color: "#1b1f28"
            border.color: "#28303f"
            border.width: 1

            RowLayout {
                id: appHeaderRow
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                Rectangle {
                    width: 44
                    height: 44
                    radius: 10
                    color: "#202530"
                    border.color: "#3daee9"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "🖐️"
                        font.pixelSize: 22
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    RowLayout {
                        spacing: 10
                        Text {
                            text: "Edgepad"
                            font.bold: true
                            font.pixelSize: 18
                            color: "#ffffff"
                        }
                        Rectangle {
                            implicitWidth: verText.implicitWidth + 12
                            implicitHeight: 20
                            radius: 10
                            color: "#182736"
                            border.color: "#3daee9"
                            border.width: 1
                            Text {
                                id: verText
                                anchors.centerIn: parent
                                text: "v0.2.5"
                                color: "#38bdf8"
                                font.bold: true
                                font.pixelSize: 10
                            }
                        }
                    }

                    Text {
                        text: "Touchpad edge gesture manager for Linux (Fedora KDE Plasma & Wayland)"
                        font.pixelSize: 12
                        color: "#94a3b8"
                    }
                }
            }
        }

        // Configuration Management Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: configCol.implicitHeight + 28
            radius: 10
            color: "#1b1f28"
            border.color: "#28303f"
            border.width: 1

            ColumnLayout {
                id: configCol
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "Configuration"
                    font.bold: true
                    font.pixelSize: 15
                    color: "#ffffff"
                }

                Text {
                    text: "Location: ~/.config/edgepad/edgepad.toml"
                    color: "#94a3b8"
                    font.pixelSize: 11
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Button {
                        text: "Export Config"
                        icon.name: "document-save"
                        onClicked: {
                            if (edgepadController) {
                                var p = "/tmp/edgepad_backup.toml"
                                edgepadController.exportConfig(p)
                            }
                        }
                    }

                    Button {
                        text: "Import Config"
                        icon.name: "document-open"
                        onClicked: {
                            if (edgepadController) {
                                var p = "/tmp/edgepad_backup.toml"
                                edgepadController.importConfig(p)
                            }
                        }
                    }

                    Item { Layout.fillHeight: true; Layout.fillWidth: true }

                    Button {
                        text: "Reset Defaults"
                        icon.name: "edit-undo"
                        onClicked: {
                            if (edgepadController) {
                                edgepadController.resetToDefaults()
                            }
                        }
                    }
                }
            }
        }

        // System & License Info
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: sysInfoCol.implicitHeight + 28
            radius: 10
            color: "#1b1f28"
            border.color: "#28303f"
            border.width: 1

            ColumnLayout {
                id: sysInfoCol
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8

                Text {
                    text: "System Information"
                    font.bold: true
                    font.pixelSize: 14
                    color: "#ffffff"
                }

                GridLayout {
                    columns: 2
                    rowSpacing: 4
                    columnSpacing: 16

                    Text { text: "Daemon Service:"; color: "#64748b"; font.pixelSize: 11 }
                    Text { text: "edgepad.service (systemd --user)"; color: "#cbd5e1"; font.pixelSize: 11 }

                    Text { text: "Backend Engine:"; color: "#64748b"; font.pixelSize: 11 }
                    Text { text: "Rust • libevdev • uinput"; color: "#cbd5e1"; font.pixelSize: 11 }

                    Text { text: "GUI Framework:"; color: "#64748b"; font.pixelSize: 11 }
                    Text { text: "PySide6 • Qt Quick / QML"; color: "#cbd5e1"; font.pixelSize: 11 }

                    Text { text: "License:"; color: "#64748b"; font.pixelSize: 11 }
                    Text { text: "MIT / Apache-2.0 Dual License"; color: "#cbd5e1"; font.pixelSize: 11 }
                }
            }
        }
    }
}

