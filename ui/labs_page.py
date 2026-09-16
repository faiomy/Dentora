# -*- coding: utf-8 -*-
"""Labs page for the Qt version of Dentora.
Four tabs mirroring pages/labs_page.py:
- حالات المعمل: lab orders with filters, quick status changes, add/edit/delete
- المعامل: labs CRUD + enable/disable
- حساب المعمل: per-lab balance, transactions ledger, record payments
- إعدادات البنود العلاجية: per-treatment-item lab defaults
All data operations reuse the existing ``database`` functions.
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
    QComboBox,
    QTextEdit,
    QCheckBox,
    QScrollArea,
    QTabWidget,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import QFrame

import database as db
from . import design
from .constants import ltr
from .components import (
    DataTable,
    PrimaryButton,
    SecondaryButton,
    DangerButton,
    TextInput,
    ComboBox,
    DateInput,
    Card,
    ask_confirmation,
)


STATUS_LABELS = {
    "sent": "مُرسلة للمعمل",
    "in_progress": "قيد التنفيذ بالمعمل",
    "received": "تم الاستلام من المعمل",
    "delivered": "تم التسليم للمريض",
    "cancelled": "ملغاة",
}
STATUS_ORDER = ["sent", "in_progress", "received", "delivered", "cancelled"]

STATUS_COLORS = {
    "sent": design.WARNING_400,
    "in_progress": design.PRIMARY_400,
    "received": design.SUCCESS_600,
    "delivered": design.TEXT_MUTED,
    "cancelled": design.ERROR_600,
}


def _status_color(status):
    return STATUS_COLORS.get(status, design.TEXT_MUTED)


def _lab_id_by_name(labs, name):
    return next((l["id"] for l in labs if l["name"] == name), None)


def _lab_name_by_id(labs, lab_id):
    return next((l["name"] for l in labs if l["id"] == lab_id), "")


def _sender_options():
    """Unified list of everyone who can send a lab order: doctors + support staff."""
    names = []
    for d in db.get_doctors():
        name = d["full_name"]
        if name not in names:
            names.append(name)
    for s in db.get_support_staff():
        if s["full_name"] not in names:
            names.append(s["full_name"])
    return names


# ===========================================================================
# Dialogs
# ===========================================================================

class LabOrderDialog(QDialog):
    """Add / edit a lab order."""

    def __init__(self, order=None, parent=None):
        super().__init__(parent)
        self.order = order
        self.setWindowTitle("تعديل حالة معمل" if order else "حالة معمل جديدة")
        self.setModal(True)
        self.resize(480, 640)
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)
        o = self.order or {}

        active_labs = db.get_labs(active_only=True)
        self.labs = active_labs if active_labs else db.get_labs()

        # Patient
        self.patient_combo = ComboBox()
        self.patient_combo.setEditable(True)
        patients = db.get_all_patients()
        self.patients = patients
        self.patient_combo.addItem("-- بدون تحديد --", None)
        for p in patients:
            self.patient_combo.addItem(p["full_name"], p["id"])
        if o.get("patient_id"):
            idx = self.patient_combo.findData(o["patient_id"])
            if idx >= 0:
                self.patient_combo.setCurrentIndex(idx)
        elif o.get("patient_name"):
            self.patient_combo.setCurrentText(o["patient_name"])
        form.addRow("المريض (اختياري)", self.patient_combo)

        # Treatment / tooth
        self.treatment_edit = TextInput(placeholder="اسم البند العلاجي")
        self.treatment_edit.setText(str(o.get("treatment_label") or ""))
        form.addRow("اسم البند العلاجي", self.treatment_edit)

        self.tooth_edit = TextInput(placeholder="رقم السن (اختياري)")
        self.tooth_edit.setText(str(o.get("tooth_number") or ""))
        form.addRow("رقم السن", self.tooth_edit)

        # Lab
        self.lab_combo = ComboBox()
        lab_names = [l["name"] for l in self.labs]
        self.lab_combo.addItems(lab_names)
        if o.get("lab_id"):
            idx = self.lab_combo.findText(_lab_name_by_id(self.labs, o["lab_id"]))
            if idx >= 0:
                self.lab_combo.setCurrentIndex(idx)
        form.addRow("المعمل", self.lab_combo)

        # Sender / receiver
        self.sender_combo = ComboBox()
        self.sender_combo.addItems(["-- بدون تحديد --"] + _sender_options())
        if o.get("sent_by"):
            idx = self.sender_combo.findText(o["sent_by"])
            if idx >= 0:
                self.sender_combo.setCurrentIndex(idx)
        form.addRow("المرسل (من العيادة)", self.sender_combo)

        self.receiver_edit = TextInput(placeholder="المستلم بالمعمل")
        self.receiver_edit.setText(str(o.get("received_by") or ""))
        form.addRow("المستلم بالمعمل", self.receiver_edit)

        # Lab code
        self.code_edit = TextInput(placeholder="رمز الحالة عند المعمل (اختياري)")
        self.code_edit.setText(str(o.get("lab_code") or ""))
        form.addRow("الرمز", self.code_edit)

        # Status
        self.status_combo = ComboBox()
        self.status_combo.addItems([STATUS_LABELS[s] for s in STATUS_ORDER])
        if o.get("status"):
            idx = self.status_combo.findText(STATUS_LABELS.get(o["status"], o["status"]))
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)
        form.addRow("حالة الشغل", self.status_combo)

        # Dates
        self.sent_date_edit = DateInput()
        self.sent_date_edit.setDisplayFormat("yyyy-MM-dd")
        defaults = date.today()
        self.sent_date_edit.setDate(QDate(defaults.year, defaults.month, defaults.day))
        if o.get("sent_date"):
            self._apply_iso(self.sent_date_edit, o["sent_date"])
        form.addRow("تاريخ الإرسال", self.sent_date_edit)

        self.expected_date_edit = DateInput()
        self.expected_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.expected_date_edit.setCalendarPopup(True)
        if o.get("expected_date"):
            self._apply_iso(self.expected_date_edit, o["expected_date"])
        form.addRow("التاريخ المتوقع للتسليم", self.expected_date_edit)

        # Cost / notes
        self.cost_edit = TextInput(placeholder="0")
        self.cost_edit.setText(str(o.get("cost") or "0"))
        form.addRow("تكلفة المعمل (جنيه)", self.cost_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("ملاحظات (اختياري)")
        self.notes_edit.setMaximumHeight(80)
        if o.get("notes"):
            self.notes_edit.setPlainText(str(o["notes"]))
        form.addRow("ملاحظات", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def _apply_iso(date_edit, iso):
        qd = QDate.fromString(str(iso)[:10], "yyyy-MM-dd")
        if qd.isValid():
            date_edit.setDate(qd)

    def _save(self):
        treatment_label = self.treatment_edit.text().strip()
        if not treatment_label:
            return
        tooth_text = self.tooth_edit.text().strip()
        try:
            tooth_number = int(tooth_text) if tooth_text else None
        except ValueError:
            tooth_number = None
        try:
            cost = float(self.cost_edit.text().strip() or 0)
        except ValueError:
            cost = 0
        idx = self.lab_combo.currentIndex()
        lab_id = self.labs[idx]["id"] if 0 <= idx < len(self.labs) else None
        sender = self.sender_combo.currentText()
        sender = "" if sender == "-- بدون تحديد --" else sender
        status_key = next(
            (k for k, v in STATUS_LABELS.items()
             if v == self.status_combo.currentText()), "sent")
        patient_id = self.patient_combo.currentData()

        if self.order:
            db.update_lab_order(
                self.order["id"], lab_id=lab_id, tooth_number=tooth_number,
                treatment_label=treatment_label, lab_code=self.code_edit.text().strip(),
                status=status_key,
                sent_date=self.sent_date_edit.date().toString("yyyy-MM-dd"),
                expected_date=self.expected_date_edit.date().toString("yyyy-MM-dd")
                if self.expected_date_edit.date().toString("yyyy-MM-dd") else None,
                sent_by=sender, received_by=self.receiver_edit.text().strip(),
                cost=cost, notes=self.notes_edit.toPlainText())
        else:
            db.add_lab_order(
                lab_id, patient_id=patient_id, tooth_number=tooth_number,
                treatment_label=treatment_label, lab_code=self.code_edit.text().strip(),
                status=status_key,
                sent_date=self.sent_date_edit.date().toString("yyyy-MM-dd"),
                expected_date=self.expected_date_edit.date().toString("yyyy-MM-dd")
                if self.expected_date_edit.date().toString("yyyy-MM-dd") else None,
                sent_by=sender, received_by=self.receiver_edit.text().strip(),
                cost=cost, notes=self.notes_edit.toPlainText())
        self.accept()


class LabDialog(QDialog):
    """Add / edit a lab."""

    def __init__(self, lab=None, parent=None):
        super().__init__(parent)
        self.lab = lab
        self.setWindowTitle("تعديل معمل" if lab else "معمل جديد")
        self.setModal(True)
        self.resize(440, 340)
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)
        form.setSpacing(10)
        lab = self.lab or {}

        self.name_edit = TextInput(placeholder="اسم المعمل")
        self.name_edit.setText(str(lab.get("name") or ""))
        form.addRow("اسم المعمل *", self.name_edit)

        self.phone_edit = TextInput(placeholder="رقم التليفون")
        self.phone_edit.setText(str(lab.get("phone") or ""))
        form.addRow("رقم التليفون", self.phone_edit)

        self.contact_edit = TextInput(placeholder="الشخص المسؤول")
        self.contact_edit.setText(str(lab.get("contact_person") or ""))
        form.addRow("الشخص المسؤول", self.contact_edit)

        self.address_edit = TextInput(placeholder="العنوان")
        self.address_edit.setText(str(lab.get("address") or ""))
        form.addRow("العنوان", self.address_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("ملاحظات (اختياري)")
        self.notes_edit.setMaximumHeight(70)
        if lab.get("notes"):
            self.notes_edit.setPlainText(str(lab["notes"]))
        form.addRow("ملاحظات", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            return
        if self.lab:
            db.update_lab(self.lab["id"], name, self.phone_edit.text().strip(),
                          self.address_edit.text().strip(),
                          self.contact_edit.text().strip(), self.notes_edit.toPlainText())
        else:
            db.add_lab(name, self.phone_edit.text().strip(),
                       self.address_edit.text().strip(),
                       self.contact_edit.text().strip(), self.notes_edit.toPlainText())
        self.accept()


class LabPaymentDialog(QDialog):
    """Record a payment to a selected lab."""

    def __init__(self, lab_id, parent=None):
        super().__init__(parent)
        self.lab_id = lab_id
        self.setWindowTitle("تسجيل دفعة للمعمل")
        self.setModal(True)
        self.resize(420, 220)
        self._build_ui()

    def _build_ui(self):
        lab = db.get_lab(self.lab_id)
        form = QFormLayout(self)
        form.setSpacing(10)
        form.addRow("المعمل", QLabel(lab["name"] if lab else ""))

        self.amount_edit = TextInput(placeholder="0.00")
        form.addRow("المبلغ المدفوع (جنيه)", self.amount_edit)

        self.date_edit = DateInput()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        today = date.today()
        self.date_edit.setDate(QDate(today.year, today.month, today.day))
        form.addRow("التاريخ", self.date_edit)

        self.notes_edit = TextInput(placeholder="ملاحظات (اختياري)")
        form.addRow("ملاحظات", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("حفظ الدفعة")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self):
        try:
            amount = float(self.amount_edit.text().strip())
        except ValueError:
            return
        if amount <= 0:
            return
        db.add_lab_transaction(self.lab_id, "payment", amount,
                               description=self.notes_edit.text().strip(),
                               tx_date=self.date_edit.date().toString("yyyy-MM-dd"))
        self.accept()


# ===========================================================================
# Page
# ===========================================================================

class LabsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._order_status_filter = None
        self._order_lab_filter = None
        self._order_search = ""
        self._selected_lab_id = None
        self._set_id = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        title = QLabel("المعامل")
        title.setObjectName("PageTitle")
        root_layout.addWidget(title)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        self.tab_orders = QWidget()
        self.tab_labs = QWidget()
        self.tab_accounts = QWidget()
        self.tab_settings = QWidget()

        self.tabs.addTab(self.tab_orders, "حالات المعمل")
        self.tabs.addTab(self.tab_labs, "المعامل")
        self.tabs.addTab(self.tab_accounts, "حساب المعمل")
        self.tabs.addTab(self.tab_settings, "إعدادات البنود العلاجية")

        self._build_orders_tab()
        self._build_labs_tab()
        self._build_accounts_tab()
        self._build_settings_tab()

    # -----------------------------------------------------------------
    # Tab: حالات المعمل
    # -----------------------------------------------------------------
    def _build_orders_tab(self):
        layout = QVBoxLayout(self.tab_orders)
        layout.setContentsMargins(0, design.SPACING_SM, 0, 0)
        layout.setSpacing(design.SPACING * 2)

        filters = QHBoxLayout()
        filters.setSpacing(design.SPACING * 2)
        self.order_search_input = TextInput(placeholder="بحث باسم المريض/البند...")
        self.order_search_input.textChanged.connect(self._on_order_filter_changed)
        filters.addWidget(self.order_search_input, stretch=2)

        self.order_status_combo = ComboBox()
        self.order_status_combo.addItems(["كل الحالات"] + [STATUS_LABELS[s] for s in STATUS_ORDER])
        self.order_status_combo.currentIndexChanged.connect(self._on_order_filter_changed)
        filters.addWidget(self.order_status_combo)

        self.order_lab_combo = ComboBox()
        self._reload_order_lab_combo()
        self.order_lab_combo.currentIndexChanged.connect(self._on_order_filter_changed)
        filters.addWidget(self.order_lab_combo)

        add_btn = PrimaryButton("+ حالة جديدة")
        add_btn.clicked.connect(self._add_order)
        filters.addWidget(add_btn)

        layout.addLayout(filters)

        self.orders_table = DataTable()
        self.orders_model = QStandardItemModel()
        self.orders_model.setHorizontalHeaderLabels(
            ["الحالة", "البند", "المريض", "المعمل", "الرمز", "تاريخ الإرسال", "التكلفة", "ID"])
        self.orders_table.setModel(self.orders_model)
        layout.addWidget(self.orders_table, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(design.SPACING)
        edit_btn = SecondaryButton("تعديل")
        edit_btn.clicked.connect(self._edit_order)
        next_btn = PrimaryButton("➜ الحالة التالية")
        next_btn.clicked.connect(self._next_status)
        cancel_btn = SecondaryButton("إلغاء الحالة")
        cancel_btn.clicked.connect(self._cancel_order)
        delete_btn = DangerButton("حذف")
        delete_btn.clicked.connect(self._delete_order)
        actions.addWidget(edit_btn)
        actions.addWidget(next_btn)
        actions.addWidget(cancel_btn)
        actions.addWidget(delete_btn)
        actions.addStretch()
        layout.addLayout(actions)

    def _reload_order_lab_combo(self):
        current = self.order_lab_combo.currentText() if hasattr(self, "order_lab_combo") else None
        self.order_lab_combo.blockSignals(True)
        self.order_lab_combo.clear()
        self.order_lab_combo.addItems(["كل المعامل"] + [l["name"] for l in db.get_labs()])
        if current and self.order_lab_combo.findText(current) >= 0:
            self.order_lab_combo.setCurrentText(current)
        self.order_lab_combo.blockSignals(False)

    def _on_order_filter_changed(self):
        lab_name = self.order_lab_combo.currentText()
        self._order_lab_filter = _lab_id_by_name(db.get_labs(), lab_name) \
            if lab_name != "كل المعامل" else None
        status_label = self.order_status_combo.currentText()
        self._order_status_filter = next(
            (k for k, v in STATUS_LABELS.items() if v == status_label), None)
        self._order_search = self.order_search_input.text().strip()
        self.refresh_orders()

    def refresh_orders(self):
        orders = db.get_lab_orders(
            lab_id=self._order_lab_filter, status=self._order_status_filter,
            search=self._order_search or None)
        self.orders_model.removeRows(0, self.orders_model.rowCount())
        for o in orders:
            status_item = QStandardItem(STATUS_LABELS.get(o["status"], o["status"]))
            status_item.setForeground(QColor(_status_color(o["status"])))
            title = o.get("treatment_label") or "شغل معمل"
            if o.get("variant_name"):
                title += f" ({o['variant_name']})"
            if o.get("tooth_number"):
                title += f" - سن {o['tooth_number']}"
            row = [
                status_item,
                QStandardItem(title),
                QStandardItem(str(o.get("patient_name") or "")),
                QStandardItem(str(o.get("lab_name") or "")),
                QStandardItem(str(o.get("lab_code") or "")),
                QStandardItem(str(o.get("sent_date") or "")),
                QStandardItem(f"{o.get('cost') or 0:g}"),
                QStandardItem(str(o["id"])),
            ]
            self.orders_model.appendRow(row)
        self.orders_model.setProperty("orders", orders)

    def _selected_order(self):
        index = self.orders_table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        orders = self.orders_model.property("orders")
        if orders and 0 <= row < len(orders):
            return orders[row]
        return None

    def _add_order(self):
        dlg = LabOrderDialog(order=None, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_orders()

    def _edit_order(self):
        order = self._selected_order()
        if not order:
            return
        dlg = LabOrderDialog(order=order, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_orders()

    def _next_status(self):
        order = self._selected_order()
        if not order:
            return
        nxt = {"sent": "in_progress", "in_progress": "received",
               "received": "delivered"}.get(order["status"])
        if nxt:
            db.set_lab_order_status(order["id"], nxt)
            self.refresh_orders()

    def _cancel_order(self):
        order = self._selected_order()
        if not order or order["status"] in ("cancelled", "delivered"):
            return
        db.set_lab_order_status(order["id"], "cancelled")
        self.refresh_orders()

    def _delete_order(self):
        order = self._selected_order()
        if not order:
            return
        if ask_confirmation(
                self, "تأكيد الحذف",
                "هل تريد حذف هذه الحالة نهائيًا؟\n"
                "سيتم حذف أي حركة مالية مرتبطة بها من حساب المعمل أيضًا."):
            db.delete_lab_order(order["id"])
            self.refresh_orders()

    # -----------------------------------------------------------------
    # Tab: المعامل
    # -----------------------------------------------------------------
    def _build_labs_tab(self):
        layout = QVBoxLayout(self.tab_labs)
        layout.setContentsMargins(0, design.SPACING_SM, 0, 0)
        layout.setSpacing(design.SPACING * 2)

        add_btn = PrimaryButton("+ معمل جديد")
        add_btn.clicked.connect(self._add_lab)
        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(add_btn)
        layout.addLayout(top)

        self.labs_table = DataTable()
        self.labs_model = QStandardItemModel()
        self.labs_model.setHorizontalHeaderLabels(
            ["الاسم", "التليفون", "المسؤول", "العنوان", "نشط", "ID"])
        self.labs_table.setModel(self.labs_model)
        layout.addWidget(self.labs_table, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(design.SPACING)
        edit_btn = SecondaryButton("تعديل")
        edit_btn.clicked.connect(self._edit_lab)
        toggle_btn = SecondaryButton("تعطيل / تفعيل")
        toggle_btn.clicked.connect(self._toggle_lab)
        delete_btn = DangerButton("حذف")
        delete_btn.clicked.connect(self._delete_lab)
        actions.addWidget(edit_btn)
        actions.addWidget(toggle_btn)
        actions.addWidget(delete_btn)
        actions.addStretch()
        layout.addLayout(actions)

    def refresh_labs(self):
        labs = db.get_labs()
        self.labs_model.removeRows(0, self.labs_model.rowCount())
        for lab in labs:
            row = [
                QStandardItem(lab["name"] + ("" if lab["active"] else "  (معطّل)")),
                QStandardItem(ltr(str(lab.get("phone") or ""))),
                QStandardItem(str(lab.get("contact_person") or "")),
                QStandardItem(str(lab.get("address") or "")),
                QStandardItem("نعم" if lab["active"] else "لا"),
                QStandardItem(str(lab["id"])),
            ]
            self.labs_model.appendRow(row)
        self.labs_model.setProperty("labs", labs)

    def _selected_lab(self):
        index = self.labs_table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        labs = self.labs_model.property("labs")
        if labs and 0 <= row < len(labs):
            return labs[row]
        return None

    def _add_lab(self):
        dlg = LabDialog(lab=None, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_labs()
            self._reload_order_lab_combo()

    def _edit_lab(self):
        lab = self._selected_lab()
        if not lab:
            return
        dlg = LabDialog(lab=lab, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_labs()
            self._reload_order_lab_combo()

    def _toggle_lab(self):
        lab = self._selected_lab()
        if not lab:
            return
        db.set_lab_active(lab["id"], not lab["active"])
        self.refresh_labs()

    def _delete_lab(self):
        lab = self._selected_lab()
        if not lab:
            return
        if ask_confirmation(
                self, "تأكيد الحذف",
                f"هل تريد حذف معمل \"{lab['name']}\" نهائيًا؟\n"
                "سيتم حذف كل الحالات وحركات الحساب المرتبطة به.\n"
                "(الأفضل استخدام \"تعطيل\" بدل الحذف لو عندك سجل تعاملات قديم معه)"):
            db.delete_lab(lab["id"])
            self.refresh_labs()
            self.refresh_orders()
            self._reload_order_lab_combo()
            self.refresh_lab_balances()

    # -----------------------------------------------------------------
    # Tab: حساب المعمل
    # -----------------------------------------------------------------
    def _build_accounts_tab(self):
        layout = QVBoxLayout(self.tab_accounts)
        layout.setContentsMargins(0, design.SPACING_SM, 0, 0)
        layout.setSpacing(design.SPACING * 2)

        columns = QHBoxLayout()
        columns.setSpacing(design.SPACING * 2)

        # Right column (first in RTL): labs with balances
        self.labs_balance_table = DataTable()
        self.labs_balance_model = QStandardItemModel()
        self.labs_balance_model.setHorizontalHeaderLabels(["المعمل", "الرصيد"])
        self.labs_balance_table.setModel(self.labs_balance_model)
        self.labs_balance_table.selectionModel().selectionChanged.connect(
            self._on_lab_selected)
        columns.addWidget(self.labs_balance_table, stretch=2)

        # Left column: ledger of the selected lab
        ledger_box = QVBoxLayout()
        ledger_box.setSpacing(design.SPACING_SM)
        self.account_header = QLabel("اختر معمل من القائمة")
        self.account_header.setObjectName("SectionTitle")
        ledger_box.addWidget(self.account_header)

        self.account_balance_label = QLabel("")
        self.account_balance_label.setObjectName("MutedLabel")
        ledger_box.addWidget(self.account_balance_label)

        self.add_payment_btn = PrimaryButton("+ تسجيل دفعة")
        self.add_payment_btn.setEnabled(False)
        self.add_payment_btn.clicked.connect(self._add_payment)
        top_row = QHBoxLayout()
        top_row.addStretch()
        top_row.addWidget(self.add_payment_btn)
        ledger_box.addLayout(top_row)

        self.account_tx_table = DataTable()
        self.account_tx_model = QStandardItemModel()
        self.account_tx_model.setHorizontalHeaderLabels(
            ["التاريخ", "النوع", "المبلغ", "الوصف", "ID"])
        self.account_tx_table.setModel(self.account_tx_model)
        ledger_box.addWidget(self.account_tx_table, stretch=1)

        del_payment_btn = SecondaryButton("حذف الدفعة")
        del_payment_btn.clicked.connect(self._delete_payment)
        ledger_bottom = QHBoxLayout()
        ledger_bottom.addStretch()
        ledger_bottom.addWidget(del_payment_btn)
        ledger_box.addLayout(ledger_bottom)

        columns.addLayout(ledger_box, stretch=3)
        layout.addLayout(columns)

    def refresh_lab_balances(self):
        labs = db.get_all_labs_with_balances()
        self.labs_balance_model.removeRows(0, self.labs_balance_model.rowCount())
        for lab in labs:
            balance = lab["balance"]
            balance_text = f"{balance:g}" if balance else "مسدد بالكامل"
            row = [
                QStandardItem(lab["name"]),
                QStandardItem(balance_text),
            ]
            self.labs_balance_model.appendRow(row)
        self.labs_balance_model.setProperty("balance_labs", labs)
        self.refresh_account_detail()

    def _on_lab_selected(self):
        index = self.labs_balance_table.currentIndex()
        labs = self.labs_balance_model.property("balance_labs") or []
        row = index.row()
        self._selected_lab_id = labs[row]["id"] if 0 <= row < len(labs) else None
        self.refresh_account_detail()

    def refresh_account_detail(self):
        self.account_tx_model.removeRows(0, self.account_tx_model.rowCount())
        lab = db.get_lab(self._selected_lab_id) if self._selected_lab_id else None
        if not lab:
            self.account_header.setText("اختر معمل من القائمة")
            self.account_balance_label.setText("")
            self.account_balance_label.setObjectName("MutedLabel")
            self.add_payment_btn.setEnabled(False)
            return

        balance = db.get_lab_balance(lab["id"])
        self.account_header.setText(f"حساب: {lab['name']}")
        if balance > 0:
            self.account_balance_label.setText(
                f"المستحق للمعمل حاليًا: {balance:g} جنيه")
            self.account_balance_label.setObjectName("DangerLabel")
        elif balance == 0:
            self.account_balance_label.setText("رصيد صفر")
            self.account_balance_label.setObjectName("SuccessLabel")
        else:
            self.account_balance_label.setText(
                f"مبلغ زيادة مدفوع للمعمل: {abs(balance):g} جنيه")
            self.account_balance_label.setObjectName("SuccessLabel")
        self.add_payment_btn.setEnabled(True)

        txs = db.get_lab_transactions(lab["id"])
        for tx in txs:
            is_charge = tx["tx_type"] == "charge"
            sign = "+" if is_charge else "-"
            kind = "تكلفة شغل" if is_charge else "دفعة مسدَّدة"
            desc = kind
            if tx.get("description"):
                desc += f" - {tx['description']}"
            amount_item = QStandardItem(f"{sign} {tx['amount']:g}")
            amount_item.setForeground(QColor(
                design.ERROR_600 if is_charge else design.SUCCESS_600))
            row = [
                QStandardItem(str(tx.get("tx_date") or "")),
                QStandardItem(kind),
                amount_item,
                QStandardItem(desc),
                QStandardItem(str(tx["id"])),
            ]
            self.account_tx_model.appendRow(row)
        self.account_tx_model.setProperty("txs", txs)

    def _add_payment(self):
        if not self._selected_lab_id:
            return
        dlg = LabPaymentDialog(self._selected_lab_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_lab_balances()
            self.refresh_account_detail()

    def _delete_payment(self):
        tx = self._selected_payment()
        if not tx:
            return
        if ask_confirmation(self, "تأكيد", "هل تريد حذف هذه الدفعة؟"):
            db.delete_lab_transaction(tx["id"])
            self.refresh_lab_balances()
            self.refresh_account_detail()

    def _selected_payment(self):
        index = self.account_tx_table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        txs = self.account_tx_model.property("txs") or []
        if 0 <= row < len(txs):
            return txs[row]
        return None

    # -----------------------------------------------------------------
    # Tab: إعدادات البنود العلاجية
    # -----------------------------------------------------------------
    def _build_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)
        layout.setContentsMargins(0, design.SPACING_SM, 0, 0)
        layout.setSpacing(design.SPACING * 2)

        note = QLabel(
            "تحديد أي البنود العلاجية تُصنَّع في المعمل، وأي معمل هو الافتراضي لكل بند، "
            "حتى ترسل تلقائيًا حالة إلى هذا المعمل عند تسجيل هذا العلاج لأي مريض.")
        note.setWordWrap(True)
        note.setObjectName("MutedLabel")
        layout.addWidget(note)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_layout.setSpacing(design.SPACING_SM)
        self.settings_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.settings_container)
        layout.addWidget(scroll, stretch=1)

    def refresh_settings(self):
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        settings = db.get_settings()
        price_list_id = settings.get("active_price_list_id") if settings else None
        if not price_list_id:
            label = QLabel("لا توجد قائمة أسعار فعّالة حاليًا")
            label.setObjectName("MutedLabel")
            self.settings_layout.addWidget(label)
            return

        items = db.get_treatment_items_with_lab_settings(price_list_id)
        labs = db.get_labs(active_only=True)
        lab_values = ["بدون معمل افتراضي"] + [l["name"] for l in labs]

        if not items:
            label = QLabel("لا توجد بنود علاجية مسجلة")
            label.setObjectName("MutedLabel")
            self.settings_layout.addWidget(label)
            return

        for item in items:
            card = Card(padding=True)
            body = card.body()
            body.setSpacing(design.SPACING_SM)

            label_text = ("↳ " if item["is_variant"] else "") + str(item["label"])
            name_label = QLabel(label_text)
            name_label.setObjectName("SectionTitle")
            body.addWidget(name_label)

            row = QHBoxLayout()
            requires_check = QCheckBox("يحتاج معمل")
            requires_check.setChecked(bool(item["requires_lab"]))
            row.addWidget(requires_check)

            row.addWidget(QLabel("المعمل الافتراضي:"))
            lab_combo = ComboBox()
            lab_combo.addItems(lab_values)
            current = _lab_name_by_id(labs, item["default_lab_id"])
            lab_combo.setCurrentText(current if current else "بدون معمل افتراضي")
            row.addWidget(lab_combo)

            row.addWidget(QLabel("الرمز:"))
            code_edit = TextInput(placeholder="رمز عند المعمل")
            code_edit.setText(str(item.get("lab_code") or ""))
            row.addWidget(code_edit, stretch=1)

            save_btn = SecondaryButton("حفظ")
            save_btn.clicked.connect(
                lambda _=False, item=item, rc=requires_check, lc=lab_combo,
                ce=code_edit: self._save_lab_settings(item, rc, lc, ce))
            row.addWidget(save_btn)

            body.addLayout(row)
            self.settings_layout.addWidget(card)

    def _save_lab_settings(self, item, requires_check, lab_combo, code_edit):
        lab_name = lab_combo.currentText()
        lab_id = _lab_id_by_name(db.get_labs(active_only=True), lab_name) \
            if lab_name != "بدون معمل افتراضي" else None
        requires_lab = requires_check.isChecked()
        code = code_edit.text().strip()
        if item["is_variant"]:
            db.update_treatment_variant_lab_settings(
                item["id"], requires_lab, lab_id, code)
        else:
            settings = db.get_settings() or {}
            price_list_id = settings.get("active_price_list_id")
            if price_list_id:
                db.update_treatment_price_lab_settings(
                    price_list_id, item["treatment_key"], requires_lab, lab_id, code)

    # -----------------------------------------------------------------
    def refresh(self):
        self.refresh_orders()
        self.refresh_labs()
        self.refresh_lab_balances()
        self.refresh_settings()