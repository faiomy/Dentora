# -*- coding: utf-8 -*-
"""Integrations (n8n) page for the Qt version of Dentora.
A form for sending a message to any phone number via the n8n webhook, with a
background send (QThread), a live webhook-status indicator, and a message log
table. Reuses ``database`` helpers and ``n8n_integration`` without importing
Python ``threading``.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt, QThread, Signal, QObject

import database as db
from n8n_integration import send_with_retries, get_n8n_webhook_status
from . import design
from .components import (
    DataTable,
    PrimaryButton,
    SecondaryButton,
    TextInput,
    Card,
)


class _SendWorker(QObject):
    """Runs one n8n send (optional retries) off the UI thread."""

    finished = Signal(int, bool, str)  # record_id, ok, error

    def __init__(self, record_id, phone, message):
        super().__init__()
        self.record_id = record_id
        self.phone = phone
        self.message = message

    def run(self):
        ok, err = send_with_retries(self.phone, self.message)
        if ok:
            db.mark_n8n_message_status(self.record_id, "sent")
        else:
            db.mark_n8n_message_status(self.record_id, "failed", error=err)
        self.finished.emit(self.record_id, ok, err)


class _FlushWorker(QObject):
    """Re-sends all pending messages sequentially in the background."""

    done = Signal()

    def run(self):
        rows = db.get_n8n_pending_messages()
        for r in rows:
            ok, err = send_with_retries(r["phone"], r["message"])
            db.mark_n8n_message_status(r["id"], "sent" if ok else "pending", error=err)
        self.done.emit()


class IntegrationsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sending = False
        self._build_ui()
        self.refresh_log()
        self._flush_pending()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(design.SPACING * 2, design.SPACING,
                                       design.SPACING * 2, design.SPACING * 2)
        root_layout.setSpacing(design.SPACING * 2)

        title = QLabel("تكامل n8n")
        title.setObjectName("PageTitle")
        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch()
        refresh_btn = SecondaryButton("تحديث السجل")
        refresh_btn.clicked.connect(self.refresh_log)
        header_row.addWidget(refresh_btn)
        root_layout.addLayout(header_row)

        # --- Send form card --------------------------------------------
        form_card = Card(padding=True)
        body = form_card.body()
        body.setSpacing(design.SPACING_MD)

        phone_field = QHBoxLayout()
        phone_field.addWidget(QLabel("رقم الجوال:"))
        self.phone_edit = TextInput(placeholder="01xxxxxxxxx")
        phone_field.addWidget(self.phone_edit, stretch=1)
        body.addLayout(phone_field)

        ok, msg = get_n8n_webhook_status()
        self.webhook_label = QLabel(msg)
        if ok:
            self.webhook_label.setObjectName("SuccessLabel")
        else:
            self.webhook_label.setObjectName("MutedLabel")
        body.addWidget(self.webhook_label)

        body.addWidget(QLabel("الرسالة:"))
        self.msg_text = QTextEdit()
        self.msg_text.setPlaceholderText("اكتب الرسالة هنا...")
        self.msg_text.setMaximumHeight(130)
        body.addWidget(self.msg_text)

        self.send_btn = PrimaryButton("إرسال عبر n8n")
        self.send_btn.clicked.connect(self._on_send)
        send_row = QHBoxLayout()
        send_row.addStretch()
        send_row.addWidget(self.send_btn)
        body.addLayout(send_row)

        root_layout.addWidget(form_card)

        # --- Message log -----------------------------------------------
        log_card = Card(padding=True)
        log_body = log_card.body()
        log_body.setSpacing(design.SPACING_SM)
        log_title = QLabel("آخر الرسائل (30)")
        log_title.setObjectName("SectionTitle")
        log_body.addWidget(log_title)

        self.log_table = DataTable()
        self.log_model = QStandardItemModel()
        self.log_model.setHorizontalHeaderLabels(
            ["الحالة", "الرقم", "الرسالة", "المحاولات", "الخطأ"])
        self.log_table.setModel(self.log_model)
        log_body.addWidget(self.log_table)

        root_layout.addWidget(log_card, stretch=1)

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------
    def refresh_log(self):
        rows = db.get_n8n_message_log(limit=30)
        self.log_model.removeRows(0, self.log_model.rowCount())
        for r in rows:
            label, color = {
                "sent": ("تم الإرسال", design.SUCCESS_600),
                "failed": ("فشل الإرسال", design.ERROR_600),
                "pending": ("بانتظار الإرسال", design.WARNING_400),
            }.get(r["status"], (str(r["status"]), design.TEXT_MUTED))
            attempts = str(r.get("attempts") or 0)

            status_item = QStandardItem(label)
            status_item.setForeground(QColor(color))
            row_items = [
                status_item,
                QStandardItem(str(r.get("phone") or "")),
                QStandardItem(str(r.get("message") or "")[:120]),
                QStandardItem(attempts),
                QStandardItem(str(r.get("error") or "")[:80]),
            ]
            self.log_model.appendRow(row_items)
        self.log_model.setProperty("log_rows", rows)

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------
    def _on_send(self):
        if self._sending:
            return
        phone = self.phone_edit.text().strip()
        message = self.msg_text.toPlainText().strip()
        if not phone or not message:
            return

        record_id = db.add_n8n_message(phone, message)
        self.refresh_log()
        self._set_sending(True)

        self._current_thread = QThread(self)
        self._current_worker = _SendWorker(record_id, phone, message)
        self._current_worker.moveToThread(self._current_thread)
        self._current_thread.started.connect(self._current_worker.run)
        self._current_worker.finished.connect(self._on_send_done)
        self._current_worker.finished.connect(self._current_thread.quit)
        self._current_thread.finished.connect(self._current_thread.deleteLater)
        self._current_thread.start()

    def _set_sending(self, sending):
        self._sending = sending
        self.send_btn.setEnabled(not sending)
        self.send_btn.setText("جارٍ الإرسال..." if sending else "إرسال عبر n8n")

    def _on_send_done(self, record_id, ok, err):
        if self._sending:
            self._set_sending(False)
            self.refresh_log()
            if ok:
                self.msg_text.clear()

    # ------------------------------------------------------------------
    # Pending flush (on page open)
    # ------------------------------------------------------------------
    def _flush_pending(self):
        pending = db.get_n8n_pending_messages()
        if not pending:
            return
        self._flush_thread = QThread(self)
        self._flush_worker = _FlushWorker()
        self._flush_worker.moveToThread(self._flush_thread)
        self._flush_thread.started.connect(self._flush_worker.run)
        self._flush_worker.done.connect(self.refresh_log)
        self._flush_worker.done.connect(self._flush_thread.quit)
        self._flush_thread.finished.connect(self._flush_thread.deleteLater)
        self._flush_thread.start()