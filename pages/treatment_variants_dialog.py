# -*- coding: utf-8 -*-
"""
نافذة إدارة الأنواع الفرعية (الخامات) لكل بند من بنود المعالجات
مثال: تحت "تركيب تاج" تقدر تضيف زيركونيا/بورسلين/إيماكس... كل واحد بسعره ولونه
"""

import customtkinter as ctk
from tkinter import colorchooser, messagebox
import theme
import database as db
from pages.rtl_entry import RTLEntry
from pages import tooth_symbols


class TreatmentVariantsDialog(ctk.CTkToplevel):
    def __init__(self, master, price_list_id, on_change=None, focus_treatment_key=None):
        super().__init__(master)
        self.price_list_id = price_list_id
        self.on_change = on_change
        self.focus_treatment_key = focus_treatment_key
        self.title("إدارة الإجراءات الطبية")
        self.geometry("700x680")
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="إدارة الإجراءات الطبية", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(pady=(16, 4))
        ctk.CTkLabel(self,
                     text="من هنا تقدر تعدّل اسم أي إجراء أو تحذفه بالكامل، وكمان تضيف أنواعه الفرعية\n"
                          "والخامات (مثلاً زيركونيا وبورسلين وإيماكس تحت بند 'تركيب تاج')، كل نوع بسعره\n"
                          "ولونه الخاص. عند تسجيل معالجة على سن، سيسأل البرنامج عن اختيار أي نوع منها.",
                     font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                     wraplength=640, justify="center").pack(pady=(0, 12))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=theme.BG_MAIN)
        self.scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self._render()

    def _render(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        prices = db.get_treatment_prices(self.price_list_id)
        if not prices:
            ctk.CTkLabel(self.scroll, text="لا توجد بنود معالجة في هذه القائمة بعد.\nيُرجى إضافة بند من صفحة الإجراءات أولًا.",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED).pack(pady=30)
            return

        # لو محدد بند معين نبدأ بيه فوق
        keys_order = list(prices.keys())
        if self.focus_treatment_key and self.focus_treatment_key in keys_order:
            keys_order.remove(self.focus_treatment_key)
            keys_order.insert(0, self.focus_treatment_key)

        for key in keys_order:
            self._render_treatment_section(key, prices[key])

    def _render_treatment_section(self, treatment_key, info):
        section = ctk.CTkFrame(self.scroll, fg_color=theme.CARD_BG, corner_radius=10,
                                border_width=2 if treatment_key == self.focus_treatment_key else 0,
                                border_color=theme.ACCENT_BORDER)
        section.pack(fill="x", pady=6)

        is_builtin = treatment_key in tooth_symbols.BUILTIN_TREATMENT_KEYS

        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(10, 4))

        # اسم الإجراء - قابل للتعديل مباشرة من هنا
        name_entry = RTLEntry(header, width=190, height=32, font=theme.FONT_NORMAL)
        name_entry.insert(0, info["label"])
        name_entry.pack(side="right")

        def save_name():
            new_name = name_entry.get().strip()
            if not new_name:
                return
            db.update_treatment_price(
                self.price_list_id, treatment_key, new_name, info["price"],
                info["commission_percent"], color=info.get("color"), symbol_key=info.get("symbol_key"))
            self._render()
            if self.on_change:
                self.on_change()

        ctk.CTkButton(header, text="حفظ الاسم", width=90, height=30, fg_color=theme.SUCCESS,
                      hover_color=theme.lighten_color(theme.SUCCESS, 0.15),
                      font=theme.FONT_SMALL, command=save_name).pack(side="right", padx=6)

        ctk.CTkLabel(header, text=f"(السعر الأساسي: {info['price']:g} جنيه)", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(side="right", padx=8)

        if is_builtin:
            ctk.CTkLabel(header, text="بند أساسي", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="left", padx=4)
        ctk.CTkButton(header, text="حذف الإجراء بالكامل", width=140, height=30, fg_color=theme.DANGER,
                      hover_color=theme.lighten_color(theme.DANGER, 0.15),
                      font=theme.FONT_SMALL,
                      command=lambda: self._delete_treatment(treatment_key, info["label"])).pack(
            side="left", padx=4)

        variants = db.get_treatment_variants(self.price_list_id, treatment_key)
        if not variants:
            ctk.CTkLabel(section, text="لا توجد أنواع فرعية مضافة بعد لهذا البند",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(anchor="e", padx=18, pady=2)
        for v in variants:
            self._render_variant_row(section, v)

        self._render_new_variant_row(section, treatment_key)

    def _delete_treatment(self, treatment_key, label):
        confirmed = messagebox.askyesno(
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف إجراء \"{label}\" بالكامل؟\n"
            "سيتم حذف كل أنواعه الفرعية معه، ولن يظهر بعد ذلك في شارت الأسنان.",
            parent=self)
        if not confirmed:
            return
        db.delete_treatment_price(self.price_list_id, treatment_key)
        self._render()
        if self.on_change:
            self.on_change()

    def _pick_color(self, current_color, on_pick):
        popup = ctk.CTkToplevel(self)
        popup.title("اختر لون")
        popup.geometry("300x260")
        popup.grab_set()

        ctk.CTkLabel(popup, text="اختر لون مميز لهذا النوع", font=theme.FONT_NORMAL).pack(pady=(14, 8))

        grid = ctk.CTkFrame(popup, fg_color="transparent")
        grid.pack(padx=14)
        for i, color in enumerate(theme.TREATMENT_COLOR_PALETTE):
            def pick(c=color):
                popup.destroy()
                on_pick(c)
            ctk.CTkButton(grid, text="✓" if color == current_color else "", text_color="#FFFFFF",
                          width=30, height=30, corner_radius=15,
                          fg_color=color, hover_color=color, command=pick).grid(
                row=i // 6, column=5 - (i % 6), padx=3, pady=3)

        def custom_pick():
            picked = colorchooser.askcolor(title="لون مخصص", initialcolor=current_color)
            if picked and picked[1]:
                popup.destroy()
                on_pick(picked[1])

        ctk.CTkButton(popup, text="لون مخصص...", height=34, fg_color=theme.BG_MAIN,
                      text_color=theme.TEXT_DARK, border_width=1, border_color=theme.BORDER,
                      command=custom_pick).pack(padx=14, pady=(14, 10), fill="x")

    def _render_variant_row(self, parent, v):
        row = ctk.CTkFrame(parent, fg_color=theme.BG_MAIN, corner_radius=8)
        row.pack(fill="x", padx=14, pady=3)

        ctk.CTkButton(row, text="حذف", width=48, height=30, fg_color=theme.DANGER,
                      font=theme.FONT_SMALL,
                      command=lambda: self._delete_variant(v["id"])).pack(side="left", padx=6, pady=6)

        color_state = {"value": v.get("color") or "#1E88E5"}
        swatch = ctk.CTkButton(row, text="", width=30, height=30, corner_radius=6,
                                fg_color=color_state["value"], hover_color=color_state["value"],
                                border_width=1, border_color=theme.BORDER)
        swatch.pack(side="right", padx=(6, 4), pady=6)

        def choose_color():
            def apply(picked_color):
                color_state["value"] = picked_color
                swatch.configure(fg_color=picked_color, hover_color=picked_color)
            self._pick_color(color_state["value"], apply)

        swatch.configure(command=choose_color)

        commission_entry = ctk.CTkEntry(row, width=75, height=32, justify="center", font=theme.FONT_SMALL)
        commission_entry.insert(0, f"{v.get('commission_percent', 0):g}")
        commission_entry.pack(side="right", padx=4, pady=6)
        ctk.CTkLabel(row, text="عمولة%", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(side="right")

        price_entry = ctk.CTkEntry(row, width=85, height=32, justify="center", font=theme.FONT_SMALL)
        price_entry.insert(0, f"{v['price']:g}")
        price_entry.pack(side="right", padx=4, pady=6)

        name_entry = RTLEntry(row, width=160, height=32)
        name_entry.insert(0, v["variant_name"])
        name_entry.pack(side="right", padx=4, pady=6)

        def save():
            name = name_entry.get().strip()
            if not name:
                return
            try:
                price = float(price_entry.get().strip() or 0)
                commission = float(commission_entry.get().strip() or 0)
            except ValueError:
                return
            db.update_treatment_variant(v["id"], name, price, commission, color_state["value"])
            if self.on_change:
                self.on_change()

        ctk.CTkButton(row, text="حفظ", width=55, height=30, fg_color=theme.SUCCESS,
                      font=theme.FONT_SMALL, command=save).pack(side="left", padx=4, pady=6)

    def _render_new_variant_row(self, parent, treatment_key):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(4, 12))

        new_color_state = {"value": theme.TREATMENT_COLOR_PALETTE[
            hash(treatment_key) % len(theme.TREATMENT_COLOR_PALETTE)]}
        new_swatch = ctk.CTkButton(row, text="", width=30, height=34, corner_radius=6,
                                    fg_color=new_color_state["value"], hover_color=new_color_state["value"],
                                    border_width=1, border_color=theme.BORDER)
        new_swatch.pack(side="right", padx=(4, 4))

        def choose_new_color():
            def apply(picked_color):
                new_color_state["value"] = picked_color
                new_swatch.configure(fg_color=picked_color, hover_color=picked_color)
            self._pick_color(new_color_state["value"], apply)

        new_swatch.configure(command=choose_new_color)

        name_entry = RTLEntry(row, width=140, height=34, placeholder_text="اسم النوع (مثلاً: زيركونيا)")
        name_entry.pack(side="right", padx=4)
        price_entry = ctk.CTkEntry(row, width=80, height=34, justify="center",
                                    placeholder_text="السعر", font=theme.FONT_SMALL)
        price_entry.pack(side="right", padx=4)
        commission_entry = ctk.CTkEntry(row, width=70, height=34, justify="center",
                                         placeholder_text="عمولة %", font=theme.FONT_SMALL)
        commission_entry.pack(side="right", padx=4)

        def add():
            name = name_entry.get().strip()
            if not name:
                return
            try:
                price = float(price_entry.get().strip() or 0)
                commission = float(commission_entry.get().strip() or 0)
            except ValueError:
                return
            db.add_treatment_variant(self.price_list_id, treatment_key, name, price, commission,
                                      new_color_state["value"])
            self._render()
            if self.on_change:
                self.on_change()

        ctk.CTkButton(row, text="+ إضافة نوع", width=100, height=34, fg_color=theme.PRIMARY_LIGHT,
                      command=add).pack(side="left", padx=4)

    def _delete_variant(self, variant_id):
        db.delete_treatment_variant(variant_id)
        self._render()
        if self.on_change:
            self.on_change()
