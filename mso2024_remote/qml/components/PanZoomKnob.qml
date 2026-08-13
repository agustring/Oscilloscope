import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root
    property string panValue: ""
    property string zoomValue: ""
    property color accent: "#b9c4bd"
    property real panAngle: 0
    property real zoomAngle: 0
    signal panIncrement(bool fine)
    signal panDecrement(bool fine)
    signal zoomIncrement(bool fine)
    signal zoomDecrement(bool fine)
    signal zoomPushed()
    implicitWidth: 190
    implicitHeight: 112
    focus: true

    Text {
        anchors.top: parent.top
        anchors.left: dial.left
        anchors.right: dial.right
        horizontalAlignment: Text.AlignHCenter
        text: "PAN / ZOOM"
        color: ScopeTheme.muted
        font.pixelSize: 10
        font.bold: true
    }

    Item {
        id: dial
        width: 88
        height: 88
        x: 2
        y: 17

        Repeater {
            model: 20
            Rectangle {
                width: 2
                height: 5
                color: "#737a76"
                x: 43
                y: 0
                transform: Rotation { origin.x: 1; origin.y: 44; angle: index * 18 }
            }
        }

        Rectangle {
            anchors.centerIn: parent
            width: 80
            height: 80
            radius: 40
            color: outerMouse.pressed ? "#202426" : "#303638"
            border.color: root.accent
            border.width: 2
        }
        Rectangle {
            width: 3
            height: 11
            radius: 1
            color: root.accent
            anchors.horizontalCenter: parent.horizontalCenter
            y: 5
            transform: Rotation { origin.x: 1.5; origin.y: 39; angle: root.panAngle }
        }

        MouseArea {
            id: outerMouse
            anchors.fill: parent
            hoverEnabled: true
            property real startY
            onPressed: {
                root.forceActiveFocus()
                startY = mouseY
            }
            onPositionChanged: mouse => { if (pressed && Math.abs(mouseY - startY) > 7) {
                const up = mouseY < startY
                root.panAngle += up ? 12 : -12
                up ? root.panIncrement((mouse.modifiers & Qt.ShiftModifier) !== 0)
                   : root.panDecrement((mouse.modifiers & Qt.ShiftModifier) !== 0)
                startY = mouseY
            } }
            onWheel: {
                const up = wheel.angleDelta.y > 0
                root.panAngle += up ? 12 : -12
                up ? root.panIncrement((wheel.modifiers & Qt.ShiftModifier) !== 0)
                   : root.panDecrement((wheel.modifiers & Qt.ShiftModifier) !== 0)
            }
            ToolTip.visible: containsMouse && !innerMouse.containsMouse
            ToolTip.delay: 650
            ToolTip.text: "Pan\nWheel or drag the outer ring"
        }

        Rectangle {
            anchors.centerIn: parent
            width: 52
            height: 52
            radius: 26
            color: innerMouse.pressed ? "#202426" : "#3a4042"
            border.color: root.accent
            border.width: 2
            z: 2
        }
        Rectangle {
            width: 3
            height: 15
            radius: 1
            color: root.accent
            anchors.horizontalCenter: parent.horizontalCenter
            y: 22
            z: 3
            transform: Rotation { origin.x: 1.5; origin.y: 22; angle: root.zoomAngle }
        }
        MouseArea {
            id: innerMouse
            width: 52
            height: 52
            anchors.centerIn: parent
            hoverEnabled: true
            z: 4
            property real startY
            property bool moved: false
            onPressed: {
                root.forceActiveFocus()
                startY = mouseY
                moved = false
            }
            onPositionChanged: mouse => { if (pressed && Math.abs(mouseY - startY) > 7) {
                const up = mouseY < startY
                moved = true
                root.zoomAngle += up ? 12 : -12
                up ? root.zoomIncrement((mouse.modifiers & Qt.ShiftModifier) !== 0)
                   : root.zoomDecrement((mouse.modifiers & Qt.ShiftModifier) !== 0)
                startY = mouseY
            } }
            onClicked: if (!moved) root.zoomPushed()
            onWheel: {
                const up = wheel.angleDelta.y > 0
                root.zoomAngle += up ? 12 : -12
                up ? root.zoomIncrement((wheel.modifiers & Qt.ShiftModifier) !== 0)
                   : root.zoomDecrement((wheel.modifiers & Qt.ShiftModifier) !== 0)
            }
            ToolTip.visible: containsMouse
            ToolTip.delay: 650
            ToolTip.text: "Zoom\nWheel or drag the inner knob\nClick: toggle zoom"
        }
    }

    Column {
        anchors.left: dial.right
        anchors.leftMargin: 10
        anchors.verticalCenter: dial.verticalCenter
        spacing: 12
        Text { text: "PAN  " + root.panValue; color: root.accent; font.pixelSize: 11; font.bold: true }
        Text { text: "ZOOM  " + root.zoomValue; color: root.accent; font.pixelSize: 11; font.bold: true }
    }

    Keys.onLeftPressed: root.panDecrement((event.modifiers & Qt.ShiftModifier) !== 0)
    Keys.onRightPressed: root.panIncrement((event.modifiers & Qt.ShiftModifier) !== 0)
    Keys.onUpPressed: root.zoomIncrement((event.modifiers & Qt.ShiftModifier) !== 0)
    Keys.onDownPressed: root.zoomDecrement((event.modifiers & Qt.ShiftModifier) !== 0)
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_PageUp) {
            for (let i = 0; i < 5; ++i)
                root.zoomIncrement(false)
            event.accepted = true
        } else if (event.key === Qt.Key_PageDown) {
            for (let i = 0; i < 5; ++i)
                root.zoomDecrement(false)
            event.accepted = true
        }
    }
}
