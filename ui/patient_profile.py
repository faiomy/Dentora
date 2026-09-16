# -*- coding: utf-8 -*-
"""Patient profile for the Qt version of Dentora.

A single patient workspace opened from the patients list, organized in five
tabs that mirror the legacy CTk patient detail screen (``pages/patients_page.py``):

1. **الزيارات** - past/upcoming appointments (add/edit/cancel) plus follow-up
   visit notes.
2. **خريطة الأسنان** - functional odontogram (``ui.tooth_chart``).
3. **الحسابات** - patient charges / payments / discount / balance.
4. **بيانات المريض** - read-only view of the full record (no in-place edits).
5. **تعديل البيانات** - dedicated edit form (explicit Save / Cancel).

Every write goes through the existing ``database`` module; no sample or
static data anywhere.
"""

from datetime import date

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFormLayout,
    QPlainTextEdit,
    QLineEdit,
    QDoubleSpinBox,
    QScrollArea,
    QTabWidget,
    QFrame,
)

import database as db
from . import design
from .constants import ltr, status_key_to_label
from .components import (
    DataTable,
    PrimaryButton,
    SecondaryButton,
    DangerButton,
    TextInput,
    DateInput,
    FieldLabel,
    Card,
    StatCard,
    show_info,
    show_error,
    ask_confirmation,
)
from .tooth_chart import ToothChartWidget
from .appointments_page import AppointmentDialog


# ---------------------------------------------------------------------------
# Patient edit form (shared by the standalone PatientDialog and the profile's
# "تعديل البيانات" tab, so there is exactly one definition of the fields).
# ---------------------------------------------------------------------------
class PatientForm(QWidget):
    """The patient data-entry form. Used both as a modal dialog and inside
    the profile edit tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        self.name_edit = TextInput()
        self.name_edit.textChanged.connect(lambda _: self.name_edit.set_error(False))
        form.addRow(FieldLabel("الاسم", required=True), self.name_edit)

        self.phone_edit = TextInput(placeholder="رقم الهاتف")
        form.addRow(FieldLabel("الهاتف"), self.phone_edit)

        self.birth_edit = DateInput()
        self.birth_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow(FieldLabel("تاريخ الميلاد"), self.birth_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "ذكر", "أنثى"])
        form.addRow(FieldLabel("النوع"), self.gender_combo)

        self.address_edit = TextInput(placeholder="العنوان")
        form.addRow(FieldLabel("العنوان"), self.address_edit)

        self.occupation_edit = TextInput(placeholder="المهنة")
        form.addRow(FieldLabel("المهنة"), self.occupation_edit)

        self.nationality_edit = TextInput(placeholder="الجنسية")
        form.addRow(FieldLabel("الجنسية"), self.nationality_edit)

        self.family_edit = TextInput(placeholder="رقم العائلة")
        form.addRow(FieldLabel("رقم العائلة"), self.family_edit)

        self.allergies_edit = TextInput(placeholder="الحساسية")
        form.addRow(FieldLabel("الحساسية"), self.allergies_edit)

        self.notes_edit = TextInput(placeholder="ملاحظات طبية")
        form.addRow(FieldLabel("ملاحظات طبية"), self.notes_edit)

    # ------------------------------------------------------------------
    def load(self, patient=None):
        p = patient or {}
        self.name_edit.setText(str(p.get("full_name") or ""))
        self.phone_edit.setText(str(p.get("phone") or ""))
        birth = str(p.get("birth_date") or "")
        if birth:
            d = QDate.fromString(birth, "yyyy-MM-dd")
            if d.isValid():
                self.birth_edit.setDate(d)
        gender = str(p.get("gender") or "")
        self.gender_combo.setCurrentIndex(0)
        if gender:
            idx = self.gender_combo.findText(gender)
            if idx >= 0:
                self.gender_combo.setCurrentIndex(idx)
            else:
                # Preserve legacy values already stored in the database.
                self.gender_combo.addItem(gender)
                self.gender_combo.setCurrentIndex(self.gender_combo.count() - 1)
        self.address_edit.setText(str(p.get("address") or ""))
        self.occupation_edit.setText(str(p.get("occupation") or ""))
        self.nationality_edit.setText(str(p.get("nationality") or ""))
        self.family_edit.setText(str(p.get("family_id") or ""))
        self.allergies_edit.setText(str(p.get("allergies") or ""))
        self.notes_edit.setText(str(p.get("medical_notes") or ""))

    def validate(self):
        """Returns the offending widget (or None when valid) and flags it."""
        if not self.name_edit.text().strip():
            self.name_edit.set_error(True)
            self.name_edit.setFocus()
            return self.name_edit
        return None

    def get_data(self):
        return {
            "full_name": self.name_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "birth_date": self.birth_edit.date().toString("yyyy-MM-dd"),
            "gender": self.gender_combo.currentText().strip(),
            "address": self.address_edit.text().strip(),
            "occupation": self.occupation_edit.text().strip(),
            "nationality": self.nationality_edit.text().strip(),
            "family_id": self.family_edit.text().strip(),
            "allergies": self.allergies_edit.text().strip(),
            "medical_notes": self.notes_edit.text().strip(),
        }


# ---------------------------------------------------------------------------
# Read-only patient data tab
# ---------------------------------------------------------------------------
class PatientInfoTab(QWidget):
    """Read-only full record. Editing only through the dedicated edit tab."""

    _FIELDS = (
        ("full_name", "الاسم"),
        ("phone", "الهاتف"),
        ("birth_date", "تاريخ الميلاد"),
        ("gender", "النوع"),
        ("address", "العنوان"),
        ("occupation", "المهنة"),
        ("nationality", "الجنسية"),
        ("family_id", "رقم العائلة"),
        ("allergies", "الحساسية"),
        ("medical_notes", "ملاحظات طبية"),
    )

    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self._labels = {}
        self._build_ui()
        self.reload()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)

        title = QLabel("بيانات المريض")
        title.setObjectName("SectionTitle")
        v.addWidget(title)

        self.extra_line = QLabel("")
        self.extra_line.setObjectName("PageSubtitle")
        self.extra_line.setWordWrap(True)
        v.addWidget(self.extra_line)

        card = Card(parent=container, padding=True)
        form = QFormLayout(card)
        form.setSpacing(design.SPACING_MD)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for key, label in self._FIELDS:
            value = QLabel("")
            value.setObjectName("PageSubtitle")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            value.setWordWrap(True)
            form.addRow(FieldLabel(label), value)
            self._labels[key] = value
        v.addWidget(card)
        v.addStretch()

        scroll.setWidget(container)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

    def reload(self):
        try:
            patient = db.get_patient(self.patient_id) or {}
        except Exception:
            patient = {}
        for key, _ in self._FIELDS:
            self._labels[key].setText(str(patient.get(key) or ""))
        extra = []
        try:
            phones = db.get_patient_phones(self.patient_id)
            if phones:
                extra.append("أرقام إضافية: " + "، ".join(
                    ltr(str(p.get("phone_number") or "")) for p in phones))
        except Exception:
            pass
        try:
            files = db.get_patient_files(self.patient_id)
            extra.append(f"ملفات مرفقة: {len(files)}")
        except Exception:
            pass
        self.extra_line.setText("  •  ".join(extra) if extra else "")


# ---------------------------------------------------------------------------
# Small entry dialogs (payment / manual charge / edit amount / visit note)
# ---------------------------------------------------------------------------
class _TxDialog(QDialog):
    """Amount + date + description entry used for payments and manual charges."""

    def __init__(self, title, dialog_label, parent=None, with_discount=False,
                 initial_amount=0.0, initial_discount=0.0, description=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(420, 240)
        self._with_discount = with_discount
        self._discount_changed = False
        self._build_ui(dialog_label, initial_amount, initial_discount, description)

    def _build_ui(self, dialog_label, amount, discount, description):
        form = QFormLayout(self)
        form.setSpacing(10)
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10_000_000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSingleStep(10)
        self.amount_spin.setValue(amount)
        form.addRow(FieldLabel(dialog_label, required=True), self.amount_spin)

        self.date_edit = DateInput()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow(FieldLabel("التاريخ"), self.date_edit)

        self.discount_spin = None
        if self._with_discount:
            self.discount_spin = QDoubleSpinBox()
            self.discount_spin.setRange(0, 10_000_000)
            self.discount_spin.setDecimals(2)
            self.discount_spin.setSingleStep(10)
            self.discount_spin.setValue(discount)
            self.discount_spin.valueChanged.connect(lambda _: self._mark_discount())
            form.addRow(FieldLabel("الخصم"), self.discount_spin)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("الوصف (اختياري)")
        self.desc_edit.setText(description)
        form.addRow(FieldLabel("الوصف"), self.desc_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _mark_discount(self):
        self._discount_changed = True

    def _save(self):
        if self.amount_spin.value() <= 0:
            self.amount_spin.setFocus()
            show_info(self, "مبلغ غير صالح", "أدخل مبلغًا أكبر من صفر.")
            return
        self.accept()

    @property
    def amount(self):
        return round(self.amount_spin.value(), 2)

    @property
    def discount(self):
        return round(self.discount_spin.value(), 2) if self.discount_spin else 0.0

    @property
    def amount_changed_only(self):
        return bool(self.discount_spin) and not self._discount_changed

    @property
    def tx_date(self):
        return self.date_edit.date().toString("yyyy-MM-dd")

    @property
    def description(self):
        return self.desc_edit.text().strip()


class _VisitDialog(QDialog):
    """Follow-up visit note entry (date + doctor + notes)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة زيارة متابعة")
        self.setModal(True)
        self.resize(420, 260)
        form = QFormLayout(self)
        form.setSpacing(10)

        self.date_edit = DateInput()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow(FieldLabel("التاريخ"), self.date_edit)

        self.doctor_combo = QComboBox()
        self.doctor_combo.addItem("")
        for d in db.get_doctors():
            self.doctor_combo.addItem(str(d.get("full_name") or ""))
        form.addRow(FieldLabel("الطبيب"), self.doctor_combo)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("ملاحظات الزيارة")
        self.notes_edit.setFixedHeight(80)
        form.addRow(FieldLabel("الملاحظات"), self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        if not self.notes_edit.toPlainText().strip():
            self.notes_edit.setFocus()
            show_info(self, "ملاحظة فارغة", "اكتب ملاحظة الزيارة أولًا.")
            return
        self.accept()

    @property
    def visit_date(self):
        return self.date_edit.date().toString("yyyy-MM-dd")

    @property
    def doctor_name(self):
        return self.doctor_combo.currentText().strip()

    @property
    def notes(self):
        return self.notes_edit.toPlainText().strip()


# ---------------------------------------------------------------------------
# Visits / appointments tab
# ---------------------------------------------------------------------------
class AppointmentsTab(QWidget):
    """Past & upcoming appointments plus follow-up visit notes."""

    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(design.SPACING_MD)

        # -- upcoming appointments --------------------------------------
        title = QLabel("المواعيد القادمة")
        title.setObjectName("SectionTitle")
        v.addWidget(title)

        self.upcoming_table = DataTable()
        self.upcoming_model = QStandardItemModel()
        self.upcoming_model.setHorizontalHeaderLabels(
            ["التاريخ", "الوقت", "المدة", "الطبيب", "الحالة", "الملاحظات"])
        self.upcoming_table.setModel(self.upcoming_model)
        self.upcoming_table.configure_columns(stretch=3, exclude_center=(5,))
        self.upcoming_table.setMinimumHeight(150)
        v.addWidget(self.upcoming_table)

        row = QHBoxLayout()
        new_btn = PrimaryButton("+ موعد جديد")
        new_btn.clicked.connect(self._add_appointment)
        edit_btn = SecondaryButton("تعديل الموعد")
        edit_btn.clicked.connect(self._edit_appointment)
        cancel_btn = SecondaryButton("إلغاء الموعد")
        cancel_btn.clicked.connect(self._cancel_appointment)
        row.addWidget(new_btn)
        row.addWidget(edit_btn)
        row.addWidget(cancel_btn)
        row.addStretch()
        v.addLayout(row)

        # -- past appointments ------------------------------------------
        title = QLabel("الزيارات السابقة")
        title.setObjectName("SectionTitle")
        v.addWidget(title)

        self.past_table = DataTable()
        self.past_model = QStandardItemModel()
        self.past_model.setHorizontalHeaderLabels(
            ["التاريخ", "الوقت", "الدكتور", "الحالة", "الملاحظات"])
        self.past_table.setModel(self.past_model)
        self.past_table.configure_columns(stretch=2, exclude_center=(4,))
        self.past_table.setMinimumHeight(150)
        v.addWidget(self.past_table)

        # -- follow-up visits -------------------------------------------
        title = QLabel("زيارات المتابعة")
        title.setObjectName("SectionTitle")
        v.addWidget(title)

        self.visits_table = DataTable()
        self.visits_model = QStandardItemModel()
        self.visits_model.setHorizontalHeaderLabels(["التاريخ", "الطبيب", "الملاحظات"])
        self.visits_table.setModel(self.visits_model)
        self.visits_table.configure_columns(stretch=2)
        self.visits_table.setMinimumHeight(150)
        v.addWidget(self.visits_table)

        row = QHBoxLayout()
        add_visit_btn = PrimaryButton("+ إضافة زيارة")
        add_visit_btn.clicked.connect(self._add_visit)
        del_visit_btn = SecondaryButton("حذف الزيارة")
        del_visit_btn.clicked.connect(self._delete_visit)
        row.addWidget(add_visit_btn)
        row.addWidget(del_visit_btn)
        row.addStretch()
        v.addLayout(row)

        v.addStretch()
        scroll.setWidget(container)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

    # ------------------------------------------------------------------
    def refresh(self):
        today = date.today().isoformat()
        appts = [a for a in db.get_appointments()
                 if a.get("patient_id") == self.patient_id]

        upcoming = sorted(
            (a for a in appts if (a.get("appt_date") or "") >= today),
            key=lambda a: (a.get("appt_date") or "", a.get("appt_time") or ""))
        past = sorted(
            (a for a in appts if (a.get("appt_date") or "") < today),
            key=lambda a: (a.get("appt_date") or "", a.get("appt_time") or ""),
            reverse=True)

        self._fill_table(self.upcoming_model, upcoming,
                         ["appt_date", "appt_time", "duration_minutes",
                          "doctor_name", "status", "notes"])
        self._fill_table(self.past_model, past,
                         ["appt_date", "appt_time", "doctor_name", "status", "notes"])

        visits = db.get_visits(self.patient_id)
        visits = sorted(visits, key=lambda v: (v.get("visit_date") or ""),
                        reverse=True)
        self._fill_table(self.visits_model, visits,
                         ["visit_date", "doctor_name", "notes"])

    @staticmethod
    def _fill_table(model, rows, keys):
        model.removeRows(0, model.rowCount())
        for r in rows:
            values = []
            for key in keys:
                if key == "duration_minutes":
                    values.append(f"{int(r.get(key) or 0)} د" if r.get(key) else "")
                elif key == "status":
                    values.append(status_key_to_label(r.get(key)))
                elif key == "notes":
                    values.append(str(r.get(key) or ""))
                else:
                    values.append(str(r.get(key) or ""))
            model.appendRow([QStandardItem(v) for v in values])
        model.setProperty("rows", rows)

    # ------------------------------------------------------------------
    def _selected_appt(self):
        rows = self.upcoming_model.property("rows") or []
        idx = self.upcoming_table.currentIndex()
        if not idx.isValid() or not (0 <= idx.row() < len(rows)):
            return None
        return rows[idx.row()]

    def _add_appointment(self):
        dlg = AppointmentDialog(parent=self)
        for i, p in enumerate(dlg._patients):
            if p["id"] == self.patient_id:
                dlg.patient_combo.setCurrentIndex(i)
                break
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _edit_appointment(self):
        appt = self._selected_appt()
        if not appt:
            return
        dlg = AppointmentDialog(appointment=appt, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _cancel_appointment(self):
        appt = self._selected_appt()
        if not appt:
            return
        if ask_confirmation(self, "إلغاء موعد",
                            f"هل تريد حذف موعد «{appt.get('appt_date')}»؟"):
            db.delete_appointment(appt["id"])
            self.refresh()

    def _add_visit(self):
        dlg = _VisitDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            db.add_visit(self.patient_id, dlg.notes,
                         visit_date=dlg.visit_date, doctor_name=dlg.doctor_name)
            self.refresh()

    def _delete_visit(self):
        rows = self.visits_model.property("rows") or []
        idx = self.visits_table.currentIndex()
        if not idx.isValid() or not (0 <= idx.row() < len(rows)):
            return
        if ask_confirmation(self, "حذف زيارة",
                            "هل تريد حذف ملاحظة هذه الزيارة؟"):
            db.delete_visit(rows[idx.row()]["id"])
            self.refresh()


# ---------------------------------------------------------------------------
# Financial account tab
# ---------------------------------------------------------------------------
class FinancesTab(QWidget):
    """Patient account: charges, payments, discounts, running balance."""

    _COLUMNS = ["التاريخ", "النوع", "المبلغ", "الخصم", "الصافي", "الوصف"]
    _STRETCH = 4
    _EXCLUDE = (5,)

    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(design.SPACING_MD)

        # Summary cards
        cards = QHBoxLayout()
        cards.setSpacing(design.SPACING_MD)
        self.charges_card = StatCard("إجمالي المستحق", value_color=design.TEXT_PRIMARY)
        self.paid_card = StatCard("المدفوع", value_color=design.SUCCESS_600)
        self.balance_card = StatCard("المتبقي")
        for c in (self.charges_card, self.paid_card, self.balance_card):
            cards.addWidget(c, stretch=1)
        v.addLayout(cards)

        title = QLabel("كشف الحساب")
        title.setObjectName("SectionTitle")
        v.addWidget(title)

        self.table = DataTable()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(self._COLUMNS)
        self.table.setModel(self.model)
        self.table.configure_columns(stretch=self._STRETCH, exclude_center=self._EXCLUDE)
        v.addWidget(self.table, stretch=1)

        row = QHBoxLayout()
        pay_btn = PrimaryButton("+ دفعة")
        pay_btn.clicked.connect(self._add_payment)
        charge_btn = SecondaryButton("+ مستحق يدوي")
        charge_btn.clicked.connect(self._add_charge)
        edit_btn = SecondaryButton("تعديل المبلغ")
        edit_btn.clicked.connect(self._edit_selected)
        del_btn = DangerButton("حذف")
        del_btn.clicked.connect(self._delete_selected)
        row.addWidget(pay_btn)
        row.addWidget(charge_btn)
        row.addWidget(edit_btn)
        row.addWidget(del_btn)
        row.addStretch()
        v.addLayout(row)

    # ------------------------------------------------------------------
    def refresh(self):
        try:
            balance = db.get_patient_balance(self.patient_id)
        except Exception:
            balance = {"total_charges": 0, "total_paid": 0, "balance": 0}
        self.charges_card.set_value(str(round(balance.get("total_charges") or 0, 2)))
        self.paid_card.set_value(str(round(balance.get("total_paid") or 0, 2)))
        remaining = round(balance.get("balance") or 0, 2)
        self.balance_card.set_value(str(remaining))
        self.balance_card.set_value_color(
            design.SUCCESS_600 if remaining <= 0 else design.ERROR_600)

        txs = db.get_transactions(self.patient_id)
        self.model.removeRows(0, self.model.rowCount())
        for tx in txs:
            tx_type = tx.get("tx_type")
            amount = round(float(tx.get("amount") or 0), 2)
            discount = round(float(tx.get("discount_amount") or 0), 2)
            net = amount - discount if tx_type == "charge" else amount
            row = [
                QStandardItem(str(tx.get("tx_date") or "")),
                QStandardItem("مستحق" if tx_type == "charge" else "دفعة"),
                QStandardItem(ltr(str(amount))),
                QStandardItem(ltr(str(discount)) if tx_type == "charge" and discount else ""),
                QStandardItem(ltr(str(net))),
                QStandardItem(str(tx.get("description") or "")),
            ]
            if tx_type == "payment":
                row[4].setForeground(QColor(design.SUCCESS_600))
            self.model.appendRow(row)
        self.model.setProperty("rows", txs)

    # ------------------------------------------------------------------
    def _selected_tx(self):
        rows = self.model.property("rows") or []
        idx = self.table.currentIndex()
        if not idx.isValid() or not (0 <= idx.row() < len(rows)):
            return None
        return rows[idx.row()]

    def _add_payment(self):
        dlg = _TxDialog("دفعة جديدة", "المبلغ", parent=self)
        if dlg.exec() == QDialog.Accepted:
            try:
                db.add_transaction(self.patient_id, "payment", dlg.amount,
                                   description=dlg.description, tx_date=dlg.tx_date)
            except Exception as exc:  # pragma: no cover - defensive
                show_error(self, "تعذّر الحفظ", f"حدث خطأ:\n{exc}")
                return
            self.refresh()

    def _add_charge(self):
        dlg = _TxDialog("مستحق يدوي", "المبلغ", parent=self)
        if dlg.exec() == QDialog.Accepted:
            try:
                db.add_manual_treatment_record(
                    self.patient_id, dlg.description or "مستحق يدوي", dlg.amount,
                    treatment_date=dlg.tx_date)
            except Exception as exc:  # pragma: no cover - defensive
                show_error(self, "تعذّر الحفظ", f"حدث خطأ:\n{exc}")
                return
            self.refresh()

    def _edit_selected(self):
        tx = self._selected_tx()
        if not tx:
            return
        is_charge = tx.get("tx_type") == "charge"
        dlg = _TxDialog(
            "تعديل الحركة", "المبلغ", parent=self,
            with_discount=is_charge,
            initial_amount=float(tx.get("amount") or 0),
            initial_discount=float(tx.get("discount_amount") or 0),
            description=str(tx.get("description") or ""))
        if dlg.exec() == QDialog.Accepted:
            try:
                db.update_transaction_amount(tx["id"], dlg.amount)
                if is_charge and not dlg.amount_changed_only:
                    db.update_transaction_discount(tx["id"], dlg.discount)
            except Exception as exc:  # pragma: no cover - defensive
                show_error(self, "تعذّر الحفظ", f"حدث خطأ:\n{exc}")
                return
            self.refresh()

    def _delete_selected(self):
        tx = self._selected_tx()
        if not tx:
            return
        if ask_confirmation(self, "حذف حركة",
                            "هل تريد حذف هذه الحركة المالية؟ سيُحذف سجل المعالجة المرتبط إن وُجد."):
            try:
                db.delete_transaction(tx["id"])
            except Exception as exc:  # pragma: no cover - defensive
                show_error(self, "تعذّر الحذف", f"حدث خطأ:\n{exc}")
                return
            self.refresh()


# ---------------------------------------------------------------------------
# The profile dialog itself
# ---------------------------------------------------------------------------
class PatientProfileDialog(QDialog):
    """Five-tab patient workspace opened from the patients list."""

    def __init__(self, patient, parent=None):
        super().__init__(parent)
        self.patient_id = patient.get("id") or patient.get("patient_id")
        self.setModal(True)
        self.resize(960, 720)
        self._build_ui()
        self._reload_header()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(design.SPACING_MD)

        self.header_name = QLabel("")
        self.header_name.setObjectName("PageTitle")
        root.addWidget(self.header_name)

        self.header_sub = QLabel("")
        self.header_sub.setObjectName("PageSubtitle")
        self.header_sub.setWordWrap(True)
        root.addWidget(self.header_sub)

        self.tabs = QTabWidget()
        self.visits_tab = AppointmentsTab(self.patient_id)
        self.tabs.addTab(self.visits_tab, "الزيارات")

        self.finance_tab = FinancesTab(self.patient_id)
        self.tabs.addTab(self.finance_tab, "الحسابات")

        # المعالجة الجديدة على شارت الأسنان بتنشئ "مستحق" مالي - لذلك يعاود
        # الحسابات بعد إغلاق حوار أي سن
        birth = ""
        try:
            patient = db.get_patient(self.patient_id) or {}
            birth = str(patient.get("birth_date") or "")
        except Exception:
            pass
        self.chart_tab = ToothChartWidget(self.patient_id, birth_date=birth,
                                          on_changed=self._refresh_finance)
        self.tabs.addTab(self.chart_tab, "خريطة الأسنان")

        self.info_tab = PatientInfoTab(self.patient_id)
        self.tabs.addTab(self.info_tab, "بيانات المريض")

        self.edit_tab = QWidget()
        edit_layout = QVBoxLayout(self.edit_tab)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("تعديل بيانات المريض")
        title.setObjectName("SectionTitle")
        edit_layout.addWidget(title)
        self.edit_form = PatientForm(parent=self.edit_tab)
        self.edit_form.load(db.get_patient(self.patient_id) or {})
        edit_layout.addWidget(self.edit_form)
        row = QHBoxLayout()
        save_btn = PrimaryButton("حفظ")
        save_btn.clicked.connect(self._save_edit)
        cancel_btn = SecondaryButton("إلغاء")
        cancel_btn.clicked.connect(self._reload_edit_form)
        row.addWidget(save_btn)
        row.addWidget(cancel_btn)
        row.addStretch()
        edit_layout.addLayout(row)
        edit_layout.addStretch()
        self.tabs.addTab(self.edit_tab, "تعديل البيانات")

        root.addWidget(self.tabs, stretch=1)

        actions = QHBoxLayout()
        close_btn = SecondaryButton("إغلاق")
        close_btn.clicked.connect(self.accept)
        actions.addStretch()
        actions.addWidget(close_btn)
        root.addLayout(actions)

    # ------------------------------------------------------------------
    def _reload_header(self):
        try:
            p = db.get_patient(self.patient_id) or {}
        except Exception:
            p = {}
        name = str(p.get("full_name") or "")
        self.setWindowTitle(f"ملف المريض — {name}")
        self.header_name.setText(name)
        parts = []
        if p.get("phone"):
            parts.append(ltr(str(p["phone"])))
        if p.get("gender"):
            parts.append(str(p["gender"]))
        if p.get("birth_date"):
            parts.append(str(p["birth_date"]))
        self.header_sub.setText("  •  ".join(parts))

    def _reload_edit_form(self):
        self.edit_form.load(db.get_patient(self.patient_id) or {})

    def _save_edit(self):
        if self.edit_form.validate() is not None:
            return
        data = self.edit_form.get_data()
        try:
            db.update_patient(self.patient_id, **data)
        except Exception as exc:  # pragma: no cover - defensive
            show_error(self, "تعذّر الحفظ", f"حدث خطأ:\n{exc}")
            return
        self._reload_header()
        self.info_tab.reload()
        show_info(self, "تم الحفظ", "تم حفظ بيانات المريض.")

    def _refresh_finance(self):
        self.finance_tab.refresh()