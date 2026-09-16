# -*- coding: utf-8 -*-
"""Clinic accounts page for the Qt version of Dentora.
Revenue (collected from patients) vs expenses and net profit/loss across any
period (today / this month / this year / custom range), reusing the existing
``database`` functions get_clinic_financials / get_expenses_by_category /
get_doctor_commissions_summary.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QDate

import database as db
from . import design
from .components import (
    DataTable,
    StatCard,
    PrimaryButton,
    SecondaryButton,
    DateInput,
)


class AccountsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        today = date.today()
        self.start_date = today.replace(day=1)
        self.end_date = today
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        title = QLabel("حسابات العيادة")
        title.setObjectName("PageTitle")
        root_layout.addWidget(title)

        # --- Quick period buttons (rightmost first under RTL) -----------
        quick_row = QHBoxLayout()
        quick_row.setSpacing(design.SPACING)
        today_btn = SecondaryButton("اليوم")
        today_btn.clicked.connect(self._set_today)
        month_btn = SecondaryButton("هذا الشهر")
        month_btn.clicked.connect(self._set_this_month)
        year_btn = SecondaryButton("هذه السنة")
        year_btn.clicked.connect(self._set_this_year)
        quick_row.addWidget(today_btn)
        quick_row.addWidget(month_btn)
        quick_row.addWidget(year_btn)
        quick_row.addStretch()
        root_layout.addLayout(quick_row)

        # --- Custom range ------------------------------------------------
        custom_row = QHBoxLayout()
        custom_row.setSpacing(design.SPACING)
        custom_row.addWidget(QLabel("من:"))
        self.start_edit = DateInput()
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        self._set_date(self.start_edit, self.start_date)
        custom_row.addWidget(self.start_edit)
        custom_row.addWidget(QLabel("إلى:"))
        self.end_edit = DateInput()
        self.end_edit.setDisplayFormat("yyyy-MM-dd")
        self._set_date(self.end_edit, self.end_date)
        custom_row.addWidget(self.end_edit)
        apply_btn = PrimaryButton("تطبيق الفترة")
        apply_btn.clicked.connect(self._apply_custom_range)
        custom_row.addWidget(apply_btn)
        custom_row.addStretch()
        root_layout.addLayout(custom_row)

        # --- Summary stat cards -----------------------------------------
        stats_row = QHBoxLayout()
        stats_row.setSpacing(design.SPACING * 2)
        self.revenue_card = StatCard("الإيرادات (المحصّل من المرضى)", "0",
                                     value_color=design.SUCCESS_600)
        self.expenses_card = StatCard("المصروفات", "0",
                                      value_color=design.ERROR_600)
        self.profit_card = StatCard("صافي الربح", "0")
        for card in (self.revenue_card, self.expenses_card, self.profit_card):
            stats_row.addWidget(card)
        stats_row.addStretch()
        root_layout.addLayout(stats_row)

        # --- Expenses by category ---------------------------------------
        self._add_section_label(root_layout, "المصروفات حسب التصنيف")
        self.category_table = DataTable()
        self.category_model = QStandardItemModel()
        self.category_model.setHorizontalHeaderLabels(["الفئة", "الإجمالي"])
        self.category_table.setModel(self.category_model)
        self.category_table.configure_columns(stretch=0)
        root_layout.addWidget(self.category_table)

        # --- Doctor commissions -----------------------------------------
        self._add_section_label(root_layout, "عمولات الأطباء في نفس الفترة")
        self.commission_table = DataTable()
        self.commission_model = QStandardItemModel()
        self.commission_model.setHorizontalHeaderLabels(
            ["الطبيب", "عدد الإجراءات", "إجمالي العمولة"])
        self.commission_table.setModel(self.commission_model)
        self.commission_table.configure_columns(stretch=0)
        root_layout.addWidget(self.commission_table, stretch=1)

    @staticmethod
    def _add_section_label(layout, text: str):
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        layout.addWidget(label)

    @staticmethod
    def _set_date(date_edit, d: date):
        date_edit.setDate(QDate(d.year, d.month, d.day))

    # ------------------------------------------------------------------
    def _set_today(self):
        d = date.today()
        self.start_date = self.end_date = d
        self._sync_edits()

    def _set_this_month(self):
        today = date.today()
        self.start_date = today.replace(day=1)
        self.end_date = today
        self._sync_edits()

    def _set_this_year(self):
        today = date.today()
        self.start_date = today.replace(month=1, day=1)
        self.end_date = today
        self._sync_edits()

    def _sync_edits(self):
        self._set_date(self.start_edit, self.start_date)
        self._set_date(self.end_edit, self.end_date)
        self.refresh()

    def _apply_custom_range(self):
        qd = self.start_edit.date()
        self.start_date = date(qd.year(), qd.month(), qd.day())
        qd = self.end_edit.date()
        self.end_date = date(qd.year(), qd.month(), qd.day())
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        start = self.start_date.isoformat()
        end = self.end_date.isoformat()

        financials = db.get_clinic_financials(start, end)
        profit = financials["profit"]
        self.revenue_card.set_value(f"{financials['revenue']:g} جنيه")
        self.expenses_card.set_value(f"{financials['expenses']:g} جنيه")
        self.profit_card.set_value(f"{abs(profit):g} جنيه")
        self.profit_card.title_label.setText(
            "صافي الربح" if profit >= 0 else "صافي الخسارة")
        self.profit_card.set_value_color(
            design.SUCCESS_600 if profit >= 0 else design.ERROR_600)

        by_category = db.get_expenses_by_category(start, end)
        self.category_model.removeRows(0, self.category_model.rowCount())
        for c in by_category:
            self.category_model.appendRow([
                QStandardItem(str(c["category"])),
                QStandardItem(f"{c['total']:g}"),
            ])
        self.category_model.setProperty("category_rows", by_category)

        commissions = db.get_doctor_commissions_summary(start, end)
        self.commission_model.removeRows(0, self.commission_model.rowCount())
        for c in commissions:
            self.commission_model.appendRow([
                QStandardItem(str(c["doctor_name"])),
                QStandardItem(str(c["treatments_count"])),
                QStandardItem(f"{c['total_commission']:g}"),
            ])
        self.commission_model.setProperty("commission_rows", commissions)