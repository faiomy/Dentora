# -*- coding: utf-8 -*-
"""
صفحة حسابات العيادة الإجمالية: الإيرادات (المدفوع من المرضى) مقابل المصروفات،
وصافي الربح أو الخسارة، خلال أي فترة (يوم/شهر/سنة/فترة مخصصة)
"""

from datetime import date, datetime, timedelta
import customtkinter as ctk
import theme
import database as db


class ClinicAccountsPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        today = date.today()
        self.start_date = today.replace(day=1)
        self.end_date = today
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(header, text="حسابات العيادة", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")

        # أزرار فترات سريعة
        quick_row = ctk.CTkFrame(self, fg_color="transparent")
        quick_row.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(quick_row, text="اليوم", width=90, height=34, fg_color=theme.PRIMARY_LIGHT,
                      command=self._set_today).pack(side="right", padx=4)
        ctk.CTkButton(quick_row, text="هذا الشهر", width=90, height=34, fg_color=theme.PRIMARY_LIGHT,
                      command=self._set_this_month).pack(side="right", padx=4)
        ctk.CTkButton(quick_row, text="هذه السنة", width=90, height=34, fg_color=theme.PRIMARY_LIGHT,
                      command=self._set_this_year).pack(side="right", padx=4)

        # فترة مخصصة
        custom_row = ctk.CTkFrame(self, fg_color="transparent")
        custom_row.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(custom_row, text="من:", font=theme.FONT_NORMAL).pack(side="right", padx=(0, 4))
        self.start_entry = ctk.CTkEntry(custom_row, width=120, justify="center", font=theme.FONT_NORMAL)
        self.start_entry.insert(0, self.start_date.isoformat())
        self.start_entry.pack(side="right", padx=4)
        ctk.CTkLabel(custom_row, text="إلى:", font=theme.FONT_NORMAL).pack(side="right", padx=(8, 4))
        self.end_entry = ctk.CTkEntry(custom_row, width=120, justify="center", font=theme.FONT_NORMAL)
        self.end_entry.insert(0, self.end_date.isoformat())
        self.end_entry.pack(side="right", padx=4)
        ctk.CTkButton(custom_row, text="تطبيق الفترة", width=110, height=34, fg_color=theme.ACCENT_BORDER,
                      command=self._apply_custom_range).pack(side="right", padx=8)

        self.content_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True)

        self.refresh()

    def _set_today(self):
        self.start_date = self.end_date = date.today()
        self._sync_entries()
        self.refresh()

    def _set_this_month(self):
        today = date.today()
        self.start_date = today.replace(day=1)
        self.end_date = today
        self._sync_entries()
        self.refresh()

    def _set_this_year(self):
        today = date.today()
        self.start_date = today.replace(month=1, day=1)
        self.end_date = today
        self._sync_entries()
        self.refresh()

    def _sync_entries(self):
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, self.start_date.isoformat())
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, self.end_date.isoformat())

    def _apply_custom_range(self):
        try:
            self.start_date = datetime.strptime(self.start_entry.get().strip(), "%Y-%m-%d").date()
            self.end_date = datetime.strptime(self.end_entry.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            return
        self.refresh()

    def refresh(self):
        for w in self.content_area.winfo_children():
            w.destroy()

        start = self.start_date.isoformat()
        end = self.end_date.isoformat()

        financials = db.get_clinic_financials(start, end)
        profit = financials["profit"]
        profit_color = theme.SUCCESS if profit >= 0 else theme.DANGER
        profit_label = "صافي الربح" if profit >= 0 else "صافي الخسارة"

        summary_card = ctk.CTkFrame(self.content_area, fg_color=theme.CARD_BG, corner_radius=12)
        summary_card.pack(fill="x", pady=6)
        summary_row = ctk.CTkFrame(summary_card, fg_color="transparent")
        summary_row.pack(fill="x", padx=20, pady=20)

        for label, value, color in [
            ("الإيرادات (المحصّل من المرضى)", financials["revenue"], theme.SUCCESS),
            ("المصروفات", financials["expenses"], theme.DANGER),
            (profit_label, abs(profit), profit_color),
        ]:
            box = ctk.CTkFrame(summary_row, fg_color=theme.BG_MAIN, corner_radius=10)
            box.pack(side="right", fill="both", expand=True, padx=6)
            ctk.CTkLabel(box, text=label, font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_MUTED).pack(pady=(16, 4))
            ctk.CTkLabel(box, text=f"{value:g} جنيه", font=theme.FONT_TITLE,
                         text_color=color).pack(pady=(0, 16))

        # تفصيل المصروفات حسب التصنيف
        by_category = db.get_expenses_by_category(start, end)
        cat_card = ctk.CTkFrame(self.content_area, fg_color=theme.CARD_BG, corner_radius=12)
        cat_card.pack(fill="x", pady=6)
        ctk.CTkLabel(cat_card, text="المصروفات حسب التصنيف", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", padx=20, pady=(16, 8))

        if not by_category:
            ctk.CTkLabel(cat_card, text="لا توجد مصروفات في هذه الفترة", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(anchor="e", padx=20, pady=(0, 16))
        else:
            for c in by_category:
                row = ctk.CTkFrame(cat_card, fg_color=theme.BG_MAIN, corner_radius=8)
                row.pack(fill="x", padx=20, pady=4)
                ctk.CTkLabel(row, text=f"{c['total']:g} جنيه", font=theme.FONT_NORMAL,
                             text_color=theme.DANGER, anchor="w").pack(side="left", padx=10, pady=8)
                ctk.CTkLabel(row, text=c["category"], font=theme.FONT_NORMAL,
                             text_color=theme.TEXT_DARK, anchor="e").pack(side="right", padx=10, pady=8)
            ctk.CTkFrame(cat_card, fg_color="transparent", height=10).pack()

        # عمولات الأطباء في نفس الفترة (مفيد لمعرفة صافي الربح الحقيقي بعد العمولات)
        commissions = db.get_doctor_commissions_summary(start, end)
        comm_card = ctk.CTkFrame(self.content_area, fg_color=theme.CARD_BG, corner_radius=12)
        comm_card.pack(fill="x", pady=6)
        ctk.CTkLabel(comm_card, text="عمولات الأطباء في نفس الفترة", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", padx=20, pady=(16, 8))

        if not commissions:
            ctk.CTkLabel(comm_card, text="لا توجد عمولات مسجلة في هذه الفترة", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(anchor="e", padx=20, pady=(0, 16))
        else:
            for c in commissions:
                row = ctk.CTkFrame(comm_card, fg_color=theme.BG_MAIN, corner_radius=8)
                row.pack(fill="x", padx=20, pady=4)
                ctk.CTkLabel(row, text=f"{c['total_commission']:g} جنيه", font=theme.FONT_NORMAL,
                             text_color=theme.WARNING, anchor="w").pack(side="left", padx=10, pady=8)
                ctk.CTkLabel(row, text=f"{c['doctor_name']}  ({c['treatments_count']} إجراء)",
                             font=theme.FONT_NORMAL, text_color=theme.TEXT_DARK,
                             anchor="e").pack(side="right", padx=10, pady=8)
            ctk.CTkFrame(comm_card, fg_color="transparent", height=10).pack()
