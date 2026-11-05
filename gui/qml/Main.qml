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
    minimumWidth: 720
    minimumHeight: 500
    title: "Edgepad — Linux Touchpad Edge Gesture Manager"
    color: "#181b20"

    SystemPalette {
        id: sysPalette
        colorGroup: SystemPalette.Active
    }

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
                status: edgepadController ? edgepadController.daemonStatus : "stopped"
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
                    checked: Boolean(edgepadController && edgepadController.masterEnabled)
                    onToggled: {
                        if (edgepadController) {
                            edgepadController.setMasterEnabled(checked)
                        }
                    }
                }
            }

            // Unsaved changes alert & Save button
            Rectangle {
                visible: Boolean(edgepadController && edgepadController.hasUnsavedChanges)
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
                highlighted: Boolean(edgepadController && edgepadController.hasUnsavedChanges)
                enabled: Boolean(edgepadController && edgepadController.hasUnsavedChanges)
                onClicked: {
                    if (edgepadController) {
                        edgepadController.saveConfiguration()
                    }
                }
            }
        }
    }

    function navigateToPage(pageIndex, subTabIndex = 0) {
        var idx = 0;
        if (typeof pageIndex === "string") {
            var targets = {
                "dashboard": 0,
                "tap-actions": 1,
                "gestures": 2,
                "calibration": 3,
                "gesture-calibration": 3,
                "live-tester": 4,
                "touchpad": 5,
                "device": 5,
                "devices": 5,
                "diagnostics": 6,
                "about": 7,
                "settings": 7,
                "hitbox-calibration": 8,
                "hitbox": 8
            };
            idx = targets[pageIndex] !== undefined ? targets[pageIndex] : 0;
        } else {
            idx = Number(pageIndex);
        }
        navStack.currentIndex = Math.max(0, Math.min(idx, navStack.count - 1));
        if (navStack.currentIndex === 2 && subTabIndex !== undefined) {
            gesturesViewItem.selectedTab = subTabIndex;
        }
    }

    function isNavActive(item) {
        return item.page === navStack.currentIndex;
    }

    // Main Body: Sidebar + StackLayout Views
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Responsive Sidebar Navigation
        Rectangle {
            id: sidebarRect
            readonly property bool isCompact: appWindow.width < 860
            Layout.preferredWidth: isCompact ? 64 : 200
            Layout.fillHeight: true
            color: "#1b1e25"
            border.color: "#282d37"
            border.width: 1

            Behavior on Layout.preferredWidth {
                NumberAnimation { duration: 150; easing.type: Easing.InOutQuad }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: sidebarRect.isCompact ? 6 : 10
                spacing: 6

                Repeater {
                    model: [
                        { name: "Dashboard", icon: "📊", page: 0 },
                        { name: "Tap Actions", icon: "🎯", page: 1 },
                        { name: "Edge Gestures", icon: "⚡", page: 2 },
                        { name: "Calibration", icon: "🎛️", page: 3 },
                        { name: "Live Tester", icon: "🧪", page: 4 },
                        { name: "Devices", icon: "🖱️", page: 5 },
                        { name: "Diagnostics", icon: "🩺", page: 6 },
                        { name: "About", icon: "ℹ️", page: 7 }
                    ]

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 38
                        radius: 8
                        color: isNavActive(modelData) ? "#3daee9" : (sidebarHover.containsMouse ? "#262b35" : "transparent")

                        MouseArea {
                            id: sidebarHover
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: appWindow.navigateToPage(modelData.page, modelData.tab)
                        }

                        ToolTip.visible: sidebarHover.containsMouse
                        ToolTip.text: modelData.name
                        ToolTip.delay: 300

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: sidebarRect.isCompact ? 0 : 12
                            anchors.rightMargin: sidebarRect.isCompact ? 0 : 12
                            spacing: sidebarRect.isCompact ? 0 : 12

                            Text {
                                text: modelData.icon
                                font.pixelSize: 16
                                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                                Layout.fillWidth: sidebarRect.isCompact
                                horizontalAlignment: sidebarRect.isCompact ? Text.AlignHCenter : Text.AlignLeft
                            }

                            Text {
                                visible: !sidebarRect.isCompact
                                text: modelData.name
                                font.bold: isNavActive(modelData)
                                font.pixelSize: 13
                                color: isNavActive(modelData) ? "#ffffff" : "#ecf0f1"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // Daemon Engine Version Info Card at bottom of sidebar
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: sidebarRect.isCompact ? 36 : 48
                    radius: 8
                    color: "#15181e"

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Text {
                            text: sidebarRect.isCompact ? "v0.2.5" : "Edgepad Engine v0.2.5"
                            font.bold: true
                            font.pixelSize: sidebarRect.isCompact ? 10 : 11
                            color: "#bdc3c7"
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            visible: !sidebarRect.isCompact
                            text: "Fedora KDE • Wayland"
                            font.pixelSize: 10
                            color: "#7f8c8d"
                            Layout.alignment: Qt.AlignHCenter
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

            DashboardView { id: dashboardViewItem }
            TapActionsView { id: tapActionsViewItem }
            GesturesView { id: gesturesViewItem }
            GestureCalibrationView {}
            LiveTesterView {}
            DeviceSelectionView {}
            DiagnosticsView {}
            AboutView {}
            HitboxCalibrationView {}
        }
    }

    // Bottom Toast / Status Bar for errors & messages
    footer: ToolBar {
        id: notificationFooter
        visible: Boolean(edgepadController && (edgepadController.lastMessage !== "" || edgepadController.lastError !== ""))
        implicitHeight: footerLayout.implicitHeight + 16

        background: Rectangle {
            color: (edgepadController && edgepadController.lastError !== "") ? "#c0392b" : "#27ae60"
            border.color: (edgepadController && edgepadController.lastError !== "") ? "#e74c3c" : "#2ecc71"
            border.width: 1
        }

        RowLayout {
            id: footerLayout
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.topMargin: 8
            anchors.bottomMargin: 8
            spacing: 12

            Text {
                text: (edgepadController && edgepadController.lastError !== "") ? "⚠️" : "✓"
                font.pixelSize: 14
                color: "#ffffff"
                Layout.alignment: Qt.AlignVCenter
            }

            Text {
                text: {
                    if (!edgepadController) return ""
                    return edgepadController.lastError !== "" ? edgepadController.lastError : edgepadController.lastMessage
                }
                font.bold: true
                font.pixelSize: 12
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
            }

            Button {
                id: dismissBtn
                text: "Dismiss"
                flat: true
                Layout.alignment: Qt.AlignVCenter
                onClicked: {
                    if (edgepadController) {
                        edgepadController.dismissCurrentNotification()
                    }
                }
            }
        }
    }
}
