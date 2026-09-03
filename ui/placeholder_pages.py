# -*- coding: utf-8 -*-
"""Placeholder page widgets for the Qt version of Dentora.
Each page simply displays its name; real UI will replace them later.
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class PlaceholderPage(QWidget):
    """Base class for placeholder pages.
    Subclasses only need to set ``self.title``.
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel(title)
        label.setStyleSheet("font-size: 24px; color: #555555;")
        layout.addWidget(label)


# Individual placeholders – easy to extend later
class DashboardPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("الصفحة الرئيسية – Dashboard", parent)

class AppointmentsPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("المواعيد – Appointments", parent)

class PatientsPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("المرضى – Patients", parent)

class ProceduresPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("الإجراءات الطبية – Procedures", parent)

class StaffPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("طاقم العمل – Staff", parent)

class AccountsPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("الحسابات – Accounts", parent)

class ExpensesPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("المصروفات – Expenses", parent)

class IntegrationsPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("التكاملات – Integrations", parent)

class SettingsPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("الإعدادات – Settings", parent)
