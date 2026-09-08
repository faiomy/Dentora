# -*- coding: utf-8 -*-
"""
Entry point for the Qt (PySide6) version of Dentora.

Technical foundation:
- Fusion style + ONE global stylesheet built from ui/design.py tokens
  (applied at QApplication level - no per-widget "default" look survives)
- RTL layout direction app-wide
- Cairo font (assets/fonts/*.ttf) loaded via QFontDatabase at startup
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtCore import Qt

# Ensure the module path includes the project root (for imports of ui package)
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ui import design
from ui.stylesheet import build_global_stylesheet
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow


def load_fonts():
    """Load the bundled Cairo font files (Regular/Medium/SemiBold) so the app
    never depends on the font being installed on the OS."""
    fonts_dir = os.path.join(PROJECT_ROOT, "assets", "fonts")
    loaded = []
    if os.path.isdir(fonts_dir):
        for name in ("Cairo-Regular.ttf", "Cairo-Medium.ttf", "Cairo-SemiBold.ttf"):
            path = os.path.join(fonts_dir, name)
            if os.path.exists(path):
                font_id = QFontDatabase.addApplicationFont(path)
                if font_id >= 0:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    loaded.extend(families)
    return loaded


def apply_font(app, families):
    """Set Cairo as the application font (falls back to Segoe UI if the
    font files could not be loaded)."""
    family = design.FONT_FAMILY if design.FONT_FAMILY in families else "Segoe UI"
    font = QFont(family)
    font.setPointSize(design.FONT_SIZE_BASE)
    app.setFont(font)
    return family


def main():
    app = QApplication(sys.argv)

    # ---- Technical foundation ------------------------------------------
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.RightToLeft)   # RTL app-wide

    families = load_fonts()
    font_family = apply_font(app, families)

    # ONE global stylesheet at the application level
    app.setStyleSheet(build_global_stylesheet())

    if "--print-font" in sys.argv:
        print(f"font family in use: {font_family} (loaded: {families})")

    # ---------------------------------------------------------------------
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
        # Login cancelled or failed - exit application
        sys.exit(0)


if __name__ == "__main__":
    main()
