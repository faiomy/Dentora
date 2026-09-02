# -*- coding: utf-8 -*-
"""
الجدول الزمني العالمي للتسنين (بيانات مرجعية من الأطالس السنية القياسية -
ADA/WHO): أعمار بزوغ الأسنان اللبنية وسقوطها، وأعمار بزوغ الأسنان الدائمة،
لكل "موضع" سن في الفك (١..٨ لكل ربع فم) بمعيار FDI.

الاستخدام الأساسي: توليد خريطة أسنان مبدئية تلقائيًا لأي مريض عند إنشاء
ملفه لأول مرة، بناءً على عمره بالشهور وقت الإنشاء، مع هامش "تفاوت طبيعي"
قابل للتعديل عشان يراعي اختلاف الأشخاص عن المتوسط العالمي.

كل القيم بالشهور عشان الدقة (بدل السنين) خصوصًا في مرحلة التسنين اللبني.
"""

from datetime import date as _dt_date

# ---------------- ترقيم FDI ----------------
# أرباع الفم: علوي يمين=1, علوي شمال=2, سفلي شمال=3, سفلي يمين=4 (دائم)
# وأرباع الأسنان اللبنية: علوي يمين=5, علوي شمال=6, سفلي شمال=7, سفلي يمين=8
PERMANENT_QUADRANTS = {"upper_right": 1, "upper_left": 2, "lower_left": 3, "lower_right": 4}
PRIMARY_QUADRANTS = {"upper_right": 5, "upper_left": 6, "lower_left": 7, "lower_right": 8}

# المواضع اللي ليها سن لبني مقابل (١ قاطعة مركزية .. ٥ ضرس لبني تاني) -
# الأضراس الدائمة (٦،٧،٨) مفيش لها سن لبني بيسبقها، بتبزغ في مكان جديد تمامًا
PRIMARY_POSITIONS = (1, 2, 3, 4, 5)
ALL_POSITIONS = (1, 2, 3, 4, 5, 6, 7, 8)

# ---------------- أعمار بزوغ الأسنان اللبنية (بالشهور) - (أدنى، متوسط، أقصى) ----------------
PRIMARY_ERUPTION_MONTHS = {
    ("upper", 1): (8, 10, 12),
    ("upper", 2): (9, 11, 13),
    ("upper", 3): (16, 19, 22),
    ("upper", 4): (13, 16, 19),
    ("upper", 5): (25, 29, 33),
    ("lower", 1): (6, 8, 10),
    ("lower", 2): (10, 13, 16),
    ("lower", 3): (17, 20, 23),
    ("lower", 4): (14, 16, 18),
    ("lower", 5): (23, 27, 31),
}

# ---------------- أعمار سقوط الأسنان اللبنية (بالشهور) ----------------
PRIMARY_EXFOLIATION_MONTHS = {
    ("upper", 1): (72, 78, 84),
    ("upper", 2): (84, 90, 96),
    ("upper", 3): (120, 132, 144),
    ("upper", 4): (108, 114, 120),
    ("upper", 5): (120, 132, 144),
    ("lower", 1): (72, 78, 84),
    ("lower", 2): (84, 90, 96),
    ("lower", 3): (108, 120, 144),
    ("lower", 4): (108, 114, 120),
    ("lower", 5): (120, 132, 144),
}

# ---------------- أعمار بزوغ الأسنان الدائمة (بالشهور) ----------------
PERMANENT_ERUPTION_MONTHS = {
    ("upper", 1): (84, 90, 96),
    ("upper", 2): (96, 105, 114),
    ("upper", 3): (132, 138, 144),
    ("upper", 4): (120, 126, 132),
    ("upper", 5): (120, 132, 144),
    ("upper", 6): (72, 78, 84),
    ("upper", 7): (144, 150, 156),
    ("upper", 8): (204, 216, 252),
    ("lower", 1): (72, 78, 84),
    ("lower", 2): (84, 90, 96),
    ("lower", 3): (108, 114, 120),
    ("lower", 4): (120, 132, 144),
    ("lower", 5): (132, 138, 144),
    ("lower", 6): (72, 78, 84),
    ("lower", 7): (132, 144, 156),
    ("lower", 8): (204, 216, 252),
}

# حالات بزوغ/وجود السن الممكنة (تتخزن في tooth_chart.status)
PRESENT = "present"                    # سن دائم موجود وباقٍ بشكل طبيعي
PRIMARY_PRESENT = "primary_present"    # سن لبني لسه موجود ولم يسقط بعد
UNERUPTED = "unerupted"                # لم يبزغ بعد (طبيعي حسب السن)
MISSING = "missing"                    # مفقود (عدم تكوّن خلقي / متأخر بشكل غير طبيعي)
IMPACTED = "impacted"                  # مطمور (تكوّن لكن لم يبزغ بشكل طبيعي)

PRESENCE_LABELS = {
    PRESENT: "موجود (دائم)",
    PRIMARY_PRESENT: "لبني - لم يسقط بعد",
    UNERUPTED: "لم يبزغ بعد (طبيعي حسب السن)",
    MISSING: "مفقود / غير موجود",
    IMPACTED: "مطمور",
}

# ترتيب الاختيارات في قوائم الواجهة
PRESENCE_CHOICES = [PRESENT, PRIMARY_PRESENT, UNERUPTED, MISSING, IMPACTED]

# ترقيم FDI لكل الأسنان الدائمة الـ32 (مفتاح ثابت لكل "موضع" في الفك -
# معرّف هنا كمصدر وحيد يستورد منه أي ملف تاني، عشان نتجنب أي استيراد
# دائري بين database.py وصفحات الواجهة)
UPPER_ROW = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
LOWER_ROW = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]


def age_in_months(birth_date_iso, as_of=None):
    """بتحسب عمر المريض بالشهور الكاملة من تاريخ ميلاد بصيغة YYYY-MM-DD.
    بترجع None لو التاريخ فاضي أو غلط. أدق من الحساب بالسنين لأنها أساس
    كل حسابات جدول التسنين (خصوصًا في السنتين الأولين من العمر)."""
    if not birth_date_iso:
        return None
    try:
        y, m, d = map(int, str(birth_date_iso).split("-"))
        born = _dt_date(y, m, d)
    except Exception:
        return None
    today = as_of or _dt_date.today()
    months = (today.year - born.year) * 12 + (today.month - born.month)
    if today.day < born.day:
        months -= 1
    return max(months, 0)


def _jaw_of(upper):
    return "upper" if upper else "lower"


def expected_presence(pos, upper, age_months, variation_months=0):
    """بترجع حالة البزوغ المتوقعة لموضع سن (pos من ١ لـ ٨) حسب عمر المريض
    بالشهور، مع هامش تفاوت طبيعي (variation_months) بيوسع/يضيق نطاق الأعمار
    القياسية عشان يراعي اختلاف الأشخاص عن المتوسط العالمي. الدالة "قراءة
    فقط" (heuristic) بتُستخدم للتوليد التلقائي المبدئي بس - أي تعديل يدوي
    من الطبيب بعد كده بيتفضّل عليها دايمًا."""
    jaw = _jaw_of(upper)
    v = max(0, variation_months)
    perm_min, perm_avg, perm_max = PERMANENT_ERUPTION_MONTHS[(jaw, pos)]
    perm_min -= v

    if pos not in PRIMARY_POSITIONS:
        # ضرس دائم مفيش له سن لبني قبله (الأول/الثاني/العقل)
        return PRESENT if age_months >= perm_min else UNERUPTED

    pri_min, pri_avg, pri_max = PRIMARY_ERUPTION_MONTHS[(jaw, pos)]
    exf_min, exf_avg, exf_max = PRIMARY_EXFOLIATION_MONTHS[(jaw, pos)]
    pri_min -= v
    exf_max += v

    if age_months < pri_min:
        # لسه بدري حتى على بزوغ اللبني - طبيعي تمامًا (مثلاً رضيع)
        return UNERUPTED
    if age_months < exf_min or age_months < perm_min:
        # اللبني المفروض يكون موجود لسه (قبل معاد سقوطه الطبيعي وقبل معاد
        # بزوغ الدائم بديله)
        return PRIMARY_PRESENT
    # دخلنا فترة الاستبدال الطبيعية أو بعدها
    return PRESENT if age_months >= perm_min else PRIMARY_PRESENT


def generate_chart(age_months, variation_months=0):
    """بترجع dict: {permanent_tooth_number: presence_status} للـ32 موضع سن
    كلهم (بترقيم FDI للسن الدائم كمفتاح ثابت للموضع - راجع الملاحظة في
    database.py) - دي الخريطة المبدئية اللي بتتخزن تلقائيًا أول ما يتعمل
    ملف مريض جديد وعنده تاريخ ميلاد"""
    result = {}
    for tooth_num in UPPER_ROW:
        pos = tooth_num % 10
        result[tooth_num] = expected_presence(pos, True, age_months, variation_months)
    for tooth_num in LOWER_ROW:
        pos = tooth_num % 10
        result[tooth_num] = expected_presence(pos, False, age_months, variation_months)
    return result


def primary_number_for(permanent_tooth_number):
    """بترجع رقم FDI للسن اللبني المقابل لموضع سن دائم معين، أو None لو
    الموضع ده (ضرس دائم) مفيش له سن لبني بيسبقه أصلاً"""
    pos = permanent_tooth_number % 10
    if pos not in PRIMARY_POSITIONS:
        return None
    perm_quadrant = permanent_tooth_number // 10
    primary_quadrant = perm_quadrant + 4  # 1->5, 2->6, 3->7, 4->8
    return primary_quadrant * 10 + pos
