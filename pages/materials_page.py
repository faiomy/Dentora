# -*- coding: utf-8 -*-
"""
صفحة المصروفات
كل مصروف بيتسجل بتاريخه ومبلغه وبينضاف تلقائياً لحسابات العيادة الإجمالية

تصنيفات المصروفات معروضة كتبويبات أيقونية صغيرة (زي صف أيقونات
بيانات/حسابات/أسنان في صفحة المرضى) بدل المنسدلة القديمة - كل تبويب
بيفلتر المصروفات المعروضة على تصنيفه بس، وصف التبويبات نفسه متسنتر في
نص الصفحة. زرار "إضافة مصروف" موجود في هيدر الصفحة ويفتح ديالوج لإضافة
مصروف جديد في أي تصنيف. عمود الموردين المشترك متشال للوقت الحالي لأن
الموردين هيتم التعامل معهم جوه كل تبويب بشكل مستقل بعدين.
"""

import customtkinter as ctk
import theme
import database as db
from pages.rtl_entry import RTLEntry
from pages.patients_page import _Tooltip
from pages.expense_icons import get_category_icon


class MaterialsPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._active_category = db.EXPENSE_CATEGORIES[0]
        self._category_tab_buttons = {}
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        theme.make_shadowed_button(header, "＋ إضافة مصروف", command=self._open_add_expense_dialog,
                                   width=140, height=36, font=theme.FONT_SUBTITLE).pack(side="left")

        ctk.CTkLabel(header, text="المصروفات", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")

        # صف تبويبات أيقونية صغيرة لتصنيفات المصروفات - بديل المنسدلة
        # القديمة، بنفس أسلوب صف أيقونات صفحة المرضى (GlassIconButton)،
        # ومتسنتر في نص الصفحة (مش ملزّق يمين ولا شمال)
        tabs_outer = ctk.CTkFrame(self, fg_color="transparent")
        tabs_outer.pack(fill="x", pady=(0, 12))
        tabs_row = ctk.CTkFrame(tabs_outer, fg_color="transparent")
        tabs_row.pack(anchor="center")
        accent = theme.ACCENT_BORDER
        # نسبة تكبير الأيقونات هنا تحديدًا +60% عن الحجم الافتراضي
        # (0.62 من أصغر ضلع في الزرار) لأنها كانت بادية صغيرة جوه المربعات
        icon_scale = 0.62 * 1.6
        for name in db.EXPENSE_CATEGORIES:
            btn = theme.GlassIconButton(
                tabs_row, text="", width=48, height=36, accent_color=accent,
                canvas_bg=theme.BG_MAIN, active=(name == self._active_category),
                font=(theme.FONT_FAMILY, 18), corner_radius=10,
                icon_image=get_category_icon(name), icon_scale=icon_scale,
                command=(lambda n=name: self._on_category_tab_click(n)))
            btn.pack(side="right", padx=4)
            # فونط التلميح هنا أكبر 4 بيكسل من الافتراضي (14 بدل 10) —
            # خاص بأيقونات صفحة المصروفات بس، من غير ما يأثر على أي
            # تلميحات تانية في البرنامج بتستخدم نفس الكلاس
            _Tooltip(btn.canvas, name, font_size=14)
            self._category_tab_buttons[name] = btn

        # عمود المصروفات (بعرض الصفحة بالكامل دلوقتي بعد ما اتشال عمود
        # الموردين المشترك)
        self.expenses_container = ctk.CTkScrollableFrame(self, fg_color=theme.CARD_BG, corner_radius=12)
        self.expenses_container.pack(fill="both", expand=True)

        self._refresh_expenses()

    # ---------------- تبويبات التصنيف ----------------

    def _on_category_tab_click(self, name):
        if name == self._active_category:
            return
        self._active_category = name
        for cat_name, btn in self._category_tab_buttons.items():
            btn.set_active(cat_name == name)
        self._refresh_expenses()

    # ---------------- المصروفات ----------------

    def _refresh_expenses(self):
        for w in self.expenses_container.winfo_children():
            w.destroy()

        expenses = db.get_expenses(category=self._active_category)

        if not expenses:
            ctk.CTkLabel(self.expenses_container, text="لا توجد مصروفات مسجلة في هذا التصنيف",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED).pack(pady=40)
            return

        total = sum(e["amount"] for e in expenses)
        total_label = ctk.CTkLabel(
            self.expenses_container, text=f"إجمالي مصروفات {self._active_category}: {total:g} جنيه",
            font=theme.FONT_SUBTITLE, text_color=theme.DANGER)
        total_label.pack(anchor="e", padx=16, pady=(14, 10))

        for e in expenses:
            row = ctk.CTkFrame(self.expenses_container, fg_color=theme.BG_MAIN, corner_radius=8)
            row.pack(fill="x", padx=16, pady=4)

            ctk.CTkButton(row, text="حذف", width=50, height=28, fg_color=theme.DANGER,
                          font=theme.FONT_SMALL,
                          command=lambda eid=e["id"]: self._delete_expense(eid)).pack(
                side="left", padx=8, pady=8)

            ctk.CTkLabel(row, text=f"{e['amount']:g} جنيه", font=theme.FONT_SUBTITLE,
                         text_color=theme.DANGER, width=110, anchor="w").pack(
                side="left", padx=8, pady=8)

            ctk.CTkLabel(row, text=e["expense_date"], font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED, width=90, anchor="e").pack(
                side="right", padx=(0, 8), pady=8)

            desc = e["item_name"]
            if e.get("supplier_name"):
                desc += f"  -  مورد: {e['supplier_name']}"
            ctk.CTkLabel(row, text=desc, font=theme.FONT_NORMAL, text_color=theme.TEXT_DARK,
                         anchor="e").pack(side="right", padx=8, pady=8, fill="x", expand=True)

    def _delete_expense(self, expense_id):
        db.delete_expense(expense_id)
        self._refresh_expenses()

    def _open_add_expense_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("إضافة مصروف")
        dialog.geometry("360x520")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="إضافة مصروف جديد", font=theme.FONT_SUBTITLE).pack(pady=(16, 14))

        ctk.CTkLabel(dialog, text="التصنيف", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        category_menu = ctk.CTkOptionMenu(dialog, values=db.EXPENSE_CATEGORIES, width=280,
                                           **theme.optionmenu_colors())
        category_menu.set(self._active_category)
        category_menu.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(dialog, text="اسم البند", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        item_entry = RTLEntry(dialog, width=280, height=40)
        item_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(dialog, text="المبلغ", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        amount_entry = ctk.CTkEntry(dialog, width=280, height=40, justify="right", font=theme.FONT_NORMAL)
        amount_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(dialog, text="التاريخ (YYYY-MM-DD)", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        date_entry = ctk.CTkEntry(dialog, width=280, height=40, justify="right", font=theme.FONT_NORMAL)
        from datetime import datetime
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.pack(padx=30, pady=(2, 16), anchor="e")

        def save():
            try:
                amount = float(amount_entry.get().strip())
            except ValueError:
                return
            item_name = item_entry.get().strip()
            if not item_name or amount <= 0:
                return
            db.add_expense(category_menu.get(), item_name, amount,
                            expense_date=date_entry.get().strip())
            dialog.destroy()
            self._refresh_expenses()

        ctk.CTkButton(dialog, text="حفظ المصروف", height=44, fg_color=theme.SUCCESS,
                      command=save).pack(padx=30, pady=10, fill="x")
