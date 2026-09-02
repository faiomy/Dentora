# -*- coding: utf-8 -*-
"""
صفحة طاقم العمل:
- إضافة أو حذف أي عامل (وتعديل بياناته الحساسة زي المرتب) بيتطلب تأكيد
  باسورد حساب المدير، ومتاح للمدير بس (باقي الأدوار بتشوف البيانات بس)
- المديرين والأطباء والسكرتارية حسابات دخول فعلية (جدول users)
- مساعدين الأطباء وخدمات مساعدة مالهمش حساب دخول (جدول support_staff)
- العرض بتابات كبيرة وخط واضح - كل تاب بيوضح بلون مميز لما يتحدد
- بيانات كل عامل: شخصية (ميلاد/عنوان/تليفونات/صورة/رقم قومي وصورته) ومالية
  (مرتب ثابت/نسبة من الدخل/تاريخ استلام العمل/نسبة الزيادة السنوية) - المرتب
  الثابت بيتزاد تلقائيًا كل سنة بالنسبة المحددة من تاريخ الاستلام
"""

import os
import shutil
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image
import theme
from pages.notebook_tabs import NotebookTabview
import database as db
from pages.rtl_entry import RTLEntry

WEEKDAYS = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]

STAFF_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(db.DB_PATH)), "assets", "staff_files")


def _save_uploaded_file(src_path, prefix):
    os.makedirs(STAFF_FILES_DIR, exist_ok=True)
    ext = os.path.splitext(src_path)[1]
    dest_name = f"{prefix}_{abs(hash(src_path)) % 100000}{ext}"
    dest_path = os.path.join(STAFF_FILES_DIR, dest_name)
    shutil.copy(src_path, dest_path)
    return dest_path


class StaffPage(ctk.CTkFrame):
    def __init__(self, master, current_user=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_user = current_user
        self._add_tooltip = None
        self._build()

    def _is_manager(self):
        return bool(self.current_user and self.current_user.get("role") == "manager")

    # ---------------- تأكيد باسورد المدير قبل أي إضافة/حذف/تعديل حساس ----------------

    def _require_manager_password(self, on_confirmed):
        if not self._is_manager():
            theme.show_toast(self, "هذا الإجراء متاح للمدير فقط", kind="error")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("تأكيد الهوية")
        dialog.geometry("340x220")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="أدخل باسورد حساب المدير للتأكيد",
                     font=theme.FONT_NORMAL, wraplength=280, justify="right").pack(pady=(20, 10))

        password_entry = ctk.CTkEntry(dialog, show="*", width=260, height=38,
                                       justify="right", font=theme.FONT_NORMAL)
        password_entry.pack(pady=(0, 6))
        password_entry.focus()

        error_label = ctk.CTkLabel(dialog, text="", font=theme.FONT_SMALL, text_color=theme.DANGER)
        error_label.pack()

        def confirm():
            password = password_entry.get().strip()
            verified = db.authenticate_user(self.current_user["username"], password)
            if not verified or verified.get("role") != "manager":
                error_label.configure(text="⚠ الباسورد غلط")
                return
            dialog.destroy()
            on_confirmed()

        password_entry.bind("<Return>", lambda e: confirm())
        ctk.CTkButton(dialog, text="✔ تأكيد", height=40, fg_color=theme.SUCCESS,
                      command=confirm).pack(padx=30, pady=14, fill="x")

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(header, text="طاقم العمل", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")

        # زرار "إضافة" واحد بس - شكل شيك (أيقونة + نص)، هوفر بيوضح الغرض،
        # ودوسة بتفتح قايمة اختيار نوع العضو (لو المستخدم مش مدير هيتقفل تلقائيًا)
        add_btn = ctk.CTkButton(header, text="＋  إضافة", width=130, height=40,
                                 corner_radius=theme.RADIUS_MD, font=theme.FONT_NAV,
                                 fg_color=theme.SUCCESS, hover_color=theme.darken_color(theme.SUCCESS, 0.85),
                                 command=self._open_add_menu)
        add_btn.pack(side="left")
        self._add_btn = add_btn
        add_btn.bind("<Enter>", self._show_add_tooltip)
        add_btn.bind("<Leave>", self._hide_add_tooltip)

        if not self._is_manager():
            ctk.CTkLabel(header, text="🔒 إضافة/حذف/تعديل بيانات طاقم العمل متاحة للمدير بس",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(side="left", padx=10)

        # تابات أكبر وخط أوضح وBold - متساوية المساحة ومتصلة بالمحتوى تحتها
        # زي فواصل الكشكول الورقي
        self.tabview = NotebookTabview(self, font=(theme.CONTENT_FONT_FAMILY, 17, "bold"),
                                       active_fg_color=theme.TAB_ACTIVE_BG,
                                       inactive_fg_color=theme.TAB_INACTIVE_BG,
                                       border_color=theme.ACCENT_BORDER,
                                       content_fg_color=theme.CARD_BG,
                                       corner_radius=theme.TAB_RADIUS)
        self.tabview.pack(fill="both", expand=True)

        self.tab_managers = self.tabview.add("المديرين")
        self.tab_doctors = self.tabview.add("الأطباء")
        self.tab_assistants = self.tabview.add("مساعدين الأطباء")
        self.tab_secretaries = self.tabview.add("السكرتارية")
        self.tab_support = self.tabview.add("خدمات مساعدة")

        self.tab_frames = {}
        for tab in (self.tab_managers, self.tab_doctors, self.tab_assistants,
                    self.tab_secretaries, self.tab_support):
            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=4, pady=4)
            self.tab_frames[tab] = scroll

        self.refresh()

    # ---------------- زرار الإضافة: هوفر + قايمة الاختيار ----------------

    def _show_add_tooltip(self, event=None):
        self._hide_add_tooltip()
        tooltip = tk.Toplevel(self)
        tooltip.overrideredirect(True)
        tooltip.attributes("-topmost", True)
        card = ctk.CTkFrame(tooltip, fg_color=theme.TEXT_DARK, corner_radius=theme.RADIUS_SM)
        card.pack()
        ctk.CTkLabel(card, text="إضافة عضو عامل جديد", font=theme.FONT_SMALL,
                     text_color="#FFFFFF").pack(padx=10, pady=6)
        x = self._add_btn.winfo_rootx()
        y = self._add_btn.winfo_rooty() + self._add_btn.winfo_height() + 4
        tooltip.geometry(f"+{x}+{y}")
        self._add_tooltip = tooltip

    def _hide_add_tooltip(self, event=None):
        if self._add_tooltip is not None:
            try:
                self._add_tooltip.destroy()
            except Exception:
                pass
            self._add_tooltip = None

    def _open_add_menu(self):
        self._hide_add_tooltip()
        if not self._is_manager():
            theme.show_toast(self, "الإضافة متاحة للمدير بس", kind="error")
            return
        menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 13))
        menu.add_command(label="👑  إضافة مدير", command=lambda: self._open_add_user_dialog("manager"))
        menu.add_command(label="🩺  إضافة طبيب", command=lambda: self._open_add_user_dialog("doctor"))
        menu.add_command(label="🗂️  إضافة سكرتارية", command=lambda: self._open_add_user_dialog("secretary"))
        menu.add_command(label="🧑‍⚕️  إضافة مساعد طبيب",
                          command=lambda: self._open_add_support_dialog("assistant"))
        menu.add_command(label="🧰  إضافة خدمات مساعدة",
                          command=lambda: self._open_add_support_dialog("support"))
        try:
            x = self._add_btn.winfo_rootx()
            y = self._add_btn.winfo_rooty() + self._add_btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # ---------------- عرض العاملين حسب كل تاب ----------------

    def refresh(self):
        rows_config = [
            (self.tab_managers, "user", [
                u for u in db.get_all_users() if u["role"] == "manager" and u["active"]
            ]),
            (self.tab_doctors, "user", [
                u for u in db.get_all_users() if u["role"] == "doctor" and u["active"]
            ]),
            (self.tab_assistants, "support", db.get_support_staff(staff_type="assistant")),
            (self.tab_secretaries, "user", [
                u for u in db.get_all_users() if u["role"] == "secretary" and u["active"]
            ]),
            (self.tab_support, "support", db.get_support_staff(staff_type="support")),
        ]
        for tab, kind, rows in rows_config:
            self._render_tab(tab, kind, rows)

    def _render_tab(self, tab, kind, rows):
        scroll = self.tab_frames[tab]
        for w in scroll.winfo_children():
            w.destroy()

        if not rows:
            ctk.CTkLabel(scroll, text="لا يوجد أحد مسجل هنا بعد", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(pady=30)
            return

        for r in rows:
            card = ctk.CTkFrame(scroll, fg_color=theme.CARD_BG, corner_radius=theme.RADIUS_MD,
                                 border_width=1, border_color=theme.BORDER)
            card.pack(fill="x", pady=5, padx=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(10, 2))

            if self._is_manager():
                remove_cmd = self._deactivate_user if kind == "user" else self._deactivate_support
                ctk.CTkButton(top_row, text="حذف", width=64, height=26, fg_color=theme.DANGER,
                              font=theme.FONT_SMALL,
                              command=lambda rid=r["id"], k=kind: self._require_manager_password(
                                  lambda: remove_cmd(rid))).pack(side="left", padx=(0, 6))

                ctk.CTkButton(top_row, text="تعديل بيانات", width=90, height=26,
                              fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK,
                              border_width=1, border_color=theme.BORDER, font=theme.FONT_SMALL,
                              command=lambda row=r, k=kind: self._require_manager_password(
                                  lambda: self._open_edit_dialog(row, k))).pack(side="left")

            extra = r.get("username") if kind == "user" else None
            name_text = r["full_name"] + (f"  ({extra})" if extra else "")
            ctk.CTkLabel(top_row, text=name_text, font=(theme.CONTENT_FONT_FAMILY, 17, "bold"),
                         text_color=theme.TEXT_DARK).pack(side="right")

            details_row = ctk.CTkFrame(card, fg_color="transparent")
            details_row.pack(fill="x", padx=14, pady=(0, 6))

            details = []
            if r.get("phone"):
                details.append(f"📞 {r['phone']}")
            if r.get("specialty"):
                details.append(f"🩺 {r['specialty']}")
            if r.get("work_days"):
                details.append(f"🗓 {r['work_days']}")
            age = db.calculate_age(r.get("birth_date"))
            if age is not None:
                details.append(f"العمر {age}")
            if r.get("address"):
                details.append(f"📍 {r['address']}")
            if not details:
                details.append("لا توجد بيانات إضافية مسجلة")

            ctk.CTkLabel(details_row, text="   -   ".join(details), font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED, anchor="e", wraplength=700,
                         justify="right").pack(side="right")

            # بيانات المرتب - ظاهرة للمدير بس
            if self._is_manager() and (r.get("salary") or r.get("income_percent")):
                salary_row = ctk.CTkFrame(card, fg_color=theme.BG_MAIN, corner_radius=theme.RADIUS_SM)
                salary_row.pack(fill="x", padx=14, pady=(0, 10))
                salary_parts = []
                if r.get("salary"):
                    current_salary = db.calculate_current_salary(
                        r.get("salary"), r.get("start_date"), r.get("annual_raise_percent"))
                    salary_parts.append(f"💰 المرتب الحالي: {current_salary:g} ج")
                    if r.get("annual_raise_percent"):
                        salary_parts.append(f"(زيادة سنوية {r['annual_raise_percent']:g}%)")
                if r.get("income_percent"):
                    salary_parts.append(f"نسبة من الدخل: {r['income_percent']:g}%")
                if r.get("start_date"):
                    salary_parts.append(f"بدأ العمل: {r['start_date']}")
                ctk.CTkLabel(salary_row, text="   -   ".join(salary_parts), font=theme.FONT_SMALL,
                             text_color=theme.TEXT_DARK, anchor="e").pack(side="right", padx=10, pady=6)

    def _deactivate_user(self, user_id):
        db.deactivate_user(user_id)
        self.refresh()
        theme.show_toast(self, "تم الحذف", kind="error")

    def _deactivate_support(self, staff_id):
        db.set_support_staff_active(staff_id, False)
        self.refresh()
        theme.show_toast(self, "تم الحذف", kind="error")

    # ---------------- عنصر مشترك: اختيار أيام العمل ----------------

    def _build_workdays_picker(self, parent, selected_days=None):
        selected_set = set((selected_days or "").split("،")) if selected_days else set()
        ctk.CTkLabel(parent, text="أيام العمل", font=theme.FONT_NORMAL).pack(anchor="e", padx=30, pady=(4, 2))
        days_row = ctk.CTkFrame(parent, fg_color="transparent")
        days_row.pack(padx=30, pady=(0, 10), anchor="e", fill="x")

        # بنستخدم Grid (4 أعمدة × صفين) بدل صف واحد طويل، عشان الأيام السبعة
        # كلها تبقى ظاهرة مهما كان عرض النافذة (كان "الجمعة" بيختفي لإن
        # الصف الواحد كان بيطلع بره حدود النافذة)
        day_vars = {}
        cols = 4
        for i, day in enumerate(WEEKDAYS):
            var = ctk.BooleanVar(value=day in selected_set)
            chk = ctk.CTkCheckBox(days_row, text=day, variable=var, font=theme.FONT_SMALL,
                                   width=1, checkbox_width=18, checkbox_height=18,
                                   **theme.checkbox_colors())
            row_i, col_i = divmod(i, cols)
            # عرض من اليمين لليسار: العمود 0 أقصى اليمين
            chk.grid(row=row_i, column=cols - 1 - col_i, padx=6, pady=4, sticky="e")
            day_vars[day] = var

        def get_selected():
            return "،".join(d for d in WEEKDAYS if day_vars[d].get())

        return get_selected

    def _build_date_entry(self, parent, label_text, initial_iso=None):
        """حقل تاريخ متقسم (يوم/شهر/سنة) بيتنقل تلقائي من خانة للتانية بعد
        ما تملاها - بدل ما تكتب التاريخ كله يدوي بصيغة نصية"""
        ctk.CTkLabel(parent, text=label_text, font=theme.FONT_NORMAL).pack(anchor="e", padx=30, pady=(4, 2))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(padx=30, pady=(0, 10), anchor="e")

        init_y, init_m, init_d = "", "", ""
        if initial_iso:
            try:
                init_y, init_m, init_d = initial_iso.split("-")
                init_m, init_d = init_m.lstrip("0") or "0", init_d.lstrip("0") or "0"
            except Exception:
                pass

        year_entry = ctk.CTkEntry(row, width=60, height=36, justify="center", font=theme.FONT_NORMAL)
        ctk.CTkLabel(row, text="/", font=theme.FONT_NORMAL).pack(side="right")
        month_entry = ctk.CTkEntry(row, width=46, height=36, justify="center", font=theme.FONT_NORMAL)
        ctk.CTkLabel(row, text="/", font=theme.FONT_NORMAL).pack(side="right")
        day_entry = ctk.CTkEntry(row, width=46, height=36, justify="center", font=theme.FONT_NORMAL)

        # ترتيب العرض من اليمين لليسار: يوم / شهر / سنة (زي ما بتتكتب التواريخ بالعربي)
        day_entry.pack(side="right", padx=2)
        month_entry.pack(side="right", padx=2)
        year_entry.pack(side="right", padx=2)

        day_entry.insert(0, init_d)
        month_entry.insert(0, init_m)
        year_entry.insert(0, init_y)

        def on_day_key(event):
            if len(day_entry.get()) >= 2:
                month_entry.focus()
                month_entry.select_range(0, "end")

        def on_month_key(event):
            if len(month_entry.get()) >= 2:
                year_entry.focus()
                year_entry.select_range(0, "end")

        day_entry.bind("<KeyRelease>", on_day_key)
        month_entry.bind("<KeyRelease>", on_month_key)

        def get_iso():
            y, m, d = year_entry.get().strip(), month_entry.get().strip(), day_entry.get().strip()
            if not (y and m and d):
                return ""
            try:
                return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            except ValueError:
                return ""

        return get_iso

    def _build_photo_picker(self, parent, label_text, current_path=None):
        ctk.CTkLabel(parent, text=label_text, font=theme.FONT_NORMAL).pack(anchor="e", padx=30, pady=(4, 2))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(padx=30, pady=(0, 10), anchor="e", fill="x")

        path_holder = {"value": current_path or ""}
        preview_label = ctk.CTkLabel(row, text="", width=50, height=50, fg_color=theme.BG_MAIN,
                                      corner_radius=theme.RADIUS_SM)
        preview_label.pack(side="right", padx=(6, 0))

        def refresh_preview():
            if path_holder["value"] and os.path.exists(path_holder["value"]):
                try:
                    img = Image.open(path_holder["value"])
                    ctk_img = ctk.CTkImage(light_image=img, size=(50, 50))
                    preview_label.configure(image=ctk_img, text="")
                except Exception:
                    preview_label.configure(image=None, text="⚠")
            else:
                preview_label.configure(image=None, text="—")

        refresh_preview()

        def choose():
            path = filedialog.askopenfilename(
                title="اختيار صورة", filetypes=[("صور", "*.jpg *.jpeg *.png")])
            if path:
                path_holder["value"] = path
                refresh_preview()

        ctk.CTkButton(row, text="اختيار صورة", width=110, height=36, fg_color=theme.PRIMARY_LIGHT,
                      command=choose).pack(side="right", padx=6)

        return path_holder

    # ---------------- إضافة مدير / طبيب / سكرتارية (حساب دخول فعلي) ----------------

    def _open_add_user_dialog(self, role):
        role_titles = {"manager": "مدير", "doctor": "طبيب", "secretary": "سكرتارية"}
        role_title = role_titles.get(role, role)

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"إضافة {role_title}")
        dialog.geometry("420x900")
        dialog.grab_set()

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text=f"إضافة {role_title} جديد", font=theme.FONT_SUBTITLE).pack(
            pady=(16, 14))

        ctk.CTkLabel(scroll, text="الاسم بالكامل", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        name_entry = RTLEntry(scroll, width=280, height=38)
        name_entry.pack(padx=30, pady=(2, 10), anchor="e")

        get_birth_date = self._build_date_entry(scroll, "تاريخ الميلاد")

        ctk.CTkLabel(scroll, text="محل الإقامة / العنوان", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        address_entry = RTLEntry(scroll, width=280, height=38)
        address_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="أرقام التليفونات", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        phone_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        phone_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="الرقم القومي", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        national_id_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right",
                                          font=theme.FONT_NORMAL)
        national_id_entry.pack(padx=30, pady=(2, 10), anchor="e")

        photo_holder = self._build_photo_picker(scroll, "الصورة الشخصية")
        national_id_photo_holder = self._build_photo_picker(scroll, "صورة الرقم القومي")

        specialty_entry = None
        if role == "doctor":
            ctk.CTkLabel(scroll, text="التخصص", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
            specialty_entry = RTLEntry(scroll, width=280, height=38)
            specialty_entry.pack(padx=30, pady=(2, 10), anchor="e")

        get_selected_days = self._build_workdays_picker(scroll)

        ctk.CTkFrame(scroll, fg_color=theme.BORDER, height=1).pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(scroll, text="البيانات المالية", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e", padx=30, pady=(0, 6))

        ctk.CTkLabel(scroll, text="المرتب الثابت (الأساسي)", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        salary_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        salary_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="نسبة الطبيب/العامل من الدخل %", font=theme.FONT_NORMAL).pack(
            anchor="e", padx=30)
        income_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        income_entry.pack(padx=30, pady=(2, 10), anchor="e")

        get_start_date = self._build_date_entry(scroll, "تاريخ بدء العمل")

        ctk.CTkLabel(scroll, text="نسبة الزيادة السنوية % (على المرتب الثابت)",
                     font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        raise_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        raise_entry.pack(padx=30, pady=(2, 16), anchor="e")

        ctk.CTkFrame(scroll, fg_color=theme.BORDER, height=1).pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(scroll, text="اسم المستخدم (بالإنجليزي - لتسجيل الدخول)",
                     font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        username_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right",
                                       font=theme.FONT_NORMAL)
        username_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="كلمة المرور", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        password_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right",
                                       font=theme.FONT_NORMAL)
        password_entry.pack(padx=30, pady=(2, 16), anchor="e")

        error_label = ctk.CTkLabel(scroll, text="", font=theme.FONT_SMALL, text_color=theme.DANGER)
        error_label.pack()

        def save():
            full_name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if not (full_name and username and password):
                error_label.configure(text="لازم تملأ كل الحقول")
                return
            try:
                salary = float(salary_entry.get().strip() or 0)
                income_percent = float(income_entry.get().strip() or 0)
                raise_percent = float(raise_entry.get().strip() or 0)
            except ValueError:
                error_label.configure(text="⚠ تأكد إن المرتب/النسب أرقام صحيحة")
                return

            try:
                new_id = db.add_user(username, password, full_name, role,
                                      phone=phone_entry.get().strip(),
                                      specialty=specialty_entry.get().strip() if specialty_entry else "",
                                      work_days=get_selected_days())
            except Exception:
                error_label.configure(text="اسم المستخدم هذا مستخدَم من قبل")
                return

            photo_path = photo_holder["value"]
            if photo_path:
                photo_path = _save_uploaded_file(photo_path, "photo")
            id_photo_path = national_id_photo_holder["value"]
            if id_photo_path:
                id_photo_path = _save_uploaded_file(id_photo_path, "national_id")

            db.update_user(
                new_id,
                birth_date=get_birth_date(),
                address=address_entry.get().strip(),
                national_id=national_id_entry.get().strip(),
                photo_path=photo_path,
                national_id_photo_path=id_photo_path,
                salary=salary,
                income_percent=income_percent,
                start_date=get_start_date(),
                annual_raise_percent=raise_percent,
            )

            dialog.destroy()
            self.refresh()
            theme.show_toast(self, f"تم إضافة {role_title}")

        ctk.CTkButton(scroll, text=f"✔ إضافة {role_title}", height=44, fg_color=theme.SUCCESS,
                      command=save).pack(padx=30, pady=10, fill="x")

    # ---------------- إضافة مساعد طبيب / خدمات مساعدة (من غير حساب دخول) ----------------

    def _open_add_support_dialog(self, staff_type):
        titles = {"assistant": "مساعد طبيب", "support": "خدمات مساعدة"}
        title = titles.get(staff_type, staff_type)

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"إضافة {title}")
        dialog.geometry("420x900")
        dialog.grab_set()

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text=f"إضافة {title} جديد", font=theme.FONT_SUBTITLE).pack(pady=(16, 14))

        ctk.CTkLabel(scroll, text="الاسم بالكامل", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        name_entry = RTLEntry(scroll, width=280, height=38)
        name_entry.pack(padx=30, pady=(2, 10), anchor="e")

        get_birth_date = self._build_date_entry(scroll, "تاريخ الميلاد")

        ctk.CTkLabel(scroll, text="محل الإقامة / العنوان", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        address_entry = RTLEntry(scroll, width=280, height=38)
        address_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="أرقام التليفونات", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        phone_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        phone_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="الرقم القومي", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        national_id_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right",
                                          font=theme.FONT_NORMAL)
        national_id_entry.pack(padx=30, pady=(2, 10), anchor="e")

        photo_holder = self._build_photo_picker(scroll, "الصورة الشخصية")
        national_id_photo_holder = self._build_photo_picker(scroll, "صورة الرقم القومي")

        specialty_entry = None
        if staff_type == "assistant":
            ctk.CTkLabel(scroll, text="التخصص/المهمة", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
            specialty_entry = RTLEntry(scroll, width=280, height=38)
            specialty_entry.pack(padx=30, pady=(2, 10), anchor="e")

        get_selected_days = self._build_workdays_picker(scroll)

        ctk.CTkFrame(scroll, fg_color=theme.BORDER, height=1).pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(scroll, text="البيانات المالية", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e", padx=30, pady=(0, 6))

        ctk.CTkLabel(scroll, text="المرتب الثابت (الأساسي)", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        salary_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        salary_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="نسبة من الدخل %", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        income_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        income_entry.pack(padx=30, pady=(2, 10), anchor="e")

        get_start_date = self._build_date_entry(scroll, "تاريخ بدء العمل")

        ctk.CTkLabel(scroll, text="نسبة الزيادة السنوية % (على المرتب الثابت)",
                     font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        raise_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        raise_entry.pack(padx=30, pady=(2, 16), anchor="e")

        ctk.CTkFrame(scroll, fg_color=theme.BORDER, height=1).pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(scroll, text="ملاحظات", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        notes_box = ctk.CTkTextbox(scroll, width=280, height=60, font=theme.FONT_NORMAL)
        notes_box.pack(padx=30, pady=(2, 16), anchor="e")

        error_label = ctk.CTkLabel(scroll, text="", font=theme.FONT_SMALL, text_color=theme.DANGER)
        error_label.pack()

        def save():
            full_name = name_entry.get().strip()
            if not full_name:
                error_label.configure(text="لازم تكتب الاسم")
                return
            try:
                salary = float(salary_entry.get().strip() or 0)
                income_percent = float(income_entry.get().strip() or 0)
                raise_percent = float(raise_entry.get().strip() or 0)
            except ValueError:
                error_label.configure(text="⚠ تأكد إن المرتب/النسب أرقام صحيحة")
                return

            new_id = db.add_support_staff(
                staff_type=staff_type,
                full_name=full_name,
                phone=phone_entry.get().strip(),
                notes=notes_box.get("1.0", "end").strip(),
                specialty=specialty_entry.get().strip() if specialty_entry else "",
                work_days=get_selected_days(),
            )

            photo_path = photo_holder["value"]
            if photo_path:
                photo_path = _save_uploaded_file(photo_path, "photo")
            id_photo_path = national_id_photo_holder["value"]
            if id_photo_path:
                id_photo_path = _save_uploaded_file(id_photo_path, "national_id")

            db.update_support_staff(
                new_id,
                birth_date=get_birth_date(),
                address=address_entry.get().strip(),
                national_id=national_id_entry.get().strip(),
                photo_path=photo_path,
                national_id_photo_path=id_photo_path,
                salary=salary,
                income_percent=income_percent,
                start_date=get_start_date(),
                annual_raise_percent=raise_percent,
            )

            dialog.destroy()
            self.refresh()
            theme.show_toast(self, f"تم إضافة {title}")

        ctk.CTkButton(scroll, text=f"✔ إضافة {title}", height=44, fg_color=theme.SUCCESS,
                      command=save).pack(padx=30, pady=10, fill="x")

    # ---------------- تعديل بيانات عامل موجود (شخصية + مالية) - مدير بس ----------------

    def _open_edit_dialog(self, row, kind):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"تعديل بيانات: {row['full_name']}")
        dialog.geometry("420x820")
        dialog.grab_set()

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text=f"تعديل بيانات {row['full_name']}", font=theme.FONT_SUBTITLE).pack(
            pady=(16, 14))

        get_birth_date = self._build_date_entry(scroll, "تاريخ الميلاد", row.get("birth_date"))

        ctk.CTkLabel(scroll, text="محل الإقامة / العنوان", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        address_entry = RTLEntry(scroll, width=280, height=38)
        if row.get("address"):
            address_entry.insert(0, row["address"])
        address_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="أرقام التليفونات", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        phone_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        if row.get("phone"):
            phone_entry.insert(0, row["phone"])
        phone_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="الرقم القومي", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        national_id_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right",
                                          font=theme.FONT_NORMAL)
        if row.get("national_id"):
            national_id_entry.insert(0, row["national_id"])
        national_id_entry.pack(padx=30, pady=(2, 10), anchor="e")

        photo_holder = self._build_photo_picker(scroll, "الصورة الشخصية", row.get("photo_path"))
        national_id_photo_holder = self._build_photo_picker(
            scroll, "صورة الرقم القومي", row.get("national_id_photo_path"))

        get_selected_days = self._build_workdays_picker(scroll, row.get("work_days"))

        ctk.CTkFrame(scroll, fg_color=theme.BORDER, height=1).pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(scroll, text="البيانات المالية (سرّية - يطّلع عليها المدير فقط)",
                     font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED).pack(anchor="e", padx=30, pady=(0, 6))

        ctk.CTkLabel(scroll, text="المرتب الثابت (الأساسي)", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        salary_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        if row.get("salary"):
            salary_entry.insert(0, f"{row['salary']:g}")
        salary_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(scroll, text="نسبة الطبيب/العامل من الدخل %", font=theme.FONT_NORMAL).pack(
            anchor="e", padx=30)
        income_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        if row.get("income_percent"):
            income_entry.insert(0, f"{row['income_percent']:g}")
        income_entry.pack(padx=30, pady=(2, 10), anchor="e")

        get_start_date = self._build_date_entry(scroll, "تاريخ بدء العمل", row.get("start_date"))

        ctk.CTkLabel(scroll, text="نسبة الزيادة السنوية % (على المرتب الثابت)",
                     font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        raise_entry = ctk.CTkEntry(scroll, width=280, height=38, justify="right", font=theme.FONT_NORMAL)
        if row.get("annual_raise_percent"):
            raise_entry.insert(0, f"{row['annual_raise_percent']:g}")
        raise_entry.pack(padx=30, pady=(2, 16), anchor="e")

        error_label = ctk.CTkLabel(scroll, text="", font=theme.FONT_SMALL, text_color=theme.DANGER)
        error_label.pack()

        def save():
            try:
                salary = float(salary_entry.get().strip() or 0)
                income_percent = float(income_entry.get().strip() or 0)
                raise_percent = float(raise_entry.get().strip() or 0)
            except ValueError:
                error_label.configure(text="⚠ تأكد إن المرتب/النسب أرقام صحيحة")
                return

            photo_path = photo_holder["value"]
            if photo_path and not photo_path.startswith(STAFF_FILES_DIR):
                photo_path = _save_uploaded_file(photo_path, "photo")
            id_photo_path = national_id_photo_holder["value"]
            if id_photo_path and not id_photo_path.startswith(STAFF_FILES_DIR):
                id_photo_path = _save_uploaded_file(id_photo_path, "national_id")

            fields = dict(
                birth_date=get_birth_date(),
                address=address_entry.get().strip(),
                phone=phone_entry.get().strip(),
                national_id=national_id_entry.get().strip(),
                photo_path=photo_path,
                national_id_photo_path=id_photo_path,
                work_days=get_selected_days(),
                salary=salary,
                income_percent=income_percent,
                start_date=get_start_date(),
                annual_raise_percent=raise_percent,
            )
            if kind == "user":
                db.update_user(row["id"], **fields)
            else:
                db.update_support_staff(row["id"], **fields)

            dialog.destroy()
            self.refresh()
            theme.show_toast(self, "تم حفظ التعديلات")

        ctk.CTkButton(scroll, text="✔ حفظ التعديلات", height=44, fg_color=theme.SUCCESS,
                      command=save).pack(padx=30, pady=10, fill="x")
