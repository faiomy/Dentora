# -*- coding: utf-8 -*-
"""Patients page for the Qt version of Dentora.

Provides a searchable patient list plus two distinct workflows:
- A full five-tab *profile* workspace (PatientProfileDialog) - visits,
  odontogram, financial account, read-only data and a dedicated edit tab;
- A standalone add/edit *dialog* (PatientDialog) wrapping the shared
  PatientForm - viewing never edits in place, and every edit/delete is an
  explicit, confirmed action.

All data operations reuse the existing ``database`` module.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QDialogButtonBox,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

import database as db
from . import design
from .constants import ltr
from .components import DataTable, PrimaryButton, SecondaryButton, TextInput
from .patient_profile import PatientForm, PatientProfileDialog


class PatientDialog(QDialog):
    """Add / edit a patient (a dedicated editing step - separate from viewing)."""

    def __init__(self, patient=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مريض جديد" if not patient else "تعديل بيانات المريض")
        self.setModal(True)
        self.resize(520, 620)
        self.patient = patient
        root = QVBoxLayout(self)
        root.setSpacing(design.SPACING_MD)
        self.form = PatientForm(self)
        self.form.load(patient)
        root.addWidget(self.form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def gender_combo(self):
        # Kept public (delegates to the shared form) for compatibility with
        # existing callers/tests that inspect the dialog's controls.
        return self.form.gender_combo

    def _save(self):
        if self.form.validate() is not None:
            return
        data = self.form.get_data()
        if self.patient:
            db.update_patient(self.patient["id"], **data)
        else:
            db.add_patient(data["full_name"], phone=data["phone"], birth_date=data["birth_date"],
                           gender=data["gender"], address=data["address"],
                           medical_notes=data["medical_notes"], allergies=data["allergies"],
                           occupation=data["occupation"], family_id=data["family_id"],
                           nationality=data["nationality"])
        self.accept()


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
        self.table.configure_columns(stretch=1)
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