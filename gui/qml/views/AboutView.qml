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

        // Hero Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 180
            radius: 12
            color: "#1e242f"
            border.color: "#3daee9"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 20

                Rectangle {
                    width: 72
                    height: 72
                    radius: 36
                    color: "#3daee9"

                    Text {
                        anchors.centerIn: parent
                        text: "🖐️"
                        font.pixelSize: 36
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: "Edgepad"
                        font.bold: true
                        font.pixelSize: 24
                        color: "#ffffff"
                    }

                    Text {
                        text: "Native Linux Touchpad Edge Gesture Manager for Fedora KDE Plasma & Wayland"
                        font.pixelSize: 13
                        color: "#3daee9"
                    }

                    Text {
                        text: "Version 0.1.0 • Built with Rust and Qt 6 / QML"
                        font.pixelSize: 11
                        color: "#bdc3c7"
                    }

                    Text {
                        text: "Dual-licensed under MIT and Apache-2.0 upstream licenses."
                        font.pixelSize: 10
                        color: "#95a5a6"
                    }
                }
            }
        }

        // Configuration Backup & Transfer Card
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
                    text: "Configuration Management & Backup"
                    font.bold: true
                    font.pixelSize: 15
                    color: "#ffffff"
                }

                Text {
                    text: "Config File: ~/.config/edgepad/edgepad.toml  |  Automatic Backups: ~/.config/edgepad/backups/"
                    color: "#bdc3c7"
                    font.pixelSize: 11
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Button {
                        text: "Export Configuration..."
                        onClicked: {
                            var p = "/tmp/edgepad_backup.toml"
                            edgepadController.exportConfig(p)
                        }
                    }

                    Button {
                        text: "Import Configuration..."
                        onClicked: {
                            var p = "/tmp/edgepad_backup.toml"
                            edgepadController.importConfig(p)
                        }
                    }

                    Item { Layout.fillHeight: true; Layout.fillWidth: true }

                    Button {
                        text: "Reset All to Factory Defaults"
                        onClicked: edgepadController.resetToDefaults()
                    }
                }
            }
        }

        // Architecture & Features Details
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 170
            radius: 12
            color: "#21252d"
            border.color: "#2f3542"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 8

                Text {
                    text: "Key Architectural Features"
                    font.bold: true
                    font.pixelSize: 14
                    color: "#ffffff"
                }

                Text {
                    text: "• Native /dev/uinput virtual keyboard backend safely emits real Linux input events (brightness, volume, media keys).\n• Exclusive multi-touch proxy routes edge gestures without intercepting normal pointer motion, clicks, or two-finger scrolling.\n• Low-latency Unix socket IPC daemon communicates with Qt GUI in real time.\n• Zero stuck keys: all virtual keys are logically auto-released on contact release, error, or shutdown."
                    color: "#bdc3c7"
                    font.pixelSize: 11
                    lineHeight: 1.3
                }
            }
        }
    }
}
