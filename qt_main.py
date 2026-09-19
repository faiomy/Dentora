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

import atexit

from ui import design
from ui.stylesheet import apply_ui_theme
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow

import database as db


def _stop_api_server_at_exit():
    try:
        from api.server import stop_api_server
        stop_api_server()
    except Exception:
        pass


def start_api_server_if_enabled():
    """تشغيل خادم الـ API في الخلفية لو مفعّل من إعدادات العيادة (محلي فقط
    افتراضيًا على 127.0.0.1) - من غير ما يوقف أو يجمّد حلقات الـ UI."""
    try:
        from api.server import start_api_server_if_enabled as _start
        started = _start()
        if started:
            from api.server import get_api_server
            print(f"[API] خادم التكامل يعمل على {get_api_server().url}")
    except Exception:
        pass


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

    # Ensure the database schema exists (idempotent).
    db.init_db()

    # تشغيل خادم الـ API في الخلفية (لو مفعّل) + إيقافه عند الخروج
    atexit.register(_stop_api_server_at_exit)
    start_api_server_if_enabled()

    # ONE global stylesheet at the application level, themed from the
    # clinic-wide settings so the login screen already matches the brand.
    settings = db.get_settings() or {}
    apply_ui_theme(
        settings.get("theme_id"),
        primary=settings.get("primary_color"),
        secondary=settings.get("secondary_color"),
        app=app,
    )

    if "--print-font" in sys.argv:
        print(f"font family in use: {font_family} (loaded: {families})")

    # ---------------------------------------------------------------------
    login = LoginDialog()
    if login.exec() == LoginDialog.Accepted:
        user = login.user
        if not user:
            QMessageBox.critical(None, "Error", "Login succeeded but no user data was returned.")
            sys.exit(1)
        # Per-user appearance: merge the user's personal theme preferences
        # (theme_id is clinic-wide; fonts may be personal).
        effective = db.get_effective_settings(user["id"]) or {}
        apply_ui_theme(
            effective.get("theme_id"),
            primary=effective.get("primary_color"),
            secondary=effective.get("secondary_color"),
            app=app,
        )
        main_win = MainWindow(user)
        main_win.show()
        sys.exit(app.exec())
    else:
        # Login cancelled or failed - exit application
        sys.exit(0)


if __name__ == "__main__":
    main()
