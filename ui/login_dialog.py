# -*- coding: utf-8 -*-
"""Qt login dialog that authenticates using the existing `database` module.
It respects the existing settings (require password, remember login) but
only implements the minimal UI needed for Phase 1.
"""

import os
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

import database as db
import theme


class LoginDialog(QDialog):
    """Simple login dialog.

    - Shows a dropdown of active users (full name + role).
    - If the settings require a password, a password field is shown.
    - On successful authentication, ``self.user`` holds the user record.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تسجيل الدخول - Dentora")
        self.setModal(True)
        self.resize(380, 260)
        # Use the Dentora icon if it exists
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "dentora_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.user = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Header branding (minimal for now)
        header = QLabel("Dentora")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #003366;")
        layout.addWidget(header)

        settings = db.get_settings()
        require_password = bool(settings.get("require_password", 1))

        # Populate active users
        users = [u for u in db.get_all_users() if u["active"]]
        if not users:
            QMessageBox.critical(self, "خطأ", "لا يوجد مستخدمون مفعَّلون. راجع قاعدة البيانات.")
            self.reject()
            return
        self.user_map = {
            f"{u['full_name']} ({db.ROLE_LABELS.get(u['role'], u['role'])})": u for u in users
        }
        user_names = list(self.user_map.keys())
        remembered = settings.get("remembered_username")
        default_user = user_names[0]
        if remembered:
            for name, u in self.user_map.items():
                if u["username"] == remembered:
                    default_user = name
                    break

        user_label = QLabel("المستخدم")
        user_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(user_label)
        self.user_combo = QComboBox()
        self.user_combo.addItems(user_names)
        self.user_combo.setCurrentText(default_user)
        layout.addWidget(self.user_combo)

        # Password field (optional)
        self.password_edit = None
        if require_password:
            pw_label = QLabel("كلمة المرور")
            pw_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(pw_label)
            pw_row = QHBoxLayout()
            self.password_edit = QLineEdit()
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_edit.setPlaceholderText("******")
            pw_row.addWidget(self.password_edit)
            # Show/hide eye button (simple without external icon)
            self.toggle_eye_btn = QPushButton("👁")
            self.toggle_eye_btn.setCheckable(True)
            self.toggle_eye_btn.setFixedSize(24, 24)
            self.toggle_eye_btn.setStyleSheet("border: none;")
            self.toggle_eye_btn.toggled.connect(self._toggle_password_visibility)
            pw_row.addWidget(self.toggle_eye_btn)
            layout.addLayout(pw_row)

        # Remember me checkbox
        self.remember_cb = QCheckBox("تذكر بيانات الدخول")
        self.remember_cb.setChecked(bool(settings.get("remember_login", 0)))
        layout.addWidget(self.remember_cb)

        # Login button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        login_btn = QPushButton("تسجيل الدخول")
        login_btn.clicked.connect(self._attempt_login)
        btn_layout.addWidget(login_btn)
        layout.addLayout(btn_layout)

    def _toggle_password_visibility(self, checked: bool):
        if self.password_edit:
            self.password_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def _attempt_login(self):
        selected_name = self.user_combo.currentText()
        user = self.user_map.get(selected_name)
        if not user:
            QMessageBox.warning(self, "خطأ", "المستخدم غير صالح.")
            return
        password = self.password_edit.text() if self.password_edit else ""
        if db.authenticate_user(user["username"], password):
            # Remember login settings
            if self.remember_cb.isChecked():
                db.set_setting_value("remember_login", 1)
                db.set_setting_value("remembered_username", user["username"])
            else:
                db.set_setting_value("remember_login", 0)
                db.set_setting_value("remembered_username", "")
            self.user = user
            self.accept()
        else:
            QMessageBox.warning(self, "خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة.")
