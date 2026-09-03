# -*- coding: utf-8 -*-
"""Staff page for the Qt version of Dentora.
Manages users (manager/doctor/secretary) and support staff (assistant/support),
reusing the existing ``database`` functions.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QDialogButtonBox,
    QTabWidget,
    QComboBox,
    QFormLayout,
    QLineEdit,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

import database as db
from . import design
from .components import (
    DataTable,
    PrimaryButton,
    SecondaryButton,
    TextInput,
)

ROLE_LABELS = {"manager": "مدير", "doctor": "طبيب", "secretary": "سكرتارية"}


class UserDialog(QDialog):
    """Add / edit a user account."""

    def __init__(self, role, user=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"إضافة {ROLE_LABELS.get(role, role)}" if not user else "تعديل المستخدم")
        self.setModal(True)
        self.resize(440, 360)
        self.role = role
        self.user = user
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)
        u = self.user or {}

        self.username_edit = TextInput()
        self.username_edit.setText(str(u.get("username") or ""))
        self.username_edit.setEnabled(not self.user)  # username changeable only on add
        form.addRow("اسم المستخدم", self.username_edit)

        self.password_edit = TextInput(placeholder="كلمة المرور")
        self.password_edit.setEchoMode(QLineEdit.Password)
        if not self.user:
            form.addRow("كلمة المرور", self.password_edit)

        self.fullname_edit = TextInput()
        self.fullname_edit.setText(str(u.get("full_name") or ""))
        form.addRow("الاسم الكامل", self.fullname_edit)

        self.phone_edit = TextInput(placeholder="الهاتف")
        self.phone_edit.setText(str(u.get("phone") or ""))
        form.addRow("الهاتف", self.phone_edit)

        self.specialty_edit = TextInput(placeholder="التخصص")
        self.specialty_edit.setText(str(u.get("specialty") or ""))
        form.addRow("التخصص", self.specialty_edit)

        # Read-only role label
        role_label = QLabel(ROLE_LABELS.get(self.role, self.role))
        form.addRow("الدور", role_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        username = self.username_edit.text().strip()
        full_name = self.fullname_edit.text().strip()
        if not full_name:
            return
        phone = self.phone_edit.text().strip()
        specialty = self.specialty_edit.text().strip()
        if self.user:
            db.update_user(self.user["id"], full_name=full_name, phone=phone, specialty=specialty)
        else:
            password = self.password_edit.text().strip()
            if not username or not password:
                return
            db.add_user(username, password, full_name, self.role, phone=phone, specialty=specialty)
        self.accept()


class SupportDialog(QDialog):
    """Add / edit a support staff member."""

    def __init__(self, staff_type, staff=None, parent=None):
        super().__init__(parent)
        self.staff_type = staff_type
        self.staff = staff
        self.setWindowTitle("إضافة عضو" if not staff else "تعديل عضو")
        self.setModal(True)
        self.resize(440, 320)
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)
        s = self.staff or {}

        self.fullname_edit = TextInput()
        self.fullname_edit.setText(str(s.get("full_name") or ""))
        form.addRow("الاسم الكامل", self.fullname_edit)

        self.phone_edit = TextInput(placeholder="الهاتف")
        self.phone_edit.setText(str(s.get("phone") or ""))
        form.addRow("الهاتف", self.phone_edit)

        self.specialty_edit = TextInput(placeholder="التخصص")
        self.specialty_edit.setText(str(s.get("specialty") or ""))
        form.addRow("التخصص", self.specialty_edit)

        self.notes_edit = TextInput(placeholder="ملاحظات")
        self.notes_edit.setText(str(s.get("notes") or ""))
        form.addRow("ملاحظات", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        full_name = self.fullname_edit.text().strip()
        if not full_name:
            return
        if self.staff:
            db.update_support_staff(self.staff["id"], full_name=full_name,
                                    phone=self.phone_edit.text().strip(),
                                    specialty=self.specialty_edit.text().strip(),
                                    notes=self.notes_edit.text().strip())
        else:
            db.add_support_staff(self.staff_type, full_name, phone=self.phone_edit.text().strip(),
                                 notes=self.notes_edit.text().strip(),
                                 specialty=self.specialty_edit.text().strip())
        self.accept()


class _StaffTab(QWidget):
    """A single staff table tab (users or support staff)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(design.SPACING * 2)

        self.table = DataTable()
        self.model = QStandardItemModel()
        self.table.setModel(self.model)
        layout.addWidget(self.table, stretch=1)

        actions = QHBoxLayout()
        self.add_btn = PrimaryButton("+ إضافة")
        self.add_btn.clicked.connect(self._add)
        edit_btn = SecondaryButton("تعديل")
        edit_btn.clicked.connect(self._edit)
        deactivate_btn = SecondaryButton("تعطيل")
        deactivate_btn.clicked.connect(self._deactivate)
        actions.addWidget(self.add_btn)
        actions.addWidget(edit_btn)
        actions.addWidget(deactivate_btn)
        actions.addStretch()
        layout.addLayout(actions)

    # Methods to override -------------------------------------------------
    def _add(self):
        raise NotImplementedError

    def _edit(self):
        raise NotImplementedError

    def _deactivate(self):
        raise NotImplementedError

    def headers(self):
        raise NotImplementedError

    def refresh(self):
        raise NotImplementedError

    def _selected(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        if 0 <= row < len(self.rows):
            return self.rows[row]
        return None

    def _set_headers(self, headers):
        self.model.setHorizontalHeaderLabels(headers)
        self.model.removeRows(0, self.model.rowCount())


class UsersTab(_StaffTab):
    def __init__(self, role, parent=None):
        self.role = role
        super().__init__(parent)
        self._set_headers(["اسم المستخدم", "الاسم الكامل", "التخصص", "نشط"])

    def refresh(self):
        self._set_headers(["اسم المستخدم", "الاسم الكامل", "التخصص", "نشط"])
        self.rows = [u for u in db.get_all_users() if u["role"] == self.role]
        for u in self.rows:
            self.model.appendRow([
                QStandardItem(str(u.get("username") or "")),
                QStandardItem(str(u.get("full_name") or "")),
                QStandardItem(str(u.get("specialty") or "")),
                QStandardItem("نعم" if u.get("active") else "لا"),
            ])
        self.model.setProperty("users", self.rows)

    def _add(self):
        dlg = UserDialog(self.role, user=None, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _edit(self):
        u = self._selected()
        if not u:
            return
        dlg = UserDialog(self.role, user=u, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _deactivate(self):
        u = self._selected()
        if not u:
            return
        from .components import ask_confirmation
        if ask_confirmation(self, "تعطيل", f"تعطيل «{u.get('full_name')}»؟"):
            db.deactivate_user(u["id"])
            self.refresh()


class SupportTab(_StaffTab):
    def __init__(self, staff_type, parent=None):
        self.staff_type = staff_type
        super().__init__(parent)
        self._set_headers(["الاسم الكامل", "الهاتف", "التخصص", "ملاحظات"])

    def refresh(self):
        self._set_headers(["الاسم الكامل", "الهاتف", "التخصص", "ملاحظات"])
        self.rows = db.get_support_staff(self.staff_type)
        for s in self.rows:
            self.model.appendRow([
                QStandardItem(str(s.get("full_name") or "")),
                QStandardItem(str(s.get("phone") or "")),
                QStandardItem(str(s.get("specialty") or "")),
                QStandardItem(str(s.get("notes") or "")),
            ])
        self.model.setProperty("staff", self.rows)

    def _add(self):
        dlg = SupportDialog(self.staff_type, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _edit(self):
        s = self._selected()
        if not s:
            return
        dlg = SupportDialog(self.staff_type, staff=s, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _deactivate(self):
        s = self._selected()
        if not s:
            return
        from .components import ask_confirmation
        if ask_confirmation(self, "تعطيل", f"تعطيل «{s.get('full_name')}»؟"):
            db.set_support_staff_active(s["id"], False)
            self.refresh()


class StaffPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        title = QLabel("طاقم العمل")
        title.setStyleSheet(
            f"font-size: {design.FONT_SIZE + 8}px; font-weight: bold; color: {design.TEXT_COLOR};"
        )
        root_layout.addWidget(title)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        self.tab_managers = UsersTab("manager")
        self.tab_doctors = UsersTab("doctor")
        self.tab_secretaries = UsersTab("secretary")
        self.tab_assistants = SupportTab("assistant")
        self.tab_support = SupportTab("support")

        self.tabs.addTab(self.tab_managers, "المديرين")
        self.tabs.addTab(self.tab_doctors, "الأطباء")
        self.tabs.addTab(self.tab_secretaries, "السكرتارية")
        self.tabs.addTab(self.tab_assistants, "مساعدين الأطباء")
        self.tabs.addTab(self.tab_support, "خدمات مساعدة")

        for tab in (self.tab_managers, self.tab_doctors, self.tab_secretaries,
                    self.tab_assistants, self.tab_support):
            tab.refresh()

    def refresh(self):
        for tab in (self.tab_managers, self.tab_doctors, self.tab_secretaries,
                    self.tab_assistants, self.tab_support):
            tab.refresh()
