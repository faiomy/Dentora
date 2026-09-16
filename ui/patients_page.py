# -*- coding: utf-8 -*-
"""Patients page for the Qt version of Dentora.
Provides a searchable patient list plus two distinct workflows:
- A read-only *profile* view (PatientProfileDialog) with the patient's full
  record and recent appointments;
- A separate *edit* dialog (PatientDialog) - viewing never edits in place,
  and every edit/delete is an explicit, confirmed action.
All data operations reuse the existing ``database`` module.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

import database as db
from . import design
from .constants import ltr, status_key_to_label
from .components import (
    DataTable,
    PrimaryButton,
    SecondaryButton,
    TextInput,
    DateInput,
    FieldLabel,
    show_info,
)


class PatientDialog(QDialog):
    """Add / edit a patient (a dedicated editing step - separate from viewing)."""

    def __init__(self, patient=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مريض جديد" if not patient else "تعديل بيانات المريض")
        self.setModal(True)
        self.resize(520, 620)
        self.patient = patient
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)

        p = self.patient or {}

        self.name_edit = TextInput()
        self.name_edit.setText(str(p.get("full_name") or ""))
        self.name_edit.textChanged.connect(lambda _: self.name_edit.set_error(False))
        form.addRow(FieldLabel("الاسم", required=True), self.name_edit)

        self.phone_edit = TextInput(placeholder="رقم الهاتف")
        self.phone_edit.setText(str(p.get("phone") or ""))
        form.addRow(FieldLabel("الهاتف"), self.phone_edit)

        self.birth_edit = DateInput()
        self.birth_edit.setDisplayFormat("yyyy-MM-dd")
        birth = str(p.get("birth_date") or "")
        if birth:
            from PySide6.QtCore import QDate
            d = QDate.fromString(birth, "yyyy-MM-dd")
            if d.isValid():
                self.birth_edit.setDate(d)
        form.addRow(FieldLabel("تاريخ الميلاد"), self.birth_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.setEditable(True)
        self.gender_combo.addItems(["", "ذكر", "أنثى"])
        self.gender_combo.setCurrentText(str(p.get("gender") or ""))
        form.addRow(FieldLabel("النوع"), self.gender_combo)

        self.address_edit = TextInput(placeholder="العنوان")
        self.address_edit.setText(str(p.get("address") or ""))
        form.addRow(FieldLabel("العنوان"), self.address_edit)

        self.occupation_edit = TextInput(placeholder="المهنة")
        self.occupation_edit.setText(str(p.get("occupation") or ""))
        form.addRow(FieldLabel("المهنة"), self.occupation_edit)

        self.nationality_edit = TextInput(placeholder="الجنسية")
        self.nationality_edit.setText(str(p.get("nationality") or ""))
        form.addRow(FieldLabel("الجنسية"), self.nationality_edit)

        self.family_edit = TextInput(placeholder="رقم العائلة")
        self.family_edit.setText(str(p.get("family_id") or ""))
        form.addRow(FieldLabel("رقم العائلة"), self.family_edit)

        self.allergies_edit = TextInput(placeholder="الحساسية")
        self.allergies_edit.setText(str(p.get("allergies") or ""))
        form.addRow(FieldLabel("الحساسية"), self.allergies_edit)

        self.notes_edit = TextInput(placeholder="ملاحظات طبية")
        self.notes_edit.setText(str(p.get("medical_notes") or ""))
        form.addRow(FieldLabel("ملاحظات طبية"), self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        full_name = self.name_edit.text().strip()
        if not full_name:
            self.name_edit.set_error(True)
            self.name_edit.setFocus()
            return
        data = {
            "full_name": full_name,
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
        if self.patient:
            db.update_patient(self.patient["id"], **data)
        else:
            db.add_patient(data["full_name"], phone=data["phone"], birth_date=data["birth_date"],
                           gender=data["gender"], address=data["address"],
                           medical_notes=data["medical_notes"], allergies=data["allergies"],
                           occupation=data["occupation"], family_id=data["family_id"],
                           nationality=data["nationality"])
        self.accept()


class PatientProfileDialog(QDialog):
    """Read-only patient profile with the full record + recent appointments.
    Editing happens through a dedicated edit dialog opened from here - never
    directly on the profile."""

    def __init__(self, patient, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"ملف المريض — {patient.get('full_name') or ''}")
        self.setModal(True)
        self.resize(660, 560)
        self.patient = patient
        self._build_ui()
        self._reload()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(design.SPACING * 2)

        # Summary card
        self.summary = QLabel("")
        self.summary.setObjectName("PageSubtitle")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.RichText)
        self.details.setObjectName("PageSubtitle")
        root.addWidget(self.details)

        # Recent appointments
        title = QLabel("أحدث المواعيد")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        self.appt_table = DataTable()
        self.appt_model = QStandardItemModel()
        self.appt_model.setHorizontalHeaderLabels(["التاريخ", "الوقت", "الطبيب", "الحالة"])
        self.appt_table.setModel(self.appt_model)
        root.addWidget(self.appt_table, stretch=1)

        # Actions
        actions = QHBoxLayout()
        edit_btn = PrimaryButton("تعديل البيانات")
        edit_btn.clicked.connect(self._open_edit)
        actions.addWidget(edit_btn)
        close_btn = SecondaryButton("إغلاق")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)
        actions.addStretch()
        root.addLayout(actions)

    # ------------------------------------------------------------------
    def _reload(self):
        p = db.get_patient(self.patient["id"]) or self.patient
        self.patient = p
        name = str(p.get("full_name") or "")
        self.setWindowTitle(f"ملف المريض — {name}")
        self.summary.setText(
            f"{name}  •  {ltr(str(p.get('phone') or ''))}  •  {str(p.get('gender') or '')}"
        )
        lines = []
        for key, label in (
            ("birth_date", "تاريخ الميلاد"),
            ("address", "العنوان"),
            ("occupation", "المهنة"),
            ("nationality", "الجنسية"),
            ("family_id", "رقم العائلة"),
            ("allergies", "الحساسية"),
            ("medical_notes", "ملاحظات طبية"),
        ):
            val = str(p.get(key) or "").strip()
            if val:
                lines.append(f"<b>{label}:</b> {val}")
        self.details.setText(" &nbsp;|&nbsp; ".join(lines) if lines else "لا توجد بيانات إضافية")

        # Recent appointments for this patient
        appts = [a for a in db.get_appointments() if a.get("patient_id") == p["id"]]
        appts = sorted(appts, key=lambda a: (a.get("appt_date") or "", a.get("appt_time") or ""),
                       reverse=True)[:10]
        self.appt_model.removeRows(0, self.appt_model.rowCount())
        for a in appts:
            row = [
                str(a.get("appt_date") or ""),
                str(a.get("appt_time") or ""),
                str(a.get("doctor_name") or ""),
                status_key_to_label(a.get("status")),
            ]
            items = [QStandardItem(v) for v in row]
            for it in items:
                it.setTextAlignment(Qt.AlignCenter)
            self.appt_model.appendRow(items)

    def _open_edit(self):
        dlg = PatientDialog(patient=self.patient, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._reload()


class PatientsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        # Title
        title = QLabel("المرضى")
        title.setObjectName("PageTitle")
        root_layout.addWidget(title)

        # Search + actions row
        controls = QHBoxLayout()
        controls.setSpacing(design.SPACING * 2)
        self.search_input = TextInput(placeholder="بحث بالاسم أو الهاتف...")
        self.search_input.textChanged.connect(self._on_search)
        controls.addWidget(self.search_input, stretch=1)

        profile_btn = SecondaryButton("الملف")
        profile_btn.clicked.connect(self._show_profile)
        add_btn = PrimaryButton("+ مريض جديد")
        add_btn.clicked.connect(self._add_new)
        edit_btn = SecondaryButton("تعديل")
        edit_btn.clicked.connect(self._edit_selected)
        delete_btn = SecondaryButton("حذف")
        delete_btn.clicked.connect(self._delete_selected)

        controls.addWidget(profile_btn)
        controls.addWidget(add_btn)
        controls.addWidget(edit_btn)
        controls.addWidget(delete_btn)

        root_layout.addLayout(controls)

        # Table (ID column kept in the model only for lookups)
        self.table = DataTable()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["ID", "الاسم", "الهاتف", "النوع",
                                              "تاريخ الميلاد", "المهنة", "الجنسية"])
        self.table.setModel(self.model)
        self.table.hide_columns(0)
        root_layout.addWidget(self.table, stretch=1)

    def _on_search(self, text):
        self.refresh()

    def refresh(self):
        search = self.search_input.text().strip()
        patients = db.get_all_patients(search)
        self.model.removeRows(0, self.model.rowCount())
        for p in patients:
            row = [
                str(p.get("id") if "id" in p else p.get("patient_id") or ""),
                str(p.get("full_name") or ""),
                ltr(str(p.get("phone") or "")),
                str(p.get("gender") or ""),
                str(p.get("birth_date") or ""),
                str(p.get("occupation") or ""),
                str(p.get("nationality") or ""),
            ]
            self.model.appendRow([QStandardItem(v) for v in row])
        self.model.setProperty("patients", patients)

    def _selected_patient(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        patients = self.model.property("patients")
        if patients and 0 <= row < len(patients):
            return patients[row]
        return None

    def _show_profile(self):
        patient = self._selected_patient()
        if not patient:
            return
        dlg = PatientProfileDialog(patient, parent=self)
        dlg.exec()
        self.refresh()

    def _add_new(self):
        dlg = PatientDialog(patient=None, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _edit_selected(self):
        patient = self._selected_patient()
        if not patient:
            return
        dlg = PatientDialog(patient=patient, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_selected(self):
        patient = self._selected_patient()
        if not patient:
            return
        from .components import ask_confirmation, show_error
        try:
            related = db.get_appointments()
            appt_count = len([a for a in related if a.get("patient_id") == patient["id"]])
        except Exception:
            appt_count = 0
        if appt_count:
            show_error(self, "لا يمكن الحذف",
                       f"المريض له {appt_count} موعد مسجَّل. يمكنك إلغاء مواعيده أو ترك بياناته دون حذف.")
            return
        if ask_confirmation(self, "حذف مريض",
                            f"هل تريد حذف المريض «{patient.get('full_name')}»؟"):
            db.delete_patient(patient["id"])
            self.refresh()