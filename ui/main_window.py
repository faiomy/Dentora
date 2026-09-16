# -*- coding: utf-8 -*-
"""Main application window for the Qt version of Dentora.

RTL navigation: the sidebar sits on the RIGHT side of the window (the layout
direction is RTL, so the first added child lands on the right). Active item
shows a 3px accent bar on its right edge (see the global stylesheet's
``QPushButton#NavButton:checked`` rule) with a PRIMARY_600 background.
"""

import os
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QSpacerItem,
    QSizePolicy,
    QLabel,
    QButtonGroup,
    QFrame,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QSize

import database as db
import qtawesome as qta

from . import design
from .dashboard_page import DashboardPage
from .appointments_page import AppointmentsPage
from .patients_page import PatientsPage
from .procedures_page import ProceduresPage
from .staff_page import StaffPage
from .settings_page import SettingsPage
from .expenses_page import ExpensesPage
from .accounts_page import AccountsPage
from .integrations_page import IntegrationsPage
from .labs_page import LabsPage

# Sidebar entries: (key, arabic label, qtawesome icon name, permission key)
NAV_ITEMS = [
    ("dashboard", "الرئيسية", "fa5s.home", None),
    ("appointments", "المواعيد", "fa5s.calendar-alt", "view_appointments"),
    ("patients", "المرضى", "fa5s.user-injured", "view_patients"),
    ("procedures", "الإجراءات الطبية", "fa5s.tooth", "manage_prices"),
    ("staff", "طاقم العمل", "fa5s.users", "manage_staff"),
    ("labs", "المعامل", "fa5s.flask", "manage_labs"),
    ("accounts", "الحسابات", "fa5s.wallet", "view_clinic_accounts"),
    ("expenses", "المصروفات", "fa5s.shopping-basket", "manage_expenses"),
    ("integrations", "التكاملات", "fa5s.plug", "always"),
    ("settings", "الإعدادات", "fa5s.cog", "always"),
]

NAV_PERMISSIONS = {key: perm for key, _, _, perm in NAV_ITEMS}

LOGOUT_ICON = "fa5s.sign-out-alt"


class MainWindow(QMainWindow):
    """Core window with a right-side (RTL) sidebar navigation.

    Parameters
    ----------
    user: dict
        The authenticated user record (from ``LoginDialog.user``).
    """

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self._clinic_name = str((db.get_settings() or {}).get("clinic_name") or "")
        self._refresh_title()
        self.resize(1200, 800)
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "dentora_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self._init_ui()

    def _refresh_title(self):
        # Branding rule: the running clinic's name leads, the product name
        # (Dentora) follows - so a clinic never looks like another's app.
        base = f" — Dentora" if self._clinic_name else "Dentora"
        self.setWindowTitle(f"{self._clinic_name}{base}")

    def set_clinic_name(self, name: str):
        name = str(name or "").strip()
        if name != self._clinic_name:
            self._clinic_name = name
            self._refresh_title()

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._permissions = db.get_role_permissions(self.user.get("role") or "")

        # ---- Sidebar (first child = right side under RTL) -----------------
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        logo_label = QLabel("Dentora")
        logo_label.setObjectName("sidebarLogo")
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)

        # Clinic name (branding: product vs clinic are kept distinct)
        clinic_label = QLabel(self._clinic_name or "")
        clinic_label.setObjectName("sidebarClinic")
        clinic_label.setAlignment(Qt.AlignCenter)
        clinic_label.setWordWrap(True)
        sidebar_layout.addWidget(clinic_label)

        # Small accent line under the logo
        accent_line = QFrame()
        accent_line.setObjectName("AccentLine")
        accent_line.setFixedHeight(3)
        sidebar_layout.addWidget(accent_line)

        # Navigation buttons with flat icons
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        icon_color = design.PRIMARY_100
        for key, label, icon_name, permission in NAV_ITEMS:
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setObjectName("NavButton")
            btn.setProperty("navKey", key)
            btn.setIcon(qta.icon(icon_name, color=icon_color))
            btn.setIconSize(QSize(16, 16))
            btn.clicked.connect(self._on_nav_clicked)
            btn.setEnabled(self._can_access(permission))
            self.button_group.addButton(btn)
            btn.setFixedHeight(46)
            sidebar_layout.addWidget(btn)

        # Spacer to push user section to the bottom
        sidebar_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Current user label
        user_label = QLabel(f"{self.user['full_name']} ({self.user['role']})")
        user_label.setObjectName("sidebarUser")
        user_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(user_label)

        # Logout button
        logout_btn = QPushButton("  تسجيل خروج")
        logout_btn.setObjectName("LogoutButton")
        logout_btn.setIcon(qta.icon(LOGOUT_ICON, color=design.ACCENT_100))
        logout_btn.setIconSize(QSize(15, 15))
        logout_btn.clicked.connect(self._logout)
        sidebar_layout.addWidget(logout_btn)

        layout.addWidget(sidebar)

        # ---- Central stacked area ------------------------------------------
        self.stack = QStackedWidget()
        self.stack.setObjectName("pageArea")
        layout.addWidget(self.stack)

        self.page_widgets = {
            "dashboard": DashboardPage(),
            "appointments": AppointmentsPage(),
            "patients": PatientsPage(),
            "procedures": ProceduresPage(),
            "staff": StaffPage(),
            "labs": LabsPage(),
            "accounts": AccountsPage(),
            "expenses": ExpensesPage(),
            "integrations": IntegrationsPage(),
            "settings": SettingsPage(),
        }
        for widget in self.page_widgets.values():
            self.stack.addWidget(widget)

        # Select default page (dashboard)
        self._select_page("dashboard")

        # Keep dashboard live: refresh when returning to it. Guards against
        # pages that do not define refresh().
        self.stack.currentChanged.connect(self._on_page_changed)

        # Allow settings to push the clinic name change back to the title bar.
        settings_page = self.page_widgets.get("settings")
        if settings_page:
            settings_page.on_clinic_changed = self.set_clinic_name
            settings_page.user_id = self.user.get("id")
            settings_page.user_role = self.user.get("role")
            settings_page.refresh()

    def _on_page_changed(self, index):
        """Refresh the displayed page only when it carries real clinic data."""
        widget = self.stack.widget(index)
        if hasattr(widget, "refresh"):
            try:
                widget.refresh()
            except Exception:
                pass

    def _on_nav_clicked(self):
        btn = self.sender()
        if btn:
            key = btn.property("navKey")
            self._select_page(key)

    def _select_page(self, key: str):
        if not self._can_access(NAV_PERMISSIONS.get(key)):
            return
        widget = self.page_widgets.get(key)
        if widget:
            self.stack.setCurrentWidget(widget)
            for b in self.button_group.buttons():
                b.setChecked(b.property("navKey") == key)

    def _logout(self):
        # Close this window - the calling script will re-show the login dialog
        self.close()

    def _can_access(self, permission_key):
        """Mirrors main.py._can_access: managers bypass the matrix, while
        None/"always" permissions are always allowed for every role."""
        if not permission_key or permission_key == "always":
            return True
        if (self.user.get("role") or "") == "manager":
            return True
        return bool(self._permissions.get(permission_key))
