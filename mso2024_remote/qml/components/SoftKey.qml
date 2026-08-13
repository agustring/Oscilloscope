import QtQuick
import QtQuick.Controls
import ".."
Rectangle { id:root; property string title:""; property string value:""; property bool selected:false; property bool available:true; property string reason:""; signal clicked(); radius:ScopeTheme.cornerRadius; opacity:available?1:0.42; color:selected?"#293d34":"#171d1d"; border.color:selected?ScopeTheme.accent:"#53605b"
 Column { anchors.centerIn:parent; spacing:2
  Text { anchors.horizontalCenter:parent.horizontalCenter; text:root.title; color:ScopeTheme.muted; font.pixelSize:ScopeTheme.fontSmall }
  Text { anchors.horizontalCenter:parent.horizontalCenter; text:root.value; color:ScopeTheme.text; font.pixelSize:ScopeTheme.fontNormal; font.bold:true }
 }
 MouseArea { id:mouse; anchors.fill:parent; hoverEnabled:true; cursorShape:root.available?Qt.PointingHandCursor:Qt.ArrowCursor; onClicked:if(root.available)root.clicked()
  ToolTip.visible:containsMouse&&!root.available; ToolTip.delay:500; ToolTip.text:root.reason||"Not available"
 }
}
