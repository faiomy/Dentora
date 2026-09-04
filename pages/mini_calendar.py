# -*- coding: utf-8 -*-
"""
كالندر شهري صغير لاختيار اليوم بسرعة (زي أي تقويم جانبي)
- ممكن تسحب حده الشمال بالماوس تكبر/تصغر بيه
- أيام الإجازة (الأسبوعية الثابتة أو المحددة بعينها) بتظهر بلون أحمر
"""

import calendar
import math
import os
import json
import locale
from datetime import date, timedelta
import customtkinter as ctk
import theme
import database as db

# بعض إعدادات ويندوز العربية (استبدال الأرقام بالأرقام الهندية ٠١٢٣) بتأثر
# على شكل الأرقام اللي بترسمها المكتبات الرسومية زي tkinter حتى لو النص نفسه
# مكتوب بأرقام إنجليزية عادية. بنجبر اللوكال يبقى إنجليزي/محايد عشان نضمن
# إن الأرقام تفضل تتكتب بالشكل الإنجليزي (0123) دايمًا.
try:
    locale.setlocale(locale.LC_ALL, "C")
except Exception:
    pass

AR_MONTHS = ["", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
             "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
# ترتيب زي ما بترجعها calendar.Calendar(firstweekday=0) يعني الاثنين أول يوم
AR_WEEKDAYS_FULL = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
AR_WEEKDAYS_SHORT = ["إث", "ثل", "أر", "خم", "جم", "سب", "أح"]

# حجم ثابت لكل خانة يوم (مش بيتغيّر حسب حجم الشاشة أو عدد الصفوف) - بنفس
# الفكرة اللي بتتحسب بيها الساعات في شارت المواعيد: قيمة ثابتة معروفة
# بدل تخمين ديناميكي كان بيغلط أحيانًا ويقطع آخر أسبوع في الشهر.
DAY_CELL = 25
DAY_CELL_GAP = 0
# حجم رقم اليوم - قلّلناه يتناسب مع حجم الخانة الجديد الأصغر (25) عشان
# الرقم يفضل واضح وميتقصّش، مع فضل مساحة كافية جوه الخانة نفسها
DAY_FONT_SIZE = 12
# أقل عرض للكالندر يمنع قطع أي عمود من الـ7 أعمدة (7 أيام) بمربعات بالحجم ده -
# وبرضو أقل عرض مسموح بيه لما تسحبي مقبض تغيير الحجم يدويًا، عشان متقدريش
# تصغريه لحد ما يقطع الأعمدة تاني
MIN_WIDTH = DAY_CELL * 7 + 40
MIN_CALENDAR_WIDTH = MIN_WIDTH
MAX_WIDTH = 420


class MiniCalendar(ctk.CTkFrame):
    def __init__(self, master, on_date_selected, on_width_changed=None, on_live_resize=None,
                 width=260, show_resize_handle=True, **kwargs):
        kwargs.pop("width", None)
        # أقل عرض ممكن يمنع قطع أي عمود من الـ7 أعمدة، بعد ما كبّرنا حجم
        # مربع اليوم - لو المستخدم كان محفوظ عنده عرض أصغر من نسخة قديمة
        width = max(width, MIN_CALENDAR_WIDTH)
        super().__init__(master, fg_color=theme.CARD_BG, corner_radius=12, width=width,
                          height=kwargs.pop("height", 300), **kwargs)
        self.pack_propagate(False)
        self.on_date_selected = on_date_selected
        self.on_width_changed = on_width_changed
        self.on_live_resize = on_live_resize
        # لما الكالندر ده يبقى جوه LinkedMiniCalendars (ميلادي + هجري مع
        # بعض)، مقبض السحب بيتعمل مرة واحدة بس في الحاوية الأب (عشان
        # يمتد بطول الكالندرين مع بعض)، فبنشيله من هنا فالحالة دي
        self.show_resize_handle = show_resize_handle
        self.view_year = date.today().year
        self.view_month = date.today().month
        self.selected_date = date.today()
        self._drag_start_x = None
        self._drag_start_width = None
        self._build()

    def _build(self):
        # مقبض السحب لتغيير الحجم - على الحافة الشمال (المتاخمة للشارت الرئيسي)
        if self.show_resize_handle:
            self.resize_handle = ctk.CTkFrame(self, width=6, fg_color=theme.BORDER, corner_radius=0,
                                               cursor="sb_h_double_arrow")
            self.resize_handle.pack(side="left", fill="y")
            self.resize_handle.bind("<Button-1>", self._on_drag_start)
            self.resize_handle.bind("<B1-Motion>", self._on_drag_motion)
            self.resize_handle.bind("<ButtonRelease-1>", self._on_drag_end)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="right", fill="both", expand=True)

        nav_row = ctk.CTkFrame(content, fg_color="transparent")
        nav_row.pack(fill="x", padx=8, pady=(8, 2))

        ctk.CTkButton(nav_row, text="«", width=24, height=26,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._prev_year).pack(side="left")
        ctk.CTkButton(nav_row, text="⟨", width=24, height=26,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._prev_month).pack(side="left", padx=(2, 0))

        ctk.CTkButton(nav_row, text="»", width=24, height=26,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._next_year).pack(side="right")
        ctk.CTkButton(nav_row, text="⟩", width=24, height=26,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._next_month).pack(side="right", padx=(0, 2))

        # اسم الشهر والسنة بين الأسهم في نفس الصف (بدل سطر لوحده تحتهم)
        # عشان يقلل المساحة الرأسية اللي الكالندر بياخدها
        self.month_label = ctk.CTkLabel(nav_row, text="", font=theme.FONT_NORMAL,
                                         text_color=theme.TEXT_DARK, cursor="hand2",
                                         anchor="center")
        self.month_label.pack(side="left", fill="x", expand=True, padx=4)
        self.month_label.bind("<Button-1>", lambda e: self._jump_today())

        # الشبكة نفسها (من غير سكرول فريم) - الارتفاع بيتحسب ديناميكيًا في
        # _apply_dynamic_height() بالظبط حسب عدد أسابيع الشهر، فمفيش داعي
        # لسكرول فريم أصلاً؛ وده كان بيسبب مشكلة إن آخر صف (الخامس) بيختفي
        # لأن مساحة عرض السكرول الداخلية كانت بتتجمد على قياس قديم
        self.grid_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=3, pady=(2, 6))
        # كل الأعمدة السبعة بنفس الوزن ونفس المجموعة، فـ tkinter نفسه بيقسم
        # المساحة المتاحة بالتساوي بينهم دايمًا - يعني الـ 7 أيام هتفضل ظاهرة
        # مهما ضاقت المساحة (بيصغروا كلهم مع بعض، مش بيتقطع حد منهم).
        for c in range(7):
            self.grid_frame.grid_columnconfigure(c, weight=1, uniform="wd")

        self._current_mode = "letter"
        self._render_grid()
        # لما الحجم الحقيقي يتحدد فعليًا بعد الرسم، نعيد اختيار حجم النص المناسب
        self.grid_frame.bind("<Configure>", self._on_grid_configure)

    # ---------------- تغيير الحجم بالسحب ----------------

    def _on_drag_start(self, event):
        self._drag_start_x = event.x_root
        self.update_idletasks()
        self._drag_start_width = self.winfo_width()

    def _on_drag_motion(self, event):
        if self._drag_start_x is None:
            return
        # السحب لليمين (بعيد عن الشارت الرئيسي) = تصغير، لليسار = تكبير
        moved = event.x_root - self._drag_start_x
        new_width = self._drag_start_width - moved
        new_width = max(MIN_WIDTH, min(MAX_WIDTH, new_width))
        self.configure(width=new_width)
        self._render_grid()
        if self.on_live_resize:
            self.on_live_resize(new_width)

    def _on_drag_end(self, event):
        self._drag_start_x = None
        self.update_idletasks()
        final_width = self.winfo_width()
        if self.on_width_changed:
            self.on_width_changed(final_width)

    # ---------------- التنقل بين الشهور ----------------

    def _prev_month(self):
        self.view_month -= 1
        if self.view_month == 0:
            self.view_month = 12
            self.view_year -= 1
        self._render_grid()

    def _next_month(self):
        self.view_month += 1
        if self.view_month == 13:
            self.view_month = 1
            self.view_year += 1
        self._render_grid()

    def _prev_year(self):
        self.view_year -= 1
        self._render_grid()

    def _next_year(self):
        self.view_year += 1
        self._render_grid()

    def _jump_today(self):
        self.jump_to(date.today())
        if self.on_date_selected:
            self.on_date_selected(date.today())

    def jump_to(self, d: date):
        self.selected_date = d
        self.view_year = d.year
        self.view_month = d.month
        self._render_grid()

    def refresh_holidays(self):
        """يستخدم لما تتغير إعدادات الإجازات عشان الألوان تتحدث"""
        self._render_grid()

    def _on_grid_configure(self, event):
        new_mode = self._pick_mode(event.width)
        if new_mode != self._current_mode:
            self._current_mode = new_mode
            self._render_grid()

    @staticmethod
    def _pick_mode(total_width):
        col_w = (total_width / 7) if total_width and total_width > 0 else 0
        if col_w >= 64:
            return "full"
        elif col_w >= 34:
            return "short"
        return "letter"

    # ---------------- الرسم ----------------

    def _render_grid(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        self.month_label.configure(text=f"{AR_MONTHS[self.view_month]} {self.view_year}")

        mode = getattr(self, "_current_mode", "letter")
        use_full_names = mode == "full"
        use_short_names = mode == "short"
        header_font_size = 12 if use_full_names else 11
        day_btn_size = DAY_CELL

        weekly_holidays = db.get_weekly_holidays()
        holiday_dates = db.get_holiday_dates()

        # بنعمل الأعمدة السبعة دايمًا مهما كان الوضع - العمود بياخد المساحة
        # اللي الـ uniform حددها له، مش أكتر، فمينفعش يتقطع أو يختفي.
        for i in range(7):
            if use_full_names:
                wd_text = AR_WEEKDAYS_FULL[i]
            elif use_short_names:
                wd_text = AR_WEEKDAYS_SHORT[i]
            else:
                wd_text = AR_WEEKDAYS_SHORT[i][0]
            is_weekly_holiday = i in weekly_holidays
            lbl = ctk.CTkLabel(self.grid_frame, text=wd_text,
                         font=(theme.CONTENT_FONT_FAMILY, header_font_size, "bold" if is_weekly_holiday else "normal"),
                         text_color=theme.DANGER if is_weekly_holiday else theme.TEXT_MUTED,
                         width=1)
            lbl.grid(row=0, column=6 - i, pady=(0, 2), sticky="nsew")

        cal = calendar.Calendar(firstweekday=0)  # الإثنين أول يوم
        weeks = cal.monthdayscalendar(self.view_year, self.view_month)
        today = date.today()

        for r, week in enumerate(weeks, start=1):
            for c, day_num in enumerate(week):
                if day_num == 0:
                    continue
                this_date = date(self.view_year, self.view_month, day_num)
                is_today = this_date == today
                is_selected = this_date == self.selected_date
                is_holiday = (c in weekly_holidays) or (this_date.isoformat() in holiday_dates)

                fg = theme.CARD_BG
                text_color = theme.DANGER if is_holiday else theme.TEXT_DARK
                if is_selected:
                    fg = theme.PRIMARY_LIGHT
                    text_color = "#FFFFFF"
                elif is_today:
                    fg = theme.BG_MAIN
                    text_color = theme.PRIMARY_LIGHT if not is_holiday else theme.DANGER

                btn = ctk.CTkButton(
                    self.grid_frame, text=str(day_num), width=day_btn_size, height=day_btn_size,
                    corner_radius=10, border_spacing=0,
                    # بنستخدم "Segoe UI" هنا تحديدًا (مش خط المحتوى المختار
                    # من الإعدادات) لأن بعض الخطوط العربية مالهاش أرقام بولد
                    # كاملة فويندوز بيستبدلها برموز غلط بدل الأرقام
                    font=("Segoe UI", DAY_FONT_SIZE, "bold"),
                    fg_color=fg, text_color=text_color,
                    hover_color=theme.lighten_color(theme.PRIMARY_LIGHT, 0.75),
                    command=lambda d=this_date: self._select(d)
                )
                btn.grid(row=r, column=6 - c, pady=0, padx=0, sticky="nsew")

        # بنحسب الارتفاع المطلوب تلقائيًا حسب عدد أسابيع الشهر الفعلي (4 أو 5
        # أو 6 صفوف) - بالظبط زي ما بنحسب عرض عمود اليوم في شارت المواعيد
        # حسب عدد الأيام المعروضة، بدل ما نحجز ارتفاع ثابت أكبر من اللازم
        self._apply_dynamic_height(len(weeks))

    def _apply_dynamic_height(self, rows):
        self.last_rows_count = rows
        nav_h = 38
        weekday_row_h = 20
        rows_h = rows * (DAY_CELL + DAY_CELL_GAP)
        # هامش أمان إضافي عشان آخر صف (خصوصًا في الشهور اللي فيها 6 أسابيع)
        # ميختفيش لو التقدير كان أقل من المساحة الحقيقية بشوية
        padding = 34
        self.configure(height=nav_h + weekday_row_h + rows_h + padding)

    def _select(self, d):
        self.selected_date = d
        self._render_grid()
        if self.on_date_selected:
            self.on_date_selected(d)


# ==================== التقويم الهجري ====================
# بنستخدم خوارزمية حسابية معروفة (Kuwaiti Algorithm / التقويم الهجري الجدولي)
# لتحويل التاريخ من ميلادي لهجري والعكس، من غير أي مكتبات خارجية.
# التاريخ الهجري بيختلف أحيانًا يوم أو يومين حسب رؤية الهلال من بلد لبلد،
# فمُتاح تعديل يدوي (إزاحة بالأيام) بتتحفظ في ملف صغير جنب البرنامج.

HIJRI_MONTHS = ["", "محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة",
                "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]

_HIJRI_OFFSET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hijri_offset.json")
_CALENDAR_PREFS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mini_calendar_prefs.json")


def _load_calendar_prefs():
    try:
        with open(_CALENDAR_PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {"width": int(data.get("width", 260)), "size_scale": float(data.get("size_scale", 1.0))}
    except Exception:
        return {"width": 260, "size_scale": 1.0}


def _save_calendar_prefs(width, size_scale):
    try:
        with open(_CALENDAR_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump({"width": int(width), "size_scale": float(size_scale)}, f)
    except Exception:
        pass


def _load_hijri_offset():
    try:
        with open(_HIJRI_OFFSET_FILE, "r", encoding="utf-8") as f:
            return int(json.load(f).get("offset", 0))
    except Exception:
        return 0


def _save_hijri_offset(offset):
    try:
        with open(_HIJRI_OFFSET_FILE, "w", encoding="utf-8") as f:
            json.dump({"offset": int(offset)}, f)
    except Exception:
        pass


_HIJRI_OFFSET = _load_hijri_offset()


def get_hijri_offset():
    return _HIJRI_OFFSET


def set_hijri_offset(new_offset):
    global _HIJRI_OFFSET
    _HIJRI_OFFSET = int(new_offset)
    _save_hijri_offset(_HIJRI_OFFSET)


def _gregorian_to_jdn(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _jdn_to_gregorian(jdn):
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def _jdn_to_hijri(jdn):
    ell = jdn - 1948440 + 10632
    n = (ell - 1) // 10631
    ell = ell - 10631 * n + 354
    j = ((10985 - ell) // 5316) * ((50 * ell) // 17719) + (ell // 5670) * ((43 * ell) // 15238)
    ell = ell - ((30 - j) // 15) * ((17719 * j) // 50) - (j // 16) * ((15238 * j) // 43) + 29
    m = (24 * ell) // 709
    d = ell - (709 * m) // 24
    y = 30 * n + j - 30
    return y, m, d


def _hijri_to_jdn(y, m, d):
    # تقدير مبدئي بمتوسط طول السنة والشهر الهجري، وبعدين بحث محلي بسيط
    # حوالين التقدير عشان نلاقي الـ jdn اللي بيرجع بالظبط نفس التاريخ لما
    # نحوله بالدالة التانية (jdn_to_hijri) المتأكد إنها صحيحة. الطريقة دي
    # أضمن من صيغة حسابية مباشرة ممكن يكون فيها خطأ.
    approx = int((y - 1) * 354.36707 + (m - 1) * 29.5305882 + d + 1948439.5)
    for delta in range(-5, 6):
        candidate = approx + delta
        cy, cm, cd = _jdn_to_hijri(candidate)
        if (cy, cm, cd) == (y, m, d):
            return candidate
    return approx  # احتياطي (عمليًا مايحصلش لإن البحث فوق بيغطي هامش كافي


def gregorian_to_hijri(g_date):
    jdn = _gregorian_to_jdn(g_date.year, g_date.month, g_date.day) + _HIJRI_OFFSET
    return _jdn_to_hijri(jdn)


def hijri_to_gregorian(hy, hm, hd):
    jdn = _hijri_to_jdn(hy, hm, hd) - _HIJRI_OFFSET
    y, m, d = _jdn_to_gregorian(jdn)
    return date(y, m, d)


class HijriMiniCalendar(ctk.CTkFrame):
    """كالندر شهري صغير بالتاريخ الهجري - نفس شكل الكالندر الميلادي بالظبط"""

    def __init__(self, master, on_date_selected=None, width=260, **kwargs):
        kwargs.pop("width", None)
        width = max(width, MIN_CALENDAR_WIDTH)
        super().__init__(master, fg_color=theme.CARD_BG, corner_radius=12, width=width,
                          height=kwargs.pop("height", 300), **kwargs)
        self.pack_propagate(False)
        self.on_date_selected = on_date_selected
        self.selected_date = date.today()
        hy, hm, _ = gregorian_to_hijri(self.selected_date)
        self.view_hijri_year = hy
        self.view_hijri_month = hm
        self._build()

    def _build(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)

        nav_row = ctk.CTkFrame(content, fg_color="transparent")
        nav_row.pack(fill="x", padx=8, pady=(8, 0))

        ctk.CTkButton(nav_row, text="«", width=24, height=26,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._prev_year).pack(side="left")
        ctk.CTkButton(nav_row, text="⟨", width=24, height=26,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._prev_month).pack(side="left", padx=(2, 0))

        ctk.CTkButton(nav_row, text="✎", width=24, height=26, fg_color=theme.BG_MAIN,
                      text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._open_edit_dialog).pack(side="right")
        ctk.CTkButton(nav_row, text="»", width=24, height=26,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._next_year).pack(side="right", padx=(0, 2))
        ctk.CTkButton(nav_row, text="⟩", width=24, height=26,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG,
                      command=self._next_month).pack(side="right", padx=(0, 2))

        self.month_label = ctk.CTkLabel(nav_row, text="", font=theme.FONT_NORMAL,
                                         text_color=theme.TEXT_DARK, anchor="center")
        self.month_label.pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkLabel(content, text="التقويم الهجري", font=theme.FONT_MINI_CAL_LABEL,
                     text_color=theme.TEXT_MUTED).pack(pady=(0, 2))

        # نفس الحل بالظبط زي الكالندر الميلادي: من غير سكرول فريم، ومعتمدين
        # على الارتفاع المحسوب ديناميكيًا عشان الشهر يظهر كامل دايمًا
        self.grid_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=3, pady=(1, 4))
        for c in range(7):
            self.grid_frame.grid_columnconfigure(c, weight=1, uniform="hwd")

        self._current_mode = "letter"
        self._render_grid()
        self.grid_frame.bind("<Configure>", self._on_grid_configure)

    # ---------------- التنقل ----------------

    def _prev_month(self):
        self.view_hijri_month -= 1
        if self.view_hijri_month == 0:
            self.view_hijri_month = 12
            self.view_hijri_year -= 1
        self._render_grid()

    def _next_month(self):
        self.view_hijri_month += 1
        if self.view_hijri_month == 13:
            self.view_hijri_month = 1
            self.view_hijri_year += 1
        self._render_grid()

    def _prev_year(self):
        self.view_hijri_year -= 1
        self._render_grid()

    def _next_year(self):
        self.view_hijri_year += 1
        self._render_grid()

    def jump_to(self, g_date):
        """بتستقبل تاريخ ميلادي وبتعرض الشهر الهجري المقابل ليه"""
        self.selected_date = g_date
        hy, hm, _ = gregorian_to_hijri(g_date)
        self.view_hijri_year = hy
        self.view_hijri_month = hm
        self._render_grid()

    def _on_grid_configure(self, event):
        new_mode = MiniCalendar._pick_mode(event.width)
        if new_mode != self._current_mode:
            self._current_mode = new_mode
            self._render_grid()

    # ---------------- الرسم ----------------

    def _render_grid(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        self.month_label.configure(text=f"{HIJRI_MONTHS[self.view_hijri_month]}  {self.view_hijri_year} هـ")

        day_btn_size = DAY_CELL

        # من غير صف أسماء أيام الأسبوع هنا - أسماء الأيام ظاهرة فوق في
        # الكالندر الميلادي المتراكب معاه، فمفيش داعي نكررها تاني

        # أول يوم في الشهر الهجري الحالي (بالتاريخ الميلادي المقابل)
        first_greg = hijri_to_gregorian(self.view_hijri_year, self.view_hijri_month, 1)
        # بنجرب يوم 30: لو لسه في نفس الشهر يبقى الشهر 30 يوم، غير كده 29
        test_greg = hijri_to_gregorian(self.view_hijri_year, self.view_hijri_month, 30)
        _, hm2, _ = gregorian_to_hijri(test_greg)
        days_in_month = 30 if hm2 == self.view_hijri_month else 29

        start_weekday = first_greg.weekday()  # 0 = الاثنين
        today = date.today()
        weekly_holidays = db.get_weekly_holidays()
        holiday_dates = db.get_holiday_dates()
        hm = self.view_hijri_month

        row = 0
        col = start_weekday
        for day_num in range(1, days_in_month + 1):
            this_greg = first_greg + timedelta(days=day_num - 1)
            is_today = this_greg == today
            is_selected = this_greg == self.selected_date

            is_eid = (hm == 10 and day_num in (1, 2, 3)) or (hm == 12 and day_num in (10, 11, 12, 13))
            is_ashura = hm == 1 and day_num == 10
            is_new_year = hm == 1 and day_num == 1
            is_mawlid = hm == 3 and day_num == 12
            is_ramadan = hm == 9
            is_holiday = (this_greg.weekday() in weekly_holidays) or (this_greg.isoformat() in holiday_dates)

            # ألوان المناسبات - بترتيب أولوية:
            # عيد > عاشوراء > رأس السنة > المولد النبوي > رمضان > إجازة عادية
            fg = theme.CARD_BG
            text_color = theme.TEXT_DARK
            if is_eid:
                fg = "#FFB300"
                text_color = "#5C3D00"
            elif is_ashura:
                fg = "#8E24AA"
                text_color = "#FFFFFF"
            elif is_new_year:
                fg = "#3949AB"
                text_color = "#FFFFFF"
            elif is_mawlid:
                fg = "#00897B"
                text_color = "#FFFFFF"
            elif is_ramadan:
                fg = "#43A047"
                text_color = "#FFFFFF"
            elif is_holiday:
                text_color = theme.DANGER

            border_width = 0
            border_color = theme.CARD_BG
            if is_selected:
                fg = theme.PRIMARY_LIGHT
                text_color = "#FFFFFF"
            if is_today:
                # علامة واضحة لليوم الحالي الفعلي (نفس اليوم في الكالندر
                # الميلادي) - حلقة بلون الثيم المميز حوالين الرقم فوق أي لون تاني
                border_width = 2
                border_color = theme.darken_color(theme.PRIMARY_LIGHT, 0.7) if is_selected else theme.PRIMARY_LIGHT

            btn = ctk.CTkButton(
                self.grid_frame, text=str(day_num), width=day_btn_size, height=day_btn_size,
                corner_radius=10, border_spacing=0,
                font=("Segoe UI", DAY_FONT_SIZE, "bold"),
                fg_color=fg, text_color=text_color,
                border_width=border_width, border_color=border_color,
                hover_color=theme.lighten_color(theme.PRIMARY_LIGHT, 0.75),
                command=lambda d=this_greg: self._select(d)
            )
            btn.grid(row=row, column=6 - col, pady=0, padx=0, sticky="nsew")

            col += 1
            if col > 6:
                col = 0
                row += 1

        total_rows = math.ceil((start_weekday + days_in_month) / 7)
        self._apply_dynamic_height(total_rows, day_btn_size)

    def _apply_dynamic_height(self, rows, day_btn_size):
        self.last_rows_count = rows
        nav_h = 38
        subtitle_h = 20
        rows_h = rows * (day_btn_size + 2)
        padding = 32
        self.configure(height=nav_h + subtitle_h + rows_h + padding)

    def _select(self, g_date):
        self.selected_date = g_date
        self._render_grid()
        if self.on_date_selected:
            self.on_date_selected(g_date)

    # ---------------- التعديل اليدوي ----------------

    def _open_edit_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("تعديل التاريخ الهجري")
        dialog.geometry("320x280")
        dialog.grab_set()

        today_hy, today_hm, today_hd = gregorian_to_hijri(date.today())

        ctk.CTkLabel(dialog, text="التاريخ الهجري الصحيح للنهاردة", font=theme.FONT_NORMAL,
                     wraplength=280).pack(pady=(18, 4))
        ctk.CTkLabel(dialog, text="(لو مختلف عن اللي ظاهر عندك بسبب رؤية الهلال)",
                     font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                     wraplength=280).pack(pady=(0, 14))

        row = ctk.CTkFrame(dialog, fg_color="transparent")
        row.pack(pady=6)

        year_entry = ctk.CTkEntry(row, width=64, height=36, justify="center", font=theme.FONT_NORMAL)
        year_entry.insert(0, str(today_hy))
        year_entry.pack(side="right", padx=4)

        month_menu = ctk.CTkOptionMenu(row, values=HIJRI_MONTHS[1:], width=120,
                                        **theme.optionmenu_colors())
        month_menu.set(HIJRI_MONTHS[today_hm])
        month_menu.pack(side="right", padx=4)

        day_entry = ctk.CTkEntry(row, width=50, height=36, justify="center", font=theme.FONT_NORMAL)
        day_entry.insert(0, str(today_hd))
        day_entry.pack(side="right", padx=4)

        error_label = ctk.CTkLabel(dialog, text="", font=theme.FONT_SMALL, text_color=theme.DANGER)
        error_label.pack(pady=(8, 0))

        def save():
            try:
                new_day = int(day_entry.get().strip())
                new_year = int(year_entry.get().strip())
                new_month = HIJRI_MONTHS.index(month_menu.get())
                if not (1 <= new_day <= 30):
                    raise ValueError
            except (ValueError, TypeError):
                error_label.configure(text="⚠ تأكدي إن اليوم والسنة أرقام صحيحة")
                return
            entered_jdn = _hijri_to_jdn(new_year, new_month, new_day)
            today_base_jdn = _gregorian_to_jdn(date.today().year, date.today().month, date.today().day)
            set_hijri_offset(entered_jdn - today_base_jdn)
            dialog.destroy()
            self.jump_to(self.selected_date)

        ctk.CTkButton(dialog, text="حفظ التعديل", height=42, fg_color=theme.SUCCESS,
                      hover_color=theme.lighten_color(theme.SUCCESS, 0.15),
                      font=theme.FONT_NORMAL, command=save).pack(padx=24, pady=18, fill="x")


class LinkedMiniCalendars(ctk.CTkFrame):
    """كالندر ميلادي فوق + كالندر هجري تحته، مربوطين ببعض بالكامل:
    - اختيار يوم في أي واحد فيهم بيحدّث التاني ليعرض نفس اليوم
    - تكبير/تصغير العرض (يمين/شمال) بيتطبق على الاتنين مع بعض لحظيًا
    - حجم خانة اليوم ثابت (زي فكرة تقسيمة الساعات في شارت المواعيد) عشان
      الشهر يظهر كامل دايمًا من غير تخمين؛ ولو المساحة المتاحة على الشاشة
      لسه مش كفاية، كل كالندر فيه سكرول داخلي حقيقي بدل ما يتقطع"""

    def __init__(self, master, on_date_selected=None, on_width_changed=None, width=260, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_date_selected = on_date_selected
        self.on_width_changed = on_width_changed
        width = max(width, MIN_CALENDAR_WIDTH)
        self.current_width = width
        self._drag_start_x = None
        self._drag_start_width = None

        # مقبض سحب واحد بس هنا (مش جوه كل كالندر لوحده)، وبيمتد بطول
        # الكالندرين الاتنين (الميلادي + الهجري) مع بعض من فوق لتحت،
        # مش الكالندر الميلادي بس زي ما كان قبل كده
        self.resize_handle = ctk.CTkFrame(self, width=6, fg_color=theme.BORDER, corner_radius=0,
                                           cursor="sb_h_double_arrow")
        self.resize_handle.pack(side="left", fill="y")
        self.resize_handle.bind("<Button-1>", self._on_drag_start)
        self.resize_handle.bind("<B1-Motion>", self._on_drag_motion)
        self.resize_handle.bind("<ButtonRelease-1>", self._on_drag_end)

        calendars_col = ctk.CTkFrame(self, fg_color="transparent")
        calendars_col.pack(side="right", fill="both", expand=True)

        # الكالندر الميلادي فوق - من غير مقبض سحب خاص بيه (بقى بره في
        # الحاوية دي)، ومن غير fill="x" عشان يتحكم في عرضه بنفسه
        self.greg_cal = MiniCalendar(calendars_col, on_date_selected=self._on_greg_pick,
                                      show_resize_handle=False, width=width)
        self.greg_cal.pack(side="top")

        self.hijri_cal = HijriMiniCalendar(calendars_col, on_date_selected=self._on_hijri_pick, width=width)
        self.hijri_cal.pack(side="top", pady=(8, 0))

    # ---------------- الربط بين الكالندرين ----------------

    def _on_greg_pick(self, d):
        self.hijri_cal.jump_to(d)
        if self.on_date_selected:
            self.on_date_selected(d)

    def _on_hijri_pick(self, d):
        self.greg_cal.jump_to(d)
        if self.on_date_selected:
            self.on_date_selected(d)

    def jump_to(self, d):
        self.greg_cal.jump_to(d)
        self.hijri_cal.jump_to(d)

    def refresh_holidays(self):
        self.greg_cal.refresh_holidays()

    # ---------------- التحكم في العرض (يمين/شمال) ----------------
    # المقبض بقى هنا في الحاوية الأب، فمنطق السحب بقى هنا برضو (بدل ما
    # كان جوه الكالندر الميلادي وبيبلّغ التاني عن طريق on_live_resize)

    def _on_drag_start(self, event):
        self._drag_start_x = event.x_root
        self.update_idletasks()
        self._drag_start_width = self.current_width

    def _on_drag_motion(self, event):
        if self._drag_start_x is None:
            return
        # السحب لليمين (بعيد عن الشارت الرئيسي) = تصغير، لليسار = تكبير
        moved = event.x_root - self._drag_start_x
        new_width = self._drag_start_width - moved
        new_width = max(MIN_WIDTH, min(MAX_WIDTH, new_width))
        self.current_width = new_width
        self.greg_cal.configure(width=new_width)
        self.greg_cal._render_grid()
        self.hijri_cal.configure(width=new_width)
        self.hijri_cal._render_grid()

    def _on_drag_end(self, event):
        self._drag_start_x = None
        self.update_idletasks()
        final_width = self.current_width
        if self.on_width_changed:
            self.on_width_changed(final_width)

    # ---------------- الحفظ ----------------

    def save_size(self):
        """بتحفظ عرض الكالندرين الحالي - بتتنادى من زرار حفظ عدد الأيام
        في صفحة المواعيد (نفس الزرار بقى بيحفظ الاتنين مع بعض)"""
        _save_calendar_prefs(self.current_width, 1.0)
        if self.on_width_changed:
            self.on_width_changed(self.current_width)
