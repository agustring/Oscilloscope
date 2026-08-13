import QtQuick
import QtQuick.Controls
import ".."
Rectangle {
 id: root; property string text: ""; property string help:""; property bool active: false; property color accent: ScopeTheme.accent; signal clicked()
 implicitWidth: ScopeTheme.buttonWidth; implicitHeight: ScopeTheme.controlSmall; radius: ScopeTheme.cornerRadius; color: mouse.pressed?"#111416":(active?Qt.darker(accent,2.8):"#303638")
 border.color: active?accent:"#596064"; border.width: active?2:1
 Text { anchors.centerIn: parent; text: root.text; color: root.active?root.accent:ScopeTheme.text; font.pixelSize: ScopeTheme.fontNormal; font.bold: true }
 MouseArea { id: mouse; anchors.fill: parent; hoverEnabled:true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
 ToolTip.visible:mouse.containsMouse; ToolTip.delay:650; ToolTip.text:help||text
}
