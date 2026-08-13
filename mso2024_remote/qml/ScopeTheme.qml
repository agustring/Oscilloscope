pragma Singleton
import QtQuick
QtObject {
 readonly property color panel: "#22272a"; readonly property color panelDark: "#15191b"
 readonly property color display: "#050909"; readonly property color text: "#e5e5d8"
 readonly property color muted: "#89928c"; readonly property color accent: "#39b86c"
 readonly property color warning: "#f3a43b"; readonly property var channels: ["#ffd21f","#29c9ee","#e94ccc","#45d06f"]
 readonly property int spacingSmall: 4; readonly property int spacingNormal: 8
 readonly property int fontSmall: 10; readonly property int fontNormal: 11; readonly property int fontLarge: 15
 readonly property int controlSmall: 34; readonly property int controlMedium: 42; readonly property int buttonWidth: 82
 readonly property int cornerRadius: 3; readonly property int transitionFast: 90
}
