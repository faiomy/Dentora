# -*- coding: utf-8 -*-
"""Procedures page for the Qt version of Dentora.
Manages treatment price lists, treatments (procedures), and their variants,
reusing the existing ``database`` functions.
"""

import uuid

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
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
)


class NewPriceListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("قائمة أسعار جديدة")
        self.setModal(True)
        self.resize(360, 140)
        form = QFormLayout(self)
        self.name_edit = TextInput()
        form.addRow("اسم القائمة", self.name_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        name = self.name_edit.text().strip()
        if name:
            db.add_price_list(name)
            self.accept()


class TreatmentDialog(QDialog):
    """Add / edit a treatment price in a price list."""

    def __init__(self, price_list_id, existing_key=None, existing_info=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("بند معالجة جديد" if not existing_key else "تعديل بند معالجة")
        self.setModal(True)
        self.resize(420, 260)
        self.price_list_id = price_list_id
        self.existing_key = existing_key
        self.existing_info = existing_info or {}
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)

        self.label_edit = TextInput()
        self.label_edit.setText(str(self.existing_info.get("label") or ""))
        form.addRow("الاسم", self.label_edit)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 10000000)
        self.price_spin.setDecimals(2)
        self.price_spin.setSingleStep(5)
        if self.existing_info.get("price") is not None:
            self.price_spin.setValue(float(self.existing_info["price"]))
        form.addRow("السعر", self.price_spin)

        self.commission_spin = QSpinBox()
        self.commission_spin.setRange(0, 100)
        self.commission_spin.setSuffix(" %")
        if self.existing_info.get("commission_percent") is not None:
            self.commission_spin.setValue(int(self.existing_info["commission_percent"]))
        form.addRow("العمولة", self.commission_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        label = self.label_edit.text().strip()
        if not label:
            return
        key = self.existing_key or f"custom_{uuid.uuid4().hex[:8]}"
        price = self.price_spin.value()
        commission = self.commission_spin.value()
        db.update_treatment_price(self.price_list_id, key, label, price, commission)
        self.accept()


class VariantsDialog(QDialog):
    """Manage treatment variants (subtypes/materials) for a treatment."""

    def __init__(self, price_list_id, treatment_key, treatment_label, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"الأنواع الفرعية – {treatment_label}")
        self.setModal(True)
        self.resize(520, 460)
        self.price_list_id = price_list_id
        self.treatment_key = treatment_key
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(design.SPACING * 2)

        self.table = DataTable()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["الاسم", "السعر", "العمولة", "ID"])
        self.table.setModel(self.model)
        layout.addWidget(self.table, stretch=1)

        buttons_row = QHBoxLayout()
        add_btn = PrimaryButton("+ نوع جديد")
        add_btn.clicked.connect(self._add)
        edit_btn = SecondaryButton("تعديل")
        edit_btn.clicked.connect(self._edit)
        delete_btn = SecondaryButton("حذف")
        delete_btn.clicked.connect(self._delete)
        close_btn = SecondaryButton("إغلاق")
        close_btn.clicked.connect(self.accept)
        buttons_row.addWidget(add_btn)
        buttons_row.addWidget(edit_btn)
        buttons_row.addWidget(delete_btn)
        buttons_row.addStretch()
        buttons_row.addWidget(close_btn)
        layout.addLayout(buttons_row)

    def refresh(self):
        variants = db.get_treatment_variants(self.price_list_id, self.treatment_key)
        self.model.removeRows(0, self.model.rowCount())
        for v in variants:
            self.model.appendRow([
                QStandardItem(str(v.get("variant_name") or "")),
                QStandardItem(str(v.get("price") or "")),
                QStandardItem(str(v.get("commission_percent") or "")),
                QStandardItem(str(v.get("id") or "")),
            ])
        self.model.setProperty("variants", variants)

    def _selected_variant(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        variants = self.model.property("variants")
        if variants and 0 <= row < len(variants):
            return variants[row]
        return None

    def _variant_dialog(self, variant=None):
        dlg = QDialog(self)
        dlg.setWindowTitle("نوع جديد" if not variant else "تعديل نوع")
        dlg.setModal(True)
        dlg.resize(400, 220)
        form = QFormLayout(dlg)
        name_edit = TextInput()
        name_edit.setText(str(variant.get("variant_name") or "") if variant else "")
        price_spin = QDoubleSpinBox()
        price_spin.setRange(0, 10000000)
        price_spin.setDecimals(2)
        if variant and variant.get("price") is not None:
            price_spin.setValue(float(variant["price"]))
        comm_spin = QSpinBox()
        comm_spin.setRange(0, 100)
        comm_spin.setSuffix(" %")
        if variant and variant.get("commission_percent") is not None:
            comm_spin.setValue(int(variant["commission_percent"]))
        form.addRow("الاسم", name_edit)
        form.addRow("السعر", price_spin)
        form.addRow("العمولة", comm_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        form.addRow(buttons)
        result = {}
        def _save():
            nm = name_edit.text().strip()
            if not nm:
                return
            result["name"] = nm
            result["price"] = price_spin.value()
            result["commission"] = comm_spin.value()
            dlg.accept()
        buttons.accepted.connect(_save)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            return result
        return None

    def _add(self):
        data = self._variant_dialog()
        if data:
            db.add_treatment_variant(self.price_list_id, self.treatment_key,
                                     data["name"], data["price"], data["commission"])
            self.refresh()

    def _edit(self):
        v = self._selected_variant()
        if not v:
            return
        data = self._variant_dialog(v)
        if data:
            db.update_treatment_variant(v["id"], data["name"], data["price"], data["commission"])
            self.refresh()

    def _delete(self):
        v = self._selected_variant()
        if not v:
            return
        from .components import ask_confirmation
        if ask_confirmation(self, "حذف نوع", f"حذف «{v.get('variant_name')}»؟"):
            db.delete_treatment_variant(v["id"])
            self.refresh()


class ProceduresPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_list_id = None
        self._key_list = []
        self._build_ui()
        self._reload_lists()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        title = QLabel("الإجراءات الطبية")
        title.setStyleSheet(
            f"font-size: {design.FONT_SIZE + 8}px; font-weight: bold; color: {design.TEXT_COLOR};"
        )
        root_layout.addWidget(title)

        # Price list controls
        lists_row = QHBoxLayout()
        lists_row.setSpacing(design.SPACING * 2)
        lists_row.addWidget(QLabel("قائمة الأسعار:"))
        self.list_combo = QComboBox()
        self.list_combo.currentIndexChanged.connect(self._on_list_changed)
        lists_row.addWidget(self.list_combo)

        self.active_badge = QLabel("")
        self.active_badge.setStyleSheet(f"color: {design.SUCCESS_COLOR}; font-weight: bold;")
        lists_row.addWidget(self.active_badge)

        set_active_btn = SecondaryButton("تعيين كنشطة")
        set_active_btn.clicked.connect(self._set_active)
        lists_row.addWidget(set_active_btn)

        add_list_btn = SecondaryButton("+ قائمة جديدة")
        add_list_btn.clicked.connect(self._add_list)
        lists_row.addWidget(add_list_btn)

        delete_list_btn = SecondaryButton("حذف القائمة")
        delete_list_btn.clicked.connect(self._delete_list)
        lists_row.addWidget(delete_list_btn)

        lists_row.addStretch()
        root_layout.addLayout(lists_row)

        # Treatments table
        self.table = DataTable()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["الاسم", "السعر", "العمولة", "الأنواع الفرعية"])
        self.table.setModel(self.model)
        root_layout.addWidget(self.table, stretch=1)

        # Actions
        actions = QHBoxLayout()
        add_btn = PrimaryButton("+ بند جديد")
        add_btn.clicked.connect(self._add_treatment)
        edit_btn = SecondaryButton("تعديل")
        edit_btn.clicked.connect(self._edit_treatment)
        delete_btn = SecondaryButton("حذف")
        delete_btn.clicked.connect(self._delete_treatment)
        variants_btn = SecondaryButton("إدارة الأنواع الفرعية")
        variants_btn.clicked.connect(self._manage_variants)
        actions.addWidget(add_btn)
        actions.addWidget(edit_btn)
        actions.addWidget(delete_btn)
        actions.addWidget(variants_btn)
        actions.addStretch()
        root_layout.addLayout(actions)

    # ------------------------------------------------------------------
    def _reload_lists(self):
        self.lists = db.get_price_lists()
        self.list_combo.blockSignals(True)
        self.list_combo.clear()
        for l in self.lists:
            self.list_combo.addItem(l["name"], l["id"])
        # Select active or first
        active_id = db.get_settings().get("active_price_list_id")
        idx = 0
        for i, l in enumerate(self.lists):
            if l["id"] == active_id:
                idx = i
                break
        if self.lists:
            self.list_combo.setCurrentIndex(idx)
            self.selected_list_id = self.lists[idx]["id"]
        else:
            self.selected_list_id = None
        self.list_combo.blockSignals(False)
        self._update_active_badge()
        self.refresh()

    def _on_list_changed(self):
        idx = self.list_combo.currentIndex()
        if 0 <= idx < len(self.lists):
            self.selected_list_id = self.lists[idx]["id"]
            self._update_active_badge()
            self.refresh()

    def _update_active_badge(self):
        active_id = db.get_settings().get("active_price_list_id")
        if self.selected_list_id == active_id:
            self.active_badge.setText("القائمة النشطة")
        else:
            self.active_badge.setText("")

    def _set_active(self):
        if self.selected_list_id is not None:
            db.set_active_price_list(self.selected_list_id)
            self._update_active_badge()

    def _add_list(self):
        dlg = NewPriceListDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._reload_lists()

    def _delete_list(self):
        if self.selected_list_id is None:
            return
        from .components import ask_confirmation
        if ask_confirmation(self, "حذف قائمة", "هل تريد حذف هذه القائمة؟"):
            db.delete_price_list(self.selected_list_id)
            self._reload_lists()

    # ------------------------------------------------------------------
    def refresh(self):
        self.model.removeRows(0, self.model.rowCount())
        self._key_list = []
        if self.selected_list_id is None:
            return
        prices = db.get_treatment_prices(self.selected_list_id)
        variants = db.get_all_treatment_variants(self.selected_list_id)
        for key, info in prices.items():
            self._key_list.append(key)
            self.model.appendRow([
                QStandardItem(str(info.get("label") or "")),
                QStandardItem(str(info.get("price") or "")),
                QStandardItem(str(info.get("commission_percent") or "")),
                QStandardItem(str(len(variants.get(key, [])))),
            ])
        self.model.setProperty("prices", prices)

    def _selected_key(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        if 0 <= row < len(self._key_list):
            return self._key_list[row]
        return None

    def _selected_info(self):
        prices = self.model.property("prices") or {}
        key = self._selected_key()
        return (key, prices.get(key)) if key else (None, None)

    def _add_treatment(self):
        if self.selected_list_id is None:
            return
        dlg = TreatmentDialog(self.selected_list_id, None, None, self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _edit_treatment(self):
        if self.selected_list_id is None:
            return
        key, info = self._selected_info()
        if key is None:
            return
        dlg = TreatmentDialog(self.selected_list_id, key, info, self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_treatment(self):
        if self.selected_list_id is None:
            return
        key, info = self._selected_info()
        if key is None:
            return
        from .components import ask_confirmation
        if ask_confirmation(self, "حذف بند", f"حذف «{info.get('label')}»؟"):
            db.delete_treatment_price(self.selected_list_id, key)
            self.refresh()

    def _manage_variants(self):
        if self.selected_list_id is None:
            return
        key, info = self._selected_info()
        if key is None:
            return
        dlg = VariantsDialog(self.selected_list_id, key, info.get("label") or key, self)
        dlg.exec()
        self.refresh()
