from __future__ import annotations

import sys

from PySide6 import QtWidgets
import pyqtgraph as pg

from .gui.main_window import MainWindow


STYLE = """
QWidget { background: #111a22; color: #dce8f1; font-size: 10pt; }
QMainWindow, QDialog { background: #0b1218; }
QPushButton { background: #20303d; border: 1px solid #3a5366; border-radius: 4px; padding: 6px 10px; }
QPushButton:hover { background: #2b4353; }
QPushButton[active="true"] { background: #246f4c; border-color: #42c17b; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTableWidget {
    background: #0b141b; border: 1px solid #314654; border-radius: 3px; padding: 3px;
}
QTabWidget::pane { border: 1px solid #2a3d4a; }
QTabBar::tab { background: #192630; padding: 6px 14px; }
QTabBar::tab:selected { background: #294253; }
QLabel[state="on"] { color: #54e58b; font-weight: bold; }
QLabel[state="off"] { color: #ff7a72; font-weight: bold; }
QLabel[class="note"] { color: #8ea7b8; font-size: 9pt; }
QHeaderView::section { background: #1c2c37; color: #dce8f1; padding: 4px; border: 0; }
"""


def main() -> int:
    pg.setConfigOptions(antialias=False, background="#081016", foreground="#b8c8d8")
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Tektronix MSO2024 Remote")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
