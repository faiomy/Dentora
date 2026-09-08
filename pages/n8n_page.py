# -*- coding: utf-8 -*-
"""
صفحة تكامل n8n
بتوفر فورم إرسال رسالة لأي رقم عن طريق webhook بتاع n8n.

الرسالة بتتبعت في الخلفية (thread) من غير ما توقف الواجهة، وبتتعمل
3 محاولات مع انتظار متزايد بينهم، ونتيجة كل رسالة بتتسجل في جدول
n8n_message_log. الرسالة اللي فشلت بعد كل المحاولات بتتعاد محاولتها
تاني أول ما البرنامج يفتح (طالما عدّد محاولاتها الإجمالي أقل من الحد
الأقصى) - شوف database.get_n8n_pending_messages().
"""

import threading

import customtkinter as ctk

import theme
import database as db
from n8n_integration import send_with_retries, get_n8n_webhook_status
from pages import components as ui
from pages.components import PageHeader, empty_state


class N8nPage(ctk.CTkFrame):
    """صفحة إرسال الرسائل عبر n8n + سجل حالة الإرسال."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = PageHeader(self, "تكامل n8n")
        header.pack(fill="x", pady=(0, 12))
        header.add_action("تحديث السجل", self._refresh_log, kind="subtle",
                          width=120, height=34)

        # ---------------- كارت الفورم ----------------
        form_card = ui.card(self)
        form_card.pack(fill="x")

        phone_row = ui.FormFieldRow(form_card, "رقم الجوال")
        phone_row.pack(fill="x", padx=20, pady=(20, 8))
        self.phone_entry = ui.add_themed_entry(phone_row, width=260, height=40,
                                               justify="right",
                                               font=theme.FONT_NORMAL)

        # حالة الويب هوك - عرض فقط، بيوضّح لو متغيرات البيئة متظبطة ولا لأ
        webhook_ok, webhook_msg = get_n8n_webhook_status()
        ctk.CTkLabel(form_card, text=webhook_msg,
                     font=theme.FONT_SMALL,
                     text_color=theme.SUCCESS if webhook_ok else theme.WARNING).pack(
            anchor="e", padx=20, pady=(0, 8))

        ctk.CTkLabel(form_card, text="الرسالة:", font=theme.FONT_NORMAL,
                     text_color=theme.INPUT_LABEL_COLOR, anchor="e").pack(
            fill="x", padx=20, pady=(0, 4))
        self.msg_text = ctk.CTkTextbox(form_card, height=130, font=theme.FONT_NORMAL)
        theme.apply_sunken_style(self.msg_text)
        self.msg_text.pack(fill="x", padx=20, pady=(0, 14))

        self.send_btn = ui.toolbar_button(form_card, "إرسال عبر n8n", self._on_send,
                                          kind="primary", width=180, height=42)
        self.send_btn.pack(anchor="e", padx=20, pady=(0, 20))

        # ---------------- سجل الإرسال ----------------
        log_card = ui.card(self)
        log_card.pack(fill="both", expand=True, pady=(12, 0))
        ctk.CTkLabel(log_card, text="آخر الرسائل", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", padx=20, pady=(16, 8))
        self.log_area = ctk.CTkScrollableFrame(log_card, fg_color="transparent")
        self.log_area.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._refresh_log()

        # أول ما الصفحة تفتح: إعادة إرسال الرسايل المعلّقة من تشغيل سابق
        self._flush_pending()

    # ---------------- السجل ----------------

    def _refresh_log(self):
        for w in self.log_area.winfo_children():
            w.destroy()

        rows = db.get_n8n_message_log(limit=30)
        if not rows:
            empty_state(self.log_area, "لا يوجد إرسال محفوظ بعد", pady=24)
            return

        for r in rows:
            row = ui.inner_row(self.log_area)
            row.pack(fill="x", padx=8, pady=3)

            status, color = {
                "sent": ("تم الإرسال", theme.SUCCESS),
                "failed": ("فشل الإرسال", theme.DANGER),
                "pending": ("بانتظار الإرسال", theme.WARNING),
            }.get(r["status"], (r["status"], theme.TEXT_MUTED))
            attempts_note = f" ({r['attempts']} محاولات)" if r["attempts"] > 1 else ""
            ctk.CTkLabel(row, text=status + attempts_note, font=theme.FONT_SMALL,
                         text_color=color, width=170, anchor="e").pack(
                side="right", padx=8, pady=6)

            message_preview = (r["message"] or "")[:80]
            ctk.CTkLabel(row, text=message_preview, font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED, anchor="e").pack(
                side="right", padx=8, pady=6, fill="x", expand=True)

            ctk.CTkLabel(row, text=r["phone"], font=theme.FONT_SMALL,
                         text_color=theme.TEXT_DARK, width=130, anchor="e").pack(
                side="right", padx=8, pady=6)

            if r["error"]:
                ctk.CTkLabel(row, text=r["error"][:60], font=theme.FONT_SMALL,
                             text_color=theme.DANGER, anchor="w").pack(
                    side="left", padx=8, pady=6)

    # ---------------- الإرسال ----------------

    def _on_send(self):
        phone = self.phone_entry.get().strip()
        message = self.msg_text.get("1.0", "end").strip()
        if not phone or not message:
            theme.show_toast(self, "اكتب رقم الجوال والرسالة الأول", kind="error")
            return

        record_id = db.add_n8n_message(phone, message)
        self._refresh_log()
        self._set_sending(True)

        def work():
            ok, err = send_with_retries(phone, message)
            if ok:
                db.mark_n8n_message_status(record_id, "sent")
            else:
                # فشلت بعد كل محاولاتها - هتتعاد تلقائيًا أول ما البرنامج
                # يفتح تاني (طالما عدّد محاولاتها أقل من الحد الأقصى)
                db.mark_n8n_message_status(record_id, "failed", error=err)
            self.after(0, lambda: self._on_send_done(ok, err))

        threading.Thread(target=work, daemon=True).start()

    def _set_sending(self, sending):
        try:
            self.send_btn.configure(state="disabled" if sending else "normal",
                                    text="جارٍ الإرسال..." if sending else "إرسال عبر n8n")
        except Exception:
            pass

    def _on_send_done(self, ok, err):
        self._set_sending(False)
        self._refresh_log()
        if ok:
            self.msg_text.delete("1.0", "end")
            theme.show_toast(self, "تم إرسال الرسالة عبر n8n")
        else:
            theme.show_toast(self, "فشل الإرسال - هتتعاد المحاولة عند فتح البرنامج",
                             kind="error")

    # ---------------- إعادة إرسال المعلّق عند الفتح ----------------

    def _flush_pending(self):
        rows = db.get_n8n_pending_messages()
        if not rows:
            return

        def work():
            # إرسال متسلسل (مش متوازي) عشان مش نزنق الويب هوك بعدد رسايل
            # فجأة لو في كمية معلقة كبيرة - والنتيجة بتتسجل لكل رسالة لوحدها
            for r in rows:
                ok, err = send_with_retries(r["phone"], r["message"])
                if ok:
                    db.mark_n8n_message_status(r["id"], "sent")
                else:
                    db.mark_n8n_message_status(r["id"], "pending", error=err)
            self.after(0, self._refresh_log)

        threading.Thread(target=work, daemon=True).start()
