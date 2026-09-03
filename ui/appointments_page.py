# -*- coding: utf-8 -*-
"""Appointments page for the Qt version of Dentora.
Provides a day‑based scheduling view with date navigation, doctor filtering,
and add/edit/delete/status management. All data operations reuse the existing
``database`` module (add_appointment / update_appointment / delete_appointment).
"""

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QTimeEdit,
    QSpinBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QTextEdit,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

import database as db
import theme
from . import design
from .components import DataTable, PrimaryButton, SecondaryButton, DateInput


# Status key -> (Arabic label, color). Mirrors theme.APPOINTMENT_STATUSES.
STATUSES = theme.APPOINTMENT_STATUSES


def _fmt_time(appt_time) -> str:
    return str(appt_time or "")


class AppointmentDialog(QDialog):
    """Add / edit an appointment."""

    def __init__(self, appointment=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("موعد جديد" if not appointment else "تعديل موعد")
        self.setModal(True)
        self.resize(460, 520)
        self.appointment = appointment  # dict or None
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)

        # Patient combo
        self.patient_combo = QComboBox()
        patients = db.get_all_patients()
        self._patients = patients
        self._patient_keys = [f"{p['id']} – {p['full_name']}" for p in patients]
        self.patient_combo.addItems(self._patient_keys)
        if self.appointment:
            pid = self.appointment.get("patient_id")
            for i, p in enumerate(patients):
                if p["id"] == pid:
                    self.patient_combo.setCurrentIndex(i)
                    break
        form.addRow("المريض", self.patient_combo)

        # Doctor combo
        self.doctor_combo = QComboBox()
        doctors = db.get_doctors()
        self._doctors = [d["full_name"] for d in doctors]
        self.doctor_combo.addItems(self._doctors)
        if self.appointment and self.appointment.get("doctor_name"):
            idx = self.doctor_combo.findText(self.appointment["doctor_name"])
            if idx >= 0:
                self.doctor_combo.setCurrentIndex(idx)
        form.addRow("الطبيب", self.doctor_combo)

        # Date
        self.date_edit = DateInput()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        if self.appointment and self.appointment.get("appt_date"):
            from PySide6.QtCore import QDate
            d = QDate.fromString(str(self.appointment["appt_date"]), "yyyy-MM-dd")
            if d.isValid():
                self.date_edit.setDate(d)
        form.addRow("التاريخ", self.date_edit)

        # Time
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        if self.appointment and self.appointment.get("appt_time"):
            from PySide6.QtCore import QTime
            t = QTime.fromString(str(self.appointment["appt_time"]), "HH:mm")
            if t.isValid():
                self.time_edit.setTime(t)
        form.addRow("الوقت", self.time_edit)

        # Duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 600)
        self.duration_spin.setSuffix(" دقيقة")
        self.duration_spin.setValue(int(self.appointment.get("duration_minutes") or 30) if self.appointment else 30)
        form.addRow("المدة", self.duration_spin)

        # Status
        self.status_combo = QComboBox()
        self._status_keys = list(STATUSES.keys())
        self._status_labels = [STATUSES[k]["label"] for k in self._status_keys]
        self.status_combo.addItems(self._status_labels)
        if self.appointment:
            key = self.appointment.get("status")
            if key in self._status_keys:
                self.status_combo.setCurrentIndex(self._status_keys.index(key))
        form.addRow("الحالة", self.status_combo)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("ملاحظات (اختياري)")
        self.notes_edit.setMaximumHeight(90)
        if self.appointment and self.appointment.get("notes"):
            self.notes_edit.setPlainText(str(self.appointment["notes"]))
        form.addRow("الملاحظات", self.notes_edit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        idx = self.patient_combo.currentIndex()
        if idx < 0 or idx >= len(self._patients):
            return
        patient_id = self._patients[idx]["id"]
        appt_date = self.date_edit.date().toString("yyyy-MM-dd")
        appt_time = self.time_edit.time().toString("HH:mm")
        duration = self.duration_spin.value()
        doctor_name = self.doctor_combo.currentText() if self.doctor_combo.currentIndex() >= 0 else ""
        status_key = self._status_keys[self.status_combo.currentIndex()]
        notes = self.notes_edit.toPlainText().strip()

        if self.appointment:
            appt_id = self.appointment["id"]
            db.update_appointment(appt_id, appt_date=appt_date, appt_time=appt_time,
                                  duration_minutes=duration, doctor_name=doctor_name, notes=notes)
            db.update_appointment_status(appt_id, status_key)
        else:
            db.add_appointment(patient_id, appt_date, appt_time, doctor_name,
                               status_key, notes, duration)
        self.accept()


class AppointmentsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_date = date.today()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        # Title
        title = QLabel("المواعيد")
        title.setStyleSheet(
            f"font-size: {design.FONT_SIZE + 8}px; font-weight: bold; color: {design.TEXT_COLOR};"
        )
        root_layout.addWidget(title)

        # --- Controls row ------------------------------------------------
        controls = QHBoxLayout()
        controls.setSpacing(design.SPACING * 2)

        prev_btn = SecondaryButton("السابق")
        prev_btn.clicked.connect(self._go_prev_day)
        controls.addWidget(prev_btn)

        self.date_edit = DateInput()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.dateChanged.connect(self._on_date_changed)
        controls.addWidget(self.date_edit)

        next_btn = SecondaryButton("التالي")
        next_btn.clicked.connect(self._go_next_day)
        controls.addWidget(next_btn)

        today_btn = SecondaryButton("اليوم")
        today_btn.clicked.connect(self._go_today)
        controls.addWidget(today_btn)

        controls.addStretch()

        # Doctor filter
        controls.addWidget(QLabel("الطبيب:"))
        self.doctor_filter = QComboBox()
        self.doctor_filter.addItem("الكل")
        for d in db.get_doctors():
            self.doctor_filter.addItem(d["full_name"])
        self.doctor_filter.currentIndexChanged.connect(self.refresh)
        controls.addWidget(self.doctor_filter, stretch=1)

        root_layout.addLayout(controls)

        # --- Table -------------------------------------------------------
        self.table = DataTable()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(
            ["الوقت", "المدة", "المريض", "الطبيب", "الحالة", "الملاحظات", "ID"]
        )
        self.table.setModel(self.model)
        root_layout.addWidget(self.table, stretch=1)

        # --- Action buttons ----------------------------------------------
        actions = QHBoxLayout()
        actions.setSpacing(design.SPACING * 2)
        edit_btn = PrimaryButton("تعديل")
        edit_btn.clicked.connect(self._edit_selected)
        delete_btn = SecondaryButton("حذف")
        delete_btn.clicked.connect(self._delete_selected)
        add_btn = PrimaryButton("+ موعد جديد")
        add_btn.clicked.connect(self._add_new)
        actions.addWidget(add_btn)
        actions.addWidget(edit_btn)
        actions.addWidget(delete_btn)
        actions.addStretch()
        root_layout.addLayout(actions)

    # ------------------------------------------------------------------
    def _go_prev_day(self):
        self.current_date -= timedelta(days=1)
        self._sync_date_edit()

    def _go_next_day(self):
        self.current_date += timedelta(days=1)
        self._sync_date_edit()

    def _go_today(self):
        self.current_date = date.today()
        self._sync_date_edit()

    def _sync_date_edit(self):
        from PySide6.QtCore import QDate
        self.date_edit.setDate(QDate(self.current_date.year, self.current_date.month,
                                     self.current_date.day))
        self.refresh()

    def _on_date_changed(self):
        qdate = self.date_edit.date()
        self.current_date = date(qdate.year(), qdate.month(), qdate.day())
        self.refresh()

    # ------------------------------------------------------------------
    @staticmethod
    def _status_key_to_label(key):
        info = STATUSES.get(key)
        return info["label"] if info else str(key)

    def refresh(self):
        appt_date = self.current_date.isoformat()
        appts = db.get_appointments(appt_date)

        # Doctor filter
        doctor = self.doctor_filter.currentText()
        if doctor and doctor != "الكل":
            appts = [a for a in appts if a.get("doctor_name") == doctor]

        self.model.removeRows(0, self.model.rowCount())
        for a in appts:
            row = [
                _fmt_time(a.get("appt_time")),
                str(a.get("duration_minutes") or ""),
                str(a.get("full_name") or ""),
                str(a.get("doctor_name") or ""),
                self._status_key_to_label(a.get("status")),
                str(a.get("notes") or ""),
                str(a.get("id") or ""),
            ]
            item_row = [QStandardItem(v) for v in row]
            # Hide the ID column by shrinking it (kept for reference)
            self.model.appendRow(item_row)
        self.model.setProperty("appts", appts)

    def _selected_appt(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        appts = self.model.property("appts")
        if appts and 0 <= row < len(appts):
            return appts[row]
        return None

    def _add_new(self):
        dlg = AppointmentDialog(appointment=None, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _edit_selected(self):
        appt = self._selected_appt()
        if not appt:
            return
        dlg = AppointmentDialog(appointment=appt, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_selected(self):
        appt = self._selected_appt()
        if not appt:
            return
        from .components import ask_confirmation
        if ask_confirmation(self, "حذف موعد", "هل تريد حذف هذا الموعد؟"):
            db.delete_appointment(appt["id"])
            self.refresh()
