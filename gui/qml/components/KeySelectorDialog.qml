import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root

    property string currentKey: "KEY_BRIGHTNESSUP"
    property var knownKeysList: []
    signal keySelected(string keyName, int keyCode)

    title: "Select Linux Keyboard Key"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    width: 520
    height: 480
    anchors.centerIn: parent

    onOpened: {
        searchField.text = ""
        keyListView.model = root.knownKeysList
    }

    onAccepted: {
        if (keyListView.currentIndex >= 0 && keyListView.currentIndex < keyListView.model.length) {
            var item = keyListView.model[keyListView.currentIndex]
            root.keySelected(item.name, item.code)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // Search Field
        TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search by key name (e.g. brightness, volume, play, f1)..."
            selectByMouse: true

            onTextChanged: {
                if (text.trim() === "") {
                    keyListView.model = root.knownKeysList
                } else {
                    var q = text.toLowerCase()
                    var filtered = []
                    for (var i = 0; i < root.knownKeysList.length; i++) {
                        var k = root.knownKeysList[i]
                        if (k.name.toLowerCase().indexOf(q) !== -1 ||
                            k.friendly.toLowerCase().indexOf(q) !== -1 ||
                            k.category.toLowerCase().indexOf(q) !== -1 ||
                            k.code.toString() === q) {
                            filtered.push(k)
                        }
                    }
                    keyListView.model = filtered
                }
            }
        }

        // Selected key preview badge
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 36
            radius: 6
            color: "#2c3e50"
            border.color: "#3daee9"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Text {
                    text: "Selected Key:"
                    color: "#bdc3c7"
                    font.pixelSize: 11
                }

                Text {
                    id: selectedKeyBadge
                    text: {
                        if (keyListView.currentIndex >= 0 && keyListView.currentIndex < keyListView.model.length) {
                            var item = keyListView.model[keyListView.currentIndex]
                            return item.name + " (" + item.friendly + " • Code " + item.code + ")"
                        }
                        return root.currentKey
                    }
                    color: "#3daee9"
                    font.bold: true
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
        }

        // Key List
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ListView {
                id: keyListView
                spacing: 4
                boundsBehavior: Flickable.StopAtBounds

                delegate: Rectangle {
                    id: delegateItem
                    width: keyListView.width
                    height: 40
                    radius: 6
                    color: {
                        if (keyListView.currentIndex === index) return "#3daee9"
                        if (hoverArea.containsMouse) return "#34495e"
                        return "#242831"
                    }

                    MouseArea {
                        id: hoverArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            keyListView.currentIndex = index
                        }
                        onDoubleClicked: {
                            keyListView.currentIndex = index
                            root.accept()
                        }
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10

                        Text {
                            text: modelData.name
                            font.bold: true
                            font.pixelSize: 12
                            color: keyListView.currentIndex === index ? "#ffffff" : "#ecf0f1"
                            Layout.preferredWidth: 200
                            elide: Text.ElideRight
                        }

                        Text {
                            text: modelData.friendly
                            font.pixelSize: 11
                            color: keyListView.currentIndex === index ? "#ffffff" : "#bdc3c7"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            implicitWidth: codeText.implicitWidth + 8
                            implicitHeight: 20
                            radius: 4
                            color: keyListView.currentIndex === index ? "#2980b9" : "#1a1d24"

                            Text {
                                id: codeText
                                anchors.centerIn: parent
                                text: "#" + modelData.code
                                font.pixelSize: 10
                                color: "#95a5a6"
                            }
                        }
                    }
                }
            }
        }
    }
}
