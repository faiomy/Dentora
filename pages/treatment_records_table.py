# -*- coding: utf-8 -*-
"""
جدول "سجل المعالجات" - شكل جدول عادي (زي إكسل) بصفوف متبدّلة اللون
وصف عناوين ثابت، وبيتحسب عرض أعمدته تلقائيًا حسب المساحة المتاحة فعليًا
في الصفحة (مفيش عرض ثابت بيتقطع - الأعمدة بتاخد نسبة من العرض المتاح
باستخدام grid weights بدل عرض ثابت بالبكسل، فبيتظبط أوتوماتيك حتى لو
اتسحب سايد بار الصور وغيّر المساحة المتاحة).

مهم: الهيدر وصفوف البيانات وصفوف الفراغ الوهمية (اللي بتكمّل شكل الجدول)
كلهم دلوقتي جوه grid واحد بس (self._table)، مش كل واحد فيهم بيتحسب في
Frame منفصل بتنسيق أعمدة خاص بيه. ده اللي بيضمن إن الفواصل الرأسية
والأعمدة بتتطابق 100% بين الهيدر والصفوف مهما كان عددها - لأن فيه مصدر
واحد بس لعرض كل عمود (grid_columnconfigure على self._table) بدل ما كل
صف يحسب لوحده وممكن يحصل فرق تقريب/توقيت بينهم زي ما كان بيحصل قبل كده.

الضغط على أي حقل قابل للتعديل بيفتحه للكتابة، وبيظهر زرين تأكيد/إلغاء في
عمود الأكشن (أقصى شمال الجدول) لحد ما تأكدي أو تلغي.
"""

import customtkinter as ctk

import theme
import database as db
from pages.rtl_entry import RTLEntry
from pages.date_auto_entry import DateAutoEntry


def _fmt_num(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.2f}"


def _to_float(text, default=0.0):
    text = (text or "").strip().replace(",", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return None


# تعريف أعمدة الجدول بترتيب القراءة من اليمين لليسار (زي ما هيتقرا عربي):
# (المفتاح, العنوان, أقل عرض بالبكسل, وزن التمدد النسبي, النوع)
# الأنواع: date / text / doctor / number / percent / computed / lab
COLUMNS = [
    ("treatment_date",    "التاريخ",          100, 9,  "date"),
    ("doctor_name",       "الطبيب",           92,  11, "doctor"),
    ("treatment_label",   "المعالجة",         120, 15, "text"),
    ("teeth",             "الاسنان",          64,  7,  "teeth"),
    ("price",             "القيمة",           68,  9,  "number"),
    ("discount_amount",   "الخصم (مبلغ)",     82,  9,  "number"),
    ("discount_percent",  "الخصم (%)",        76,  8,  "percent"),
    ("net",               "اجمالي المستحق",   92,  10, "computed"),
    ("paid_amount",       "المدفوع",          70,  9,  "number"),
    ("remaining",         "المتبقي",          70,  9,  "computed"),
    ("lab_name",          "المعمل",           86,  11, "lab"),
    ("notes",             "ملاحظات",          110, 13, "text"),
]
ACTION_COL_MINSIZE = 66
N_COLS = len(COLUMNS)
# أقل عرض ممكن يوصله أي عمود بيانات لو المساحة المتاحة ضاقت جدًا (سحب سايد
# بار الصور لآخره مثلاً) - عشان الأعمدة تنكمش بدل ما تتقطع/تختفي
MIN_COL_FLOOR = 34

# نفس بنيان جدول المرضى الرئيسي: خلايا متلاصقة (من غير padx/pady بينها)
# وكل خلية ليها حد (border) رفيع بلون واحد، فالحدود بتتلاقى مع بعضها
# وتبان كخط فاصل واحد بس بين كل خلية وجارتها - مفيش فراغات.
# ارتفاع الصف اتقلل 4 بيكسل عن القيمة السابقة (كانت 24) بناءً على طلب المستخدم.
ROW_HEIGHT = 20
HEADER_HEIGHT = 30
ACTION_CELL_WIDTH = ACTION_COL_MINSIZE - 8
CELL_FONT = (theme.CONTENT_FONT_FAMILY, 13, "bold")
CELL_FONT_BOLD = (theme.CONTENT_FONT_FAMILY, 13, "bold")
HEADER_FONT = (theme.CONTENT_FONT_FAMILY, 13, "bold")
EDIT_WIDGET_HEIGHT = max(ROW_HEIGHT - 4, 14)
# ارتفاع صريح لكل خلية (Label) لازم نحطه إحنا بالظبط، وإلا الـheight
# الافتراضي بتاع CTkLabel (28) أو CTkFrame (200) بيدخل في حساب مساحة
# الصف جوه الـgrid وممكن "يكسّر" الطول المطلوب ويخليه أكبر بكتير من غير
# قصد - ده أصل مشكلة الفراغات الرأسية الكبيرة اللي كانت ظاهرة
HEADER_CELL_HEIGHT = HEADER_HEIGHT
ROW_CELL_HEIGHT = ROW_HEIGHT
# لون خط شبكة الجدول - نفس اللون المستخدم في جدول المرضى الرئيسي، عشان
# الشكل يبقى متطابق مع باقي الشاشات
GRID_LINE = theme.BORDER


def _grid_col(i):
    """بيحوّل ترتيب العمود المنطقي (0 = التاريخ ...) لرقم عمود الـgrid،
    بحيث عمود الأكشن يبقى أقصى الشمال وعمود التاريخ أقصى اليمين (قراءة RTL).
    مفيش عواميد فاصلة تانية دلوقتي - كل عمود بيانات جنب التاني على طول،
    والحد (border) بتاع كل خلية هو اللي بيرسم الخط الفاصل بينهم."""
    return N_COLS - i


class TreatmentRecordsTable(ctk.CTkFrame):
    def __init__(self, master, patient_id, on_change=None, can_edit=True, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        self.patient_id = patient_id
        self.on_change = on_change
        self.can_edit = can_edit

        self._doctor_names = []
        self._editing = None  # dict بتفاصيل الخلية اللي بتتعدل حاليًا
        self._col_widths = {key: minsize for key, _l, minsize, _w, _k in COLUMNS}
        self._stretch_mode = True  # فاضل مساحة زيادة توزّع تناسبيًا على الأعمدة
        self._resize_job = None
        self._real_row_count = 0
        # أعلى رقم صف (grid row) اتعمله rowconfigure ليه فعليًا في self._table
        # (مش عدّاد الصفوف الحقيقية بس - بيشمل صفوف الفراغ الوهمية كمان)،
        # محتاجينه عشان نصفّر الـrowconfigure بتاع الصفوف اللي اتشالت بدل ما
        # تفضل مساحتها محجوزة فاضية وتبوّظ محاذاة الجدول.
        self._max_row_used = 0

        self._build_static_ui()
        self.refresh()

    # ---------------- الهيكل الثابت (رأس الجدول + جسم قابل للسكرول الرأسي) ----------------

    def _build_static_ui(self):
        try:
            self._build_static_ui_inner()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_build_error(e)

    def _show_build_error(self, error):
        # لو أي خطأ حصل أثناء بناء الجدول، نوريه في مكانه بدل ما التاب يفضل
        # فاضي تمامًا من غير أي تفسير - عشان لو التطبيق شغال من غير نافذة
        # طرفية (console) العادي، الرسالة كانت هتضيع من غير ما حد يشوفها
        box = ctk.CTkFrame(self, fg_color="#FDECEC", corner_radius=10,
                            border_width=1, border_color=theme.DANGER)
        box.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(box, text="حصل خطأ أثناء عرض سجل المعالجات:",
                     font=(theme.CONTENT_FONT_FAMILY, 13, "bold"),
                     text_color=theme.DANGER, anchor="e").pack(
            anchor="e", padx=14, pady=(12, 2), fill="x")
        ctk.CTkLabel(box, text=f"{type(error).__name__}: {error}",
                     font=theme.FONT_SMALL, text_color=theme.TEXT_DARK,
                     anchor="e", justify="right", wraplength=700).pack(
            anchor="e", padx=14, pady=(0, 12), fill="x")

    def _build_static_ui_inner(self):
        card = ctk.CTkFrame(self, fg_color=theme.CARD_BG, corner_radius=8,
                             border_width=3, border_color=theme.HEADER_GRAD_END)
        card.pack(fill="both", expand=True)

        # ------- صف "الإجمالي" ثابت دايمًا أسفل الجدول (خارج منطقة
        # السكرول تمامًا)، فالسكرول الداخلي بقى خاص بصفوف البيانات بس -
        # بنبنيه الأول (side="bottom") عشان يحجز مكانه، وبعدين self._scroller
        # بياخد المساحة المتبقية فوقه (fill="both", expand=True) -------
        self._totals_bar = ctk.CTkFrame(card, fg_color=theme.CARD_BG, corner_radius=0)
        self._totals_bar.pack(fill="x", side="bottom", padx=3, pady=(0, 3))
        self._apply_columns(self._totals_bar)
        self._totals_bar.grid_rowconfigure(0, minsize=ROW_HEIGHT, weight=0)

        self._scroller = ctk.CTkScrollableFrame(card, fg_color=theme.CARD_BG, corner_radius=0)
        self._scroller.pack(fill="both", expand=True, padx=3, pady=3)

        # ------- جدول واحد بس (grid واحد) بيحتوي الهيدر وكل صفوف البيانات
        # وصفوف الفراغ الوهمية سوا. كل الأعمدة (بيانات + فواصل) بتتنسّق
        # مرة واحدة بس على self._table نفسه (_apply_columns)، فمفيش أي
        # احتمال يحصل اختلاف في عرض أي عمود بين الهيدر وأي صف تحته -------
        self._table = ctk.CTkFrame(self._scroller, fg_color=theme.CARD_BG, corner_radius=0)
        self._table.pack(fill="x")
        self._apply_columns(self._table)
        self._table.grid_rowconfigure(0, minsize=HEADER_HEIGHT, weight=0)

        # صف العناوين (row=0 من نفس الجدول) - خلايا متلاصقة بحد رفيع لكل
        # خلية (زي جدول المرضى الرئيسي بالظبط)، بلون خلفية متماشي مع الثيم
        ctk.CTkLabel(self._table, text="", height=HEADER_CELL_HEIGHT,
                     fg_color=theme.HEADER_GRAD_END, corner_radius=0,
                     border_width=1, border_color=GRID_LINE).grid(
            row=0, column=0, sticky="nsew")
        for i, (_key, label, _minsize, _weight, _kind) in enumerate(COLUMNS):
            ctk.CTkLabel(self._table, text=label, font=HEADER_FONT, height=HEADER_CELL_HEIGHT,
                         text_color="#FFFFFF", fg_color=theme.HEADER_GRAD_END,
                         corner_radius=0, border_width=1, border_color=GRID_LINE,
                         anchor="center").grid(
                row=0, column=_grid_col(i), sticky="nsew")

        # ------- خط سفلي مربوط بأسفل الجدول مباشرة بـplace (بدل pack) عشان
        # يفضل ظاهر دايمًا في نفس المكان مهما كان عدد الصفوف أو حجم المحتوى،
        # مش معتمد على ترتيب الحزم (pack) جوه المساحة المتبقية -------
        bottom_bar = ctk.CTkFrame(card, fg_color=theme.HEADER_GRAD_END, corner_radius=0,
                                   height=3)
        bottom_bar.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        # بنراقب عرض الـcanvas الداخلي الفعلي بتاع السكرول (ده هو نفسه العرض
        # اللي بتاخده كل الصفوف - بما فيهم صف العناوين دلوقتي)، وأي تغيير فيه
        # (بسبب سحب سايد بار الصور أو تغيير حجم الشاشة) بيعيد حساب عرض كل
        # عمود من واقع المساحة الفعلية المتاحة
        canvas = self._scroller._parent_canvas
        canvas.bind("<Configure>", self._on_canvas_configure, add="+")
        self.after(80, lambda: self._on_canvas_configure(None))
        self.after(400, lambda: self._on_canvas_configure(None))

    # ---------------- حساب/تطبيق عرض الأعمدة حسب المساحة المتاحة فعليًا ----------------

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
            # لسه المكوّنات ماترسمتش فعليًا، نجرب تاني بعد شوية
            self._resize_job = self.after(120, self._recompute_layout)
            return

        available = canvas_width - ACTION_COL_MINSIZE
        natural_sum = sum(minsize for _k, _l, minsize, _w, _kind in COLUMNS)
        scale = available / natural_sum if natural_sum > 0 else 1.0

        if scale >= 1.0:
            self._stretch_mode = True
            self._col_widths = {key: minsize for key, _l, minsize, _w, _k in COLUMNS}
        else:
            self._stretch_mode = False
            self._col_widths = {
                key: max(MIN_COL_FLOOR, int(minsize * scale))
                for key, _l, minsize, _w, _k in COLUMNS
            }

        # مصدر واحد بس لعرض الأعمدة - الجدول الواحد بتاعنا. تطبيقه هنا بيغيّر
        # عرض كل عمود في الهيدر وكل الصفوف تحته في نفس اللحظة، لأنهم كلهم
        # بيستخدموا نفس الأعمدة بالظبط (مفيش أي Frame تاني بيوزّع لوحده)
        self._apply_columns(self._table)
        # وصف "الإجمالي" الثابت لازم ياخد نفس عرض الأعمدة بالظبط برضه عشان
        # يفضل مظبوط تحت كل عمود
        self._apply_columns(self._totals_bar)

        self._sync_filler_rows()

    def _apply_columns(self, frame):
        frame.grid_columnconfigure(0, weight=0, minsize=ACTION_COL_MINSIZE)
        for i, (key, _label, _minsize, weight, _kind) in enumerate(COLUMNS):
            col = _grid_col(i)
            w = self._col_widths.get(key, _minsize)
            if self._stretch_mode:
                frame.grid_columnconfigure(col, weight=weight, minsize=w)
            else:
                frame.grid_columnconfigure(col, weight=0, minsize=w)

    # ---------------- أدوات صغيرة للوصول لخلية معيّنة جوه الجدول الواحد ----------------

    def _cell(self, row_index, col_index):
        slaves = self._table.grid_slaves(row=row_index, column=col_index)
        return slaves[0] if slaves else None

    def _reset_row_range(self, start_row, end_row):
        """بيصفّر حجز المساحة (rowconfigure) للصفوف اللي بين start_row و
        end_row عشان لو عدد الصفوف قلّ، الجدول ما يفضلش شايل مساحة فاضية
        محجوزة لصفوف مبقتش موجودة (وده كان بيسبب 'الترحيل الكبير')."""
        for r in range(start_row, end_row + 1):
            self._table.grid_rowconfigure(r, minsize=0, weight=0)

    # ---------------- تحديث/إعادة رسم الصفوف ----------------

    def refresh(self):
        if not hasattr(self, "_scroller"):
            # بناء الجدول نفسه فشل وبيوصلك رسالة الخطأ بدل الجدول، فمفيش
            # داعي نحاول نعمل refresh على حاجة مش موجودة
            return
        try:
            self._refresh_inner()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_build_error(e)

    def _refresh_inner(self):
        self._editing = None
        self._clear_body(full=True)

        records = db.get_treatment_records(self.patient_id)
        self._last_records = records
        self._render_totals_row()

        if not records:
            self._render_empty_row()
            self._real_row_count = 1
            self._max_row_used = 1
            self._sync_filler_rows()
            return

        self._doctor_names = [d["full_name"] for d in db.get_doctors()]

        for idx, record in enumerate(records):
            self._build_row(record, idx)
        self._real_row_count = len(records)
        self._max_row_used = self._real_row_count
        self._sync_filler_rows()

    def _render_empty_row(self):
        """لما مفيش أي معالجات، بدل ما نعرض جملة "لا توجد معالجات..."
        كنص منفصل بره الجدول (كان بيقطع استمرارية خطوط الشبكة)، بنعرضها
        كصف عادي جوه الجدول نفسه ممتد على كل الأعمدة، بنفس حدود وألوان
        باقي الصفوف - عشان شكل الجدول يفضل متصل ومتناسق تمامًا حتى لو
        فاضي، وصفوف الفراغ بعده تكمل نفس الرسم من غير أي انقطاع"""
        row_index = 1
        self._table.grid_rowconfigure(row_index, minsize=ROW_HEIGHT, weight=0)
        total_cols = len(COLUMNS) + 1
        lbl = ctk.CTkLabel(self._table, text="لا توجد معالجات مسجَّلة بعد", font=CELL_FONT,
                            text_color=theme.TEXT_MUTED, fg_color=theme.CARD_BG,
                            corner_radius=0, border_width=1, border_color=GRID_LINE,
                            anchor="center")
        lbl.grid(row=row_index, column=0, columnspan=total_cols, sticky="nsew")
        lbl._is_data_row = True

    # ---------------- صف "الإجمالي" الثابت أسفل الجدول ----------------

    def _render_totals_row(self):
        for w in list(self._totals_bar.winfo_children()):
            w.destroy()

        records = getattr(self, "_last_records", []) or []
        total_price = sum(float(r.get("price") or 0) for r in records)
        total_discount = sum(float(r.get("discount_amount") or 0) for r in records)
        total_net = total_price - total_discount
        total_paid = sum(float(r.get("paid_amount") or 0) for r in records)
        total_remaining = total_net - total_paid
        overall_percent = (total_discount / total_price * 100) if total_price > 0 else 0

        TOTALS_BG = theme.BG_MAIN

        def cell(col_index, text, color=theme.TEXT_DARK):
            ctk.CTkLabel(self._totals_bar, text=text, font=CELL_FONT_BOLD, height=ROW_HEIGHT,
                         text_color=color, fg_color=TOTALS_BG, corner_radius=0,
                         border_width=1, border_color=GRID_LINE, anchor="center").grid(
                row=0, column=col_index, sticky="nsew")

        cell(0, "")  # عمود الأكشن فاضي في صف الإجمالي
        for i, (key, _label, _minsize, _weight, _kind) in enumerate(COLUMNS):
            col = _grid_col(i)
            if key == "treatment_date":
                cell(col, "الإجمالي")
            elif key == "price":
                cell(col, _fmt_num(total_price))
            elif key == "discount_amount":
                cell(col, _fmt_num(total_discount), color=theme.WARNING)
            elif key == "discount_percent":
                cell(col, f"{overall_percent:.1f}%" if total_price else "-", color=theme.WARNING)
            elif key == "net":
                cell(col, _fmt_num(total_net))
            elif key == "paid_amount":
                cell(col, _fmt_num(total_paid), color=theme.SUCCESS)
            elif key == "remaining":
                cell(col, _fmt_num(total_remaining),
                     color=(theme.DANGER if total_remaining > 0 else theme.SUCCESS))
            else:
                cell(col, "")

    def _clear_body(self, full):
        """بيمسح محتوى جسم الجدول (صفوف البيانات + صفوف الفراغ الوهمية +
        الفواصل الرأسية بتاعتهم) وبيصفّر المساحة المحجوزة ليهم، من غير ما
        يلمس صف الهيدر (row=0) خالص. full=True بتمسح كل حاجة (بيانات
        وفراغ سوا، مستخدمة لما البيانات نفسها بتتغيّر)."""
        for w in list(self._table.winfo_children()):
            if getattr(w, "_is_filler", False) or (full and getattr(w, "_is_data_row", False)):
                w.destroy()

        if full:
            self._reset_row_range(1, max(self._max_row_used, 1))
            self._max_row_used = 0
        else:
            self._reset_row_range(self._real_row_count + 1, max(self._max_row_used, 1))
            self._max_row_used = self._real_row_count

    # ---------------- صفوف وهمية فاضية بتكمّل شكل الجدول لحد آخر مساحة ----------------
    # (عشان الجدول يبان "كامل" زي إكسل حتى لو مفيش بيانات كفاية تملاه، بدل
    # ما يفضل فراغ أبيض تحت آخر صف حقيقي)

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

        for i in range(target_filler):
            self._build_filler_row(real_count + i)

    def _build_filler_row(self, idx):
        row_index = idx + 1  # +1 عشان صف الهيدر واخد row=0
        self._table.grid_rowconfigure(row_index, minsize=ROW_HEIGHT, weight=0)
        self._max_row_used = max(self._max_row_used, row_index)
        row_bg = theme.CARD_BG if idx % 2 == 0 else theme.TAB_ACTIVE_GRAD_TOP

        action_cell = ctk.CTkFrame(self._table, fg_color=row_bg,
                                    width=ACTION_CELL_WIDTH, height=ROW_CELL_HEIGHT,
                                    corner_radius=0, border_width=1, border_color=GRID_LINE)
        action_cell.grid(row=row_index, column=0, sticky="nsew")
        action_cell._is_filler = True

        for i, (_key, _label, _minsize, _weight, _kind) in enumerate(COLUMNS):
            lbl = ctk.CTkLabel(self._table, text="", height=ROW_CELL_HEIGHT, fg_color=row_bg,
                                corner_radius=0, border_width=1, border_color=GRID_LINE)
            lbl.grid(row=row_index, column=_grid_col(i), sticky="nsew")
            lbl._is_filler = True

    # ---------------- بناء صف واحد ----------------

    def _build_row(self, record, idx):
        row_index = idx + 1  # +1 عشان صف الهيدر واخد row=0
        self._table.grid_rowconfigure(row_index, minsize=ROW_HEIGHT, weight=0)
        row_bg = theme.CARD_BG if idx % 2 == 0 else theme.TAB_ACTIVE_GRAD_TOP

        record_id = record["id"]

        action_cell = ctk.CTkFrame(self._table, fg_color=row_bg,
                                    width=ACTION_CELL_WIDTH, height=ROW_CELL_HEIGHT,
                                    corner_radius=0, border_width=1, border_color=GRID_LINE)
        action_cell.grid(row=row_index, column=0, sticky="nsew")
        action_cell.pack_propagate(False)
        action_cell._is_data_row = True
        self._render_delete_button(action_cell, record_id)

        net = float(record.get("price") or 0) - float(record.get("discount_amount") or 0)
        remaining = net - float(record.get("paid_amount") or 0)
        display_values = dict(record)
        display_values["net"] = net
        display_values["remaining"] = remaining
        # عمود "الاسنان" - رقم السن (+ الأسطح لو مسجَّلة)، أو "—" للبنود
        # اليدوية اللي مش جايه من شارت الأسنان (مفيهاش سن محدد)
        tooth_num = record.get("tooth_number")
        surfaces = record.get("surfaces")
        display_values["teeth"] = (f"{tooth_num}" + (f" ({surfaces})" if surfaces else "")
                                    if tooth_num else "—")

        for i, (key, _label, _minsize, _weight, kind) in enumerate(COLUMNS):
            self._render_cell_view(row_index, record, key, kind, display_values.get(key),
                                    grid_col=_grid_col(i), row_bg=row_bg)

    def _render_delete_button(self, action_cell, record_id):
        for w in action_cell.winfo_children():
            w.destroy()
        # لو المستخدم مالوش صلاحية تعديل الحسابات، عمود الحذف بيفضل فاضي
        if not self.can_edit:
            return

        # زرار حذف مربع (نفس الطول والعرض) بإطار أسود غير متماثل السُمك
        # (يمين وتحت 3 بيكسل، فوق وشمال بيكسل واحد) وعلامة X سودة جواه.
        # الحجم اتقلل 25% عن الشكل المستطيل اللي كان قبل كده.
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
        from tkinter import messagebox
        if not messagebox.askyesno(
                "تأكيد الحذف",
                "هل تريد حذف هذه المعالجة نهائيًا؟\n"
                "سيتم حذفها من شارت الأسنان ومن حساب المريض المالي معًا.",
                parent=self):
            return
        self._delete_record(record_id)

    def _delete_record(self, record_id):
        db.delete_treatment_record(record_id)
        self.refresh()
        if self.on_change:
            self.on_change()

    # ---------------- عرض قيمة الخلية (وضع القراءة) ----------------

    def _render_cell_view(self, row_index, record, key, kind, value, grid_col, row_bg):
        if kind == "computed":
            # القيمة/المدفوع/المتبقي كلهم بالأسود العادي زي باقي خلايا
            # الجدول - من غير تمييز بالأحمر/الأخضر
            text = _fmt_num(value)
            lbl = ctk.CTkLabel(self._table, text=text, font=CELL_FONT, height=ROW_CELL_HEIGHT,
                                text_color=theme.TEXT_DARK, fg_color=row_bg, anchor="center",
                                corner_radius=0, border_width=1, border_color=GRID_LINE)
            lbl.grid(row=row_index, column=grid_col, sticky="nsew")
            lbl._is_data_row = True
            return

        if kind == "lab":
            lbl = ctk.CTkLabel(self._table, text=(value or "—"), font=CELL_FONT, height=ROW_CELL_HEIGHT,
                                text_color=theme.TEXT_MUTED, fg_color=row_bg, anchor="center",
                                corner_radius=0, border_width=1, border_color=GRID_LINE)
            lbl.grid(row=row_index, column=grid_col, sticky="nsew")
            lbl._is_data_row = True
            return

        if kind == "teeth":
            # عمود للقراءة فقط - رقم السن بيتحدد من شارت الأسنان نفسه (أو
            # بند يدوي مفيهوش سن)، مش بيتعدّل من هنا عشان يفضل مطابق للشارت
            lbl = ctk.CTkLabel(self._table, text=(value or "—"), font=CELL_FONT, height=ROW_CELL_HEIGHT,
                                text_color=theme.TEXT_DARK, fg_color=row_bg, anchor="center",
                                corner_radius=0, border_width=1, border_color=GRID_LINE)
            lbl.grid(row=row_index, column=grid_col, sticky="nsew")
            lbl._is_data_row = True
            return

        if kind == "number":
            text = _fmt_num(value)
        elif kind == "percent":
            text = f"{_fmt_num(value)}%"
        elif kind == "date":
            text = value or "—"
        else:
            text = str(value).strip() if str(value or "").strip() else "—"

        lbl = ctk.CTkLabel(self._table, text=text, font=CELL_FONT, height=ROW_CELL_HEIGHT,
                            text_color=theme.TEXT_DARK,
                            fg_color=row_bg, anchor="center", cursor="hand2" if self.can_edit else "arrow",
                            corner_radius=0, border_width=1, border_color=GRID_LINE)
        lbl.grid(row=row_index, column=grid_col, sticky="nsew")
        lbl._is_data_row = True
        if self.can_edit:
            lbl.bind("<Button-1>", lambda e: self._start_edit(row_index, record, key, kind, grid_col, row_bg))

    # ---------------- الدخول في وضع التعديل ----------------

    def _start_edit(self, row_index, record, key, kind, grid_col, row_bg):
        if self._editing is not None:
            self._cancel_edit()

        action_cell = self._cell(row_index, 0)
        old_widget = self._cell(row_index, grid_col)
        cell_width = max(old_widget.winfo_width(), 60)
        old_widget.destroy()

        widget = self._make_edit_widget(record, key, kind, cell_width)
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
        self._render_confirm_cancel(action_cell)

    def _make_edit_widget(self, record, key, kind, cell_width):
        current = record.get(key)
        if kind == "date":
            w = DateAutoEntry(self._table, width=cell_width, height=EDIT_WIDGET_HEIGHT,
                               font=CELL_FONT, justify="center")
            if current:
                w.set_iso_date(current)
            w.bind("<Return>", lambda e: self._confirm_edit())
            w.bind("<Escape>", lambda e: self._cancel_edit())
            return w

        if kind == "doctor":
            values = list(self._doctor_names) or ["لا يوجد أطباء مسجلين"]
            if current and current not in values:
                values = [current] + values
            w = ctk.CTkOptionMenu(self._table, values=values, width=cell_width, height=EDIT_WIDGET_HEIGHT,
                                   font=CELL_FONT, **theme.optionmenu_colors())
            w.set(current or values[0])
            return w

        if kind in ("number", "percent"):
            w = ctk.CTkEntry(self._table, width=cell_width, height=EDIT_WIDGET_HEIGHT,
                              font=CELL_FONT, justify="center")
            w.insert(0, _fmt_num(current).replace(",", ""))
            w.bind("<Return>", lambda e: self._confirm_edit())
            w.bind("<Escape>", lambda e: self._cancel_edit())
            return w

        # text / notes
        w = RTLEntry(self._table, width=cell_width, height=EDIT_WIDGET_HEIGHT, font=CELL_FONT)
        if current:
            w.insert("1.0", str(current))
        w.bind("<Escape>", lambda e: self._cancel_edit())
        return w

    def _render_confirm_cancel(self, action_cell):
        for w in action_cell.winfo_children():
            w.destroy()
        wrap = ctk.CTkFrame(action_cell, fg_color="transparent", width=48, height=20)
        wrap.pack()
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
        self._render_cell_view(editing["row_index"], record, key, kind, record.get(key),
                                editing["grid_col"], editing["row_bg"])
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
            fields = {"treatment_date": new_value}

        elif kind == "doctor":
            fields = {"doctor_name": widget.get()}

        elif kind in ("number", "percent"):
            new_value = _to_float(widget.get())
            if new_value is None or new_value < 0:
                return
            fields = self._compute_linked_fields(record, key, new_value)

        else:  # text / notes
            try:
                text_value = widget.get("1.0", "end").strip()
            except Exception:
                text_value = ""
            fields = {key: text_value}

        db.update_treatment_record_fields(record["id"], **fields)
        self._editing = None
        self.refresh()
        if self.on_change:
            self.on_change()

    def _compute_linked_fields(self, record, key, new_value):
        """الخصم (مبلغ) والخصم (نسبة%) مترابطين وبيحدّثوا بعض تلقائي؛
        وتعديل القيمة بيحافظ على نسبة الخصم الحالية ويعيد حساب مبلغ الخصم."""
        price = float(record.get("price") or 0)

        if key == "price":
            percent = float(record.get("discount_percent") or 0)
            new_discount_amount = round(new_value * percent / 100, 2)
            return {"price": new_value, "discount_amount": new_discount_amount}

        if key == "discount_amount":
            new_percent = round((new_value / price) * 100, 2) if price > 0 else 0
            return {"discount_amount": new_value, "discount_percent": new_percent}

        if key == "discount_percent":
            new_amount = round(price * new_value / 100, 2) if price > 0 else 0
            return {"discount_percent": new_value, "discount_amount": new_amount}

        return {key: new_value}
