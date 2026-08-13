import QtQuick
import QtQuick.Controls
import ".."
Item {
 id: root; property string label: ""; property string valueText: ""; property color accent: ScopeTheme.text; property bool pushEnabled: false
 property real angle: 25; signal increment(bool fine); signal decrement(bool fine); signal pushed(); implicitWidth: 90; implicitHeight: 108; focus: true
 Text { anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter; text: root.label; color: ScopeTheme.muted; font.pixelSize: 10; font.bold: true }
 Item { id: dial; width: 62; height: 62; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: 16
  Repeater { model: 17; Rectangle { width: 2; height: 5; color: "#737a76"; x:30; y:0; transform: Rotation { origin.x:1; origin.y:31; angle:-120+index*15 } } }
  Rectangle { anchors.centerIn: parent; width:54; height:54; radius:27; color: mouse.pressed?"#202426":"#353b3d"; border.color:root.accent; border.width:2 }
  Rectangle { width:3; height:18; radius:1; color:root.accent; anchors.horizontalCenter:parent.horizontalCenter; y:7; transform: Rotation { origin.x:1.5; origin.y:24; angle:root.angle } }
  MouseArea { id:mouse; anchors.fill:parent; hoverEnabled:true; property real startY; property bool moved:false
   onPressed:{root.forceActiveFocus();startY=mouseY;moved=false}
   onPositionChanged: mouse=>{if(pressed&&Math.abs(mouseY-startY)>7){var up=mouseY<startY;moved=true;root.angle+=up?12:-12;up?root.increment((mouse.modifiers&Qt.ShiftModifier)!==0):root.decrement((mouse.modifiers&Qt.ShiftModifier)!==0);startY=mouseY}}
   onClicked:if(root.pushEnabled&&!moved)root.pushed()
   onWheel:{root.angle+=wheel.angleDelta.y>0?12:-12;wheel.angleDelta.y>0?root.increment((wheel.modifiers&Qt.ShiftModifier)!==0):root.decrement((wheel.modifiers&Qt.ShiftModifier)!==0)}
  }
  ToolTip.visible:mouse.containsMouse; ToolTip.delay:650; ToolTip.text:root.label+"\nWheel or drag vertically: adjust\nUp/Down: one detent · Page Up/Down: five\nShift: fine adjustment"+(root.pushEnabled?"\nClick: push encoder":"")
 }
 Text { anchors.top:parent.top; anchors.topMargin:82; anchors.horizontalCenter:parent.horizontalCenter; text:root.valueText; color:root.accent; font.pixelSize:11; font.bold:true }
 Keys.onUpPressed:increment((event.modifiers&Qt.ShiftModifier)!==0); Keys.onDownPressed:decrement((event.modifiers&Qt.ShiftModifier)!==0)
 Keys.onPressed:function(event){
  if(event.key===Qt.Key_PageUp){root.angle+=60;for(var i=0;i<5;i++)root.increment(false);event.accepted=true}
  else if(event.key===Qt.Key_PageDown){root.angle-=60;for(var j=0;j<5;j++)root.decrement(false);event.accepted=true}
 }
}
