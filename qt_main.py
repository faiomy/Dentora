# -*- coding: utf-8 -*-
"""
Entry point for the Qt (PySide6) version of the Clinic App.
It launches a minimal placeholder main window.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import Qt


class PlaceholderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dentora – Qt Prototype")
        self.resize(1000, 720)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)
        label = QLabel("Placeholder Qt UI – actual UI will be built in later phases.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)


def main():
    app = QApplication(sys.argv)
    # Global RTL layout for Arabic UI
    app.setLayoutDirection(Qt.RightToLeft)
    win = PlaceholderWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
