# -*- coding: utf-8 -*-
"""
Entry point for the Qt (PySide6) version of the Clinic App.
It launches a minimal placeholder main window.
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

# Ensure the module path includes the project root (for imports of ui package)
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    # RTL layout for Arabic UI (global)
    app.setLayoutDirection(Qt.RightToLeft)

    login = LoginDialog()
    if login.exec() == LoginDialog.Accepted:
        user = login.user
        if not user:
            QMessageBox.critical(None, "Error", "Login succeeded but no user data was returned.")
            sys.exit(1)
        main_win = MainWindow(user)
        main_win.show()
        sys.exit(app.exec())
    else:
        # Login cancelled or failed – exit application
        sys.exit(0)


if __name__ == "__main__":
    main()
