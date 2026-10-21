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
            spacing: 12

            Text {
                text: "Dashboard"
                font.bold: true
                font.pixelSize: 22
                color: "#ffffff"
                Layout.fillWidth: true
            }

            StatusBadge {
                status: edgepadController ? edgepadController.daemonStatus : "stopped"
            }
        }

        // Service Migration / Repair Alert Banner
        Rectangle {
            Layout.fillWidth: true
            visible: Boolean(edgepadController && (edgepadController.legacyServiceDetected || edgepadController.daemonStatus === "error"))
            color: "#2c1c1d"
            border.color: "#e74c3c"
            border.width: 1
            radius: 8
            implicitHeight: bannerCol.implicitHeight + 20

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Text {
                    text: "⚠️"
                    font.pixelSize: 20
                }

                ColumnLayout {
                    id: bannerCol
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: (edgepadController && edgepadController.legacyServiceDetected) ? "Legacy Service Unit Detected" : "Service Issue Detected"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    Text {
                        text: (edgepadController && edgepadController.legacyServiceDetected)
                            ? "A legacy service unit overrides the canonical system service. Click Repair to migrate."
                            : "The daemon service is not running. Click Repair to reset and reload the service unit."
                        font.pixelSize: 12
                        color: "#dcdde1"
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                Button {
                    text: "Repair Service"
                    highlighted: true
                    onClicked: if (edgepadController) edgepadController.repairService()
                }
            }
        }

        // Top Status Cards Grid
        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 920 ? 3 : (root.width > 600 ? 2 : 1)
            rowSpacing: 14
            columnSpacing: 14

            // Card 1: Service Engine Controls
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 130
                radius: 10
                color: "#21252d"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Gesture Service"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#ffffff"
                            Layout.fillWidth: true
                        }
                        Switch {
                            checked: Boolean(edgepadController && edgepadController.masterEnabled)
                            onToggled: if (edgepadController) edgepadController.setMasterEnabled(checked)
                        }
                    }

                    Text {
                        text: (edgepadController && edgepadController.daemonStatus === "running") ? "Daemon is running and active" : "Daemon is stopped"
                        color: (edgepadController && edgepadController.daemonStatus === "running") ? "#27ae60" : "#95a5a6"
                        font.pixelSize: 11
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                            text: (edgepadController && edgepadController.daemonStatus === "running") ? "Restart" : "Start"
                            highlighted: true
                            Layout.fillWidth: true
                            onClicked: {
                                if (!edgepadController) return
                                if (edgepadController.daemonStatus === "running") {
                                    edgepadController.restartService()
                                } else {
                                    edgepadController.startService()
                                }
                            }
                        }

                        Button {
                            text: "Stop"
                            enabled: Boolean(edgepadController && edgepadController.daemonStatus === "running")
                            Layout.fillWidth: true
                            onClicked: if (edgepadController) edgepadController.stopService()
                        }
                    }
                }
            }

            // Card 2: Active Touchpad Hardware
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 130
                radius: 10
                color: "#21252d"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text {
                        text: "Touchpad Device"
                        font.bold: true
                        font.pixelSize: 14
                        color: "#ffffff"
                    }

                    Text {
                        text: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.name) || "Default Touchpad"
                        font.bold: true
                        font.pixelSize: 12
                        color: "#3daee9"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Text {
                        text: (edgepadController && edgepadController.selectedDeviceDetails && edgepadController.selectedDeviceDetails.path) ? edgepadController.selectedDeviceDetails.path : "Auto-detected"
                        color: "#7f8c8d"
                        font.pixelSize: 11
                    }

                    Item { Layout.fillHeight: true }

                    Button {
                        text: "Manage Devices →"
                        flat: true
                        Layout.alignment: Qt.AlignRight
                        onClicked: appWindow.navigateToPage(6)
                    }
                }
            }

            // Card 3: System Preferences & Actions
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 130
                radius: 10
                color: "#21252d"
                border.color: "#2f3542"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Start at Login"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#ffffff"
                            Layout.fillWidth: true
                        }
                        Switch {
                            checked: Boolean(edgepadController && edgepadController.startAtLogin)
                            onToggled: if (edgepadController) edgepadController.setStartAtLogin(checked)
                        }
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                            text: "Restore Defaults"
                            Layout.fillWidth: true
                            onClicked: if (edgepadController) edgepadController.applyDefaultPreset()
                        }

                        Button {
                            text: "Live Tester →"
                            flat: true
                            Layout.fillWidth: true
                            onClicked: appWindow.navigateToPage(5)
                        }
                    }
                }
            }
        }

        // Configured Gestures & Mappings Section
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: summaryCol.implicitHeight + 28
            radius: 10
            color: "#21252d"
            border.color: "#2f3542"
            border.width: 1

            ColumnLayout {
                id: summaryCol
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Configured Actions"
                        font.bold: true
                        font.pixelSize: 15
                        color: "#ffffff"
                        Layout.fillWidth: true
                    }

                    Button {
                        text: "Configure Tap Actions"
                        highlighted: true
                        onClicked: appWindow.navigateToPage(1)
                    }

                    Button {
                        text: "Edit Swipes →"
                        flat: true
                        onClicked: appWindow.navigateToPage(2, 0)
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 760 ? 2 : 1
                    rowSpacing: 10
                    columnSpacing: 14

                    // Left Column: Corner Double-Tap Shortcuts
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 140
                        radius: 8
                        color: "#1a1d24"
                        border.color: "#282d37"
                        border.width: 1

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: appWindow.navigateToPage(1)
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "🎯 Corner Double-Taps"
                                    font.bold: true
                                    font.pixelSize: 12
                                    color: "#3daee9"
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: "Configure →"
                                    font.pixelSize: 10
                                    color: "#3daee9"
                                }
                            }

                            Text {
                                text: "↖ Top-Left:  " + ((edgepadController && edgepadController.cornerTapRules && edgepadController.cornerTapRules["top-left"]) ? edgepadController.cornerTapRules["top-left"].shortcutDisplay : "Unset")
                                font.pixelSize: 11
                                color: "#ecf0f1"
                            }
                            Text {
                                text: "↗ Top-Right:  " + ((edgepadController && edgepadController.cornerTapRules && edgepadController.cornerTapRules["top-right"]) ? edgepadController.cornerTapRules["top-right"].shortcutDisplay : "Unset")
                                font.pixelSize: 11
                                color: "#ecf0f1"
                            }
                            Text {
                                text: "↙ Bottom-Left:  " + ((edgepadController && edgepadController.cornerTapRules && edgepadController.cornerTapRules["bottom-left"]) ? edgepadController.cornerTapRules["bottom-left"].shortcutDisplay : "Unset")
                                font.pixelSize: 11
                                color: "#ecf0f1"
                            }
                            Text {
                                text: "↘ Bottom-Right:  " + ((edgepadController && edgepadController.cornerTapRules && edgepadController.cornerTapRules["bottom-right"]) ? edgepadController.cornerTapRules["bottom-right"].shortcutDisplay : "Unset")
                                font.pixelSize: 11
                                color: "#ecf0f1"
                            }
                        }
                    }

                    // Right Column: Directional Edge Swipes
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 140
                        radius: 8
                        color: "#1a1d24"
                        border.color: "#282d37"
                        border.width: 1

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: appWindow.navigateToPage(2, 0)
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "⚡ Edge Swipes"
                                    font.bold: true
                                    font.pixelSize: 12
                                    color: "#f39c12"
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: "Configure →"
                                    font.pixelSize: 10
                                    color: "#f39c12"
                                }
                            }

                            Text {
                                text: "Left Edge (Brightness):  ↑ Up / ↓ Down"
                                font.pixelSize: 11
                                color: "#ecf0f1"
                            }
                            Text {
                                text: "Right Edge (Volume):  ↑ Up / ↓ Down"
                                font.pixelSize: 11
                                color: "#ecf0f1"
                            }
                            Text {
                                text: "Rotary Encoder:  Proportional discrete ticks"
                                font.pixelSize: 11
                                color: "#bdc3c7"
                            }
                        }
                    }
                }
            }
        }
    }
}
