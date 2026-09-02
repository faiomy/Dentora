# -*- coding: utf-8 -*-
"""
جدول "زيارات المتابعة" - نفس شكل جدول "سجل المعالجات" بالظبط (خلايا
متلاصقة بحدود رفيعة، صفوف متبدّلة اللون، وصفوف فراغ وهمية تكمّل شكل
الجدول)، لكن بأعمدة مختلفة: مسلسل - التاريخ - الطبيب - ما تم في الزيارة،
ومن غير زرار "+ إضافة" منفصل خالص.

الإضافة بقت بتحصل مباشرة من جوه الجدول نفسه: الضغط على أي خانة في أول
صف فاضي (صف الفراغ الوهمي) بينشئ زيارة جديدة فورًا بقيم افتراضية
(تاريخ اليوم + "كل الأطباء" + ملاحظة فاضية) وبيفتح نفس الخانة اللي
ضغطت عليها للتعديل على طول، بالظبط زي ما بيحصل مع أي خانة عادية في صف
موجود فعلًا.

ترتيب الأعمدة بيتحدد ديناميكيًا حسب لغة البرنامج (إعداد "language" في
جدول العيادة): في العربي (RTL) الجدول بيتقرا من اليمين لليسار فيبدأ
بعمود "مسلسل" ثم "التاريخ" أقصى اليمين، وفي الإنجليزي (LTR) نفس ترتيب
القراءة (مسلسل ثم التاريخ) لكن معكوس فعليًا فيبدأ من الشمال - الجدول
كله بينعكس مرآويًا بين الاتجاهين (زرار الحذف/التأكيد بيتنقل للطرف
التاني بالمثل) عشان يفضل شكل الجدول متسق مع اتجاه الكتابة.
"""

from datetime import datetime

import customtkinter as ctk

import theme
import database as db
from pages.rtl_entry import RTLEntry
from pages.date_auto_entry import DateAutoEntry

ALL_DOCTORS_LABEL = "كل الأطباء"


def _to_iso_today():
    return datetime.now().strftime("%Y-%m-%d")


# تعريف أعمدة بيانات الجدول بترتيب القراءة (اللي بييجي بعد عمود "مسلسل"
# مباشرة): (المفتاح, العنوان, أقل عرض بالبكسل, وزن التمدد النسبي, النوع).
# عمودي التاريخ والطبيب اتصغروا لأقل مساحة ممكنة، وعمود الملاحظات هو اللي
# بياخد كل المساحة الإضافية المتاحة (وزن تمدد عالي) عشان يفضل هو المتغيّر
# الرئيسي في العرض مش التاريخ/الطبيب
COLUMNS = [
    ("visit_date",  "التاريخ",                 66, 6,  "date"),
    ("doctor_name", "الطبيب",                  76, 8,  "doctor"),
    ("notes",       "ما تم في الزيارة (المعالجة)", 220, 70, "text"),
]

# عمود "مسلسل" (رقم تسلسلي للزيارة) - دايمًا أول عمود في ترتيب القراءة
# (قبل التاريخ مباشرة)، وعرضه ثابت صغير زي عمود الأكشن بالظبط، مش بيتمدد
# ولا بيتصغّر مع باقي الأعمدة
SERIAL_KEY = "serial"
SERIAL_LABEL = "م"
SERIAL_COL_MINSIZE = 34

ACTION_COL_MINSIZE = 66
N_DATA_COLS = len(COLUMNS)
N_READING_COLS = N_DATA_COLS + 1  # +1 لعمود المسلسل
MIN_COL_FLOOR = 34

ROW_HEIGHT = 26
HEADER_HEIGHT = 32
ACTION_CELL_WIDTH = ACTION_COL_MINSIZE - 8
CELL_FONT = (theme.CONTENT_FONT_FAMILY, 13)
HEADER_FONT = (theme.CONTENT_FONT_FAMILY, 13, "bold")
EDIT_WIDGET_HEIGHT = max(ROW_HEIGHT - 4, 14)
HEADER_CELL_HEIGHT = HEADER_HEIGHT
ROW_CELL_HEIGHT = ROW_HEIGHT
# نفس لون خط شبكة جدول سجل المعالجات - عشان الشكل يفضل متطابق بين الجدولين
GRID_LINE = "#C7CCD6"


class PatientVisitsTable(ctk.CTkFrame):
    def __init__(self, master, patient_id, on_change=None, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        self.patient_id = patient_id
        self.on_change = on_change

        self._doctor_names = []
        self._editing = None
        self._rtl = self._compute_rtl()
        self._col_widths = {key: minsize for key, _l, minsize, _w, _k in COLUMNS}
        self._stretch_mode = True
        self._resize_job = None
        self._real_row_count = 0
        self._max_row_used = 0

        self._build_static_ui()
        self.refresh()

    # ---------------- اتجاه الجدول (RTL/LTR) حسب لغة البرنامج ----------------

    def _compute_rtl(self):
        """بترجع True لو الجدول لازم يتقرا من اليمين لليسار (أي لغة غير
        الإنجليزية - افتراضيًا العربي)، أو False لو إنجليزي (LTR)"""
        try:
            settings = db.get_settings() or {}
            lang = str(settings.get("language") or "ar").strip().lower()
        except Exception:
            lang = "ar"
        return lang != "en"

    def _grid_col(self, reading_index):
        """بتحوّل ترتيب القراءة (0 = مسلسل، 1..N لأعمدة COLUMNS بالترتيب)
        لرقم عمود الـ grid الفعلي، حسب اتجاه اللغة: في RTL بيبدأ ترتيب
        القراءة من أقصى اليمين (المسلسل ثم التاريخ...) وعمود الأكشن أقصى
        الشمال؛ وفي LTR الجدول كله معكوس - ترتيب القراءة بيبدأ من أقصى
        الشمال وعمود الأكشن بينتقل لأقصى اليمين"""
        if self._rtl:
            return N_READING_COLS - reading_index
        return reading_index

    def _action_col(self):
        return 0 if self._rtl else N_READING_COLS

    # ---------------- ألوان الصفوف (متبدّلة: أبيض / لون الثيم الفاتح بتركيز 40%) ----------------

    def _alt_row_bg(self):
        """لون الثيم الفاتح (primary) بتركيز 40% فوق الأبيض - يُحسب من
        theme.PRIMARY_LIGHT الحالي عشان يفضل متزامن مع أي ثيم مفعّل"""
        return theme.lighten_color(theme.PRIMARY_LIGHT, 0.6)

    def _row_bg(self, idx):
        return theme.CARD_BG if idx % 2 == 0 else self._alt_row_bg()

    def _is_white_bg(self, color):
        return str(color).strip().upper() == str(theme.CARD_BG).strip().upper()

    # ---------------- الهيكل الثابت ----------------

    def _build_static_ui(self):
        try:
            self._build_static_ui_inner()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_build_error(e)

    def _show_build_error(self, error):
        box = ctk.CTkFrame(self, fg_color="#FDECEC", corner_radius=10,
                            border_width=1, border_color=theme.DANGER)
        box.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(box, text="حصل خطأ أثناء عرض زيارات المتابعة:",
                     font=(theme.CONTENT_FONT_FAMILY, 13, "bold"),
                     text_color=theme.DANGER, anchor="e").pack(
            anchor="e", padx=14, pady=(12, 2), fill="x")
        ctk.CTkLabel(box, text=f"{type(error).__name__}: {error}",
                     font=theme.FONT_SMALL, text_color=theme.TEXT_DARK,
                     anchor="e", justify="right", wraplength=700).pack(
            anchor="e", padx=14, pady=(0, 12), fill="x")

    def _build_static_ui_inner(self):
        # لون الحد المميز حوالين الجدول والخط السفلي بقى لون الثيم الفاتح
        # (PRIMARY_LIGHT) بدل لون الثيم الغامق (HEADER_GRAD_END) - عشان
        # نلغي لون الثيم الغامق من الجدول تمامًا
        card = ctk.CTkFrame(self, fg_color=theme.CARD_BG, corner_radius=8,
                             border_width=3, border_color=theme.PRIMARY_LIGHT)
        card.pack(fill="both", expand=True)

        self._scroller = ctk.CTkScrollableFrame(card, fg_color=theme.CARD_BG, corner_radius=0)
        self._scroller.pack(fill="both", expand=True, padx=3, pady=3)

        self._table = ctk.CTkFrame(self._scroller, fg_color=theme.CARD_BG, corner_radius=0)
        self._table.pack(fill="x")
        self._apply_columns(self._table)
        self._table.grid_rowconfigure(0, minsize=HEADER_HEIGHT, weight=0)

        # خانة هيدر عمود الأكشن (فاضية) - بنفس لون الثيم الفاتح زي باقي الهيدر
        ctk.CTkLabel(self._table, text="", height=HEADER_CELL_HEIGHT,
                     fg_color=theme.PRIMARY_LIGHT, corner_radius=0,
                     border_width=1, border_color=GRID_LINE).grid(
            row=0, column=self._action_col(), sticky="nsew")

        # خانة هيدر عمود المسلسل
        ctk.CTkLabel(self._table, text=SERIAL_LABEL, font=HEADER_FONT,
                     height=HEADER_CELL_HEIGHT, text_color="#FFFFFF",
                     fg_color=theme.PRIMARY_LIGHT, corner_radius=0,
                     border_width=1, border_color=GRID_LINE,
                     anchor="center").grid(
            row=0, column=self._grid_col(0), sticky="nsew")

        for i, (_key, label, _minsize, _weight, _kind) in enumerate(COLUMNS):
            ctk.CTkLabel(self._table, text=label, font=HEADER_FONT, height=HEADER_CELL_HEIGHT,
                         text_color="#FFFFFF", fg_color=theme.PRIMARY_LIGHT,
                         corner_radius=0, border_width=1, border_color=GRID_LINE,
                         anchor="center").grid(
                row=0, column=self._grid_col(i + 1), sticky="nsew")

        self._empty_label = ctk.CTkLabel(
            card, text="لا توجد زيارات متابعة مسجَّلة بعد - اضغط على أي خانة بالأسفل لإضافة زيارة",
            font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED)

        bottom_bar = ctk.CTkFrame(card, fg_color=theme.PRIMARY_LIGHT, corner_radius=0,
                                   height=3)
        bottom_bar.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        canvas = self._scroller._parent_canvas
        canvas.bind("<Configure>", self._on_canvas_configure, add="+")
        self.after(80, lambda: self._on_canvas_configure(None))
        self.after(400, lambda: self._on_canvas_configure(None))

    # ---------------- حساب/تطبيق عرض الأعمدة ----------------

    def _on_canvas_configure(self, _event):
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(40, self._recompute_layout)

    def _recompute_layout(self):
        self._resize_job = None
        try:
            self.update_idletasks()
            canvas = self._scroller._parent_canvas
            canvas_width = canvas.winfo_width()
        except Exception:
            return
        if canvas_width <= 1:
            self._resize_job = self.after(120, self._recompute_layout)
            return

        available = canvas_width - ACTION_COL_MINSIZE - SERIAL_COL_MINSIZE
        natural_sum = sum(minsize for _k, _l, minsize, _w, _kind in COLUMNS)
        scale = available / natural_sum if natural_sum > 0 else 1.0

        if scale >= 1.0:
            self._stretch_mode = True
            self._col_widths = {key: minsize for key, _l, minsize, _w, _k in COLUMNS}
        else:
            self._stretch_mode = False
            self._col_widths = {
                key: max(MIN_COL_FLOOR, int(minsize * scale))
                for key, _l, minsize, _w, _kind in COLUMNS
            }

        self._apply_columns(self._table)
        self._sync_filler_rows()

    def _apply_columns(self, frame):
        frame.grid_columnconfigure(self._action_col(), weight=0, minsize=ACTION_COL_MINSIZE)
        frame.grid_columnconfigure(self._grid_col(0), weight=0, minsize=SERIAL_COL_MINSIZE)
        for i, (key, _label, _minsize, weight, _kind) in enumerate(COLUMNS):
            col = self._grid_col(i + 1)
            w = self._col_widths.get(key, _minsize)
            if self._stretch_mode:
                frame.grid_columnconfigure(col, weight=weight, minsize=w)
            else:
                frame.grid_columnconfigure(col, weight=0, minsize=w)

    # ---------------- أدوات صغيرة ----------------

    def _cell(self, row_index, col_index):
        slaves = self._table.grid_slaves(row=row_index, column=col_index)
        return slaves[0] if slaves else None

    def _reset_row_range(self, start_row, end_row):
        for r in range(start_row, end_row + 1):
            self._table.grid_rowconfigure(r, minsize=0, weight=0)

    def _doctor_values(self):
        values = [ALL_DOCTORS_LABEL] + list(self._doctor_names)
        return values

    # ---------------- تحديث/إعادة رسم الصفوف ----------------

    def refresh(self):
        if not hasattr(self, "_scroller"):
            return
        try:
            self._refresh_inner()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_build_error(e)

    def _refresh_inner(self):
        self._editing = None
        # نرجّع كل الأعمدة لإعدادها الطبيعي (احتياطًا لو فيه عمود اتجمّد
        # مؤقتًا وقت تعديل خلية ولسه ما رجعش لوضعه الطبيعي)
        self._apply_columns(self._table)
        self._clear_body(full=True)

        self._doctor_names = [d["full_name"] for d in db.get_doctors()]
        records = db.get_visits(self.patient_id)
        self._empty_label.pack_forget()

        if not records:
            self._real_row_count = 0
            self._empty_label.pack(pady=24)
            self._max_row_used = 0
            self._sync_filler_rows()
            return

        for idx, record in enumerate(records):
            self._build_row(record, idx)
        self._real_row_count = len(records)
        self._max_row_used = self._real_row_count
        self._sync_filler_rows()

    def _clear_body(self, full):
        for w in list(self._table.winfo_children()):
            if getattr(w, "_is_filler", False) or (full and getattr(w, "_is_data_row", False)):
                w.destroy()

        if full:
            self._reset_row_range(1, max(self._max_row_used, 1))
            self._max_row_used = 0
        else:
            self._reset_row_range(self._real_row_count + 1, max(self._max_row_used, 1))
            self._max_row_used = self._real_row_count

    # ---------------- صفوف وهمية فاضية (وهي كمان بوابة إضافة زيارة جديدة) ----------------

    def _sync_filler_rows(self):
        try:
            canvas_height = self._scroller._parent_canvas.winfo_height()
        except Exception:
            return
        if canvas_height <= 1:
            return

        self._clear_body(full=False)

        real_count = getattr(self, "_real_row_count", 0)
        used_height = HEADER_HEIGHT + real_count * ROW_HEIGHT
        remaining = canvas_height - used_height
        target_filler = int(remaining // ROW_HEIGHT) if remaining > 0 else 0
        # لازم يفضل صف فاضي واحد على الأقل ظاهر دايمًا، حتى لو الجدول
        # مليان المساحة المتاحة بالكامل، عشان يفضل فيه طريقة واضحة لإضافة
        # زيارة جديدة من غير الحاجة لعمل سكرول لتحت الأول
        target_filler = max(target_filler, 1)

        for i in range(target_filler):
            self._build_filler_row(real_count + i)

    def _build_filler_row(self, idx):
        row_index = idx + 1
        self._table.grid_rowconfigure(row_index, minsize=ROW_HEIGHT, weight=0)
        self._max_row_used = max(self._max_row_used, row_index)
        row_bg = self._row_bg(idx)

        action_cell = ctk.CTkFrame(self._table, fg_color=row_bg,
                                    width=ACTION_CELL_WIDTH, height=ROW_CELL_HEIGHT,
                                    corner_radius=0, border_width=1, border_color=GRID_LINE)
        action_cell.grid(row=row_index, column=self._action_col(), sticky="nsew")
        action_cell._is_filler = True

        serial_lbl = ctk.CTkLabel(self._table, text="", height=ROW_CELL_HEIGHT, fg_color=row_bg,
                                   corner_radius=0, border_width=1, border_color=GRID_LINE,
                                   cursor="hand2")
        serial_lbl.grid(row=row_index, column=self._grid_col(0), sticky="nsew")
        serial_lbl._is_filler = True
        serial_lbl.bind("<Button-1>", lambda e: self._start_new_row("notes", "text"))

        for i, (key, _label, _minsize, _weight, kind) in enumerate(COLUMNS):
            lbl = ctk.CTkLabel(self._table, text="", height=ROW_CELL_HEIGHT, fg_color=row_bg,
                                corner_radius=0, border_width=1, border_color=GRID_LINE,
                                cursor="hand2")
            lbl.grid(row=row_index, column=self._grid_col(i + 1), sticky="nsew")
            lbl._is_filler = True
            lbl.bind("<Button-1>", lambda e, k=key, kd=kind: self._start_new_row(k, kd))

    # ---------------- إنشاء زيارة جديدة بالضغط على صف فاضي ----------------

    def _start_new_row(self, key, kind):
        if self._editing is not None:
            self._cancel_edit()

        new_id = db.add_visit(
            self.patient_id, notes="", visit_date=_to_iso_today(),
            doctor_name=ALL_DOCTORS_LABEL)

        self.refresh()

        records = db.get_visits(self.patient_id)
        for idx, record in enumerate(records):
            if record["id"] == new_id:
                row_index = idx + 1
                col_i = [c[0] for c in COLUMNS].index(key)
                grid_col = self._grid_col(col_i + 1)
                row_bg = self._row_bg(idx)
                self._start_edit(row_index, record, key, kind, grid_col, row_bg)
                break

        # ملحوظة مهمة: من غير قصد on_change() هنا كانت بتنادي على تحديث
        # التاب كله من صفحة المريض (patients_page._refresh_active_detail_tab)،
        # وده بيهدم الجدول الحالي بالكامل ويبنيه من جديد - يعني الخلية اللي
        # فتحناها للتو للتعديل كانت بتتمسح فورًا (قبل ما المستخدم يشوفها
        # حتى) وترجع لوضع العرض العادي (وتظهر "—"). ما بنستدعيش on_change
        # هنا؛ هو بيتنادى تلقائيًا من _confirm_edit() لما التعديل يتأكد فعلًا

    # ---------------- بناء صف بيانات حقيقي ----------------

    def _build_row(self, record, idx):
        row_index = idx + 1
        self._table.grid_rowconfigure(row_index, minsize=ROW_HEIGHT, weight=0)
        row_bg = self._row_bg(idx)

        record_id = record["id"]

        action_cell = ctk.CTkFrame(self._table, fg_color=row_bg,
                                    width=ACTION_CELL_WIDTH, height=ROW_CELL_HEIGHT,
                                    corner_radius=0, border_width=1, border_color=GRID_LINE)
        action_cell.grid(row=row_index, column=self._action_col(), sticky="nsew")
        action_cell.pack_propagate(False)
        action_cell._is_data_row = True
        self._render_delete_button(action_cell, record_id)

        # عمود المسلسل - رقم ترتيب الزيارة (للعرض فقط، مش قابل للتعديل)
        serial_cell = ctk.CTkLabel(self._table, text=str(idx + 1), font=CELL_FONT,
                                    height=ROW_CELL_HEIGHT, text_color=theme.TEXT_DARK,
                                    fg_color=row_bg, anchor="center",
                                    corner_radius=0, border_width=1, border_color=GRID_LINE)
        serial_cell.grid(row=row_index, column=self._grid_col(0), sticky="nsew")
        serial_cell._is_data_row = True

        for i, (key, _label, _minsize, _weight, kind) in enumerate(COLUMNS):
            self._render_cell_view(row_index, record, key, kind, record.get(key),
                                    grid_col=self._grid_col(i + 1), row_bg=row_bg)

    def _render_delete_button(self, action_cell, record_id):
        for w in action_cell.winfo_children():
            w.destroy()

        row_bg = action_cell.cget("fg_color")

        btn_size = max(round(ROW_CELL_HEIGHT * 0.75), 12)
        outer = ctk.CTkFrame(action_cell, fg_color="#000000", corner_radius=3,
                              width=btn_size, height=btn_size)
        outer.pack(expand=True)
        outer.pack_propagate(False)

        inner = ctk.CTkFrame(outer, fg_color=row_bg, corner_radius=0)
        inner.pack(padx=(1, 3), pady=(1, 3), fill="both", expand=True)

        label = ctk.CTkLabel(inner, text="✕", font=(theme.CONTENT_FONT_FAMILY, 9, "bold"),
                              text_color="#000000")
        label.pack(expand=True, fill="both")

        def _trigger(_e=None):
            self._confirm_delete(record_id)

        for w in (outer, inner, label):
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass
            w.bind("<Button-1>", _trigger)

    def _confirm_delete(self, record_id):
        theme.confirm_dialog(
            self, "هل تريد حذف هذه الزيارة نهائيًا؟",
            lambda: self._delete_record(record_id),
            title="تأكيد الحذف", confirm_text="حذف", danger=True,
        )

    def _delete_record(self, record_id):
        db.delete_visit(record_id)
        self.refresh()
        if self.on_change:
            self.on_change()

    # ---------------- عرض قيمة الخلية (وضع القراءة) ----------------

    def _render_cell_view(self, row_index, record, key, kind, value, grid_col, row_bg):
        if kind == "date":
            text = value or "—"
        elif kind == "doctor":
            text = value or ALL_DOCTORS_LABEL
        else:
            text = str(value).strip() if str(value or "").strip() else "—"

        # عمود "ما تم في الزيارة" بيتحاذى شمال (مش وسط زي باقي الأعمدة)
        # حتى في وضع العرض العادي (مش بس وقت التعديل)
        cell_anchor = "w" if kind == "text" else "center"
        lbl = ctk.CTkLabel(self._table, text=text, font=CELL_FONT, height=ROW_CELL_HEIGHT,
                            text_color=theme.TEXT_DARK,
                            fg_color=row_bg, anchor=cell_anchor, cursor="hand2",
                            padx=8 if cell_anchor == "w" else 0,
                            corner_radius=0, border_width=1, border_color=GRID_LINE)
        lbl.grid(row=row_index, column=grid_col, sticky="nsew")
        lbl._is_data_row = True
        lbl.bind("<Button-1>", lambda e: self._start_edit(row_index, record, key, kind, grid_col, row_bg))

    # ---------------- الدخول في وضع التعديل ----------------

    def _start_edit(self, row_index, record, key, kind, grid_col, row_bg):
        if self._editing is not None:
            self._cancel_edit()

        action_cell = self._cell(row_index, self._action_col())
        old_widget = self._cell(row_index, grid_col)
        cell_width = max(old_widget.winfo_width(), 60) if old_widget else 100
        if old_widget:
            old_widget.destroy()

        # نجمّد عرض العمود اللي بيتفتح للتعديل بالظبط على مقاسه الحالي.
        # بدون التجميد ده، مجرد تمرير نفس العرض (width=cell_width) لودجت
        # التعديل (حقل/منسدلة) بيخلي الحد الأدنى المطلوب للعمود يتخطى الـ
        # minsize الأصلي المسجّل في grid_columnconfigure، وده بيغيّر حسبة
        # توزيع المساحة الإضافية (weight) على كل الأعمدة، فيكبر العمود
        # أكتر من cell_width الأصلية (وهي المشكلة اللي كانت بتحصل قبل كده -
        # توسّع العمود حوالي 1 و1/3 مرة عند فتح أي خلية للتعديل). التجميد
        # ده بيقفل العمود على مقاسه بالظبط لحد ما يترجع الإعداد الطبيعي في
        # _refresh_inner بعد التأكيد أو الإلغاء
        self._table.grid_columnconfigure(grid_col, minsize=cell_width, weight=0)

        widget = self._make_edit_widget(record, key, kind, cell_width, row_bg)
        widget.grid(row=row_index, column=grid_col, sticky="nsew")
        widget._is_data_row = True

        try:
            widget.focus_set()
        except Exception:
            pass

        self._editing = {
            "record": record, "key": key, "kind": kind, "row_index": row_index,
            "widget": widget, "action_cell": action_cell,
            "grid_col": grid_col, "row_bg": row_bg,
        }
        if action_cell is not None:
            self._render_confirm_cancel(action_cell)

    def _make_edit_widget(self, record, key, kind, cell_width, row_bg):
        current = record.get(key)
        if kind == "date":
            w = DateAutoEntry(self._table, width=cell_width, height=EDIT_WIDGET_HEIGHT,
                               font=CELL_FONT, justify="center")
            w.set_iso_date(current or _to_iso_today())
            w.bind("<Return>", lambda e: self._confirm_edit())
            w.bind("<Escape>", lambda e: self._cancel_edit())
            self._bind_tab_navigation(w)
            return w

        if kind == "doctor":
            values = self._doctor_values()
            if current and current not in values:
                values = [current] + values
            # منسدلة الأطباء بلون معكوس عن لون صف الجدول: لو الصف أبيض
            # تاخد لون الثيم الفاتح (40%)، ولو الصف ملوّن تاخد الأبيض
            inverse_bg = self._alt_row_bg() if self._is_white_bg(row_bg) else theme.CARD_BG
            w = ctk.CTkOptionMenu(self._table, values=values, width=cell_width, height=EDIT_WIDGET_HEIGHT,
                                   font=CELL_FONT, fg_color=inverse_bg, button_color=inverse_bg,
                                   button_hover_color=theme.PRIMARY_LIGHT,
                                   text_color=theme.TEXT_DARK,
                                   dropdown_fg_color=theme.CARD_BG,
                                   dropdown_text_color=theme.TEXT_DARK,
                                   dropdown_hover_color=self._alt_row_bg(),
                                   # بمجرد اختيار طبيب من القايمة بيتسجل ويتحفظ على طول
                                   # (مش لازم تدوس ✓ منفصل بعدها) - عشان الاختيار ميضاعش
                                   command=lambda value: self._confirm_edit())
            w.set(current or ALL_DOCTORS_LABEL)
            self._bind_tab_navigation(w)
            return w

        # text (ما تم في الزيارة) - محاذاة شمال (مش يمين زي افتراضي كلاس
        # RTLEntry) - بنعدّل تاج المحاذاة بتاع النسخة دي بس من غير ما نلمس
        # كلاس RTLEntry نفسه (المستخدم في أماكن تانية بمحاذاة يمين طبيعية)
        w = RTLEntry(self._table, width=cell_width, height=EDIT_WIDGET_HEIGHT, font=CELL_FONT)
        try:
            w._textbox.tag_configure("rtl", justify="left")
        except Exception:
            pass
        if current:
            w.insert("1.0", str(current))
        w.bind("<Escape>", lambda e: self._cancel_edit())
        self._bind_tab_navigation(w)
        return w

    # ---------------- الانتقال بين الخانات بزرار Tab ----------------

    def _bind_tab_navigation(self, widget):
        """بتخلي زرار Tab (و Shift+Tab) ينقل التركيز للخانة اللي بعد/قبل
        الخانة الحالية في نفس الصف (بعد ما يحفظ التعديل الحالي أوتوماتيك)،
        بدل السلوك الافتراضي (إدراج تاب أو قفزة تركيز عشوائية)"""
        widget.bind("<Tab>", lambda e: self._handle_tab(reverse=False))
        widget.bind("<Shift-Tab>", lambda e: self._handle_tab(reverse=True))
        # على لينكس زرار Shift+Tab بيتبعت أحيانًا كـ ISO_Left_Tab مش Shift-Tab
        widget.bind("<Shift-ISO_Left_Tab>", lambda e: self._handle_tab(reverse=True))

    def _handle_tab(self, reverse=False):
        if not self._editing:
            return "break"
        editing = self._editing
        record_id = editing["record"]["id"]
        key = editing["key"]
        col_keys = [c[0] for c in COLUMNS]
        try:
            cur_idx = col_keys.index(key)
        except ValueError:
            return "break"
        direction = -1 if reverse else 1
        next_idx = cur_idx + direction

        self._confirm_edit()
        if self._editing is not None:
            # التأكيد فشل (مثلاً تاريخ ناقص/غير صحيح) - نفضل في نفس الخانة
            return "break"

        if 0 <= next_idx < len(col_keys):
            next_key, next_kind = col_keys[next_idx], COLUMNS[next_idx][4]
            self._open_cell_for_record(record_id, next_key, next_kind)
        else:
            self._open_adjacent_row(record_id, direction)
        return "break"

    def _open_cell_for_record(self, record_id, key, kind):
        records = db.get_visits(self.patient_id)
        for idx, record in enumerate(records):
            if record["id"] == record_id:
                row_index = idx + 1
                col_i = [c[0] for c in COLUMNS].index(key)
                grid_col = self._grid_col(col_i + 1)
                row_bg = self._row_bg(idx)
                self._start_edit(row_index, record, key, kind, grid_col, row_bg)
                return True
        return False

    def _open_adjacent_row(self, record_id, direction):
        """لما التاب يوصل لآخر/أول عمود في الصف، بينتقل لأول عمود في الصف
        اللي بعده أو آخر عمود في الصف اللي قبله؛ ولو كان في آخر صف
        وبيتحرك للقدام، بينشئ زيارة جديدة زي بالظبط الضغط على خانة فاضية"""
        records = db.get_visits(self.patient_id)
        ids = [r["id"] for r in records]
        try:
            pos = ids.index(record_id)
        except ValueError:
            return
        target_pos = pos + direction
        first_key, first_kind = COLUMNS[0][0], COLUMNS[0][4]
        last_key, last_kind = COLUMNS[-1][0], COLUMNS[-1][4]

        if direction > 0:
            if target_pos < len(records):
                self._open_cell_for_record(records[target_pos]["id"], first_key, first_kind)
            else:
                self._start_new_row(first_key, first_kind)
        else:
            if target_pos >= 0:
                self._open_cell_for_record(records[target_pos]["id"], last_key, last_kind)

    def _render_confirm_cancel(self, action_cell):
        for w in action_cell.winfo_children():
            w.destroy()
        wrap = ctk.CTkFrame(action_cell, fg_color="transparent", width=48, height=20)
        # expand=True (بدل pack() لوحدها) عشان الإطار يتوسّط رأسيًا بالظبط
        # في نص ارتفاع خانة الأكشن، مش يفضل ملتصق بأعلاها زي ما كان بيحصل
        wrap.pack(expand=True)
        wrap.pack_propagate(False)
        ctk.CTkButton(wrap, text="✓", width=22, height=20, fg_color=theme.SUCCESS,
                       font=(theme.CONTENT_FONT_FAMILY, 11, "bold"),
                       command=self._confirm_edit).pack(side="left", padx=(0, 2))
        ctk.CTkButton(wrap, text="✕", width=22, height=20, fg_color=theme.DANGER,
                       font=(theme.CONTENT_FONT_FAMILY, 11, "bold"),
                       command=self._cancel_edit).pack(side="left")

    # ---------------- تأكيد / إلغاء التعديل ----------------

    def _cancel_edit(self):
        if not self._editing:
            return
        editing = self._editing
        self._editing = None
        record, key, kind = editing["record"], editing["key"], editing["kind"]
        editing["widget"].destroy()
        # نرجّع إعداد الأعمدة الطبيعي (بعد ما كان اتجمّد وقت التعديل)
        self._apply_columns(self._table)
        self._render_cell_view(editing["row_index"], record, key, kind, record.get(key),
                                editing["grid_col"], editing["row_bg"])
        if editing["action_cell"] is not None:
            self._render_delete_button(editing["action_cell"], record["id"])

    def _confirm_edit(self):
        if not self._editing:
            return
        editing = self._editing
        record, key, kind, widget = (editing["record"], editing["key"],
                                      editing["kind"], editing["widget"])

        if kind == "date":
            new_value = widget.get_iso_date()
            if not new_value:
                return
            fields = {"visit_date": new_value}

        elif kind == "doctor":
            fields = {"doctor_name": widget.get()}

        else:  # text
            try:
                text_value = widget.get("1.0", "end").strip()
            except Exception:
                text_value = ""
            fields = {"notes": text_value}

        db.update_visit_fields(record["id"], **fields)
        self._editing = None
        self.refresh()
        if self.on_change:
            self.on_change()
