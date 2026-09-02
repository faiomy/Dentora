# -*- coding: utf-8 -*-
"""
مكتبة الرموز العامة اللي ممكن تتحدد لأي "معالجة أساسية جديدة" تتضاف من صفحة
الأسعار - كل رمز له معنى بصري منطقي (زي الخط الرأسي لعلاج الجذور وعلامة الـX
للخلع اللي أصلاً موجودين ومرسومين برموزهم الخاصة في شارت الأسنان).

كل دالة رسم بتاخد: canvas (أو أي حاجة عندها create_line/create_oval/...)،
مركز الرمز (cx, cy)، نص قطر الرمز (r) تقريبًا، واللون. الحجم (r) بيتغير حسب
مكان الاستخدام: صغير جوه خانة السن نفسها، وأكبر في نافذة اختيار الرمز.
"""


def _vertical_line(canvas, cx, cy, r, color):
    canvas.create_line(cx, cy - r, cx, cy + r, fill=color, width=max(2, r // 4))


def _horizontal_line(canvas, cx, cy, r, color):
    canvas.create_line(cx - r, cy, cx + r, cy, fill=color, width=max(2, r // 4))


def _x_mark(canvas, cx, cy, r, color):
    canvas.create_line(cx - r, cy - r, cx + r, cy + r, fill=color, width=max(2, r // 4))
    canvas.create_line(cx - r, cy + r, cx + r, cy - r, fill=color, width=max(2, r // 4))


def _circle(canvas, cx, cy, r, color):
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=max(2, r // 4))


def _filled_circle(canvas, cx, cy, r, color):
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=color)


def _triangle_up(canvas, cx, cy, r, color):
    canvas.create_polygon(cx, cy - r, cx - r, cy + r, cx + r, cy + r,
                           outline=color, fill="", width=max(2, r // 4))


def _triangle_down(canvas, cx, cy, r, color):
    canvas.create_polygon(cx, cy + r, cx - r, cy - r, cx + r, cy - r,
                           outline=color, fill="", width=max(2, r // 4))


def _square(canvas, cx, cy, r, color):
    canvas.create_rectangle(cx - r, cy - r, cx + r, cy + r, outline=color, width=max(2, r // 4))


def _filled_square(canvas, cx, cy, r, color):
    canvas.create_rectangle(cx - r, cy - r, cx + r, cy + r, fill=color, outline=color)


def _diamond(canvas, cx, cy, r, color):
    canvas.create_polygon(cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy,
                           outline=color, fill="", width=max(2, r // 4))


def _filled_diamond(canvas, cx, cy, r, color):
    canvas.create_polygon(cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy,
                           fill=color, outline=color)


def _plus(canvas, cx, cy, r, color):
    w = max(2, r // 3)
    canvas.create_line(cx, cy - r, cx, cy + r, fill=color, width=w)
    canvas.create_line(cx - r, cy, cx + r, cy, fill=color, width=w)


def _asterisk_star(canvas, cx, cy, r, color):
    w = max(2, r // 4)
    canvas.create_line(cx, cy - r, cx, cy + r, fill=color, width=w)
    canvas.create_line(cx - r, cy, cx + r, cy, fill=color, width=w)
    d = r * 0.7
    canvas.create_line(cx - d, cy - d, cx + d, cy + d, fill=color, width=w)
    canvas.create_line(cx - d, cy + d, cx + d, cy - d, fill=color, width=w)


def _arrow_up(canvas, cx, cy, r, color):
    w = max(2, r // 4)
    canvas.create_line(cx, cy + r, cx, cy - r, fill=color, width=w)
    canvas.create_line(cx - r * 0.6, cy - r * 0.3, cx, cy - r, fill=color, width=w)
    canvas.create_line(cx + r * 0.6, cy - r * 0.3, cx, cy - r, fill=color, width=w)


def _arrow_down(canvas, cx, cy, r, color):
    w = max(2, r // 4)
    canvas.create_line(cx, cy - r, cx, cy + r, fill=color, width=w)
    canvas.create_line(cx - r * 0.6, cy + r * 0.3, cx, cy + r, fill=color, width=w)
    canvas.create_line(cx + r * 0.6, cy + r * 0.3, cx, cy + r, fill=color, width=w)


def _double_line(canvas, cx, cy, r, color):
    w = max(2, r // 4)
    canvas.create_line(cx - r * 0.4, cy - r, cx - r * 0.4, cy + r, fill=color, width=w)
    canvas.create_line(cx + r * 0.4, cy - r, cx + r * 0.4, cy + r, fill=color, width=w)


def _wave_line(canvas, cx, cy, r, color):
    w = max(2, r // 4)
    points = []
    steps = 6
    for i in range(steps + 1):
        x = cx - r + (2 * r * i / steps)
        y = cy + (r * 0.5 if i % 2 == 0 else -r * 0.5)
        points.extend([x, y])
    canvas.create_line(*points, fill=color, width=w, smooth=True)


def _dotted_line(canvas, cx, cy, r, color):
    dot_r = max(1.5, r / 5)
    for frac in (-0.8, 0, 0.8):
        y = cy + frac * r
        canvas.create_oval(cx - dot_r, y - dot_r, cx + dot_r, y + dot_r, fill=color, outline=color)


def _dome_cap(canvas, cx, cy, r, color):
    """قبة (نص دائرة لفوق) - زي شكل التاج/الكابة"""
    canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=0, extent=180,
                       outline=color, width=max(2, r // 4), style="arc")
    canvas.create_line(cx - r, cy, cx + r, cy, fill=color, width=max(2, r // 4))


def _bowl_cup(canvas, cx, cy, r, color):
    """كوب/حفرة (نص دائرة لتحت) - زي فتحة أو تجويف"""
    canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=180, extent=180,
                       outline=color, width=max(2, r // 4), style="arc")
    canvas.create_line(cx - r, cy, cx + r, cy, fill=color, width=max(2, r // 4))


def _crown_cap_preview(canvas, cx, cy, r, color):
    """معاينة صغيرة بس لرمز "تغطية كاملة للسن" (طربوش) في نافذة اختيار
    الرمز - شكل قبة مليانة بسيطة (الرسمة الحقيقية على شكل السن نفسه
    بتحصل في شارت الأسنان مباشرة، مش من هنا)"""
    canvas.create_arc(cx - r, cy - r, cx + r, cy + r * 1.1, start=0, extent=180,
                       fill=color, outline=color)
    canvas.create_rectangle(cx - r, cy, cx + r, cy + r * 0.6, fill=color, outline=color)


def _water_drop(canvas, cx, cy, r, color):
    """قطرة مياه: مثلث مدبب لفوق + دائرة مليانة تحته، كلها كجسم واحد"""
    top = cy - r * 1.15
    side = r * 0.78
    canvas.create_polygon(
        cx, top,
        cx - side, cy - r * 0.15,
        cx + side, cy - r * 0.15,
        fill=color, outline=color, smooth=True)
    canvas.create_oval(cx - r, cy - r * 0.15, cx + r, cy + r * 1.15,
                        fill=color, outline=color)


def _wave_smooth(canvas, cx, cy, r, color):
    """خط متعرج ناعم كالموج (تجاويف موجية كاملة، أنعم وأكبر من الخط
    المتعرج العادي)"""
    w = max(2, r // 4)
    points = []
    steps = 12
    for i in range(steps + 1):
        x = cx - r + (2 * r * i / steps)
        y = cy + (r * 0.45) * (1 if (i // 3) % 2 == 0 else -1)
        points.extend([x, y])
    canvas.create_line(*points, fill=color, width=w, smooth=True, splinesteps=24)


def _zigzag_polygon(canvas, cx, cy, r, color):
    """خط متعرج مضلع: زاوية حادة متكررة (سن المنشار) بدون تنعيم، عكس
    الموجة الناعمة"""
    w = max(2, r // 4)
    points = []
    steps = 6
    for i in range(steps + 1):
        x = cx - r + (2 * r * i / steps)
        y = cy + (r * 0.6 if i % 2 == 0 else -r * 0.6)
        points.extend([x, y])
    canvas.create_line(*points, fill=color, width=w, smooth=False)


def _scalpel_blade(canvas, cx, cy, r, color):
    """شفرة مشرط جراحي صغير: مقبض (خط مستقيم) وشفرة منحنية عند الطرف"""
    w = max(2, r // 5)
    handle_end_x = cx - r * 0.15
    canvas.create_line(cx - r, cy + r * 0.55, handle_end_x, cy - r * 0.05,
                        fill=color, width=w)
    canvas.create_polygon(
        handle_end_x, cy - r * 0.05,
        cx + r * 0.55, cy - r,
        cx + r, cy - r * 0.25,
        cx + r * 0.25, cy + r * 0.35,
        fill=color, outline=color, smooth=True)


def _dental_needle(canvas, cx, cy, r, color):
    """سن إبرة بنج أسنان: إبرة رفيعة طويلة بطرف مشطوف مدبب"""
    w = max(1.5, r // 6)
    canvas.create_line(cx - r, cy + r * 0.7, cx + r * 0.55, cy - r * 0.55,
                        fill=color, width=w)
    canvas.create_polygon(
        cx + r * 0.55, cy - r * 0.55,
        cx + r, cy - r,
        cx + r * 0.35, cy - r * 0.35,
        fill=color, outline=color, smooth=True)


def _filled_dot_medium(canvas, cx, cy, r, color):
    """نقطة متوسطة الحجم مصمتة - أصغر من الدائرة المليانة العادية،
    مناسبة كعلامة توضيحية خفيفة لا تغطي مساحة كبيرة من خانة السن"""
    dot_r = r * 0.5
    canvas.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                        fill=color, outline=color)


# كل رمز: (المفتاح الداخلي، الاسم المعروض، دالة الرسم)
SYMBOL_CHOICES = [
    ("vertical_line", "خط رأسي (زي علاج الجذور)", _vertical_line),
    ("horizontal_line", "خط أفقي", _horizontal_line),
    ("x_mark", "علامة X (زي الخلع)", _x_mark),
    ("circle", "دائرة فارغة", _circle),
    ("filled_circle", "دائرة مليانة", _filled_circle),
    ("triangle_up", "مثلث لأعلى", _triangle_up),
    ("triangle_down", "مثلث لأسفل", _triangle_down),
    ("square", "مربع فارغ", _square),
    ("filled_square", "مربع مليان", _filled_square),
    ("diamond", "معين فارغ", _diamond),
    ("filled_diamond", "معين مليان", _filled_diamond),
    ("plus", "علامة زائد", _plus),
    ("asterisk_star", "نجمة", _asterisk_star),
    ("arrow_up", "سهم لأعلى", _arrow_up),
    ("arrow_down", "سهم لأسفل", _arrow_down),
    ("double_line", "خطين متوازيين", _double_line),
    ("wave_line", "خط متعرج", _wave_line),
    ("dotted_line", "خط منقط", _dotted_line),
    ("dome_cap", "قبة (زي التاج)", _dome_cap),
    ("bowl_cup", "كوب/حفرة", _bowl_cup),
    ("crown_cap", "تغطية كاملة للسن (طربوش)", _crown_cap_preview),
    ("water_drop", "قطرة مياه", _water_drop),
    ("wave_smooth", "خط متعرج كالموج", _wave_smooth),
    ("zigzag_polygon", "خط متعرج مضلع", _zigzag_polygon),
    ("scalpel_blade", "شفرة مشرط جراحي صغير", _scalpel_blade),
    ("dental_needle", "سن إبرة بنج أسنان", _dental_needle),
    ("filled_dot_medium", "نقطة متوسطة الحجم مصمتة", _filled_dot_medium),
]

SYMBOL_DRAWERS = {key: fn for key, _label, fn in SYMBOL_CHOICES}
SYMBOL_LABELS = {key: label for key, label, _fn in SYMBOL_CHOICES}

DEFAULT_SYMBOL_KEY = "filled_circle"

# مفتاح الرمز الخاص باللي بيغطي شكل السن كله (زي التاج/الطربوش) - أي
# بند علاجي "مخصص" (اتضاف من صفحة الأسعار) يتحدد له الرمز ده بيترسم في
# شارت الأسنان بشكل التاج الحقيقي (مش نقطة صغيرة زي باقي الرموز العامة)،
# بشفافية خفيفة عشان يبان شكل السن اللي تحته. الشارت نفسه (tooth_chart_widget)
# هو اللي بيتعرف على المفتاح ده ويرسم بيه شكل السن الحقيقي
CROWN_CAP_SYMBOL_KEY = "crown_cap"

# أسماء بنود شائعة بتتعامل تلقائيًا كـ"طربوش" حتى لو محدّش حدد لها رمز
# التغطية الكاملة يدويًا من صفحة الأسعار - عشان البنود القديمة اللي
# اتضافت قبل إضافة الرمز ده تتصلح تلقائيًا من غير ما المستخدم يحتاج
# يرجع يظبطها يدويًا
CROWN_CAP_AUTO_LABELS = {"طربوش", "تاج", "تلبيسة"}


def is_crown_cap(symbol_key, label=None):
    """بيحدد هل البند ده لازم يترسم بشكل تغطية كاملة للسن (زي التاج) بدل
    الرمز الصغير العادي - إما لأن المستخدم حدد له رمز التغطية الكاملة
    صراحة، أو لأن اسمه من الأسماء الشائعة المعروفة"""
    if symbol_key == CROWN_CAP_SYMBOL_KEY:
        return True
    if symbol_key:
        return False
    return bool(label) and label.strip() in CROWN_CAP_AUTO_LABELS

# البنود الأساسية الجاهزة اللي ليها رسمة خاصة بيها من كود شارت الأسنان نفسه
# (زي خط الجذر وعلامة الخلع)، مش من نظام الرموز العام - أي بند تاني (تضيفه
# بنفسك من صفحة الأسعار) بيستخدم نظام اختيار الرمز العام
BUILTIN_TREATMENT_KEYS = {
    "decay", "filled", "root_canal", "crown", "post", "implant", "calculus", "extracted",
}

# رمز "توضيحي" بس لعرضه جنب البنود الأساسية الجاهزة في صفحة الأسعار (عشان
# تبقى شايف بصريًا كل بند بيمثل إيه) - ده مش هو اللي بيتحكم في رسمة السن
# الفعلية بتاعت البند ده (اللي لسه مرسومة برسمة خاصة بيها جوه شارت الأسنان
# نفسه)، مجرد رمز يوضح المعنى في جدول الأسعار بس
BUILTIN_DISPLAY_SYMBOLS = {
    "decay": "filled_circle",
    "filled": "filled_square",
    "root_canal": "vertical_line",
    "crown": "dome_cap",
    "post": "plus",
    "implant": "triangle_up",
    # إزالة الجير بقت بترسم في شارت الأسنان بخط مستقيم متصل عند خط اللثة
    # بدل النقاط المتقطعة القديمة، فرمزها التوضيحي هنا لازم يعكس نفس الشكل
    "calculus": "horizontal_line",
    "extracted": "x_mark",
}

# ألوان ثابتة (غير قابلة للتخصيص) للبنود الأساسية الجاهزة - المستخدم مايقدرش
# يغيّرها من صفحة الإجراءات، عشان تفضل موحّدة ومعروفة في كل العيادات (نفس
# منطق الرمز الثابت لهذه البنود). القيم مطابقة للألوان الافتراضية القديمة
# اللي كانت قابلة للتخصيص قبل كده
BUILTIN_TREATMENT_COLORS = {
    "decay": "#E53935",
    "filled": "#1E88E5",
    "root_canal": "#FB8C00",
    "post": "#6D4C41",
    "implant": "#00897B",
    "calculus": "#9E9D24",
    "extracted": "#9E9E9E",
}


def draw_symbol(canvas, symbol_key, cx, cy, r, color):
    """بترسم الرمز المطلوب في مكان ومقاس ولون معينين - المكان الوحيد اللي
    بيعرف يرسم كل الرموز، مستخدم في شارت الأسنان الفعلي وفي نافذة الاختيار"""
    drawer = SYMBOL_DRAWERS.get(symbol_key) or SYMBOL_DRAWERS[DEFAULT_SYMBOL_KEY]
    drawer(canvas, cx, cy, r, color)
