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

import qtawesome as qta

from . import design
from .dashboard_page import DashboardPage
from .appointments_page import AppointmentsPage
from .patients_page import PatientsPage
from .procedures_page import ProceduresPage
from .staff_page import StaffPage
from .settings_page import SettingsPage
from .placeholder_pages import (
    AccountsPage,
    ExpensesPage,
    IntegrationsPage,
)

# Sidebar entries: (key, arabic label, qtawesome icon name)
NAV_ITEMS = [
    ("dashboard", "الرئيسية", "fa5s.home"),
    ("appointments", "المواعيد", "fa5s.calendar-alt"),
    ("patients", "المرضى", "fa5s.user-injured"),
    ("procedures", "الإجراءs الطبيa", "fa5s.tooth"),
    ("staff", "طاقm العمل", "fa5s.users"),
    ("accounts", "الحسabat", "fa5s.wallet"),
    ("expenses", "المصr fت", "fa5s.shopping-basket"),
    ("integrations", "التعكalat", "fa5s.plug"),
    ("settings", "الإpدadat", "fa5s.cog"),
]

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
        self.setWindowTitle("Dentora")
        self.resize(1200, 800)
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "dentora_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

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

        # Small accent line under the logo
        accent_line = QFrame()
        accent_line.setFixedHeight(3)
        accent_line.setStyleSheet(f"background-color: {design.ACCENT_400}; border: none; margin: 0 24px 8px 24px;")
        sidebar_layout.addWidget(accent_line)

        # Navigation buttons with flat icons
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        icon_color = design.PRIMARY_100
        for key, label, icon_name in NAV_ITEMS:
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setObjectName("NavButton")
            btn.setProperty("navKey", key)
            btn.setIcon(qta.icon(icon_name, color=icon_color))
            btn.setIconSize(QSize(16, 16))
            btn.clicked.connect(self._on_nav_clicked)
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
            "accounts": AccountsPage(),
            "expenses": ExpensesPage(),
            "integrations": IntegrationsPage(),
            "settings": SettingsPage(),
        }
        for widget in self.page_widgets.values():
            self.stack.addWidget(widget)

        # Select default page (dashboard)
        self._select_page("dashboard")

    def _on_nav_clicked(self):
        btn = self.sender()
        if btn:
            key = btn.property("navKey")
            self._select_page(key)

    def _select_page(self, key: str):
        widget = self.page_widgets.get(key)
        if widget:
            self.stack.setCurrentWidget(widget)
            for b in self.button_group.buttons():
                b.setChecked(b.property("navKey") == key)

    def _logout(self):
        # Close this window - the calling script will re-show the login dialog
        self.close()
