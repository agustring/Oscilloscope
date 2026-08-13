import QtQuick
import ".."
import "../menus"
import "../components"
Rectangle { id:root; objectName:"scopeDisplay"; color:ScopeTheme.display; border.color:"#65706b"; border.width:2; property var traces:scope.waveforms
 function eng(v,u){var a=Math.abs(v);if(a<1e-6)return (v*1e9).toPrecision(3)+" n"+u;if(a<1e-3)return (v*1e6).toPrecision(3)+" µ"+u;if(a<1)return (v*1e3).toPrecision(3)+" m"+u;return v.toPrecision(3)+" "+u}
 Connections { target:scope; function onWaveformChanged(){wave.requestPaint()} function onStateChanged(){wave.requestPaint()} }
 Canvas { id:wave; anchors.fill:parent; anchors.rightMargin:scope.sideMenuVisible?148:0; anchors.bottomMargin:scope.menuContext?68:0
  onPaint:{var c=getContext("2d"),w=width,h=height;c.reset();c.fillStyle=ScopeTheme.display;c.fillRect(0,0,w,h);c.lineWidth=1
   for(var x=0;x<=10;x++){c.strokeStyle=x===5?"#667168":"#26302c";c.beginPath();c.moveTo(x*w/10,0);c.lineTo(x*w/10,h);c.stroke()}
   for(var y=0;y<=8;y++){c.strokeStyle=y===4?"#667168":"#26302c";c.beginPath();c.moveTo(0,y*h/8);c.lineTo(w,y*h/8);c.stroke()}
   for(var ch=0;ch<4;ch++)if(scope.channelEnabledStates[ch]){var a=root.traces[ch];if(!a||a.length<2)continue;c.strokeStyle=ScopeTheme.channels[ch];c.lineWidth=1.7;c.beginPath();var s=Math.max(scope.channelScales[ch],1e-9);for(var i=0;i<a.length;i++){var px=i*w/(a.length-1),py=h/2-a[i]*h/(8*s);i?c.lineTo(px,py):c.moveTo(px,py)}c.stroke()}
   var ref=scope.referenceWaveform;if(scope.referenceVisible&&ref&&ref.length>1){c.strokeStyle="#d7d7d0";c.lineWidth=1.2;c.setLineDash([5,3]);c.beginPath();var rs=Math.max(scope.channelScales[scope.selectedChannel-1],1e-9);for(var ri=0;ri<ref.length;ri++){var rx=ri*w/(ref.length-1),ry=h/2-ref[ri]*h/(8*rs);ri?c.lineTo(rx,ry):c.moveTo(rx,ry)}c.stroke();c.setLineDash([])}
  }
  MouseArea { anchors.fill:parent; acceptedButtons:Qt.LeftButton|Qt.RightButton; property real lastY; property real lastX
   onPressed:{lastY=mouseY;lastX=mouseX;if(mouse.button===Qt.LeftButton)contextMenu.visible=false;else if(mouse.button===Qt.RightButton){contextMenu.x=Math.min(mouseX,wave.width-contextMenu.width);contextMenu.y=Math.min(mouseY,wave.height-contextMenu.height);contextMenu.visible=true;scope.openMenu("channel")}}
   onPositionChanged:mouse=>{if(pressedButtons&Qt.LeftButton){var dx=mouseX-lastX,dy=mouseY-lastY;if(Math.abs(dx)>Math.abs(dy)&&Math.abs(dx)>5){scope.adjustHorizontalPosition(-dx*10/width);lastX=mouseX;lastY=mouseY}else if(Math.abs(dy)>8){scope.adjustChannelPosition(scope.selectedChannel,dy<0?1:-1,(mouse.modifiers&Qt.ShiftModifier)!==0);lastX=mouseX;lastY=mouseY}}}
   onWheel:(wheel.modifiers&Qt.ControlModifier)?scope.adjustTimeScale(wheel.angleDelta.y>0?1:-1):scope.adjustChannelScale(scope.selectedChannel,wheel.angleDelta.y>0?1:-1)
   onDoubleClicked:scope.resetView()
  }
 }
 Rectangle { id:contextMenu; objectName:"waveformContextMenu"; visible:false; width:180;height:contextColumn.implicitHeight+12;color:"#151c1c";border.color:ScopeTheme.channels[scope.selectedChannel-1];z:15
  Column { id:contextColumn; anchors.fill:parent;anchors.margins:6;spacing:4
   Text { width:parent.width;height:24;text:"CH"+scope.selectedChannel; color:ScopeTheme.channels[scope.selectedChannel-1];font.bold:true;horizontalAlignment:Text.AlignHCenter }
   ScopeButton { width:parent.width;text:scope.channelEnabledStates[scope.selectedChannel-1]?"DISABLE CHANNEL":"ENABLE CHANNEL";onClicked:{scope.pressChannel(scope.selectedChannel);contextMenu.visible=false} }
   ScopeButton { width:parent.width;text:"COUPLING";onClicked:{scope.openMenu("channel");scope.selectMenuItem(0);contextMenu.visible=false} }
   ScopeButton { width:parent.width;text:"PROBE ATTENUATION";onClicked:{scope.openMenu("channel");scope.selectMenuItem(2);contextMenu.visible=false} }
   ScopeButton { width:parent.width;text:"INVERT";onClicked:{scope.openMenu("channel");scope.selectMenuItem(3);contextMenu.visible=false} }
   ScopeButton { width:parent.width;text:"ADD MEASUREMENT";onClicked:{scope.openMenu("measure");scope.selectMenuItem(0);contextMenu.visible=false} }
  }
 }
 Connections { target:scope; function onMenuChanged(){if(scope.menuContext==="")contextMenu.visible=false} }
 Text { anchors.left:parent.left; anchors.top:parent.top; anchors.margins:8; text:scope.running?"RUN":"STOP"; color:scope.running?ScopeTheme.accent:ScopeTheme.warning; font.bold:true }
 Text { anchors.horizontalCenter:parent.horizontalCenter; anchors.top:parent.top; anchors.topMargin:7; text:"T  ▼  "+scope.triggerLevel.toFixed(2)+" V"; color:ScopeTheme.warning; font.pixelSize:11 }
 Rectangle { id:zoomOverview; objectName:"zoomOverview"; visible:scope.zoomEnabled; x:wave.width*0.2; width:wave.width*0.6; y:25; height:18; color:"#18221f"; border.color:"#78857d"
  Rectangle { width:Math.max(8,parent.width*Math.min(1,scope.zoomScale/Math.max(scope.timeScale,1e-9))); height:parent.height-4; y:2; x:Math.max(0,Math.min(parent.width-width,(scope.zoomPosition/100)*parent.width-width/2)); color:"#596b61"; opacity:0.75 }
  Text { anchors.centerIn:parent; text:"ZOOM OVERVIEW"; color:"#c9d0ca"; font.pixelSize:8 }
  MouseArea { anchors.fill:parent; cursorShape:Qt.SizeHorCursor
   onPressed:scope.setZoomPosition(mouseX/width*100)
   onPositionChanged:if(pressed)scope.setZoomPosition(mouseX/width*100)
   onWheel:scope.adjustZoom(wheel.angleDelta.y>0?1:-1,(wheel.modifiers&Qt.ShiftModifier)!==0)
  }
 }
 Repeater { model:[scope.cursorX1,scope.cursorX2]
  Item { visible:scope.cursorFunction==="VBARS"||scope.cursorFunction==="SCREEN"||scope.cursorFunction==="WAVEFORM"; width:11; height:wave.height; y:0; x:Math.max(0,Math.min(wave.width-11,wave.width*(0.5+modelData/(10*scope.timeScale))-5))
   Rectangle { width:1; height:parent.height; anchors.horizontalCenter:parent.horizontalCenter; color:ScopeTheme.warning }
   Text { text:"X"+(index+1); color:ScopeTheme.warning; font.pixelSize:9; anchors.top:parent.top; anchors.left:parent.horizontalCenter }
   MouseArea { anchors.fill:parent; cursorShape:Qt.SizeHorCursor; onPositionChanged:if(pressed){var p=mapToItem(wave,mouseX,mouseY);scope.setCursorPosition("VBARS",index+1,(p.x/wave.width-0.5)*10*scope.timeScale)} }
  }
 }
 Repeater { model:[scope.cursorY1,scope.cursorY2]
  Item { visible:scope.cursorFunction==="HBARS"||scope.cursorFunction==="SCREEN"; height:11; width:wave.width; x:0; y:Math.max(0,Math.min(wave.height-11,wave.height*(0.5-modelData/(8*scope.channelScales[scope.selectedChannel-1]))-5))
   Rectangle { height:1; width:parent.width; anchors.verticalCenter:parent.verticalCenter; color:ScopeTheme.warning }
   Text { text:"Y"+(index+1); color:ScopeTheme.warning; font.pixelSize:9; anchors.left:parent.left; anchors.bottom:parent.verticalCenter }
   MouseArea { anchors.fill:parent; cursorShape:Qt.SizeVerCursor; onPositionChanged:if(pressed){var p=mapToItem(wave,mouseX,mouseY);scope.setCursorPosition("HBARS",index+1,(0.5-p.y/wave.height)*8*scope.channelScales[scope.selectedChannel-1])} }
  }
 }
 Repeater { model:4
  Item { visible:scope.channelEnabledStates[index]; width:18;height:18;x:0;y:Math.max(12,Math.min(wave.height-20,wave.height/2-scope.channelPositions[index]*wave.height/8-9))
   Rectangle { anchors.fill:parent; color:ScopeTheme.channels[index]; border.color:"#050909"; Text { anchors.centerIn:parent; text:index+1; color:"#101313"; font.pixelSize:10; font.bold:true } }
   MouseArea { anchors.fill:parent; cursorShape:Qt.SizeVerCursor; onClicked:scope.selectChannel(index+1); onDoubleClicked:scope.setChannelPosition(index+1,0); onPositionChanged:if(pressed){var p=mapToItem(wave,mouseX,mouseY);scope.setChannelPosition(index+1,(wave.height/2-p.y)*8/wave.height)} }
 }
}
 Rectangle { visible:scope.cursorFunction!=="OFF"; width:190; height:(scope.cursorFunction==="SCREEN"||scope.cursorFunction==="WAVEFORM")?55:36; anchors.right:side.left; anchors.bottom:status.top; anchors.margins:5; color:"#111817"; border.color:ScopeTheme.warning
  property real dt:Math.abs(scope.cursorX2-scope.cursorX1); property real dv:Math.abs(scope.cursorY2-scope.cursorY1)
  Text { anchors.fill:parent; anchors.margins:5; color:ScopeTheme.warning; font.pixelSize:10
   text:(scope.cursorFunction==="VBARS"||scope.cursorFunction==="WAVEFORM"||scope.cursorFunction==="SCREEN"?("Δt  "+root.eng(parent.dt,"s")+"    1/Δt  "+(parent.dt>0?root.eng(1/parent.dt,"Hz"):"—")):"")+((scope.cursorFunction==="SCREEN"||scope.cursorFunction==="WAVEFORM")?"\n":"")+(scope.cursorFunction==="WAVEFORM"?("ΔV  "+root.eng(scope.cursorWaveformDelta,"V")):(scope.cursorFunction==="HBARS"||scope.cursorFunction==="SCREEN"?("ΔV  "+root.eng(parent.dv,"V")):""))
  }
 }
Item { objectName:"triggerMarker"; width:18;height:18;x:wave.width-18;y:Math.max(12,Math.min(wave.height-20,wave.height/2-scope.triggerLevel*wave.height/(8*scope.channelScales[scope.selectedChannel-1])-9))
  Rectangle { anchors.fill:parent; color:ScopeTheme.warning; Text { anchors.centerIn:parent;text:"T";color:"#18130c";font.pixelSize:10;font.bold:true } }
  MouseArea { anchors.fill:parent; cursorShape:Qt.SizeVerCursor; onDoubleClicked:scope.centerTrigger(); onPositionChanged:if(pressed){var p=mapToItem(wave,mouseX,mouseY);scope.setTriggerLevel((wave.height/2-p.y)*8*scope.channelScales[scope.selectedChannel-1]/wave.height)} }
 }
 Row { anchors.left:parent.left; anchors.bottom:menu.top; anchors.margins:5; spacing:10
  Repeater { model:4; Text { visible:scope.channelEnabledStates[index]; text:"CH"+(index+1)+"  "+root.eng(scope.channelScales[index],"V/div"); color:ScopeTheme.channels[index]; font.pixelSize:11; font.bold:true } }
 }
 Column { anchors.right:side.left; anchors.top:parent.top; anchors.margins:5; spacing:3
  Repeater { model:scope.measurementReadouts
   Rectangle { width:190; height:34; color:"#101716"; border.color:ScopeTheme.channels[Math.max(0,parseInt(modelData.source.substring(2))-1)]
    Text { anchors.fill:parent; anchors.margins:5; text:"M"+modelData.slot+"  "+modelData.type+"  "+modelData.source+"  "+modelData.value+" "+modelData.unit; color:ScopeTheme.text; font.pixelSize:10; verticalAlignment:Text.AlignVCenter }
   }
 }
}
Text { id:status; anchors.right:side.left; anchors.bottom:menu.top; anchors.margins:5; text:"H  "+root.eng(scope.timeScale,"s/div")+"   "+(scope.delayMode?("Delay "+root.eng(scope.horizontalDelay,"s")):("Pos "+scope.horizontalPosition.toFixed(1)+" %"))+"   CH"+scope.selectedChannel+"  "+root.eng(scope.channelScales[scope.selectedChannel-1],"V/div")+"  Pos "+scope.channelPositions[scope.selectedChannel-1].toFixed(1)+" div   Trig "+scope.triggerStatus+"  "+scope.triggerSource+"  "+scope.triggerLevel.toFixed(2)+" V   "+scope.waveformPointCount+" pts"; color:"#9fc4ca"; font.pixelSize:10; font.bold:true }
 SideBezelMenu { id:side; visible:scope.sideMenuVisible; anchors.right:parent.right; anchors.top:parent.top; anchors.bottom:menu.top; width:visible?145:0; title:scope.sideMenuTitle; entries:scope.sideMenu }
 BottomBezelMenu { id:menu; visible:scope.menuContext!==""; anchors.left:parent.left; anchors.right:parent.right; anchors.bottom:parent.bottom; height:visible?63:0; context:scope.menuContext; selection:scope.menuSelection }
}
