# -*- coding: utf-8 -*-
"""Settings page for the Qt version of Dentora.
Category navigation over: clinic info, appearance (theme / brand color /
dark mode), schedule & holidays, security, and account management.
All changes persist through the existing ``database`` functions and the
appearance category applies immediately by rebuilding the global QSS.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QStackedWidget,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QListWidgetItem,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QColorDialog,
    QApplication,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt

import database as db
import theme
from . import design
from .constants import ltr
from .components import (
    DataTable,
    PrimaryButton,
    SecondaryButton,
    TextInput,
    DateInput,
    FieldLabel,
    show_error,
    show_info,
)

WEEKDAY_NAMES = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
                 4: "الجمعة", 5: "السبت", 6: "الأحد"}


class AccountDialog(QDialog):
    """Add / edit a user account through the existing auth architecture.

    - New accounts require a username, password and full name.
    - Editing keeps the password unless a new one is typed.
    - Role and the active flag are editable in both directions
      (db.add_user / db.update_user / db.deactivate_user).
    """

    def __init__(self, user=None, current_user_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مستخدم جديد" if not user else "تعديل مستخدم")
        self.setModal(True)
        self.resize(480, 400)
        self.user = user
        self.current_user_id = current_user_id
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)
        u = self.user or {}

        self.username_edit = TextInput()
        self.username_edit.setText(str(u.get("username") or ""))
        self.username_edit.setEnabled(not self.user)
        self.username_edit.textChanged.connect(lambda _: self.username_edit.set_error(False))
        form.addRow(FieldLabel("اسم المستخدم", required=not self.user), self.username_edit)

        self.password_edit = TextInput(placeholder="كلمة المرور")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.textChanged.connect(lambda _: self.password_edit.set_error(False))
        form.addRow(
            FieldLabel("كلمة المرور", required=not self.user),
            self.password_edit,
        )
        if self.user:
            note = QLabel("اتركه فارغًا لإبقاء كلمة المرور الحالية")
            note.setObjectName("MutedLabel")
            form.addRow("", note)

        self.fullname_edit = TextInput()
        self.fullname_edit.setText(str(u.get("full_name") or ""))
        self.fullname_edit.textChanged.connect(lambda _: self.fullname_edit.set_error(False))
        form.addRow(FieldLabel("الاسم الكامل", required=True), self.fullname_edit)

        self.phone_edit = TextInput(placeholder="الهاتف")
        self.phone_edit.setText(str(u.get("phone") or ""))
        form.addRow(FieldLabel("الهاتف"), self.phone_edit)

        self.specialty_edit = TextInput(placeholder="التخصص")
        self.specialty_edit.setText(str(u.get("specialty") or ""))
        form.addRow(FieldLabel("التخصص"), self.specialty_edit)

        self.role_combo = QComboBox()
        self._role_keys = list(db.ROLE_LABELS.keys())
        self.role_combo.addItems([db.ROLE_LABELS[k] for k in self._role_keys])
        if self.user:
            role = u.get("role")
            if role in self._role_keys:
                self.role_combo.setCurrentIndex(self._role_keys.index(role))
        form.addRow(FieldLabel("الدور"), self.role_combo)

        self.active_cb = QCheckBox("حساب نشط (مسموح بتسجيل الدخول)")
        self.active_cb.setChecked(bool(u.get("active", 1)) if self.user else True)
        form.addRow(FieldLabel("الحالة"), self.active_cb)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        username = self.username_edit.text().strip()
        full_name = self.fullname_edit.text().strip()
        password = self.password_edit.text().strip()
        errors = False
        if not full_name:
            self.fullname_edit.set_error(True)
            errors = True
        if not self.user and not username:
            self.username_edit.set_error(True)
            errors = True
        if not self.user and not password:
            self.password_edit.set_error(True)
            errors = True
        if errors:
            return
        role = self._role_keys[self.role_combo.currentIndex()]
        active = 1 if self.active_cb.isChecked() else 0
        if not active and self.user and self.current_user_id == self.user["id"]:
            show_error(self, "خطأ", "لا يمكنك تعطيل حسابك الحالي.")
            return
        phone = self.phone_edit.text().strip()
        specialty = self.specialty_edit.text().strip()
        if self.user:
            fields = dict(full_name=full_name, phone=phone, specialty=specialty,
                          role=role, active=active)
            if password:
                fields["password"] = password
            db.update_user(self.user["id"], **fields)
        else:
            if not username or not password:
                return
            db.add_user(username, password, full_name, role, phone=phone, specialty=specialty)
        self.accept()


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = db.get_settings()
        self.user_id = None          # assigned by MainWindow when available
        self.on_clinic_changed = None  # callback(clinic_name) for the title bar
        self._build_ui()
        self._refresh_clinic()
        self._refresh_appearance()
        self._refresh_schedule()
        self._refresh_users()
        self._refresh_users_table()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING, design.SPACING,
                                       design.SPACING, design.SPACING)
        root_layout.setSpacing(design.SPACING * 2)

        # Sidebar categories
        self.category_list = QListWidget()
        self.category_list.setObjectName("SettingsCategories")
        self.category_list.setFixedWidth(200)
        self.settings = self.settings or {}
        categories = ["بيانات العيادة", "المظهر", "المواعيد والإجازات", "الأمان", "المستخدمون"]
        for c in categories:
            self.category_list.addItem(c)
        self.category_list.currentRowChanged.connect(self._switch_category)
        root_layout.addWidget(self.category_list)

        # Stacked panels
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        self.clinic_panel = self._build_clinic_panel()
        self.appearance_panel = self._build_appearance_panel()
        self.schedule_panel = self._build_schedule_panel()
        self.security_panel = self._build_security_panel()
        self.users_panel = self._build_users_panel()

        self.stack.addWidget(self.clinic_panel)
        self.stack.addWidget(self.appearance_panel)
        self.stack.addWidget(self.schedule_panel)
        self.stack.addWidget(self.security_panel)
        self.stack.addWidget(self.users_panel)

        self.category_list.setCurrentRow(0)

    def _switch_category(self, row):
        self.stack.setCurrentIndex(row)

    # ------------------------------------------------------------------
    # Clinic info
    # ------------------------------------------------------------------
    def _build_clinic_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(design.SPACING * 2)

        layout.addWidget(QLabel("بيانات العيادة"))
        form = QVBoxLayout()
        self.clinic_name_edit = TextInput()
        self.clinic_address_edit = TextInput()
        self.tax_card_edit = TextInput()
        form.addWidget(self._labeled("اسم العيادة", self.clinic_name_edit))
        form.addWidget(self._labeled("العنوان", self.clinic_address_edit))
        form.addWidget(self._labeled("رقم البطاقة الضريبية", self.tax_card_edit))
        save_btn = PrimaryButton("حفظ")
        save_btn.clicked.connect(self._save_clinic)
        layout.addLayout(form)
        layout.addWidget(save_btn)

        layout.addWidget(QLabel("أرقام هواتف العيادة"))
        self.phones_list = QListWidget()
        layout.addWidget(self.phones_list, stretch=1)
        phone_row = QHBoxLayout()
        self.new_phone_edit = TextInput(placeholder="رقم الهاتف")
        add_phone_btn = SecondaryButton("إضافة")
        add_phone_btn.clicked.connect(self._add_phone)
        del_phone_btn = SecondaryButton("حذف")
        del_phone_btn.clicked.connect(self._delete_phone)
        phone_row.addWidget(self.new_phone_edit, stretch=1)
        phone_row.addWidget(add_phone_btn)
        phone_row.addWidget(del_phone_btn)
        layout.addLayout(phone_row)

        return panel

    def _labeled(self, text, widget):
        row = QWidget()
        lay = QVBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lab = FieldLabel(text)
        lay.addWidget(lab)
        lay.addWidget(widget)
        return row

    def _refresh_clinic(self):
        s = self.settings or {}
        self.clinic_name_edit.setText(str(s.get("clinic_name") or ""))
        self.clinic_address_edit.setText(str(s.get("clinic_address") or ""))
        self.tax_card_edit.setText(str(s.get("tax_card_number") or ""))
        self._refresh_phones()

    def _refresh_phones(self):
        self.phones_list.clear()
        for p in db.get_clinic_phones():
            self.phones_list.addItem(QListWidgetItem(ltr(str(p["phone_number"]))))

    def _save_clinic(self):
        name = self.clinic_name_edit.text().strip()
        db.update_settings(
            clinic_name=name,
            clinic_address=self.clinic_address_edit.text().strip(),
            tax_card_number=self.tax_card_edit.text().strip(),
        )
        self.settings = db.get_settings()
        if self.on_clinic_changed:
            self.on_clinic_changed(name)
        show_info(self, "تم", "تم حفظ بيانات العيادة.")

    def _add_phone(self):
        num = self.new_phone_edit.text().strip()
        if num:
            db.add_clinic_phone(num)
            self.new_phone_edit.clear()
            self._refresh_phones()

    def _delete_phone(self):
        row = self.phones_list.currentRow()
        if row < 0:
            return
        phones = db.get_clinic_phones()
        if 0 <= row < len(phones):
            db.delete_clinic_phone(phones[row]["id"])
            self._refresh_phones()

    # ------------------------------------------------------------------
    # Appearance (theme / brand color / dark mode) - applies immediately
    # ------------------------------------------------------------------
    def _build_appearance_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(design.SPACING * 2)
        layout.addWidget(QLabel("المظهر"))

        layout.addWidget(FieldLabel("الثيم (الألوان)"))
        row = QHBoxLayout()
        self.theme_swatch = QLabel("  ")
        self.theme_swatch.setFixedSize(26, 26)
        self.theme_swatch.setStyleSheet("border-radius: 13px; border: 1px solid transparent;")
        self.theme_combo = QComboBox()
        self._theme_ids = []
        for tid, preset in theme.THEME_PRESETS.items():
            self.theme_combo.addItem(preset.get("name", tid))
            self._theme_ids.append(tid)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selected)
        row.addWidget(self.theme_swatch)
        row.addWidget(self.theme_combo, stretch=1)
        layout.addLayout(row)
        hint = QLabel("اختيار الثيم يُطبَّق فورًا")
        hint.setObjectName("MutedLabel")
        layout.addWidget(hint)

        layout.addWidget(FieldLabel("الوضع الداكن"))
        self.dark_cb = QCheckBox("تفعيل الوضع الداكن")
        self.dark_cb.toggled.connect(self._on_dark_toggled)
        layout.addWidget(self.dark_cb)

        layout.addWidget(FieldLabel("لون العلامة التجارية"))
        brand_row = QHBoxLayout()
        self.brand_swatch = QLabel("  ")
        self.brand_swatch.setFixedSize(26, 26)
        self.brand_swatch.setStyleSheet("border-radius: 13px; border: 1px solid currentColor;")
        choose_btn = SecondaryButton("اختيار لون مخصص")
        choose_btn.clicked.connect(self._pick_brand_color)
        reset_btn = SecondaryButton("استعادة لون الثيم")
        reset_btn.clicked.connect(self._reset_brand_color)
        brand_row.addWidget(self.brand_swatch)
        brand_row.addWidget(choose_btn)
        brand_row.addWidget(reset_btn)
        brand_row.addStretch()
        layout.addLayout(brand_row)
        hint2 = QLabel("اللون المخصص يُطبق على الأزرار الرئيسية والعناصر المميزة")
        hint2.setObjectName("MutedLabel")
        layout.addWidget(hint2)

        layout.addStretch()
        return panel

    def _effective(self):
        if self.user_id:
            return db.get_effective_settings(self.user_id) or self.settings or {}
        return self.settings or {}

    def _refresh_appearance(self):
        eff = self._effective()
        theme_id = eff.get("theme_id") or theme.DEFAULT_THEME_ID
        preset = theme.THEME_PRESETS.get(theme_id, {})
        dark = bool(eff.get("dark_mode"))
        self.dark_cb.blockSignals(True)
        self.dark_cb.setChecked(dark)
        self.dark_cb.blockSignals(False)
        idx = self._theme_ids.index(theme_id) if theme_id in self._theme_ids else 0
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)
        primary = eff.get("primary_color") or preset.get("primary") or design.PRIMARY_400
        self._set_swatch(self.theme_swatch, primary)
        self._set_swatch(self.brand_swatch, primary)

    @staticmethod
    def _set_swatch(label, color):
        label.setStyleSheet(
            f"background-color: {color}; border-radius: 13px; border: 1px solid {design.BORDER};"
        )

    def _apply_appearance(self, notify=False):
        eff = self._effective()
        from .stylesheet import apply_ui_theme
        app = QApplication.instance()
        apply_ui_theme(eff.get("theme_id"), dark=bool(eff.get("dark_mode")),
                       primary=eff.get("primary_color"),
                       secondary=eff.get("secondary_color"),
                       app=app)
        self._refresh_appearance()
        self.settings = db.get_settings()

    def _on_theme_selected(self, index):
        if index < 0 or index >= len(self._theme_ids):
            return
        theme_id = self._theme_ids[index]
        if self.user_id:
            db.set_user_theme(self.user_id, theme_id)
        else:
            db.set_theme(theme_id)
        preset = theme.THEME_PRESETS.get(theme_id, {})
        self._set_swatch(self.theme_swatch, preset.get("primary", design.PRIMARY_400))
        self._apply_appearance()

    def _on_dark_toggled(self, checked):
        db.set_setting_value("dark_mode", 1 if checked else 0)
        self._apply_appearance()

    def _pick_brand_color(self):
        eff = self._effective()
        initial = QColor(eff.get("primary_color") or design.PRIMARY_400)
        color = QColorDialog.getColor(initial, self, "لون العلامة التجارية")
        if not color.isValid():
            return
        hex_color = color.name()
        secondary = design.mix(hex_color, "#000000", 0.5)
        db.update_settings(primary_color=hex_color, secondary_color=secondary)
        self._apply_appearance()
        show_info(self, "تم", "تم حفظ لون العلامة التجارية.")

    def _reset_brand_color(self):
        eff = self._effective()
        theme_id = eff.get("theme_id") or theme.DEFAULT_THEME_ID
        preset = theme.THEME_PRESETS.get(theme_id, {})
        if preset:
            db.update_settings(primary_color=preset["primary"],
                               secondary_color=preset["secondary"])
            self._apply_appearance()

    # ------------------------------------------------------------------
    # Schedule & holidays
    # ------------------------------------------------------------------
    def _build_schedule_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(design.SPACING * 2)

        layout.addWidget(QLabel("ساعات العمل"))
        hour_row = QHBoxLayout()
        self.start_hour = QSpinBox()
        self.start_hour.setRange(0, 23)
        self.end_hour = QSpinBox()
        self.end_hour.setRange(1, 24)
        hour_row.addWidget(QLabel("من:"))
        hour_row.addWidget(self.start_hour)
        hour_row.addWidget(QLabel("إلى:"))
        hour_row.addWidget(self.end_hour)
        save_schedule_btn = PrimaryButton("حفظ الساعات")
        save_schedule_btn.clicked.connect(self._save_schedule_hours)
        hour_row.addWidget(save_schedule_btn)
        hour_row.addStretch()
        layout.addLayout(hour_row)

        layout.addWidget(QLabel("الإجازات الأسبوعية"))
        self.day_checks = {}
        day_grid = QHBoxLayout()
        for num, name in WEEKDAY_NAMES.items():
            cb = QCheckBox(name)
            self.day_checks[num] = cb
            day_grid.addWidget(cb)
        layout.addLayout(day_grid)
        save_days_btn = PrimaryButton("حفظ الإجازات الأسبوعية")
        save_days_btn.clicked.connect(self._save_weekly_holidays)
        layout.addWidget(save_days_btn)

        layout.addWidget(QLabel("إجازات محددة"))
        self.holiday_dates_list = QListWidget()
        layout.addWidget(self.holiday_dates_list, stretch=1)
        hol_row = QHBoxLayout()
        self.holiday_date_edit = DateInput()
        self.holiday_date_edit.setDisplayFormat("yyyy-MM-dd")
        add_hol_btn = SecondaryButton("إضافة")
        add_hol_btn.clicked.connect(self._add_holiday)
        del_hol_btn = SecondaryButton("حذف")
        del_hol_btn.clicked.connect(self._remove_holiday)
        hol_row.addWidget(self.holiday_date_edit)
        hol_row.addWidget(add_hol_btn)
        hol_row.addWidget(del_hol_btn)
        hol_row.addStretch()
        layout.addLayout(hol_row)

        return panel

    def _refresh_schedule(self):
        s = self.settings or {}
        try:
            self.start_hour.setValue(int(s.get("schedule_start_hour") or 9))
            self.end_hour.setValue(int(s.get("schedule_end_hour") or 18))
        except (TypeError, ValueError):
            pass
        weekly = db.get_weekly_holidays()
        for num, cb in self.day_checks.items():
            cb.setChecked(num in weekly)
        self._refresh_holiday_dates()

    def _refresh_holiday_dates(self):
        self.holiday_dates_list.clear()
        for d in sorted(db.get_holiday_dates()):
            self.holiday_dates_list.addItem(QListWidgetItem(d))

    def _save_schedule_hours(self):
        db.set_schedule_hours(self.start_hour.value(), self.end_hour.value())
        show_info(self, "تم", "تم حفظ ساعات العمل.")

    def _save_weekly_holidays(self):
        sel = [num for num, cb in self.day_checks.items() if cb.isChecked()]
        db.set_weekly_holidays(sel)
        show_info(self, "تم", "تم حفظ الإجازات الأسبوعية.")

    def _add_holiday(self):
        d = self.holiday_date_edit.date().toString("yyyy-MM-dd")
        db.add_holiday_date(d)
        self._refresh_holiday_dates()

    def _remove_holiday(self):
        item = self.holiday_dates_list.currentItem()
        if item:
            db.remove_holiday_date(item.text())
            self._refresh_holiday_dates()

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    def _build_security_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(design.SPACING * 2)
        layout.addWidget(QLabel("الأمان"))

        layout.addWidget(QLabel("طلب كلمة المرور عند تسجيل الدخول"))
        self.require_pw_cb = QCheckBox("طلب كلمة المرور")
        layout.addWidget(self.require_pw_cb)
        save_pw_btn = PrimaryButton("حفظ")
        save_pw_btn.clicked.connect(self._save_require_password)
        layout.addWidget(save_pw_btn)

        layout.addWidget(QLabel("تغيير كلمة المرور لمستخدم"))
        user_row = QHBoxLayout()
        self.pw_user_combo = QComboBox()
        user_row.addWidget(self.pw_user_combo, stretch=1)
        layout.addLayout(user_row)
        self.new_password_edit = TextInput(placeholder="كلمة المرور الجديدة")
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.new_password_edit)
        change_pw_btn = PrimaryButton("تغيير كلمة المرور")
        change_pw_btn.clicked.connect(self._change_password)
        layout.addWidget(change_pw_btn)
        layout.addStretch()

        return panel

    def _refresh_users(self):
        self.users = db.get_all_users()
        self.pw_user_combo.clear()
        for u in self.users:
            self.pw_user_combo.addItem(f"{u['full_name']} ({u['username']})", u["id"])

    def _save_require_password(self):
        db.set_require_password(self.require_pw_cb.isChecked())
        self.settings = db.get_settings()
        show_info(self, "تم", "تم حفظ إعدادات الأمان.")

    def _change_password(self):
        idx = self.pw_user_combo.currentIndex()
        new_pw = self.new_password_edit.text().strip()
        if idx < 0 or not new_pw:
            show_error(self, "خطأ", "اختر مستخدمًا وأدخل كلمة مرور جديدة.")
            return
        user_id = self.pw_user_combo.itemData(idx)
        db.update_user(user_id, password=new_pw)
        self.new_password_edit.clear()
        show_info(self, "تم", "تم تغيير كلمة المرور.")

    # ------------------------------------------------------------------
    # Users (account management)
    # ------------------------------------------------------------------
    def _build_users_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(design.SPACING * 2)
        layout.addWidget(QLabel("المستخدمون"))
        self.users_table = DataTable()
        self.users_model = QStandardItemModel()
        self.users_model.setHorizontalHeaderLabels(
            ["اسم المستخدم", "الاسم الكامل", "الدور", "نشط"])
        self.users_table.setModel(self.users_model)
        layout.addWidget(self.users_table, stretch=1)

        actions = QHBoxLayout()
        add_btn = PrimaryButton("+ مستخدم جديد")
        add_btn.clicked.connect(self._add_user)
        edit_btn = SecondaryButton("تعديل")
        edit_btn.clicked.connect(self._edit_user)
        toggle_btn = SecondaryButton("تفعيل / تعطيل")
        toggle_btn.clicked.connect(self._toggle_user_active)
        actions.addWidget(add_btn)
        actions.addWidget(edit_btn)
        actions.addWidget(toggle_btn)
        actions.addStretch()
        layout.addLayout(actions)
        return panel

    def _refresh_users_table(self):
        self._refresh_users()
        self.users_model.removeRows(0, self.users_model.rowCount())
        for u in self.users:
            self.users_model.appendRow([
                QStandardItem(str(u.get("username") or "")),
                QStandardItem(str(u.get("full_name") or "")),
                QStandardItem(db.ROLE_LABELS.get(u.get("role"), u.get("role") or "")),
                QStandardItem("نعم" if u.get("active") else "لا"),
            ])

    def _selected_user(self):
        index = self.users_table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        if 0 <= row < len(self.users):
            return self.users[row]
        return None

    def _add_user(self):
        dlg = AccountDialog(user=None, current_user_id=self.user_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_users_table()

    def _edit_user(self):
        u = self._selected_user()
        if not u:
            return
        dlg = AccountDialog(user=u, current_user_id=self.user_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_users_table()

    def _toggle_user_active(self):
        u = self._selected_user()
        if not u:
            return
        new_active = not bool(u.get("active"))
        if not new_active and self.user_id == u["id"]:
            show_error(self, "خطأ", "لا يمكنك تعطيل حسابك الحالي.")
            return
        db.update_user(u["id"], active=1 if new_active else 0)
        self._refresh_users_table()

    # ------------------------------------------------------------------
    def refresh(self):
        self.settings = db.get_settings()
        self._refresh_clinic()
        self._refresh_appearance()
        self._refresh_schedule()
        self._refresh_users()
        self._refresh_users_table()