import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Rectangle {
 id:root; color:"#101616"; border.color:"#59635f"; radius:2
 property string title:""; property var entries:[]
 Text { id:heading; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:5; height:24; text:root.title; color:ScopeTheme.muted; font.pixelSize:10; font.bold:true; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter }
 Column {
  id:measurementSources; visible:scope.menuContext==="measure"&&scope.menuSelection===0
  anchors.left:parent.left; anchors.right:parent.right; anchors.top:heading.bottom; anchors.margins:5; spacing:3
  Text { width:parent.width; text:"SOURCE 1  ·  "+scope.measurementSource; color:ScopeTheme.text; font.pixelSize:9; font.bold:true }
  Row { spacing:3
   Repeater { model:4
    ScopeButton { objectName:"measurementSource1Channel"+(index+1); width:29; height:27; text:"CH"+(index+1); accent:ScopeTheme.channels[index]; active:scope.measurementSource==="CH"+(index+1); onClicked:scope.setMeasurementSource(1,index+1) }
   }
  }
  Text { visible:scope.measurementUsesTwoSources; width:parent.width; text:"SOURCE 2  ·  "+scope.measurementSource2; color:ScopeTheme.text; font.pixelSize:9; font.bold:true }
  Row { visible:scope.measurementUsesTwoSources; spacing:3
   Repeater { model:4
    ScopeButton { objectName:"measurementSource2Channel"+(index+1); width:29; height:27; text:"CH"+(index+1); accent:ScopeTheme.channels[index]; active:scope.measurementSource2==="CH"+(index+1); onClicked:scope.setMeasurementSource(2,index+1) }
   }
  }
 }
 Flickable {
  id:listView; anchors.left:parent.left; anchors.right:parent.right; anchors.top:measurementSources.visible?measurementSources.bottom:heading.bottom; anchors.bottom:parent.bottom; anchors.margins:5; clip:true
  contentHeight:entryColumn.height; boundsBehavior:Flickable.StopAtBounds
  ScrollBar.vertical: ScrollBar { policy:root.entries.length>8?ScrollBar.AsNeeded:ScrollBar.AlwaysOff }
  Column {
   id:entryColumn; width:listView.width-(root.entries.length>8?10:0); spacing:4
   Repeater {
    model:root.entries
    ScopeButton { objectName:"sideSoftKey"+index; width:entryColumn.width; height:38; text:modelData.label; active:modelData.selected; available:modelData.enabled; opacity:available?1:0.42; help:modelData.reason; onClicked:scope.selectSideItem(index) }
   }
  }
 }
}
