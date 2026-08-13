import QtQuick
import ".."
import "../components"
Row { id:root; property string context:""; property int selection:0; spacing:3
 Repeater { model:scope.bottomMenu; SoftKey { width:(root.width-Math.max(0,scope.bottomMenu.length-1)*3)/Math.max(1,scope.bottomMenu.length); height:root.height; title:modelData.title; value:modelData.value; selected:index===root.selection; onClicked:scope.pressMenuItem(index) } }
}
