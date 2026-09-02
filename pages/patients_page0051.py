# -*- coding: utf-8 -*-
"""
صفحة المرضى: قائمة + بحث + إضافة + تفاصيل المريض (بيانات + مخطط الأسنان)
"""

import os
import shutil
import tkinter as tk
from datetime import datetime, date
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

import theme
import database as db
from pages.tooth_chart_widget import ToothChart
from pages.rtl_entry import RTLEntry
from pages.date_auto_entry import DateAutoEntry
from pages.draggable_field import DraggableCell
from pages.patient_files_widget import PatientFilesStrip, open_with_default_app
from pages.treatment_records_table import TreatmentRecordsTable
from pages.visits_table import PatientVisitsTable
from pages import pdf_report

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
PROFILE_PHOTOS_DIR = os.path.join(ASSETS_DIR, "profile_photos")


class _Tooltip:
    """تلميح صغير بيظهر عند عمل hover على أي widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        # add="+" عشان الحدث ده ميلغيش أي ربط تاني موجود على نفس الودجت
        # (زي تأثير الـ hover بتاع أزرار الأيقونات الزجاجية)
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2 - 30
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg="#1B1E23", fg="#FFFFFF",
                 font=(theme.CONTENT_FONT_FAMILY, 10), padx=8, pady=4,
                 borderwidth=0).pack()

    def _hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class PatientsPage(ctk.CTkFrame):
    def __init__(self, master, current_user=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_user = current_user
        self.selected_patient_id = None
        self.list_container = None
        self.detail_container = None
        self._build_layout()
        self.show_list()

    def _build_layout(self):
        self.list_container = ctk.CTkFrame(self, fg_color="transparent")
        self.detail_container = ctk.CTkFrame(self, fg_color="transparent")

    # ---------------- قائمة المرضى ----------------

    def show_list(self):
        self.detail_container.pack_forget()
        self.list_container.pack(fill="both", expand=True)
        for widget in self.list_container.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(self.list_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(header, text="المرضى", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")

        add_btn = ctk.CTkButton(header, text="+ إضافة مريض جديد", width=170, height=38,
                                 fg_color=theme.HEADER_GRAD_END, hover_color=theme.HEADER_GRAD_START,
                                 text_color="#FFFFFF", border_width=0,
                                 command=self.show_add_form)
        add_btn.pack(side="left")

        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(header, textvariable=self.search_var,
                                     placeholder_text="ابحث بالاسم - الوظيفة - التليفون - العنوان...",
                                     width=320, height=38, justify="right")
        search_entry.pack(side="left", padx=10)
        search_entry.bind("<KeyRelease>", lambda e: self._refresh_table())

        self.table_frame = ctk.CTkScrollableFrame(self.list_container, fg_color=theme.CARD_BG,
                                                    corner_radius=12)
        self.table_frame.pack(fill="both", expand=True)

        self._refresh_table()

    # ترتيب الأعمدة من اليمين لليسار (زي القراءة العربية الطبيعية).
    # في الـ grid، العمود صاحب أعلى رقم index بيبقى أقصى اليمين، فبنعكس
    # هذا الترتيب حتى يظهر "رقم الملف" فعليًا كأول عمود من اليمين.
    TABLE_COLUMNS = [
        ("العنوان", 220, "address"),
        ("السن", 60, "age"),
        ("تاريخ الميلاد", 110, "birth_date"),
        ("التليفون", 130, "phone"),
        ("النوع", 70, "gender"),
        ("الاسم", 220, "full_name"),
        ("رقم الملف", 90, "id"),
    ]

    HEADER_BG = "#1B1E23"
    HEADER_TEXT = "#FFFFFF"
    ROW_BG_A = "#FFFFFF"
    ROW_BG_B = "#EEF1F6"
    GRID_LINE = "#C7CCD6"

    @staticmethod
    def _calc_age(birth_date_str):
        if not birth_date_str:
            return "-"
        try:
            y, m, d = map(int, birth_date_str.split("-"))
            born = date(y, m, d)
            today = date.today()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            return str(age) if age >= 0 else "-"
        except Exception:
            return "-"

    def _refresh_table(self):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        patients = db.get_all_patients(self.search_var.get() if hasattr(self, "search_var") else "")

        if not patients:
            ctk.CTkLabel(self.table_frame, text="لا يوجد مرضى مسجلين بعد",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED).pack(pady=30)
            return

        # جدول شبكي حقيقي (grid) بدلًا من صفوف pack منفصلة - بهذا الشكل تنضبط عناوين
        # الأعمدة وبيانات كل صف فوق بعضها تمامًا، ولا يوجد أي احتمال "لانزياح"
        # لأن العمود الواحد يأخذ نفس العرض تمامًا في كل الصفوف والترويسة.
        # عمود المساحة الفارغة (الذي يأخذ أي عرض زائد) يجب أن يكون index=0
        # (أقصى اليسار)، حتى تظل بيانات الجدول ملتصقة بأقصى اليمين
        # بدلًا من الانزلاق نحو المنتصف/اليسار.
        grid = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        n = len(self.TABLE_COLUMNS)
        grid.grid_columnconfigure(0, weight=1)  # المساحة الفاضية أقصى الشمال
        for i, (_, width, _) in enumerate(self.TABLE_COLUMNS):
            grid.grid_columnconfigure(i + 1, minsize=width, weight=0)

        # هيدر الأعمدة
        ctk.CTkLabel(grid, text="", fg_color=self.HEADER_BG, corner_radius=0,
                     border_width=1, border_color=self.GRID_LINE, height=34).grid(
            row=0, column=0, sticky="nsew")
        for i, (label_text, width, _) in enumerate(self.TABLE_COLUMNS):
            header_cell = ctk.CTkLabel(
                grid, text=label_text, font=theme.FONT_SUBTITLE,
                text_color=self.HEADER_TEXT, fg_color=self.HEADER_BG,
                corner_radius=0, border_width=1, border_color=self.GRID_LINE,
                anchor="e", padx=10, height=34)
            header_cell.grid(row=0, column=i + 1, sticky="nsew")

        # صفوف البيانات - ألوان متبادلة (Zebra) لتباين واضح وسهولة قراءة،
        # ومن دون هوامش رأسية داخلية زائدة حتى يظهر أكبر عدد ممكن من الصفوف
        for row_idx, p in enumerate(patients, start=1):
            row_bg = self.ROW_BG_A if row_idx % 2 == 1 else self.ROW_BG_B
            values = {
                "id": f"{p['id']:06d}",
                "birth_date": p["birth_date"] or "-",
                "age": self._calc_age(p["birth_date"]),
                "gender": p["gender"] or "-",
                "phone": p["phone"] or "-",
                "full_name": p["full_name"],
                "address": p["address"] or "-",
            }
            # خانة فاضية بنفس لون الصف أقصى الشمال
            filler = ctk.CTkLabel(grid, text="", fg_color=row_bg, corner_radius=0,
                                   border_width=1, border_color=self.GRID_LINE, height=28)
            filler.grid(row=row_idx, column=0, sticky="nsew")
            filler.bind("<Button-1>", lambda e, pid=p["id"]: self.show_detail(pid))

            for i, (_, width, key) in enumerate(self.TABLE_COLUMNS):
                cell = ctk.CTkLabel(
                    grid, text=values[key], font=theme.FONT_NORMAL,
                    text_color=theme.TEXT_DARK, fg_color=row_bg,
                    corner_radius=0, border_width=1, border_color=self.GRID_LINE,
                    anchor="e", padx=10, height=28, cursor="hand2")
                cell.grid(row=row_idx, column=i + 1, sticky="nsew")
                cell.bind("<Button-1>", lambda e, pid=p["id"]: self.show_detail(pid))

    # ---------------- إضافة مريض ----------------

    def _make_age_birth_fields(self, parent, initial_birth_iso=None):
        """تُعيد (row_frame, birth_entry, age_entry) - الحقلان مرتبطان ببعضهما تلقائيًا:
        تغيير أي منهما يُحدِّث الآخر بناءً على تاريخ اليوم الفعلي"""
        row = ctk.CTkFrame(parent, fg_color="transparent")

        age_entry = ctk.CTkEntry(row, width=70, height=42, justify="center", font=theme.FONT_NORMAL)
        birth_entry = DateAutoEntry(row, width=160, height=42, font=theme.FONT_NORMAL)

        def sync_age_from_birth():
            iso = birth_entry.get_iso_date()
            if not iso:
                return
            try:
                y, m, d = map(int, iso.split("-"))
                born = date(y, m, d)
                today = date.today()
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                if age >= 0:
                    current = age_entry.get().strip()
                    if current != str(age):
                        age_entry.delete(0, "end")
                        age_entry.insert(0, str(age))
            except Exception:
                pass

        def sync_birth_from_age(event=None):
            val = age_entry.get().strip()
            if not val.isdigit():
                return
            age = int(val)
            today = date.today()
            try:
                born = date(today.year - age, today.month, today.day)
            except ValueError:
                born = date(today.year - age, today.month, 1)
            birth_entry.set_iso_date(born.isoformat())

        birth_entry.on_change = sync_age_from_birth
        age_entry.bind("<KeyRelease>", sync_birth_from_age)

        if initial_birth_iso:
            birth_entry.set_iso_date(initial_birth_iso)
            sync_age_from_birth()

        ctk.CTkLabel(row, text="سنة", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(side="right", padx=(0, 4))
        age_entry.pack(side="right", padx=(4, 14))
        birth_entry.pack(side="right", padx=(4, 4))
        ctk.CTkLabel(row, text="السن", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(side="right", padx=(14, 4))

        return row, birth_entry, age_entry

    def show_add_form(self):
        self.list_container.pack_forget()
        self.detail_container.pack(fill="both", expand=True)
        for widget in self.detail_container.winfo_children():
            widget.destroy()

        ctk.CTkButton(self.detail_container, text="← رجوع للقائمة", width=140, height=38,
                      fg_color=theme.HEADER_GRAD_END, hover_color=theme.HEADER_GRAD_START,
                      text_color="#FFFFFF", border_width=0,
                      command=self.show_list).pack(anchor="w", pady=(0, 10))

        def save(fields):
            name = fields["full_name"].get().strip()
            if not name:
                return
            db.add_patient(
                full_name=name,
                phone=fields["phone"].get().strip(),
                birth_date=fields["birth_date"].get_iso_date(),
                gender=fields["gender"].get().strip(),
                address=fields["address"].get().strip(),
                allergies=fields["allergies"].get().strip(),
                occupation=fields["occupation"].get().strip(),
                nationality=fields["nationality"].get().strip(),
                family_id=fields["family_id"].get().strip(),
                medical_notes=fields["_notes"].get("1.0", "end").strip(),
            )
            self.show_list()

        self._build_patient_form(self.detail_container, title="إضافة مريض جديد",
                                  patient=None, save_label="حفظ المريض", on_save=save)

    # ---------------- ملف المريض ----------------
    # ملحوظة: صفحة "تعديل البيانات" المنفصلة اتشالت خالص - التعديل بقى
    # مباشرة جوه تاب "البيانات" نفسه (_render_info_tab بوضع edit_mode=True)،
    # وكمان صورة المريض بقت قابلة للتعديل من خانتها في نفس التاب مباشرة
    # (_build_info_photo_cell) - مفيش زرار "تعديل" منفصل في صف الأيقونات تاني.

    def _build_patient_form(self, container, title, patient, save_label, on_save):
        """
        نموذج واحد مشترك تستخدمه كل من "إضافة مريض جديد" و"تعديل بيانات مريض"،
        حتى يظل الاثنان نسخة واحدة دائمًا بدلًا من تكرار الكود نفسه في مكانين.
        patient=None يعني نموذج إضافة فارغ، وأي dict آخر يعني نموذج تعديل معبَّأ بالبيانات الحالية.
        """
        fields = {}

        # زرار الحفظ في فوتر ثابت تحت الشاشة - صغير الحجم وبإطار وظل واضح
        # (مش ممدود على طول العرض زي الأزرار التانية)
        footer = ctk.CTkFrame(container, fg_color="transparent")
        footer.pack(side="bottom", fill="x", pady=(10, 4))
        save_btn_wrapper = theme.make_shadowed_button(
            footer, f"✔ {save_label}", command=lambda: on_save(fields),
            width=170, height=42, font=theme.FONT_SUBTITLE)
        save_btn_wrapper.pack(anchor="e", padx=4)

        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        form_card = ctk.CTkFrame(scroll, fg_color=theme.CARD_BG, corner_radius=12)
        form_card.pack(fill="x", pady=6)

        ctk.CTkLabel(form_card, text=title, font=theme.FONT_SUBTITLE).pack(pady=(16, 10))

        def field_title(parent, text, small=False):
            ctk.CTkLabel(parent, text=text,
                         font=theme.FONT_SMALL if small else
                         (theme.FONT_FAMILY, theme.CONTENT_FONT_SIZE, "bold"),
                         text_color=theme.INPUT_LABEL_COLOR, anchor="e").pack(fill="x", padx=6)

        # ---- منطقة الحقول الصغيرة: قابلة للسحب وتغيير المقاس بحرية ----
        LAYOUT_KEY = "patient_form_fields"
        DEFAULT_LAYOUT = {
            "full_name":   {"x": 470, "y": 4,  "w": 190, "h": 60},
            "gender":      {"x": 380, "y": 4,  "w": 82,  "h": 60},
            "phone":       {"x": 246, "y": 4,  "w": 126, "h": 60},
            "occupation":  {"x": 116, "y": 4,  "w": 122, "h": 60},
            "nationality": {"x": 0,   "y": 4,  "w": 108, "h": 60},
            "birth_date":  {"x": 320, "y": 76, "w": 210, "h": 60},
            "family_id":   {"x": 60,  "y": 76, "w": 250, "h": 60},
        }
        saved_layout = db.get_ui_layout(LAYOUT_KEY) or {}
        layout = {**DEFAULT_LAYOUT, **saved_layout}

        edit_mode_state = {"on": False}
        cells = {}

        toolbar = ctk.CTkFrame(form_card, fg_color="transparent")
        toolbar.pack(fill="x", padx=22, pady=(0, 4))

        def on_cell_change(field_key, x, y, w, h):
            layout[field_key] = {"x": x, "y": y, "w": w, "h": h}

        canvas_area = ctk.CTkFrame(form_card, fg_color=theme.BG_MAIN, corner_radius=8, height=150)
        canvas_area.pack(fill="x", padx=22, pady=(0, 10))
        canvas_area.pack_propagate(False)

        def make_cell(field_key):
            d = layout[field_key]
            cell = DraggableCell(canvas_area, field_key, d["x"], d["y"], d["w"], d["h"],
                                  edit_mode_getter=lambda: edit_mode_state["on"],
                                  on_change=on_cell_change)
            cells[field_key] = cell
            return cell

        def toggle_edit_mode():
            edit_mode_state["on"] = not edit_mode_state["on"]
            edit_toggle_btn.configure(
                text=("🔓 وضع التعديل مفعَّل (اسحب أي حقل أو كبِّره من زاويته)"
                      if edit_mode_state["on"] else "✎ تعديل شكل الحقول"),
                fg_color=theme.SUCCESS if edit_mode_state["on"] else theme.CARD_BG,
                text_color="#FFFFFF" if edit_mode_state["on"] else theme.TEXT_DARK)
            for c in cells.values():
                c._refresh_edit_look()

        def save_layout():
            db.save_ui_layout(LAYOUT_KEY, layout)
            save_layout_btn.configure(text="✔ اتحفظ الشكل")
            save_layout_btn.after(1400, lambda: save_layout_btn.configure(text="💾 حفظ الشكل"))

        def reset_layout():
            db.reset_ui_layout(LAYOUT_KEY)
            for key, cell in cells.items():
                d = DEFAULT_LAYOUT[key]
                cell.place(x=d["x"], y=d["y"])
                cell.configure(width=d["w"], height=d["h"])
                layout[key] = dict(d)

        edit_toggle_btn = ctk.CTkButton(toolbar, text="✎ تعديل شكل الحقول", width=190, height=32,
                                         font=theme.FONT_SMALL, fg_color=theme.CARD_BG,
                                         text_color=theme.TEXT_DARK, border_width=1,
                                         border_color=theme.BORDER, command=toggle_edit_mode)
        edit_toggle_btn.pack(side="right", padx=4)
        save_layout_btn = ctk.CTkButton(toolbar, text="💾 حفظ الشكل", width=120, height=32,
                                         font=theme.FONT_SMALL, fg_color=theme.PRIMARY_LIGHT,
                                         command=save_layout)
        save_layout_btn.pack(side="right", padx=4)
        ctk.CTkButton(toolbar, text="↺ افتراضي", width=90, height=32, font=theme.FONT_SMALL,
                      fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK, border_width=1,
                      border_color=theme.BORDER, command=reset_layout).pack(side="right", padx=4)
        ctk.CTkLabel(toolbar, text="اسحب أي حقل من مكانه، وكبّره/صغّره من ◢ في زاويته",
                     font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(side="left")

        # الاسم بالكامل
        cell = make_cell("full_name")
        field_title(cell, "الاسم بالكامل *", small=True)
        name_entry = RTLEntry(cell, height=32)
        theme.apply_sunken_style(name_entry)
        if patient and patient.get("full_name"):
            name_entry.insert(0, patient["full_name"])
        name_entry.pack(fill="x", padx=6, pady=(2, 4))
        fields["full_name"] = name_entry

        # النوع
        cell = make_cell("gender")
        field_title(cell, "النوع", small=True)
        gender_menu = ctk.CTkOptionMenu(cell, values=["ذكر", "أنثى"], height=32,
                                         font=theme.FONT_SMALL,
                                         fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                                         button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9))
        gender_menu.set((patient.get("gender") if patient else None) or "ذكر")
        gender_menu.pack(fill="x", padx=6, pady=(2, 4))
        fields["gender"] = gender_menu

        # الوظيفة
        cell = make_cell("occupation")
        field_title(cell, "الوظيفة", small=True)
        occupation_entry = RTLEntry(cell, height=32)
        theme.apply_sunken_style(occupation_entry)
        if patient and patient.get("occupation"):
            occupation_entry.insert(0, patient["occupation"])
        occupation_entry.pack(fill="x", padx=6, pady=(2, 4))
        fields["occupation"] = occupation_entry

        # الجنسية
        cell = make_cell("nationality")
        field_title(cell, "الجنسية", small=True)
        nationality_entry = RTLEntry(cell, height=32)
        theme.apply_sunken_style(nationality_entry)
        if patient and patient.get("nationality"):
            nationality_entry.insert(0, patient["nationality"])
        nationality_entry.pack(fill="x", padx=6, pady=(2, 4))
        fields["nationality"] = nationality_entry

        # رقم التليفون + زرار أرقام إضافية (واتساب وغيره)
        cell = make_cell("phone")
        phone_title_row = ctk.CTkFrame(cell, fg_color="transparent")
        phone_title_row.pack(fill="x", padx=6)
        ctk.CTkLabel(phone_title_row, text="تليفون", font=theme.FONT_SMALL,
                     text_color=theme.INPUT_LABEL_COLOR, anchor="e").pack(side="right")
        if patient:
            extra_count = len(db.get_patient_phones(patient["id"]))
            phones_btn = ctk.CTkButton(
                phone_title_row, text=f"📱+{extra_count}" if extra_count else "📱+", width=36, height=20,
                font=(theme.FONT_FAMILY, 10), fg_color="transparent", text_color=theme.ACCENT_BORDER,
                hover_color=theme.BG_MAIN,
                command=lambda: self._open_manage_phones_dialog(patient["id"]))
            phones_btn.pack(side="left")
        phone_entry = ctk.CTkEntry(cell, height=32, justify="right", font=theme.FONT_NORMAL)
        theme.apply_sunken_style(phone_entry)
        if patient and patient.get("phone"):
            phone_entry.insert(0, patient["phone"])
        phone_entry.pack(fill="x", padx=6, pady=(2, 4))
        fields["phone"] = phone_entry

        # تاريخ الميلاد + السن (مربوطين ببعض تلقائيًا) - خلية واحدة
        cell = make_cell("birth_date")
        field_title(cell, "تاريخ الميلاد / السن", small=True)
        age_birth_row, birth_entry, age_entry = self._make_age_birth_fields(
            cell, initial_birth_iso=(patient.get("birth_date") if patient else None))
        theme.apply_sunken_style(birth_entry)
        theme.apply_sunken_style(age_entry)
        age_birth_row.pack(fill="x", padx=6, pady=(2, 4))
        fields["birth_date"] = birth_entry

        # رقم/كود الأسرة
        cell = make_cell("family_id")
        field_title(cell, "رقم/كود الأسرة (اختياري)", small=True)
        family_entry = ctk.CTkEntry(cell, height=32, justify="right",
                                     font=theme.FONT_SMALL, placeholder_text="مثال: FAM-001")
        theme.apply_sunken_style(family_entry)
        if patient and patient.get("family_id"):
            family_entry.insert(0, patient["family_id"])
        family_entry.pack(fill="x", padx=6, pady=(2, 4))
        fields["family_id"] = family_entry

        if not patient:
            existing_families = db.get_all_family_ids()
            if existing_families:
                ctk.CTkLabel(form_card, text="عائلات موجودة بالفعل: " + "، ".join(existing_families),
                             font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                             wraplength=500, justify="right").pack(anchor="e", padx=30, pady=(0, 6))
            ctk.CTkLabel(form_card, text="💡 تقدر تضيف أرقام تليفونات إضافية (منها واتساب) بعد ما تحفظ المريض",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(anchor="e", padx=30, pady=(0, 6))

        # ---- الحقول الطويلة (سطر عريض لكل واحد) ----
        long_wrap = ctk.CTkFrame(form_card, fg_color="transparent")
        long_wrap.pack(fill="x", padx=22, pady=(6, 6))

        long_field_defs = [
            ("address", "العنوان"),
            ("allergies", "حساسية من أدوية"),
        ]
        for key, label in long_field_defs:
            field_title(long_wrap, label)
            entry = RTLEntry(long_wrap, height=42)
            theme.apply_sunken_style(entry)
            if patient and patient.get(key):
                entry.insert(0, patient[key])
            entry.pack(fill="x", pady=(4, 12))
            fields[key] = entry

        # ملاحظات طبية
        field_title(long_wrap, "ملاحظات طبية")
        notes_box = ctk.CTkTextbox(long_wrap, height=70, font=theme.FONT_NORMAL)
        theme.apply_sunken_style(notes_box)
        if patient and patient.get("medical_notes"):
            notes_box.insert("1.0", patient["medical_notes"])
        notes_box.pack(fill="x", pady=(4, 18))
        fields["_notes"] = notes_box

        return fields

    # ---------------- أرقام تليفونات إضافية (منها واتساب) ----------------

    def _open_manage_phones_dialog(self, patient_id, on_close=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title("أرقام تليفونات إضافية")
        dialog.geometry("380x460")
        dialog.grab_set()
        if on_close:
            dialog.protocol("WM_DELETE_WINDOW", lambda: (dialog.destroy(), on_close()))

        ctk.CTkLabel(dialog, text="أرقام تليفونات إضافية", font=theme.FONT_SUBTITLE).pack(pady=(16, 4))
        ctk.CTkLabel(dialog, text="حدِّد أي رقم كـ«واتساب» ليُستخدم لاحقًا عند ربط البرنامج بواتساب",
                     font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                     wraplength=320, justify="center").pack(pady=(0, 10))

        list_frame = ctk.CTkScrollableFrame(dialog, fg_color=theme.BG_MAIN, corner_radius=8)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        def refresh_list():
            for w in list_frame.winfo_children():
                w.destroy()
            phones = db.get_patient_phones(patient_id)
            if not phones:
                ctk.CTkLabel(list_frame, text="لا توجد أرقام إضافية مسجَّلة بعد",
                             font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(pady=20)
            for p in phones:
                row = ctk.CTkFrame(list_frame, fg_color=theme.CARD_BG, corner_radius=8)
                row.pack(fill="x", pady=4, padx=4)
                ctk.CTkButton(row, text="✕", width=26, height=26, fg_color=theme.DANGER,
                              font=theme.FONT_SMALL,
                              command=lambda pid=p["id"]: (db.delete_patient_phone(pid), refresh_list())
                              ).pack(side="left", padx=6, pady=6)
                if p["is_whatsapp"]:
                    ctk.CTkLabel(row, text="💬 واتساب", font=theme.FONT_SMALL, text_color="#FFFFFF",
                                 fg_color="#25D366", corner_radius=6, width=70, height=24).pack(
                        side="right", padx=6, pady=6)
                else:
                    ctk.CTkLabel(row, text=p["label"], font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                                 width=60).pack(side="right", padx=6, pady=6)
                ctk.CTkLabel(row, text=p["phone_number"], font=theme.FONT_NORMAL,
                             text_color=theme.TEXT_DARK).pack(side="right", padx=6, pady=6)

        refresh_list()

        add_row = ctk.CTkFrame(dialog, fg_color="transparent")
        add_row.pack(fill="x", padx=20, pady=(0, 10))
        number_entry = ctk.CTkEntry(add_row, height=38, justify="right",
                                     placeholder_text="رقم التليفون", font=theme.FONT_NORMAL)
        theme.apply_sunken_style(number_entry)
        number_entry.pack(fill="x", pady=(0, 6))

        options_row = ctk.CTkFrame(dialog, fg_color="transparent")
        options_row.pack(fill="x", padx=20, pady=(0, 6))
        label_menu = ctk.CTkOptionMenu(options_row, values=["منزل", "عمل", "ولي أمر", "آخر"], width=140,
                                        **theme.optionmenu_colors())
        label_menu.pack(side="right", padx=(6, 0))
        is_whatsapp_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_row, text="هذا رقم واتساب", variable=is_whatsapp_var,
                         font=theme.FONT_NORMAL, **theme.checkbox_colors()).pack(side="right", padx=10)

        def add_number():
            number = number_entry.get().strip()
            if not number:
                return
            db.add_patient_phone(patient_id, number, label=label_menu.get(),
                                  is_whatsapp=is_whatsapp_var.get())
            number_entry.delete(0, "end")
            is_whatsapp_var.set(False)
            refresh_list()

        ctk.CTkButton(dialog, text="+ إضافة الرقم", height=40, fg_color=theme.SUCCESS,
                      command=add_number).pack(padx=20, pady=(0, 8), fill="x")
        ctk.CTkButton(dialog, text="تم", height=36, fg_color="transparent", border_width=1,
                      border_color=theme.BORDER, text_color=theme.TEXT_DARK,
                      command=lambda: (dialog.destroy(), on_close() if on_close else None)
                      ).pack(padx=20, pady=(0, 16), fill="x")

    def show_detail(self, patient_id):
        self.selected_patient_id = patient_id
        patient = db.get_patient(patient_id)
        if not patient:
            self.show_list()
            return

        self.list_container.pack_forget()
        self.detail_container.pack(fill="both", expand=True)
        for widget in self.detail_container.winfo_children():
            widget.destroy()

        top_bar = ctk.CTkFrame(self.detail_container, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(top_bar, text="← رجوع للقائمة", width=140,
                      fg_color=theme.HEADER_GRAD_END, hover_color=theme.HEADER_GRAD_START,
                      text_color="#FFFFFF", border_width=0,
                      command=self.show_list).pack(side="left")

        # ترتيب الهيدر من أقصى يمين الصفحة: اسم المريض أولاً، وبعده الصورة،
        # وبعدها أيقونات التعديل/الخريطة/الحسابات...الخ (بترسم اسم المريض
        # والصورة الأول عشان ياخدوا أقصى يمين الصفحة فعلاً، وبعدين الأيقونات
        # بعدهم على الشمال شوية)
        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="right", padx=(0, 14))

        text_stack = ctk.CTkFrame(title_box, fg_color="transparent")
        text_stack.pack(side="right")
        ctk.CTkLabel(text_stack, text=f"ملف المريض: {patient['full_name']}", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e")
        ctk.CTkLabel(text_stack, text=f"رقم الملف: {patient_id:06d}", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e")

        # صورة المريض هنا للعرض بس (مجرد صورة صغيرة جنب الاسم) - زرار
        # تغيير/حذف الصورة اتنقل لصفحة "تعديل البيانات" بدل ما يكون هنا في
        # الهيدر، عشان الهيدر يفضل بسيط ومرتب
        self._header_photo_col = ctk.CTkFrame(title_box, fg_color="transparent")
        self._header_photo_col.pack(side="left", padx=(10, 0))
        self._build_header_photo(patient_id, patient, show_controls=False)

        # صف أيقونات موحَّد: بيانات - حسابات - أسنان - متابعات (زرار
        # "تعديل البيانات" اتشال خالص من هنا - التعديل بقى مباشرة جوه تاب
        # البيانات نفسه). الأزرار دي أصغر رأسيًا من غير هوامش داخلية زيادة
        # بين الرسمة وحدود الزرار، وبتاخد لون الثيم بتأثير زجاجي لامع
        # (GlassIconButton) بدل الشكل الرمادي البسيط القديم
        accounts_icon = self._accounts_tab_icon(patient_id, patient)
        icons_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        icons_row.pack(side="right", padx=(0, 14))

        # لون التمييز بياخد لون الثيم الحالي المطبّق فعليًا (اللي ممكن يكون
        # تفضيل شخصي للمستخدم الحالي لو مخصصه، مش بالضرورة لون العيادة
        # العام) - عشان يفضل متسق مع باقي شكل البرنامج المطبّق على الشاشة
        accent = theme.ACCENT_BORDER
        self._detail_icon_buttons = {}
        icon_specs = [
            ("records", "📋", "سجل المعالجات"),
            ("visits", "📅", "زيارات المتابعة"),
            ("teeth", "🦷", "خريطة الأسنان"),
            ("accounts", accounts_icon, "الحسابات"),
            ("info", "🧑", "البيانات الشخصية"),
        ]
        for key, icon_char, tip_text in icon_specs:
            btn = theme.GlassIconButton(
                icons_row, text=icon_char, width=48, height=34, accent_color=accent,
                canvas_bg=theme.BG_MAIN, active=False, font=(theme.FONT_FAMILY, 17),
                corner_radius=10, command=(lambda k=key: self._on_detail_icon_click(k, patient_id)))
            btn.pack(side="right", padx=4)
            _Tooltip(btn.canvas, tip_text)
            self._detail_icon_buttons[key] = btn

        body_row = ctk.CTkFrame(self.detail_container, fg_color="transparent")
        body_row.pack(fill="both", expand=True)

        # سايد بار صور الأشعة/الملفات - على الشمال، ثابت وظاهر مهما كان
        # التاب المفتوح، وله سكرول رأسي منفصل عن باقي الصفحة. العرض
        # الابتدائي هنا (279 = 321 بعد تصغيره 13%) هو مجرد نقطة بداية بس -
        # PatientFilesStrip دلوقتي بتراقب عرضها الحقيقي على الشاشة لحظة
        # بلحظة (بدل ما تعتمد على الرقم المكتوب هنا وبس) وتظبط عليه حجم
        # الصور والتفاف النص، عشان تتفادى مشكلة "بيتعرض أصغر من المكتوب
        # والكلام بيتقطع" اللي كانت بتحصل على بعض الأجهزة (زي شاشات اللاب
        # توب بنسبة تكبير مختلفة في إعدادات ويندوز)، حتى لو محاولة إصلاحها
        # السابقة عن طريق ctk.deactivate_automatic_dpi_awareness() في
        # main.py متفعّلة برضه.
        SIDEBAR_LAYOUT_KEY = "patient_files_sidebar_width"
        SIDEBAR_MIN_W, SIDEBAR_MAX_W = 180, 520
        saved_layout = db.get_ui_layout(SIDEBAR_LAYOUT_KEY) or {}
        saved_width = saved_layout.get("width", 279)
        saved_width = max(SIDEBAR_MIN_W, min(SIDEBAR_MAX_W, saved_width))

        files_sidebar = PatientFilesStrip(body_row, patient_id=patient_id, vertical=True,
                                           width=saved_width)
        files_sidebar.pack(side="left", fill="y")
        files_sidebar.pack_propagate(False)

        # مقبض سحب يدوي بين السايد بار وباقي الصفحة - بيسمح للمستخدم يوسّع
        # أو يصغّر عرض سايد بار الصور/الأشعة بالماوس، والعرض الجديد بيتحفظ
        # عشان يفضل زي ما هو المرة الجاية كمان
        resize_handle = tk.Frame(body_row, width=6, bg=theme.BORDER, cursor="sb_h_double_arrow")
        resize_handle.pack(side="left", fill="y", padx=(2, 8))

        def _on_handle_enter(_e):
            resize_handle.configure(bg=theme.ACCENT_BORDER)

        def _on_handle_leave(_e):
            resize_handle.configure(bg=theme.BORDER)

        def _on_drag_start(event):
            resize_handle._drag_start_x = event.x_root
            resize_handle._start_width = files_sidebar.winfo_width()

        def _on_drag_motion(event):
            dx = event.x_root - getattr(resize_handle, "_drag_start_x", event.x_root)
            new_width = getattr(resize_handle, "_start_width", saved_width) + dx
            new_width = max(SIDEBAR_MIN_W, min(SIDEBAR_MAX_W, new_width))
            files_sidebar.configure(width=new_width)

        def _on_drag_end(_event):
            db.save_ui_layout(SIDEBAR_LAYOUT_KEY, {"width": files_sidebar.winfo_width()})

        resize_handle.bind("<Enter>", _on_handle_enter)
        resize_handle.bind("<Leave>", _on_handle_leave)
        resize_handle.bind("<Button-1>", _on_drag_start)
        resize_handle.bind("<B1-Motion>", _on_drag_motion)
        resize_handle.bind("<ButtonRelease-1>", _on_drag_end)

        self._detail_content = ctk.CTkFrame(body_row, fg_color="transparent")
        self._detail_content.pack(side="right", fill="both", expand=True)

        self._active_detail_tab = "info"
        self._highlight_detail_icon("info")
        self._render_info_tab(patient_id, patient)

    def _on_detail_icon_click(self, key, patient_id):
        self._active_detail_tab = key
        self._highlight_detail_icon(key)
        for w in self._detail_content.winfo_children():
            w.destroy()
        if key == "info":
            self._render_info_tab(patient_id)
        elif key == "accounts":
            self._render_accounts_tab(patient_id)
        elif key == "teeth":
            self._render_teeth_tab(patient_id)
        elif key == "visits":
            self._render_visits_tab(patient_id)
        elif key == "records":
            self._render_records_tab(patient_id)

    def _highlight_detail_icon(self, active_key):
        for key, btn in self._detail_icon_buttons.items():
            btn.set_active(key == active_key)

    def _refresh_active_detail_tab(self, patient_id):
        """تعيد رسم التبويب المفتوح حاليًا فقط (تُستخدم بعد أي تعديل أو حذف)"""
        key = getattr(self, "_active_detail_tab", "info")
        for w in self._detail_content.winfo_children():
            w.destroy()
        if key == "info":
            self._render_info_tab(patient_id)
        elif key == "accounts":
            self._render_accounts_tab(patient_id)
        elif key == "teeth":
            self._render_teeth_tab(patient_id)
        elif key == "visits":
            self._render_visits_tab(patient_id)
        elif key == "records":
            self._render_records_tab(patient_id)

    def _accounts_tab_icon(self, patient_id, patient=None):
        patient = patient or db.get_patient(patient_id)
        balance = db.get_patient_balance(patient_id)
        discount_percent = (patient["discount_percent"] or 0) if patient else 0
        discount_amount = balance["total_charges"] * discount_percent / 100
        final_balance = (balance["total_charges"] - discount_amount) - balance["total_paid"]
        if final_balance == 0:
            return "💰🟢"
        elif final_balance < 0:
            return "💰🟡"
        else:
            return "💰🔴"

    # ---------------- تاب البيانات الشخصية ----------------

    def _render_info_tab(self, patient_id, patient=None, edit_mode=False):
        """تاب "البيانات الشخصية" - بيعرض البيانات للقراءة بس افتراضيًا، وفيه
        زرار "✎ تعديل البيانات" ظاهر من أول ما تفتحي التاب. الضغط عليه
        بيحوّل نفس الخانات (من غير ما تتغيّر أماكنها ولا مسمياتها) لحقول
        قابلة للكتابة مباشرة (edit_mode=True) بدل ما ينتقل لصفحة منفصلة.
        صورة المريض بقت خانة زي باقي البيانات، لكن ليها زرار تغيير/حذف
        منفصل خاص بيها بس (شغّال دايمًا بغض النظر عن edit_mode)"""
        parent = self._detail_content
        for w in parent.winfo_children():
            w.destroy()
        patient = patient or db.get_patient(patient_id)
        if not patient:
            return

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        info_card = ctk.CTkFrame(scroll, fg_color=theme.CARD_BG, corner_radius=12)
        info_card.pack(fill="x", pady=6)

        # ---- هيدر الكارت: زرار الأرقام الإضافية + زرار تعديل/حفظ/إلغاء ----
        phones_header = ctk.CTkFrame(info_card, fg_color="transparent")
        phones_header.pack(fill="x", padx=20, pady=(12, 0))
        extra_phones_count = len(db.get_patient_phones(patient_id))
        ctk.CTkButton(
            phones_header,
            text=f"📱 أرقام تليفونات إضافية ({extra_phones_count})" if extra_phones_count
            else "📱 إضافة رقم تليفون آخر (واتساب مثلاً)",
            width=240, height=30, font=theme.FONT_SMALL,
            fg_color=theme.BG_MAIN, text_color=theme.ACCENT_BORDER, border_width=1, border_color=theme.BORDER,
            command=lambda: self._open_manage_phones_dialog(
                patient_id, on_close=lambda: self._render_info_tab(patient_id))
        ).pack(side="left")

        fields = {}  # هتتملي بقيم الحقول القابلة للتعديل بس لو edit_mode=True

        if edit_mode:
            def do_cancel():
                self._render_info_tab(patient_id, edit_mode=False)

            def do_save():
                name = fields["full_name"].get().strip()
                if not name:
                    return
                db.update_patient(
                    patient_id,
                    full_name=name,
                    phone=fields["phone"].get().strip(),
                    gender=fields["gender"].get().strip(),
                    occupation=fields["occupation"].get().strip(),
                    nationality=fields["nationality"].get().strip(),
                    birth_date=fields["birth_date"].get_iso_date(),
                    address=fields["address"].get().strip(),
                    allergies=fields["allergies"].get().strip(),
                    medical_notes=fields["medical_notes"].get().strip(),
                )
                # show_detail بدل _render_info_tab بس عشان اسم المريض في هيدر
                # الصفحة نفسه يتحدّث كمان لو المستخدم غيّر الاسم
                self.show_detail(patient_id)

            ctk.CTkButton(phones_header, text="✖ إلغاء", width=90, height=30, font=theme.FONT_SMALL,
                          fg_color="transparent", border_width=1, border_color=theme.BORDER,
                          text_color=theme.TEXT_DARK, command=do_cancel).pack(side="right", padx=(6, 0))
            theme.make_shadowed_button(phones_header, "✔ حفظ التعديلات", command=do_save,
                                        width=150, height=32, font=theme.FONT_SMALL
                                        ).pack(side="right")
        else:
            ctk.CTkButton(
                phones_header, text="✎ تعديل البيانات", width=150, height=30, font=theme.FONT_SMALL,
                fg_color=theme.BG_MAIN, text_color=theme.ACCENT_BORDER, border_width=1,
                border_color=theme.BORDER,
                command=lambda: self._render_info_tab(patient_id, edit_mode=True)
            ).pack(side="right")

        info_body = ctk.CTkFrame(info_card, fg_color="transparent")
        info_body.pack(padx=20, pady=16, fill="x")

        # ---- خانة صورة المريض - زي باقي الخانات بالظبط، لكن ليها زرار
        # تغيير/حذف منفصل خاص بيها (مش جزء من وضع تعديل باقي البيانات) ----
        photo_cell = ctk.CTkFrame(info_body, fg_color=theme.BG_MAIN, corner_radius=8)
        photo_cell.pack(fill="x", pady=(0, 10))
        self._build_info_photo_cell(photo_cell, patient_id, patient)

        info_grid = ctk.CTkFrame(info_body, fg_color="transparent")
        info_grid.pack(fill="x", expand=True)

        computed_age = db.calculate_age(patient["birth_date"])
        age_text = f"{computed_age} سنة" if computed_age is not None else "-"

        # كل بيان هنا بمسماه الثابت (label) اللي مش قابل للتعديل أبدًا، وبنوع
        # الحقل المناسب لتعديل قيمته بس (text/gender/date/readonly). "الاسم"
        # بقى أول بيان في الشبكة (زي ما طلب)، و"السن" فضل للقراءة بس لأنه
        # محسوب تلقائيًا من تاريخ الميلاد مش قيمة منفصلة تتكتب
        field_defs = [
            ("full_name", "الاسم", patient["full_name"] or "-", "text"),
            ("phone", "التليفون", patient["phone"] or "-", "text"),
            ("gender", "النوع", patient["gender"] or "-", "gender"),
            ("occupation", "الوظيفة", patient["occupation"] or "-", "text"),
            ("nationality", "الجنسية", patient["nationality"] or "-", "text"),
            ("birth_date", "تاريخ الميلاد", patient["birth_date"] or "-", "date"),
            ("age", "السن", age_text, "readonly"),
            ("address", "العنوان", patient["address"] or "-", "text"),
            ("allergies", "حساسية", patient["allergies"] or "-", "text"),
            ("medical_notes", "ملاحظات طبية", patient["medical_notes"] or "-", "text"),
        ]
        # شبكة 3 بيانات في السطر، وكل بيان في صندوق منفصل (تسمية أعلاه بلون خافت،
        # والقيمة أسفلها في مساحتها الخاصة) حتى تبقى واضحة ومنفصلة عن بعضها
        COLS = 3
        for idx, (key, label, value, ftype) in enumerate(field_defs):
            r = idx // COLS
            col = COLS - 1 - (idx % COLS)
            cell = ctk.CTkFrame(info_grid, fg_color=theme.BG_MAIN, corner_radius=8)
            cell.grid(row=r, column=col, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(cell, text=label, font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED, anchor="e").pack(fill="x", padx=12, pady=(8, 2))

            if edit_mode and ftype != "readonly":
                if ftype == "gender":
                    widget = ctk.CTkOptionMenu(
                        cell, values=["ذكر", "أنثى"], height=30, font=theme.FONT_SMALL,
                        fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                        button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9))
                    widget.set(patient["gender"] if patient["gender"] in ("ذكر", "أنثى") else "ذكر")
                    widget.pack(fill="x", padx=12, pady=(0, 10))
                elif ftype == "date":
                    widget = DateAutoEntry(cell, height=30, font=theme.FONT_SMALL)
                    theme.apply_sunken_style(widget)
                    if patient.get("birth_date"):
                        widget.set_iso_date(patient["birth_date"])
                    widget.pack(fill="x", padx=12, pady=(0, 10))
                else:
                    widget = RTLEntry(cell, height=30, font=theme.FONT_SMALL)
                    theme.apply_sunken_style(widget)
                    raw_value = patient.get(key)
                    if raw_value:
                        widget.insert(0, raw_value)
                    widget.pack(fill="x", padx=12, pady=(0, 10))
                fields[key] = widget
            else:
                ctk.CTkLabel(cell, text=value, font=theme.FONT_NORMAL,
                             text_color=theme.TEXT_DARK, anchor="e",
                             wraplength=200, justify="right").pack(fill="x", padx=12, pady=(0, 10))
        for c in range(COLS):
            info_grid.grid_columnconfigure(c, weight=1)

        if patient["family_id"]:
            family_row = ctk.CTkFrame(info_grid, fg_color=theme.BG_MAIN, corner_radius=8)
            family_row.grid(row=(len(field_defs) // COLS) + 1, column=0, columnspan=COLS,
                             sticky="ew", padx=5, pady=(8, 5))
            inner = ctk.CTkFrame(family_row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(inner, text="رقم الأسرة:", font=theme.FONT_SUBTITLE,
                         text_color=theme.TEXT_MUTED, anchor="e").pack(side="right")
            ctk.CTkLabel(inner, text=patient["family_id"], font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_DARK, anchor="e").pack(side="right", padx=(6, 10))
            ctk.CTkButton(inner, text="عرض أفراد الأسرة", width=140, height=28,
                          font=theme.FONT_SMALL, fg_color=theme.BG_MAIN, text_color=theme.ACCENT_BORDER,
                          border_width=1, border_color=theme.BORDER,
                          command=lambda: self._show_family_dialog(patient_id, patient["family_id"])
                          ).pack(side="right", padx=8)

        # الصور والملفات موجودة دلوقتي في سايد بار ثابت على شمال الصفحة (شايفاه دايمًا مهما كان التاب المفتوح)

    def _build_info_photo_cell(self, parent, patient_id, patient):
        """بترسم خانة صورة المريض جوه تاب البيانات - صورة + زرار "تغيير"
        (وزرار "حذف" لو فيه صورة أصلًا) بتاعتها بس هي، شغّالين دايمًا بغض
        النظر عن وضع تعديل باقي البيانات (fields) اللي فوق"""
        self._info_photo_cell_parent = parent
        for w in parent.winfo_children():
            w.destroy()

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=10)

        photo_frame = ctk.CTkFrame(row, fg_color=theme.CARD_BG, corner_radius=12, width=64, height=64)
        photo_frame.pack(side="right")
        photo_frame.pack_propagate(False)

        has_photo = bool(patient["profile_photo_path"] and os.path.exists(patient["profile_photo_path"]))
        if has_photo:
            try:
                img = Image.open(patient["profile_photo_path"])
                img.thumbnail((58, 58))
                ctk_img = ctk.CTkImage(light_image=img, size=img.size)
                ctk.CTkLabel(photo_frame, image=ctk_img, text="").pack(expand=True)
            except Exception:
                has_photo = False
                ctk.CTkLabel(photo_frame, text="🧑", font=(theme.FONT_FAMILY, 28)).pack(expand=True)
        else:
            ctk.CTkLabel(photo_frame, text="🧑", font=(theme.FONT_FAMILY, 28)).pack(expand=True)

        btn_col = ctk.CTkFrame(row, fg_color="transparent")
        btn_col.pack(side="right", padx=(0, 12))
        ctk.CTkLabel(btn_col, text="صورة المريض", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED, anchor="e").pack(anchor="e")
        btn_row = ctk.CTkFrame(btn_col, fg_color="transparent")
        btn_row.pack(anchor="e", pady=(4, 0))
        if has_photo:
            ctk.CTkButton(btn_row, text="✕ حذف", width=64, height=28, font=theme.FONT_SMALL,
                          fg_color=theme.DANGER, hover_color="#B71C1C",
                          command=lambda: self._delete_profile_photo(patient_id)
                          ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btn_row, text="✎ تغيير الصورة", width=120, height=28, font=theme.FONT_SMALL,
                      fg_color=theme.HEADER_GRAD_END, hover_color=theme.HEADER_GRAD_START,
                      text_color="#FFFFFF", border_width=0,
                      command=lambda: self._change_profile_photo(patient_id)).pack(side="right")

    # ---------------- تاب زيارات المتابعة ----------------

    def _render_visits_tab(self, patient_id):
        parent = self._detail_content
        for w in parent.winfo_children():
            w.destroy()

        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        ctk.CTkLabel(wrap, text="زيارات المتابعة", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", pady=(0, 8))

        visits_table = PatientVisitsTable(
            wrap, patient_id=patient_id,
            on_change=lambda: self._refresh_active_detail_tab(patient_id))
        visits_table.pack(fill="both", expand=True)

    def _build_header_photo(self, patient_id, patient=None, show_controls=True):
        """بترسم صورة المريض الصغيرة جوه self._header_photo_col (اللي بيكون
        في الهيدر جنب اسم المريض). show_controls=False تعني عرض الصورة بس
        من غير أزرار تغيير/حذف (زي ما بيحصل في هيدر ملف المريض دلوقتي -
        أزرار التعديل بقت في صفحة "تعديل البيانات" بدل هنا). بنعيد بناءها
        كل ما الصورة تتغيّر عشان تتحدث فورًا من غير ما نعيد رسم الصفحة كلها"""
        col = getattr(self, "_header_photo_col", None)
        if col is None or not col.winfo_exists():
            return
        patient = patient or db.get_patient(patient_id)
        if not patient:
            return
        for w in col.winfo_children():
            w.destroy()

        photo_frame = ctk.CTkFrame(col, fg_color=theme.BG_MAIN, corner_radius=12,
                                    width=60, height=60)
        photo_frame.pack()
        photo_frame.pack_propagate(False)

        has_photo = bool(patient["profile_photo_path"] and os.path.exists(patient["profile_photo_path"]))
        if has_photo:
            try:
                img = Image.open(patient["profile_photo_path"])
                img.thumbnail((55, 55))
                ctk_img = ctk.CTkImage(light_image=img, size=img.size)
                ctk.CTkLabel(photo_frame, image=ctk_img, text="").pack(expand=True)
            except Exception:
                has_photo = False
                ctk.CTkLabel(photo_frame, text="🧑", font=(theme.FONT_FAMILY, 26)).pack(expand=True)
        else:
            ctk.CTkLabel(photo_frame, text="🧑", font=(theme.FONT_FAMILY, 26)).pack(expand=True)

        if not show_controls:
            return

        btn_row = ctk.CTkFrame(col, fg_color="transparent")
        btn_row.pack(pady=(4, 0))
        # زر "حذف الصورة" بيظهر بس لو فيه صورة متسجّلة أصلًا، جنب زر التغيير
        if has_photo:
            del_btn = ctk.CTkButton(btn_row, text="✕", width=26, height=22, corner_radius=6,
                          fg_color=theme.DANGER, hover_color="#B71C1C",
                          font=(theme.FONT_FAMILY, 12),
                          command=lambda: self._delete_profile_photo(patient_id))
            del_btn.pack(side="right", padx=(3, 0))
            _Tooltip(del_btn, "حذف الصورة")
        edit_btn = ctk.CTkButton(btn_row, text="✎", width=26, height=22, corner_radius=6,
                      font=(theme.FONT_FAMILY, 12),
                      fg_color=theme.HEADER_GRAD_END, hover_color=theme.HEADER_GRAD_START,
                      text_color="#FFFFFF", border_width=0,
                      command=lambda: self._change_profile_photo(patient_id))
        edit_btn.pack(side="right")
        _Tooltip(edit_btn, "تغيير الصورة")

    def _change_profile_photo(self, patient_id):
        path = filedialog.askopenfilename(
            title="اختر الصورة الشخصية",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if not path:
            return
        os.makedirs(PROFILE_PHOTOS_DIR, exist_ok=True)
        dest = os.path.join(PROFILE_PHOTOS_DIR, f"patient_{patient_id}{os.path.splitext(path)[1]}")
        try:
            shutil.copy(path, dest)
        except Exception:
            return
        db.set_profile_photo(patient_id, dest)
        self._refresh_photo_widgets(patient_id)

    def _delete_profile_photo(self, patient_id):
        patient = db.get_patient(patient_id)
        old_path = patient["profile_photo_path"] if patient else None
        db.set_profile_photo(patient_id, None)
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
        self._refresh_photo_widgets(patient_id)

    def _refresh_photo_widgets(self, patient_id):
        """بتحدّث أي عنصر واجهة بيعرض صورة المريض حاليًا (صورة الهيدر
        الصغيرة و/أو خانة الصورة جوه تاب البيانات) - أيًا منهم كان موجود
        فعلاً في الشاشة وقتها"""
        if getattr(self, "_header_photo_col", None) is not None:
            self._build_header_photo(patient_id, show_controls=False)
        photo_cell = getattr(self, "_info_photo_cell_parent", None)
        if photo_cell is not None and photo_cell.winfo_exists():
            patient = db.get_patient(patient_id)
            if patient:
                self._build_info_photo_cell(photo_cell, patient_id, patient)

    def _show_family_dialog(self, patient_id, family_id):
        members = db.get_family_members(family_id, exclude_patient_id=patient_id)

        dialog = ctk.CTkToplevel(self)
        dialog.title("أفراد الأسرة")
        dialog.geometry("340x420")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"أفراد الأسرة ({family_id})", font=theme.FONT_SUBTITLE).pack(
            pady=(16, 10))

        if not members:
            ctk.CTkLabel(dialog, text="لا يوجد أفراد آخرون مسجَّلون بنفس رقم الأسرة",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED,
                         wraplength=280).pack(pady=30)
            return

        list_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        for m in members:
            row = ctk.CTkFrame(list_frame, fg_color=theme.BG_MAIN, corner_radius=8)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=m["full_name"], font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_DARK, anchor="e").pack(side="right", padx=10, pady=10)
            ctk.CTkButton(row, text="فتح الملف", width=90, height=30, font=theme.FONT_SMALL,
                          fg_color=theme.BG_MAIN, text_color=theme.ACCENT_BORDER,
                          border_width=1, border_color=theme.BORDER,
                          command=lambda mid=m["id"]: (dialog.destroy(), self.show_detail(mid))
                          ).pack(side="left", padx=8)

    # ---------------- تاب خريطة الأسنان ----------------

    def _render_teeth_tab(self, patient_id):
        parent = self._detail_content
        for w in parent.winfo_children():
            w.destroy()
        patient = db.get_patient(patient_id)

        # سكرول عام كـ"شبكة أمان" بس - العناصر المهمة (اختيار الطبيب، أزرار
        # العلاج) بقت فوق خالص جنب الشارت عشان تبقى ظاهرة من غير ما تحتاجي
        # تنزلي بالسكرول أصلاً على أغلب الشاشات، لكن السكرول العام لسه موجود
        # احتياطيًا عشان مفيش ضمان إن كل الشاشات هتسع كل حاجة بارتفاعها
        # الطبيعي (شاشات صغيرة/لاب توب بنسب تكبير مختلفة مثلاً)
        container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True)

        chart = ToothChart(container, patient_id=patient_id, current_user=self.current_user,
                            on_change=lambda: self._render_teeth_tab(patient_id))
        chart.pack(fill="x", pady=(6, 8))

    # ---------------- تاب سجل المعالجات (جدول مستقل) ----------------

    def _render_records_tab(self, patient_id):
        parent = self._detail_content
        for w in parent.winfo_children():
            w.destroy()

        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        ctk.CTkLabel(wrap, text="سجل المعالجات", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", pady=(0, 8))

        records_table = TreatmentRecordsTable(
            wrap, patient_id=patient_id,
            on_change=lambda: self._refresh_active_detail_tab(patient_id))
        records_table.pack(fill="both", expand=True)

    # ---------------- تاب الحسابات ----------------

    def _render_accounts_tab(self, patient_id):
        parent = self._detail_content
        for w in parent.winfo_children():
            w.destroy()
        patient = db.get_patient(patient_id)

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        balance = db.get_patient_balance(patient_id)
        discount_percent = patient["discount_percent"] or 0
        discount_amount = balance["total_charges"] * discount_percent / 100
        total_after_discount = balance["total_charges"] - discount_amount
        final_balance = total_after_discount - balance["total_paid"]

        # نسبة الخصم
        discount_card = ctk.CTkFrame(scroll, fg_color=theme.CARD_BG, corner_radius=12)
        discount_card.pack(fill="x", pady=6)
        discount_row = ctk.CTkFrame(discount_card, fg_color="transparent")
        discount_row.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(discount_row, text="نسبة الخصم %", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_DARK).pack(side="right", padx=(0, 8))
        discount_entry = ctk.CTkEntry(discount_row, width=90, height=36, justify="center",
                                       font=theme.FONT_NORMAL)
        discount_entry.insert(0, f"{discount_percent:g}")
        discount_entry.pack(side="right")

        def apply_discount():
            try:
                new_discount = float(discount_entry.get().strip())
            except ValueError:
                return
            new_discount = max(0, min(100, new_discount))
            db.update_patient(patient_id, discount_percent=new_discount)
            self._render_accounts_tab(patient_id)

        can_edit_accounts_early = (not self.current_user) or db.has_permission(
            self.current_user["role"], "edit_accounts")

        if can_edit_accounts_early:
            ctk.CTkButton(discount_row, text="تطبيق الخصم", width=110, height=36,
                          fg_color=theme.ACCENT_BORDER,
                          command=apply_discount).pack(side="right", padx=8)

        if discount_percent > 0:
            ctk.CTkLabel(discount_row,
                         text=f"قيمة الخصم: {discount_amount:g} جنيه  -  الإجمالي بعد الخصم: {total_after_discount:g} جنيه",
                         font=theme.FONT_SMALL, text_color=theme.SUCCESS).pack(side="left")

        summary_card = ctk.CTkFrame(scroll, fg_color=theme.CARD_BG, corner_radius=12)
        summary_card.pack(fill="x", pady=6)
        summary_row = ctk.CTkFrame(summary_card, fg_color="transparent")
        summary_row.pack(fill="x", padx=20, pady=16)

        for label, value, color in [
            ("إجمالي المعالجات", balance["total_charges"], theme.TEXT_DARK),
            ("الإجمالي بعد الخصم", total_after_discount, theme.TEXT_DARK),
            ("إجمالي المدفوع", balance["total_paid"], theme.SUCCESS),
            ("المتبقي المستحق", final_balance, theme.DANGER if final_balance > 0 else theme.SUCCESS),
        ]:
            box = ctk.CTkFrame(summary_row, fg_color=theme.BG_MAIN, corner_radius=10)
            box.pack(side="right", fill="both", expand=True, padx=6)
            ctk.CTkLabel(box, text=label, font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_MUTED).pack(pady=(14, 2))
            ctk.CTkLabel(box, text=f"{value:g} جنيه", font=theme.FONT_TITLE,
                         text_color=color).pack(pady=(0, 14))

        can_edit_accounts = (not self.current_user) or db.has_permission(
            self.current_user["role"], "edit_accounts")

        if can_edit_accounts:
            actions_row = ctk.CTkFrame(scroll, fg_color="transparent")
            actions_row.pack(fill="x", pady=(6, 10))
            ctk.CTkButton(actions_row, text="+ إضافة دفعة", height=44, fg_color=theme.SUCCESS,
                          font=theme.FONT_NORMAL,
                          command=lambda: self._open_payment_dialog(patient_id)).pack(
                side="right", fill="x", expand=True, padx=(6, 0))
            ctk.CTkButton(actions_row, text="+ إضافة مبلغ مستحق يدوي", height=44,
                          fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
                          border_width=1, border_color=theme.BORDER, font=theme.FONT_NORMAL,
                          command=lambda: self._open_charge_dialog(patient_id)).pack(
                side="right", fill="x", expand=True, padx=(0, 6))
        else:
            discount_entry.configure(state="disabled")

        print_row = ctk.CTkFrame(scroll, fg_color="transparent")
        print_row.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(print_row, text="🖨️ طباعة كشف حساب", height=44,
                      fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
                      border_width=1, border_color=theme.BORDER, font=theme.FONT_NORMAL,
                      command=lambda: self._open_print_statement_dialog(patient_id)).pack(fill="x")

        # سجل الحركات
        tx_card = ctk.CTkFrame(scroll, fg_color=theme.CARD_BG, corner_radius=12)
        tx_card.pack(fill="x", pady=6)
        ctk.CTkLabel(tx_card, text="سجل الحركات المالية", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", padx=20, pady=(16, 8))

        transactions = db.get_transactions(patient_id)
        if not transactions:
            ctk.CTkLabel(tx_card, text="لا توجد حركات مالية مسجَّلة بعد",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(
                anchor="e", padx=20, pady=(0, 16))
        else:
            for tx in transactions:
                is_charge = tx["tx_type"] == "charge"
                row = ctk.CTkFrame(tx_card, fg_color=theme.BG_MAIN, corner_radius=8)
                row.pack(fill="x", padx=20, pady=4)

                if can_edit_accounts_early:
                    ctk.CTkButton(row, text="إلغاء", width=55, height=26, fg_color=theme.DANGER,
                                  font=theme.FONT_SMALL,
                                  command=lambda tid=tx["id"]: self._delete_transaction(tid, patient_id)
                                  ).pack(side="left", padx=8)

                amount_text = f"{'+' if not is_charge else '-'}{tx['amount']:g} جنيه"
                ctk.CTkLabel(row, text=amount_text, font=theme.FONT_SUBTITLE,
                             text_color=theme.DANGER if is_charge else theme.SUCCESS,
                             width=110, anchor="w").pack(side="left", padx=8, pady=8)

                ctk.CTkLabel(row, text=tx["tx_date"], font=theme.FONT_SMALL,
                             text_color=theme.TEXT_MUTED, width=90, anchor="e").pack(
                    side="right", padx=(0, 8), pady=8)
                badge_text = "معالجة" if is_charge else "دفعة"
                ctk.CTkLabel(row, text=badge_text, font=theme.FONT_SMALL,
                             text_color="#FFFFFF",
                             fg_color=theme.DANGER if is_charge else theme.SUCCESS,
                             corner_radius=6, width=60, height=24).pack(side="right", padx=6)
                ctk.CTkLabel(row, text=tx["description"] or "-", font=theme.FONT_NORMAL,
                             text_color=theme.TEXT_DARK, anchor="e").pack(
                    side="right", padx=8, pady=8, fill="x", expand=True)
            ctk.CTkFrame(tx_card, fg_color="transparent", height=10).pack()

    def _delete_transaction(self, tx_id, patient_id):
        db.delete_transaction(tx_id)
        self._render_accounts_tab(patient_id)

    def _open_payment_dialog(self, patient_id):
        self._open_transaction_dialog(patient_id, "payment", "إضافة دفعة",
                                       "المبلغ المدفوع", theme.SUCCESS)

    def _open_print_statement_dialog(self, patient_id):
        earliest_records = db.get_treatment_records(patient_id)
        default_start = earliest_records[-1]["treatment_date"] if earliest_records else \
            datetime.now().strftime("%Y-%m-%d")

        dialog = ctk.CTkToplevel(self)
        dialog.title("طباعة كشف حساب")
        dialog.geometry("340x320")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="طباعة كشف حساب المريض", font=theme.FONT_SUBTITLE).pack(pady=(16, 14))

        ctk.CTkLabel(dialog, text="من تاريخ (YYYY-MM-DD)", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        start_entry = ctk.CTkEntry(dialog, width=260, height=40, justify="right", font=theme.FONT_NORMAL)
        start_entry.insert(0, default_start)
        start_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(dialog, text="إلى تاريخ (YYYY-MM-DD)", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        end_entry = ctk.CTkEntry(dialog, width=260, height=40, justify="right", font=theme.FONT_NORMAL)
        end_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        end_entry.pack(padx=30, pady=(2, 10), anchor="e")

        error_label = ctk.CTkLabel(dialog, text="", font=theme.FONT_SMALL, text_color=theme.DANGER,
                                    wraplength=280)
        error_label.pack(pady=4)

        def do_print():
            start = start_entry.get().strip()
            end = end_entry.get().strip()
            try:
                path = pdf_report.generate_account_statement(patient_id, start, end)
            except ImportError:
                error_label.configure(
                    text="محتاج تثبت مكتبات الـ PDF الأول: pip install fpdf2 arabic-reshaper python-bidi")
                return
            except Exception as e:
                error_label.configure(text=f"حصل خطأ: {e}")
                return
            dialog.destroy()
            open_with_default_app(path)

        ctk.CTkButton(dialog, text="🖨️ توليد وفتح الكشف", height=44, fg_color=theme.SUCCESS,
                      command=do_print).pack(padx=30, pady=16, fill="x")

    def _open_charge_dialog(self, patient_id):
        self._open_transaction_dialog(patient_id, "charge", "إضافة مبلغ مستحق",
                                       "المبلغ المستحق", theme.DANGER)

    def _open_transaction_dialog(self, patient_id, tx_type, title, amount_label, color):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("320x360")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=title, font=theme.FONT_SUBTITLE).pack(pady=(16, 10))

        ctk.CTkLabel(dialog, text=amount_label, font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        amount_entry = ctk.CTkEntry(dialog, width=250, justify="right", font=theme.FONT_NORMAL)
        amount_entry.pack(padx=30, pady=(2, 10), anchor="e")

        ctk.CTkLabel(dialog, text="ملاحظة", font=theme.FONT_NORMAL).pack(anchor="e", padx=30)
        note_entry = RTLEntry(dialog, width=250, height=60)
        note_entry.pack(padx=30, pady=(2, 10), anchor="e")

        def save():
            try:
                amount = float(amount_entry.get().strip())
            except ValueError:
                return
            if amount <= 0:
                return
            db.add_transaction(patient_id, tx_type, amount, description=note_entry.get().strip())
            dialog.destroy()
            self._render_accounts_tab(patient_id)

        ctk.CTkButton(dialog, text="حفظ", height=44, fg_color=color,
                      font=theme.FONT_SUBTITLE, command=save).pack(pady=20, padx=30, fill="x")
