# -*- coding: utf-8 -*-
"""Patients page for the Qt version of Dentora.
Provides a searchable patient list and add/edit/delete dialogs that reuse the
existing ``database`` module.
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
)


class PatientDialog(QDialog):
    """Add / edit a patient."""

    def __init__(self, patient=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مريض جديد" if not patient else "تعديل بيانات المريض")
        self.setModal(True)
        self.resize(480, 560)
        self.patient = patient
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)

        p = self.patient or {}

        self.name_edit = TextInput()
        self.name_edit.setText(str(p.get("full_name") or ""))
        form.addRow("الاسم *", self.name_edit)

        self.phone_edit = TextInput(placeholder="رقم الهاتف")
        self.phone_edit.setText(str(p.get("phone") or ""))
        form.addRow("الهاتف", self.phone_edit)

        self.birth_edit = TextInput(placeholder="YYYY-MM-DD (اختياري)")
        self.birth_edit.setText(str(p.get("birth_date") or ""))
        form.addRow("تاريخ الميلاد", self.birth_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.setEditable(True)
        self.gender_combo.addItems(["", "ذكر", "أنثى"])
        self.gender_combo.setCurrentText(str(p.get("gender") or ""))
        form.addRow("النوع", self.gender_combo)

        self.address_edit = TextInput(placeholder="العنوان")
        self.address_edit.setText(str(p.get("address") or ""))
        form.addRow("العنوان", self.address_edit)

        self.occupation_edit = TextInput(placeholder="المهنة")
        self.occupation_edit.setText(str(p.get("occupation") or ""))
        form.addRow("المهنة", self.occupation_edit)

        self.nationality_edit = TextInput(placeholder="الجنسية")
        self.nationality_edit.setText(str(p.get("nationality") or ""))
        form.addRow("الجنسية", self.nationality_edit)

        self.family_edit = TextInput(placeholder="رقم العائلة")
        self.family_edit.setText(str(p.get("family_id") or ""))
        form.addRow("رقم العائلة", self.family_edit)

        self.allergies_edit = TextInput(placeholder="الحساسية")
        self.allergies_edit.setText(str(p.get("allergies") or ""))
        form.addRow("الحساسية", self.allergies_edit)

        self.notes_edit = TextInput(placeholder="ملاحظات طبية")
        self.notes_edit.setText(str(p.get("medical_notes") or ""))
        form.addRow("ملاحظات طبية", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        full_name = self.name_edit.text().strip()
        if not full_name:
            return  # validation: name required
        data = {
            "full_name": full_name,
            "phone": self.phone_edit.text().strip(),
            "birth_date": self.birth_edit.text().strip(),
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
        title.setStyleSheet(
            f"font-size: {design.FONT_SIZE + 8}px; font-weight: bold; color: {design.TEXT_COLOR};"
        )
        root_layout.addWidget(title)

        # Search + actions row
        controls = QHBoxLayout()
        controls.setSpacing(design.SPACING * 2)
        self.search_input = TextInput(placeholder="بحث بالاسم أو الهاتف...")
        self.search_input.textChanged.connect(self._on_search)
        controls.addWidget(self.search_input)

        add_btn = PrimaryButton("+ مريض جديد")
        add_btn.clicked.connect(self._add_new)
        edit_btn = SecondaryButton("تعديل")
        edit_btn.clicked.connect(self._edit_selected)
        delete_btn = SecondaryButton("حذف")
        delete_btn.clicked.connect(self._delete_selected)

        controls.addWidget(add_btn)
        controls.addWidget(edit_btn)
        controls.addWidget(delete_btn)

        root_layout.addLayout(controls)

        # Table
        self.table = DataTable()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["ID", "الاسم", "الهاتف", "النوع",
                                              "تاريخ الميلاد", "المهنة", "الجنسية"])
        self.table.setModel(self.model)
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
                str(p.get("phone") or ""),
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
        from .components import ask_confirmation
        if ask_confirmation(self, "حذف مريض",
                            f"هل تريد حذف المريض «{patient.get('full_name')}»؟"):
            db.delete_patient(patient["id"])
            self.refresh()
