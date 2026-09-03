# -*- coding: utf-8 -*-
"""Real Dashboard page for the Qt version of Dentora.
Shows at-a-glance statistics and today's / upcoming appointments using the
existing ``database`` module. No new backend functionality is introduced.
"""

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

import database as db
from . import design
from .components import StatCard, DataTable, SecondaryButton


def _today_iso() -> str:
    return date.today().isoformat()


def _currency(amount) -> str:
    try:
        return f"{float(amount):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


class DashboardPage(QWidget):
    """Landing page showing real clinic summary data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        # Page title
        title = QLabel("الرئيسية")
        title.setStyleSheet(
            f"font-size: {design.FONT_SIZE + 8}px; font-weight: bold; color: {design.TEXT_COLOR};"
        )
        root_layout.addWidget(title)

        # Stat cards
        self.cards = {}
        stat_row = QHBoxLayout()
        stat_row.setSpacing(design.SPACING * 2)

        self.cards["today_appts"] = StatCard("مواعيد اليوم", "0")
        self.cards["patients"] = StatCard("إجمالي المرضى", "0")
        self.cards["today_revenue"] = StatCard("إيراد اليوم", "0")
        self.cards["upcoming"] = StatCard("مواعيد قادمة", "0")

        for card in self.cards.values():
            stat_row.addWidget(card)

        root_layout.addLayout(stat_row)

        # Today's appointments table
        today_section = QLabel("مواعيد اليوم")
        today_section.setStyleSheet(
            f"font-size: {design.FONT_SIZE + 4}px; font-weight: bold; color: {design.TEXT_COLOR};"
        )
        root_layout.addWidget(today_section)

        self.today_table = DataTable()
        self.today_model = QStandardItemModel()
        self.today_model.setHorizontalHeaderLabels(["الوقت", "المريض", "الطبيب", "الحالة"])
        self.today_table.setModel(self.today_model)
        root_layout.addWidget(self.today_table, stretch=3)

        # Upcoming appointments table
        upcoming_section = QLabel("المواعيد القادمة")
        upcoming_section.setStyleSheet(
            f"font-size: {design.FONT_SIZE + 4}px; font-weight: bold; color: {design.TEXT_COLOR};"
        )
        root_layout.addWidget(upcoming_section)

        self.upcoming_table = DataTable()
        self.upcoming_model = QStandardItemModel()
        self.upcoming_model.setHorizontalHeaderLabels(
            ["التاريخ", "الوقت", "المريض", "الطبيب", "الحالة"]
        )
        self.upcoming_table.setModel(self.upcoming_model)
        root_layout.addWidget(self.upcoming_table, stretch=3)

        # Refresh button
        refresh_btn = SecondaryButton("تحديث")
        refresh_btn.clicked.connect(self.refresh)
        root_layout.addWidget(refresh_btn, alignment=Qt.AlignLeft)

    # ------------------------------------------------------------------
    def refresh(self):
        today = _today_iso()

        # --- Stat cards ------------------------------------------------
        today_appts = db.get_appointments(today)
        all_patients = db.get_all_patients()
        financials = db.get_clinic_financials(today, today)

        all_appts = db.get_appointments()
        upcoming = [a for a in all_appts if (a.get("appt_date") or "") > today]
        upcoming = sorted(upcoming, key=lambda a: (a.get("appt_date") or "", a.get("appt_time") or ""))[:20]

        self.cards["today_appts"].set_value(str(len(today_appts)))
        self.cards["patients"].set_value(str(len(all_patients)))
        self.cards["today_revenue"].set_value(_currency(financials.get("revenue", 0)))
        self.cards["upcoming"].set_value(str(len(upcoming)))

        self._fill_model(self.today_model, today_appts, include_date=False)
        self._fill_model(self.upcoming_model, upcoming, include_date=True)

    # ------------------------------------------------------------------
    @staticmethod
    def _fill_model(model: QStandardItemModel, appointments, include_date: bool):
        model.removeRows(0, model.rowCount())
        for appt in appointments:
            row = []
            if include_date:
                row.append(str(appt.get("appt_date") or ""))
            row.append(str(appt.get("appt_time") or ""))
            row.append(str(appt.get("full_name") or ""))
            row.append(str(appt.get("doctor_name") or ""))
            row.append(str(appt.get("status") or ""))
            items = [QStandardItem(v) for v in row]
            model.appendRow(items)
        model.setHorizontalHeaderLabels(
            ["التاريخ", "الوقت", "المريض", "الطبيب", "الحالة"]
            if include_date else ["الوقت", "المريض", "الطبيب", "الحالة"]
        )
