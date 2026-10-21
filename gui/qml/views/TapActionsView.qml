import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root

    contentWidth: availableWidth
    clip: true

    property string selectedCorner: "top-left"

    // Corner definition model
    readonly property var cornerList: [
        { id: "top-left", name: "Top-Left Corner", icon: "↖️", pos: "top-left" },
        { id: "top-right", name: "Top-Right Corner", icon: "↗️", pos: "top-right" },
        { id: "bottom-left", name: "Bottom-Left Corner", icon: "↙️", pos: "bottom-left" },
        { id: "bottom-right", name: "Bottom-Right Corner", icon: "↘️", pos: "bottom-right" }
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Page Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: "Touchpad Corner Double-Tap Actions"
                font.bold: true
                font.pixelSize: 22
                color: "#ffffff"
                Layout.fillWidth: true
            }

            Button {
                text: "Restore Defaults"
                onClicked: resetCornerDefaultsDialog.open()
            }
        }

        // Responsive Layout: Touchpad Canvas on Left (or Top), 4 Corner Double-Tap Cards on Right (or Bottom)
        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 860 ? 2 : 1
            rowSpacing: 16
            columnSpacing: 16
            Layout.alignment: Qt.AlignTop

            // Left Column: Interactive Touchpad Corner Diagram
            Rectangle {
                id: leftColBox
                Layout.fillWidth: root.width <= 860
                Layout.preferredWidth: root.width > 860 ? 350 : -1
                Layout.maximumWidth: root.width <= 860 ? 460 : -1
                Layout.alignment: Qt.AlignTop | (root.width <= 860 ? Qt.AlignHCenter : Qt.AlignLeft)
                implicitHeight: leftColLayout.implicitHeight + 32
                radius: 12
                color: "#1a1d24"
                border.color: "#282d37"
                border.width: 1

                ColumnLayout {
                    id: leftColLayout
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    // Visual Touchpad Surface
                    Rectangle {
                        id: touchpadSurface
                        Layout.fillWidth: true
                        implicitHeight: 270
                        radius: 16
                        color: "#15181f"
                        border.color: "#2c3e50"
                        border.width: 2
                        clip: true

                        // Subtle surface grid
                        Canvas {
                            anchors.fill: parent
                            opacity: 0.1
                            onPaint: {
                                var ctx = getContext("2d");
                                ctx.strokeStyle = "#ffffff";
                                ctx.lineWidth = 1;
                                var step = 20;
                                for (var x = step; x < width; x += step) {
                                    ctx.beginPath();
                                    ctx.moveTo(x, 0);
                                    ctx.lineTo(x, height);
                                    ctx.stroke();
                                }
                                for (var y = step; y < height; y += step) {
                                    ctx.beginPath();
                                    ctx.moveTo(0, y);
                                    ctx.lineTo(width, y);
                                    ctx.stroke();
                                }
                            }
                        }

                        // Center label
                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Text {
                                text: "TOUCHPAD SURFACE"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#4a5568"
                                horizontalAlignment: Text.AlignHCenter
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "Double-Tap Corner Zones (" + Math.round((edgepadController ? edgepadController.cornerHitbox : 0.15) * 100) + "% Hitbox)"
                                font.pixelSize: 10
                                color: "#3daee9"
                                horizontalAlignment: Text.AlignHCenter
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }

                        // Corner Zone: Top-Left
                        Rectangle {
                            id: cornerTL
                            x: 0
                            y: 0
                            width: touchpadSurface.width * (edgepadController ? edgepadController.cornerHitbox : 0.15)
                            height: touchpadSurface.height * (edgepadController ? edgepadController.cornerHitbox : 0.15)
                            color: root.selectedCorner === "top-left" ? "#1e4976" : "#1a2a3a"
                            opacity: {
                                var r = (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules["top-left"] || {}) : {};
                                return r.enabled ? 0.9 : 0.4;
                            }
                            border.color: root.selectedCorner === "top-left" ? "#3daee9" : "#2980b9"
                            border.width: root.selectedCorner === "top-left" ? 2 : 1
                            radius: 8
                            clip: true

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedCorner = "top-left"
                            }

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 2
                                Text {
                                    text: parent.parent.width < 50 ? "↖" : "↖ Top-Left"
                                    font.bold: true
                                    font.pixelSize: parent.parent.width < 50 ? 9 : 11
                                    color: "#ffffff"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    visible: parent.parent.height >= 50 && parent.parent.width >= 50
                                    text: {
                                        var r = (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules["top-left"] || {}) : {};
                                        return r.configured ? r.shortcutDisplay : "Unset";
                                    }
                                    font.pixelSize: 9
                                    color: root.selectedCorner === "top-left" ? "#3daee9" : "#94a3b8"
                                    Layout.alignment: Qt.AlignHCenter
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: parent.parent.width - 8
                                }
                            }
                        }

                        // Corner Zone: Top-Right
                        Rectangle {
                            id: cornerTR
                            x: touchpadSurface.width - width
                            y: 0
                            width: touchpadSurface.width * (edgepadController ? edgepadController.cornerHitbox : 0.15)
                            height: touchpadSurface.height * (edgepadController ? edgepadController.cornerHitbox : 0.15)
                            color: root.selectedCorner === "top-right" ? "#1e4976" : "#1a2a3a"
                            opacity: {
                                var r = (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules["top-right"] || {}) : {};
                                return r.enabled ? 0.9 : 0.4;
                            }
                            border.color: root.selectedCorner === "top-right" ? "#3daee9" : "#2980b9"
                            border.width: root.selectedCorner === "top-right" ? 2 : 1
                            radius: 8
                            clip: true

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedCorner = "top-right"
                            }

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 2
                                Text {
                                    text: parent.parent.width < 50 ? "↗" : "↗ Top-Right"
                                    font.bold: true
                                    font.pixelSize: parent.parent.width < 50 ? 9 : 11
                                    color: "#ffffff"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    visible: parent.parent.height >= 50 && parent.parent.width >= 50
                                    text: {
                                        var r = (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules["top-right"] || {}) : {};
                                        return r.configured ? r.shortcutDisplay : "Unset";
                                    }
                                    font.pixelSize: 9
                                    color: root.selectedCorner === "top-right" ? "#3daee9" : "#94a3b8"
                                    Layout.alignment: Qt.AlignHCenter
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: parent.parent.width - 8
                                }
                            }
                        }

                        // Corner Zone: Bottom-Left
                        Rectangle {
                            id: cornerBL
                            x: 0
                            y: touchpadSurface.height - height
                            width: touchpadSurface.width * (edgepadController ? edgepadController.cornerHitbox : 0.15)
                            height: touchpadSurface.height * (edgepadController ? edgepadController.cornerHitbox : 0.15)
                            color: root.selectedCorner === "bottom-left" ? "#1e4976" : "#1a2a3a"
                            opacity: {
                                var r = (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules["bottom-left"] || {}) : {};
                                return r.enabled ? 0.9 : 0.4;
                            }
                            border.color: root.selectedCorner === "bottom-left" ? "#3daee9" : "#2980b9"
                            border.width: root.selectedCorner === "bottom-left" ? 2 : 1
                            radius: 8
                            clip: true

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedCorner = "bottom-left"
                            }

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 2
                                Text {
                                    text: parent.parent.width < 50 ? "↙" : "↙ Bottom-Left"
                                    font.bold: true
                                    font.pixelSize: parent.parent.width < 50 ? 9 : 11
                                    color: "#ffffff"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    visible: parent.parent.height >= 50 && parent.parent.width >= 50
                                    text: {
                                        var r = (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules["bottom-left"] || {}) : {};
                                        return r.configured ? r.shortcutDisplay : "Unset";
                                    }
                                    font.pixelSize: 9
                                    color: root.selectedCorner === "bottom-left" ? "#3daee9" : "#94a3b8"
                                    Layout.alignment: Qt.AlignHCenter
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: parent.parent.width - 8
                                }
                            }
                        }

                        // Corner Zone: Bottom-Right
                        Rectangle {
                            id: cornerBR
                            x: touchpadSurface.width - width
                            y: touchpadSurface.height - height
                            width: touchpadSurface.width * (edgepadController ? edgepadController.cornerHitbox : 0.15)
                            height: touchpadSurface.height * (edgepadController ? edgepadController.cornerHitbox : 0.15)
                            color: root.selectedCorner === "bottom-right" ? "#1e4976" : "#1a2a3a"
                            opacity: {
                                var r = (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules["bottom-right"] || {}) : {};
                                return r.enabled ? 0.9 : 0.4;
                            }
                            border.color: root.selectedCorner === "bottom-right" ? "#3daee9" : "#2980b9"
                            border.width: root.selectedCorner === "bottom-right" ? 2 : 1
                            radius: 8
                            clip: true

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedCorner = "bottom-right"
                            }

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 2
                                Text {
                                    text: parent.parent.width < 50 ? "↘" : "↘ Bottom-Right"
                                    font.bold: true
                                    font.pixelSize: parent.parent.width < 50 ? 9 : 11
                                    color: "#ffffff"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    visible: parent.parent.height >= 50 && parent.parent.width >= 50
                                    text: {
                                        var r = (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules["bottom-right"] || {}) : {};
                                        return r.configured ? r.shortcutDisplay : "Unset";
                                    }
                                    font.pixelSize: 9
                                    color: root.selectedCorner === "bottom-right" ? "#3daee9" : "#94a3b8"
                                    Layout.alignment: Qt.AlignHCenter
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: parent.parent.width - 8
                                }
                            }
                        }
                    }

                    // Legend & Quick selection buttons
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Repeater {
                            model: root.cornerList
                            Button {
                                Layout.fillWidth: true
                                text: modelData.icon
                                highlighted: root.selectedCorner === modelData.id
                                onClicked: root.selectedCorner = modelData.id
                                ToolTip.visible: hovered
                                ToolTip.text: modelData.name
                            }
                        }
                    }

                    // Corner Hitbox Size Slider Card
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 68
                        radius: 8
                        color: "#15181f"
                        border.color: "#282d37"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Corner Hitbox Size:"
                                    font.bold: true
                                    font.pixelSize: 12
                                    color: "#ffffff"
                                }
                                Text {
                                    text: Math.round((edgepadController ? edgepadController.cornerHitbox : 0.15) * 100) + "%"
                                    font.bold: true
                                    font.pixelSize: 13
                                    color: "#3daee9"
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: "5% – 35%"
                                    font.pixelSize: 11
                                    color: "#95a5a6"
                                }
                            }

                            Slider {
                                id: hitboxSlider
                                Layout.fillWidth: true
                                from: 0.05
                                to: 0.35
                                stepSize: 0.01
                                value: edgepadController ? edgepadController.cornerHitbox : 0.15
                                onMoved: {
                                    if (edgepadController) edgepadController.setCornerHitbox(value)
                                }
                            }
                        }
                    }
                }
            }

            // Right Column: The 4 Corner Double-Tap Configuration Cards
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 12

                Repeater {
                    model: root.cornerList

                    Rectangle {
                        id: cornerCard
                        Layout.fillWidth: true
                        implicitHeight: 120
                        radius: 12
                        color: isSelected ? "#222733" : "#1a1d24"
                        border.color: isSelected ? "#3daee9" : "#282d37"
                        border.width: isSelected ? 2 : 1

                        readonly property bool isSelected: root.selectedCorner === modelData.id
                        readonly property var rule: (edgepadController && edgepadController.cornerTapRules) ? (edgepadController.cornerTapRules[modelData.id] || {}) : {}
                        readonly property bool isConfigured: rule.configured === true
                        readonly property bool isEnabled: rule.enabled === true

                        MouseArea {
                            anchors.fill: parent
                            propagateComposedEvents: true
                            onClicked: function(mouse) {
                                root.selectedCorner = modelData.id
                                mouse.accepted = false
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            // Top Row: Corner Name, Icon, "Double Tap Only" Badge, Switch
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Text {
                                    text: modelData.icon
                                    font.pixelSize: 18
                                }

                                Text {
                                    text: modelData.name
                                    font.bold: true
                                    font.pixelSize: 14
                                    color: "#ffffff"
                                }

                                // Double Tap Only Badge
                                Rectangle {
                                    implicitWidth: dTapText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: 10
                                    color: "#2d3748"
                                    Text {
                                        id: dTapText
                                        anchors.centerIn: parent
                                        text: "Double Tap Only"
                                        font.bold: true
                                        font.pixelSize: 10
                                        color: "#cbd5e1"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Switch {
                                    checked: cornerCard.isEnabled
                                    enabled: cornerCard.isConfigured
                                    onToggled: if (edgepadController) edgepadController.toggleCornerRule(modelData.id, checked)
                                }
                            }

                            // Middle Row: Shortcut Display Badge and Action Buttons
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                // Shortcut Preview Display Box
                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 38
                                    radius: 8
                                    color: cornerCard.isConfigured ? (cornerCard.isEnabled ? "#172b4d" : "#232b38") : "#16181f"
                                    border.color: cornerCard.isConfigured ? (cornerCard.isEnabled ? "#3daee9" : "#4a5568") : "#333846"
                                    border.width: 1

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        spacing: 8

                                        Text {
                                            text: "⌨️"
                                            font.pixelSize: 14
                                        }

                                        Text {
                                            text: cornerCard.isConfigured ? cornerCard.rule.shortcutDisplay : "No shortcut assigned (Click Record to set)"
                                            font.bold: cornerCard.isConfigured
                                            font.pixelSize: 13
                                            color: cornerCard.isConfigured ? (cornerCard.isEnabled ? "#ffffff" : "#94a3b8") : "#64748b"
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }

                                        // Linux keycodes chip
                                        Text {
                                            visible: cornerCard.isConfigured && cornerCard.rule.keys && cornerCard.rule.keys.length > 0
                                            text: "[" + (cornerCard.rule.keys ? cornerCard.rule.keys.join(" + ") : "") + "]"
                                            font.pixelSize: 10
                                            color: "#38bdf8"
                                            font.family: "Monospace"
                                            elide: Text.ElideRight
                                            Layout.maximumWidth: 160
                                        }
                                    }
                                }

                                // Record Shortcut Button
                                Button {
                                    text: cornerCard.isConfigured ? "Re-record" : "Record Shortcut"
                                    highlighted: !cornerCard.isConfigured || cornerCard.isSelected
                                    onClicked: {
                                        root.selectedCorner = modelData.id
                                        if (edgepadController) edgepadController.startShortcutRecording(modelData.id)
                                        shortcutRecordDialog.open()
                                    }
                                }

                                // Clear Button
                                Button {
                                    text: "Clear"
                                    enabled: cornerCard.isConfigured
                                    onClicked: if (edgepadController) edgepadController.clearCornerShortcut(modelData.id)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ==============================================================
    // SHORTCUT RECORDER MODAL DIALOG
    // ==============================================================
    Dialog {
        id: shortcutRecordDialog
        title: "Record Keyboard Shortcut"
        modal: true
        width: 540
        anchors.centerIn: parent

        background: Rectangle {
            color: "#1e222b"
            radius: 12
            border.color: "#3daee9"
            border.width: 2
        }

        onOpened: {
            recorderKeyHandler.forceActiveFocus()
        }

        onClosed: {
            if (edgepadController && edgepadController.isRecording) {
                edgepadController.cancelShortcutRecording()
            }
        }

        contentItem: FocusScope {
            id: recorderKeyHandler
            focus: true

            // Global Key Press & Shortcut Interception while Recording Dialog is open
            Keys.onShortcutOverride: function(event) {
                event.accepted = true
                if (edgepadController) edgepadController.processRecordedKey(event.key, event.modifiers, event.text)
            }

            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Escape && event.modifiers === Qt.NoModifier) {
                    if (edgepadController) edgepadController.cancelShortcutRecording()
                    shortcutRecordDialog.close()
                    event.accepted = true
                    return
                }
                if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && event.modifiers === Qt.NoModifier) {
                    // If we have captured a valid shortcut, Enter can confirm
                    if (edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0) {
                        edgepadController.confirmRecordedShortcut()
                        shortcutRecordDialog.close()
                        event.accepted = true
                        return
                    }
                }
                event.accepted = true
                if (edgepadController) edgepadController.processRecordedKey(event.key, event.modifiers, event.text)
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 14

            // Header info
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: 32
                    height: 32
                    radius: 8
                    color: "#3daee9"
                    Text {
                        anchors.centerIn: parent
                        text: "⌨️"
                        font.pixelSize: 18
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "Recording Shortcut for " + formatCornerName(root.selectedCorner)
                        font.bold: true
                        font.pixelSize: 15
                        color: "#ffffff"
                    }
                    Text {
                        text: "Press any key combination (e.g. Alt + Tab, Ctrl + Alt + T), click a preset, or use the builder below"
                        font.pixelSize: 11
                        color: "#94a3b8"
                    }
                }
            }

            // Live Captured Combination Box
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 80
                radius: 10
                color: "#13171f"
                border.color: (edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0) ? "#22c55e" : "#ef4444"
                border.width: 2

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 6

                    // Recording pulsating status
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 6
                        Rectangle {
                            width: 10
                            height: 10
                            radius: 5
                            color: "#ef4444"
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                NumberAnimation { from: 1.0; to: 0.2; duration: 600 }
                                NumberAnimation { from: 0.2; to: 1.0; duration: 600 }
                            }
                        }
                        Text {
                            text: (edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0) ? "Combination Captured" : "Listening for keystrokes..."
                            font.bold: true
                            font.pixelSize: 11
                            color: (edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0) ? "#4ade80" : "#f87171"
                        }
                    }

                    // Combination Text Preview
                    Text {
                        text: (edgepadController && edgepadController.recordedShortcutDisplay) ? edgepadController.recordedShortcutDisplay : ""
                        font.bold: true
                        font.pixelSize: 18
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Structured evdev keys display
                    Text {
                        visible: Boolean(edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0)
                        text: "[" + ((edgepadController && edgepadController.recordedKeys) ? edgepadController.recordedKeys.join(", ") : "") + "]"
                        font.pixelSize: 10
                        color: "#38bdf8"
                        font.family: "Monospace"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // Manual Combination Builder
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 74
                radius: 8
                color: "#161b24"
                border.color: "#283040"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    Text {
                        text: "Manual Combination Builder (Click modifiers & pick key):"
                        font.bold: true
                        font.pixelSize: 11
                        color: "#94a3b8"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Button {
                            text: "Ctrl"
                            highlighted: Boolean(edgepadController && edgepadController.hasRecordedKey("KEY_LEFTCTRL"))
                            onClicked: if (edgepadController) edgepadController.toggleRecordedModifier("KEY_LEFTCTRL")
                        }
                        Button {
                            text: "Alt"
                            highlighted: Boolean(edgepadController && edgepadController.hasRecordedKey("KEY_LEFTALT"))
                            onClicked: if (edgepadController) edgepadController.toggleRecordedModifier("KEY_LEFTALT")
                        }
                        Button {
                            text: "Shift"
                            highlighted: Boolean(edgepadController && edgepadController.hasRecordedKey("KEY_LEFTSHIFT"))
                            onClicked: if (edgepadController) edgepadController.toggleRecordedModifier("KEY_LEFTSHIFT")
                        }
                        Button {
                            text: "Super"
                            highlighted: Boolean(edgepadController && edgepadController.hasRecordedKey("KEY_LEFTMETA"))
                            onClicked: if (edgepadController) edgepadController.toggleRecordedModifier("KEY_LEFTMETA")
                        }

                        Text {
                            text: "+"
                            font.bold: true
                            color: "#718096"
                        }

                        ComboBox {
                            id: keyPickerCombo
                            Layout.fillWidth: true
                            model: [
                                "Pick Key...",
                                "Tab",
                                "F4",
                                "Space",
                                "Enter",
                                "Esc",
                                "Delete",
                                "Backspace",
                                "T",
                                "D",
                                "L",
                                "W",
                                "Q",
                                "C",
                                "V",
                                "Z",
                                "Up",
                                "Down",
                                "Left",
                                "Right",
                                "PageUp",
                                "PageDown",
                                "Home",
                                "End",
                                "F1",
                                "F2",
                                "F5",
                                "F11",
                                "F12"
                            ]
                            onActivated: function(index) {
                                if (index > 0 && edgepadController) {
                                    edgepadController.setRecordedPrimaryKey(currentText)
                                }
                            }
                        }
                    }
                }
            }

            // Quick Preset Chips
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    text: "Quick Presets:"
                    font.bold: true
                    font.pixelSize: 11
                    color: "#94a3b8"
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 6

                    PresetChip {
                        label: "🔀 Switch Window (Alt+Tab)"
                        keys: ["KEY_LEFTALT", "KEY_TAB"]
                        name: "Switch Window"
                    }
                    PresetChip {
                        label: "🗔 Overview / Tasks (Super+Tab)"
                        keys: ["KEY_LEFTMETA", "KEY_TAB"]
                        name: "Window Overview"
                    }
                    PresetChip {
                        label: "Terminal (Ctrl+Alt+T)"
                        keys: ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"]
                        name: "Terminal"
                    }
                    PresetChip {
                        label: "Lock Screen (Super+L)"
                        keys: ["KEY_LEFTMETA", "KEY_L"]
                        name: "Lock Screen"
                    }
                    PresetChip {
                        label: "Close Window (Alt+F4)"
                        keys: ["KEY_LEFTALT", "KEY_F4"]
                        name: "Close Window"
                    }
                    PresetChip {
                        label: "Show Desktop (Super+D)"
                        keys: ["KEY_LEFTMETA", "KEY_D"]
                        name: "Show Desktop"
                    }
                    PresetChip {
                        label: "System Monitor (Ctrl+Shift+Esc)"
                        keys: ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_ESC"]
                        name: "System Monitor"
                    }
                    PresetChip {
                        label: "Play / Pause"
                        keys: ["KEY_PLAYPAUSE"]
                        name: "Play / Pause"
                    }
                    PresetChip {
                        label: "Mute Audio"
                        keys: ["KEY_MUTE"]
                        name: "Mute Audio"
                    }
                }
            }

            // Dialog Action Buttons: Clear, Cancel, Confirm
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Button {
                    text: "Clear"
                    enabled: Boolean(edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0)
                    onClicked: if (edgepadController) edgepadController.clearRecordedShortcut()
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: "Cancel"
                    onClicked: {
                        if (edgepadController) edgepadController.cancelShortcutRecording()
                        shortcutRecordDialog.close()
                    }
                }

                Button {
                    text: "Confirm & Save"
                    highlighted: true
                    enabled: Boolean(edgepadController && edgepadController.recordedKeys && edgepadController.recordedKeys.length > 0)
                    onClicked: {
                        if (edgepadController) edgepadController.confirmRecordedShortcut()
                        shortcutRecordDialog.close()
                    }
                }
            }
        }
        }

        // Helper component for quick presets inside dialog
        component PresetChip: Button {
            property var keys: []
            property string name: ""
            property string label: ""
            text: label
            font.pixelSize: 11
            onClicked: {
                if (edgepadController) edgepadController.setRecordedShortcut(keys)
            }
        }
    }

    // ==============================================================
    // RESTORE CORNER DEFAULTS CONFIRMATION DIALOG
    // ==============================================================
    Dialog {
        id: resetCornerDefaultsDialog
        title: "Restore Default Corner Actions?"
        modal: true
        width: 440
        anchors.centerIn: parent

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            Text {
                text: "⚠️ Restore Corner Double-Tap Actions to Defaults?"
                font.bold: true
                font.pixelSize: 13
                color: "#e67e22"
            }

            Text {
                text: "This will reset all 4 corner double-tap actions to the recommended system shortcuts:\n\n• Top-Left: Terminal (Ctrl + Alt + T)\n• Top-Right: Lock Screen (Super + L)\n• Bottom-Left: System Monitor (Ctrl + Shift + Esc)\n• Bottom-Right: Show Desktop (Super + D)\n\nDirectional edge swipes and rotary sliders will remain unchanged."
                color: "#cbd5e1"
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Item { Layout.fillWidth: true }

                Button {
                    text: "Cancel"
                    onClicked: resetCornerDefaultsDialog.close()
                }

                Button {
                    text: "Restore Defaults"
                    highlighted: true
                    onClicked: {
                        if (edgepadController) edgepadController.resetCornerRulesToDefaults()
                        resetCornerDefaultsDialog.close()
                    }
                }
            }
        }
    }

    function formatCornerName(cornerId) {
        if (cornerId === "top-left") return "Top-Left Corner";
        if (cornerId === "top-right") return "Top-Right Corner";
        if (cornerId === "bottom-left") return "Bottom-Left Corner";
        if (cornerId === "bottom-right") return "Bottom-Right Corner";
        return cornerId;
    }
}
