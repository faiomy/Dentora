# -*- coding: utf-8 -*-
"""
صفحة الإعدادات: اسم العيادة، اللوجو، الألوان، الخطوط، اللغة، والمستخدمين والصلاحيات (للمدير فقط)

شكل الصفحة: كل حقل وعنوانه في نفس السطر (بدل عنوان فوق وحقل تحت) عشان توفير
المساحة وشكل أرتب، مع تباين واضح بين لون خلفية الصفحة وخلفية الكروت الثابتة
وخلفية صناديق الإدخال المتغيرة.
"""

import os
import shutil
import customtkinter as ctk
from tkinter import filedialog
import theme
import database as db
from pages.rtl_entry import RTLEntry
from pages.notebook_tabs import NotebookTabview
from pages import icons

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

LANGUAGE_OPTIONS = {"العربية": "ar", "English": "en"}
LANGUAGE_OPTIONS_REVERSE = {v: k for k, v in LANGUAGE_OPTIONS.items()}

LABEL_COL_WIDTH = 190  # عرض ثابت لعمود العناوين عشان كل الحقول تتظبط تحت بعض

# نفس فونت وحجم هيدر الأيام في صفحة المواعيد (اللي بيعرض اليوم والتاريخ) -
# بيتطبق على كل عناوين الحقول ونصوص الأزرار في صفحة الإعدادات عشان يبقى
# فيه توحيد للخط في الصفحتين
HEADER_LABEL_FONT = (theme.FONT_FAMILY, 13, "bold")


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, current_user=None, on_settings_changed=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_user = current_user
        self.on_settings_changed = on_settings_changed
        self.settings = db.get_effective_settings(current_user["id"] if current_user else None)
        self._build()

    # ---------------- أدوات بناء عامة (Helpers) ----------------

    def _make_card(self, parent, title=None, subtitle=None):
        """كارت بخلفية بيضاء وإطار واضح، متباين عن خلفية الصفحة الرمادية الفاتحة"""
        ctk.CTkFrame(parent, fg_color="transparent", height=16).pack()
        card = ctk.CTkFrame(parent, fg_color=theme.CARD_BG, corner_radius=12,
                             border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=4)
        if title:
            ctk.CTkLabel(card, text=title, font=theme.FONT_SUBTITLE,
                         text_color=theme.TEXT_DARK).pack(anchor="e", padx=22, pady=(18, 2 if subtitle else 14))
        if subtitle:
            ctk.CTkLabel(card, text=subtitle, font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                         wraplength=560, justify="right").pack(anchor="e", padx=22, pady=(0, 14))
        return card

    def _field_row(self, parent, label_text, label_width=LABEL_COL_WIDTH, pady=4):
        """
        صف واحد: عنوان الحقل على اليمين بعرض ثابت (يضمن محاذاة كل الحقول تحت
        بعض)، والحقول نفسها بتتحط بعده جوه نفس الصف (مش تحته). بترجع الصف
        عشان اللي بيستدعيها يضيف فيه عنصر الإدخال بعد كده.
        """
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=pady)
        ctk.CTkLabel(row, text=label_text, font=HEADER_LABEL_FONT,
                     text_color=theme.INPUT_LABEL_COLOR, anchor="e",
                     width=label_width).pack(side="right", padx=(12, 0))
        return row

    def _styled_entry(self, row, initial_value="", height=32, placeholder=""):
        entry = RTLEntry(row, height=height, placeholder_text=placeholder, font=HEADER_LABEL_FONT)
        theme.apply_sunken_style(entry)
        if initial_value:
            entry.insert(0, initial_value)
        entry.pack(side="right", fill="x", expand=True)
        return entry

    def _styled_option_menu(self, row, values, current_value, width=160, command=None):
        menu = ctk.CTkOptionMenu(row, values=values, width=width, command=command,
                                  font=HEADER_LABEL_FONT,
                                  fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                                  button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9))
        menu.set(current_value)
        menu.pack(side="right")
        return menu

    # ---------------- بناء الصفحة ----------------

    def _build(self):
        ctk.CTkLabel(self, text="إعدادات العيادة", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", pady=(0, 8))

        self._new_logo_path = None
        is_manager = bool(self.current_user and self.current_user["role"] == "manager")

        self.tabview = NotebookTabview(self, font=HEADER_LABEL_FONT,
                                       active_fg_color=theme.TAB_ACTIVE_BG,
                                       inactive_fg_color=theme.TAB_INACTIVE_BG,
                                       border_color=theme.ACCENT_BORDER,
                                       content_fg_color=theme.CARD_BG,
                                       corner_radius=theme.TAB_RADIUS)
        self.tabview.pack(fill="both", expand=True)

        tab_clinic = self.tabview.add("بيانات العيادة")
        tab_appearance = self.tabview.add("المظهر والخطوط")
        if is_manager:
            tab_security = self.tabview.add("الأمان")
            tab_schedule = self.tabview.add("المواعيد والإجازات")
            tab_users = self.tabview.add("المستخدمون والصلاحيات")

        scroll_clinic = ctk.CTkScrollableFrame(tab_clinic, fg_color="transparent")
        scroll_clinic.pack(fill="both", expand=True)
        self._build_clinic_info_tab(scroll_clinic)

        scroll_appearance = ctk.CTkScrollableFrame(tab_appearance, fg_color="transparent")
        scroll_appearance.pack(fill="both", expand=True)
        self._build_appearance_tab(scroll_appearance)

        if is_manager:
            scroll_security = ctk.CTkScrollableFrame(tab_security, fg_color="transparent")
            scroll_security.pack(fill="both", expand=True)
            self._build_login_security_section(scroll_security)

            scroll_schedule = ctk.CTkScrollableFrame(tab_schedule, fg_color="transparent")
            scroll_schedule.pack(fill="both", expand=True)
            self._build_schedule_hours_section(scroll_schedule)
            self._build_holidays_section(scroll_schedule)

            scroll_users = ctk.CTkScrollableFrame(tab_users, fg_color="transparent")
            scroll_users.pack(fill="both", expand=True)
            self._build_users_section(scroll_users)

    def _build_clinic_info_tab(self, scroll):
        card = self._make_card(scroll)

        # اسم العيادة
        row = self._field_row(card, "اسم العيادة")
        self.name_entry = self._styled_entry(row, self.settings["clinic_name"])

        # اللوجو
        row = self._field_row(card, "لوجو العيادة")
        ctk.CTkButton(row, text="اختيار صورة اللوجو", width=160, height=32, font=HEADER_LABEL_FONT,
                      fg_color=theme.PRIMARY_LIGHT,
                      command=self._choose_logo).pack(side="right")
        self.logo_path_label = ctk.CTkLabel(
            row, text=os.path.basename(self.settings["logo_path"]) if self.settings["logo_path"]
            else "لا يوجد لوجو مرفوع", font=HEADER_LABEL_FONT, text_color=theme.TEXT_MUTED)
        self.logo_path_label.pack(side="right", padx=10)

        # عنوان العيادة
        row = self._field_row(card, "عنوان العيادة")
        self.address_entry = self._styled_entry(row, self.settings.get("clinic_address") or "")

        # أرقام تليفونات العيادة
        row = self._field_row(card, "أرقام تليفونات العيادة", pady=(4, 4))
        add_phone_btn = ctk.CTkButton(row, text="+ رقم جديد", width=100, height=30, font=HEADER_LABEL_FONT,
                                       fg_color="transparent", border_width=1, border_color=theme.BORDER,
                                       text_color=theme.TEXT_DARK,
                                       command=lambda: self._add_phone_row())
        add_phone_btn.pack(side="left")
        self.phones_list_frame = ctk.CTkFrame(row, fg_color="transparent")
        self.phones_list_frame.pack(side="right", fill="x", expand=True)
        self.phone_entries = []  # [(phone_id_or_None, entry_widget, row_frame), ...]
        existing_phones = db.get_clinic_phones()
        for phone in existing_phones:
            self._add_phone_row(phone_id=phone["id"], phone_number=phone["phone_number"])
        if not existing_phones:
            self._add_phone_row()

        # البطاقة الضريبية
        row = self._field_row(card, "رقم البطاقة الضريبية")
        self.tax_card_entry = self._styled_entry(row, self.settings.get("tax_card_number") or "")

        save_wrapper = theme.make_shadowed_button(
            card, "حفظ الإعدادات", command=self._save, width=190, height=40, font=HEADER_LABEL_FONT)
        save_wrapper.pack(pady=(14, 18))

    def _build_appearance_tab(self, scroll):
        card = self._make_card(scroll, title="المظهر")
        ctk.CTkLabel(card, text="جميع هذه الاختيارات قوائم منسدلة تُطبَّق فورًا بمجرد الاختيار، وهي خاصة "
                                 "بالمستخدم الحالي فقط (لا تؤثر في شكل البرنامج لدى باقي المستخدمين "
                                 "الذين يستخدمون نفس الجهاز)",
                     font=HEADER_LABEL_FONT, text_color=theme.TEXT_MUTED,
                     wraplength=560, justify="right").pack(anchor="e", padx=22, pady=(16, 10))

        # ---- الثيم (منسدلة بالألوان بس، من غير أسماء ظاهرة) ----
        self._current_theme_id = self.settings.get("theme_id") or theme.DEFAULT_THEME_ID
        self._theme_popup = None
        row = self._field_row(card, "الثيم (الألوان)")
        self._build_theme_dropdown(row)

        # فاصل
        ctk.CTkFrame(card, fg_color=theme.BORDER, height=1).pack(fill="x", padx=22, pady=(10, 4))

        # ---- تصميم أزرار الشريط العلوي الرئيسي (منسدلة بالأسماء) ----
        self._current_nav_style = self.settings.get("nav_button_style") or "classic"
        row = self._field_row(card, "تصميم أزرار الشريط الرئيسي")
        self._build_nav_style_dropdown(row)

        # ---- نمط رسم أيقونات الشريط العلوي (منسدلة بالأسماء) ----
        self._current_icon_pattern = self.settings.get("icon_pattern") or "outline"
        row = self._field_row(card, "نمط رسم الأيقونات الرئيسية")
        self._build_icon_pattern_dropdown(row)

        # فاصل
        ctk.CTkFrame(card, fg_color=theme.BORDER, height=1).pack(fill="x", padx=22, pady=(10, 4))

        # اللغة
        row = self._field_row(card, "لغة البرنامج")
        ctk.CTkLabel(row, text="(الترجمة الإنجليزية ما تزال في مراحلها الأولى)",
                     font=HEADER_LABEL_FONT, text_color=theme.TEXT_MUTED).pack(side="left")
        self.language_menu = self._styled_option_menu(
            row, list(LANGUAGE_OPTIONS.keys()),
            LANGUAGE_OPTIONS_REVERSE.get(self.settings["language"], "العربية"), width=140,
            command=self._apply_appearance_settings)

        # فاصل
        ctk.CTkFrame(card, fg_color=theme.BORDER, height=1).pack(fill="x", padx=22, pady=(4, 4))

        # إظهار/إخفاء أسماء الأزرار تحت الأيقونات في الشريط العلوي
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(6, 4))
        self.show_ribbon_labels_var = ctk.BooleanVar(
            value=bool(self.settings.get("show_ribbon_labels", 1)))
        switch = ctk.CTkSwitch(row, text="إظهار أسماء الصفحات تحت أيقونات الشريط العلوي",
                                font=HEADER_LABEL_FONT, variable=self.show_ribbon_labels_var,
                                command=self._toggle_show_ribbon_labels, **theme.switch_colors())
        switch.pack(side="right")

        # فاصل
        ctk.CTkFrame(card, fg_color=theme.BORDER, height=1).pack(fill="x", padx=22, pady=(4, 4))
        ctk.CTkLabel(card, text="إعدادات الخط", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", padx=22, pady=(6, 2))

        # خط النظام - نوع الخط بس (مقاسه ثابت في الكود عشان الاتساق)
        row = self._field_row(card, "خط النظام (الشريط العلوي)")
        self.system_font_menu = self._styled_option_menu(
            row, theme.FONT_OPTIONS, self.settings["system_font_family"], width=180,
            command=self._apply_appearance_settings)
        self.system_font_menu.pack(side="right", padx=(0, 8))

        # خط المحتوى - نوع الخط بس (مقاسه ثابت في الكود عشان الاتساق)
        row = self._field_row(card, "خط المحتوى (البيانات)")
        self.content_font_menu = self._styled_option_menu(
            row, theme.FONT_OPTIONS, self.settings["content_font_family"], width=180,
            command=self._apply_appearance_settings)
        self.content_font_menu.pack(side="right", padx=(0, 8))

        # فاصل + زرار "رجّع مظهر العيادة الافتراضي" - بيمسح كل التخصيصات
        # الشخصية اللي المستخدم الحالي اختارها، ويرجّعه يشوف نفس المظهر
        # اللي باقي المستخدمين شايفينه (إعداد العيادة العام)
        if self.current_user:
            ctk.CTkFrame(card, fg_color=theme.BORDER, height=1).pack(fill="x", padx=22, pady=(10, 4))
            reset_row = ctk.CTkFrame(card, fg_color="transparent")
            reset_row.pack(fill="x", padx=22, pady=(2, 16))
            ctk.CTkButton(reset_row, text="↺ رجّع مظهر العيادة الافتراضي", height=32,
                          fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                          hover_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                          font=HEADER_LABEL_FONT,
                          command=self._reset_user_appearance).pack(side="right")

        ctk.CTkLabel(scroll, text="جميع التغييرات تُطبَّق فورًا من دون الحاجة لحفظ أي شيء يدويًا.",
                     font=HEADER_LABEL_FONT, text_color=theme.TEXT_MUTED,
                     wraplength=500, justify="right").pack(anchor="e", pady=(6, 0))

    # ---------------- أمان تسجيل الدخول (مدير بس) ----------------

    def _build_login_security_section(self, parent):
        card = self._make_card(
            parent, title="أمان تسجيل الدخول",
            subtitle="عند إيقاف كلمة المرور، يمكن لأي شخص يفتح البرنامج الدخول بمجرد اختيار اسمه من دون كلمة مرور، "
                     "وسيستمر بنفس صلاحيات نوع الحساب المختار. هذا مفيد أثناء تجربة البرنامج، "
                     "لكن يُفضَّل إعادة تفعيلها بعد ذلك.")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(0, 20))
        self.require_password_var = ctk.BooleanVar(value=bool(self.settings.get("require_password", 1)))
        switch = ctk.CTkSwitch(row, text="طلب كلمة مرور عند تسجيل الدخول", font=HEADER_LABEL_FONT,
                                variable=self.require_password_var,
                                command=self._toggle_require_password, **theme.switch_colors())
        switch.pack(side="right")

    def _toggle_require_password(self):
        db.set_require_password(self.require_password_var.get())
        self.settings = db.get_effective_settings(self.current_user["id"] if self.current_user else None)
        if self.on_settings_changed:
            self.on_settings_changed()

    def _toggle_show_ribbon_labels(self):
        db.set_show_ribbon_labels(self.show_ribbon_labels_var.get())
        self.settings = db.get_effective_settings(self.current_user["id"] if self.current_user else None)
        if self.on_settings_changed:
            self.on_settings_changed()

    # ---------------- منسدلة الثيم (ألوان بس، من غير أسماء ظاهرة) ----------------

    def _build_theme_dropdown(self, row):
        """بتبني "منسدلة" شكلها زي أي حقل اختيار تاني في الصفحة، بس بدل ما
        تعرض اسم بتعرض دايرة بلون الثيم الحالي - وبمجرد الضغط عليها بتفتح
        نافذة صغيرة تحتها فيها شبكة (5×5 = 25) من دواير الألوان بس (من غير
        أي اسم ظاهر جنبها)، وأي دايرة تتضغط الثيم يتغيّر فورًا"""
        wrapper = ctk.CTkFrame(row, fg_color=theme.INPUT_SUNKEN_BG, corner_radius=6,
                                width=160, height=32)
        wrapper.pack(side="right")
        wrapper.pack_propagate(False)

        current_preset = theme.THEME_PRESETS.get(self._current_theme_id, {})
        self.theme_swatch_dot = ctk.CTkLabel(
            wrapper, text="", fg_color=current_preset.get("primary", theme.PRIMARY_LIGHT),
            width=20, height=20, corner_radius=10)
        self.theme_swatch_dot.pack(side="right", padx=(0, 10), pady=6)

        arrow = ctk.CTkLabel(wrapper, text="▼", font=HEADER_LABEL_FONT, text_color=theme.TEXT_MUTED)
        arrow.pack(side="left", padx=(10, 0))

        self.theme_dropdown_wrapper = wrapper
        for widget in (wrapper, self.theme_swatch_dot, arrow):
            widget.bind("<Button-1>", lambda e: self._toggle_theme_popup())

    def _toggle_theme_popup(self):
        if getattr(self, "_theme_popup", None) and self._theme_popup.winfo_exists():
            self._close_theme_popup()
        else:
            self._open_theme_popup()

    def _open_theme_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        self.update_idletasks()
        x = self.theme_dropdown_wrapper.winfo_rootx()
        y = self.theme_dropdown_wrapper.winfo_rooty() + self.theme_dropdown_wrapper.winfo_height() + 4
        popup.geometry(f"+{x}+{y}")

        outer = ctk.CTkFrame(popup, fg_color=theme.CARD_BG, corner_radius=10,
                              border_width=1, border_color=theme.BORDER)
        outer.pack()

        self._theme_popup_name_label = ctk.CTkLabel(
            outer, text=theme.THEME_PRESETS.get(self._current_theme_id, {}).get("name", ""),
            font=HEADER_LABEL_FONT, text_color=theme.TEXT_MUTED)
        self._theme_popup_name_label.pack(pady=(10, 4))

        grid = ctk.CTkFrame(outer, fg_color="transparent")
        grid.pack(padx=10, pady=(0, 10))

        cols = 5
        for idx, (theme_id, preset) in enumerate(theme.THEME_PRESETS.items()):
            r, c = divmod(idx, cols)
            is_active = theme_id == self._current_theme_id
            dot = ctk.CTkButton(
                grid, text="✔" if is_active else "", width=34, height=34, corner_radius=17,
                fg_color=preset["primary"], hover_color=theme.darken_color(preset["primary"], 0.85),
                text_color="#FFFFFF", font=(theme.FONT_FAMILY, 13, "bold"),
                border_width=2 if is_active else 0, border_color=theme.TEXT_DARK,
                command=lambda tid=theme_id: self._pick_theme_from_popup(tid))
            dot.grid(row=r, column=c, padx=4, pady=4)
            dot.bind("<Enter>", lambda e, name=preset["name"]: self._theme_popup_name_label.configure(text=name))

        popup.after(200, lambda: self._arm_theme_popup_autoclose(popup))
        self._theme_popup = popup

    def _arm_theme_popup_autoclose(self, popup):
        """بنراقب أي نقرة (Button-1) بتحصل في أي حتة في البرنامج، ولو كانت
        برا حدود المنسدلة بنقفلها إحنا بنفسنا. ده بديل عن الاعتماد على
        FocusOut: تجربة عملية أثبتت إن FocusOut على نافذة overrideredirect
        زي دي بيحصل أحيانًا في نفس لحظة الضغط على زرار اللون نفسه (خصوصًا
        على ويندوز)، وده كان بيقفل المنسدلة (وبالتالي بيدمر الزرار) قبل ما
        الضغطة تخلص وتنفّذ الـ command بتاعها - يعني اختيار اللون كان بيتلغي
        صامت والمستخدم يحس إن الثيم "مش بيستجيب" خالص"""
        if not popup.winfo_exists():
            return
        try:
            popup.focus_force()
        except Exception:
            pass
        root = self.winfo_toplevel()
        self._theme_popup_click_guard_active = True
        root.bind_all("<Button-1>", self._on_click_outside_theme_popup, add="+")

    def _on_click_outside_theme_popup(self, event):
        popup = getattr(self, "_theme_popup", None)
        if not popup or not popup.winfo_exists():
            return
        widget = event.widget
        while widget is not None:
            if widget == popup:
                return  # النقرة جوه المنسدلة نفسها (أو زرار لون فيها) - سيبها تكمل عادي
            widget = getattr(widget, "master", None)
        self._close_theme_popup()

    def _close_theme_popup(self):
        if getattr(self, "_theme_popup_click_guard_active", False):
            try:
                self.winfo_toplevel().unbind_all("<Button-1>")
            except Exception:
                pass
            self._theme_popup_click_guard_active = False
        if getattr(self, "_theme_popup", None):
            try:
                self._theme_popup.destroy()
            except Exception:
                pass
            self._theme_popup = None

    def _pick_theme_from_popup(self, theme_id):
        # بنقفل النافذة المنسدلة الأول، وبعدين (بعد ما حدث الضغطة يخلص
        # تمامًا) بنطبق الثيم - عشان تطبيق الثيم بيعمل إعادة بناء كاملة
        # للبرنامج (وبيهد صفحة الإعدادات الحالية اللي فيها الزرار نفسه اللي
        # اتضغط عليه)، ولو ده حصل من جوه نفس ضغطة الزرار ده ممكن يعطل
        # الإجراء ويخلي الثيم ميتغيرش فعليًا رغم إن المستخدم دوس صح
        self._close_theme_popup()
        self.after(10, lambda: self._select_theme(theme_id))

    def _select_theme(self, theme_id):
        if self.current_user:
            db.set_user_theme(self.current_user["id"], theme_id)
        else:
            db.set_theme(theme_id)
        self.settings = db.get_effective_settings(self.current_user["id"] if self.current_user else None)
        self._current_theme_id = theme_id
        preset = theme.THEME_PRESETS.get(theme_id, {})
        try:
            self.theme_swatch_dot.configure(fg_color=preset.get("primary", theme.PRIMARY_LIGHT))
        except Exception:
            pass  # الصفحة ممكن تكون بدأت تتهد بالفعل - مش مشكلة
        if self.on_settings_changed:
            self.on_settings_changed()

    # ---------------- منسدلة تصميم أزرار الشريط الرئيسي (أسماء بس) ----------------

    def _build_nav_style_dropdown(self, row):
        self._nav_style_name_to_id = {meta["name"]: sid for sid, meta in theme.NAV_BUTTON_STYLES.items()}
        names = list(self._nav_style_name_to_id.keys())
        current_name = theme.NAV_BUTTON_STYLES.get(self._current_nav_style, {}).get("name", names[0])
        self.nav_style_menu = self._styled_option_menu(
            row, names, current_name, width=180,
            command=lambda v: self._select_nav_style(self._nav_style_name_to_id[v]))

    def _select_nav_style(self, style_id):
        if self.current_user:
            db.set_user_nav_button_style(self.current_user["id"], style_id)
        else:
            db.set_nav_button_style(style_id)
        self.settings = db.get_effective_settings(self.current_user["id"] if self.current_user else None)
        self._current_nav_style = style_id
        if self.on_settings_changed:
            self.on_settings_changed()

    # ---------------- منسدلة نمط رسم الأيقونات (أسماء بس) ----------------

    def _build_icon_pattern_dropdown(self, row):
        self._icon_pattern_name_to_id = {meta["name"]: pid for pid, meta in theme.ICON_PATTERNS.items()}
        names = list(self._icon_pattern_name_to_id.keys())
        current_name = theme.ICON_PATTERNS.get(self._current_icon_pattern, {}).get("name", names[0])
        self.icon_pattern_menu = self._styled_option_menu(
            row, names, current_name, width=180,
            command=lambda v: self._select_icon_pattern(self._icon_pattern_name_to_id[v]))

    def _select_icon_pattern(self, pattern_id):
        if self.current_user:
            db.set_user_icon_pattern(self.current_user["id"], pattern_id)
        else:
            db.set_icon_pattern(pattern_id)
        self.settings = db.get_effective_settings(self.current_user["id"] if self.current_user else None)
        self._current_icon_pattern = pattern_id
        icons.set_icon_pattern(pattern_id)
        if self.on_settings_changed:
            self.on_settings_changed()

    # ---------------- نطاق ساعات جدول المواعيد (مدير بس) ----------------

    def _build_schedule_hours_section(self, parent):
        card = self._make_card(
            parent, title="ساعات عمل جدول المواعيد",
            subtitle="الجدول متاح افتراضيًا على مدار 24 ساعة. يمكن تحديد نطاق أضيق (مثلاً من 8 إلى 10) عند "
                     "عدم الحاجة لعرض كل الساعات، وسيُغلَق الباقي من الجدول.")

        row = self._field_row(card, "النطاق المسموح", pady=(0, 20))
        current = db.get_settings()
        hours_values = [f"{h:02d}:00" for h in range(24)] + ["24:00"]

        end_h = current["schedule_end_hour"]
        self.schedule_end_menu = ctk.CTkOptionMenu(row, values=hours_values[1:], width=90,
                                                     fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                                                     button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                                                     command=lambda v: self._save_schedule_hours())
        self.schedule_end_menu.set("24:00" if end_h == 24 else f"{end_h:02d}:00")
        self.schedule_end_menu.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(row, text="إلى", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(side="left", padx=4)

        self.schedule_start_menu = ctk.CTkOptionMenu(row, values=hours_values[:24], width=90,
                                                       fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                                                       button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                                                       command=lambda v: self._save_schedule_hours())
        self.schedule_start_menu.set(f"{current['schedule_start_hour']:02d}:00")
        self.schedule_start_menu.pack(side="right")
        ctk.CTkLabel(row, text="من", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(side="right", padx=4)

    def _save_schedule_hours(self):
        start_h = int(self.schedule_start_menu.get().split(":")[0])
        end_h = int(self.schedule_end_menu.get().split(":")[0])
        if end_h <= start_h:
            end_h = min(start_h + 1, 24)
            self.schedule_end_menu.set("24:00" if end_h == 24 else f"{end_h:02d}:00")
        db.set_schedule_hours(start_h, end_h)
        if self.on_settings_changed:
            self.on_settings_changed()

    # ---------------- أيام الإجازة الأسبوعية الثابتة (مدير بس) ----------------

    WEEKDAY_OPTIONS = [
        (0, "الاثنين"), (1, "الثلاثاء"), (2, "الأربعاء"),
        (3, "الخميس"), (4, "الجمعة"), (5, "السبت"), (6, "الأحد"),
    ]

    def _build_holidays_section(self, parent):
        card = self._make_card(
            parent, title="أيام الإجازة الأسبوعية",
            subtitle="يمكن تحديد الأيام التي تكون العيادة إجازة فيها أسبوعيًا، وستظهر باللون الأحمر في التقويم. "
                     "كما يمكن تمييز أيام إجازة إضافية معيّنة من زر (🏖) أعلى كل يوم في صفحة المواعيد.")

        row = ctk.CTkFrame(card, fg_color=theme.BG_MAIN, corner_radius=8)
        row.pack(fill="x", padx=22, pady=(0, 20))
        self.weekly_holiday_vars = {}
        current = db.get_weekly_holidays()
        for wd_num, wd_label in self.WEEKDAY_OPTIONS:
            var = ctk.BooleanVar(value=wd_num in current)
            self.weekly_holiday_vars[wd_num] = var
            chk = ctk.CTkCheckBox(row, text=wd_label, font=HEADER_LABEL_FONT, variable=var,
                                   command=self._save_weekly_holidays, **theme.checkbox_colors())
            chk.pack(side="right", padx=10, pady=10)

    def _save_weekly_holidays(self):
        selected = [wd for wd, var in self.weekly_holiday_vars.items() if var.get()]
        db.set_weekly_holidays(selected)
        if self.on_settings_changed:
            self.on_settings_changed()

    def _choose_logo(self):
        path = filedialog.askopenfilename(
            title="اختر صورة اللوجو",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        if path:
            os.makedirs(ASSETS_DIR, exist_ok=True)
            dest = os.path.join(ASSETS_DIR, "clinic_logo" + os.path.splitext(path)[1])
            shutil.copy(path, dest)
            self._new_logo_path = dest
            self.logo_path_label.configure(text=os.path.basename(dest))

    def _add_phone_row(self, phone_id=None, phone_number=""):
        row = ctk.CTkFrame(self.phones_list_frame, fg_color="transparent")
        row.pack(anchor="e", pady=2, fill="x")

        entry = ctk.CTkEntry(row, height=30, justify="right", font=HEADER_LABEL_FONT)
        theme.apply_sunken_style(entry)
        if phone_number:
            entry.insert(0, phone_number)
        entry.pack(side="right", fill="x", expand=True, padx=(6, 0))

        def remove():
            row.destroy()
            self.phone_entries[:] = [t for t in self.phone_entries if t[2] is not row]

        ctk.CTkButton(row, text="✕", width=32, height=32, fg_color=theme.DANGER,
                      command=remove).pack(side="right")

        self.phone_entries.append((phone_id, entry, row))

    def _apply_appearance_settings(self, *_args):
        """بتتنادى فورًا لما اللغة أو أي إعداد خط يتغيّر - بتحفظ وتطبّق على
        طول من غير ما يحتاج المستخدم يدوس على زرار حفظ منفصل (زي ما بقى
        شغال بالظبط للثيمات الجاهزة). الخط تفضيل شخصي بيتحفظ للمستخدم
        الحالي بس، أما اللغة فإعداد عام للعيادة كلها (بيأثر على كل حد
        بيستخدم البرنامج، مش مظهر شخصي)"""
        if self.current_user:
            db.set_user_fonts(
                self.current_user["id"],
                system_font_family=self.system_font_menu.get(),
                content_font_family=self.content_font_menu.get())
        else:
            db.update_settings(
                system_font_family=self.system_font_menu.get(),
                content_font_family=self.content_font_menu.get())
        db.update_settings(language=LANGUAGE_OPTIONS.get(self.language_menu.get(), "ar"))
        self.settings = db.get_effective_settings(self.current_user["id"] if self.current_user else None)
        if self.on_settings_changed:
            self.on_settings_changed()

    def _reset_user_appearance(self):
        """بيمسح كل تخصيصات المظهر الشخصية للمستخدم الحالي (ثيم/شكل أزرار/
        نمط أيقونات/خط) ويرجّعه يشوف نفس مظهر العيادة الافتراضي اللي باقي
        المستخدمين شايفينه"""
        if not self.current_user:
            return
        db.reset_user_appearance(self.current_user["id"])
        self.settings = db.get_effective_settings(self.current_user["id"])
        if self.on_settings_changed:
            self.on_settings_changed()

    def _save(self):
        db.update_settings(
            clinic_name=self.name_entry.get().strip() or "عيادتي",
            logo_path=self._new_logo_path if self._new_logo_path else self.settings["logo_path"],
            clinic_address=self.address_entry.get().strip(),
            tax_card_number=self.tax_card_entry.get().strip(),
        )

        # مزامنة أرقام التليفونات: نحدّث الموجود، نضيف الجديد، ونمسح أي رقم
        # اتشال من الشاشة (اللي اتحذف بزرار ✕ ومبقاش موجود في phone_entries)
        existing_ids = {p["id"] for p in db.get_clinic_phones()}
        kept_ids = set()
        for phone_id, entry, _row in self.phone_entries:
            value = entry.get().strip()
            if not value:
                continue
            if phone_id is None:
                new_id = db.add_clinic_phone(value)
                kept_ids.add(new_id)
            else:
                db.update_clinic_phone(phone_id, value)
                kept_ids.add(phone_id)
        for old_id in existing_ids - kept_ids:
            db.delete_clinic_phone(old_id)

        if self.on_settings_changed:
            self.on_settings_changed()

    # ---------------- المستخدمين والصلاحيات (مدير بس) ----------------

    def _build_users_section(self, parent):
        users_card = self._make_card(parent)

        header = ctk.CTkFrame(users_card, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(0, 10))
        ctk.CTkLabel(header, text="المستخدمون", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")
        ctk.CTkButton(header, text="+ إضافة مستخدم", width=140, height=34, font=HEADER_LABEL_FONT,
                      fg_color=theme.PRIMARY_LIGHT,
                      command=self._open_add_user_dialog).pack(side="left")

        for u in db.get_all_users():
            if not u["active"]:
                continue
            row = ctk.CTkFrame(users_card, fg_color=theme.BG_MAIN, corner_radius=8)
            row.pack(fill="x", padx=22, pady=4)

            if u["id"] != self.current_user["id"]:
                ctk.CTkButton(row, text="تعطيل", width=70, height=28, fg_color=theme.DANGER,
                              font=theme.FONT_SMALL,
                              command=lambda uid=u["id"]: self._deactivate_user(uid)
                              ).pack(side="left", padx=8, pady=8)

            ctk.CTkButton(row, text="🔑 كلمة المرور", width=110, height=28,
                          font=theme.FONT_SMALL, fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
                          border_width=1, border_color=theme.BORDER,
                          command=lambda uid=u["id"], uname=u["username"], fname=u["full_name"]:
                          self._open_change_password_dialog(uid, uname, fname)
                          ).pack(side="left", padx=4, pady=8)

            role_label = db.ROLE_LABELS.get(u["role"], u["role"])
            ctk.CTkLabel(row, text=role_label, font=theme.FONT_SMALL, text_color="#FFFFFF",
                         fg_color=theme.TEXT_MUTED, corner_radius=6, width=70, height=26).pack(
                side="right", padx=8, pady=8)
            ctk.CTkLabel(row, text=f"{u['full_name']}  ({u['username']})", font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_DARK, anchor="e").pack(side="right", padx=8, pady=8)

        ctk.CTkFrame(users_card, fg_color="transparent", height=14).pack()

        # ---- جدول الصلاحيات الحقيقي (Grid) ----
        perm_card = self._make_card(
            parent, title="صلاحيات الأدوار",
            subtitle="تحديد الصلاحيات التي يمكن للطبيب أو السكرتارية الوصول إليها. يملك المدير جميع الصلاحيات دائمًا تلقائيًا.")

        table = ctk.CTkFrame(perm_card, fg_color="transparent")
        table.pack(fill="x", padx=22, pady=(0, 8))
        # عمود التسمية بياخد الباقي من العرض، وعمودين الصلاحيات بعرض ثابت
        # متساوي - كده الخانات بتتظبط في نفس المكان بالظبط من أول صف لآخر صف
        table.grid_columnconfigure(0, weight=1)
        table.grid_columnconfigure(1, weight=0, minsize=100)
        table.grid_columnconfigure(2, weight=0, minsize=100)

        # هيدر الجدول
        ctk.CTkLabel(table, text="الصلاحية", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK, anchor="e").grid(
            row=0, column=0, sticky="e", padx=(10, 6), pady=(4, 8))
        ctk.CTkLabel(table, text="سكرتارية", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                     anchor="center").grid(row=0, column=1, pady=(4, 8))
        ctk.CTkLabel(table, text="طبيب", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                     anchor="center").grid(row=0, column=2, pady=(4, 8))

        ctk.CTkFrame(table, fg_color=theme.BORDER, height=1).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        matrix = db.get_full_permissions_matrix()
        self.permission_vars = {}

        for i, (perm_key, perm_label) in enumerate(db.PERMISSION_LABELS.items(), start=2):
            # تلوين متبادل للصفوف (Zebra striping) عشان يبقى أسهل في القراءة
            # وتتبع الصف الصح لحد آخر خانة اختيار فيه
            row_bg = theme.BG_MAIN if i % 2 == 0 else theme.CARD_BG

            label_cell = ctk.CTkLabel(table, text=perm_label, font=theme.FONT_NORMAL,
                                       text_color=theme.TEXT_DARK, anchor="e", justify="right",
                                       fg_color=row_bg, wraplength=340)
            label_cell.grid(row=i, column=0, sticky="ew", padx=(10, 6), pady=1, ipady=8)

            doctor_var = ctk.BooleanVar(value=matrix["doctor"].get(perm_key, False))
            secretary_var = ctk.BooleanVar(value=matrix["secretary"].get(perm_key, False))
            self.permission_vars[perm_key] = {"doctor": doctor_var, "secretary": secretary_var}

            secretary_cell = ctk.CTkFrame(table, fg_color=row_bg)
            secretary_cell.grid(row=i, column=1, sticky="nsew", pady=1)
            ctk.CTkCheckBox(secretary_cell, text="", variable=secretary_var,
                             width=24, **theme.checkbox_colors()).pack(expand=True, pady=8)

            doctor_cell = ctk.CTkFrame(table, fg_color=row_bg)
            doctor_cell.grid(row=i, column=2, sticky="nsew", pady=1)
            ctk.CTkCheckBox(doctor_cell, text="", variable=doctor_var,
                             width=24, **theme.checkbox_colors()).pack(expand=True, pady=8)

        save_perm_wrapper = theme.make_shadowed_button(
            perm_card, "حفظ الصلاحيات", command=self._save_permissions,
            width=170, height=42, font=theme.FONT_SUBTITLE)
        save_perm_wrapper.pack(pady=(12, 20))

    def _save_permissions(self):
        for perm_key, roles in self.permission_vars.items():
            db.set_role_permission("doctor", perm_key, roles["doctor"].get())
            db.set_role_permission("secretary", perm_key, roles["secretary"].get())
        if self.on_settings_changed:
            self.on_settings_changed()

    def _deactivate_user(self, user_id):
        db.deactivate_user(user_id)
        if self.on_settings_changed:
            self.on_settings_changed()

    def _build_password_fields(self, parent, label="كلمة المرور"):
        """
        صف كلمة مرور + تأكيدها، مع زرار عين لإظهار/إخفاء الاتنين. بيرجع
        (password_entry, confirm_entry) عشان تقدري تقرأي القيمة منهم بعدين.
        """
        ctk.CTkLabel(parent, text=label, font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        pw_row = ctk.CTkFrame(parent, fg_color="transparent")
        pw_row.pack(fill="x", padx=30, pady=(2, 10))
        password_entry = ctk.CTkEntry(pw_row, show="*", height=40, justify="right", font=theme.FONT_NORMAL)
        theme.apply_sunken_style(password_entry)
        password_entry.pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(parent, text="تأكيد كلمة المرور", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        confirm_row = ctk.CTkFrame(parent, fg_color="transparent")
        confirm_row.pack(fill="x", padx=30, pady=(2, 6))
        confirm_entry = ctk.CTkEntry(confirm_row, show="*", height=40, justify="right", font=theme.FONT_NORMAL)
        theme.apply_sunken_style(confirm_entry)
        confirm_entry.pack(side="right", fill="x", expand=True)

        state = {"visible": False}

        def toggle():
            state["visible"] = not state["visible"]
            show_char = "" if state["visible"] else "*"
            password_entry.configure(show=show_char)
            confirm_entry.configure(show=show_char)
            eye_btn.configure(text="🙈" if state["visible"] else "👁")

        eye_btn = ctk.CTkButton(pw_row, text="👁", width=36, height=40, font=(theme.FONT_FAMILY, 13),
                                 fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                                 hover_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                                 command=toggle)
        eye_btn.pack(side="left", padx=(6, 0))

        return password_entry, confirm_entry

    def _open_add_user_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("إضافة مستخدم")
        dialog.geometry("340x580")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="إضافة مستخدم جديد", font=theme.FONT_SUBTITLE).pack(pady=(16, 14))

        ctk.CTkLabel(dialog, text="الاسم بالكامل", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        name_entry = RTLEntry(dialog, width=260, height=40)
        theme.apply_sunken_style(name_entry)
        name_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(dialog, text="اسم المستخدم (بالإنجليزي)", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        username_entry = ctk.CTkEntry(dialog, width=260, height=40, justify="right", font=theme.FONT_NORMAL)
        theme.apply_sunken_style(username_entry)
        username_entry.pack(padx=30, pady=(2, 10), anchor="e")

        password_entry, confirm_entry = self._build_password_fields(dialog)

        ctk.CTkLabel(dialog, text="نوع الحساب", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        role_menu = ctk.CTkOptionMenu(dialog, values=["مدير", "طبيب", "سكرتارية"], width=260,
                                       fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                                       button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9))
        role_menu.set("سكرتارية")
        role_menu.pack(padx=30, pady=(2, 16), anchor="e")

        status_label = ctk.CTkLabel(dialog, text="", font=theme.FONT_SMALL, text_color=theme.DANGER,
                                     wraplength=280)
        status_label.pack()

        role_map = {"مدير": "manager", "طبيب": "doctor", "سكرتارية": "secretary"}

        def save():
            full_name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get()
            confirm = confirm_entry.get()

            if not (full_name and username and password):
                status_label.configure(text="لازم تملأ كل الحقول")
                return
            if password != confirm:
                status_label.configure(text="كلمة المرور وتأكيدها غير متطابقين")
                return

            try:
                db.add_user(username, password, full_name, role_map[role_menu.get()])
            except Exception:
                status_label.configure(text="اسم المستخدم هذا مستخدَم من قبل")
                return

            # تأكيد فعلي إن الباسورد اتسجل صح قبل ما نقفل الشاشة - بنجرب ندخل بيه فورًا
            verified = db.authenticate_user(username, password)
            if not verified:
                status_label.configure(
                    text="⚠ المستخدم اتسجل بس حصل خطأ غير متوقع في حفظ كلمة المرور. جربي تاني.",
                    text_color=theme.DANGER)
                return

            status_label.configure(text="✔ تم الإضافة والتأكد إن كلمة المرور شغالة",
                                    text_color=theme.SUCCESS)
            dialog.after(700, dialog.destroy)
            if self.on_settings_changed:
                dialog.after(720, self.on_settings_changed)

        ctk.CTkButton(dialog, text="إضافة", height=44, fg_color=theme.SUCCESS,
                      command=save).pack(padx=30, pady=10, fill="x")

    def _open_change_password_dialog(self, user_id, username, full_name):
        dialog = ctk.CTkToplevel(self)
        dialog.title("تغيير كلمة المرور")
        dialog.geometry("340x400")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"تغيير كلمة مرور: {full_name}", font=theme.FONT_SUBTITLE,
                     wraplength=280).pack(pady=(16, 14))

        password_entry, confirm_entry = self._build_password_fields(dialog, label="كلمة المرور الجديدة")

        status_label = ctk.CTkLabel(dialog, text="", font=theme.FONT_SMALL, text_color=theme.DANGER,
                                     wraplength=280)
        status_label.pack(pady=4)

        def save():
            password = password_entry.get()
            confirm = confirm_entry.get()

            if not password:
                status_label.configure(text="اكتب كلمة المرور الجديدة", text_color=theme.DANGER)
                return
            if password != confirm:
                status_label.configure(text="كلمة المرور وتأكيدها غير متطابقين", text_color=theme.DANGER)
                return

            db.update_user(user_id, password=password)

            # تأكيد فعلي إن كلمة المرور الجديدة شغالة قبل ما نقفل الشاشة
            verified = db.authenticate_user(username, password)
            if not verified:
                status_label.configure(
                    text="⚠ حصل خطأ في حفظ كلمة المرور الجديدة. جربي تاني.", text_color=theme.DANGER)
                return

            status_label.configure(text="✔ اتغيّرت وتم التأكد إنها شغالة", text_color=theme.SUCCESS)
            dialog.after(700, dialog.destroy)

        ctk.CTkButton(dialog, text="حفظ كلمة المرور الجديدة", height=44, fg_color=theme.SUCCESS,
                      command=save).pack(padx=30, pady=10, fill="x")
