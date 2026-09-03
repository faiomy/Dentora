# -*- coding: utf-8 -*-
"""Settings page for the Qt version of Dentora.
Provides category navigation and panels for clinic info, schedule/holidays,
security, and users. Reuses the existing ``database`` functions.
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
    DateInput,
    show_error,
    show_info,
)

WEEKDAY_NAMES = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
                 4: "الجمعة", 5: "السبت", 6: "الأحد"}


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = db.get_settings()
        self._build_ui()
        self._refresh_clinic()
        self._refresh_schedule()
        self._refresh_users()
        self._refresh_users_table()

    def _build_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING, design.SPACING,
                                       design.SPACING, design.SPACING)
        root_layout.setSpacing(design.SPACING * 2)

        # Sidebar categories
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(180)
        self.settings = self.settings or {}
        categories = ["بيانات العيادة", "المواعيد والإجازات", "الأمان", "المستخدمون"]
        for c in categories:
            self.category_list.addItem(c)
        self.category_list.currentRowChanged.connect(self._switch_category)
        root_layout.addWidget(self.category_list)

        # Stacked panels
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        self.clinic_panel = self._build_clinic_panel()
        self.schedule_panel = self._build_schedule_panel()
        self.security_panel = self._build_security_panel()
        self.users_panel = self._build_users_panel()

        self.stack.addWidget(self.clinic_panel)
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
        phone_row.addWidget(self.new_phone_edit)
        phone_row.addWidget(add_phone_btn)
        phone_row.addWidget(del_phone_btn)
        layout.addLayout(phone_row)

        return panel

    def _labeled(self, text, widget):
        row = QWidget()
        lay = QVBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lab = QLabel(text)
        lab.setStyleSheet(f"font-weight: bold; color: {design.TEXT_SECONDARY_COLOR};")
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
            self.phones_list.addItem(QListWidgetItem(str(p["phone_number"])))

    def _save_clinic(self):
        db.update_settings(
            clinic_name=self.clinic_name_edit.text().strip(),
            clinic_address=self.clinic_address_edit.text().strip(),
            tax_card_number=self.tax_card_edit.text().strip(),
        )
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
        user_row.addWidget(self.pw_user_combo)
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
    # Users (read-only list)
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
        return panel

    def _refresh_users_table(self):
        self.users_model.removeRows(0, self.users_model.rowCount())
        for u in db.get_all_users():
            self.users_model.appendRow([
                QStandardItem(str(u.get("username") or "")),
                QStandardItem(str(u.get("full_name") or "")),
                QStandardItem(db.ROLE_LABELS.get(u.get("role"), u.get("role") or "")),
                QStandardItem("نعم" if u.get("active") else "لا"),
            ])

    def refresh(self):
        self.settings = db.get_settings()
        self._refresh_clinic()
        self._refresh_schedule()
        self._refresh_users()
        self._refresh_users_table()
