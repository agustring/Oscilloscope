import QtQuick
import ".."
Rectangle { id:root; property string title:""; property string value:""; property bool selected:false; signal clicked(); radius:ScopeTheme.cornerRadius; color:selected?"#293d34":"#171d1d"; border.color:selected?ScopeTheme.accent:"#53605b"
 Column { anchors.centerIn:parent; spacing:2
  Text { anchors.horizontalCenter:parent.horizontalCenter; text:root.title; color:ScopeTheme.muted; font.pixelSize:ScopeTheme.fontSmall }
  Text { anchors.horizontalCenter:parent.horizontalCenter; text:root.value; color:ScopeTheme.text; font.pixelSize:ScopeTheme.fontNormal; font.bold:true }
 }
 MouseArea { anchors.fill:parent; cursorShape:Qt.PointingHandCursor; onClicked:root.clicked() }
}
