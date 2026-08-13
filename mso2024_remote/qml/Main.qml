import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "."
import "components"
import "scope"

ApplicationWindow {
 id:window; visible:true; width:1500; height:920; minimumWidth:1080; minimumHeight:680
 title:"Tektronix MSO2024 Remote"; color:ScopeTheme.panelDark
 property bool debugVisible:false; property bool enhancedMode:false
 property bool compactLayout:height<730
 property bool frontPanelMode:!enhancedMode&&!compactLayout
 function eng(v,u){if(v<1e-6)return (v*1e9).toPrecision(3)+" n"+u;if(v<1e-3)return (v*1e6).toPrecision(3)+" µ"+u;if(v<1)return (v*1e3).toPrecision(3)+" m"+u;return v.toPrecision(3)+" "+u}
 Shortcut { sequence:"F11"; onActivated:window.visibility===Window.FullScreen?window.showNormal():window.showFullScreen() }
 Shortcut { sequence:"Space"; enabled:scope.connected; onActivated:scope.toggleRun() }
 Shortcut { sequence:"S"; enabled:scope.connected; onActivated:scope.single() }
 Shortcut { sequence:"A"; enabled:scope.connected; onActivated:scope.autoset() }
 Shortcut { sequence:"T"; enabled:scope.connected; onActivated:scope.openMenu("trigger") }
 Shortcut { sequence:"M"; enabled:scope.connected; onActivated:scope.openMenu("measure") }
 Shortcut { sequence:"C"; enabled:scope.connected; onActivated:scope.openMenu("cursor") }
 Shortcut { sequence:"Escape"; onActivated:scope.closeMenu() }
 Shortcut { sequence:"Ctrl+Shift+D"; onActivated:debugVisible=!debugVisible }
 Shortcut { sequence:"1"; enabled:scope.connected; onActivated:scope.pressChannel(1) }
 Shortcut { sequence:"2"; enabled:scope.connected; onActivated:scope.pressChannel(2) }
 Shortcut { sequence:"3"; enabled:scope.connected; onActivated:scope.pressChannel(3) }
 Shortcut { sequence:"4"; enabled:scope.connected; onActivated:scope.pressChannel(4) }
 Connections { target:scope; function onFileDialogRequested(kind){if(kind==="screen-save")screenSaveDialog.open();else if(kind==="waveform-save")waveformSaveDialog.open();else if(kind==="waveform-load")waveformLoadDialog.open()} }
 FileDialog { id:screenSaveDialog; title:"Save remote panel image"; fileMode:FileDialog.SaveFile; nameFilters:["PNG images (*.png)"]; defaultSuffix:"png"
  onAccepted:scope.savePanelImage(selectedFile.toString(),window)
 }
 FileDialog { id:waveformSaveDialog; title:"Export selected waveform"; fileMode:FileDialog.SaveFile; nameFilters:["CSV waveforms (*.csv)"]; defaultSuffix:"csv"; onAccepted:scope.exportWaveform(selectedFile.toString()) }
 FileDialog { id:waveformLoadDialog; title:"Load CSV as local reference"; fileMode:FileDialog.OpenFile; nameFilters:["CSV waveforms (*.csv)"]; onAccepted:scope.loadReferenceWaveform(selectedFile.toString()) }

 ColumnLayout { anchors.fill:parent; anchors.margins:10; spacing:8
  Rectangle { Layout.fillWidth:true; Layout.preferredHeight:42; color:"#1c2123"; border.color:"#3e4749"
   RowLayout { anchors.fill:parent; anchors.margins:10
    Text { text:"TEKTRONIX"; color:"#56b9df"; font.pixelSize:17; font.bold:true }
    Text { text:"MSO2024 REMOTE"; color:ScopeTheme.text; font.pixelSize:15; font.bold:true }
    ScopeButton { objectName:"modeToggleButton"; text:window.compactLayout?"COMPACT":(window.enhancedMode?"ENHANCED":"FRONT PANEL"); active:!window.frontPanelMode; enabled:!window.compactLayout; onClicked:window.enhancedMode=!window.enhancedMode; help:window.compactLayout?"Waveform-focused layout is automatic below 730 px high":"Toggle faithful front-panel and waveform-focused PC modes" }
    Item { Layout.fillWidth:true }
    Rectangle { width:9;height:9;radius:5;color:scope.connected?ScopeTheme.accent:"#c84f47" }
    Text { text:scope.simulation?"SIMULATION":(scope.connected?"CONNECTED":"DISCONNECTED");color:ScopeTheme.text;font.pixelSize:11;font.bold:true }
   }
  }
  RowLayout { Layout.fillWidth:true; Layout.fillHeight:true; spacing:8
   ColumnLayout { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumWidth:700; spacing:8
    ScopeDisplay { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:390 }
    Rectangle { visible:!window.frontPanelMode; Layout.fillWidth:true; Layout.preferredHeight:46; color:ScopeTheme.panel; border.color:"#485052"
     RowLayout { anchors.fill:parent; anchors.margins:5
      Repeater { model:4; ScopeButton { text:"CH"+(index+1); active:scope.channelEnabledStates[index]; accent:ScopeTheme.channels[index]; onClicked:scope.pressChannel(index+1) } }
      Item { Layout.fillWidth:true }
      Text { text:"H  "+window.eng(scope.timeScale,"s/div"); color:"#83bfcf"; font.bold:true }
      ScopeButton { text:"TRIGGER"; active:scope.menuContext==="trigger"; onClicked:scope.openMenu("trigger") }
      ScopeButton { text:"MEASURE"; active:scope.menuContext==="measure"; onClicked:scope.openMenu("measure") }
      ScopeButton { text:scope.running?"RUN":"STOP"; active:scope.running; onClicked:scope.toggleRun() }
     }
    }
    Rectangle { visible:window.frontPanelMode; Layout.fillWidth:true; Layout.preferredHeight:260; color:ScopeTheme.panel; border.color:"#485052"
     RowLayout { anchors.fill:parent; anchors.margins:8; spacing:5
      Repeater { model:4
       Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; color:"#1a1e20"; border.color:scope.selectedChannel===index+1?ScopeTheme.channels[index]:"#464d50"
        Column { anchors.centerIn:parent; spacing:3
         ScopeButton { objectName:"frontChannelButton"+(index+1); text:"CH"+(index+1); active:scope.channelEnabledStates[index]; accent:ScopeTheme.channels[index]; onClicked:scope.pressChannel(index+1) }
         RotaryKnob { objectName:"channelPositionKnob"+(index+1); label:"POSITION"; valueText:scope.channelPositions[index].toFixed(1)+" div"; accent:ScopeTheme.channels[index]; onIncrement:f=>scope.adjustChannelPosition(index+1,1,f); onDecrement:f=>scope.adjustChannelPosition(index+1,-1,f) }
         RotaryKnob { objectName:"channelScaleKnob"+(index+1); label:"SCALE"; valueText:window.eng(scope.channelScales[index],"V/div"); accent:ScopeTheme.channels[index]; onIncrement:scope.adjustChannelScale(index+1,1); onDecrement:scope.adjustChannelScale(index+1,-1) }
        }
       }
      }
     }
    }
   }
   Rectangle { id:hardwarePanel; visible:window.frontPanelMode; Layout.preferredWidth:visible?330:0; Layout.fillHeight:true; color:ScopeTheme.panel; border.color:"#485052"
    Flickable { anchors.fill:parent; contentHeight:panel.height; clip:true; flickableDirection:Flickable.VerticalFlick; boundsBehavior:Flickable.StopAtBounds
     ScrollBar.vertical:Basic.ScrollBar { id:hardwareScroll; policy:parent.contentHeight>parent.height?Basic.ScrollBar.AlwaysOn:Basic.ScrollBar.AlwaysOff; width:8
      background:Rectangle { color:"#171c1e"; border.color:"#30383a" }
      contentItem:Rectangle { implicitWidth:6; radius:3; color:hardwareScroll.pressed?ScopeTheme.accent:"#697276"; opacity:hardwareScroll.active?1:0.7 }
     }
     Column { id:panel; width:parent.width; padding:10; spacing:8
      Text { text:"MULTIPURPOSE"; color:ScopeTheme.text; font.bold:true; font.pixelSize:12 }
      Row { spacing:10
       RotaryKnob { objectName:"multipurposeAKnob"; label:"A · "+scope.knobALabel; valueText:scope.knobAValue; accent:"#d6d8c8"; pushEnabled:true; onIncrement:scope.adjustMultipurpose("A",1); onDecrement:scope.adjustMultipurpose("A",-1); onPushed:scope.applyMultipurpose() }
       RotaryKnob { objectName:"multipurposeBKnob"; label:"B · "+scope.knobBLabel; valueText:scope.knobBValue; accent:"#d6d8c8"; onIncrement:scope.adjustMultipurpose("B",1); onDecrement:scope.adjustMultipurpose("B",-1) }
      }
      Rectangle { width:parent.width-20;height:1;color:"#51585a" }
      Text { text:"HORIZONTAL"; color:ScopeTheme.text; font.bold:true; font.pixelSize:12 }
      Row { spacing:10
       RotaryKnob { objectName:"horizontalPositionKnob"; label:scope.delayMode?"DELAY":"POSITION"; valueText:scope.delayMode?window.eng(scope.horizontalDelay,"s"):scope.horizontalPosition.toFixed(1)+" %"; onIncrement:f=>scope.adjustHorizontalPosition(f?0.02:0.1); onDecrement:f=>scope.adjustHorizontalPosition(f?-0.02:-0.1) }
       RotaryKnob { objectName:"horizontalScaleKnob"; label:"SCALE"; valueText:window.eng(scope.timeScale,"s/div"); accent:"#83bfcf"; onIncrement:scope.adjustTimeScale(1); onDecrement:scope.adjustTimeScale(-1) }
      }
      Row { spacing:6
       ScopeButton { objectName:"runStopButton"; text:scope.running?"RUN / STOP":"STOPPED"; active:scope.running; onClicked:scope.toggleRun() }
       ScopeButton { objectName:"singleButton"; text:"SINGLE"; onClicked:scope.single() }
       ScopeButton { objectName:"autosetButton"; text:"AUTOSET"; onClicked:scope.autoset() }
      }
      Rectangle { width:parent.width-20;height:1;color:"#51585a" }
      Text { text:"TRIGGER"; color:ScopeTheme.text; font.bold:true; font.pixelSize:12 }
      Row { spacing:8
       ScopeButton { text:"MENU"; active:scope.menuContext==="trigger"; onClicked:scope.openMenu("trigger") }
       RotaryKnob { objectName:"triggerLevelKnob"; label:"LEVEL"; valueText:scope.triggerLevel.toFixed(2)+" V"; accent:ScopeTheme.warning; pushEnabled:true; onIncrement:f=>scope.adjustTriggerLevel(1,f); onDecrement:f=>scope.adjustTriggerLevel(-1,f); onPushed:scope.centerTrigger() }
       ScopeButton { text:"FORCE\nTRIG"; onClicked:scope.forceTrigger() }
      }
      Text { text:"FUNCTIONS"; color:ScopeTheme.text; font.bold:true; font.pixelSize:12 }
      Grid { columns:3; spacing:6
       ScopeButton { objectName:"acquireButton"; text:"ACQUIRE"; active:scope.menuContext==="acquire"; onClicked:scope.openMenu("acquire") }
       ScopeButton { objectName:"measureButton"; text:"MEASURE"; active:scope.menuContext==="measure"; onClicked:scope.openMenu("measure") }
       ScopeButton { text:"SEARCH"; active:scope.menuContext==="search"; onClicked:scope.openMenu("search") }
       ScopeButton { text:"TEST"; active:scope.menuContext==="test"; help:"Application-specific tests; available contents depend on installed modules"; onClicked:scope.openTestMenu() }
       ScopeButton { text:"CURSORS"; active:scope.menuContext==="cursor"; onClicked:scope.openMenu("cursor") }
       ScopeButton { text:"UTILITY"; active:scope.menuContext==="utility"; onClicked:scope.openMenu("utility") }
       ScopeButton { text:"SAVE/RECALL"; active:scope.menuContext==="save"; onClicked:scope.openMenu("save") }
       ScopeButton { text:"B1"; active:scope.menuContext==="bus"; onClicked:scope.openBusMenu(1) }
       ScopeButton { text:"B2"; active:scope.menuContext==="bus"; onClicked:scope.openBusMenu(2) }
       ScopeButton { text:"MATH"; active:scope.menuContext==="math"; onClicked:scope.openMenu("math") }
       ScopeButton { text:"REF"; active:scope.menuContext==="reference"; onClicked:scope.openMenu("reference") }
       ScopeButton { text:"DEFAULT SETUP"; onClicked:scope.defaultSetup() }
       ScopeButton { text:"MENU OFF"; onClicked:scope.closeMenu() }
      }
      Text { text:"WAVE INSPECTOR"; color:ScopeTheme.text; font.bold:true; font.pixelSize:12 }
      PanZoomKnob { objectName:"waveInspectorKnob"; panValue:scope.zoomPosition.toFixed(0)+" %"; zoomValue:window.eng(scope.zoomScale,"s"); onPanIncrement:f=>scope.panZoom(1,f); onPanDecrement:f=>scope.panZoom(-1,f); onZoomIncrement:f=>scope.adjustZoom(1,f); onZoomDecrement:f=>scope.adjustZoom(-1,f); onZoomPushed:scope.toggleZoom() }
      Row { spacing:7
       ScopeButton { text:"◀ PREV"; onClicked:scope.moveMark("previous") }
       ScopeButton { text:scope.inspectorPlaying?"PAUSE":"PLAY"; active:scope.inspectorPlaying; onClicked:scope.toggleInspectorPlayback() }
       ScopeButton { text:"NEXT ▶"; onClicked:scope.moveMark("next") }
      }
      ScopeButton { text:"SET / CLEAR MARK"; onClicked:scope.toggleMark() }
     }
    }
   }
  }
 }
 Item { id:connectionOverlay; objectName:"connectionOverlay"; visible:!scope.connected; anchors.fill:parent; z:20
  Rectangle { anchors.fill:parent; color:"#b0050909" }
  MouseArea { anchors.fill:parent }
  Rectangle { anchors.centerIn:parent; width:520;height:Math.min(430,210+scope.resources.length*48);color:"#202628";border.color:"#697276"
   Column { anchors.fill:parent; anchors.margins:22; spacing:10
    Text { anchors.horizontalCenter:parent.horizontalCenter;text:"TEKTRONIX MSO2024 REMOTE";color:ScopeTheme.text;font.pixelSize:18;font.bold:true }
    Text { anchors.horizontalCenter:parent.horizontalCenter;text:scope.searching?"Searching for instruments…":"INSTRUMENT DISCONNECTED · displayed data is stale";color:scope.searching?ScopeTheme.muted:ScopeTheme.warning }
    Repeater { model:scope.resources
     ScopeButton { width:parent.width; height:42; text:(modelData.is_mso2024?"MSO2024  ":"OTHER  ")+modelData.resource; active:modelData.is_mso2024; help:modelData.identity||modelData.error; onClicked:if(modelData.is_mso2024)scope.connectResource(modelData.resource) }
    }
    Item { width:1;height:4 }
    Row { anchors.horizontalCenter:parent.horizontalCenter; spacing:10
     ScopeButton { text:"SCAN AGAIN"; onClicked:scope.reconnect() }
     ScopeButton { text:"SIMULATION"; accent:ScopeTheme.warning; onClicked:scope.enableSimulation() }
    }
   }
  }
 }
 Rectangle { visible:debugVisible; anchors.right:parent.right;anchors.top:parent.top;anchors.margins:12;width:410;height:285;color:"#111819";border.color:ScopeTheme.accent;z:30
  Text { anchors.fill:parent;anchors.margins:12;text:"DEVELOPER DIAGNOSTICS\n\n"+scope.diagnosticsText;color:ScopeTheme.text;font.family:"Consolas";font.pixelSize:11 }
 }
 onClosing:scope.close()
}
