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

        // Page Header
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: "Touchpad Device Selection"
                    font.bold: true
                    font.pixelSize: 22
                    color: "#ffffff"
                }
                Text {
                    text: "Select physical touchpad device and inspect permissions and hardware identifiers"
                    font.pixelSize: 13
                    color: "#95a5a6"
                }
            }

            Button {
                text: "Refresh Devices"
                highlighted: true
                onClicked: edgepadController.refreshDevices()
            }
        }

        // Automatic Selection Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 70
            radius: 10
            color: edgepadController.selectedDevice === "auto" ? "#1e2b37" : "#21252d"
            border.color: edgepadController.selectedDevice === "auto" ? "#3daee9" : "#2f3542"
            border.width: edgepadController.selectedDevice === "auto" ? 2 : 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 14

                RadioButton {
                    checked: edgepadController.selectedDevice === "auto"
                    onClicked: edgepadController.selectDevice("auto")
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "Automatic Touchpad Discovery (Recommended)"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }
                    Text {
                        text: "Automatically selects the primary physical touchpad at startup, robust to reboot node changes"
                        color: "#bdc3c7"
                        font.pixelSize: 11
                    }
                }

                Rectangle {
                    implicitWidth: 90
                    implicitHeight: 22
                    radius: 4
                    color: "#27ae60"
                    Text {
                        anchors.centerIn: parent
                        text: "RECOMMENDED"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 9
                    }
                }
            }
        }

        Text {
            text: "Discovered Touchpad Devices (" + edgepadController.touchpads.length + ")"
            font.bold: true
            font.pixelSize: 15
            color: "#ffffff"
        }

        // Touchpad Devices List
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10

            Repeater {
                model: edgepadController.touchpads

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 110
                    radius: 10
                    color: (edgepadController.selectedDevice === modelData.path ||
                            edgepadController.selectedDevice === modelData.persistent_path) ? "#1e2b37" : "#21252d"
                    border.color: (edgepadController.selectedDevice === modelData.path ||
                                   edgepadController.selectedDevice === modelData.persistent_path) ? "#3daee9" : "#2f3542"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 14

                        RadioButton {
                            checked: (edgepadController.selectedDevice === modelData.path ||
                                      edgepadController.selectedDevice === modelData.persistent_path)
                            onClicked: edgepadController.selectDevice(modelData.persistent_path || modelData.path)
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3

                            RowLayout {
                                spacing: 8
                                Text {
                                    text: modelData.name
                                    font.bold: true
                                    font.pixelSize: 14
                                    color: "#ffffff"
                                }
                                Rectangle {
                                    implicitWidth: idText.implicitWidth + 8
                                    implicitHeight: 18
                                    radius: 3
                                    color: "#2c3e50"
                                    Text {
                                        id: idText
                                        anchors.centerIn: parent
                                        text: "Vendor:Product " + modelData.id
                                        color: "#3daee9"
                                        font.pixelSize: 10
                                    }
                                }
                            }

                            Text {
                                text: "Device Node: " + modelData.path + "  |  Persistent: " + modelData.persistent_path
                                color: "#bdc3c7"
                                font.pixelSize: 11
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            RowLayout {
                                spacing: 14
                                Text {
                                    text: "Resolution: X: " + modelData.x_range + "  Y: " + modelData.y_range + "  Slots: " + modelData.slots
                                    color: "#95a5a6"
                                    font.pixelSize: 11
                                }

                                Text {
                                    text: "Permissions: " + (modelData.readable ? "✓ Read OK" : "✗ Read Denied") + " • " + (modelData.writable ? "✓ Write OK" : "✗ Write Denied")
                                    color: (modelData.readable && modelData.writable) ? "#27ae60" : "#e74c3c"
                                    font.bold: true
                                    font.pixelSize: 11
                                }
                            }
                        }

                        Button {
                            text: "Select Device"
                            onClicked: edgepadController.selectDevice(modelData.persistent_path || modelData.path)
                        }
                    }
                }
            }
        }

        // Permissions & Access Overview Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 90
            radius: 10
            color: "#1a1e26"
            border.color: "#2c3e50"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 14

                Rectangle {
                    width: 36
                    height: 36
                    radius: 18
                    color: "#2c3e50"
                    Text {
                        anchors.centerIn: parent
                        text: "🛡️"
                        font.pixelSize: 16
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "Input Access & Security Model"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }
                    Text {
                        text: "Access to /dev/input and /dev/uinput is granted through user membership in the 'input' group and systemd uaccess. Root access is never required."
                        color: "#95a5a6"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
}
