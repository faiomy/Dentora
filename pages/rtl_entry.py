# -*- coding: utf-8 -*-
"""
ويدجت بديل لحقل الإدخال العادي (CTkEntry) عشان يدعم الكتابة العربية صح.
المشكلة: حقل Entry العادي في Tkinter مش بيطبق خوارزمية اتجاه الكتابة (bidi)
صح، فبيظهر العربي وهو بيتكتب من الشمال لليمين بدل العكس.
الحل: بنستخدم صندوق نص (Text) بسطر واحد، لأنه بيدعم الاتجاه العربي بشكل أفضل.
"""

import customtkinter as ctk


class RTLEntry(ctk.CTkTextbox):
    def __init__(self, master, width=250, height=40, placeholder_text="", **kwargs):
        kwargs.setdefault("wrap", "none")
        super().__init__(master, width=width, height=height, **kwargs)
        self._placeholder = placeholder_text
        self._has_placeholder = False

        # منع إنزال سطر جديد لما تدوس Enter (عشان يفضل حقل بسطر واحد)
        self.bind("<Return>", lambda e: "break")
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._show_placeholder)

        # محاذاة النص لليمين
        try:
            self._textbox.tag_configure("rtl", justify="right")
            self._textbox.tag_add("rtl", "1.0", "end")
        except Exception:
            pass

        if placeholder_text:
            self._show_placeholder()

    def _clear_placeholder(self, event=None):
        if self._has_placeholder:
            super().delete("1.0", "end")
            self._has_placeholder = False
            self.configure(text_color=("#1B1E23", "#FFFFFF"))

    def _show_placeholder(self, event=None):
        if not super().get("1.0", "end-1c").strip():
            super().delete("1.0", "end")
            super().insert("1.0", self._placeholder)
            self._has_placeholder = True
            self.configure(text_color=("#9CA3AF", "#9CA3AF"))

    def get(self, *args):
        if self._has_placeholder:
            return ""
        return super().get("1.0", "end-1c")

    def insert(self, index, text):
        """متوافق مع استدعاء entry.insert(0, text) القديم"""
        self._has_placeholder = False
        self.configure(text_color=("#1B1E23", "#FFFFFF"))
        super().delete("1.0", "end")
        super().insert("1.0", text)
        try:
            self._textbox.tag_add("rtl", "1.0", "end")
        except Exception:
            pass

    def delete(self, *args):
        super().delete("1.0", "end")
