# -*- coding: utf-8 -*-
"""
حقل تاريخ بيحط علامات التقسيم (يوم/شهر/سنة) تلقائيًا وانت بس بتكتب أرقام،
من غير ما تحتاجي تكتبي "/" بنفسك.
"""
import customtkinter as ctk


class DateAutoEntry(ctk.CTkEntry):
    def __init__(self, master, on_change=None, **kwargs):
        kwargs.setdefault("justify", "center")
        kwargs.setdefault("placeholder_text", "DD/MM/YYYY")
        super().__init__(master, **kwargs)
        self.on_change = on_change
        self.bind("<KeyRelease>", self._on_key_release)

    def _on_key_release(self, event):
        if event.keysym in ("BackSpace", "Delete", "Left", "Right", "Tab", "Shift_L", "Shift_R"):
            if self.on_change:
                self.on_change()
            return
        raw = self.get()
        digits = "".join(ch for ch in raw if ch.isdigit())[:8]
        if len(digits) > 4:
            formatted = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"
        elif len(digits) > 2:
            formatted = f"{digits[:2]}/{digits[2:]}"
        else:
            formatted = digits
        if formatted != raw:
            self.delete(0, "end")
            self.insert(0, formatted)
        if self.on_change:
            self.on_change()

    def get_iso_date(self):
        """بترجع التاريخ بصيغة YYYY-MM-DD لو التاريخ مكتمل، أو فاضي لو ناقص"""
        raw = self.get().strip()
        parts = raw.split("/")
        if len(parts) == 3 and all(p.isdigit() for p in parts) and len(parts[2]) == 4:
            day, month, year = parts
            try:
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            except ValueError:
                return ""
        return ""

    def set_iso_date(self, iso_str):
        if not iso_str:
            return
        try:
            year, month, day = iso_str.split("-")
            self.delete(0, "end")
            self.insert(0, f"{int(day):02d}/{int(month):02d}/{year}")
        except Exception:
            pass
