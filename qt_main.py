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
import logging
import tempfile
from typing import Optional
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtCore import Qt, QObject

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


LOGGER = logging.getLogger("dentora.qt")


def configure_logging():
    """Configure a small local startup log without ever recording secrets."""
    log_dir = os.environ.get("DENTORA_LOG_DIR")
    if not log_dir:
        log_dir = os.path.join(
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
            or tempfile.gettempdir(),
            "Dentora",
        )
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "dentora_startup.log")
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root = logging.getLogger("dentora")
        root.setLevel(logging.INFO)
        if not any(getattr(h, "baseFilename", None) == handler.baseFilename
                   for h in root.handlers):
            root.addHandler(handler)
        LOGGER.info("Dentora startup logging initialized")
        return log_path
    except Exception:
        # Logging must never prevent the application from launching.
        return None


def _show_startup_failure(title, message, exc=None):
    if exc is not None:
        LOGGER.exception(message)
    else:
        LOGGER.error(message)
    QMessageBox.warning(None, title, message)


def _handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Keep unexpected startup/runtime failures visible and recorded."""
    if exc_type is KeyboardInterrupt:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    LOGGER.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(
            None,
            "خطأ غير متوقع",
            "حدث خطأ غير متوقع. راجع سجل Dentora لمزيد من التفاصيل.",
        )
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


def _stop_api_server_at_exit():
    try:
        from api.server import stop_api_server
        stop_api_server()
        LOGGER.info("API server stopped")
    except Exception:
        LOGGER.exception("Failed to stop the API server")


def shutdown_runtime():
    """Explicit, idempotent shutdown for runtime services."""
    _stop_api_server_at_exit()


def start_api_server_if_enabled():
    """تشغيل خادم الـ API في الخلفية لو مفعّل من إعدادات العيادة (محلي فقط
    افتراضيًا على 127.0.0.1) - من غير ما يوقف أو يجمّد حلقات الـ UI."""
    settings = db.get_settings() or {}
    if not settings.get("api_server_enabled"):
        LOGGER.info("API server is disabled")
        return False
    try:
        from api.server import start_api_server_if_enabled as _start
        started = _start()
        if started:
            from api.server import get_api_server
            url = get_api_server().url
            LOGGER.info("API server started at %s", url)
            print(f"[API] خادم التكامل يعمل على {url}")
            return True
        from api.server import get_api_server
        url = get_api_server().url
        _show_startup_failure(
            "تعذر تشغيل API",
            f"خادم التكامل مفعّل لكنه لم يبدأ على {url}. "
            "يمكنك تعديل المنفذ من الإعدادات.",
        )
        return False
    except Exception as exc:
        _show_startup_failure(
            "تعذر تشغيل API",
            "حدث خطأ أثناء تشغيل خادم التكامل. راجع سجل Dentora.",
            exc,
        )
        return False


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


class SessionController(QObject):
    """Own the authenticated Qt session and support logout/re-login."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.login_dialog: Optional[LoginDialog] = None
        self.main_window: Optional[MainWindow] = None

    def show_main_window(self, user):
        effective = db.get_effective_settings(user["id"]) or {}
        apply_ui_theme(
            effective.get("theme_id"),
            primary=effective.get("primary_color"),
            secondary=effective.get("secondary_color"),
            app=self.app,
        )
        self.main_window = MainWindow(user)
        self.main_window.logout_requested.connect(self._on_logout_requested)
        self.main_window.show()
        LOGGER.info("Authenticated session started for user id=%s", user.get("id"))

    def _on_logout_requested(self):
        window = self.main_window
        self.main_window = None
        if window is not None:
            window.close()
            window.deleteLater()
        LOGGER.info("User logged out; showing login dialog")
        self._show_login_again()

    def _show_login_again(self):
        dialog = LoginDialog()
        self.login_dialog = dialog
        dialog.accepted.connect(self._on_relogin_accepted)
        dialog.rejected.connect(self._on_relogin_rejected)
        dialog.open()

    def _on_relogin_accepted(self):
        dialog = self.login_dialog
        self.login_dialog = None
        if dialog is None or not dialog.user:
            LOGGER.error("Login dialog accepted without a user")
            self.app.quit()
            return
        dialog.deleteLater()
        self.show_main_window(dialog.user)

    def _on_relogin_rejected(self):
        self.login_dialog = None
        LOGGER.info("Login dialog closed after logout; exiting")
        self.app.quit()


def create_application(argv=None):
    app = QApplication(sys.argv if argv is None else argv)
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.RightToLeft)
    return app


def main():
    app = create_application()
    configure_logging()
    sys.excepthook = _handle_uncaught_exception
    app.aboutToQuit.connect(shutdown_runtime)

    try:
        families = load_fonts()
        font_family = apply_font(app, families)
        LOGGER.info("Font selected: %s; bundled families: %s", font_family, families)

        # Ensure the database schema exists (idempotent).
        db.init_db()

        # Apply the clinic theme before any startup warning or dialog appears.
        settings = db.get_settings() or {}
        apply_ui_theme(
            settings.get("theme_id"),
            primary=settings.get("primary_color"),
            secondary=settings.get("secondary_color"),
            app=app,
        )

        start_api_server_if_enabled()

        if "--print-font" in sys.argv:
            print(f"font family in use: {font_family} (loaded: {families})")

        # Initial login remains modal so the main window is never exposed
        # before authentication. Re-login after logout is non-modal and uses
        # the normal application event loop.
        login = LoginDialog()
        if login.exec() != QDialog.Accepted or not login.user:
            LOGGER.info("Initial login cancelled or failed")
            return 0

        controller = SessionController(app)
        controller.show_main_window(login.user)
        return app.exec()
    except Exception:
        LOGGER.exception("Application startup failed")
        QMessageBox.critical(
            None,
            "تعذر تشغيل Dentora",
            "تعذر تشغيل البرنامج. راجع سجل Dentora لمزيد من التفاصيل.",
        )
        return 1
    finally:
        # aboutToQuit covers normal event-loop exits; this covers initial
        # login cancellation and startup failures before the event loop.
        shutdown_runtime()


if __name__ == "__main__":
    sys.exit(main())
