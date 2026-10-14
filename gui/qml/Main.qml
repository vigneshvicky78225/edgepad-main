import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "views"

ApplicationWindow {
    id: appWindow

    visible: true
    width: 1060
    height: 720
    minimumWidth: 880
    minimumHeight: 580
    title: "Edgepad — Linux Touchpad Edge Gesture Manager"
    color: "#181b20"

    // Top Header Bar
    header: ToolBar {
        background: Rectangle {
            color: "#1f232b"
            border.color: "#2b303c"
            border.width: 1
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 14

            Rectangle {
                width: 28
                height: 28
                radius: 6
                color: "#3daee9"
                Text {
                    anchors.centerIn: parent
                    text: "🖐️"
                    font.pixelSize: 16
                }
            }

            Text {
                text: "Edgepad"
                font.bold: true
                font.pixelSize: 16
                color: "#ffffff"
            }

            Text {
                text: "•"
                color: "#7f8c8d"
            }

            StatusBadge {
                status: edgepadController.daemonStatus
            }

            Item { Layout.fillWidth: true }

            // Master Enable switch in toolbar
            RowLayout {
                spacing: 8
                Text {
                    text: "Gestures:"
                    font.pixelSize: 12
                    color: "#bdc3c7"
                }
                Switch {
                    checked: edgepadController.masterEnabled
                    onToggled: edgepadController.setMasterEnabled(checked)
                }
            }

            // Unsaved changes alert & Save button
            Rectangle {
                visible: edgepadController.hasUnsavedChanges
                implicitWidth: unsavedRow.implicitWidth + 14
                implicitHeight: 28
                radius: 14
                color: "#d35400"

                RowLayout {
                    id: unsavedRow
                    anchors.centerIn: parent
                    spacing: 6
                    Text {
                        text: "● Unsaved Changes"
                        font.bold: true
                        font.pixelSize: 11
                        color: "#ffffff"
                    }
                }
            }

            Button {
                text: "Save Changes"
                highlighted: edgepadController.hasUnsavedChanges
                enabled: edgepadController.hasUnsavedChanges
                onClicked: edgepadController.saveConfiguration()
            }
        }
    }

    // Main Body: Sidebar + StackLayout Views
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar Navigation
        Rectangle {
            Layout.preferredWidth: 200
            Layout.fillHeight: true
            color: "#1b1e25"
            border.color: "#282d37"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                Repeater {
                    model: [
                        { name: "Dashboard", icon: "📊" },
                        { name: "Gestures", icon: "⚡" },
                        { name: "Edge Zones", icon: "📐" },
                        { name: "Touchpad", icon: "🖱️" },
                        { name: "Live Tester", icon: "🎯" },
                        { name: "Diagnostics", icon: "🩺" },
                        { name: "About", icon: "ℹ️" }
                    ]

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 42
                        radius: 8
                        color: navStack.currentIndex === index ? "#3daee9" : (sidebarHover.containsMouse ? "#262b35" : "transparent")

                        MouseArea {
                            id: sidebarHover
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: navStack.currentIndex = index
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 12

                            Text {
                                text: modelData.icon
                                font.pixelSize: 16
                            }

                            Text {
                                text: modelData.name
                                font.bold: navStack.currentIndex === index
                                font.pixelSize: 13
                                color: navStack.currentIndex === index ? "#ffffff" : "#ecf0f1"
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // Daemon Engine Version Info Card at bottom of sidebar
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 48
                    radius: 8
                    color: "#15181e"

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Text {
                            text: "Edgepad Engine v0.1.0"
                            font.bold: true
                            font.pixelSize: 11
                            color: "#bdc3c7"
                        }
                        Text {
                            text: "Fedora KDE • Wayland"
                            font.pixelSize: 10
                            color: "#7f8c8d"
                        }
                    }
                }
            }
        }

        // View Stack
        StackLayout {
            id: navStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: 0

            DashboardView {}
            GesturesView {}
            EdgeZonesView {}
            DeviceSelectionView {}
            LiveTesterView {}
            DiagnosticsView {}
            AboutView {}
        }
    }

    // Bottom Toast / Status Bar for errors & messages
    footer: ToolBar {
        visible: edgepadController.lastMessage !== "" || edgepadController.lastError !== ""
        background: Rectangle {
            color: edgepadController.lastError !== "" ? "#c0392b" : "#27ae60"
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16

            Text {
                text: edgepadController.lastError !== "" ? ("⚠️ " + edgepadController.lastError) : ("✓ " + edgepadController.lastMessage)
                font.bold: true
                font.pixelSize: 12
                color: "#ffffff"
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Button {
                text: "Dismiss"
                flat: true
                onClicked: {
                    edgepadController.lastError = ""
                    edgepadController.lastMessage = ""
                }
            }
        }
    }
}
