from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PySide6 import QtCore, QtGui, QtQml

from .qml_bridge import ScopeController


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation", action="store_true", help="run without an oscilloscope")
    args = parser.parse_args()
    app = QtGui.QGuiApplication(sys.argv[:1])
    app.setApplicationName("Tektronix MSO2024 Remote")
    engine = QtQml.QQmlApplicationEngine()
    controller = ScopeController(simulation=args.simulation)
    engine.rootContext().setContextProperty("scope", controller)
    qml_dir = Path(__file__).with_name("qml")
    engine.addImportPath(str(qml_dir))
    engine.load(QtCore.QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
    if not engine.rootObjects():
        controller.close()
        return 1
    result = app.exec()
    controller.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
