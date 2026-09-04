# -*- coding: utf-8 -*-
"""Main application window for the Qt version of Dentora.
It provides a RTL sidebar navigation and a central QStackedWidget for pages.
Only placeholder pages are loaded at this stage – real UI will replace them later.
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
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

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


class MainWindow(QMainWindow):
    """Core window with sidebar navigation.

    Parameters
    ----------
    user: dict
        The authenticated user record (from ``LoginDialog.user``).
    """

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Dentora – Qt UI")
        self.resize(1200, 800)
        # Set application icon (Dentora) if exists
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "dentora_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Sidebar ------------------------------------------------------
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Title / logo area (simple label for now)
        logo_label = QLabel("Dentora")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 12px; color: #003366;")
        sidebar_layout.addWidget(logo_label)

        # Navigation buttons
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        nav_items = [
            ("dashboard", "الرئيسية"),
            ("appointments", "المواعيد"),
            ("patients", "المرضى"),
            ("procedures", "الإجراءات الطبية"),
            ("staff", "طاقم العمل"),
            ("accounts", "الحسابات"),
            ("expenses", "المصروفات"),
            ("integrations", "التكاملات"),
            ("settings", "الإعدادات"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName(f"nav_{key}")
            btn.setProperty("navKey", key)
            btn.clicked.connect(self._on_nav_clicked)
            self.button_group.addButton(btn)
            btn.setFixedHeight(44)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding-left: 16px; border: none; background-color: transparent; font-size: 14px; color: #333333; }"
                "QPushButton:hover { background-color: #e6f2ff; }"
                "QPushButton:checked { background-color: #003366; color: #ffffff; font-weight: bold; border-left: 4px solid #1E88E5; }"
                "QPushButton:checked:hover { background-color: #003366; }"
            )
            sidebar_layout.addWidget(btn)

        # Spacer to push logout to bottom
        sidebar_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Current user label
        user_label = QLabel(f"{self.user['full_name']} ({self.user['role']})")
        user_label.setAlignment(Qt.AlignCenter)
        user_label.setStyleSheet("font-size: 12px; padding: 8px;")
        sidebar_layout.addWidget(user_label)

        # Logout button
        logout_btn = QPushButton("تسجيل خروج")
        logout_btn.setObjectName("logout_btn")
        logout_btn.setFixedHeight(40)
        logout_btn.setStyleSheet(
            "QPushButton { background-color: #ffdddd; border: none; font-weight: bold; }"
            "QPushButton:hover { background-color: #ffbbbb; }"
        )
        logout_btn.clicked.connect(self._logout)
        sidebar_layout.addWidget(logout_btn)

        layout.addWidget(sidebar)

        # ---- Central stacked area ------------------------------------------
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Instantiate placeholder pages and add to stack
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
            # Update button checked state
            for b in self.button_group.buttons():
                b.setChecked(b.property("navKey") == key)

    def _logout(self):
        # Close this window – the calling script will re-show the login dialog
        self.close()
