import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Rectangle {
 id:root; color:"#101616"; border.color:"#59635f"; radius:2
 property string title:""; property var entries:[]
 Text { id:heading; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:5; height:24; text:root.title; color:ScopeTheme.muted; font.pixelSize:10; font.bold:true; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter }
 Flickable {
  id:listView; anchors.left:parent.left; anchors.right:parent.right; anchors.top:heading.bottom; anchors.bottom:parent.bottom; anchors.margins:5; clip:true
  contentHeight:entryColumn.height; boundsBehavior:Flickable.StopAtBounds
  ScrollBar.vertical: ScrollBar { policy:root.entries.length>8?ScrollBar.AsNeeded:ScrollBar.AlwaysOff }
  Column {
   id:entryColumn; width:listView.width-(root.entries.length>8?10:0); spacing:4
   Repeater {
    model:root.entries
    ScopeButton { width:entryColumn.width; height:38; text:modelData.label; active:modelData.selected; enabled:modelData.enabled; opacity:enabled?1:0.42; help:modelData.reason; onClicked:scope.selectSideItem(index) }
   }
  }
 }
}
