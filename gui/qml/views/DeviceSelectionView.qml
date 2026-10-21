import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root

    readonly property string currentSelectedDevice: edgepadController ? edgepadController.selectedDevice : ""
    readonly property var touchpadsList: (edgepadController && edgepadController.touchpads) ? edgepadController.touchpads : []

    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Page Header
        RowLayout {
            Layout.fillWidth: true

            Text {
                text: "Input Devices"
                font.bold: true
                font.pixelSize: 20
                color: "#ffffff"
                Layout.fillWidth: true
            }

            Button {
                text: "Scan Devices"
                icon.name: "view-refresh"
                onClicked: {
                    if (edgepadController) {
                        edgepadController.refreshDevices()
                    }
                }
            }
        }

        // Automatic Selection Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 60
            radius: 10
            color: currentSelectedDevice === "auto" ? "#1e2b37" : "#1b1f28"
            border.color: currentSelectedDevice === "auto" ? "#3daee9" : "#28303f"
            border.width: currentSelectedDevice === "auto" ? 2 : 1

            MouseArea {
                anchors.fill: parent
                onClicked: if (edgepadController) edgepadController.selectDevice("auto")
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                RadioButton {
                    checked: currentSelectedDevice === "auto"
                    onClicked: if (edgepadController) edgepadController.selectDevice("auto")
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "Automatic Touchpad Discovery"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }
                    Text {
                        text: "Automatically selects the primary touchpad at startup"
                        color: "#94a3b8"
                        font.pixelSize: 11
                    }
                }

                Rectangle {
                    implicitWidth: 50
                    implicitHeight: 20
                    radius: 10
                    color: "#182736"
                    border.color: "#3daee9"
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "Auto"
                        color: "#38bdf8"
                        font.bold: true
                        font.pixelSize: 10
                    }
                }
            }
        }

        Text {
            text: "Detected Touchpads (" + touchpadsList.length + ")"
            font.bold: true
            font.pixelSize: 14
            color: "#cbd5e1"
        }

        // Touchpad Devices List
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10

            Repeater {
                model: touchpadsList

                Rectangle {
                    id: devCard
                    property bool showDetails: false
                    readonly property bool isSelected: currentSelectedDevice === modelData.path ||
                                                       currentSelectedDevice === modelData.persistent_path

                    Layout.fillWidth: true
                    implicitHeight: cardCol.implicitHeight + 24
                    radius: 10
                    color: isSelected ? "#1e2b37" : "#1b1f28"
                    border.color: isSelected ? "#3daee9" : "#28303f"
                    border.width: isSelected ? 2 : 1

                    ColumnLayout {
                        id: cardCol
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            RadioButton {
                                checked: devCard.isSelected
                                onClicked: if (edgepadController) edgepadController.selectDevice(modelData.persistent_path || modelData.path)
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                RowLayout {
                                    spacing: 8
                                    Text {
                                        text: modelData.name
                                        font.bold: true
                                        font.pixelSize: 14
                                        color: "#ffffff"
                                    }

                                    Rectangle {
                                        implicitWidth: permText.implicitWidth + 8
                                        implicitHeight: 18
                                        radius: 4
                                        color: (modelData.readable && modelData.writable) ? "#163324" : "#3b1e1e"
                                        border.color: (modelData.readable && modelData.writable) ? "#22c55e" : "#ef4444"
                                        border.width: 1
                                        Text {
                                            id: permText
                                            anchors.centerIn: parent
                                            text: (modelData.readable && modelData.writable) ? "Ready" : "Permissions Issue"
                                            color: (modelData.readable && modelData.writable) ? "#4ade80" : "#f87171"
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }
                                }
                            }

                            Button {
                                text: devCard.showDetails ? "Hide Details" : "Details"
                                flat: true
                                onClicked: devCard.showDetails = !devCard.showDetails
                            }

                            Button {
                                text: devCard.isSelected ? "Selected" : "Select"
                                highlighted: !devCard.isSelected
                                enabled: !devCard.isSelected
                                onClicked: if (edgepadController) edgepadController.selectDevice(modelData.persistent_path || modelData.path)
                            }
                        }

                        // Collapsible technical details
                        ColumnLayout {
                            visible: devCard.showDetails
                            Layout.fillWidth: true
                            Layout.leftMargin: 36
                            spacing: 4

                            Rectangle { Layout.fillWidth: true; height: 1; color: "#252e3d" }

                            Text {
                                text: "Node: " + modelData.path + "  •  Vendor/Product: " + modelData.id
                                color: "#94a3b8"
                                font.pixelSize: 11
                            }

                            Text {
                                text: "Persistent: " + (modelData.persistent_path || "None")
                                color: "#64748b"
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Text {
                                text: "Resolution: X: " + modelData.x_range + "  Y: " + modelData.y_range + "  •  Slots: " + modelData.slots
                                color: "#94a3b8"
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }
        }
    }
}

