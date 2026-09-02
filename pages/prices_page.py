# -*- coding: utf-8 -*-
"""
صفحة إدارة قوائم أسعار المعالجات:
- تقدر تعمل أكتر من قائمة أسعار (عادي/VIP/تأمين...) وتختار القائمة الفعالة
- كل بند علاجي أساسي (زي "حشو") بس اسمه ورمزه في الشاشة الرئيسية - مفيش
  لون خاص بيه هنا خالص؛ الألوان بقت مقتصرة على الأنواع الفرعية بتاعته بس
  (زي "حشو زيركونيا" بلون معين، "حشو بورسلين" بلون تاني...) وبتتحدد من
  نافذة "إدارة الإجراءات الطبية"
- التعديلات كلها (اسم/رمز) بتتجمع وتتحفظ مرة واحدة بزرار حفظ واحد للصفحة
- جدول حقيقي بأعمدة ثابتة: مسلسل - اسم المعالجة - الرمز - عدد الأنواع
  الفرعية، وبمجرد ما تعمل هوفر على أي صف بتظهر قايمة سريعة بأنواعه الفرعية
"""

import customtkinter as ctk
import tkinter as tk
import theme
import database as db
from pages.rtl_entry import RTLEntry
from pages.treatment_variants_dialog import TreatmentVariantsDialog
from pages import tooth_symbols


# ملحوظة: كانت الصفحة قبل كده بتستخدم دالة اسمها _rtl() بتقلب ترتيب
# كلمات أي نص عربي فيه أكتر من كلمة قبل عرضه، على افتراض إن بعض عناصر
# الواجهة بتعكس ترتيب الكلمات في بيئات تشغيل معيّنة. اتضح إن ده مش صحيح
# فعليًا هنا - العكس هو اللي كان بيسبب ظهور الجمل مقلوبة على الشاشة (زي
# "الفرعية الأنواع عدد" بدل "عدد الأنواع الفرعية")، فشلنا الدالة دي خالص
# وبقينا نستخدم كل النصوص العربية زي ما هي من غير أي قلب في الترتيب

# لون رسم موحّد لمعاينة الرموز في هذه الصفحة بس (الألوان الفعلية بقت
# مقتصرة على الأنواع الفرعية - هنا الرمز بيتعرض بلون محايد ثابت عشان
# يوضح الشكل بس من غير ما يوهم إنه "لون البند")
SYMBOL_DISPLAY_COLOR = "#455A64"

# عرض ثابت لكل عمود (بالبكسل) - الجدول كله بعرضه الطبيعي (مجموع
# الأعمدة) بيتوسّط في نص الصفحة، مش بيتمدد على عرضها كله
COL_SERIAL_W = 64
COL_NAME_W = 280
COL_SYMBOL_W = 74
COL_COUNT_W = 210
TABLE_TOTAL_W = COL_SERIAL_W + COL_NAME_W + COL_SYMBOL_W + COL_COUNT_W

# فونط موحّد للصفحة كلها - نفس حجم ونوع فونط خانة "عدد الأنواع الفرعية"
# بالظبط (بدل ما كان فيه أحجام مختلفة متفرقة في كل عنصر)
COUNT_FONT_SIZE = 17
PAGE_FONT = (theme.CONTENT_FONT_FAMILY, COUNT_FONT_SIZE, "bold")

ROW_HEIGHT = 44
HEADER_HEIGHT = 42
# لون خطوط الشبكة بين كل الخلايا (نفس لون خط شبكة باقي جداول البرنامج)
GRID_LINE = "#C7CCD6"
# هيدر الجدول بقى بنفس لون تدرّج هيدر البرنامج نفسه (مش لون تاني منفصل)
# عشان يماشي لون الثيم المفعّل فعليًا أيًا كان
HEADER_BG = theme.HEADER_GRAD_END
HEADER_TEXT_COLOR = "#FFFFFF"
BLACK_BORDER = "#000000"

# ---------------- شكل موحّد لكل أزرار الصفحة ----------------
# نفس اللون والحجم والشكل لكل زرار في الصفحة (بدل ما كان كل زرار بلون
# وحجم مختلف)، عشان الصفحة تبان متسقة ومريحة بصريًا. بنستخدم نفس لوني
# تدرّج هيدر البرنامج (HEADER_GRAD_END/START) بدل PRIMARY_LIGHT عشان لون
# الأزرار يماشي لون الثيم المفعّل فعليًا (نفس الاتفاقية المستخدمة في باقي
# صفحات البرنامج لأزرار الإجراء الأساسية)، مع إطار أسود حوالين كل زرار
BTN_HEIGHT = 40
BTN_RADIUS = 0  # زوايا حادة 90 درجة بدل المدورة
BTN_COLOR = theme.HEADER_GRAD_END
BTN_HOVER = theme.HEADER_GRAD_START
BTN_TEXT_COLOR = "#FFFFFF"
BTN_BORDER_WIDTH = 1
# لون مميز بس لزرار الحذف (نفس الحجم والشكل والفونط والإطار الأسود زي
# باقي الأزرار بالظبط، فرق اللون بس عشان يبقى واضح إنه إجراء حذف)
BTN_DANGER_COLOR = theme.DANGER
BTN_DANGER_HOVER = theme.darken_color(theme.DANGER, 0.85)


def _make_button(parent, text, command, danger=False, width=None):
    """زرار بشكل وحجم ولون موحّد لكل أزرار الصفحة (فرق اللون الوحيد
    المسموح بيه هو لزرار الحذف بس، وبرضو بنفس الحجم والشكل والفونط
    والإطار الأسود)"""
    kwargs = dict(text=text, height=BTN_HEIGHT, corner_radius=BTN_RADIUS,
                  font=PAGE_FONT, command=command,
                  fg_color=BTN_DANGER_COLOR if danger else BTN_COLOR,
                  hover_color=BTN_DANGER_HOVER if danger else BTN_HOVER,
                  text_color=BTN_TEXT_COLOR,
                  border_width=BTN_BORDER_WIDTH, border_color=BLACK_BORDER)
    if width is not None:
        kwargs["width"] = width
    return ctk.CTkButton(parent, **kwargs)

# ترتيب أعمدة الـ grid من الشمال لليمين (رقم العمود بيزيد كل ما اتجهنا
# شمال->يمين، فعشان "مسلسل" يبقى أقصى اليمين زي ترتيب القراءة المطلوب
# (مسلسل - اسم الإجراء - الرمز - عدد الأنواع الفرعية) بنديله أعلى رقم عمود
GRID_COL_COUNT = 0
GRID_COL_SYMBOL = 1
GRID_COL_NAME = 2
GRID_COL_SERIAL = 3


class PricesPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.selected_list_id = None
        self.row_widgets = []  # [{"key":.., "label_entry":.., "symbol_state":..}, ...]
        self._variants_tooltip = None
        self._tooltip_key = None
        self._hide_job = None
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(header, text="الإجراءات الطبية", font=PAGE_FONT,
                     text_color=theme.TEXT_DARK).pack(side="right")

        # كل أزرار الهيدر بنفس الشكل والحجم واللون والفونط (فرق اللون
        # الوحيد هو لزرار الحذف في الصف اللي تحت)، ومرتبين بمسافات
        # متساوية واضحة بينهم
        _make_button(header, "+ قائمة أسعار جديدة", self._open_new_list_dialog).pack(
            side="left", padx=(6, 0))
        # الطريقة الوحيدة دلوقتي لتعديل أو حذف الإجراءات الطبية نفسها
        # بالإضافة لإدارة أنواعها الفرعية وألوانها وأسعارها
        _make_button(header, "⚙ إدارة الإجراءات الطبية", self._open_variants_manager).pack(
            side="left", padx=6)
        # زرار الحفظ الوحيد للصفحة كلها - أي تعديل (اسم/رمز) في أي عدد
        # من البنود بيتجمع، ولما تدوس هنا بيتحفظ كل حاجة مرة واحدة
        self.save_all_btn = _make_button(header, "💾 حفظ كل التغييرات", self._save_all)
        self.save_all_btn.pack(side="left", padx=6)

        lists_row = ctk.CTkFrame(self, fg_color="transparent")
        lists_row.pack(fill="x", pady=(0, 10))
        # مسافة 5 بيكسل واضحة بين كلمة "اختر القائمة:" والمنسدلة جنبها
        ctk.CTkLabel(lists_row, text="اختر القائمة:", font=PAGE_FONT).pack(
            side="right", padx=(5, 0))

        self.lists = db.get_price_lists()
        active_id = db.get_settings()["active_price_list_id"]
        self.selected_list_id = self.selected_list_id or active_id or (self.lists[0]["id"] if self.lists else None)

        self.list_names = {l["name"]: l["id"] for l in self.lists}
        current_name = next((l["name"] for l in self.lists if l["id"] == self.selected_list_id), "")

        self.list_menu = ctk.CTkOptionMenu(lists_row, values=list(self.list_names.keys()),
                                            width=220, font=PAGE_FONT,
                                            command=self._on_list_change,
                                            **theme.optionmenu_colors())
        if current_name:
            self.list_menu.set(current_name)
        self.list_menu.pack(side="right")

        self.active_badge = ctk.CTkLabel(lists_row, text="", font=PAGE_FONT,
                                          text_color=theme.SUCCESS)
        self.active_badge.pack(side="right", padx=12)

        _make_button(lists_row, "تعيين كقائمة نشطة", self._set_active).pack(side="left", padx=6)
        _make_button(lists_row, "حذف القائمة", self._delete_list, danger=True).pack(side="left", padx=6)

        self.table_container = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.table_container.pack(fill="both", expand=True)

        self._render_table()

    def _open_variants_manager(self, focus_key=None):
        if not self.selected_list_id:
            return
        TreatmentVariantsDialog(self, self.selected_list_id, on_change=self._render_table,
                                 focus_treatment_key=focus_key)

    def _on_list_change(self, name):
        self.selected_list_id = self.list_names.get(name)
        self._render_table()
        self._update_active_badge()

    def _update_active_badge(self):
        active_id = db.get_settings()["active_price_list_id"]
        if self.selected_list_id == active_id:
            self.active_badge.configure(text="✔ هي القائمة النشطة حالياً")
        else:
            self.active_badge.configure(text="")

    def _set_active(self):
        if self.selected_list_id:
            db.set_active_price_list(self.selected_list_id)
            self._update_active_badge()

    def _delete_list(self):
        if not self.selected_list_id or len(self.lists) <= 1:
            return
        db.delete_price_list(self.selected_list_id)
        self.lists = db.get_price_lists()
        self.selected_list_id = self.lists[0]["id"] if self.lists else None
        self._build_refresh()

    def _build_refresh(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()

    # ---------------- حفظ كل التغييرات مرة واحدة ----------------

    def _save_all(self):
        if not self.selected_list_id:
            return
        for entry in self.row_widgets:
            new_label = entry["label_entry"].get().strip() or entry["original_label"]
            db.update_treatment_price(
                self.selected_list_id, entry["key"], new_label,
                entry["price"], entry["commission"],
                color=None,  # الألوان بقت مقتصرة على الأنواع الفرعية - محدش بيتحكم في لون البند من هنا
                symbol_key=None if entry["is_builtin"] else entry["symbol_state"]["value"],
            )
        original_text = self.save_all_btn.cget("text")
        self.save_all_btn.configure(text="✔ تم حفظ الكل")
        self.after(1200, lambda: self.save_all_btn.configure(text=original_text))
        self._render_table()

    # ---------------- رسم الجدول ----------------

    def _render_table(self):
        for w in self.table_container.winfo_children():
            w.destroy()
        self.row_widgets = []
        self._hide_variants_tooltip(force=True)

        self._update_active_badge()

        # إطار الجدول الحقيقي - إطار خارجي أسود واضح حوالين الجدول كله،
        # وكل خلية جواه ليها حدود رفيعة كاملة (يمين/شمال/فوق/تحت) بنفس
        # لون خط الشبكة، فبتتلاقى حدود الخلايا المتجاورة مع بعض وتكوّن
        # شبكة متصلة زي جدول إكسيل بالظبط. الإطار ده بعرضه الطبيعي بس
        # (مجموع عرض الأعمدة الأربعة) وبيتوسّط تلقائيًا في نص المساحة
        # المتاحة (من غير fill="x") فيفضل الجدول مش عريض وله هوامش يمين
        # وشمال واضحة
        self.grid_table = ctk.CTkFrame(self.table_container, fg_color=theme.CARD_BG,
                                        corner_radius=0, border_width=2,
                                        border_color=BLACK_BORDER)
        self.grid_table.pack(pady=(12, 4))
        for col, w in ((GRID_COL_COUNT, COL_COUNT_W), (GRID_COL_SYMBOL, COL_SYMBOL_W),
                       (GRID_COL_NAME, COL_NAME_W), (GRID_COL_SERIAL, COL_SERIAL_W)):
            self.grid_table.grid_columnconfigure(col, minsize=w, weight=0)
        self.grid_table.grid_rowconfigure(0, minsize=HEADER_HEIGHT, weight=0)

        # --- رأس الجدول (مظلل بلون مختلف) - بالترتيب: مسلسل (بدون كلمة
        # "مسلسل" نفسها - العمود فاضل موجود والأرقام فعليًا ظاهرة تحته)
        # - اسم الإجراء - الرمز - عدد الأنواع الفرعية ---
        ctk.CTkLabel(self.grid_table, text="", font=PAGE_FONT,
                     text_color=HEADER_TEXT_COLOR, fg_color=HEADER_BG, corner_radius=0,
                     border_width=1, border_color=GRID_LINE, anchor="center").grid(
            row=0, column=GRID_COL_SERIAL, sticky="nsew")
        ctk.CTkLabel(self.grid_table, text="اسم الإجراء", font=PAGE_FONT,
                     text_color=HEADER_TEXT_COLOR, fg_color=HEADER_BG, corner_radius=0,
                     border_width=1, border_color=GRID_LINE, anchor="center").grid(
            row=0, column=GRID_COL_NAME, sticky="nsew")
        ctk.CTkLabel(self.grid_table, text="الرمز", font=PAGE_FONT,
                     text_color=HEADER_TEXT_COLOR, fg_color=HEADER_BG, corner_radius=0,
                     border_width=1, border_color=GRID_LINE, anchor="center").grid(
            row=0, column=GRID_COL_SYMBOL, sticky="nsew")
        ctk.CTkLabel(self.grid_table, text="عدد الأنواع الفرعية", font=PAGE_FONT,
                     text_color=HEADER_TEXT_COLOR, fg_color=HEADER_BG, corner_radius=0,
                     border_width=1, border_color=GRID_LINE, anchor="center").grid(
            row=0, column=GRID_COL_COUNT, sticky="nsew")

        if not self.selected_list_id:
            return

        prices = db.get_treatment_prices(self.selected_list_id)
        for i, (key, info) in enumerate(prices.items(), start=1):
            self._render_row(i, key, info, zebra=(i % 2 == 0))

        self._render_add_button()

    def _pick_symbol(self, current_symbol, current_color, on_pick):
        popup = ctk.CTkToplevel(self)
        popup.title("اختر رمز الشارت")
        popup.geometry("360x460")
        popup.grab_set()

        ctk.CTkLabel(popup, text="اختر الرمز الذي يدل على هذا البند في خريطة الأسنان",
                     font=theme.FONT_NORMAL, wraplength=320, justify="right").pack(pady=(14, 8))

        scroll = ctk.CTkScrollableFrame(popup, fg_color="transparent", width=320, height=340)
        scroll.pack(padx=14, fill="both", expand=True)

        for i, (key, label, _fn) in enumerate(tooth_symbols.SYMBOL_CHOICES):
            is_selected = key == current_symbol
            cell = ctk.CTkFrame(scroll, fg_color=theme.CARD_BG if not is_selected else theme.BG_MAIN,
                                 corner_radius=8, border_width=2 if is_selected else 1,
                                 border_color=theme.SUCCESS if is_selected else theme.BORDER)
            cell.grid(row=(i // 4) * 2, column=i % 4, padx=6, pady=(6, 0))

            preview = tk.Canvas(cell, width=56, height=56,
                                 bg=theme.CARD_BG if not is_selected else theme.BG_MAIN,
                                 highlightthickness=0)
            preview.pack(padx=2, pady=2)
            tooth_symbols.draw_symbol(preview, key, 28, 28, 16, current_color or SYMBOL_DISPLAY_COLOR)

            def on_click(e, k=key):
                popup.destroy()
                on_pick(k)
            preview.bind("<Button-1>", on_click)
            cell.bind("<Button-1>", on_click)

            ctk.CTkLabel(scroll, text=label, font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                         wraplength=80).grid(row=(i // 4) * 2 + 1, column=i % 4, padx=6, pady=(0, 8))

    # ---------------- هوفر: قايمة سريعة بالأنواع الفرعية ----------------

    def _bind_hover_recursive(self, widget, treatment_key, variants):
        # e=None بقيمة افتراضية عشان لو حصل استدعاء متأخر للـ callback من
        # ويدجت اتشال وقت إعادة رسم الجدول (بعد ضغطة سريعة) ما يحصلش خطأ
        widget.bind("<Enter>", lambda e=None, k=treatment_key, v=variants: self._show_variants_tooltip(e, k, v), add="+")
        widget.bind("<Leave>", lambda e=None: self._schedule_hide_tooltip(), add="+")
        for child in widget.winfo_children():
            self._bind_hover_recursive(child, treatment_key, variants)

    def _schedule_hide_tooltip(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if self._hide_job:
            self.after_cancel(self._hide_job)
        self._hide_job = self.after(150, self._hide_variants_tooltip)

    def _show_variants_tooltip(self, event, treatment_key, variants):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if self._hide_job:
            self.after_cancel(self._hide_job)
            self._hide_job = None
        if self._tooltip_key == treatment_key and self._variants_tooltip is not None:
            return
        self._hide_variants_tooltip(force=True)

        if event is not None:
            px, py = event.x_root, event.y_root
        else:
            px, py = self.winfo_pointerx(), self.winfo_pointery()

        tooltip = tk.Toplevel(self)
        tooltip.overrideredirect(True)
        tooltip.attributes("-topmost", True)
        tooltip.configure(bg=theme.TEXT_DARK)

        card = ctk.CTkFrame(tooltip, fg_color=theme.CARD_BG, corner_radius=8,
                             border_width=1, border_color=theme.BORDER)
        card.pack(padx=1, pady=1)
        ctk.CTkLabel(card, text="الأنواع الفرعية", font=(theme.CONTENT_FONT_FAMILY, 13, "bold"),
                     text_color=theme.TEXT_DARK).pack(anchor="e", padx=10, pady=(8, 2))

        if not variants:
            ctk.CTkLabel(card, text="لا توجد أنواع فرعية مضافة بعد", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(anchor="e", padx=10, pady=(0, 8))
        else:
            for v in variants:
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(anchor="e", padx=10, pady=2, fill="x")
                ctk.CTkLabel(row, text="  ", fg_color=v.get("color") or "#1E88E5",
                             width=10, height=10, corner_radius=5).pack(side="right", padx=(4, 0))
                text = f"{v['variant_name']}  —  {v['price']:g} ج"
                ctk.CTkLabel(row, text=text, font=(theme.CONTENT_FONT_FAMILY, 12),
                             text_color=theme.TEXT_DARK).pack(side="right")
            ctk.CTkFrame(card, fg_color="transparent", height=4).pack()

        tooltip.update_idletasks()
        x = px + 14
        y = py + 10
        screen_w = tooltip.winfo_screenwidth()
        screen_h = tooltip.winfo_screenheight()
        tip_w = tooltip.winfo_width()
        tip_h = tooltip.winfo_height()
        if x + tip_w > screen_w:
            x = px - tip_w - 14
        if y + tip_h > screen_h:
            y = py - tip_h - 10
        tooltip.geometry(f"+{x}+{y}")

        self._variants_tooltip = tooltip
        self._tooltip_key = treatment_key

    def _hide_variants_tooltip(self, force=False):
        self._hide_job = None
        if self._variants_tooltip is not None:
            try:
                self._variants_tooltip.destroy()
            except Exception:
                pass
            self._variants_tooltip = None
            self._tooltip_key = None

    # ---------------- صف واحد في الجدول ----------------

    def _render_row(self, serial, treatment_key, info, zebra=False):
        self.grid_table.grid_rowconfigure(serial, minsize=ROW_HEIGHT, weight=0)
        row_bg = theme.CARD_BG if not zebra else theme.lighten_color(theme.PRIMARY_LIGHT, 0.85)

        variants = db.get_treatment_variants(self.selected_list_id, treatment_key)
        is_builtin = treatment_key in tooth_symbols.BUILTIN_TREATMENT_KEYS
        hover_targets = []

        # --- مسلسل (رقم الترتيب فعليًا موجود، بس من غير كلمة "مسلسل"
        # في الهيدر) ---
        serial_cell = ctk.CTkLabel(self.grid_table, text=str(serial), font=PAGE_FONT,
                                    text_color=theme.TEXT_DARK, fg_color=row_bg, corner_radius=0,
                                    border_width=1, border_color=GRID_LINE, anchor="center")
        serial_cell.grid(row=serial, column=GRID_COL_SERIAL, sticky="nsew")
        hover_targets.append(serial_cell)

        # --- اسم الإجراء - خلية ذات حدود جوّها حقل تعديل مباشر ---
        name_cell = ctk.CTkFrame(self.grid_table, fg_color=row_bg, corner_radius=0,
                                  border_width=1, border_color=GRID_LINE)
        name_cell.grid(row=serial, column=GRID_COL_NAME, sticky="nsew")
        name_entry = RTLEntry(name_cell, width=COL_NAME_W - 16, height=ROW_HEIGHT - 14,
                               font=PAGE_FONT)
        name_entry.insert(0, info["label"])
        name_entry.pack(padx=6, pady=5)
        hover_targets.append(name_cell)

        # --- الرمز - ظاهر لكل البنود، لكن قابل للتغيير بس للبنود اللي
        # مش من البنود الأساسية الجاهزة (اللي ليها رسمة خاصة بيها في شارت
        # الأسنان زي خط الجذر وعلامة الخلع) ---
        if is_builtin:
            initial_symbol = tooth_symbols.BUILTIN_DISPLAY_SYMBOLS.get(
                treatment_key, tooth_symbols.DEFAULT_SYMBOL_KEY)
        else:
            initial_symbol = info.get("symbol_key") or tooth_symbols.DEFAULT_SYMBOL_KEY
        symbol_state = {"value": initial_symbol}

        symbol_cell = ctk.CTkFrame(self.grid_table, fg_color=row_bg, corner_radius=0,
                                    border_width=1, border_color=GRID_LINE)
        symbol_cell.grid(row=serial, column=GRID_COL_SYMBOL, sticky="nsew")
        symbol_preview = tk.Canvas(symbol_cell, width=COL_SYMBOL_W - 20, height=ROW_HEIGHT - 16,
                                    bg=row_bg, highlightthickness=0)
        symbol_preview.pack(expand=True)
        hover_targets.append(symbol_cell)

        def redraw_symbol_preview():
            symbol_preview.delete("all")
            w = int(symbol_preview["width"])
            h = int(symbol_preview["height"])
            tooth_symbols.draw_symbol(symbol_preview, symbol_state["value"], w // 2, h // 2, 10,
                                       SYMBOL_DISPLAY_COLOR)
        redraw_symbol_preview()

        if not is_builtin:
            def choose_symbol():
                def apply_symbol(picked_key):
                    symbol_state["value"] = picked_key
                    redraw_symbol_preview()
                self._pick_symbol(symbol_state["value"], SYMBOL_DISPLAY_COLOR, apply_symbol)
            symbol_preview.configure(cursor="hand2")
            symbol_preview.bind("<Button-1>", lambda e: choose_symbol())

        # --- عدد الأنواع الفرعية - خط أكبر بـ3 بيكسل من باقي الجدول،
        # وزرار بيفتح إدارة الأنواع الفرعية لهذا البند تحديدًا ---
        count_cell = ctk.CTkFrame(self.grid_table, fg_color=row_bg, corner_radius=0,
                                   border_width=1, border_color=GRID_LINE)
        count_cell.grid(row=serial, column=GRID_COL_COUNT, sticky="nsew")
        count_btn = ctk.CTkButton(count_cell, text=f"({len(variants)}) الأنواع الفرعية",
                                   width=COL_COUNT_W - 16, height=ROW_HEIGHT - 14,
                                   corner_radius=0,
                                   fg_color="transparent", text_color=theme.ACCENT_BORDER,
                                   hover_color=theme.lighten_color(theme.PRIMARY_LIGHT, 0.7),
                                   font=PAGE_FONT,
                                   command=lambda k=treatment_key: self._open_variants_manager(focus_key=k))
        count_btn.pack(padx=4, pady=4)
        hover_targets.append(count_cell)

        # هوفر على أي خلية في الصف بيظهر قايمة سريعة بالأنواع الفرعية بتاعته
        for target in hover_targets:
            self._bind_hover_recursive(target, treatment_key, variants)

        self.row_widgets.append({
            "key": treatment_key,
            "label_entry": name_entry,
            "symbol_state": symbol_state,
            "is_builtin": is_builtin,
            "original_label": info["label"],
            "price": info["price"],
            "commission": info["commission_percent"],
        })

    # ---------------- إضافة إجراء جديد (نافذة منبثقة) ----------------

    def _render_add_button(self):
        row = ctk.CTkFrame(self.table_container, fg_color="transparent", width=TABLE_TOTAL_W)
        row.pack(pady=(4, 16))
        _make_button(row, "+ إضافة", self._open_add_treatment_dialog).pack(side="right", padx=4)
        ctk.CTkLabel(row, text="إضافة إجراء علاجي جديد", font=PAGE_FONT,
                     text_color=theme.TEXT_MUTED).pack(side="right", padx=(0, 8))

    def _open_add_treatment_dialog(self):
        if not self.selected_list_id:
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("إضافة إجراء جديد")
        dialog.geometry("380x380")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="اسم الإجراء الجديد", font=theme.FONT_NORMAL).pack(
            anchor="e", padx=30, pady=(20, 4))
        name_entry = RTLEntry(dialog, width=300, height=40)
        name_entry.pack(padx=30, pady=(0, 14), anchor="e")

        ctk.CTkLabel(dialog, text="اختر رمزه في شارت الأسنان", font=theme.FONT_NORMAL).pack(
            anchor="e", padx=30, pady=(0, 6))

        symbol_state = {"value": tooth_symbols.DEFAULT_SYMBOL_KEY}
        symbol_preview = tk.Canvas(dialog, width=48, height=48, bg=theme.BG_MAIN,
                                    highlightthickness=1, highlightbackground=theme.BORDER,
                                    cursor="hand2")
        symbol_preview.pack(pady=(0, 4))

        def redraw():
            symbol_preview.delete("all")
            tooth_symbols.draw_symbol(symbol_preview, symbol_state["value"], 24, 24, 16, SYMBOL_DISPLAY_COLOR)
        redraw()

        def choose_symbol():
            def apply_symbol(picked_key):
                symbol_state["value"] = picked_key
                redraw()
            self._pick_symbol(symbol_state["value"], SYMBOL_DISPLAY_COLOR, apply_symbol)
        symbol_preview.bind("<Button-1>", lambda e: choose_symbol())

        ctk.CTkLabel(dialog, text="(اضغط على الرمز لاختيار غيره)", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(pady=(0, 16))

        def save():
            label = name_entry.get().strip()
            if not label:
                return
            treatment_key = "custom_" + str(abs(hash(label)) % 100000)
            db.update_treatment_price(self.selected_list_id, treatment_key, label, 0, 0,
                                       color=None, symbol_key=symbol_state["value"])
            dialog.destroy()
            self._render_table()

        ctk.CTkButton(dialog, text="+ إضافة", height=42, fg_color=theme.SUCCESS,
                      command=save).pack(padx=30, pady=10, fill="x")

    def _open_new_list_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("قائمة أسعار جديدة")
        dialog.geometry("340x300")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="اسم القائمة الجديدة", font=theme.FONT_NORMAL).pack(
            anchor="e", padx=30, pady=(20, 4))
        name_entry = RTLEntry(dialog, width=260, height=40)
        name_entry.pack(padx=30, pady=(0, 14), anchor="e")

        copy_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(dialog, text="انسخ الأسعار من القائمة الحالية", variable=copy_var,
                         font=theme.FONT_NORMAL, **theme.checkbox_colors()).pack(anchor="e", padx=30, pady=(0, 20))

        def save():
            name = name_entry.get().strip()
            if not name:
                return
            copy_from = self.selected_list_id if copy_var.get() else None
            new_id = db.add_price_list(name, copy_from_list_id=copy_from)
            self.selected_list_id = new_id
            dialog.destroy()
            self._build_refresh()

        ctk.CTkButton(dialog, text="إنشاء القائمة", height=42, fg_color=theme.SUCCESS,
                      command=save).pack(padx=30, pady=10, fill="x")
