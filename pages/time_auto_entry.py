# -*- coding: utf-8 -*-
"""
حقل إدخال وقت (ساعة : دقيقة) بإدخال يدوي بدل القوائم المنسدلة، مع انتقال
تلقائي من خانة الساعات (أقصى الشمال) لخانة الدقايق (أقصى اليمين) بمجرد ما
تكمّلي رقمين في خانة الساعات، من غير ما تحتاجي تدوسي Tab أو تكتبي ":" بنفسك.
"""
import customtkinter as ctk
import theme


class TimeAutoEntry(ctk.CTkFrame):
    """
    فريم صغير فيه خانة ساعات (شمال) + ":" + خانة دقايق (يمين).
    hour_min/hour_max بيحددوا مدى الساعات المسموح بيه:
    - نظام 24 ساعة: hour_min=0, hour_max=23
    - نظام 12 ساعة: hour_min=1, hour_max=12
    """

    def __init__(self, master, hour_min=0, hour_max=23, on_change=None,
                 entry_width=44, entry_height=34, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.hour_min = hour_min
        self.hour_max = hour_max
        self.on_change = on_change

        # خانة الساعات في أقصى الشمال
        self.hour_entry = ctk.CTkEntry(self, width=entry_width, height=entry_height,
                                        justify="center", font=theme.FONT_NORMAL)
        self.hour_entry.pack(side="left")
        ctk.CTkLabel(self, text=":", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_DARK).pack(side="left", padx=2)
        # خانة الدقايق في أقصى اليمين
        self.minute_entry = ctk.CTkEntry(self, width=entry_width, height=entry_height,
                                          justify="center", font=theme.FONT_NORMAL)
        self.minute_entry.pack(side="left")

        self.hour_entry.insert(0, f"{hour_min:02d}")
        self.minute_entry.insert(0, "00")

        self.hour_entry.bind("<KeyRelease>", self._on_hour_key)
        self.minute_entry.bind("<KeyRelease>", self._on_minute_key)
        self.minute_entry.bind("<BackSpace>", self._on_minute_backspace)

        self.hour_entry.bind("<FocusIn>", lambda e: self.hour_entry.select_range(0, "end"))
        self.minute_entry.bind("<FocusIn>", lambda e: self.minute_entry.select_range(0, "end"))

    def _on_hour_key(self, event):
        if event.keysym in ("Tab", "ISO_Left_Tab", "Shift_L", "Shift_R", "Left", "Right"):
            return
        raw = self.hour_entry.get()
        digits = "".join(ch for ch in raw if ch.isdigit())[:2]
        if digits:
            val = int(digits)
            if val > self.hour_max:
                digits = f"{self.hour_max:02d}"
        if digits != raw:
            self.hour_entry.delete(0, "end")
            self.hour_entry.insert(0, digits)
        # لما تتكمل خانة الساعات (رقمين)، انتقال تلقائي لخانة الدقايق
        if len(digits) >= 2 and event.keysym not in ("BackSpace", "Delete"):
            self.hour_entry.icursor("end")
            self.minute_entry.focus_set()
            self.minute_entry.select_range(0, "end")
        if self.on_change:
            self.on_change()

    def _on_minute_key(self, event):
        if event.keysym in ("Tab", "ISO_Left_Tab", "Shift_L", "Shift_R", "Left", "Right"):
            return
        raw = self.minute_entry.get()
        digits = "".join(ch for ch in raw if ch.isdigit())[:2]
        if digits:
            val = int(digits)
            if val > 59:
                digits = "59"
        if digits != raw:
            self.minute_entry.delete(0, "end")
            self.minute_entry.insert(0, digits)
        if self.on_change:
            self.on_change()

    def _on_minute_backspace(self, event):
        # لو خانة الدقايق فاضية ودست Backspace، بيرجع تلقائي لخانة الساعات
        if self.minute_entry.get() == "" and self.minute_entry.index("insert") == 0:
            self.hour_entry.focus_set()
            self.hour_entry.icursor("end")
            self.hour_entry.select_range(0, "end")

    def get_hour(self):
        raw = "".join(ch for ch in self.hour_entry.get() if ch.isdigit())
        if not raw:
            return self.hour_min
        val = int(raw)
        return max(self.hour_min, min(val, self.hour_max))

    def get_minute(self):
        raw = "".join(ch for ch in self.minute_entry.get() if ch.isdigit())
        if not raw:
            return 0
        val = int(raw)
        return max(0, min(val, 59))

    def set_time(self, hour, minute):
        self.hour_entry.delete(0, "end")
        self.hour_entry.insert(0, f"{int(hour):02d}")
        self.minute_entry.delete(0, "end")
        self.minute_entry.insert(0, f"{int(minute):02d}")

    def focus_hour(self):
        self.hour_entry.focus_set()
        self.hour_entry.select_range(0, "end")
