# -*- coding: utf-8 -*-
"""Expenses page for the Qt version of Dentora.
A category-filtered list of expenses with add/delete support, reusing the
existing ``database`` functions (get_expenses / add_expense / delete_expense).
Categories mirror ``db.EXPENSE_CATEGORIES`` and are shown as filter chips.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QPushButton,
    QButtonGroup,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QDate

import database as db
from . import design
from .components import (
    DataTable,
    PrimaryButton,
    SecondaryButton,
    TextInput,
    ComboBox,
    DateInput,
    ask_confirmation,
)


class ExpenseDialog(QDialog):
    """Add a new expense."""

    def __init__(self, default_category=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة مصروف")
        self.setModal(True)
        self.resize(440, 300)
        self.default_category = default_category or db.EXPENSE_CATEGORIES[0]
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)

        self.category_combo = ComboBox()
        self.category_combo.addItems(db.EXPENSE_CATEGORIES)
        self.category_combo.setCurrentText(self.default_category)
        form.addRow("التصنيف", self.category_combo)

        self.item_edit = TextInput(placeholder="اسم البند")
        form.addRow("اسم البند", self.item_edit)

        self.amount_edit = TextInput(placeholder="0.00")
        self.amount_edit.setAlignment(Qt.AlignRight)
        form.addRow("المبلغ", self.amount_edit)

        self.date_edit = DateInput()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        today = date.today()
        self.date_edit.setDate(QDate(today.year, today.month, today.day))
        form.addRow("التاريخ", self.date_edit)

        self.notes_edit = TextInput(placeholder="ملاحظات (اختياري)")
        form.addRow("ملاحظات", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ المصروف")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        item_name = self.item_edit.text().strip()
        amount_text = self.amount_edit.text().strip()
        if not item_name or not amount_text:
            return
        try:
            amount = float(amount_text)
        except ValueError:
            return
        if amount <= 0:
            return
        db.add_expense(
            self.category_combo.currentText(),
            item_name,
            amount,
            expense_date=self.date_edit.date().toString("yyyy-MM-dd"),
            notes=self.notes_edit.text().strip(),
        )
        self.accept()


class ExpensesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_category = db.EXPENSE_CATEGORIES[0]
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        title = QLabel("المصروفات")
        title.setObjectName("PageTitle")
        root_layout.addWidget(title)

        # --- Category filter chips --------------------------------------
        chip_row = QHBoxLayout()
        chip_row.setSpacing(design.SPACING_SM)
        self._chip_group = QButtonGroup(self)
        self._chip_group.setExclusive(True)
        self._chip_buttons = []
        for name in db.EXPENSE_CATEGORIES:
            chip = QPushButton(name)
            chip.setObjectName("TimeChip")
            chip.setCheckable(True)
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _, n=name: self._on_category_changed(n))
            self._chip_group.addButton(chip)
            chip_row.addWidget(chip)
            self._chip_buttons.append(chip)
        self._chip_buttons[0].setChecked(True)
        chip_row.addStretch()
        root_layout.addLayout(chip_row)

        # --- Total label ------------------------------------------------
        self.total_label = QLabel("")
        self.total_label.setObjectName("DangerLabel")
        root_layout.addWidget(self.total_label, alignment=Qt.AlignLeft)

        # --- Table ------------------------------------------------------
        self.table = DataTable()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["التاريخ", "الفئة", "البند", "المبلغ", "ملاحظات"])
        self.table.setModel(self.model)
        root_layout.addWidget(self.table, stretch=1)

        # --- Actions ----------------------------------------------------
        actions = QHBoxLayout()
        actions.setSpacing(design.SPACING * 2)
        add_btn = PrimaryButton("+ إضافة مصروف")
        add_btn.clicked.connect(self._add_new)
        delete_btn = SecondaryButton("حذف")
        delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(add_btn)
        actions.addWidget(delete_btn)
        actions.addStretch()
        root_layout.addLayout(actions)

    def _on_category_changed(self, name):
        self._active_category = name
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        expenses = db.get_expenses(category=self._active_category)
        total = sum(e["amount"] for e in expenses)
        self.total_label.setText(
            f"إجمالي مصروفات {self._active_category}: {total:g} جنيه")

        self.model.removeRows(0, self.model.rowCount())
        for e in expenses:
            row = [
                str(e.get("expense_date") or ""),
                str(e.get("category") or ""),
                str(e.get("item_name") or ""),
                f"{e['amount']:g}",
                str(e.get("notes") or ""),
            ]
            self.model.appendRow([QStandardItem(v) for v in row])
        self.model.setProperty("expenses", expenses)

    def _selected_expense(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        expenses = self.model.property("expenses")
        if expenses and 0 <= row < len(expenses):
            return expenses[row]
        return None

    def _add_new(self):
        dlg = ExpenseDialog(default_category=self._active_category, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_selected(self):
        expense = self._selected_expense()
        if not expense:
            return
        if ask_confirmation(self, "حذف مصروف",
                            "هل أنت متأكد من حذف هذا المصروف؟ لن يمكن التراجع."):
            db.delete_expense(expense["id"])
            self.refresh()