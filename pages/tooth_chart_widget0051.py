# -*- coding: utf-8 -*-
"""
مخطط الأسنان الاحترافي (Odontogram) - نظام رموز حقيقي:
- كل نوع علاج ليه رمز شكله يعبّر عنه (تاج، دعامة، زراعة، حشو بـ5 أسطح، جير، خلع)
- كل سن ممكن يحمل أكتر من رمز في نفس الوقت (تاج فوق دعامة مثلاً)
- لون كل رمز قابل للتحكم من صفحة الأسعار
"""

from collections import defaultdict

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageTk
import theme
import database as db
from pages import tooth_symbols
from pages import teething_timeline as teeth_time
from pages.date_auto_entry import DateAutoEntry

UPPER_ROW = teeth_time.UPPER_ROW
LOWER_ROW = teeth_time.LOWER_ROW

TOOTH_W, TOOTH_H = 50, 84

# نسبة تصغير حجم السن اللبني بالنسبة لنفس السن الدائم في نفس الموضع (السن
# اللبني أصغر فعليًا من الدائم اللي هيحل مكانه - بنحافظ على نفس النسب
# التشريحية للشكل، بس بمقاس أصغر ومركّز حول نفس خط اللثة)
PRIMARY_SCALE = 0.74


def _tooth_category(tooth_num):
    """بيحدد نوع السن من آخر رقم في ترقيم FDI، عشان نرسم شكل واقعي مختلف
    لكل نوع (قواطع/أنياب/ضواحك/أضراس) زي أسنان حقيقية مش شكل واحد لكل الأسنان.
    الأسنان اللبنية (أرباع ٥-٨) مفيهاش ضواحك أصلاً - موضعي ٤ و٥ عندها
    بيشغلهم "ضرس لبني" (شكل ضرس حقيقي مصغّر) مش ضاحك، زي التشريح الحقيقي"""
    is_primary = (tooth_num // 10) >= 5
    pos = tooth_num % 10
    if pos in (1, 2):
        return "incisor"
    if pos == 3:
        return "canine"
    if pos in (4, 5):
        return "molar" if is_primary else "premolar"
    return "molar"


def _tooth_geometry(category, upper, jaw_upper):
    """بترجع نقط رسم السن: (crown, roots, outline).
    - outline: مسار واحد متصل بيرسم السن كله (تاج + جذر/جذور) كشكل فراغي
      واحد من غير أي خط فاصل بين التاج والجذر - هو ده اللي بيتلوّن فعليًا.
      الجذور المتعددة (زي جذور الضرس) بتتفرّع من نفس الجسم وتتباعد عن بعضها
      لحد أطرافها (زي أصابع اليد) بدل ما تبان ملزّقة/متوازية جنب بعض.
    - crown / roots: بيانات مساعدة (مش بترسم لوحدها) بتستخدم في حسابات
      تانية (خط علاج العصب في كل جذر، مكان رمز التاج الصناعي، إلخ).
    كل الأشكال متحسوبة في اتجاه "سن فوقاني" (تاج لفوق، جذر لتحت)، وبتتعكس
    تلقائيًا حسب اتجاه الرسم (upper). عدد جذور الضرس بيتحدد من وضع الفك
    الحقيقي (jaw_upper) مش من اتجاه الرسم، عشان الضرس العلوي الحقيقي ياخد
    3 جذور والسفلي ياخد جذرين زي التشريح الحقيقي بالظبط. خط اللثة (نهاية
    التاج/بداية الجذر) فاضل ثابت عند نفس الارتفاع لكل الأنواع عشان باقي
    الرموز (حشو، تسوس، جير، علاج عصب) تتحط في مكانها الصح بالظبط"""
    GUM_Y = 34
    if category == "incisor":
        crown = [(15, 6), (35, 6), (36, 22), (33, GUM_Y), (17, GUM_Y), (14, 22)]
        roots = [[(18, GUM_Y), (32, GUM_Y), (25, 80)]]
        outline = [(15, 6), (35, 6), (36, 22), (33, GUM_Y), (25, 80), (17, GUM_Y), (14, 22)]
    elif category == "canine":
        crown = [(25, 4), (37, 22), (35, GUM_Y), (15, GUM_Y), (13, 22)]
        roots = [[(17, GUM_Y), (33, GUM_Y), (25, 82)]]
        outline = [(25, 4), (37, 22), (35, GUM_Y), (25, 82), (15, GUM_Y), (13, 22)]
    elif category == "premolar":
        crown = [(14, 16), (20, 6), (25, 12), (30, 6), (36, 16), (37, GUM_Y), (13, GUM_Y)]
        roots = [[(16, GUM_Y), (34, GUM_Y), (25, 78)]]
        outline = [(14, 16), (20, 6), (25, 12), (30, 6), (36, 16), (37, GUM_Y),
                   (25, 78), (13, GUM_Y)]
    else:  # molar
        # نهاية التاج (43,28)/(7,28) لازم تتطابق بالظبط مع نقط "كتف" التاج
        # في المسار الموحّد outline تحت - عشان رمز التاج الصناعي (الطربوش)
        # لما يترسم فوق بنفس شكل crown ده يغطي التاج الأصلي بالظبط من غير
        # ما يزيد عليه أو ينقص، ومن غير أي خط/فرق شكل بينه وبين الجسم اللي تحته
        crown = [(7, 18), (13, 6), (19, 14), (25, 6), (31, 14), (37, 6), (43, 18), (43, 28), (7, 28)]
        if jaw_upper:
            # الضرس العلوي الحقيقي بيه 3 جذور (لثوي وفلحي أمامي وفلحي خلفي) - مش 2
            roots = [
                [(8, GUM_Y), (18, GUM_Y), (13, 76)],
                [(19, GUM_Y), (31, GUM_Y), (25, 80)],
                [(32, GUM_Y), (42, GUM_Y), (37, 76)],
            ]
            # مسار واحد متصل: من كتف التاج الأيمن، بره الجذر البعيد وبتاعد
            # لطرفه، راجع لوادي ضيق قريب من خط اللثة (مش نازل لنص الجذر)
            # يفصله عن الجذر الأوسط، وهكذا للجذر التالت - كل جذر بيبان
            # واضح متباعد عن التاني زي أصابع منفرجة (مش بمجرد شق رفيع)
            # زي التشريح الحقيقي، وبيرجعوا يتلاقوا في قاعدة واحدة قريبة
            # جدًا من خط اللثة (مش نازلين ملتصقين لنص الجذر)
            outline = [
                (7, 18), (13, 6), (19, 14), (25, 6), (31, 14), (37, 6), (43, 18),
                (43, 28),
                (48, 36), (47, 52), (42, 68), (38, 78),
                (33, 64), (31, 50), (30, 40),
                (27, 50), (26, 64), (25, 80),
                (24, 64), (23, 50), (20, 40),
                (17, 50), (15, 64), (12, 78),
                (7, 68), (3, 52), (2, 36),
                (7, 28),
            ]
        else:
            # الضرس السفلي الحقيقي بيه جذرين (أمامي وخلفي)
            roots = [
                [(10, GUM_Y), (23, GUM_Y), (16, 76)],
                [(27, GUM_Y), (40, GUM_Y), (34, 76)],
            ]
            outline = [
                (7, 18), (13, 6), (19, 14), (25, 6), (31, 14), (37, 6), (43, 18),
                (43, 28),
                (47, 38), (46, 56), (40, 72), (35, 82),
                (29, 68), (26, 54), (25, 42),
                (23, 54), (20, 68), (15, 82),
                (10, 72), (4, 56), (3, 38),
                (7, 28),
            ]

    if not upper:
        crown = [(x, TOOTH_H - y) for x, y in crown]
        roots = [[(x, TOOTH_H - y) for x, y in pts] for pts in roots]
        outline = [(x, TOOTH_H - y) for x, y in outline]
    return crown, roots, outline


def _scale_shape(crown, roots, outline, upper, scale):
    """بتصغّر شكل السن كله (تاج وجذر/جذور والمسار الموحّد) حوالين نقطة
    ارتكاز عند منتصف خط اللثة أفقيًا وعليه رأسيًا - بيحافظ على نفس النسب
    التشريحية بالظبط (نفس الشكل تمامًا) بس بحجم أصغر، وفاضل ملتصق بخط
    اللثة زي ما هو (السن اللبني فعليًا أصغر من الدائم اللي هيحل مكانه لكنه
    بيبان من نفس المكان)"""
    if scale >= 0.999:
        return crown, roots, outline
    gum_y = 34 if upper else TOOTH_H - 34
    cx = TOOTH_W / 2

    def sc(pts):
        return [(cx + (x - cx) * scale, gum_y + (y - gum_y) * scale) for x, y in pts]

    return sc(crown), [sc(r) for r in roots], sc(outline)


# ترتيب أولوية العرض (اللي فوق بيترسم فوق اللي تحته)
SYMBOL_ORDER = ["implant", "post", "root_canal", "crown", "filled", "decay", "calculus", "extracted"]

# الأسطح الخمسة للحشو
SURFACES = [
    ("M", "قريب (وسطي)"),
    ("D", "بعيد (طرفي)"),
    ("O", "إطباقي/قاطع"),
    ("B", "دهليزي/وجني"),
    ("L", "لساني/حنكي"),
]

# ملحوظة: بنود العلاج مبقتش متسجلة هنا بشكل ثابت - بتتقرا مباشرة من قايمة
# الأسعار الحالية (نفس الأسماء ونفس الأنواع الفرعية بالظبط)، عشان أي تعديل
# في صفحة الأسعار (إضافة/حذف/تغيير اسم بند) ينعكس هنا تلقائيًا من غير أي
# تكرار أو اختلاف بين الصفحتين

# ---------------- ألوان مينا السن الأساسية (قبل أي رمز علاج فوقها) ----------------
# السن الدائم: لون عاجي فاتح. السن اللبني: لون مائل للأزرق الفاتح - واضح
# بصريًا إنه لبني من أول نظرة، غير لون أي رمز علاج (اللي بييجي فوقه لاحقًا)
PERMANENT_ENAMEL = "#F6F3EC"
PRIMARY_ENAMEL = "#E4F1FF"

# ألوان حالات "عدم وجود السن الفعلي" (شبح/تخطيطي بس مش سن حقيقي مرسوم)
GHOST_COLORS = {
    "unerupted": "#B7BEC9",   # لسه ما بزغش - طبيعي حسب السن (رمادي محايد)
    "missing": "#D98C8C",     # مفقود / غير موجود (أحمر باهت)
    "impacted": "#D6A24E",    # مطمور (كهرماني)
}


def _hex_to_rgb(hex_color):
    hex_color = (hex_color or "#9E9E9E").lstrip("#")
    if len(hex_color) != 6:
        hex_color = "9E9E9E"
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c))) for c in rgb)


def _shade(hex_color, factor):
    """بتفتّح (factor موجب لحد ١) أو بتغمّق (factor سالب لحد -١) لون معين -
    الأساس اللي بنبني بيه إحساس الإضاءة والظل (شكل شبه ثلاثي الأبعاد) على
    أشكال مسطحة في الـCanvas"""
    r, g, b = _hex_to_rgb(hex_color)
    if factor >= 0:
        r += (255 - r) * factor
        g += (255 - g) * factor
        b += (255 - b) * factor
    else:
        f = 1 + factor
        r, g, b = r * f, g * f, b * f
    return _rgb_to_hex((r, g, b))


def _blend(color_hex, base_hex, alpha):
    """بتخلط لون (color_hex) فوق لون تحته (base_hex) بنسبة شفافية alpha
    (٠ = شفاف تمامًا وبيبان اللون اللي تحت بس، ١ = اللون الأصلي صافي من
    غير شفافية) - ده الحل البديل لعدم دعم Tkinter Canvas لشفافية حقيقية
    (alpha) على الأشكال، فبدل كده بنحسب لون وسط بين اللونين يدّي إحساس
    الشفافية بصريًا"""
    r1, g1, b1 = _hex_to_rgb(color_hex)
    r2, g2, b2 = _hex_to_rgb(base_hex)
    return _rgb_to_hex((
        r2 + (r1 - r2) * alpha,
        g2 + (g1 - g2) * alpha,
        b2 + (b1 - b2) * alpha,
    ))


def _draw_shaded_polygon(canvas, pts, base_color, glossy=True, outline_color=None, crown_at_top=True):
    """بترسم مضلع (تاج/جذر) بإحساس ثلاثي الأبعاد بسيط: تظليل خفيف على
    الجسم كله + بقعة لمعان (Highlight) بتوحي بانعكاس ضوء على سطح لامع
    محدّب، بدل التلوين المسطح العادي. بقعة اللمعة لازم تفضل دايمًا ناحية
    التاج (الجزء الظاهر في الفم) مش ناحية الجذر - عشان كده لازم نحدد فين
    التاج فعليًا في نظام الإحداثيات الحالي (crown_at_top): في الصف السفلي
    التاج فوق (crown_at_top=True)، وفي الصف العلوي التاج بقى تحت بعد قلب
    الاتجاه (crown_at_top=False) - فلازم بقعة اللمعة تتبع الاتجاه ده"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)

    outline = outline_color or _shade(base_color, -0.45)
    canvas.create_polygon(*[c for p in pts for c in p], fill=_shade(base_color, -0.04),
                           outline=outline, width=1, smooth=True)

    if glossy and (max_x - min_x) > 6 and (max_y - min_y) > 6:
        light_x = min_x + (max_x - min_x) * 0.36
        if crown_at_top:
            light_y = min_y + (max_y - min_y) * 0.28
        else:
            light_y = max_y - (max_y - min_y) * 0.28
        hi_pts = [(light_x + (x - light_x) * 0.4, light_y + (y - light_y) * 0.4) for x, y in pts]
        canvas.create_polygon(*[c for p in hi_pts for c in p], fill=_shade(base_color, 0.55),
                               outline="", smooth=True)
        canvas.create_oval(light_x - 2.5, light_y - 2.5, light_x + 2, light_y + 1.5,
                            fill=_shade(base_color, 0.85), outline="")


class ToothChart(ctk.CTkFrame):
    def __init__(self, master, patient_id, current_user=None, on_change=None, **kwargs):
        super().__init__(master, fg_color=theme.CARD_BG, corner_radius=12, **kwargs)
        self.patient_id = patient_id
        self.current_user = current_user
        self.on_change = on_change
        self.active_conditions = {}
        self.tooth_canvases = {}
        self.tooth_labels = {}
        self.note_markers = {}
        self.selected_tooth = None
        self.selected_teeth = set()
        self.prices_cache = {}
        self.presence_map = {}
        self.tooth_annotations = {}
        self.age_months = None
        self._tooth_tooltip = None
        self._rubber_band_start = None
        self._rubber_band_drag_happened = False
        self._rubber_band_win = None
        self._build()
        self.refresh()

    def _build(self):
        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(8, 2))
        ctk.CTkLabel(title_row, text="خريطة الأسنان", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")

        self.selection_label = ctk.CTkLabel(
            title_row, text="اختر سن من الأسفل عشان تحدد حالته",
            font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED)
        self.selection_label.pack(side="left")

        # اختيار الطبيب المعالج - رافعه لفوق جنب صف العمر مباشرة (قبل شارت
        # الأسنان نفسه) عشان يفضل ظاهر دايمًا من غير ما تحتاجي تنزلي بالسكرول
        # عشان توصليله، خصوصًا إنه أهم حاجة لازم تتحددد قبل تسجيل أي معالجة
        doctor_row = ctk.CTkFrame(self, fg_color="transparent")
        doctor_row.pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkLabel(doctor_row, text="الطبيب المعالج:", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_MUTED).pack(side="right", padx=(0, 8))

        doctors = db.get_doctors()
        PLACEHOLDER_DOCTOR = "-- اختر الطبيب --"
        doctor_names = [PLACEHOLDER_DOCTOR] + [d["full_name"] for d in doctors] if doctors else ["لا يوجد أطباء مسجلين - ضيفي من الإعدادات"]
        default_doctor = doctor_names[0]
        if self.current_user and self.current_user["role"] == "doctor" and doctors:
            default_doctor = self.current_user["full_name"]

        self.doctor_menu = ctk.CTkOptionMenu(doctor_row, values=doctor_names, width=200, height=34,
                                              **theme.optionmenu_colors())
        self.doctor_menu.set(default_doctor)
        self.doctor_menu.pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=10)

        chart_col = ctk.CTkFrame(body, fg_color="transparent")
        chart_col.pack(side="right", fill="both", expand=True)

        row_upper = ctk.CTkFrame(chart_col, fg_color="transparent")
        row_upper.pack(pady=(4, 1))
        for i, t in enumerate(UPPER_ROW):
            # خط رأسي فاصل في نص الصف بالظبط (بين سن 11 وسن 21) - يفصل بصريًا
            # بين نص الشارت اليمين ونص الشارت الشمال، عشان يبقى أسهل للعين
            # إنها تميّز بين النصين من غير ما تعدّي الأسنان واحد واحد
            if i == len(UPPER_ROW) // 2:
                ctk.CTkFrame(row_upper, fg_color=theme.BORDER, width=2,
                             height=TOOTH_H + 30).pack(side="left", padx=4)
            self._make_tooth(row_upper, t, upper=True)

        divider = ctk.CTkFrame(chart_col, fg_color=theme.BORDER, height=2)
        divider.pack(fill="x", padx=20, pady=3)

        row_lower = ctk.CTkFrame(chart_col, fg_color="transparent")
        row_lower.pack(pady=(1, 3))
        for i, t in enumerate(LOWER_ROW):
            if i == len(LOWER_ROW) // 2:
                ctk.CTkFrame(row_lower, fg_color=theme.BORDER, width=2,
                             height=TOOTH_H + 30).pack(side="left", padx=4)
            self._make_tooth(row_lower, t, upper=False)

        # مفتاح الألوان (بيتقرأ من قائمة الأسعار الحالية)
        legend_col = ctk.CTkFrame(body, fg_color=theme.BG_MAIN, corner_radius=10)
        legend_col.pack(side="left", padx=(10, 0), pady=3, fill="y")
        ctk.CTkLabel(legend_col, text="المفتاح", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(pady=(8, 4), padx=14)
        self.legend_frame = ctk.CTkFrame(legend_col, fg_color="transparent")
        self.legend_frame.pack(padx=14, pady=(0, 8))

        # شريط العلاجات السريع - رافعه لفوق جنب الشارت مباشرة (بدل ما يكون
        # تحت اختيار الطبيب والملاحظة) عشان يبقى قريب وسهل الوصول من غير سكرول
        toolbar = ctk.CTkFrame(self, fg_color=theme.BG_MAIN, corner_radius=10)
        toolbar.pack(fill="x", padx=16, pady=(3, 3))

        ctk.CTkLabel(toolbar, text="حدد سن، وبعدين دوس نوع العلاج", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(pady=(4, 0))

        self.btns_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        self.btns_row.pack(pady=4)

        # لوحة تفاصيل المعالجات - ثابتة تحت الشارت طول الوقت (مش تلميح
        # بيظهر بالهوفر بس)، بتتحدث تلقائيًا مع أي اختيار سن جديد. ارتفاعها
        # محدود بسقف أقصى مع سكرول داخلي خاص بيها، عشان لو سن فيه معالجات
        # كتير أوي ما يكبرش الكارت على حساب باقي الصفحة (وتفضل الصفحة كلها
        # ظاهرة من غير سكرول عام)
        details_card = ctk.CTkFrame(self, fg_color=theme.BG_MAIN, corner_radius=10)
        details_card.pack(fill="x", padx=16, pady=(0, 3))
        ctk.CTkLabel(details_card, text="تفاصيل المعالجات على السن المحدد", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_DARK).pack(anchor="e", padx=12, pady=(6, 2))
        self.details_frame = ctk.CTkScrollableFrame(details_card, fg_color="transparent",
                                                      height=64)
        self.details_frame.pack(fill="x", padx=12, pady=(0, 8))

    def _make_tooth(self, parent, tooth_num, upper):
        # ترقيم/اتجاه شارت الأسنان بيتبع الاتفاق التشريحي الدولي (FDI) مش
        # اتجاه الكتابة العربي: بيبقى وإحنا واقفين قصاد المريض (زي الشارت
        # في أي عيادة)، فسن 18 لازم يبان أقصى الشمال فوق وسن 28 أقصى اليمين
        # فوق، وتحتهم بالظبط سن 48 أقصى الشمال وسن 38 أقصى اليمين - عشان
        # كده هنا تحديدًا بنعمل pack من الشمال لليمين (side="left") بغض
        # النظر إن باقي الصفحة RTL
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.pack(side="left", padx=1)

        # علامة صغيرة قابلة للضغط بتظهر بس لو السن ده عليه ملحوظة مفصّلة
        # (تاريخ+طبيب+نص) - فوق الأسنان العلوية وتحت الأسنان السفلية، عشان
        # تبان في اتجاه اللثة الطبيعي لكل صف
        note_marker = tk.Label(wrapper, text=" ", font=(theme.FONT_FAMILY, 11, "bold"),
                                bg=theme.CARD_BG, fg=theme.CARD_BG, cursor="hand2")
        note_marker.bind("<Button-1>", lambda e, t=tooth_num: self._open_tooth_annotation_view(t))

        label = tk.Label(wrapper, text=str(tooth_num), font=(theme.FONT_FAMILY, 11, "bold"),
                          bg=theme.CARD_BG, fg="#8A6D00")
        if upper:
            note_marker.pack()
            label.pack()

        canvas = tk.Canvas(wrapper, width=TOOTH_W, height=TOOTH_H, bg=theme.CARD_BG,
                            highlightthickness=0, cursor="hand2")
        canvas.pack()
        canvas.bind("<Button-1>", lambda e, t=tooth_num: self._on_tooth_click(e, t))
        canvas.bind("<B1-Motion>", lambda e, t=tooth_num: self._on_tooth_drag(e, t))
        canvas.bind("<ButtonRelease-1>", lambda e, t=tooth_num: self._on_tooth_release(e, t))
        canvas.bind("<Button-3>", lambda e, t=tooth_num: self._on_tooth_right_click(e, t))
        canvas.bind("<Enter>", lambda e, t=tooth_num: self._show_tooth_tooltip(e, t))
        canvas.bind("<Leave>", lambda e: self._hide_tooth_tooltip())

        if not upper:
            label.pack()
            note_marker.pack()

        self.tooth_canvases[tooth_num] = (canvas, upper)
        self.tooth_labels[tooth_num] = label
        self.note_markers[tooth_num] = note_marker

    def _show_tooth_tooltip(self, event, tooth_num):
        self._hide_tooth_tooltip()
        presence, _auto = self._slot_presence(tooth_num)
        active_num = self._active_number(tooth_num, presence)
        # بنعرض هنا "كل" المعالجات اللي اتعملت على السن ده عبر الزمن (مش
        # بس الحالة الحالية النشطة زي active_conditions) - عشان لو مثلاً
        # اتحشى مرتين في تاريخه، الاتنين يبانوا في التلميح بتاريخهم والطبيب
        # اللي عملهم، مش آخر واحدة بس
        history = self.tooth_history.get(active_num, [])
        if not history and presence == teeth_time.PRESENT:
            return

        tooltip = tk.Toplevel(self)
        tooltip.overrideredirect(True)
        tooltip.attributes("-topmost", True)
        tooltip.configure(bg=theme.TEXT_DARK)

        card = ctk.CTkFrame(tooltip, fg_color=theme.CARD_BG, corner_radius=8,
                             border_width=1, border_color=theme.BORDER)
        card.pack(padx=1, pady=1)

        title = f"سن {tooth_num}" if active_num == tooth_num else f"سن {tooth_num}  (لبني {active_num})"
        ctk.CTkLabel(card, text=title, font=(theme.CONTENT_FONT_FAMILY, 13, "bold"),
                     text_color=theme.TEXT_DARK).pack(anchor="e", padx=10, pady=(8, 2))

        if presence != teeth_time.PRESENT:
            prow = ctk.CTkFrame(card, fg_color="transparent")
            prow.pack(anchor="e", padx=10, pady=2, fill="x")
            ctk.CTkLabel(prow, text="  ", fg_color=GHOST_COLORS.get(presence, "#9E9E9E"),
                         width=10, height=10, corner_radius=5).pack(side="right", padx=(4, 0))
            ctk.CTkLabel(prow, text=teeth_time.PRESENCE_LABELS.get(presence, presence),
                         font=(theme.CONTENT_FONT_FAMILY, 12),
                         text_color=theme.TEXT_DARK).pack(side="right")

        for record in history:
            key = record.get("treatment_key")
            label = record.get("treatment_label") or self._label_for(key)
            variant_name = record.get("variant_name")
            text = f"{label} - {variant_name}" if variant_name else label
            meta_bits = [b for b in (record.get("doctor_name"), record.get("treatment_date")) if b]
            if meta_bits:
                text += "   (" + "  -  ".join(meta_bits) + ")"
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(anchor="e", padx=10, pady=2, fill="x")
            dot_color = record.get("variant_color") or self._color_for(key)
            ctk.CTkLabel(row, text="  ", fg_color=dot_color,
                         width=10, height=10, corner_radius=5).pack(side="right", padx=(4, 0))
            ctk.CTkLabel(row, text=text, font=(theme.CONTENT_FONT_FAMILY, 12),
                         text_color=theme.TEXT_DARK).pack(side="right")

        ctk.CTkFrame(card, fg_color="transparent", height=4).pack()

        tooltip.update_idletasks()
        x = event.x_root + 14
        y = event.y_root + 10
        screen_w = tooltip.winfo_screenwidth()
        screen_h = tooltip.winfo_screenheight()
        tip_w = tooltip.winfo_width()
        tip_h = tooltip.winfo_height()
        if x + tip_w > screen_w:
            x = event.x_root - tip_w - 14
        if y + tip_h > screen_h:
            y = event.y_root - tip_h - 10
        tooltip.geometry(f"+{x}+{y}")

        self._tooth_tooltip = tooltip

    def _hide_tooth_tooltip(self):
        tooltip = getattr(self, "_tooth_tooltip", None)
        if tooltip is not None:
            try:
                tooltip.destroy()
            except Exception:
                pass
            self._tooth_tooltip = None

    # ---------------- تحديث عام ----------------

    def refresh(self):
        self._hide_tooth_tooltip()
        active_list_id = db.get_settings()["active_price_list_id"]
        self.prices_cache = db.get_treatment_prices(active_list_id) if active_list_id else {}
        self.active_conditions = db.get_active_tooth_conditions(self.patient_id)

        # سجل كامل لكل معالجة اتعملت على كل سن عبر الزمن (مش بس الحالة
        # النشطة الحالية) - ده اللي التلميح (تولتيب) بيعرضه لما تعمل هوفر،
        # عشان يبان تاريخ وطبيب كل معالجة حتى لو استُبدلت بعد كده
        self.tooth_history = defaultdict(list)
        for r in db.get_treatment_records(self.patient_id):
            tooth = r.get("tooth_number")
            if tooth is None or r.get("treatment_key") == "healthy":
                continue
            self.tooth_history[tooth].append(r)

        patient = db.get_patient(self.patient_id) or {}
        self.age_months = teeth_time.age_in_months(patient.get("birth_date"))
        self.presence_map = db.get_tooth_presence(self.patient_id)
        self.tooth_annotations = db.get_tooth_annotations_map(self.patient_id)

        self._build_toolbar()
        for tooth_num in self.tooth_canvases:
            self._draw_tooth(tooth_num)
        self._render_legend()
        self._render_details()
        self._update_note_markers()

    def _update_note_markers(self):
        """بتحدّث شكل علامة الملحوظة فوق/تحت كل سن حسب وجود ملحوظة مفصّلة
        مسجلة على السن الفعلي النشط (رقم لبني أو دائم حسب الوضع الحالي)"""
        for tooth_num, marker in self.note_markers.items():
            presence, _auto = self._slot_presence(tooth_num)
            active_num = self._active_number(tooth_num, presence)
            has_note = active_num in self.tooth_annotations
            if has_note:
                marker.configure(text="📝", fg=theme.PRIMARY_LIGHT, cursor="hand2")
            else:
                marker.configure(text=" ", fg=theme.CARD_BG, cursor="arrow")

    def _slot_presence(self, tooth_num):
        """بترجع (status, is_auto) لموضع سن معين (رقم FDI الدائم) - لو
        فيه حالة محفوظة (سواء يدوية أو تلقائية) بتترجع هي، غير كده وعمر
        المريض معروف بتتحسب لحظيًا من الجدول الزمني للتسنين (من غير ما
        تتخزن لحد ما المستخدم يدوس "توليد الخريطة")"""
        rec = self.presence_map.get(tooth_num)
        if rec:
            return rec["status"], rec["auto"]
        if self.age_months is not None:
            pos = tooth_num % 10
            jaw_upper = tooth_num < 30
            status = teeth_time.expected_presence(pos, jaw_upper, self.age_months, 0)
            return status, True
        return teeth_time.PRESENT, True

    def _active_number(self, tooth_num, presence=None):
        """رقم السن الفعلي اللي المفروض يتسجل عليه أي علاج/ملاحظة دلوقتي:
        رقم السن اللبني لو لسه موجود ومحلّش الدائم مكانه، وإلا رقم السن
        الدائم العادي (رقم الموضع نفسه)"""
        if presence is None:
            presence = self._slot_presence(tooth_num)[0]
        if presence == teeth_time.PRIMARY_PRESENT:
            return teeth_time.primary_number_for(tooth_num) or tooth_num
        return tooth_num

    def _build_toolbar(self):
        """بتبني أزرار العلاج السريع مباشرة من قايمة الأسعار الحالية بنفس
        الأسماء بالظبط - أي بند مش موجود في صفحة الأسعار مش هيظهر هنا"""
        for w in self.btns_row.winfo_children():
            w.destroy()
        # ترتيب العرض بيتبع أولوية الرسم المعتادة، وأي بند زيادة (مش من
        # SYMBOL_ORDER) بيتضاف في الآخر عشان محدش يضيع
        ordered_keys = [k for k in SYMBOL_ORDER if k in self.prices_cache]
        ordered_keys += [k for k in self.prices_cache if k not in ordered_keys]
        for status_key in ordered_keys:
            label = self.prices_cache[status_key]["label"]
            ctk.CTkButton(
                self.btns_row, text=label, width=120, height=36,
                font=theme.FONT_NORMAL, corner_radius=8,
                fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
                border_width=1, border_color=theme.BORDER, hover_color=theme.BG_MAIN,
                command=lambda s=status_key: self._on_treatment_click(s)
            ).pack(side="right", padx=4, pady=4)

    def _on_tooth_right_click(self, event, tooth_num):
        presence, _auto = self._slot_presence(tooth_num)
        active_num = self._active_number(tooth_num, presence)
        conditions = self.active_conditions.get(active_num, {})

        menu = tk.Menu(self, tearoff=0)

        presence_menu = tk.Menu(menu, tearoff=0)
        for status in teeth_time.PRESENCE_CHOICES:
            mark = "● " if status == presence else "   "
            presence_menu.add_command(
                label=mark + teeth_time.PRESENCE_LABELS[status],
                command=lambda s=status, t=tooth_num: self._set_presence(t, s))
        menu.add_cascade(label="🦷 حالة بزوغ السن", menu=presence_menu)

        if conditions:
            menu.add_separator()
            for key, record in conditions.items():
                label = self._label_for(key)
                if record.get("variant_name"):
                    label += f" ({record['variant_name']})"
                menu.add_command(
                    label=f"🗑 حذف: {label}",
                    command=lambda rid=record["id"], t=tooth_num: self._delete_condition(rid, t))

        menu.add_separator()
        has_note = active_num in self.tooth_annotations
        note_label = "📝 تعديل الملحوظة" if has_note else "📝 إضافة ملحوظة"
        menu.add_command(label=note_label,
                          command=lambda t=tooth_num: self._open_tooth_annotation_dialog(t))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _set_presence(self, tooth_num, status):
        db.set_tooth_presence(self.patient_id, tooth_num, status, auto=False)
        self.refresh()
        self._select_tooth(tooth_num)
        if self.on_change:
            self.on_change()

    def _delete_condition(self, record_id, tooth_num):
        db.delete_treatment_record(record_id)
        self.refresh()
        self._select_tooth(tooth_num)
        if self.on_change:
            self.on_change()

    def _delete_condition_multi(self, record_ids):
        """بتمسح نفس نوع المعالجة من كل الأسنان المحددة سويًا مرة واحدة
        (بدل ما تمسح من سن واحد بس زي ما كان بيحصل قبل كده لما يبقى فيه
        أكتر من سن محدد في نفس الوقت)"""
        for record_id in record_ids:
            db.delete_treatment_record(record_id)
        self.refresh()
        self._refresh_selection_visuals()
        if self.on_change:
            self.on_change()

    def _color_for(self, treatment_key, conditions=None, fallback="#9E9E9E"):
        if conditions:
            record = conditions.get(treatment_key)
            if record and record.get("variant_color"):
                return record["variant_color"]
        info = self.prices_cache.get(treatment_key)
        if info and info.get("color"):
            return info["color"]
        return fallback

    def _label_for(self, treatment_key):
        info = self.prices_cache.get(treatment_key)
        if info:
            return info["label"]
        return treatment_key

    def _render_legend(self):
        for w in self.legend_frame.winfo_children():
            w.destroy()

        entries = [(self._color_for(key), self._label_for(key), False) for key in self.prices_cache]
        entries += [
            (PRIMARY_ENAMEL, "سن لبني (لم يسقط)", True),
            (GHOST_COLORS["unerupted"], "لم يبزغ (طبيعي)", True),
            (GHOST_COLORS["missing"], "مفقود", True),
            (GHOST_COLORS["impacted"], "مطمور", True),
        ]

        # شبكة عمودين (مش عمود واحد طويل) عشان المفتاح كله يبان من غير
        # ما يحتاج سكرول، حتى لو عدد البنود كتر
        row = col = 0
        for color, label, ghost in entries:
            item = ctk.CTkFrame(self.legend_frame, fg_color="transparent")
            item.grid(row=row, column=col, sticky="e", padx=(4, 8), pady=2)
            ctk.CTkLabel(item, text="  ", fg_color=color, width=11, height=11, corner_radius=5,
                         border_width=1 if ghost else 0,
                         border_color=theme.BORDER).pack(side="right", padx=(3, 0))
            ctk.CTkLabel(item, text=label, font=(theme.CONTENT_FONT_FAMILY, 10),
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=3)
            col += 1
            if col >= 2:
                col = 0
                row += 1

    # ---------------- تفاصيل المعالجات (لوحة ثابتة تحت الشارت) ----------------

    def _render_details(self):
        for w in self.details_frame.winfo_children():
            w.destroy()

        if len(self.selected_teeth) > 1:
            self._render_details_multi()
            return

        if self.selected_tooth is None:
            ctk.CTkLabel(self.details_frame, text="اختر سن من الشارت فوق عشان تشوف تفاصيل حالته ومعالجاته هنا",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(anchor="e", pady=4)
            return

        presence, _auto = self._slot_presence(self.selected_tooth)
        active_num = self._active_number(self.selected_tooth, presence)
        conditions = self.active_conditions.get(active_num, {})

        if presence != teeth_time.PRESENT:
            ghost_color = PRIMARY_ENAMEL if presence == teeth_time.PRIMARY_PRESENT else GHOST_COLORS.get(presence, "#9E9E9E")
            row = ctk.CTkFrame(self.details_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text="  ", fg_color=ghost_color, width=12, height=12,
                         corner_radius=6, border_width=1, border_color=theme.BORDER).pack(side="right", padx=(6, 4))
            ctk.CTkLabel(row, text=teeth_time.PRESENCE_LABELS.get(presence, presence),
                         font=theme.FONT_SMALL, text_color=theme.TEXT_DARK).pack(side="right")

        if not conditions:
            if presence == teeth_time.PRESENT:
                ctk.CTkLabel(self.details_frame, text="مفيش معالجات مسجلة على السن ده - سليم",
                             font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(anchor="e", pady=2)
            return

        for key, record in conditions.items():
            label = record.get("treatment_label") or self._label_for(key)
            if record.get("variant_name"):
                label += f" ({record['variant_name']})"

            row = ctk.CTkFrame(self.details_frame, fg_color=theme.CARD_BG, corner_radius=8)
            row.pack(fill="x", pady=2)

            ctk.CTkButton(row, text="حذف", width=46, height=24, font=(theme.CONTENT_FONT_FAMILY, 11),
                          fg_color=theme.DANGER, hover_color=_shade(theme.DANGER, -0.15),
                          command=lambda rid=record["id"], t=self.selected_tooth: self._delete_condition(rid, t)
                          ).pack(side="left", padx=6, pady=5)

            info_bits = [label]
            if record.get("price"):
                info_bits.append(f"{record['price']:g} جنيه")
            if record.get("doctor_name"):
                info_bits.append(record["doctor_name"])
            if record.get("treatment_date"):
                info_bits.append(record["treatment_date"])
            ctk.CTkLabel(row, text="   •   ".join(info_bits), font=theme.FONT_SMALL,
                         text_color=theme.TEXT_DARK).pack(side="right", padx=8, pady=5)
            ctk.CTkLabel(row, text="  ", fg_color=self._color_for(key, conditions), width=12, height=12,
                         corner_radius=6).pack(side="right", padx=(0, 4), pady=5)

    def _render_details_multi(self):
        """نسخة من لوحة التفاصيل بتشتغل مع أكتر من سن محدد سويًا: بتجمّع
        نفس نوع المعالجة (ونفس الـvariant لو موجود) من كل الأسنان المحددة
        في صف واحد، وزرار الحذف بتاعه بيمسح المعالجة دي من كل الأسنان
        المحددة مرة واحدة (مش من سن واحد بس زي ما كان بيحصل قبل كده)"""
        groups = {}
        for tooth_num in sorted(self.selected_teeth):
            presence, _auto = self._slot_presence(tooth_num)
            active_num = self._active_number(tooth_num, presence)
            conditions = self.active_conditions.get(active_num, {})
            for key, record in conditions.items():
                variant = record.get("variant_name") or ""
                groups.setdefault((key, variant), []).append((tooth_num, record))

        if not groups:
            ctk.CTkLabel(self.details_frame,
                         text="مفيش معالجات مسجلة على الأسنان المحددة",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(anchor="e", pady=2)
            return

        for (key, variant), items in groups.items():
            label = self._label_for(key)
            if variant:
                label += f" ({variant})"
            teeth_txt = "، ".join(str(t) for t, _r in items)

            row = ctk.CTkFrame(self.details_frame, fg_color=theme.CARD_BG, corner_radius=8)
            row.pack(fill="x", pady=2)

            record_ids = [record["id"] for _t, record in items]
            ctk.CTkButton(row, text=f"حذف من {len(items)} سن", width=90, height=24,
                          font=(theme.CONTENT_FONT_FAMILY, 11),
                          fg_color=theme.DANGER, hover_color=_shade(theme.DANGER, -0.15),
                          command=lambda ids=record_ids: self._delete_condition_multi(ids)
                          ).pack(side="left", padx=6, pady=5)

            ctk.CTkLabel(row, text=f"{label}   -   الأسنان: {teeth_txt}", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_DARK).pack(side="right", padx=8, pady=5)
            ctk.CTkLabel(row, text="  ", fg_color=self._color_for(key, {key: items[0][1]}),
                         width=12, height=12, corner_radius=6).pack(side="right", padx=(0, 4), pady=5)

    # ---------------- رسم السن بكل رموزه ----------------

    def _draw_tooth(self, tooth_num):
        canvas, upper = self.tooth_canvases[tooth_num]
        canvas.delete("all")

        presence, _auto = self._slot_presence(tooth_num)
        active_num = self._active_number(tooth_num, presence)
        is_primary = (presence == teeth_time.PRIMARY_PRESENT)
        conditions = self.active_conditions.get(active_num, {})

        # تحديث رقم السن المعروض فوق/تحت الخانة: بيبان رقم السن اللبني
        # الفعلي (بلون مميز) لو ده اللي موجود فعلاً في الفم دلوقتي، غير
        # كده رقم السن الدائم العادي (رقم الموضع في الشارت)
        label = self.tooth_labels.get(tooth_num)
        if label is not None:
            if is_primary:
                label.configure(text=str(active_num), fg="#1E88E5")
            else:
                label.configure(text=str(tooth_num), fg="#8A6D00")

        # بزوغ السن: لو مش موجود فعلي دلوقتي (لسه ما بزغش/مفقود/مطمور)
        # ومفيش زراعة اتحطت مكانه، نرسم شبح تخطيطي بس (خط منقط، بدون تفاصيل
        # علاج) عشان نفرّق بصريًا إن ده مش سن حقيقي موجود في الفم
        if presence in (teeth_time.UNERUPTED, teeth_time.MISSING, teeth_time.IMPACTED) \
                and "implant" not in conditions:
            self._draw_ghost_tooth(canvas, tooth_num, upper, presence)
            self._draw_selection_ring(canvas, tooth_num)
            return

        # بنعكس اتجاه رسم التاج/الجذر: في الصف العلوي الجذر يبقى متجه لفوق
        # (بعيد عن خط الإطباق)، وفي الصف السفلي الجذر متجه لتحت. مكان السن
        # نفسه في الشارت (فوق/تحت) وترقيمه ما بيتأثرش، ده بس شكل الرسم جوه الخانة.
        jaw_upper = upper  # وضع الفك الحقيقي (فوقاني/سفلي) - ثابت، بيتحدد بيه عدد جذور الضرس
        upper = not upper

        cx = TOOTH_W // 2
        category = _tooth_category(active_num)
        crown_pts, root_polys, outline_pts = _tooth_geometry(category, upper, jaw_upper)
        if is_primary:
            crown_pts, root_polys, outline_pts = _scale_shape(crown_pts, root_polys, outline_pts, upper, PRIMARY_SCALE)

        # لو خلع: نرسم شكل السن الحقيقي كله (تاج وجذر كجسم واحد) باهت
        # وعلامة X فوقه ونوقف هنا
        if "extracted" in conditions:
            outline = self._color_for("extracted", conditions)
            canvas.create_polygon(*[c for p in outline_pts for c in p], outline=outline,
                                   width=1, fill="#F5F5F5", smooth=True)
            canvas.create_line(8, 8, TOOTH_W - 8, TOOTH_H - 8, fill=outline, width=3)
            canvas.create_line(TOOTH_W - 8, 8, 8, TOOTH_H - 8, fill=outline, width=3)
            self._draw_selection_ring(canvas, tooth_num)
            return

        crown_fill = PRIMARY_ENAMEL if is_primary else PERMANENT_ENAMEL
        crown_outline = _shade(crown_fill, -0.35)

        # كل بنود "التغطية الكاملة للتاج" المطبقة على السن ده دلوقتي (التاج
        # الجاهز crown + أي بند مخصص من نوع "طربوش" من صفحة الأسعار) - بتتجمع
        # هنا عشان تترسم كلها (مع الدعامة والحشو والتسوس والجير) مع بعض في
        # صورة واحدة بشفافية حقيقية عبر _draw_treatment_overlay بدل ما كل
        # واحدة تغطي اللي تحتها بالكامل زي ما كان بيحصل قبل كده
        coverage_colors = []
        if "crown" in conditions:
            coverage_colors.append(self._color_for("crown", conditions))
        custom_keys = [k for k in conditions if k not in tooth_symbols.BUILTIN_TREATMENT_KEYS]
        custom_cap_keys, custom_icon_keys = [], []
        for key in custom_keys:
            info = self.prices_cache.get(key, {})
            symbol_key = info.get("symbol_key")
            label = info.get("label") or conditions[key].get("treatment_label")
            if tooth_symbols.is_crown_cap(symbol_key, label):
                custom_cap_keys.append(key)
            else:
                custom_icon_keys.append(key)
        coverage_colors += [self._color_for(k, conditions) for k in custom_cap_keys]

        # جسم السن كله (تاج + جذر/جذور) بيترسم كمسار واحد متصل بلمعان/ظل
        # بسيط (شبه ثلاثي الأبعاد) - مفيش خط فاصل بين التاج والجذر، وجذور
        # الضرس متباعدة عن بعضها بوضوح لحد أطرافها زي التشريح الحقيقي.
        # الزراعة بس بتاخد مكان الجذر بشكل مسمار ملولب حقيقي بدل الجسم الطبيعي
        has_post = "post" in conditions and "implant" not in conditions
        if "implant" in conditions:
            self._draw_implant_root(canvas, upper, conditions)
            if not coverage_colors:
                _draw_shaded_polygon(canvas, crown_pts, crown_fill, glossy=True,
                                      outline_color=crown_outline, crown_at_top=upper)
            # لو فيه تاج فوق الزرعة هيترسم في الطبقة الشفافة الموحدة تحت
        else:
            if has_post:
                _draw_shaded_polygon(canvas, outline_pts, crown_fill, glossy=True,
                                      outline_color=crown_outline, crown_at_top=upper)
                # جسم الدعامة نفسه بيترسم في الطبقة الشفافة الموحدة تحت
            elif coverage_colors:
                # التاج الصناعي بيغطي الجزء الظاهر بس - نرسم الجذر الطبيعي
                # جوه (جزء من نفس الجسم الموحّد) والتاج هيترسم بشفافية فوقه
                _draw_shaded_polygon(canvas, outline_pts, crown_fill, glossy=False,
                                      outline_color=crown_outline, crown_at_top=upper)
            else:
                _draw_shaded_polygon(canvas, outline_pts, crown_fill, glossy=True,
                                      outline_color=crown_outline, crown_at_top=upper)

        # كل "طبقات" العلاج اللي بتغطي مساحة من السن (تاج/طربوش، دعامة،
        # حشو، تسوس، جير) بترسم مع بعض بشفافية حقيقية (per-pixel alpha عبر
        # PIL) في صورة واحدة، عشان لو أكتر من معالجة موجودة على نفس السن
        # كلهم يفضلوا باينين فوق بعض زي طبقات - مش آخر واحدة بس بتغطي
        # اللي قبلها. الميزيال (M) والديستال (D) في خانة الحشو بيتبادلوا
        # أماكنهم في النص الشمال من الشارت (أسنان 11-18 و41-48) عشان
        # الميزيال دايمًا لازم يبقى ناحية خط النص (المنتصف) بغض النظر عن
        # اتجاه رسم السن على الشاشة
        post_color = self._color_for("post", conditions) if has_post else None
        filled_record = conditions.get("filled")
        decay_color = self._color_for("decay", conditions) if ("decay" in conditions and "filled" not in conditions) else None
        calculus_color = self._color_for("calculus", conditions) if "calculus" in conditions else None
        quadrant = active_num // 10
        flip_md = quadrant in (1, 4, 5, 8)

        if coverage_colors or post_color or filled_record or decay_color or calculus_color:
            self._draw_treatment_overlay(canvas, upper, crown_pts, cx, coverage_colors, post_color,
                                          filled_record, decay_color, calculus_color, flip_md)

        # علاج العصب - خط رفيع في كل جذر من جذور السن نفسها (ضاحك = خط واحد،
        # ضرس سفلي = خطين، ضرس علوي = 3 خطوط - بالظبط بعدد الجذور المرسومة)
        if "root_canal" in conditions and "implant" not in conditions:
            color = self._color_for("root_canal", conditions)
            for root in root_polys:
                # كل جذر متعرف بـ3 نقط: أول اتنين على خط اللثة، والتالتة طرف
                # الجذر - بنرسم خط من قريب اللثة لحد قريب من الطرف
                gum_x = (root[0][0] + root[1][0]) / 2
                gum_y = root[0][1]
                tip_x, tip_y = root[2] if len(root) > 2 else root[-1]
                if tip_y > gum_y:
                    y_start, y_end = gum_y + 4, tip_y - 2
                else:
                    y_start, y_end = gum_y - 4, tip_y + 2
                canvas.create_line(gum_x, y_start, tip_x, y_end, fill=color, width=2)

        # أي بند علاجي "مخصص" مش من نوع تغطية كاملة (مش من البنود الأساسية
        # الجاهزة زي الجذر والخلع، ومش طربوش/تغطية كاملة - دي اتترسمت فوق
        # كطبقات شفافة في coverage_colors) - بيترسم برمزه الصغير ولونه
        # اللي اتحدد له في صفحة الأسعار
        if custom_icon_keys:
            spacing = 14
            start_x = cx - (len(custom_icon_keys) - 1) * spacing / 2
            sym_y = 14 if upper else TOOTH_H - 14
            for i, key in enumerate(custom_icon_keys):
                info = self.prices_cache.get(key, {})
                symbol_key = info.get("symbol_key") or tooth_symbols.DEFAULT_SYMBOL_KEY
                color = self._color_for(key, conditions)
                tooth_symbols.draw_symbol(canvas, symbol_key, start_x + i * spacing, sym_y, 6, color)

        self._draw_selection_ring(canvas, tooth_num)

    def _draw_ghost_tooth(self, canvas, tooth_num, upper, presence):
        """رسم تخطيطي "شبح" لسن مش موجود فعليًا دلوقتي (لسه ما بزغش/مفقود/
        مطمور) - خط منقط باهت بشكل السن الحقيقي (نفس تصنيفه التشريحي) من
        غير أي تلوين مليان أو تفاصيل علاج، عشان يبان بوضوح إنه مش سن حقيقي
        موجود في الفم دلوقتي، لكن يفضل واضح مكانه ونوعه في الشارت"""
        color = GHOST_COLORS.get(presence, "#B0B0B0")
        jaw_upper = upper
        draw_upper = not upper
        category = _tooth_category(tooth_num)
        crown_pts, root_polys, outline_pts = _tooth_geometry(category, draw_upper, jaw_upper)
        crown_pts, root_polys, outline_pts = _scale_shape(crown_pts, root_polys, outline_pts, draw_upper, 0.86)

        canvas.create_polygon(*[c for p in outline_pts for c in p], outline=color,
                               fill="", width=1, dash=(3, 2), smooth=True)

        cx = TOOTH_W // 2
        icon_y = 18 if draw_upper else TOOTH_H - 18
        if presence == teeth_time.MISSING:
            canvas.create_line(cx - 5, icon_y - 5, cx + 5, icon_y + 5, fill=color, width=2)
            canvas.create_line(cx + 5, icon_y - 5, cx - 5, icon_y + 5, fill=color, width=2)
        elif presence == teeth_time.IMPACTED:
            canvas.create_line(cx, icon_y + 6, cx, icon_y - 6, fill=color, width=2, arrow="last")
        else:  # unerupted
            canvas.create_oval(cx - 3, icon_y - 3, cx + 3, icon_y + 3, outline=color, width=1)

    def _draw_selection_ring(self, canvas, tooth_num):
        if tooth_num in self.selected_teeth or tooth_num == self.selected_tooth:
            canvas.create_rectangle(1, 1, TOOTH_W - 1, TOOTH_H - 1,
                                     outline=theme.ACCENT_BORDER, width=2, dash=(3, 2))

    # شفافية موحدة لكل "طبقات" المعالجات اللي بتغطي مساحة من السن (تاج/
    # طربوش، دعامة، حشو، تسوس، جير) - بترسم كلها مع بعض في صورة واحدة بـ
    # per-pixel alpha حقيقي عبر PIL (مش محاكاة بمزج لون مسطح زي قبل كده)،
    # فبغض النظر عن ترتيبها أو تداخل مساحاتها كلها بتفضل باينة فوق بعض
    TREATMENT_OPACITY = 0.45
    # معامل رسم بدقة أعلى ثم تصغير (supersampling) عشان الحواف تبقى ناعمة،
    # لإن PIL معندهاش antialiasing جاهز للأشكال زي ما الـ Canvas بيعمل بـ smooth=True
    _OVERLAY_SCALE = 3

    @staticmethod
    def _hex_to_rgba(hex_color, alpha):
        h = (hex_color or "#9E9E9E").lstrip("#")
        if len(h) != 6:
            h = "9E9E9E"
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r, g, b, max(0, min(255, round(alpha * 255))))

    def _draw_treatment_overlay(self, canvas, upper, crown_pts, cx, coverage_colors, post_color,
                                 filled_record, decay_color, calculus_color, flip_md):
        """بترسم كل "طبقات" العلاج اللي ممكن تتداخل مع بعض على نفس السن
        (تاج/طربوش، دعامة، حشو، تسوس، جير) مع بعض في صورة واحدة بشفافية
        حقيقية (per-pixel alpha compositing عبر PIL) بدل الرسم المباشر
        على الـ Canvas (اللي بيرسم أشكال معتمة فوق بعض بترتيب، وآخر شكل
        بيغطي اللي قبله بالكامل مهما كان بسيط). كده أي عدد من المعالجات
        على نفس السن بيفضلوا كلهم باينين مع بعض بشفافية، مهما كان ترتيب
        أو تداخل مساحاتهم - مش بس المعالجة اللي اتعملت آخر حاجة"""
        scale = self._OVERLAY_SCALE
        img = Image.new("RGBA", (TOOTH_W * scale, TOOTH_H * scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        alpha = self.TREATMENT_OPACITY

        # التاج/الطربوش (ممكن أكتر من واحد فوق بعض)
        for color in coverage_colors:
            draw.polygon([(x * scale, y * scale) for x, y in crown_pts],
                         fill=self._hex_to_rgba(color, alpha))
        if coverage_colors:
            gum_ys = [y for _x, y in crown_pts]
            gum_y = max(gum_ys) if upper else min(gum_ys)
            xs = [x for x, _y in crown_pts]
            x_left, x_right = min(xs) + 3, max(xs) - 3
            bump_r = 3
            edge_rgba = (255, 255, 255, 200)
            x = x_left
            step = (x_right - x_left) / 4
            while x <= x_right:
                draw.arc([(x - bump_r) * scale, (gum_y - bump_r) * scale,
                          (x + bump_r) * scale, (gum_y + bump_r) * scale],
                         start=0 if upper else 180, end=180 if upper else 360,
                         fill=edge_rgba, width=scale)
                x += step
            shine_y = gum_y + (10 if upper else -10)
            cx_shine = sum(xs) / len(xs)
            draw.line([(cx_shine - 6) * scale, shine_y * scale, (cx_shine - 1) * scale,
                       (shine_y - (6 if upper else -6)) * scale], fill=edge_rgba, width=scale)

        # الدعامة (مسمار: رأس مسطح قريب من التاج + جسم مدبب نازل ناحية الجذر)
        if post_color:
            if upper:
                head_y, tip_y = 32, TOOTH_H - 8
            else:
                head_y, tip_y = TOOTH_H - 32, 8
            d = 1 if tip_y > head_y else -1
            rgba = self._hex_to_rgba(post_color, alpha)
            head_y0, head_y1 = sorted((head_y - 3 * d, head_y + 2 * d))
            draw.rectangle([(cx - 7) * scale, head_y0 * scale,
                            (cx + 7) * scale, head_y1 * scale], fill=rgba)
            draw.polygon([((cx - 4) * scale, (head_y + 2 * d) * scale),
                          ((cx + 4) * scale, (head_y + 2 * d) * scale),
                          ((cx + 1.5) * scale, (tip_y - 6 * d) * scale),
                          (cx * scale, tip_y * scale),
                          ((cx - 1.5) * scale, (tip_y - 6 * d) * scale)], fill=rgba)

        # الحشو - مربع صغير مقسم 5 أسطح، السطح اللي اتحشى بيتلون. الميزيال
        # (M) والديستال (D) بيتبادلوا الأماكن (flip_md) في النص الشمال من
        # الشارت (11-18 و41-48) عشان الميزيال يفضل دايمًا ناحية المنتصف
        if filled_record:
            surfaces_done = set((filled_record.get("surfaces") or "").split(",")) \
                if filled_record.get("surfaces") else set()
            color = filled_record.get("variant_color") or self._color_for("filled")
            cy = 22 if upper else TOOTH_H - 22
            s = 7
            m_dx, d_dx = -2 * s - 1, 2 * s + 1
            if flip_md:
                m_dx, d_dx = d_dx, m_dx
            for dx, dy, code in ((0, 0, "O"), (0, -2 * s - 1, "B"), (0, 2 * s + 1, "L"),
                                 (m_dx, 0, "M"), (d_dx, 0, "D")):
                cell_rgba = self._hex_to_rgba(color, alpha) if code in surfaces_done \
                    else (255, 255, 255, round(alpha * 255))
                draw.rectangle([(cx + dx - s) * scale, (cy + dy - s) * scale,
                                (cx + dx + s) * scale, (cy + dy + s) * scale],
                               fill=cell_rgba, outline=(102, 102, 102, 255), width=scale // 2 or 1)

        # التسوس
        if decay_color:
            dot_y = 18 if upper else TOOTH_H - 18
            draw.ellipse([(cx - 5) * scale, (dot_y - 5) * scale,
                          (cx + 5) * scale, (dot_y + 5) * scale],
                         fill=self._hex_to_rgba(decay_color, alpha))

        # الجير - 3 علامات عند خط اللثة
        if calculus_color:
            gum_y = 40 if upper else TOOTH_H - 40
            rgba = self._hex_to_rgba(calculus_color, alpha)
            for dx in (-10, 0, 10):
                draw.ellipse([(cx + dx - 2) * scale, (gum_y - 2) * scale,
                              (cx + dx + 2) * scale, (gum_y + 2) * scale], fill=rgba)

        small = img.resize((TOOTH_W, TOOTH_H), Image.LANCZOS)
        photo = ImageTk.PhotoImage(small)
        canvas.create_image(0, 0, anchor="nw", image=photo)
        # لازم نمسك مرجع للصورة عشان الـ garbage collector ميحذفهاش من الذاكرة
        canvas.image_refs = getattr(canvas, "image_refs", [])
        canvas.image_refs.append(photo)

    def _draw_implant_root(self, canvas, upper, conditions=None):
        """رمز الزراعة: مسمار زراعة حقيقي - قطعة وصل (abutment) قريبة من
        التاج، وبعدها برغي مسنن (فيه خطوط لولب مائلة) بيضيق تدريجيًا
        وينتهي بطرف مدبب ناحية الجذر بالظبط. المسافة من اللثة للطرف
        محسوبة باتجاه صريح (d) مش بترتيب min/max، عشان الشكل يفضل صح في
        الاتجاهين (تحت للأسنان السفلية، وفوق للأسنان العلوية) من غير ما
        ينقلب رأسًا على عقب زي ما كان بيحصل في الصف العلوي"""
        color = self._color_for("implant", conditions)
        cx = TOOTH_W // 2
        if upper:
            gum_y, tip = 34, TOOTH_H - 4
        else:
            gum_y, tip = TOOTH_H - 34, 4
        d = 1 if tip > gum_y else -1

        # قطعة الوصل (abutment) - قريبة من التاج، شبه منحرف بيربطه بالبرغي
        neck_near, neck_far = gum_y, gum_y + 8 * d
        canvas.create_polygon(cx - 4, neck_near, cx + 4, neck_near, cx + 6, neck_far,
                               cx - 6, neck_far, fill=color, outline="")

        # جسم البرغي - أعرض نقطة قريبة من اللثة، وبيضيق تدريجيًا لحد طرف
        # مدبب عند الجذر (بخطوط لولب مائلة توحي بالتسنين الحلزوني)
        screw_wide = neck_far
        screw_narrow = tip - 4 * d
        canvas.create_polygon(cx - 6, screw_wide, cx + 6, screw_wide,
                               cx + 3, screw_narrow, cx, tip, cx - 3, screw_narrow,
                               fill=color, outline="")

        span = abs(tip - screw_wide) or 1
        step = 6
        y = screw_wide + 3 * d
        while abs(y - screw_wide) < span - 2:
            frac = abs(y - screw_wide) / span
            w = 6 * max(0, 1 - frac) + 2
            canvas.create_line(cx - w, y, cx + w, y - 3 * d, fill="#FFFFFF", width=1)
            y += step * d

    # ---------------- التفاعل ----------------

    def _on_tooth_click(self, event, tooth_num):
        """ضغطة الماوس الشمال على سن: عادي بيحدد سن واحد بس (وبيصفّر أي
        تحديد متعدد سابق). لو Shift مضغوط، بيضيف/يشيل السن ده من التحديد
        المتعدد الحالي بدل ما يستبدله - عشان يقدر يحدد كذا سن مع بعض"""
        shift = bool(event.state & 0x0001)
        self._rubber_band_start = (event.x_root, event.y_root)
        self._rubber_band_drag_happened = False
        if shift:
            if not self.selected_teeth and self.selected_tooth is not None:
                self.selected_teeth.add(self.selected_tooth)
            if tooth_num in self.selected_teeth:
                self.selected_teeth.discard(tooth_num)
            else:
                self.selected_teeth.add(tooth_num)
            self.selected_tooth = tooth_num
            self._refresh_selection_visuals()
        else:
            self.selected_teeth.clear()
            self._select_tooth(tooth_num)

    def _on_tooth_drag(self, event, tooth_num):
        """لو Shift لسه مضغوط والماوس بيتحرك والزرار مضغوط، بنرسم مستطيل
        تحديد (rubber band) بيكبر مع حركة الماوس - أي سن يتغطى ولو جزء
        بسيط منه هيتضاف للتحديد المتعدد عند الإفلات"""
        if not (event.state & 0x0001) or self._rubber_band_start is None:
            return
        sx, sy = self._rubber_band_start
        dx, dy = event.x_root - sx, event.y_root - sy
        if not self._rubber_band_drag_happened and (abs(dx) > 4 or abs(dy) > 4):
            self._rubber_band_drag_happened = True
            self._create_rubber_band_window()
        if self._rubber_band_drag_happened:
            self._update_rubber_band_window(sx, sy, event.x_root, event.y_root)

    def _on_tooth_release(self, event, tooth_num):
        if self._rubber_band_drag_happened and self._rubber_band_start is not None:
            self._finish_rubber_band_selection(self._rubber_band_start, (event.x_root, event.y_root))
        self._destroy_rubber_band_window()
        self._rubber_band_start = None
        self._rubber_band_drag_happened = False

    def _create_rubber_band_window(self):
        try:
            win = tk.Toplevel(self)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            try:
                win.attributes("-alpha", 0.25)
            except Exception:
                pass
            win.configure(bg=theme.ACCENT_BORDER)
            self._rubber_band_win = win
        except Exception:
            self._rubber_band_win = None

    def _update_rubber_band_window(self, x1, y1, x2, y2):
        if not self._rubber_band_win:
            return
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        w, h = max(right - left, 1), max(bottom - top, 1)
        try:
            self._rubber_band_win.geometry(f"{w}x{h}+{left}+{top}")
        except Exception:
            pass

    def _destroy_rubber_band_window(self):
        if self._rubber_band_win is not None:
            try:
                self._rubber_band_win.destroy()
            except Exception:
                pass
            self._rubber_band_win = None

    def _finish_rubber_band_selection(self, start, end):
        x1, y1 = start
        x2, y2 = end
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        for tooth_num, (canvas, _upper) in self.tooth_canvases.items():
            try:
                cx1 = canvas.winfo_rootx()
                cy1 = canvas.winfo_rooty()
                cx2 = cx1 + canvas.winfo_width()
                cy2 = cy1 + canvas.winfo_height()
            except Exception:
                continue
            if cx1 < right and cx2 > left and cy1 < bottom and cy2 > top:
                self.selected_teeth.add(tooth_num)
        if self.selected_teeth:
            self.selected_tooth = max(self.selected_teeth)
        self._refresh_selection_visuals()

    def _refresh_selection_visuals(self):
        """بتحدّث رسم كل الأسنان (عشان يبان إطار التحديد على كل الأسنان
        المحددة مع بعض) ونص شريط الحالة فوق - من غير ما تفتح/تقفل أي بوب-أب"""
        for t in self.tooth_canvases:
            self._draw_tooth(t)
        if len(self.selected_teeth) > 1:
            teeth_txt = "، ".join(str(t) for t in sorted(self.selected_teeth))
            self.selection_label.configure(
                text=f"محدد {len(self.selected_teeth)} سن معًا: {teeth_txt}   -   "
                     f"دوس نوع العلاج عشان تضيفه على كل الأسنان دي مع بعض")
            self._render_details()
        elif self.selected_tooth is not None:
            self._select_tooth(self.selected_tooth)

    def _get_treatment_target_teeth(self):
        """قائمة الأسنان اللي أي علاج يتضاف عليها دلوقتي: كل الأسنان
        المحددة سويًا لو فيه تحديد متعدد فعّال، وإلا السن الواحد المحدد"""
        if len(self.selected_teeth) > 1:
            return sorted(self.selected_teeth)
        if self.selected_tooth is not None:
            return [self.selected_tooth]
        return []

    def _select_tooth(self, tooth_num):
        self.selected_tooth = tooth_num
        presence, _auto = self._slot_presence(tooth_num)
        active_num = self._active_number(tooth_num, presence)
        conditions = self.active_conditions.get(active_num, {})

        if conditions:
            parts = []
            for k, record in conditions.items():
                label = self._label_for(k)
                if record.get("variant_name"):
                    label += f" ({record['variant_name']})"
                parts.append(label)
            labels = "، ".join(parts)
        elif presence != teeth_time.PRESENT:
            labels = teeth_time.PRESENCE_LABELS.get(presence, presence)
        else:
            labels = "سليم"

        display_num = str(tooth_num) if active_num == tooth_num else f"{tooth_num}  (لبني {active_num})"
        self.selection_label.configure(text=f"السن المحدد: {display_num}   -   الحالة: {labels}")

        for t in self.tooth_canvases:
            self._draw_tooth(t)
        self._render_details()

    def _on_treatment_click(self, status_key):
        teeth = self._get_treatment_target_teeth()
        if not teeth:
            self.selection_label.configure(text="⚠ حدد سن الأول من الشارت فوق")
            return

        doctor_name = self.doctor_menu.get()
        if doctor_name in ("-- اختر الطبيب --", "لا يوجد أطباء مسجلين - ضيفي من الإعدادات"):
            self.selection_label.configure(text="⚠ لازم تحددي الطبيب المعالج الأول من القايمة فوق")
            return

        if status_key == "filled":
            self._open_surfaces_dialog(teeth)
            return

        self._maybe_choose_variant(status_key, teeth=teeth)

    def _maybe_choose_variant(self, status_key, surfaces=None, teeth=None):
        teeth = teeth if teeth is not None else self._get_treatment_target_teeth()
        active_list_id = db.get_settings()["active_price_list_id"]
        variants = db.get_treatment_variants(active_list_id, status_key) if active_list_id else []
        if variants:
            self._open_variant_dialog(status_key, variants, surfaces=surfaces, teeth=teeth)
        else:
            self._proceed_to_apply(status_key, surfaces=surfaces, variant=None, teeth=teeth)

    def _open_variant_dialog(self, status_key, variants, surfaces=None, teeth=None):
        teeth = teeth if teeth is not None else self._get_treatment_target_teeth()
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"اختر النوع - {self._label_for(status_key)}")
        dialog.geometry("360x" + str(140 + 54 * (len(variants) + 1)))
        dialog.grab_set()

        tooth_txt = f"سن {teeth[0]}" if len(teeth) == 1 else f"{len(teeth)} سن مع بعض"
        ctk.CTkLabel(dialog, text=f"{self._label_for(status_key)}  -  {tooth_txt}",
                     font=theme.FONT_SUBTITLE, wraplength=320).pack(pady=(16, 4))
        ctk.CTkLabel(dialog, text="اختر النوع/الخامة", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(pady=(0, 12))

        def pick(v=None):
            dialog.destroy()
            self._proceed_to_apply(status_key, surfaces=surfaces, variant=v, teeth=teeth)

        ctk.CTkButton(dialog, text="بدون تحديد نوع (السعر الأساسي)", height=40,
                      fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK,
                      border_width=1, border_color=theme.BORDER,
                      command=lambda: pick(None)).pack(fill="x", padx=24, pady=4)

        for v in variants:
            row = ctk.CTkFrame(dialog, fg_color="transparent")
            row.pack(fill="x", padx=24, pady=4)
            ctk.CTkLabel(row, text="  ", fg_color=v.get("color") or "#9E9E9E",
                         width=18, height=18, corner_radius=4).pack(side="right", padx=(4, 6))
            ctk.CTkButton(row, text=f"{v['variant_name']}   -   {v['price']:g} جنيه", height=40,
                          fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK,
                          border_width=1, border_color=theme.BORDER,
                          command=lambda vv=v: pick(vv)).pack(side="right", fill="x", expand=True)

    def _open_surfaces_dialog(self, teeth=None):
        teeth = teeth if teeth is not None else self._get_treatment_target_teeth()
        tooth_txt = f"سن {teeth[0]}" if len(teeth) == 1 else f"{len(teeth)} سن مع بعض"
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"حشو - {tooth_txt}")
        dialog.geometry("320x420")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"اختر الأسطح المحشوة - {tooth_txt}",
                     font=theme.FONT_SUBTITLE, wraplength=280).pack(pady=(16, 14))

        surface_vars = {}
        for code, label in SURFACES:
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(dialog, text=f"{label} ({code})", variable=var,
                             font=theme.FONT_NORMAL, **theme.checkbox_colors()).pack(anchor="e", padx=30, pady=6)
            surface_vars[code] = var

        def confirm():
            chosen = [code for code, var in surface_vars.items() if var.get()]
            if not chosen:
                chosen = ["O"]  # افتراضي لو محددش حاجة
            dialog.destroy()
            self._maybe_choose_variant("filled", surfaces=",".join(chosen), teeth=teeth)

        ctk.CTkButton(dialog, text="تأكيد الحشو", height=44, fg_color=theme.SUCCESS,
                      command=confirm).pack(padx=30, pady=16, fill="x")

    def _proceed_to_apply(self, status_key, surfaces=None, variant=None, teeth=None):
        """بعد اختيار النوع/الأسطح (لو محتاجة)، لو المعالجة هتتطبق على أكتر
        من سن مع بعض بنسأل الأول كام سن تتحسب فعليًا في التكلفة (ممكن يكون
        أقل أو أكتر من عدد الأسنان المحددة فعليًا - حسب طبيعة البند)، وإلا
        (سن واحد بس) بتتطبق على طول من غير أي بوب-أب إضافي"""
        teeth = teeth if teeth is not None else self._get_treatment_target_teeth()
        if not teeth:
            return
        if len(teeth) > 1:
            self._open_teeth_count_dialog(status_key, teeth, surfaces=surfaces, variant=variant)
        else:
            self._apply_treatment(status_key, surfaces=surfaces, variant=variant,
                                   teeth=teeth, unit_count=1)

    def _open_teeth_count_dialog(self, status_key, teeth, surfaces=None, variant=None):
        label = self._label_for(status_key)
        if variant:
            label += f" ({variant['variant_name']})"
        dialog = ctk.CTkToplevel(self)
        dialog.title("حساب التكلفة")
        dialog.geometry("360x250")
        dialog.grab_set()

        teeth_txt = "، ".join(str(t) for t in teeth)
        ctk.CTkLabel(dialog, text=f'"{label}" هتتضاف على {len(teeth)} سن:\n{teeth_txt}',
                     font=theme.FONT_NORMAL, text_color=theme.TEXT_DARK,
                     wraplength=320, justify="right").pack(padx=20, pady=(18, 6))
        ctk.CTkLabel(dialog,
                     text="التكلفة تتحسب فعليًا على كام سن؟\n"
                          "(مثال: حشو 3 أسطح منفصلة في 3 أسنان = 3 - إزالة جير للفم كله = 1)",
                     font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                     wraplength=320, justify="right").pack(padx=20, pady=(0, 10))

        count_entry = ctk.CTkEntry(dialog, width=90, height=38, justify="center",
                                    font=theme.FONT_SUBTITLE)
        count_entry.insert(0, str(len(teeth)))
        count_entry.pack(pady=4)

        def confirm():
            try:
                unit_count = int(count_entry.get())
            except Exception:
                unit_count = len(teeth)
            unit_count = max(unit_count, 0)
            dialog.destroy()
            self._apply_treatment(status_key, surfaces=surfaces, variant=variant,
                                   teeth=teeth, unit_count=unit_count)

        ctk.CTkButton(dialog, text="تأكيد", height=42, fg_color=theme.SUCCESS,
                      command=confirm).pack(padx=24, pady=(12, 16), fill="x")

    def _apply_treatment(self, status_key, surfaces=None, variant=None, teeth=None, unit_count=None):
        """بتطبق البند العلاجي على سن واحد أو أكتر مع بعض. لو أكتر من سن،
        التكلفة الفعلية بتتحسب على unit_count (اللي المستخدم حدده في بوب-أب
        عدد الأسنان، مش بالضرورة نفس عدد الأسنان المحددة فعليًا) - وبتتسجل
        كحركة مالية واحدة بس (مش مكررة على كل سن) عشان الحساب يفضل مظبوط"""
        teeth = teeth if teeth is not None else \
            ([self.selected_tooth] if self.selected_tooth is not None else [])
        if not teeth:
            return

        if variant:
            price = variant["price"]
            label = f"{self._label_for(status_key)} ({variant['variant_name']})"
            commission_percent = variant.get("commission_percent") or 0
            variant_name = variant["variant_name"]
            variant_color = variant.get("color")
            price_info = variant
        else:
            price_info = self.prices_cache.get(status_key) or db.get_price_for(status_key)
            price = price_info["price"] if price_info else 0
            label = price_info["label"] if price_info else status_key
            commission_percent = (price_info.get("commission_percent") if price_info else 0) or 0
            variant_name = None
            variant_color = None

        is_bulk = len(teeth) > 1
        if unit_count is None:
            unit_count = len(teeth)
        total_price = price * unit_count
        total_commission = price * unit_count * commission_percent / 100

        doctor_name = self.doctor_menu.get()
        if doctor_name in ("-- اختر الطبيب --", "لا يوجد أطباء مسجلين - ضيفي من الإعدادات"):
            doctor_name = ""

        # سجل معالجة مستقل على كل سن من الأسنان المحددة (عشان الرمز والتاريخ
        # يبانوا على كل سن منهم في الشارت والتلميح)، لكن التكلفة والعمولة
        # كاملة بتتسجل على أول سجل بس - عشان الفلوس ميتضاعفوش في التقارير
        record_ids, active_nums = [], []
        for i, tooth_num in enumerate(teeth):
            presence, _auto = self._slot_presence(tooth_num)
            active_num = self._active_number(tooth_num, presence)
            active_nums.append(active_num)
            record_price = total_price if i == 0 else 0
            record_commission = total_commission if i == 0 else 0
            record_notes = f"معالجة مشتركة على {len(teeth)} سن (محسوبة كـ {unit_count} سن)" if is_bulk else ""
            record_id = db.add_treatment_record(
                self.patient_id, active_num, status_key, label, record_price,
                notes=record_notes, doctor_name=doctor_name, commission_percent=commission_percent,
                commission_amount=record_commission, surfaces=surfaces,
                variant_name=variant_name, variant_color=variant_color)
            record_ids.append(record_id)

            # لو اتحطت زراعة على سن كان "مفقود"، طبيعي إننا نرجعه لحالة
            # "موجود" عشان الشارت يبان صح (فيه سن دلوقتي فعلاً مكانه، ولو
            # حصل خلع بعد كده هيتحول لرمز الخلع براحته زي أي سن تاني)
            if status_key == "implant" and presence == teeth_time.MISSING:
                db.set_tooth_presence(self.patient_id, tooth_num, teeth_time.PRESENT, auto=False)

        if total_price > 0:
            if is_bulk:
                teeth_txt = "، ".join(str(n) for n in active_nums)
                desc = f"{label} - {len(teeth)} سن ({teeth_txt}) - محسوبة كـ {unit_count} سن"
                status_msg = f"تم تسجيل {label} على {len(teeth)} سن وإضافة {total_price:g} جنيه على الحساب"
            else:
                desc = f"{label} - سن رقم {active_nums[0]}"
                status_msg = f"تم تسجيل {label} على سن {active_nums[0]} وإضافة {total_price:g} جنيه على الحساب"
            db.add_transaction(self.patient_id, "charge", total_price, description=desc,
                                related_treatment_id=record_ids[0])
        else:
            status_msg = (f"تم تحديث حالة {len(teeth)} سن" if is_bulk
                          else f"تم تحديث حالة سن {active_nums[0]}")

        # لو البند العلاجي ده محتاج معمل (تاج/إمبلانت/دعامة...)، نبعت الحالة
        # للمعمل الافتراضي بتاعه تلقائيًا، أو نفتح شاشة بسيطة لاختيار المعمل
        # لو مفيش معمل افتراضي متحدد له (مرة واحدة بس للمجموعة كلها)
        requires_lab = bool((variant or price_info or {}).get("requires_lab")) if (variant or price_info) else False
        default_lab_id = (variant or price_info or {}).get("default_lab_id") if (variant or price_info) else None
        lab_code = (variant or price_info or {}).get("lab_code") if (variant or price_info) else None
        if requires_lab:
            if default_lab_id and db.get_lab(default_lab_id):
                lab = db.get_lab(default_lab_id)
                db.add_lab_order(
                    default_lab_id, patient_id=self.patient_id, treatment_record_id=record_ids[0],
                    tooth_number=active_nums[0], treatment_key=status_key, treatment_label=label,
                    variant_name=variant_name, lab_code=lab_code or "",
                    sent_by=doctor_name, received_by=lab.get("contact_person") or "")
                status_msg += f"   |   ✅ اتبعتت الحالة تلقائيًا لمعمل {lab['name']}"
            else:
                self._prompt_choose_lab(record_ids[0], active_nums[0], status_key, label, variant_name,
                                        lab_code, doctor_name)

        self.selection_label.configure(text=status_msg)

        self.refresh()
        if is_bulk:
            self._refresh_selection_visuals()
        else:
            self._select_tooth(teeth[0])
        if self.on_change:
            self.on_change()

    def _prompt_choose_lab(self, record_id, tooth_number, treatment_key, label, variant_name,
                            lab_code, doctor_name):
        """البند محتاج معمل بس مفيش معمل افتراضي متحدد له - بنفتح بوب-أب صغير
        يسمح باختيار المعمل بسرعة (أو تجاهل الإرسال دلوقتي وإضافته يدويًا بعدين
        من شاشة المعامل)"""
        labs = db.get_labs(active_only=True)
        if not labs:
            return

        popup = ctk.CTkToplevel(self)
        popup.title("إرسال للمعمل")
        popup.geometry("360x260")
        popup.grab_set()

        ctk.CTkLabel(popup, text=f'"{label}" يحتاج معمل، ابعتيها لمين؟',
                     font=theme.FONT_NORMAL, text_color=theme.TEXT_DARK,
                     wraplength=320, justify="right").pack(padx=20, pady=(20, 10))

        lab_names = [l["name"] for l in labs]
        lab_menu = ctk.CTkOptionMenu(popup, values=lab_names, width=300, **theme.optionmenu_colors())
        lab_menu.set(lab_names[0])
        lab_menu.pack(padx=20, pady=6)

        def send():
            lab = next(l for l in labs if l["name"] == lab_menu.get())
            db.add_lab_order(
                lab["id"], patient_id=self.patient_id, treatment_record_id=record_id,
                tooth_number=tooth_number, treatment_key=treatment_key, treatment_label=label,
                variant_name=variant_name, lab_code=lab_code or "",
                sent_by=doctor_name, received_by=lab.get("contact_person") or "")
            self.selection_label.configure(
                text=self.selection_label.cget("text") + f"   |   ✅ اتبعتت لمعمل {lab['name']}")
            popup.destroy()

        def skip():
            popup.destroy()

        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.pack(pady=16)
        ctk.CTkButton(btn_row, text="إرسال", width=120, fg_color=theme.SUCCESS,
                      command=send).pack(side="right", padx=6)
        ctk.CTkButton(btn_row, text="ليس الآن", width=120, fg_color=theme.BG_MAIN,
                      text_color=theme.TEXT_DARK, border_width=1, border_color=theme.BORDER,
                      command=skip).pack(side="right", padx=6)

    # ---------------- ملحوظة مفصّلة على السن (تاريخ + طبيب + نص) ----------------

    def _text_justify_for_language(self):
        """اتجاه محاذاة النص حسب لغة البرنامج الحالية - يمين للعربي، شمال
        للإنجليزي، عشان مؤشر الكتابة يبان في مكانه الطبيعي على طول"""
        settings = db.get_settings() or {}
        return "left" if settings.get("language") == "en" else "right"

    def _open_tooth_annotation_dialog(self, tooth_num):
        """نافذة إضافة/تعديل الملحوظة المفصّلة على سن معين: تاريخ + طبيب +
        نص حر، وزر حذف (بتأكيد) لو فيه ملحوظة متسجلة بالفعل. الحفظ بيحصل
        بالضغط على Enter في خانة النص أو بزرار الحفظ"""
        presence, _auto = self._slot_presence(tooth_num)
        active_num = self._active_number(tooth_num, presence)
        existing = db.get_tooth_annotation(self.patient_id, active_num)

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"ملحوظة - سن {active_num}")
        dialog.geometry("380x420")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"ملحوظة على سن {active_num}", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(pady=(16, 10))

        date_row = ctk.CTkFrame(dialog, fg_color="transparent")
        date_row.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkLabel(date_row, text="التاريخ:", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_MUTED).pack(side="right", padx=(0, 8))
        date_entry = DateAutoEntry(date_row, width=140, height=34)
        date_entry.pack(side="right")
        if existing and existing.get("note_date"):
            date_entry.set_iso_date(existing["note_date"])
        else:
            date_entry.set_iso_date(datetime_today_iso())

        doctor_row = ctk.CTkFrame(dialog, fg_color="transparent")
        doctor_row.pack(fill="x", padx=24, pady=(0, 10))
        ctk.CTkLabel(doctor_row, text="الطبيب:", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_MUTED).pack(side="right", padx=(0, 8))
        doctors = db.get_doctors()
        doctor_names = [d["full_name"] for d in doctors] if doctors else ["-- لا يوجد أطباء مسجلين --"]
        default_doctor = existing.get("doctor_name") if existing and existing.get("doctor_name") else None
        if not default_doctor:
            current_doc = self.doctor_menu.get()
            default_doctor = current_doc if current_doc in doctor_names else doctor_names[0]
        elif default_doctor not in doctor_names:
            doctor_names = [default_doctor] + doctor_names
        note_doctor_menu = ctk.CTkOptionMenu(doctor_row, values=doctor_names, width=190, height=34,
                                              **theme.optionmenu_colors())
        note_doctor_menu.set(default_doctor)
        note_doctor_menu.pack(side="right")

        ctk.CTkLabel(dialog, text="الملحوظة:", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e", padx=24)
        justify = self._text_justify_for_language()
        text_box = ctk.CTkTextbox(dialog, width=320, height=140, wrap="word")
        text_box.pack(padx=24, pady=(4, 10))
        try:
            text_box._textbox.configure(justify=justify)
        except Exception:
            pass
        if existing and existing.get("note_text"):
            text_box.insert("1.0", existing["note_text"])
        text_box.focus_set()

        def save(event=None):
            note_text = text_box.get("1.0", "end").strip()
            if not note_text:
                messagebox.showwarning("تنبيه", "اكتب نص الملحوظة الأول", parent=dialog)
                return "break"
            iso_date = date_entry.get_iso_date() or datetime_today_iso()
            doctor_name = note_doctor_menu.get()
            if doctor_name == "-- لا يوجد أطباء مسجلين --":
                doctor_name = ""
            db.upsert_tooth_annotation(self.patient_id, active_num, iso_date, doctor_name, note_text)
            dialog.destroy()
            # لازم نجيب الملحوظات تاني من قاعدة البيانات (مش بس نحدّث شكل
            # العلامة) - وإلا self.tooth_annotations بيفضل فيه النسخة
            # القديمة (من آخر refresh) واللي مش شايفة الملحوظة الجديدة، فالعلامة
            # كانت بتفضل مخفية لحد ما نعمل ريفريش كامل للصفحة يدويًا
            self.tooth_annotations = db.get_tooth_annotations_map(self.patient_id)
            self._update_note_markers()
            self.selection_label.configure(text=f"تم حفظ الملحوظة على سن {active_num}")
            return "break"

        # Enter بيحفظ (مش بينزل سطر جديد) - Shift+Enter لو محتاجة سطر جديد فعلاً
        text_box.bind("<Return>", save)
        text_box.bind("<Shift-Return>", lambda e: None)

        def delete_note():
            if not messagebox.askyesno("تأكيد الحذف", "متأكدة إنك عايزة تمسحي الملحوظة دي؟", parent=dialog):
                return
            db.delete_tooth_annotation(self.patient_id, active_num)
            dialog.destroy()
            self.refresh()
            self.selection_label.configure(text=f"تم حذف الملحوظة من سن {active_num}")

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkButton(btn_row, text="💾 حفظ", height=40, fg_color=theme.SUCCESS,
                      command=save).pack(side="right", fill="x", expand=True, padx=(6, 0))
        if existing:
            ctk.CTkButton(btn_row, text="🗑 حذف الملحوظة", height=40, fg_color=theme.DANGER,
                          command=delete_note).pack(side="right", fill="x", expand=True, padx=(0, 6))

    def _open_tooth_annotation_view(self, tooth_num):
        """نافذة عرض الملحوظة المسجلة على سن معين (بيتفتح لما تدوسي على
        علامة الملحوظة فوق/تحت السن) - مع إمكانية التعديل أو الحذف مباشرة"""
        presence, _auto = self._slot_presence(tooth_num)
        active_num = self._active_number(tooth_num, presence)
        note = db.get_tooth_annotation(self.patient_id, active_num)
        if not note:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"ملحوظة - سن {active_num}")
        dialog.geometry("360x340")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"ملحوظة على سن {active_num}", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(pady=(16, 6))

        meta_bits = [b for b in (note.get("note_date"), note.get("doctor_name")) if b]
        if meta_bits:
            ctk.CTkLabel(dialog, text="   -   ".join(meta_bits), font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(pady=(0, 10))

        justify = self._text_justify_for_language()
        text_box = ctk.CTkTextbox(dialog, width=300, height=150, wrap="word")
        text_box.pack(padx=24, pady=(0, 12))
        try:
            text_box._textbox.configure(justify=justify)
        except Exception:
            pass
        text_box.insert("1.0", note.get("note_text") or "")
        text_box.configure(state="disabled")

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkButton(btn_row, text="✏ تعديل", height=40, fg_color=theme.PRIMARY_LIGHT,
                      command=lambda: (dialog.destroy(), self._open_tooth_annotation_dialog(tooth_num))
                      ).pack(side="right", fill="x", expand=True, padx=(6, 0))

        def delete_note():
            if not messagebox.askyesno("تأكيد الحذف", "متأكدة إنك عايزة تمسحي الملحوظة دي؟", parent=dialog):
                return
            db.delete_tooth_annotation(self.patient_id, active_num)
            dialog.destroy()
            self.refresh()
            self.selection_label.configure(text=f"تم حذف الملحوظة من سن {active_num}")

        ctk.CTkButton(btn_row, text="🗑 حذف", height=40, fg_color=theme.DANGER,
                      command=delete_note).pack(side="right", fill="x", expand=True, padx=(0, 6))


def datetime_today_iso():
    from datetime import date
    return date.today().strftime("%Y-%m-%d")
