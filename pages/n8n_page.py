# -*- coding: utf-8 -*-
"""
Simple n8n integration page.
Provides a form to send a message via n8n webhook.
"""

import os
import customtkinter as ctk
from tkinter import messagebox

# Import the integration helper (will be created)
try:
    from n8n_integration import send_message_via_n8n
except Exception:
    send_message_via_n8n = None


class N8nPage(ctk.CTkFrame):
    """Page UI for sending messages through n8n."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()

    def _build_ui(self):
        # Title
        ctk.CTkLabel(self, text="تكامل n8n", font=("Helvetica", 20, "bold")).pack(pady=12)

        # Phone entry
        phone_frame = ctk.CTkFrame(self)
        phone_frame.pack(pady=8, fill="x", padx=20)
        ctk.CTkLabel(phone_frame, text="رقم الجوال:", width=80, anchor="e").pack(side="left")
        self.phone_entry = ctk.CTkEntry(phone_frame)
        self.phone_entry.pack(side="right", fill="x", expand=True)

        # Message entry
        msg_frame = ctk.CTkFrame(self)
        msg_frame.pack(pady=8, fill="both", expand=True, padx=20)
        ctk.CTkLabel(msg_frame, text="الرسالة:", anchor="nw").pack(anchor="w")
        self.msg_text = ctk.CTkTextbox(msg_frame, height=6)
        self.msg_text.pack(fill="both", expand=True)

        # Send button
        btn = ctk.CTkButton(self, text="إرسال عبر n8n", command=self._on_send)
        btn.pack(pady=12)

    def _on_send(self):
        phone = self.phone_entry.get().strip()
        message = self.msg_text.get("1.0", "end").strip()
        if not phone or not message:
            messagebox.showerror("خطأ", "يرجى ملء رقم الجوال والرسالة.")
            return
        if send_message_via_n8n is None:
            messagebox.showerror("خطأ", "وظيفة n8n غير متاحة. تأكد من وجود n8n_integration.py.")
            return
        try:
            send_message_via_n8n(phone, message)
            messagebox.showinfo("تم", "تم إرسال الرسالة عبر n8n.")
        except Exception as e:
            messagebox.showerror("فشل الإرسال", str(e))
