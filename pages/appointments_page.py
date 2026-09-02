# -*- coding: utf-8 -*-
"""
صفحة المواعيد - عرض تقويم بالساعات (زي جوجل كالندر):
- هيدر ثابت فوق (أسماء وتواريخ الأيام) مبيتحركش مع سكرول الساعات تحته
- جدول واحد (Canvas واحد) فيه عمود الوقت الثابت + كل أعمدة الأيام، بفواصل
  واضحة بين كل عمود والتاني
- خطوط الساعة الكاملة (زي 13:00) أغمق وأوضح من خطوط نص الساعة (13:30)
- عرض الهيدر وعرض الجدول بيتحسبوا من دالة واحدة بس (_compute_columns_layout)
  عشان يفضلوا متظبطين فوق بعض بالظبط مهما كان عدد الأيام (من 1 لحد 7)
- خط أحمر بيوضح الوقت الحالي فعلياً
- كالندر شهري صغير على اليمين لاختيار اليوم بسرعة
"""

import os
import json
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
from datetime import date, datetime, timedelta

import theme
import database as db
import whatsapp_sender as wa_sender
from pages.rtl_entry import RTLEntry
from pages.mini_calendar import MiniCalendar, LinkedMiniCalendars
from pages.time_auto_entry import TimeAutoEntry

WEEKDAY_NAMES = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

HOUR_HEIGHT = 43
DIVIDER_COLOR = "#AEB6C2"
ARABIC_MONTHS = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

# تفضيل عدد الأيام المعروضة (1 لحد 7) بيتحفظ في ملف صغير جنب البرنامج عشان
# يفضل زي ما هو لما البرنامج يتقفل ويتفتح تاني
_APPT_PREFS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appointments_prefs.json")


def _load_appt_prefs():
    try:
        with open(_APPT_PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {"days_count": int(data.get("days_count", 7))}
    except Exception:
        return {"days_count": 7}


def _save_appt_prefs(days_count):
    try:
        with open(_APPT_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump({"days_count": int(days_count)}, f)
    except Exception:
        pass


def _format_day_month(d):
    """بيرجع التاريخ بصيغة 'رقم اليوم + اسم الشهر' زي '7 يوليو' بدل '07/07'"""
    return f"{d.day} {ARABIC_MONTHS[d.month - 1]}"


class AppointmentsPage(ctk.CTkFrame):
    # عرض شريط التمرير الرأسي - رقم ثابت إحنا اللي بنحدده (مش بنخمنه)، وبنفس
    # الرقم ده بنحجز مساحة مطابقة فوق في الهيدر عشان يفضلوا متزبطين مع بعض
    SCROLLBAR_WIDTH = 18
    # عرض عمود الساعات (ثابت دايمًا، مبيتقصش أو يختفي مهما زاد عدد الأيام،
    # لإنه جزء أساسي من معادلة حساب المساحة المتاحة نفسها)
    TIME_COL_WIDTH = 60
    # عرض الفاصل الظاهر بين كل عمود يوم والتاني (وبين آخر عمود وعمود الوقت)
    DIVIDER_WIDTH = 6
    # سُمك الخط الأسود تحت الهيدر (بيملا الفراغ بين الهيدر والجدول)
    HEADER_BORDER_HEIGHT = 3
    # ارتفاع صف الهيدر (أسماء وتواريخ الأيام)
    HEADER_HEIGHT = 40

    def __init__(self, master, current_user=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_user = current_user
        self.start_date = date.today()
        self.days_count = _load_appt_prefs()["days_count"]
        self.doctor_filter = None
        self.start_hour = 0
        self.end_hour = 24
        self._current_layout = None
        self._current_days = []
        self._time_col_range = None
        self._header_embedded_widgets = []
        self._build()
        self._start_time_ticker()
        # بنحاول أكتر من مرة بفواصل زمنية مختلفة عشان نضمن إن الصفحة تكون
        # اترسمت فعليًا على الشاشة قبل ما نحسب مكان التمرير (أول مرة بتفتح
        # فيها الصفحة أحيانًا بتاخد وقت أطول شوية عشان تترسم بالكامل)
        # وبنعيد استدعاء refresh() نفسها كمان (مش بس تحديد مكان السكرول) عشان
        # لو النافذة كانت لسه بتتكبّر (Full Screen) وقت أول رسم، الحساب يتصلّح
        # تلقائيًا على الحجم النهائي الصحيح من غير ما نحتاج نتفاعل يدويًا
        self.after(150, self.refresh)
        self.after(600, self.refresh)
        self.after(150, self._scroll_to_now)
        self.after(500, self._scroll_to_now)
        self.after(150, self._update_now_lines)
        self.after(500, self._update_now_lines)

    # ---------------- بناء الواجهة ----------------

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="المواعيد", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(side="right", anchor="n")
        theme.make_shadowed_button(
            header, "+ موعد جديد", command=lambda: self.open_appointment_dialog(),
            width=140, height=38, fg_color=theme.ACCENT_BORDER, font=theme.FONT_NORMAL,
            canvas_bg=theme.BG_MAIN).pack(side="left")

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 10))

        theme.make_shadowed_button(
            controls, "اليوم", command=self._go_today, width=72, height=27,
            fg_color=theme.ACCENT_BORDER, font=theme.FONT_TABLE_NAV_BUTTON,
            canvas_bg=theme.BG_MAIN).pack(side="right", padx=4)

        # أزرار عدد الأيام (1 لحد 7) بدل القايمة المنسدلة
        days_row = ctk.CTkFrame(controls, fg_color=theme.BG_MAIN, corner_radius=8)
        days_row.pack(side="right", padx=10)
        ctk.CTkLabel(days_row, text="أيام:", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(side="right", padx=(8, 2))
        self.day_count_buttons = {}
        for n in range(1, 8):
            btn = ctk.CTkButton(days_row, text=str(n), width=30, height=30, corner_radius=6,
                                 font=theme.FONT_SMALL,
                                 fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
                                 border_width=1, border_color=theme.BORDER,
                                 command=lambda n=n: self._on_days_button(n))
            btn.pack(side="right", padx=2, pady=4)
            self.day_count_buttons[n] = btn

        self.save_days_btn = ctk.CTkButton(
            days_row, text="💾", width=28, height=28, corner_radius=6,
            font=theme.FONT_SMALL, fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
            border_width=1, border_color=theme.BORDER, hover_color=theme.BG_MAIN,
            command=self._save_days_pref)
        self.save_days_btn.pack(side="right", padx=(6, 4), pady=4)

        # فلتر الطبيب
        doctors = db.get_doctors()
        doctor_names = ["كل الأطباء"] + [d["full_name"] for d in doctors]
        self.doctor_filter_menu = ctk.CTkOptionMenu(controls, values=doctor_names, width=160,
                                                      font=theme.FONT_NORMAL,
                                                      command=self._on_doctor_filter_change,
                                                      **theme.optionmenu_colors())
        self.doctor_filter_menu.set("كل الأطباء")
        self.doctor_filter_menu.pack(side="right", padx=10)

        self.range_label = ctk.CTkLabel(controls, text="", font=theme.FONT_SUBTITLE,
                                         text_color=theme.TEXT_DARK)
        self.range_label.pack(side="left", padx=10)

        # الجسم: الشارت الرئيسي على الشمال + الكالندر الشهري على اليمين
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        self.body = body

        self.mini_cal = LinkedMiniCalendars(body, on_date_selected=self._on_mini_calendar_pick,
                                             on_width_changed=self._on_mini_cal_width_changed,
                                             width=db.get_settings()["mini_calendar_width"])
        self.mini_cal.pack(side="right", padx=(10, 0), fill="y")

        main_col = ctk.CTkFrame(body, fg_color="transparent")
        main_col.pack(side="right", fill="both", expand=True)
        self.main_col = main_col
        self._last_main_col_width = None
        main_col.bind("<Configure>", self._on_main_col_configure)

        # ---- الهيدر الثابت (أسماء وتواريخ الأيام) - ثابت فوق ومبيتحركش مع
        # سكرول الساعات تحته إطلاقًا ----
        self.fixed_header_frame = ctk.CTkFrame(main_col, fg_color=theme.CARD_BG, corner_radius=12,
                                                height=self.HEADER_HEIGHT + self.HEADER_BORDER_HEIGHT)
        self.fixed_header_frame.pack(side="top", fill="x", pady=(0, 0))
        self.fixed_header_frame.pack_propagate(False)

        # خط أسود عريض تحت الهيدر بيملا المسافة كلها بين الهيدر وجدول
        # المواعيد، بدل ما يبقى فيه فراغ أبيض فاضي بينهم
        header_bottom_border = ctk.CTkFrame(self.fixed_header_frame, fg_color=theme.ACCENT_BORDER,
                                             height=self.HEADER_BORDER_HEIGHT, corner_radius=0)
        header_bottom_border.pack(side="bottom", fill="x")
        header_bottom_border.pack_propagate(False)

        # سبيسر بعرض شريط التمرير بالظبط (SCROLLBAR_WIDTH)، عشان هيدر الأيام
        # يتزبط فوق أعمدة الجدول تحته بالظبط - نفس الرقم مستخدم في الحسابين
        header_spacer = ctk.CTkFrame(self.fixed_header_frame, fg_color="transparent",
                                      width=self.SCROLLBAR_WIDTH)
        header_spacer.pack(side="left", fill="y")
        header_spacer.pack_propagate(False)

        self.header_canvas = tk.Canvas(self.fixed_header_frame, bg=theme.CARD_BG,
                                        highlightthickness=0)
        self.header_canvas.pack(side="left", fill="both", expand=True)

        # ---- منطقة الجدول القابلة للتمرير (الساعات + المواعيد) ----
        # بنعمل السكرول بإيدينا (Canvas + Scrollbar عاديين) بدل الاعتماد على
        # مكوّن جاهز بيحجز مساحة داخلية مش معروف مقدارها بالظبط، عشان نضمن
        # إن عرض شريط التمرير المحجوز في الحساب = عرضه الحقيقي فعليًا 100%
        grid_container = ctk.CTkFrame(main_col, fg_color=theme.CARD_BG, corner_radius=12)
        grid_container.pack(side="top", fill="both", expand=True)
        self.grid_container = grid_container

        self.vscrollbar = tk.Scrollbar(grid_container, orient="vertical",
                                        width=self.SCROLLBAR_WIDTH)
        self.vscrollbar.pack(side="left", fill="y", padx=(2, 0), pady=2)

        self.grid_canvas = tk.Canvas(grid_container, bg=theme.CARD_BG, highlightthickness=0,
                                      yscrollcommand=self.vscrollbar.set, yscrollincrement=40)
        self.grid_canvas.pack(side="left", fill="both", expand=True, pady=2)
        self.vscrollbar.config(command=self.grid_canvas.yview)

        self.grid_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.grid_canvas.bind("<Button-1>", self._on_canvas_click)

        self._highlight_days_button()
        self.refresh()

    def _on_main_col_configure(self, event):
        """لما عرض المنطقة الرئيسية يتغيّر (أول مرة أو بتغيير حجم الشاشة)،
        بنعيد رسم الشارت عشان أعمدة الهيدر الثابت تتظبط فوق أعمدة الساعات بالظبط"""
        new_width = event.width
        if self._last_main_col_width is not None and abs(new_width - self._last_main_col_width) < 6:
            return
        self._last_main_col_width = new_width
        if hasattr(self, "grid_canvas"):
            self.refresh()

    def _on_mousewheel(self, event):
        self._hide_appt_tooltip()
        # سكرول عمودي (بيحرك الساعات لفوق/لتحت) - ده مستقل تمامًا عن اتجاه
        # الصفحة (عربي RTL أو إنجليزي LTR)، لإن اليمين/الشمال بيتأثروا
        # باتجاه اللغة، لكن فوق/تحت (المحور الرأسي) ثابت دايمًا في الاتجاهين
        self.grid_canvas.yview_scroll(int(event.delta / 120), "units")

    def _start_time_ticker(self):
        """بيحدّث خط الوقت الحالي كل دقيقة تلقائياً من غير ما يعيد بناء الشارت كله"""
        self._update_now_lines()
        try:
            self.after(60000, self._start_time_ticker)  # 60000 مللي ثانية = دقيقة
        except Exception:
            pass

    def _update_now_lines(self):
        if not self.winfo_exists() or not hasattr(self, "grid_canvas"):
            return
        if not self.grid_canvas.winfo_exists():
            return
        self.grid_canvas.delete("nowline")
        if self._time_col_range:
            x_left, x_right = self._time_col_range
            self._draw_now_line(self.grid_canvas, x_left, x_right)

    # ---------------- التنقل بين الأيام ----------------

    def _on_days_button(self, n):
        self.days_count = n
        self._highlight_days_button()
        self.refresh()

    def _save_days_pref(self):
        _save_appt_prefs(self.days_count)
        if hasattr(self.mini_cal, "save_size"):
            self.mini_cal.save_size()
        self.save_days_btn.configure(text="✔", fg_color=theme.SUCCESS, text_color="#FFFFFF")
        self.after(1200, lambda: self.save_days_btn.configure(
            text="💾", fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK))

    def _highlight_days_button(self):
        for n, btn in self.day_count_buttons.items():
            if n == self.days_count:
                btn.configure(fg_color=theme.SUCCESS, text_color="#FFFFFF")
            else:
                btn.configure(fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK)

    def _on_doctor_filter_change(self, label):
        self.doctor_filter = None if label == "كل الأطباء" else label
        self.refresh()

    def _go_today(self):
        self.start_date = date.today()
        self.mini_cal.jump_to(self.start_date)
        self.refresh()
        self.after(80, self._scroll_to_now)

    def _on_mini_calendar_pick(self, picked_date):
        self.start_date = picked_date
        self.refresh()

    def _on_mini_cal_width_changed(self, new_width):
        db.set_mini_calendar_width(new_width)

    def _scroll_to_now(self):
        if not self.winfo_exists() or not hasattr(self, "grid_canvas"):
            return
        days = [self.start_date + timedelta(days=i) for i in range(self.days_count)]
        if date.today() not in days:
            return  # النهاردة مش ظاهر في المدى المعروض حاليًا
        total_height = (self.end_hour - self.start_hour) * HOUR_HEIGHT
        if total_height <= 0:
            return
        now = datetime.now()
        current_y = (now.hour - self.start_hour) * HOUR_HEIGHT + (now.minute / 60) * HOUR_HEIGHT
        current_y = max(0, min(current_y, total_height))
        # إزاحة ثابتة (مش نسبة من ارتفاع الشاشة اللي ممكن تترجع غلط لو
        # اتقاست بدري قبل ما الصفحة تترسم بالكامل) - بتخلي الوقت الحالي
        # يبان في تلت الشاشة العلوي تقريبًا
        FIXED_OFFSET = 180
        target_y = max(current_y - FIXED_OFFSET, 0)
        fraction = target_y / total_height if total_height else 0
        fraction = max(0.0, min(fraction, 1.0))
        self.grid_canvas.yview_moveto(fraction)

    # ---------------- حساب مساحات الأعمدة (دالة مشتركة واحدة) ----------------

    def _compute_columns_layout(self, content_width, n):
        """
        الدالة الوحيدة اللي بتحسب مواقع وعروض كل الأعمدة (عمود الوقت الثابت +
        أعمدة الأيام من 1 لحد 7) بناءً على المساحة العرضية المتاحة فعليًا
        (content_width). الهيدر الثابت وجدول المواعيد بيستدعوا نفس الدالة دي
        بالظبط بنفس المدخلات في كل refresh، فمينفعش يحصل بينهم زيح تاني -
        أي تغيير في طريقة الحساب بيتطبق على الاتنين مرة واحدة تلقائيًا.
        """
        time_col_left = content_width - self.TIME_COL_WIDTH
        # بنحجز مسافة صغيرة على أقصى الشمال (LEFT_EDGE) عشان يبقى فيه مكان
        # نرسم فيه حد رمادي واضح لآخر عمود، بدل ما يتقص على حافة الكانفاس
        # ويبقى مش ظاهر
        LEFT_EDGE = self.DIVIDER_WIDTH
        avail = max(time_col_left - n * self.DIVIDER_WIDTH - LEFT_EDGE, n * 30)
        slot_width = max(avail // n, 30)
        remainder = max(avail - slot_width * n, 0)

        # بنبني الأعمدة بدءًا من جنب عمود الوقت (يعني اليوم الحالي أول عمود،
        # وباقي الأيام ماشية لليسار - ترتيب RTL طبيعي)
        cols = []
        x_right = time_col_left
        for i in range(n):
            x_right -= self.DIVIDER_WIDTH
            width_i = slot_width + (remainder if i == n - 1 else 0)
            x_left = x_right - width_i
            cols.append({"day_index": i, "x_left": x_left, "x_right": x_right})
            x_right = x_left

        return {
            "content_width": content_width,
            "time_col_left": time_col_left,
            "time_col_right": content_width,
            "columns": cols,
            "left_edge": LEFT_EDGE,
        }

    # ---------------- رسم الشارت ----------------

    def refresh(self):
        self._hide_appt_tooltip()
        # حارس ضد التنفيذ المتداخل: أي استدعاء تاني لـ refresh() وهي شغالة
        # بيتجاهَل، عشان نضمن إن العملية تكمل من غير تصادم بين نسختين
        if getattr(self, "_refreshing", False):
            return
        self._refreshing = True
        try:
            self._do_refresh()
        finally:
            self._refreshing = False

    def _do_refresh(self):
        settings = db.get_settings()
        self.start_hour = settings["schedule_start_hour"]
        self.end_hour = settings["schedule_end_hour"]

        days = [self.start_date + timedelta(days=i) for i in range(self.days_count)]
        self._current_days = days

        end_display = days[-1]
        if self.days_count == 1:
            self.range_label.configure(text=f"{WEEKDAY_NAMES[days[0].weekday()]}  {days[0].strftime('%Y/%m/%d')}")
        else:
            self.range_label.configure(
                text=f"{days[0].strftime('%Y/%m/%d')}  ←  {end_display.strftime('%Y/%m/%d')}")

        total_height = (self.end_hour - self.start_hour) * HOUR_HEIGHT

        self.main_col.update_idletasks()
        main_width = self.main_col.winfo_width()
        if main_width <= 1:
            main_width = 1100
        # عرض المحتوى الحقيقي = عرض المنطقة الرئيسية ناقص عرض شريط التمرير
        # اللي إحنا حددناه بنفسنا (SCROLLBAR_WIDTH) - رقم معروف 100%، مش تخمين
        content_width = max(main_width - self.SCROLLBAR_WIDTH, 300)

        n = self.days_count
        layout = self._compute_columns_layout(content_width, n)
        self._current_layout = layout

        self.header_canvas.configure(width=content_width, height=self.HEADER_HEIGHT)
        self.grid_canvas.configure(width=content_width,
                                    scrollregion=(0, 0, content_width, total_height))

        self._time_col_range = None
        self._draw_header_canvas(self.header_canvas, days, layout)
        self._draw_grid_canvas(self.grid_canvas, days, layout, total_height)

        self.after(60, self._scroll_to_now)
        self.after(300, self._scroll_to_now)
        self.after(60, self._update_now_lines)
        self.after(300, self._update_now_lines)

    def _draw_dividers(self, canvas, layout, height):
        """فاصل واضح بين كل عمود يوم والتاني، وبين آخر عمود وعمود الوقت -
        نفس الدالة بتترسم في الهيدر وفي الجدول عشان يبانوا كخط واحد متصل"""
        cols = layout["columns"]
        if cols:
            canvas.create_rectangle(cols[0]["x_right"], 0, layout["time_col_left"], height,
                                     fill=DIVIDER_COLOR, outline="")
        for i in range(len(cols) - 1):
            canvas.create_rectangle(cols[i + 1]["x_right"], 0, cols[i]["x_left"], height,
                                     fill=DIVIDER_COLOR, outline="")
        # الحد الرمادي على أقصى الشمال (بعد آخر عمود يوم) - كان مختفي قبل كده
        # لإنه كان بيترسم بالظبط على حافة الكانفاس (x=0)، فدلوقتي محجوزله
        # مسافة (left_edge) عشان يبان زي باقي الفواصل بالظبط
        if cols:
            canvas.create_rectangle(0, 0, cols[-1]["x_left"], height, fill=DIVIDER_COLOR, outline="")

    def _draw_header_canvas(self, canvas, days, layout):
        for w in self._header_embedded_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        self._header_embedded_widgets = []

        canvas.delete("all")
        height = self.HEADER_HEIGHT

        canvas.create_rectangle(layout["time_col_left"], 0, layout["time_col_right"], height,
                                 fill=theme.CARD_BG, outline="")

        for col in layout["columns"]:
            d = days[col["day_index"]]
            is_holiday = db.is_holiday(d)
            is_today = d == date.today()
            bg = "#D6D9DE" if is_holiday else (theme.BG_MAIN if not is_today else theme.lighten_color(theme.ACCENT_BORDER, 0.82))
            text_color = theme.TEXT_MUTED if is_holiday else (theme.ACCENT_BORDER if is_today else theme.TEXT_DARK)

            canvas.create_rectangle(col["x_left"], 0, col["x_right"], height,
                                     fill=bg, outline=DIVIDER_COLOR)

            col_w = col["x_right"] - col["x_left"]
            # لما العمود يبقى ضيق (عدد أيام كبير على شاشة صغيرة)، بنقصر النص
            # عشان التاريخ يفضل ظاهر بدل ما يختفي/يتقص
            if col_w < 80:
                label_text = _format_day_month(d)
                font_size = 11
            elif col_w < 130:
                label_text = _format_day_month(d)
                if is_holiday:
                    label_text += " ⛱"
                font_size = 12
            else:
                label_text = f"{WEEKDAY_NAMES[d.weekday()]}  {_format_day_month(d)}"
                if is_holiday:
                    label_text += "  (إجازة)"
                font_size = 12

            cx = (col["x_left"] + col["x_right"]) / 2
            canvas.create_text(cx, height / 2, text=label_text,
                                font=(theme.CONTENT_FONT_FAMILY, theme.compensated_size(font_size), "bold"),
                                fill=text_color)

            # المدير بس يقدر يعلّم يوم بعينه كإجازة/يلغيها
            if self.current_user and self.current_user.get("role") == "manager" and col_w > 46:
                btn = ctk.CTkButton(
                    canvas, text="🏖", width=24, height=22, corner_radius=6,
                    fg_color=theme.DANGER if is_holiday else "transparent",
                    text_color="#FFFFFF" if is_holiday else theme.TEXT_MUTED,
                    hover_color=theme.DANGER,
                    command=lambda dd=d: self._toggle_holiday(dd))
                canvas.create_window(col["x_left"] + 18, height / 2, window=btn)
                self._header_embedded_widgets.append(btn)

        self._draw_dividers(canvas, layout, height)

    def _draw_grid_canvas(self, canvas, days, layout, total_height):
        canvas.delete("all")

        canvas.create_rectangle(layout["time_col_left"], 0, layout["time_col_right"], total_height,
                                 fill=theme.CARD_BG, outline="")

        for col in layout["columns"]:
            d = days[col["day_index"]]
            is_holiday = db.is_holiday(d)
            bg = "#EDEEF0" if is_holiday else theme.CARD_BG
            canvas.create_rectangle(col["x_left"], 0, col["x_right"], total_height,
                                     fill=bg, outline="")

        # خطوط الساعات - نفس اللون بالظبط لخط الساعة الكاملة (زي 13:00) وخط
        # نص الساعة (زي 13:30)، والفرق بينهم في السُمك بس (الساعة الكاملة
        # أعرض بمقدار مرة ونص) عشان الشكل يبقى متناسق ومش شاذ
        GRIDLINE_COLOR = "#C7CBD1"
        HALF_HOUR_WIDTH = 1.0
        FULL_HOUR_WIDTH = 1.5
        full_left, full_right = 0, layout["time_col_right"]
        for h in range(self.start_hour, self.end_hour + 1):
            y = (h - self.start_hour) * HOUR_HEIGHT
            canvas.create_line(full_left, y, full_right, y,
                                fill=GRIDLINE_COLOR, width=FULL_HOUR_WIDTH, tags="gridline")
            if h < self.end_hour:
                y_half = y + HOUR_HEIGHT / 2
                canvas.create_line(full_left, y_half, full_right, y_half,
                                    fill=GRIDLINE_COLOR, width=HALF_HOUR_WIDTH, tags="gridline")

        # الفواصل الواضحة بين الأعمدة (نفس دالة الهيدر بالظبط)
        self._draw_dividers(canvas, layout, total_height)

        # أرقام الساعات في عمود الوقت الثابت
        for h in range(self.start_hour, self.end_hour + 1):
            y = (h - self.start_hour) * HOUR_HEIGHT
            canvas.create_text(layout["time_col_right"] - 8, y, text=f"{h % 24:02d}:00",
                                font=theme.FONT_HOUR_TICK,
                                fill=theme.TEXT_DARK, anchor="ne")
            if h < self.end_hour:
                y_half = y + HOUR_HEIGHT / 2
                canvas.create_text(layout["time_col_right"] - 8, y_half, text="30",
                                    font=theme.FONT_HALF_HOUR_TICK,
                                    fill=theme.TEXT_MUTED, anchor="ne")

        # المواعيد + خط الوقت الحالي
        self._time_col_range = None
        for col in layout["columns"]:
            d = days[col["day_index"]]
            appts = db.get_appointments(date_filter=d.isoformat())
            if self.doctor_filter:
                appts = [a for a in appts if a.get("doctor_name") == self.doctor_filter]
            overlap_layout = self._layout_overlaps(appts)
            for appt in appts:
                slot = overlap_layout.get(appt["id"], (0, 1))
                self._draw_appointment(canvas, appt, col["x_left"], col["x_right"], slot)
            if d == date.today():
                self._time_col_range = (layout["time_col_left"], layout["time_col_right"])
                self._draw_now_line(canvas, layout["time_col_left"], layout["time_col_right"])

    def _layout_overlaps(self, appts):
        """بياخد كل مواعيد يوم واحد (لعمود واحد) وبيرجّع dict: appt_id ->
        (col_index, total_cols) - عشان أي مواعيد بتتداخل زمنيًا (بتغطي على
        بعض حاليًا) تترسم جنب بعض في نفس المدى الزمني المتداخل، مش واحد
        فوق التاني. المواعيد اللي مالهاش تداخل بتاخد العمود كله (total_cols=1)"""
        events = []
        for a in appts:
            try:
                hh, mm = map(int, a["appt_time"].split(":"))
            except Exception:
                hh, mm = self.start_hour, 0
            duration = a.get("duration_minutes") or 30
            start = hh * 60 + mm
            end = start + max(duration, 1)
            events.append({"id": a["id"], "start": start, "end": end})

        events.sort(key=lambda e: (e["start"], e["end"]))

        result = {}
        i, n = 0, len(events)
        while i < n:
            # ابني "كلستر" من الأحداث المتداخلة زمنيًا (متصلة ببعض) بدءًا من هنا
            cluster = [events[i]]
            cluster_end = events[i]["end"]
            j = i + 1
            while j < n and events[j]["start"] < cluster_end:
                cluster.append(events[j])
                cluster_end = max(cluster_end, events[j]["end"])
                j += 1

            # وزّع أحداث الكلستر على أعمدة فرعية جنب بعض: كل حدث بياخد أول
            # عمود فاضي (آخر حدث فيه خلص قبل ما الحدث ده يبدأ)، ولو مفيش
            # عمود فاضي بيتفتح عمود جديد
            columns_last_end = []
            col_of = {}
            for ev in cluster:
                placed = False
                for ci, col_end in enumerate(columns_last_end):
                    if col_end <= ev["start"]:
                        columns_last_end[ci] = ev["end"]
                        col_of[ev["id"]] = ci
                        placed = True
                        break
                if not placed:
                    columns_last_end.append(ev["end"])
                    col_of[ev["id"]] = len(columns_last_end) - 1

            total_cols = len(columns_last_end)
            for ev in cluster:
                result[ev["id"]] = (col_of[ev["id"]], total_cols)

            i = j

        return result

    def _toggle_holiday(self, d):
        date_str = d.isoformat()
        existing = db.get_holiday_dates()
        if date_str in existing:
            db.remove_holiday_date(date_str)
        else:
            db.add_holiday_date(date_str)
        self.mini_cal.refresh_holidays()
        self.refresh()

    def _draw_now_line(self, canvas, time_col_left, time_col_right):
        """بيرسم مؤشر الوقت الحالي (خط أحمر قصير + سهم صغير) جوه عمود الوقت
        الثابت بس - مش عبر عرض عمود اليوم كله زي الأول - عشان مايغطيش على
        اسم المريض/رقم تليفونه لو فيه حجز شغال بالظبط في نفس اللحظة دي.
        السهم بيشاور جهة أعمدة الأيام (يسار) عشان يوضّح إن المؤشر ده بيمثّل
        نفس اللحظة على طول الصف، من غير ما نرسم فوق محتوى الحجوزات فعليًا"""
        now = datetime.now()
        if not (self.start_hour <= now.hour < self.end_hour + 1):
            return
        y = (now.hour - self.start_hour) * HOUR_HEIGHT + (now.minute / 60) * HOUR_HEIGHT
        canvas.create_line(time_col_left, y, time_col_right, y,
                            fill="#E53935", width=2, tags="nowline")
        arrow_size = 6
        canvas.create_polygon(
            time_col_left, y - arrow_size,
            time_col_left - arrow_size, y,
            time_col_left, y + arrow_size,
            fill="#E53935", outline="", tags="nowline")
        canvas.create_oval(time_col_right - 5, y - 5, time_col_right + 5, y + 5,
                            fill="#E53935", outline="", tags="nowline")

    def _fit_text(self, text, max_width, font):
        """بيرجع النص كامل لو مقاسه أصلاً أصغر من المساحة المتاحة، أو نسخة
        مقصوصة منه ومنتهية بـ '…' لو أطول، عشان النص مايخرجش برّه عمود اليوم"""
        fnt = tkfont.Font(font=font)
        if fnt.measure(text) <= max_width:
            return text
        ellipsis = "…"
        if fnt.measure(ellipsis) > max_width:
            return ellipsis
        lo, hi = 0, len(text)
        fitted = ellipsis
        while lo < hi:
            mid = (lo + hi + 1) // 2
            candidate = text[:mid] + ellipsis
            if fnt.measure(candidate) <= max_width:
                fitted = candidate
                lo = mid
            else:
                hi = mid - 1
        return fitted

    def _draw_appointment(self, canvas, appt, x_left, x_right, slot=(0, 1)):
        try:
            hh, mm = map(int, appt["appt_time"].split(":"))
        except Exception:
            hh, mm = self.start_hour, 0
        duration = appt.get("duration_minutes") or 30

        y1 = (hh - self.start_hour) * HOUR_HEIGHT + (mm / 60) * HOUR_HEIGHT
        y2 = y1 + max(duration / 60 * HOUR_HEIGHT, 22)

        # لو الموعد ده بيتداخل زمنيًا مع مواعيد تانية في نفس اليوم، بنقسم
        # عرض عمود اليوم على عدد المواعيد المتداخلة، وكل واحد بياخد شريحته
        # (عمود فرعي) جنب التاني - بدل ما يترسموا فوق بعض ويغطي واحد التاني
        col_index, total_cols = slot
        if total_cols > 1:
            full_w = x_right - x_left
            sub_w = full_w / total_cols
            x_left, x_right = x_left + col_index * sub_w, x_left + (col_index + 1) * sub_w

        status_info = theme.APPOINTMENT_STATUSES.get(appt["status"], theme.APPOINTMENT_STATUSES["confirmed"])
        color = appt.get("color") or status_info["color"]

        pad = 3
        canvas.create_rectangle(x_left + pad, y1, x_right - pad, y2, fill=color, outline="#FFFFFF",
                                 width=1, tags=("appt", f"appt_{appt['id']}"))
        col_w = x_right - x_left
        label_text = f"{appt['appt_time']} - {appt['full_name']}"
        # رقم التليفون بيتضاف بس لو العمود واسع بما يكفي (زي أوضاع يوم واحد/
        # يومين) - عشان في أوضاع الأسبوع كامل (أعمدة ضيقة) النص يفضل مقروء
        # ومايتقصّش برّه حدود البلوك
        if appt.get("phone") and col_w >= 170:
            label_text += f" - {appt['phone']}"
        # بنقصّ النص (لو طويل) بحيث يفضل جوه حدود عمود اليوم بتاعه بالظبط،
        # وميمتدّش يكتب فوق عمود اليوم اللي بعده - بدل القص بنحط "…" في الآخر
        max_text_width = max(col_w - 2 * pad - 12, 10)
        label_text = self._fit_text(label_text, max_text_width, theme.FONT_APPOINTMENT_LABEL)
        canvas.create_text(x_right - pad - 6, (y1 + y2) / 2, text=label_text, anchor="e",
                            fill="#FFFFFF", font=theme.FONT_APPOINTMENT_LABEL,
                            tags=("appt", f"appt_{appt['id']}"))

        canvas.tag_bind(f"appt_{appt['id']}", "<Button-1>",
                         lambda e, a=appt: self._open_patient_file(a["patient_id"]))
        canvas.tag_bind(f"appt_{appt['id']}", "<Button-3>",
                         lambda e, a=appt: self._on_appt_right_click(e, a))
        canvas.tag_bind(f"appt_{appt['id']}", "<Enter>",
                         lambda e, a=appt: self._show_appt_tooltip(e, a))
        canvas.tag_bind(f"appt_{appt['id']}", "<Leave>",
                         lambda e: self._hide_appt_tooltip())

    def _show_appt_tooltip(self, event, appt):
        self._hide_appt_tooltip()

        lines = [appt["full_name"]]
        try:
            lines.append(f"رقم الملف: {int(appt['patient_id']):06d}")
        except (KeyError, TypeError, ValueError):
            pass
        if appt.get("phone"):
            lines.append(f"التليفون: {appt['phone']}")
        if appt.get("notes"):
            lines.append(f"الشكوى/ملاحظات: {appt['notes']}")
        text = "\n".join(lines)

        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        try:
            tip.attributes("-topmost", True)
        except Exception:
            pass
        x = event.x_root + 16
        y = event.y_root + 12
        tip.wm_geometry(f"+{x}+{y}")
        tk.Label(tip, text=text, bg="#1B1E23", fg="#FFFFFF",
                 font=theme.FONT_APPT_TOOLTIP, padx=10, pady=8,
                 justify="right", anchor="e", wraplength=260).pack()
        self._appt_tooltip = tip

    def _hide_appt_tooltip(self):
        tip = getattr(self, "_appt_tooltip", None)
        if tip is not None:
            try:
                tip.destroy()
            except Exception:
                pass
            self._appt_tooltip = None

    def _on_canvas_click(self, event):
        canvas = self.grid_canvas
        clicked = canvas.find_withtag("current")
        if clicked:
            tags = canvas.gettags(clicked[0])
            if "appt" in tags:
                return  # هيتعامل معاه الـ tag_bind بتاع الموعد نفسه

        layout = self._current_layout
        days = self._current_days
        if not layout or not days:
            return

        x = event.x
        day = None
        for col in layout["columns"]:
            if col["x_left"] <= x <= col["x_right"]:
                day = days[col["day_index"]]
                break
        if day is None:
            return  # اتكبس في عمود الوقت أو في فاصل بين عمودين

        # لازم نحول event.y (اللي هو نسبي للجزء الظاهر بس من الكانفاس) لإحداثي
        # حقيقي جوه الكانفاس نفسه (canvasy) - عشان لو الجدول متمرّر (scroll)
        # لأسفل، الحساب يبقى مظبوط على المكان اللي اتكبس فيه فعليًا، مش على
        # المكان زي ما لو كنا في أول الجدول
        real_y = canvas.canvasy(event.y)
        hour_offset = real_y / HOUR_HEIGHT
        # نقرّب لأقرب ساعة صحيحة كاملة (فتح على 18:00 مثلاً مش 18:15 أو 18:30)
        hour = self.start_hour + int(hour_offset)
        self.open_appointment_dialog(prefill_date=day, prefill_time=f"{hour:02d}:00")

    # ---------------- تفاصيل/تعديل موعد ----------------

    APPT_COLOR_PALETTE = [
        "#1E88E5", "#43A047", "#8E24AA", "#E53935", "#FDD835",
        "#00897B", "#6D4C41", "#3949AB", "#D81B60", "#C62828",
    ]

    def _open_appt_details(self, appt):
        """نافذة واحدة موحّدة: تفاصيل الحجز (الحالة/اللون/الحذف) + تعديله
        (التاريخ/الوقت/الطبيب/الملاحظات) مع بعض - بدل ما كانوا نافذتين
        منفصلتين قبل كده. كل خطوط النافذة (ما عدا اسم المريض) بناخد نفس
        فونط اسم الحجز في صفحة المواعيد (FONT_DIALOG_LABEL - نفس نوع
        وتخانة فونط الحجز في الكالندر، بس بمقاس مضبوط عشان يبان واضح
        في نافذة الحوار برضو)"""
        F = theme.FONT_DIALOG_LABEL
        ITEM_GAP = 15  # فاصل موحّد بين كل عنصر رئيسي والتاني في النافذة

        dialog = ctk.CTkToplevel(self)
        dialog.title("تفاصيل الحجز وتعديله")
        dialog_w, dialog_h = 440, 640
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        pos_x = (screen_w - dialog_w) // 2
        pos_y = max((screen_h - dialog_h) // 2 - 25, 0)
        dialog.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")
        dialog.minsize(400, 610)
        dialog.resizable(True, True)
        dialog.grab_set()
        # شيل زرار التصغير (-) وزرار التكبير/الاستعادة من هيدر النافذة،
        # وسيب زرار الإغلاق X بس
        theme.strip_min_max_buttons(dialog)

        # ---- شريط أزرار ثابت أسفل النافذة (حفظ + إلغاء بجوار بعض، في
        # نفس السطر، بلون واضح لكل واحد فيهم، ومساحتهم مجتمعين = ربع
        # عرض السطر بس، متوسطين) - بيتحط الأول عشان ياخد مكانه الثابت
        # تحت، ومنطقة المحتوى تاخد الباقي فوقه (من غير سكرول، كل
        # المحتوى لازم يبان مرة واحدة) ----
        footer = ctk.CTkFrame(dialog, fg_color="transparent", height=46)
        footer.pack(side="bottom", fill="x", pady=(2, 10))
        footer.pack_propagate(False)

        F_BTN = (theme.CONTENT_FONT_FAMILY, theme.compensated_size(14), "bold")
        footer_line_w = dialog_w - 40
        btn_group_w = max(int(footer_line_w * 0.25), 130)  # 1/4 من عرض السطر، بحد أدنى للوضوح
        each_btn_w = btn_group_w // 2

        btns_frame = ctk.CTkFrame(footer, fg_color="transparent")
        btns_frame.place(relx=0.5, rely=0.5, anchor="center")

        # منطقة المحتوى: فريم عادي من غير سكرول - كل الحقول لازم تبقى ظاهرة
        # بصريًا مرة واحدة من غير أي حاجة تتقص أو سكرول بار
        scroll = ctk.CTkFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=(2, 0))

        ctk.CTkLabel(scroll, text=appt["full_name"], font=theme.FONT_SUBTITLE).pack(pady=(6, ITEM_GAP))

        # ---- التاريخ: أيقونة بتفتح كالندر كامل ----
        try:
            initial_date = datetime.strptime(appt["appt_date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            initial_date = date.today()
        selected_date_holder = {"date": initial_date}

        date_row = ctk.CTkFrame(scroll, fg_color="transparent")
        date_row.pack(padx=26, pady=(0, ITEM_GAP), anchor="e", fill="x")
        ctk.CTkLabel(date_row, text="التاريخ", font=F).pack(side="right", padx=(14, 0))
        date_display_btn = ctk.CTkButton(
            date_row, text=f"📅 {selected_date_holder['date'].strftime('%Y-%m-%d')}",
            width=170, height=36, fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
            border_width=1, border_color=theme.BORDER, hover_color=theme.BG_MAIN,
            font=F)
        date_display_btn.pack(side="right")

        def open_date_picker():
            picker = ctk.CTkToplevel(dialog)
            picker.title("اختيار التاريخ")
            picker_w, picker_h = 450, 380
            p_x = (picker.winfo_screenwidth() - picker_w) // 2
            p_y = (picker.winfo_screenheight() - picker_h) // 2
            picker.geometry(f"{picker_w}x{picker_h}+{p_x}+{p_y}")
            picker.grab_set()

            def on_pick(d):
                selected_date_holder["date"] = d
                date_display_btn.configure(text=f"📅 {d.strftime('%Y-%m-%d')}")
                picker.destroy()

            cal = MiniCalendar(picker, on_date_selected=on_pick, width=420)
            cal.pack(fill="both", expand=True, padx=10, pady=10)
            cal.jump_to(selected_date_holder["date"])

        date_display_btn.configure(command=open_date_picker)

        # ---- الوقت (من/إلى): إدخال يدوي بانتقال تلقائي من خانة الساعات
        # (شمال) لخانة الدقايق (يمين) بدل القايمة المنسدلة - في سطر واحد
        # بس "من ... إلى ..." ----
        try:
            start_h, start_m = map(int, appt["appt_time"].split(":"))
        except Exception:
            start_h, start_m = 10, 0
        duration = appt.get("duration_minutes") or 30
        end_total_min = start_h * 60 + start_m + duration
        end_h, end_m = (end_total_min // 60) % 24, end_total_min % 60

        ctk.CTkLabel(scroll, text="الوقت", font=F).pack(anchor="e", padx=26)
        time_row = ctk.CTkFrame(scroll, fg_color="transparent")
        time_row.pack(padx=26, pady=(2, ITEM_GAP), anchor="e")

        ctk.CTkLabel(time_row, text="من", font=F).pack(side="right", padx=(4, 4))
        from_time = TimeAutoEntry(time_row, hour_min=0, hour_max=23)
        from_time.set_time(start_h, start_m)
        from_time.pack(side="right")

        ctk.CTkLabel(time_row, text="إلى", font=F).pack(side="right", padx=(10, 4))
        to_time = TimeAutoEntry(time_row, hour_min=0, hour_max=23)
        to_time.set_time(end_h, end_m)
        to_time.pack(side="right")

        # ---- الطبيب: منسدلة من الأطباء المسجلين بجوار عنوان "الطبيب" في
        # نفس السطر (مع ضمان ظهور الطبيب الحالي للموعد حتى لو بقى غير
        # مفعّل/محذوف من قايمة الأطباء) ----
        doctor_row = ctk.CTkFrame(scroll, fg_color="transparent")
        doctor_row.pack(padx=26, pady=(0, ITEM_GAP), anchor="e", fill="x")
        ctk.CTkLabel(doctor_row, text="الطبيب", font=F).pack(side="right", padx=(14, 0))
        doctors_list = db.get_doctors()
        doctor_names = [d["full_name"] for d in doctors_list]
        current_doctor = (appt.get("doctor_name") or "").strip()
        if current_doctor and current_doctor not in doctor_names:
            doctor_names = [current_doctor] + doctor_names
        if not doctor_names:
            doctor_names = ["لا يوجد أطباء مسجلين"]
        doctor_var = ctk.StringVar(value=current_doctor if current_doctor in doctor_names else doctor_names[0])
        ctk.CTkOptionMenu(doctor_row, values=doctor_names, variable=doctor_var, width=220,
                          font=F, dropdown_font=F,
                          **theme.optionmenu_colors()).pack(side="right")

        # ---- ملاحظات / شكوى المريض ----
        ctk.CTkLabel(scroll, text="ملاحظات / شكوى المريض", font=F).pack(anchor="e", padx=26)
        notes_box = ctk.CTkTextbox(scroll, width=300, height=64, font=F)
        if appt.get("notes"):
            notes_box.insert("1.0", appt["notes"])
        notes_box.pack(padx=26, pady=(4, 0), anchor="e")

        error_label = ctk.CTkLabel(scroll, text="", font=F, text_color=theme.DANGER)
        error_label.pack(anchor="e", padx=26)

        # فاصل رأسي بين "ملاحظات" و"الحالة" = 15px بس، زي باقي العناوين
        ctk.CTkFrame(scroll, fg_color=theme.BORDER, height=1).pack(fill="x", padx=26, pady=(ITEM_GAP, ITEM_GAP))

        # ---- الحالة: منسدلة بجوار كلمة "الحالة" في نفس السطر ----
        status_row = ctk.CTkFrame(scroll, fg_color="transparent")
        status_row.pack(anchor="center", pady=(0, ITEM_GAP))
        ctk.CTkLabel(status_row, text="الحالة", font=F).pack(side="right", padx=(14, 0))
        status_menu = ctk.CTkOptionMenu(
            status_row, width=200, font=F, dropdown_font=F,
            values=[info["label"] for info in theme.APPOINTMENT_STATUSES.values()],
            command=lambda label: self._change_status(appt["id"], label, dialog),
            **theme.optionmenu_colors())
        current_label = theme.APPOINTMENT_STATUSES.get(appt["status"], {}).get("label", "مؤكد")
        status_menu.set(current_label)
        status_menu.pack(side="right")

        # ---- اللون: الأزرار بجوار كلمة "اللون" في نفس السطر ----
        color_row = ctk.CTkFrame(scroll, fg_color="transparent")
        color_row.pack(anchor="center", pady=(0, ITEM_GAP))
        ctk.CTkLabel(color_row, text="لون الموعد في الكالندر", font=F).pack(side="right", padx=(14, 0))
        palette_frame = ctk.CTkFrame(color_row, fg_color="transparent")
        palette_frame.pack(side="right")
        for i, color in enumerate(self.APPT_COLOR_PALETTE):
            swatch = ctk.CTkButton(
                palette_frame, text="", width=26, height=26, corner_radius=13,
                fg_color=color, hover_color=color, border_width=2,
                border_color="#000000" if appt.get("color") == color else color,
                command=lambda c=color, a=appt, d=dialog: self._change_color(a["id"], c, d))
            swatch.grid(row=i // 5, column=i % 5, padx=3, pady=3)

        def confirm_delete():
            theme.confirm_dialog(
                dialog, "هل تريد حذف الموعد نهائيًا؟",
                lambda: self._delete_and_close(appt["id"], dialog), danger=True)

        # زرار إلغاء/حذف الموعد بنفس ارتفاع زراري الحفظ والإلغاء (30px)،
        # وبعرض = 1/3 عرض السطر بس، وفي النص (سنتر) زي زراير الفوتر
        cancel_appt_w = footer_line_w // 3
        ctk.CTkButton(scroll, text="🗑 حذف الموعد", fg_color=theme.DANGER,
                      hover_color=theme.darken_color(theme.DANGER, 0.85),
                      width=cancel_appt_w, height=30,
                      font=F_BTN, command=confirm_delete).pack(pady=(0, 8))


        # ---- تنفيذ الحفظ (بعد التأكيد) ----
        def save_edit():
            fh, fm = from_time.get_hour(), from_time.get_minute()
            th, tm = to_time.get_hour(), to_time.get_minute()
            new_duration = (th * 60 + tm) - (fh * 60 + fm)
            if new_duration <= 0:
                error_label.configure(text="⚠ وقت النهاية لازم يكون بعد وقت البداية")
                return
            new_date = selected_date_holder["date"].isoformat()
            db.update_appointment_details(
                appt["id"], new_date, f"{fh:02d}:{fm:02d}", new_duration,
                doctor_name=doctor_var.get() if doctors_list or current_doctor else None,
                notes=notes_box.get("1.0", "end").strip(),
            )
            dialog.destroy()
            self.refresh()
            theme.show_toast(self, "تم تعديل الموعد")

        def confirm_save():
            theme.confirm_dialog(dialog, "هل تريد حفظ تعديلات الموعد؟", save_edit)

        # ---- زرار الحفظ (أخضر) وزرار الإلغاء (أحمر، واضح) بجوار بعض في
        # نفس السطر أسفل النافذة، مصغّرين وبيملوا مع بعض ربع عرض السطر
        # بس، ومتوسطين ----
        save_btn = ctk.CTkButton(btns_frame, text="حفظ", width=each_btn_w, height=30,
                                  fg_color=theme.SUCCESS,
                                  hover_color=theme.darken_color(theme.SUCCESS, 0.85),
                                  font=F_BTN, command=confirm_save)
        save_btn.pack(side="right", padx=(4, 0))

        cancel_btn = ctk.CTkButton(btns_frame, text="إلغاء", width=each_btn_w, height=30,
                                    fg_color=theme.DANGER,
                                    hover_color=theme.darken_color(theme.DANGER, 0.85),
                                    font=F_BTN, command=dialog.destroy)
        cancel_btn.pack(side="right", padx=(0, 4))

    def _change_color(self, appt_id, color, dialog):
        db.update_appointment_color(appt_id, color)
        dialog.destroy()
        self.refresh()
        theme.show_toast(self, "تم تغيير اللون")

    def _change_status(self, appt_id, label, dialog):
        key = next((k for k, v in theme.APPOINTMENT_STATUSES.items() if v["label"] == label), "confirmed")
        db.update_appointment_status(appt_id, key)
        dialog.destroy()
        self.refresh()
        theme.show_toast(self, "تم تغيير الحالة")

    def _delete_and_close(self, appt_id, dialog):
        db.delete_appointment(appt_id)
        dialog.destroy()
        self.refresh()
        theme.show_toast(self, "تم حذف الموعد", kind="error")

    # ---------------- إضافة موعد ----------------

    def open_appointment_dialog(self, prefill_date=None, prefill_time=None):
        patients = db.get_all_patients()
        if not patients:
            dialog = ctk.CTkToplevel(self)
            dialog.title("تنبيه")
            dialog.geometry("300x120")
            ctk.CTkLabel(dialog, text="لازم تضيف مريض الأول من صفحة المرضى",
                         font=theme.FONT_NORMAL, wraplength=260).pack(pady=30)
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("موعد جديد")
        dialog_w, dialog_h = 560, 720
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        pos_x = (screen_w - dialog_w) // 2
        pos_y = max((screen_h - dialog_h) // 2 - 50, 0)
        dialog.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")
        dialog.minsize(520, 620)
        dialog.resizable(True, True)
        dialog.grab_set()

        # منطقة علوية (فيها كل حقول الإدخال) بحجمها الطبيعي بس
        top_area = ctk.CTkFrame(dialog, fg_color="transparent")
        top_area.pack(side="top", fill="x")

        ctk.CTkLabel(top_area, text="إضافة موعد جديد", font=theme.FONT_SUBTITLE).pack(pady=(14, 8))

        # ---- بحث المريض ----
        ctk.CTkLabel(top_area, text="المريض (اكتب أي جزء من الاسم/رقم الملف/التليفون/الوظيفة/الجنسية/العمر)",
                     font=theme.FONT_SMALL, wraplength=420, justify="right",
                     text_color=theme.TEXT_MUTED).pack(anchor="e", padx=24)

        selected_patient_holder = {"patient": None}

        search_entry = RTLEntry(top_area, width=470, height=28, font=theme.FONT_NORMAL)
        search_entry.pack(padx=24, pady=(4, 2), anchor="e")

        selected_label = ctk.CTkLabel(top_area, text="برجاء اختيار مريض", font=theme.FONT_SMALL,
                                       text_color=theme.TEXT_MUTED)
        selected_label.pack(anchor="e", padx=24, pady=(0, 2))

        results_frame = ctk.CTkScrollableFrame(top_area, width=470, height=52,
                                                fg_color=theme.BG_MAIN, corner_radius=8)
        results_frame.pack(padx=24, pady=(0, 6), anchor="e")

        def render_patient_results(search_text):
            for w in results_frame.winfo_children():
                w.destroy()
            matches = db.get_all_patients(search=search_text.strip()) if search_text.strip() else patients
            if not matches:
                ctk.CTkLabel(results_frame, text="لا توجد نتائج مطابقة", font=theme.FONT_SMALL,
                             text_color=theme.TEXT_MUTED).pack(pady=10)
                return
            for p in matches[:40]:
                age = db.calculate_age(p.get("birth_date"))
                subtitle_parts = [v for v in (
                    f"ملف رقم {p['id']:06d}",
                    p.get("phone"),
                    f"العمر {age}" if age is not None else None,
                    p.get("nationality"),
                    p.get("occupation"),
                    p.get("address"),
                ) if v]
                subtitle = "  -  ".join(subtitle_parts)
                display = p["full_name"] + (f"   ({subtitle})" if subtitle else "")
                ctk.CTkButton(
                    results_frame, text=display, anchor="e", fg_color="transparent",
                    text_color=theme.TEXT_DARK, hover_color=theme.CARD_BG, height=28,
                    font=theme.FONT_SMALL,
                    command=lambda pp=p: pick_patient(pp)).pack(fill="x", pady=1)

        def pick_patient(p):
            selected_patient_holder["patient"] = p
            selected_label.configure(text=f"✔ اتخترت: {p['full_name']}", text_color=theme.SUCCESS)
            search_entry.delete(0, "end")
            search_entry.insert(0, p["full_name"])

        def on_search_change(event=None):
            selected_patient_holder["patient"] = None
            selected_label.configure(text="برجاء اختيار مريض", text_color=theme.TEXT_MUTED)
            render_patient_results(search_entry.get())

        search_entry.bind("<KeyRelease>", on_search_change)
        render_patient_results("")

        # ---- صف مشترك واحد: زرار الحفظ في أقصى الشمال، وجدول موحّد على
        # اليمين فيه التاريخ + الوقت (من/إلى) + الطبيب، كلهم بعمود تسميات
        # واحد (التاريخ/الوقت/من/إلى/الطبيب) تحت بعض بالظبط ----
        selected_date_holder = {"date": prefill_date or self.start_date}

        content_row = ctk.CTkFrame(top_area, fg_color="transparent")
        content_row.pack(padx=24, pady=(4, 4), anchor="e", fill="x")

        form_grid = ctk.CTkFrame(content_row, fg_color="transparent")
        form_grid.pack(side="right")

        LABEL_COL = 4  # عمود التسميات المشترك - كل الكلمات (التاريخ/الوقت/من/إلى/الطبيب) بتتحاذى هنا

        # ---- صف التاريخ ----
        ctk.CTkLabel(form_grid, text="التاريخ", font=theme.FONT_NORMAL).grid(
            row=0, column=LABEL_COL, sticky="e", padx=(10, 0), pady=6)
        date_display_btn = ctk.CTkButton(
            form_grid, text=f"📅 {selected_date_holder['date'].strftime('%Y-%m-%d')}",
            width=170, height=36, fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
            border_width=1, border_color=theme.BORDER, hover_color=theme.BG_MAIN,
            font=theme.FONT_NORMAL)
        date_display_btn.grid(row=0, column=0, columnspan=4, sticky="e", pady=6)

        def open_date_picker():
            picker = ctk.CTkToplevel(dialog)
            picker.title("اختيار التاريخ")
            # عرض الكالندر المنبثق زاد 50% (من 280 لـ420) عشان الأرقام
            # وأسماء الأيام تبان بوضوح أكتر
            picker_w, picker_h = 450, 380
            p_screen_w = picker.winfo_screenwidth()
            p_screen_h = picker.winfo_screenheight()
            p_x = (p_screen_w - picker_w) // 2
            p_y = (p_screen_h - picker_h) // 2
            picker.geometry(f"{picker_w}x{picker_h}+{p_x}+{p_y}")
            picker.grab_set()

            def on_pick(d):
                selected_date_holder["date"] = d
                date_display_btn.configure(text=f"📅 {d.strftime('%Y-%m-%d')}")
                picker.destroy()

            cal = MiniCalendar(picker, on_date_selected=on_pick, width=420)
            cal.pack(fill="both", expand=True, padx=10, pady=10)
            cal.jump_to(selected_date_holder["date"])

        date_display_btn.configure(command=open_date_picker)

        # ---- الوقت: نظام 12 ساعة (ص/م) هنا في نافذة الإضافة بس - شريط
        # الساعات في صفحة الكالندر الرئيسية فاضل بنظام 24 ساعة زي ما هو ----
        if prefill_time:
            start_h, start_m = map(int, prefill_time.split(":"))
        else:
            start_h, start_m = 10, 0
        end_h, end_m = start_h, start_m + 60  # افتراضيًا مدة ساعة كاملة
        if end_m >= 60:
            end_m -= 60
            end_h += 1
        end_h = end_h % 24

        def to_12h(hour24):
            ampm = "ص" if hour24 < 12 else "م"
            h12 = hour24 % 12
            if h12 == 0:
                h12 = 12
            return h12, ampm

        def to_24h(h12, ampm):
            h12 = h12 % 12
            return h12 + 12 if ampm == "م" else h12

        start_h12, start_ampm = to_12h(start_h)
        end_h12, end_ampm = to_12h(end_h)

        ampm_values = ["ص", "م"]

        # صف "الوقت" - عنوان بس، بيتحاذى في نفس عمود التسميات
        ctk.CTkLabel(form_grid, text="الوقت", font=theme.FONT_NORMAL).grid(
            row=1, column=LABEL_COL, sticky="e", padx=(10, 0), pady=(10, 2))

        # صفوف "من" و"إلى" - إدخال يدوي لخانتي الساعة والدقيقة (بدل القوائم
        # المنسدلة) مع انتقال تلقائي من خانة الساعات (شمال) لخانة الدقايق
        # (يمين)، وص/م بجانبها؛ كلمتي "من"/"إلى" بيتحاذوا مع باقي التسميات
        time_widgets = {}
        row_defs = [("من", "from", start_h12, start_ampm, start_m, 2),
                    ("إلى", "to", end_h12, end_ampm, end_m, 3)]
        for label_text, key, h12_val, ampm_val, m_val, r in row_defs:
            ctk.CTkLabel(form_grid, text=label_text, font=theme.FONT_NORMAL).grid(
                row=r, column=LABEL_COL, sticky="e", padx=(10, 0), pady=4)
            ampm_menu = ctk.CTkOptionMenu(form_grid, values=ampm_values, width=50, font=theme.FONT_NORMAL,
                                           **theme.optionmenu_colors())
            ampm_menu.set(ampm_val)
            ampm_menu.grid(row=r, column=3, sticky="e", padx=(6, 0), pady=4)
            time_entry = TimeAutoEntry(form_grid, hour_min=1, hour_max=12,
                                        entry_width=44, entry_height=32)
            time_entry.set_time(h12_val, m_val)
            time_entry.grid(row=r, column=0, columnspan=3, sticky="e", padx=1, pady=4)
            time_widgets[key] = {"time": time_entry, "ampm": ampm_menu}

        from_time = time_widgets["from"]["time"]
        from_ampm_menu = time_widgets["from"]["ampm"]
        to_time = time_widgets["to"]["time"]
        to_ampm_menu = time_widgets["to"]["ampm"]

        duration_warning = ctk.CTkLabel(form_grid, text="", font=theme.FONT_SMALL,
                                         text_color=theme.DANGER)
        duration_warning.grid(row=4, column=0, columnspan=5, sticky="e", pady=(2, 0))

        # ---- صف الطبيب - بيتحاذى في نفس عمود التسميات كمان ----
        ctk.CTkLabel(form_grid, text="الطبيب", font=theme.FONT_NORMAL).grid(
            row=5, column=LABEL_COL, sticky="e", padx=(10, 0), pady=(8, 4))
        doctors_list = db.get_doctors()
        doctor_names = [d["full_name"] for d in doctors_list] if doctors_list else ["لا يوجد أطباء مسجلين"]
        doctor_var = ctk.StringVar(value=doctor_names[0])
        ctk.CTkOptionMenu(form_grid, values=doctor_names, variable=doctor_var, width=210,
                          font=theme.FONT_NORMAL,
                          **theme.optionmenu_colors()).grid(row=5, column=0, columnspan=4, sticky="e",
                                                        pady=(8, 4))

        # ---- ملاحظات / شكوى المريض ----
        ctk.CTkLabel(top_area, text="ملاحظات / شكوى المريض", font=theme.FONT_NORMAL).pack(
            anchor="e", padx=24, pady=(10, 0))
        notes_box = ctk.CTkTextbox(top_area, width=470, height=60, font=theme.FONT_NORMAL)
        notes_box.pack(padx=24, pady=(4, 4), anchor="e")

        def save():
            selected_patient = selected_patient_holder["patient"]
            if not selected_patient:
                duration_warning.configure(text="⚠ لازم تختار مريض من نتائج البحث الأول")
                return
            fh = to_24h(from_time.get_hour(), from_ampm_menu.get())
            fm = from_time.get_minute()
            th = to_24h(to_time.get_hour(), to_ampm_menu.get())
            tm = to_time.get_minute()
            duration = (th * 60 + tm) - (fh * 60 + fm)
            if duration <= 0:
                duration_warning.configure(text="⚠ وقت النهاية لازم يكون بعد وقت البداية")
                return
            db.add_appointment(
                patient_id=selected_patient["id"],
                appt_date=selected_date_holder["date"].isoformat(),
                appt_time=f"{fh:02d}:{fm:02d}",
                doctor_name=doctor_var.get() if doctors_list else "",
                duration_minutes=duration,
                notes=notes_box.get("1.0", "end").strip(),
            )
            self._send_booking_confirmation(
                selected_patient, selected_date_holder["date"].isoformat(),
                f"{fh:02d}:{fm:02d}", doctor_var.get() if doctors_list else "")
            dialog.destroy()
            self.refresh()
            theme.show_toast(self, "تم حفظ الموعد")

        # زرار الحفظ - في أقصى شمال الصفحة، طويل رأسيًا بيغطي كل الجدول
        # (التاريخ + الوقت + الطبيب) وضيق أفقيًا
        save_btn = ctk.CTkButton(content_row, text="✔\nحفظ", width=80, height=220,
                                  fg_color=theme.SUCCESS, font=theme.FONT_NORMAL, command=save)
        save_btn.pack(side="left", padx=(0, 4), pady=(2, 0))

    def _send_booking_confirmation(self, patient, appt_date, appt_time, doctor_name):
        """بترسل رسالة تأكيد فورية للمريض لحظة تسجيل الموعد - مستقلة تمامًا
        عن تذكير الساعة قبل الموعد (اللي بيبعت لاحقًا في وقته المحدد بغض
        النظر عن الرسالة دي). أي خطأ هنا (رقم غير موجود، إعداد متوقف، إلخ)
        بيتجاهل بهدوء وميوقفش حفظ الموعد نفسه"""
        try:
            settings = db.get_settings()
            if not bool(settings.get("whatsapp_booking_confirmation_enabled", 1)):
                return
            templates = db.get_message_templates("booking_confirmation")
            if not templates:
                return
            selected_id = settings.get("whatsapp_auto_booking_template_id")
            template = next((t for t in templates if t["id"] == selected_id), None) or templates[0]
            whatsapp_number = db.get_whatsapp_number(patient["id"])
            if not whatsapp_number:
                return
            message = db.fill_message_template(
                template["template_text"], patient["full_name"], appt_date, appt_time,
                doctor_name=doctor_name or "", clinic_name=settings.get("clinic_name") or "")
            use_desktop = bool(settings.get("whatsapp_auto_use_desktop_app", 1))
            wa_sender.open_whatsapp_chat(whatsapp_number, message, use_desktop_app=use_desktop)
            if bool(settings.get("whatsapp_auto_confirm_send")):
                wait_seconds = max(3, int(settings.get("whatsapp_auto_wait_seconds") or 15))
                wa_sender.press_enter_later(self, wait_seconds * 1000)
        except Exception:
            pass

    def _on_appt_right_click(self, event, appt):
        # اتعكس الترتيب عن قبل: دلوقتي الضغطة العادية (يمين الماوس... لأ،
        # زرار الماوس الشمال) بتفتح ملف المريض على طول، وده الاستخدام
        # الأكتر شيوعًا (متابعة المريض)؛ الضغطة اليمين بقت هي اللي بتجيب
        # اختيار تفاصيل الحجز نفسه وتعديله (استخدام أقل تكرارًا)
        menu = tk.Menu(self, tearoff=0, font=theme.FONT_CONTEXT_MENU)
        menu.add_command(label="📅  تفاصيل الحجز وتعديله",
                          command=lambda: self._open_appt_details(appt))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_patient_file(self, patient_id):
        app = self.winfo_toplevel()
        if hasattr(app, "show_page"):
            app.show_page("patients", open_patient_id=patient_id)
