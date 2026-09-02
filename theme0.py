# -*- coding: utf-8 -*-
"""
إعدادات الشكل العام للبرنامج (الألوان والخطوط)
الألوان والخطوط بتتقرا من قاعدة البيانات وتتغير من صفحة الإعدادات
"""

import os

# ---------------- اسم وشعار "البرنامج" نفسه (العلامة التجارية العامة) ----------------
# ده مختلف عن اسم/لوجو "العيادة" اللي بيستخدم البرنامج (اللي بيتغير من صفحة
# الإعدادات ومحفوظ في قاعدة البيانات). القيم دي مؤقتة لحد ما يتحدد الاسم
# واللوجو النهائي للبرنامج - عدّل القيمتين دول وبس عشان تغيّرهم في كل مكان
# ظاهرين فيه (حاليًا: شاشة تسجيل الدخول).
APP_NAME = "Dentora"
APP_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
APP_LOGO_PATH = os.path.join(APP_ASSETS_DIR, "dentora_icon.png")
# نسخة .ico من نفس اللوجو (دايرية، خلفية شفافة) - لازمة لأيقونة نافذة تسجيل
# الدخول تحديدًا، لأن customtkinter بيرجّع أيقونته الافتراضية لو استخدمنا
# iconphoto() بدل iconbitmap()؛ استخدام iconbitmap() بملف .ico هو الطريقة
# الوحيدة اللي بتمنع الاستبدال ده (شوف _apply_window_icon في main.py)
APP_LOGO_ICO_PATH = os.path.join(APP_ASSETS_DIR, "dentora_icon.ico")

# خيارات الخطوط المتاحة (كلها موجودة افتراضيًا على ويندوز وبتدعم العربي)
FONT_OPTIONS = [
    "Segoe UI", "Tahoma", "Arial", "Calibri",
    "Simplified Arabic", "Traditional Arabic", "Sakkal Majalla", "Andalus",
]

SIZE_OPTIONS = [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 24, 26, 28]

FONT_FAMILY = "Segoe UI"  # قيمة افتراضية احتياطية

# القيم دي بتتحدث من apply_from_settings() لما البرنامج يبدأ ولما تتغير الإعدادات
SYSTEM_FONT_FAMILY = "Segoe UI"
CONTENT_FONT_FAMILY = "Segoe UI"
SYSTEM_FONT_SIZE = 16
CONTENT_FONT_SIZE = 16

FONT_TITLE = (SYSTEM_FONT_FAMILY, 22, "bold")
FONT_SUBTITLE = (SYSTEM_FONT_FAMILY, 18, "bold")
FONT_NAV = (SYSTEM_FONT_FAMILY, 16, "bold")
FONT_NORMAL = (CONTENT_FONT_FAMILY, 16)
FONT_SMALL = (CONTENT_FONT_FAMILY, 14)

# ---------------- تعويض حجم الخط حسب نوع الفونط ----------------
# نفس الرقم بالبيكسل بيبان بأحجام مختلفة فعليًا حسب نوع الخط (مثلاً
# "Traditional Arabic" أنحف وأصغر بصريًا من "Segoe UI" في نفس المقاس).
# الجدول ده بيضيف/يطرح شوية بكسلات تلقائيًا حسب الخط المختار، عشان أي
# توكن حجمه "ثابت" (زي دول تحت) يفضل بنفس الحجم المُدرَك بصريًا مهما
# غيّر المستخدم نوع الخط من الإعدادات - من غير ما هو يلمس أي رقم يدويًا.
FONT_SIZE_COMPENSATION = {
    "Segoe UI": 0,
    "Tahoma": 0,
    "Arial": 0,
    "Calibri": 1,
    "Simplified Arabic": 2,
    "Traditional Arabic": 3,
    "Sakkal Majalla": -1,
    "Andalus": 1,
}


def compensated_size(base_size, family=None):
    """بترجع الحجم بعد إضافة تعويض نوع الخط (family) - لو family مش متحدد
    بتستخدم CONTENT_FONT_FAMILY الحالي"""
    family = family or CONTENT_FONT_FAMILY
    return base_size + FONT_SIZE_COMPENSATION.get(family, 0)


# ---------------- توكنز خطوط ثابتة الحجم لعناصر جدول المواعيد والكالندر
# الصغير ----------------
# الأحجام دي *مش* مرتبطة بمقاس "خط المحتوى" العام اللي بيتغيّر من صفحة
# الإعدادات (CONTENT_FONT_SIZE) - دي عناصر واجهة صغيرة وكثيفة (هيدر أعمدة،
# أرقام ساعات، اسم مريض جوه بلوك ضيق) لازم تفضل بمقاس ثابت ومدروس بغض
# النظر عن اختيار المستخدم لحجم خط المحتوى العام، وبيتغيّر فيها بس نوع
# الخط (family) + تعويض الحجم البصري تبعه (compensated_size)
FONT_CALENDAR_DAY_HEADER = (CONTENT_FONT_FAMILY, compensated_size(12), "bold")
FONT_HOUR_TICK = (CONTENT_FONT_FAMILY, compensated_size(12), "bold")
FONT_HALF_HOUR_TICK = (CONTENT_FONT_FAMILY, compensated_size(11), "bold")
FONT_APPOINTMENT_LABEL = (CONTENT_FONT_FAMILY, compensated_size(15), "bold")
FONT_MINI_CAL_LABEL = (CONTENT_FONT_FAMILY, compensated_size(13))
# خط أكبر شوية من FONT_APPOINTMENT_LABEL بنفس النوع/التخانة - لعناوين
# وحقول نوافذ الحوار (زي نافذة تفاصيل الحجز وتعديله) عشان تبقى واضحة
# وبارزة زي اسم الحجز في صفحة المواعيد بالظبط مش أصغر منه
FONT_DIALOG_LABEL = (CONTENT_FONT_FAMILY, compensated_size(18), "bold")
# ده التوكن الوحيد اللي حجمه *مرتبط* بمقاس خط المحتوى العام (CONTENT_FONT_SIZE)
# مش رقم منفصل - عشان لو حبينا نغيّر إحساس حجم الخط العام في البرنامج كله
# (مستقبلًا، من كود مش من إعدادات المستخدم)، الأزرار دي تتحرك معاه تلقائيًا
FONT_TABLE_NAV_BUTTON = (CONTENT_FONT_FAMILY, compensated_size(CONTENT_FONT_SIZE - 3), "bold")
# خط التلميح (Tooltip) اللي بيظهر لما الماوس يوقف فوق حجز في الجدول
FONT_APPT_TOOLTIP = (CONTENT_FONT_FAMILY, compensated_size(12))
# خط القائمة المنبثقة (Right-click) على الحجوزات
FONT_CONTEXT_MENU = (CONTENT_FONT_FAMILY, compensated_size(13))


# ---------------- ثوابت موحّدة للأبعاد والمسافات (عشان الشكل يبقى متسق في
# البرنامج كله - كل الكروت/الأزرار/الفواصل تستخدم نفس القيم دي بدل ما كل
# صفحة تختار رقم مختلف بنفسها) ----------------

# انحناء الحواف (corner_radius) - 3 مستويات بس عشان التناسق
RADIUS_SM = 6    # عناصر صغيرة: أزرار ثانوية، شارات، حقول إدخال
RADIUS_MD = 10   # عناصر متوسطة: أزرار رئيسية، صفوف الجداول
RADIUS_LG = 16   # عناصر كبيرة: الكروت الرئيسية، النوافذ المنبثقة

# المسافات (padding/spacing) - 3 مستويات بس عشان التناسق
SPACING_SM = 8    # مسافة داخلية صغيرة (بين عناصر متجاورة قريبة من بعض)
SPACING_MD = 16   # مسافة قياسية (padding الكروت والصفحات الفرعية)
SPACING_LG = 24   # مسافة كبيرة (padding حول محتوى الصفحة الرئيسي)


def rebuild_fonts():
    """يعيد حساب كل مقاسات الخط بناءً على القيم الحالية"""
    global FONT_TITLE, FONT_SUBTITLE, FONT_NAV, FONT_NORMAL, FONT_SMALL
    global FONT_CALENDAR_DAY_HEADER, FONT_HOUR_TICK, FONT_HALF_HOUR_TICK
    global FONT_APPOINTMENT_LABEL, FONT_MINI_CAL_LABEL, FONT_TABLE_NAV_BUTTON
    global FONT_APPT_TOOLTIP, FONT_CONTEXT_MENU, FONT_DIALOG_LABEL
    FONT_TITLE = (SYSTEM_FONT_FAMILY, SYSTEM_FONT_SIZE + 6, "bold")
    FONT_SUBTITLE = (SYSTEM_FONT_FAMILY, SYSTEM_FONT_SIZE + 2, "bold")
    FONT_NAV = (SYSTEM_FONT_FAMILY, SYSTEM_FONT_SIZE, "bold")
    FONT_NORMAL = (CONTENT_FONT_FAMILY, CONTENT_FONT_SIZE)
    FONT_SMALL = (CONTENT_FONT_FAMILY, max(CONTENT_FONT_SIZE - 3, 10))

    # توكنز الأحجام الثابتة (مش مرتبطة بـ CONTENT_FONT_SIZE) - بس بتاخد
    # تعويض بصري حسب نوع الخط الحالي (شوف compensated_size فوق)
    FONT_CALENDAR_DAY_HEADER = (CONTENT_FONT_FAMILY, compensated_size(12), "bold")
    FONT_HOUR_TICK = (CONTENT_FONT_FAMILY, compensated_size(12), "bold")
    FONT_HALF_HOUR_TICK = (CONTENT_FONT_FAMILY, compensated_size(11), "bold")
    FONT_APPOINTMENT_LABEL = (CONTENT_FONT_FAMILY, compensated_size(15), "bold")
    FONT_MINI_CAL_LABEL = (CONTENT_FONT_FAMILY, compensated_size(13))
    FONT_DIALOG_LABEL = (CONTENT_FONT_FAMILY, compensated_size(18), "bold")
    FONT_TABLE_NAV_BUTTON = (CONTENT_FONT_FAMILY, compensated_size(CONTENT_FONT_SIZE - 3), "bold")
    FONT_APPT_TOOLTIP = (CONTENT_FONT_FAMILY, compensated_size(12))
    FONT_CONTEXT_MENU = (CONTENT_FONT_FAMILY, compensated_size(13))


def apply_from_settings(settings: dict):
    """بتتنادى لما البرنامج يبدأ وبعد كل حفظ للإعدادات.
    ملحوظة: مقاس الخط (SYSTEM_FONT_SIZE/CONTENT_FONT_SIZE) بقى ثابت في الكود
    ومش بيتقرأ من الإعدادات تاني - المستخدم بيقدر يغيّر نوع الخط بس (family)،
    مش حجمه، عشان الاتساق يفضل مضمون في كل الشاشات."""
    global SYSTEM_FONT_FAMILY, CONTENT_FONT_FAMILY
    SYSTEM_FONT_FAMILY = settings.get("system_font_family") or SYSTEM_FONT_FAMILY
    CONTENT_FONT_FAMILY = settings.get("content_font_family") or CONTENT_FONT_FAMILY
    rebuild_fonts()
    apply_theme_palette(settings.get("theme_id"))


# ---------------- الثيمات الجاهزة (لوحات ألوان كاملة، مش لون واحد بس) ----------------
# كل ثيم بيغيّر: اللون الأساسي (هيدر الشريط العلوي والأزرار الرئيسية)،
# خلفية الصفحة، خلفية الكروت، ولون النصوص - مش بس اللون الأساسي زي الاختيار
# اليدوي القديم. الألوان الدلالية (نجاح/خطر/تحذير) والأنماط الغاطسة لصناديق
# الإدخال ثابتة في كل الثيمات عشان تفضل واضحة ومتسقة أينما كانت
# كل ثيم دلوقتي "ثيم حقيقي" مش مجرد لون واحد: بيحدد تدرج الهيدر (من لون
# لآخر، زي هيدرات ويندوز 7/XP/أوفيس 2010 الشهيرة)، ولون حد مميز (accent)
# يفرّق شكل الثيم عن التاني، وألوان التابات (المفتوحة/المقفولة). لو ثيم
# ما حددش القيم دي بنفسه، بيتحسبوا تلقائيًا من primary/secondary (شوف
# _fill_theme_defaults) عشان أي ثيم قديم أو مضاف لاحقًا يفضل شغال ومتناسق.
THEME_PRESETS = {
    # ---- ثيمات العلامة التجارية الأصلية (ألوان مسطحة أنيقة) ----
    "ocean_blue": {
        "name": "أزرق المحيط",
        "primary": "#1E88E5", "secondary": "#0D47A1",
        "bg_main": "#F5F6FA", "card_bg": "#FFFFFF",
        "text_dark": "#1B1E23", "text_muted": "#6B7280", "border": "#E5E7EB",
    },
    "medical_teal": {
        "name": "أخضر طبي",
        "primary": "#00897B", "secondary": "#00695C",
        "bg_main": "#F3F8F7", "card_bg": "#FFFFFF",
        "text_dark": "#14201E", "text_muted": "#5C7570", "border": "#D9E7E4",
    },
    "royal_purple": {
        "name": "بنفسجي ملكي",
        "primary": "#7C3AED", "secondary": "#5B21B6",
        "bg_main": "#F7F5FC", "card_bg": "#FFFFFF",
        "text_dark": "#201A2E", "text_muted": "#6E6480", "border": "#E4DFF2",
    },
    "warm_burgundy": {
        "name": "عنابي دافئ",
        "primary": "#C2185B", "secondary": "#880E4F",
        "bg_main": "#FBF5F7", "card_bg": "#FFFFFF",
        "text_dark": "#241418", "text_muted": "#7A5F68", "border": "#F0DDE3",
    },
    "sunset_orange": {
        "name": "برتقالي غروب",
        "primary": "#FB8C00", "secondary": "#E65100",
        "bg_main": "#FFF8F2", "card_bg": "#FFFFFF",
        "text_dark": "#241C14", "text_muted": "#8A6E52", "border": "#F5E3D0",
    },

    # ---- ثيمات "أنظمة تشغيل/برامج" شهيرة، بروح راقية تناسب برنامج طبي ----
    "aero_glass": {
        # مستوحى من زجاجية Windows 7 Aero: تدرج أزرق لامع في الهيدر،
        # وحد فولاذي غامق واضح، وتابات زجاجية فاتحة
        "name": "أزرق زجاجي (Aero)",
        "primary": "#2E6DA4", "secondary": "#1B3F63",
        "bg_main": "#EDF3FA", "card_bg": "#FFFFFF",
        "text_dark": "#152738", "text_muted": "#5C7086", "border": "#B9CCE0",
        "header_grad_start": "#5FA0DE", "header_grad_end": "#0F3A63",
        "accent_border": "#0F3A63",
        "tab_active": "#FFFFFF", "tab_inactive": "#CBDCEE",
    },
    "xp_royal": {
        # مستوحى من الأزرق الملكي/الفضي لـ Windows XP: تدرج أزرق-كوبالتي
        # قوي في الهيدر، مع حد ذهبي-فضي مميز يوضّح الفواصل
        "name": "أزرق ملكي كلاسيكي (XP)",
        "primary": "#245EDC", "secondary": "#0B2E82",
        "bg_main": "#EEF2FB", "card_bg": "#FFFFFF",
        "text_dark": "#141B2E", "text_muted": "#586082", "border": "#C7D0EC",
        "header_grad_start": "#3C79F2", "header_grad_end": "#08205C",
        "accent_border": "#F0A93B",
        "tab_active": "#FFFFFF", "tab_inactive": "#D7E0F7",
    },
    "office_ribbon": {
        # مستوحى من شريط أوفيس 2010: تدرج أزرق داكن هادئ في الهيدر مع خط
        # حد رفيع تحته، وتابات مربّعة الحواف تقريبًا زي شريط الأدوات
        "name": "أزرق أوفيس (Ribbon)",
        "primary": "#1F5C8B", "secondary": "#123A5C",
        "bg_main": "#F1F4F7", "card_bg": "#FFFFFF",
        "text_dark": "#1A2530", "text_muted": "#5A6B78", "border": "#D2DBE2",
        "header_grad_start": "#2E7DB0", "header_grad_end": "#0E3554",
        "accent_border": "#0E3554",
        "tab_active": "#FFFFFF", "tab_inactive": "#DCE7EF",
        "tab_radius": 3,
    },
    "graphite_dark": {
        # ثيم غامق راقٍ للتسويق (شاشات عرض/فيديوهات) - تدرج رمادي-أسود
        # في الهيدر مع حد نحاسي دافئ يعطي إحساس فخامة
        "name": "جرافيت غامق",
        "primary": "#3A3F47", "secondary": "#1C1F24",
        "bg_main": "#F1F1F2", "card_bg": "#FFFFFF",
        "text_dark": "#1B1D21", "text_muted": "#6B6E73", "border": "#DADBDD",
        "header_grad_start": "#565C66", "header_grad_end": "#15171B",
        "accent_border": "#B08A4E",
        "tab_active": "#FFFFFF", "tab_inactive": "#E2E3E5",
    },
    "emerald_exec": {
        # ثيم أخضر زمردي تنفيذي راقٍ - تدرج غامق فخم مع حد ذهبي دافئ
        "name": "زمردي تنفيذي",
        "primary": "#1B7A5C", "secondary": "#0E4A38",
        "bg_main": "#F0F7F4", "card_bg": "#FFFFFF",
        "text_dark": "#12241D", "text_muted": "#5B6F68", "border": "#D6E7E1",
        "header_grad_start": "#2E9E78", "header_grad_end": "#0A3A2C",
        "accent_border": "#C9A24B",
        "tab_active": "#FFFFFF", "tab_inactive": "#D9EDE6",
    },
    "carbon_crimson": {
        # ثيم غامق جريء بلمسة عنابية - مناسب لعرض تسويقي مميز
        "name": "كربوني عنابي",
        "primary": "#7A1F2B", "secondary": "#3B0F16",
        "bg_main": "#F6EEEF", "card_bg": "#FFFFFF",
        "text_dark": "#241416", "text_muted": "#7A6467", "border": "#E7D6D8",
        "header_grad_start": "#A83346", "header_grad_end": "#2A0A0F",
        "accent_border": "#D9B25A",
        "tab_active": "#FFFFFF", "tab_inactive": "#EDD9DB",
    },
    "sandstone_gold": {
        # ثيم فاتح دافئ راقٍ (رملي/ذهبي) - مختلف تمامًا عن الأزرقات التقليدية
        "name": "رملي ذهبي",
        "primary": "#A9782E", "secondary": "#6E4E1C",
        "bg_main": "#FBF6EC", "card_bg": "#FFFFFF",
        "text_dark": "#2A2113", "text_muted": "#8A7752", "border": "#EBDDBB",
        "header_grad_start": "#CDA24F", "header_grad_end": "#5A3D14",
        "accent_border": "#5A3D14",
        "tab_active": "#FFFFFF", "tab_inactive": "#F0E3C4",
    },

    # ---- بناتي كلاسيكي (ألوان وردية/بنفسجية ناعمة وأنيقة) ----
    "girly_blush": {
        "name": "بناتي كلاسيك - وردي بودرة",
        "primary": "#D46A9D", "secondary": "#A94A78",
        "bg_main": "#FFF6FA", "card_bg": "#FFFFFF",
        "text_dark": "#2E1E27", "text_muted": "#8A6A78", "border": "#F3D9E6",
    },
    "girly_lavender": {
        "name": "بناتي كلاسيك - بنفسجي فاتح",
        "primary": "#B47EE5", "secondary": "#7C4DB8",
        "bg_main": "#FAF6FF", "card_bg": "#FFFFFF",
        "text_dark": "#241C33", "text_muted": "#7A6D91", "border": "#E9DFF7",
    },
    "girly_peach": {
        "name": "بناتي كلاسيك - خوخي ناعم",
        "primary": "#F0918A", "secondary": "#D45F57",
        "bg_main": "#FFF7F5", "card_bg": "#FFFFFF",
        "text_dark": "#2E1E1B", "text_muted": "#8A6E68", "border": "#F6DEDA",
    },
    "girly_rosegold": {
        "name": "بناتي كلاسيك - ذهبي وردي",
        "primary": "#D9A0A0", "secondary": "#B57373",
        "bg_main": "#FFF8F5", "card_bg": "#FFFFFF",
        "text_dark": "#2A1F1D", "text_muted": "#8B7370", "border": "#F1DFDA",
    },

    # ---- شبابي (ألوان جريئة وحيوية) ----
    "youth_neon_coral": {
        "name": "شبابي - مرجاني نيون",
        "primary": "#FF5E62", "secondary": "#C62828",
        "bg_main": "#FFF5F4", "card_bg": "#FFFFFF",
        "text_dark": "#241414", "text_muted": "#8A6560", "border": "#FBD9D6",
    },
    "youth_electric_blue": {
        "name": "شبابي - أزرق كهربائي",
        "primary": "#2E7CF6", "secondary": "#1449A6",
        "bg_main": "#F2F7FF", "card_bg": "#FFFFFF",
        "text_dark": "#141B2E", "text_muted": "#5C6B8A", "border": "#D6E3FA",
    },
    "youth_lime_punch": {
        "name": "شبابي - أخضر ليموني",
        "primary": "#7CB518", "secondary": "#4C7A0A",
        "bg_main": "#F7FCF0", "card_bg": "#FFFFFF",
        "text_dark": "#1C2410", "text_muted": "#6C7A55", "border": "#DCEEC0",
    },
    # ---- صيفي (ألوان استوائية منعشة) ----
    "summer_turquoise": {
        "name": "صيفي - تركواز استوائي",
        "primary": "#00BFA5", "secondary": "#00786B",
        "bg_main": "#EFFCFA", "card_bg": "#FFFFFF",
        "text_dark": "#0F2624", "text_muted": "#5A7C78", "border": "#C9EDE7",
    },
    "summer_coral_reef": {
        "name": "صيفي - مرجاني الشعاب",
        "primary": "#FF7F50", "secondary": "#E2552B",
        "bg_main": "#FFF6F0", "card_bg": "#FFFFFF",
        "text_dark": "#2A1D14", "text_muted": "#8C6E56", "border": "#F8DFCC",
    },
    "summer_mango": {
        "name": "صيفي - مانجو صيفي",
        "primary": "#FFC93C", "secondary": "#E0A100",
        "bg_main": "#FFFBEF", "card_bg": "#FFFFFF",
        "text_dark": "#2A2410", "text_muted": "#8C7E4E", "border": "#F6ECC4",
    },
    # ---- دارك مود (خلفيات غامقة حقيقية للاستخدام الليلي) ----
    "dark_slate": {
        "name": "دارك مود - رمادي غامق",
        "primary": "#5C8DEA", "secondary": "#35507F",
        "bg_main": "#1A1D23", "card_bg": "#23262E",
        "text_dark": "#ECEDF1", "text_muted": "#98A0AC", "border": "#343841",
        "header_grad_start": "#6FA0F5", "header_grad_end": "#223257",
        "accent_border": "#6FA0F5",
        "tab_active": "#2A2E37", "tab_inactive": "#1E2127",
    },
    "dark_midnight_blue": {
        "name": "دارك مود - أزرق الليل",
        "primary": "#4C6FFF", "secondary": "#24337A",
        "bg_main": "#10131C", "card_bg": "#191D29",
        "text_dark": "#E9EBF5", "text_muted": "#8E93AE", "border": "#262B3B",
        "header_grad_start": "#5C7CFF", "header_grad_end": "#161B33",
        "accent_border": "#5C7CFF",
        "tab_active": "#20263A", "tab_inactive": "#151827",
    },
    "dark_teal": {
        "name": "دارك مود - تركواز غامق",
        "primary": "#26A69A", "secondary": "#12554D",
        "bg_main": "#10201D", "card_bg": "#182B27",
        "text_dark": "#E3F3EF", "text_muted": "#85A8A0", "border": "#24403A",
        "header_grad_start": "#34C0B1", "header_grad_end": "#0C2E29",
        "accent_border": "#34C0B1",
        "tab_active": "#1F3833", "tab_inactive": "#142521",
    },
}
DEFAULT_THEME_ID = "ocean_blue"


def darken_color(hex_color, factor=0.78):
    """بترجع نسخة أغمق من اللون المُدخل (مفيدة لحالة hover عشان تفضل الأيقونة البيضاء واضحة)"""
    hex_color = hex_color.lstrip("#")
    try:
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return hex_color
    r, g, b = (max(0, int(c * factor)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten_color(hex_color, factor=0.25):
    """بترجع نسخة أفتح من اللون المُدخل (بتخلط مع الأبيض بنسبة factor).
    factor=0 بيرجع نفس اللون، factor=1 بيرجع أبيض تمامًا"""
    hex_color = hex_color.lstrip("#")
    try:
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return hex_color
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _fill_theme_defaults(preset):
    """أي ثيم ما حددش تدرج الهيدر/لون الحد المميز/ألوان التابات بنفسه،
    بنحسبهم تلقائيًا من primary/secondary بتاعته - عشان كل الثيمات (القديمة
    والجديدة) تظهر بشكل "ثيم حقيقي" متكامل من غير ما نكرر كل القيم يدويًا"""
    primary = preset["primary"]
    secondary = preset["secondary"]
    preset.setdefault("header_grad_start", lighten_color(primary, 0.18))
    preset.setdefault("header_grad_end", secondary)
    preset.setdefault("accent_border", darken_color(secondary, 0.75))
    preset.setdefault("tab_active", preset["card_bg"])
    preset.setdefault("tab_inactive", lighten_color(preset["border"], 0.35))
    preset.setdefault("tab_radius", 10)
    # تدرج التابات: التاب المفعّلة بتاخد تدرج بلون الثيم الأساسي (فاتح شوية
    # فوق) وتنتهي تحت بلون خلفية الكارت نفسه - عشان تندمج بصريًا مع محتواها
    # من غير ما نحتاج نرسم أي حد سفلي أصلًا. التابات المقفولة بتاخد تدرج
    # محايد رمادي/بلون التاب المقفول العادي، أفتح شوية فوق وأغمق شوية تحت،
    # عشان تبان مختلفة وواضح إنها "خلف" التاب المفتوحة
    preset.setdefault("tab_active_grad_top", lighten_color(preset["primary"], 0.55))
    preset.setdefault("tab_active_grad_bottom", preset["tab_active"])
    preset.setdefault("tab_inactive_grad_top", lighten_color(preset["tab_inactive"], 0.4))
    preset.setdefault("tab_inactive_grad_bottom", darken_color(preset["tab_inactive"], 0.92))
    return preset


for _theme_id, _preset in THEME_PRESETS.items():
    _fill_theme_defaults(_preset)


def apply_theme_palette(theme_id):
    """بتطبّق لوحة ألوان الثيم المختار (خلفية الصفحة/الكروت/النصوص + تدرج
    الهيدر ولون الحد المميز وألوان التابات) على الثوابت المحايدة. ملحوظة:
    مبتلمسش primary_color/secondary_color في قاعدة البيانات نفسها - دي
    بتتحدث من set_theme() في database.py، عشان أي كود قديم بيقرا
    settings[\"primary_color\"] مباشرة يفضل شغال زي ما هو"""
    global BG_MAIN, CARD_BG, TEXT_DARK, TEXT_MUTED, BORDER
    global HEADER_GRAD_START, HEADER_GRAD_END, ACCENT_BORDER, PRIMARY_LIGHT
    global TAB_ACTIVE_BG, TAB_INACTIVE_BG, TAB_RADIUS
    global TAB_ACTIVE_GRAD_TOP, TAB_ACTIVE_GRAD_BOTTOM
    global TAB_INACTIVE_GRAD_TOP, TAB_INACTIVE_GRAD_BOTTOM
    preset = THEME_PRESETS.get(theme_id) or THEME_PRESETS[DEFAULT_THEME_ID]
    BG_MAIN = preset["bg_main"]
    CARD_BG = preset["card_bg"]
    TEXT_DARK = preset["text_dark"]
    TEXT_MUTED = preset["text_muted"]
    BORDER = preset["border"]
    HEADER_GRAD_START = preset["header_grad_start"]
    HEADER_GRAD_END = preset["header_grad_end"]
    ACCENT_BORDER = preset["accent_border"]
    # لون الثيم الفاتح (اللون الأساسي "primary" بتاع الثيم نفسه، قبل ما
    # يتغمّق)، بيتستخدم في أماكن زي تحديد اليوم في الكالندر الصغير عشان
    # يبان بلون الثيم الفاتح مش لون الحد الغامق (accent_border)
    PRIMARY_LIGHT = preset["primary"]
    TAB_ACTIVE_BG = preset["tab_active"]
    TAB_INACTIVE_BG = preset["tab_inactive"]
    TAB_RADIUS = preset["tab_radius"]
    TAB_ACTIVE_GRAD_TOP = preset["tab_active_grad_top"]
    TAB_ACTIVE_GRAD_BOTTOM = preset["tab_active_grad_bottom"]
    TAB_INACTIVE_GRAD_TOP = preset["tab_inactive_grad_top"]
    TAB_INACTIVE_GRAD_BOTTOM = preset["tab_inactive_grad_bottom"]


# ألوان محايدة ثابتة (مش بتتغير من الإعدادات)
BG_MAIN = "#F5F6FA"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#1B1E23"
TEXT_MUTED = "#6B7280"
BORDER = "#E5E7EB"
HEADER_GRAD_START = "#4FA0E8"
HEADER_GRAD_END = "#0D47A1"
ACCENT_BORDER = "#0D47A1"
PRIMARY_LIGHT = "#1E88E5"
TAB_ACTIVE_BG = "#FFFFFF"
TAB_INACTIVE_BG = "#E5E7EB"
TAB_RADIUS = 10
TAB_ACTIVE_GRAD_TOP = "#DCEBFB"
TAB_ACTIVE_GRAD_BOTTOM = "#FFFFFF"
TAB_INACTIVE_GRAD_TOP = "#F1F2F5"
TAB_INACTIVE_GRAD_BOTTOM = "#D8DADE"
DANGER = "#E53935"
SUCCESS = "#43A047"
WARNING = "#FB8C00"

# حالات السن ولون كل حالة في مخطط الأسنان
TOOTH_STATUSES = {
    "healthy":   {"label": "سليم",        "color": "#FFFFFF", "text": "#1B1E23"},
    "decay":     {"label": "تسوس",        "color": "#E53935", "text": "#FFFFFF"},
    "filled":    {"label": "محشو",        "color": "#1E88E5", "text": "#FFFFFF"},
    "crown":     {"label": "تاج",         "color": "#8E24AA", "text": "#FFFFFF"},
    "root_canal":{"label": "عصب",         "color": "#FB8C00", "text": "#FFFFFF"},
    "extracted": {"label": "مخلوع",       "color": "#9E9E9E", "text": "#FFFFFF"},
    "implant":   {"label": "زراعة",       "color": "#00897B", "text": "#FFFFFF"},
}

APPOINTMENT_STATUSES = {
    "confirmed": {"label": "مؤكد",   "color": "#1E88E5"},
    "arrived":   {"label": "حضر",    "color": "#43A047"},
    "late":      {"label": "متأخر",  "color": "#8E24AA"},
    "completed": {"label": "انتهى",  "color": "#6B7280"},
    "cancelled": {"label": "ملغي",   "color": "#E53935"},
    "no_show":   {"label": "لم يحضر","color": "#FB8C00"},
}

# لوحة ألوان (70 لون) لتمييز أنواع المعالجات والأنواع الفرعية على شارت الأسنان
# مرتبة بتدرج منطقي: أبيض -> أصفر -> برتقالي -> أحمر -> وردي -> بنفسجي ->
# أزرق -> تركواز -> أخضر -> بني -> رمادي غامق -> أسود
TREATMENT_COLOR_PALETTE = [
    "#FFFFFF",
    "#FFFDE7", "#FFF9C4", "#FFF59D", "#FFF176", "#FFEE58", "#FDD835", "#F9A825",
    "#FFF3E0", "#FFE0B2", "#FFCC80", "#FFB74D", "#FFA726", "#FB8C00", "#E65100",
    "#FFEBEE", "#FFCDD2", "#EF9A9A", "#E57373", "#EF5350", "#E53935", "#B71C1C",
    "#FCE4EC", "#F8BBD0", "#F48FB1", "#F06292", "#EC407A", "#D81B60", "#880E4F",
    "#F3E5F5", "#E1BEE7", "#CE93D8", "#BA68C8", "#AB47BC", "#8E24AA", "#4A148C",
    "#E3F2FD", "#BBDEFB", "#90CAF9", "#64B5F6", "#42A5F5", "#1E88E5", "#0D47A1",
    "#E0F2F1", "#B2DFDB", "#80CBC4", "#4DB6AC", "#26A69A", "#00897B", "#004D40",
    "#E8F5E9", "#C8E6C9", "#A5D6A7", "#81C784", "#66BB6A", "#43A047", "#1B5E20",
    "#EFEBE9", "#D7CCC8", "#BCAAA4", "#A1887F", "#8D6E63", "#6D4C41", "#3E2723",
    "#E0E0E0", "#BDBDBD", "#9E9E9E", "#757575", "#616161", "#000000",
]


def make_transparent_ctk_image(image_path, target_height):
    """بترجع الصورة الأصلية (بخلفيتها الشفافة زي ما هي، من غير أي قص دائري
    أو خلفية مضافة) كـ CTkImage، بارتفاع target_height مع حفاظ على نسبة
    العرض للارتفاع الأصلية - مفيدة لعرض لوجو شفاف مباشرة فوق خلفية ملوّنة
    (زي هيدر شاشة تسجيل الدخول) من غير أي دايرة أو مستطيل حواليه."""
    if not image_path or not os.path.exists(image_path):
        print(f"[theme] تحذير: ملف اللوجو مش موجود في المسار: {image_path}")
        return None
    try:
        from PIL import Image
        import customtkinter as ctk

        src = Image.open(image_path).convert("RGBA")
        ratio = src.width / src.height
        target_width = max(int(target_height * ratio), 1)
        return ctk.CTkImage(light_image=src, dark_image=src, size=(target_width, target_height))
    except Exception as e:
        print(f"[theme] تحذير: فشل تحميل اللوجو {image_path} - {e}")
        return None


def make_circular_pil_image(image_path, size, border_color=None, border_width=0):
    """نفس فكرة make_circular_ctk_image بالظبط، لكن بترجع كائن PIL.Image خام
    (مش CTkImage) - مفيدة لما محتاجين نستخدم الصورة الدائرية في حاجة مش
    ودجت مباشر، زي أيقونة النافذة (iconphoto) اللي محتاجة ImageTk.PhotoImage"""
    if not image_path or not os.path.exists(image_path):
        print(f"[theme] تحذير: ملف اللوجو مش موجود في المسار: {image_path}")
        return None
    try:
        from PIL import Image, ImageDraw

        scale = 4  # نرسم بحجم أكبر من المطلوب ثم نصغّر، عشان حواف الدائرة تطلع ناعمة
        s = size * scale
        src = Image.open(image_path).convert("RGBA")

        # نقص من نص الصورة مربع (أكبر مربع ممكن) قبل التصغير عشان محتواها ميتمططش
        w, h = src.size
        side = min(w, h)
        left, top = (w - side) // 2, (h - side) // 2
        src = src.crop((left, top, left + side, top + side)).resize((s, s), Image.LANCZOS)

        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, s, s), fill=255)

        result = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        result.paste(src, (0, 0), mask)

        if border_width and border_color:
            bw = border_width * scale
            ImageDraw.Draw(result).ellipse(
                (bw // 2, bw // 2, s - bw // 2, s - bw // 2), outline=border_color, width=bw)

        return result.resize((size, size), Image.LANCZOS)
    except Exception as e:
        print(f"[theme] تحذير: فشل تحميل اللوجو {image_path} - {e}")
        return None


def make_circular_ctk_image(image_path, size, border_color=None, border_width=0):
    """بتفتح صورة من المسار المُعطى وترجعها كـ CTkImage دائرية الشكل (مقصوصة
    بقناع دائري) بمقاس size×size، مع إمكانية إضافة حد ملوّن حواليها - عشان
    شعار البرنامج وشعار العيادة يظهروا بنفس الشكل الموحّد الاحترافي في كل
    مكان (حاليًا: شاشة تسجيل الدخول). لو الصورة مش موجودة أو حصل خطأ في
    فتحها بترجع None عشان تظهر أيقونة احتياطية بدلها."""
    result = make_circular_pil_image(image_path, size, border_color, border_width)
    if result is None:
        return None
    try:
        import customtkinter as ctk
        return ctk.CTkImage(light_image=result, dark_image=result, size=(size, size))
    except Exception as e:
        print(f"[theme] تحذير: فشل تحميل اللوجو {image_path} - {e}")
        return None


def _lerp_color(c1, c2, t):
    """بترجع لون بينهم بنسبة t (0=c1, 1=c2) - مستخدمة لرسم التدرج"""
    c1 = c1.lstrip("#")
    c2 = c2.lstrip("#")
    r1, g1, b1 = (int(c1[i:i + 2], 16) for i in (0, 2, 4))
    r2, g2, b2 = (int(c2[i:i + 2], 16) for i in (0, 2, 4))
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def draw_vertical_gradient(canvas, width, height, color_top, color_bottom):
    """بترسم تدرج لوني رأسي ناعم تمامًا (من فوق لتحت) باستخدام PIL بدل رسم
    مستطيلات متجاورة - عشان النتيجة تبقى تدرج حقيقي من غير أي خطوط أو
    قطاعات بينة. لازم نحتفظ بمرجع للصورة (canvas.image = ...) عشان
    Python متمسحهاش من الذاكرة (garbage collector) وتختفي الصورة"""
    canvas.delete("gradient")
    width, height = max(int(width), 1), max(int(height), 1)
    try:
        from PIL import Image, ImageTk
        top_rgb = tuple(int(color_top.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        bot_rgb = tuple(int(color_bottom.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        grad_col = Image.new("RGB", (1, height))
        for y in range(height):
            t = y / max(height - 1, 1)
            px = tuple(int(top_rgb[i] + (bot_rgb[i] - top_rgb[i]) * t) for i in range(3))
            grad_col.putpixel((0, y), px)
        img = grad_col.resize((width, height))
        photo = ImageTk.PhotoImage(img)
        canvas.image = photo  # مرجع دائم يمنع الصورة من الاختفاء
        canvas.create_image(0, 0, anchor="nw", image=photo, tags="gradient")
    except Exception:
        # خطة بديلة لو PIL مش متاحة لأي سبب: تدرج مبسّط بس رأسي برضو
        canvas.create_rectangle(0, 0, width, height, fill=color_top, outline=color_top, tags="gradient")


def rounded_rect_points(x1, y1, x2, y2, radius):
    """بترجع قائمة نقاط مضلّع مستطيل بحواف دائرية - تُستخدم مع
    canvas.create_polygon(points, smooth=True, ...) عشان نرسم مستطيلات
    (خلفية/حدود) بحواف ناعمة مباشرة على Canvas من غير ما نستخدم أي ودجت
    CTk (اللي بترسم خلفيتها بلون صلب دايمًا حتى لو fg_color=\"transparent\"،
    وده اللي بيعمل \"الإطار الصلب\" فوق خلفية الهيدر المتدرجة)"""
    radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]


# ---------------- تصاميم أزرار الشريط العلوي (ribbon) ----------------
# ثلاث هويات بصرية مختلفة لأزرار التنقل الرئيسية: "classic" (الأصلي)،
# و"glass" (عصري زجاجي/Glassmorphism)، و"luxury" (فخم بحواف ذهبية).
# محفوظة هنا مركزيًا عشان تُستخدم في الرسم الفعلي (main.py) وفي معرض
# الاختيار بصفحة الإعدادات بنفس المنطق بالظبط.
NAV_BUTTON_STYLES = {
    "classic": {"name": "الكلاسيكي", "desc": "الشكل الحالي - كارت بسيط بلون العيادة"},
    "glass": {"name": "زجاجي عصري", "desc": "كارت شفاف ناعم بحواف مضيئة (Glassmorphism)"},
    "luxury": {"name": "فاخر ذهبي", "desc": "كارت غامق بحواف وتفاصيل ذهبية فخمة"},
}
NAV_LUXURY_GOLD = "#D4AF37"

# ---------------- أنماط رسم أيقونات الشريط العلوي الرئيسية ----------------
# ده شكل "الرسمة" نفسها لكل أيقونة (تصميم البند الايقوني زي شنطة المستلزمات
# مثلاً) - مستقل تمامًا عن NAV_BUTTON_STYLES اللي بيتحكم بس في شكل خلفية
# الزرار. كل نمط هنا له رسمة مختلفة فعليًا لكل أيقونة (شوف pages/icons.py)
ICON_PATTERNS = {
    "outline": {"name": "الخطي الكلاسيكي", "desc": "رسم بخطوط رفيعة بسيطة بلون واحد (الشكل الأصلي)"},
    "filled": {"name": "المعبأ الملوّن", "desc": "أشكال مصمتة بلونين مختلفين ثابتين لكل أيقونة"},
}


def make_glass_nav_card(w, h, radius=16, active=False, enabled=True):
    """بترجع صورة PIL (RGBA) لكارت زرار بأسلوب زجاجي شفاف (Glassmorphism):
    تعبئة بيضاء شبه شفافة + حدود مضيئة رفيعة + خط لمعان أعلى الكارت.
    بترتسم فوق أي خلفية (متدرجة أو صلدة) وتاخد شكلها الشفاف منها فعليًا
    بفضل قناة الألفا، مش بمحاكاة لونية تقريبية"""
    from PIL import Image, ImageDraw
    w, h = max(int(w), 4), max(int(h), 4)
    scale = 3
    W, H = w * scale, h * scale
    R = max(radius * scale, 1)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if active:
        fill = (255, 255, 255, 235)
        border = (255, 255, 255, 255)
        bw = max(2 * scale, 2)
    elif enabled:
        fill = (255, 255, 255, 46)
        border = (255, 255, 255, 130)
        bw = max(1 * scale, 1)
    else:
        fill = (255, 255, 255, 18)
        border = (255, 255, 255, 60)
        bw = max(1 * scale, 1)

    draw.rounded_rectangle([bw, bw, W - bw - 1, H - bw - 1], radius=R, fill=fill)
    draw.rounded_rectangle([bw, bw, W - bw - 1, H - bw - 1], radius=R, outline=border, width=bw)

    if not active:
        # خط لمعان ناعم أعلى الكارت يدّي إحساس السطح الزجاجي
        highlight = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(highlight)
        hd.rounded_rectangle([bw * 2, bw * 2, W - bw * 2, H * 0.42], radius=max(R - bw, 1),
                              fill=(255, 255, 255, 26))
        img = Image.alpha_composite(img, highlight)

    return img.resize((w, h), Image.LANCZOS)


def make_luxury_nav_card(w, h, radius=8, active=False, enabled=True):
    """بترجع صورة PIL (RGBA) لكارت زرار بأسلوب فاخر: تدرج غامق (كحلي/أسود)
    رأسي + برواز ذهبي رفيع + شريط ذهبي صغير أسفل الكارت لما يكون نشط،
    عشان يدّي إحساس شعار/بادچ رسمي فخم بدل مربع تفاعلي عادي"""
    from PIL import Image, ImageDraw
    w, h = max(int(w), 4), max(int(h), 4)
    scale = 3
    W, H = w * scale, h * scale
    R = max(radius * scale, 1)

    if active:
        top, bottom = (34, 38, 52, 250), (16, 18, 26, 250)
    else:
        top, bottom = (24, 27, 38, enabled and 210 or 90), (10, 11, 16, enabled and 210 or 90)

    grad_col = Image.new("RGBA", (1, H))
    for y in range(H):
        t = y / max(H - 1, 1)
        px = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4))
        grad_col.putpixel((0, y), px)
    grad = grad_col.resize((W, H))

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([1, 1, W - 2, H - 2], radius=R, fill=255)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    draw = ImageDraw.Draw(img)
    gold = (212, 175, 55, 255) if enabled else (120, 112, 88, 200)
    bw = max((2 if active else 1) * scale, 1)
    draw.rounded_rectangle([bw / 2, bw / 2, W - bw / 2 - 1, H - bw / 2 - 1], radius=R,
                            outline=gold, width=bw)

    if active:
        bar_w = int(W * 0.4)
        bar_h = max(2 * scale, 3)
        bx0 = (W - bar_w) // 2
        by1 = H - bar_h - int(2 * scale)
        draw.rounded_rectangle([bx0, by1, bx0 + bar_w, by1 + bar_h], radius=bar_h // 2, fill=gold)

    return img.resize((w, h), Image.LANCZOS)


def draw_horizontal_gradient(canvas, width, height, color_left, color_right, steps=60):
    """بترسم تدرج لوني أفقي بسيط على Canvas (من color_left لـ color_right)
    بعدد "steps" من الأعمدة الرفيعة - مستخدمة في الشريط العلوي عشان يبقى
    شكله أفخم من لون صلب واحد بس"""
    canvas.delete("gradient")
    if width <= 0 or height <= 0:
        return
    step_w = max(width / steps, 1)
    for i in range(steps):
        t = i / max(steps - 1, 1)
        color = _lerp_color(color_left, color_right, t)
        x0 = i * step_w
        x1 = (i + 1) * step_w + 1  # +1 عشان محدش يفضل شق رفيع بين الأعمدة
        canvas.create_rectangle(x0, 0, x1, height, fill=color, outline=color, tags="gradient")
    canvas.tag_lower("gradient")


def rtl_fix(text):
    """بعض الودجتس زي CTkButton وCTkOptionMenu مش بتطبق اتجاه الكتابة العربي صح
    وبتقلب ترتيب الكلمات على الشاشة. الدالة دي بتعكس ترتيب الكلمات في الكود
    عشان تظهر بالترتيب الصحيح على الشاشة."""
    return " ".join(reversed(text.split(" ")))


# ---------------- شكل "غاطس" (Sunken) لصناديق إدخال البيانات - زي نوافذ ويندوز ----------------
INPUT_SUNKEN_BG = "#E9EBEF"       # خلفية أغمق شوية من الكارت الأبيض، تدي إحساس إن الصندوق محفور
INPUT_SUNKEN_BORDER = "#9AA0A8"   # حد رمادي غامق يوضّح حافة "الحفرة"
INPUT_LABEL_COLOR = "#2B2F36"     # لون عنوان الحقل (غامق وواضح زي عناوين نوافذ ويندوز)


def apply_sunken_style(widget):
    """يطبّق شكل الصندوق الغاطس على أي CTkEntry/RTLEntry/CTkTextbox/CTkComboBox"""
    try:
        widget.configure(fg_color=INPUT_SUNKEN_BG, border_width=2,
                          border_color=INPUT_SUNKEN_BORDER, corner_radius=4)
    except Exception:
        pass
    return widget


def _rounded_gradient_pil(width, height, top_color, bottom_color, radius=8,
                           border_color=None, border_width=2):
    """بترجع صورة PIL (RGBA) لزرار "كروم": تدرج رأسي ناعم جوه شكل بحواف
    دائرية وحد واضح حواليه، والزوايا برّه الاستدارة شفافة (alpha) تمامًا"""
    from PIL import Image, ImageDraw
    scale = 3  # سوبر-سامبلينج لتنعيم حواف الاستدارة
    w, h = max(width, 1) * scale, max(height, 1) * scale
    r = radius * scale
    top_rgb = tuple(int(top_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    bot_rgb = tuple(int(bottom_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        px = tuple(int(top_rgb[i] + (bot_rgb[i] - top_rgb[i]) * t) for i in range(3))
        grad.putpixel((0, y), px)
    grad = grad.resize((w, h))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    if border_color:
        bd = ImageDraw.Draw(img)
        bd.rounded_rectangle([0, 0, w - 1, h - 1], radius=r,
                              outline=border_color, width=border_width * scale)

    return img.resize((max(width, 1), max(height, 1)), Image.LANCZOS)


def rounded_top_gradient_pil(width, height, top_color, bottom_color, radius=10):
    """بترجع صورة PIL (RGBA) لشكل "تاب" ورقي حقيقي: تدرج رأسي ناعم، الزاويتين
    العلويتين مستديرتين والحواف السفلية مستقيمة تمامًا (من غير أي استدارة
    ولا حد) عشان التاب المفعّلة تندمج بصريًا مع محتواها تحتها بشكل طبيعي،
    من غير ما نحتاج نرسم أو نُخفي أي خط حد سفلي بعد كدا.
    الحيلة: بنرسم مستطيل بحواف مستديرة بالكامل في صورة أطول شوية من
    المطلوب (بمقدار نصف قطر الاستدارة)، وبعدين بنقص الجزء العلوي منها بس
    (بارتفاع الصورة المطلوب) - فالاستدارة السفلية بتقع برّه القص خالص"""
    from PIL import Image, ImageDraw
    scale = 3
    w = max(int(width), 1) * scale
    h = max(int(height), 1) * scale
    r = max(int(radius), 0) * scale
    tall_h = h + r

    top_rgb = tuple(int(top_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    bot_rgb = tuple(int(bottom_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    grad = Image.new("RGB", (1, tall_h))
    for y in range(tall_h):
        t = min(y / max(h - 1, 1), 1.0)
        px = tuple(int(top_rgb[i] + (bot_rgb[i] - top_rgb[i]) * t) for i in range(3))
        grad.putpixel((0, y), px)
    grad = grad.resize((w, tall_h))

    mask = Image.new("L", (w, tall_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, tall_h - 1], radius=r, fill=255)

    tall_img = Image.new("RGBA", (w, tall_h), (0, 0, 0, 0))
    tall_img.paste(grad, (0, 0), mask)
    img = tall_img.crop((0, 0, w, h))

    return img.resize((max(width, 1), max(height, 1)), Image.LANCZOS)


def make_shadowed_button(parent, text, command, width=150, height=38,
                          fg_color=None, text_color="#FFFFFF", font=None, corner_radius=8,
                          canvas_bg=None):
    """زرار "كروم" حقيقي: تدرج رأسي ناعم (فاتح فوق - غامق تحت) وحد واضح
    وظل خفيف تحته، بيلمع شوية أكتر لما الماوس يبقى فوقه - إحساس إنه بارز
    وقابل للضغط زي أزرار الأنظمة الكلاسيكية، مش لون مسطّح بس.

    ملحوظة تقنية: بنرسم الصورة والنص مع بعض على نفس الـ Canvas (مش
    CTkLabel شفاف فوق التانية) - لأن CTkLabel(fg_color="transparent")
    بيفشل في تحديد اللون الحقيقي اللي وراه لما يكون جوه CTkScrollableFrame
    (تحديدًا)، وبيظهر مربع أبيض صلب فوق النص بدل ما يبان شفاف"""
    import customtkinter as ctk
    import tkinter as tk
    fg_color = fg_color or SUCCESS
    canvas_bg = canvas_bg or CARD_BG
    wrapper = ctk.CTkFrame(parent, fg_color="transparent", width=width + 4, height=height + 4)
    wrapper.pack_propagate(False)

    shadow = ctk.CTkFrame(wrapper, fg_color="#9AA0A8", corner_radius=corner_radius,
                           width=width, height=height)
    shadow.place(x=4, y=4)

    border_color = darken_color(fg_color, 0.65)
    normal_pil = _rounded_gradient_pil(width, height, lighten_color(fg_color, 0.32),
                                        darken_color(fg_color, 0.85), corner_radius, border_color)
    hover_pil = _rounded_gradient_pil(width, height, lighten_color(fg_color, 0.48),
                                       darken_color(fg_color, 0.78), corner_radius, border_color)
    from PIL import ImageTk
    normal_img = ImageTk.PhotoImage(normal_pil)
    hover_img = ImageTk.PhotoImage(hover_pil)

    canvas = tk.Canvas(wrapper, width=width, height=height, highlightthickness=0,
                       bd=0, bg=canvas_bg, cursor="hand2")
    canvas.place(x=0, y=0)
    canvas._img_refs = (normal_img, hover_img)  # مرجع دائم يمنع الصور من الاختفاء
    canvas.create_image(0, 0, anchor="nw", image=normal_img, tags="bgimg")
    canvas.create_text(width / 2, height / 2 + 1, text=text, fill=text_color,
                        font=font or FONT_NORMAL, tags="label")

    def _on_enter(_e=None):
        canvas.itemconfigure("bgimg", image=hover_img)

    def _on_leave(_e=None):
        canvas.itemconfigure("bgimg", image=normal_img)

    def _on_click(_e=None):
        if command:
            command()

    canvas.bind("<Enter>", _on_enter)
    canvas.bind("<Leave>", _on_leave)
    canvas.bind("<Button-1>", _on_click)

    wrapper.chrome_canvas = canvas
    return wrapper


class GlassIconButton:
    """زرار أيقونة مضغوط بلون الثيم وتأثير "زجاجي لامع" (تدرج + خط لمعان
    فوقه) - مستخدم في صف أيقونات ملف المريض (بيانات/أسنان/حسابات...الخ).
    مختلف عن make_shadowed_button في إنه مصمم للأيقونات الصغيرة المربّعة
    (مش زرار نص عريض) وعنده حالة "نشط/غير نشط" بتتغير بنداء set_active()
    من غير ما نعيد بناء الزرار من الأول في كل مرة.

    ملحوظة تقنية: زي make_shadowed_button بالظبط - بنرسم الخلفية والنص مع
    بعض على نفس الـ Canvas عشان نتجنب مشكلة شفافية CTkLabel جوه
    CTkScrollableFrame/الفريمات المتداخلة"""

    def __init__(self, parent, text, command, width=48, height=34, accent_color=None,
                 canvas_bg=None, active=False, font=None, corner_radius=10):
        import tkinter as tk
        self.width = max(int(width), 4)
        self.height = max(int(height), 4)
        self.accent_color = accent_color or ACCENT_BORDER
        self.canvas_bg = canvas_bg or BG_MAIN
        self.corner_radius = corner_radius
        self.font = font or (FONT_FAMILY, 18)
        self.text = text
        self.command = command
        self.active = active
        self._hover = False

        self.wrapper = tk_frame = __import__("customtkinter").CTkFrame(
            parent, fg_color="transparent", width=self.width, height=self.height)
        tk_frame.pack_propagate(False)

        self.canvas = tk.Canvas(tk_frame, width=self.width, height=self.height,
                                 highlightthickness=0, bd=0, bg=self.canvas_bg, cursor="hand2")
        self.canvas.place(x=0, y=0)

        self._build_images()
        self._redraw()

        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)

    # ---- بناء صور PIL للحالتين (نشط/غير نشط) × (عادي/hover) ----
    def _build_images(self):
        from PIL import ImageTk
        self._img_active_normal = self._glass_pil(active=True, hover=False)
        self._img_active_hover = self._glass_pil(active=True, hover=True)
        self._img_inactive_normal = self._glass_pil(active=False, hover=False)
        self._img_inactive_hover = self._glass_pil(active=False, hover=True)
        # تحويلهم لـ PhotoImage ومسك مرجع دائم ليهم عشان ميتشالوش بالـ garbage collector
        self._tk_active_normal = ImageTk.PhotoImage(self._img_active_normal)
        self._tk_active_hover = ImageTk.PhotoImage(self._img_active_hover)
        self._tk_inactive_normal = ImageTk.PhotoImage(self._img_inactive_normal)
        self._tk_inactive_hover = ImageTk.PhotoImage(self._img_inactive_hover)

    def _glass_pil(self, active, hover):
        """صورة زرار بتدرج بلون الثيم + خط لمعان علوي شفاف (إحساس زجاجي
        لامع حقيقي، مش مجرد لون مسطّح) - وحدود رفيعة توضّح حافة الزرار"""
        from PIL import Image, ImageDraw
        w, h = self.width, self.height
        scale = 3
        W, H = w * scale, h * scale
        R = max(self.corner_radius * scale, 1)

        if active:
            top = lighten_color(self.accent_color, 0.46 if hover else 0.34)
            bottom = darken_color(self.accent_color, 0.92 if hover else 0.82)
            border = darken_color(self.accent_color, 0.55)
        else:
            top = lighten_color(self.accent_color, 0.88 if hover else 0.92)
            bottom = lighten_color(self.accent_color, 0.72 if hover else 0.80)
            border = lighten_color(self.accent_color, 0.45)

        top_rgb = tuple(int(top.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        bot_rgb = tuple(int(bottom.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        grad_col = Image.new("RGB", (1, H))
        for y in range(H):
            t = y / max(H - 1, 1)
            px = tuple(int(top_rgb[i] + (bot_rgb[i] - top_rgb[i]) * t) for i in range(3))
            grad_col.putpixel((0, y), px)
        grad = grad_col.resize((W, H))

        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=R, fill=255)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        img.paste(grad, (0, 0), mask)

        bw = max(1 * scale, 1)
        ImageDraw.Draw(img).rounded_rectangle(
            [bw / 2, bw / 2, W - bw / 2 - 1, H - bw / 2 - 1], radius=R, outline=border, width=bw)

        # خط لمعان زجاجي أعلى الزرار (نص علوي فاتح شبه شفاف) يدّي إحساس السطح اللامع
        shine = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shine_alpha = 60 if active else 130
        ImageDraw.Draw(shine).rounded_rectangle(
            [bw * 2, bw * 2, W - bw * 2, H * 0.46], radius=max(R - bw, 1),
            fill=(255, 255, 255, shine_alpha))
        img = Image.alpha_composite(img, shine)

        return img.resize((w, h), Image.LANCZOS)

    def _text_color(self):
        return "#FFFFFF" if self.active else self.accent_color

    def _redraw(self):
        self.canvas.delete("all")
        if self.active:
            img = self._tk_active_hover if self._hover else self._tk_active_normal
        else:
            img = self._tk_inactive_hover if self._hover else self._tk_inactive_normal
        self.canvas.create_image(0, 0, anchor="nw", image=img, tags="bgimg")
        self.canvas.create_text(self.width / 2, self.height / 2 + 1, text=self.text,
                                 fill=self._text_color(), font=self.font, tags="label")

    def _on_enter(self, _e=None):
        self._hover = True
        self._redraw()

    def _on_leave(self, _e=None):
        self._hover = False
        self._redraw()

    def _on_click(self, _e=None):
        if self.command:
            self.command()

    def set_active(self, active):
        self.active = active
        self._redraw()

    def pack(self, **kwargs):
        self.wrapper.pack(**kwargs)
        return self.wrapper


# لون ظل خفيف موحّد للكروت الرئيسية (شفافيته بسيطة عشان يبقى إحساس، مش عنصر ثقيل)
CARD_SHADOW_COLOR = "#D2D5DA"


def make_shadowed_card(parent, width=None, height=None, fg_color=None, corner_radius=None,
                        shadow_offset=4, **kwargs):
    """بيرجع (wrapper, card): كارت رئيسي بظل خفيف خلفه بإزاحة بسيطة، بيدي
    إحساس عمق (depth) بسيط للكروت الرئيسية بدل ما تبقى مسطّحة تمامًا.
    استخدمه بدل ما تعمل ctk.CTkFrame مباشرة للكروت الكبيرة (صفحة كاملة،
    قسم رئيسي...)؛ حط محتواك جوه "card" اللي بيرجعه، ومقاس "wrapper" هو
    اللي تحطه بنفسك في التخطيط (pack/grid)."""
    import customtkinter as ctk
    fg_color = fg_color or CARD_BG
    corner_radius = corner_radius if corner_radius is not None else RADIUS_LG

    wrapper = ctk.CTkFrame(parent, fg_color="transparent")
    if width is not None and height is not None:
        wrapper.configure(width=width + shadow_offset, height=height + shadow_offset)
        wrapper.pack_propagate(False)

    shadow = ctk.CTkFrame(wrapper, fg_color=CARD_SHADOW_COLOR, corner_radius=corner_radius,
                           width=width, height=height)
    shadow.place(x=shadow_offset, y=shadow_offset, relwidth=1 if width is None else None,
                 relheight=1 if height is None else None)

    card = ctk.CTkFrame(wrapper, fg_color=fg_color, corner_radius=corner_radius, **kwargs)
    card_kwargs_has_border = "border_width" in kwargs or "border_color" in kwargs
    if not card_kwargs_has_border:
        # حد رفيع بلون الثيم المميز (accent) - عشان الكارت يبان له هوية
        # واضحة تتغيّر مع كل ثيم، مش بس ظل خفيف
        card.configure(border_width=1, border_color=BORDER)
    if width is not None and height is not None:
        card.place(x=0, y=0, width=width, height=height)
    else:
        card.place(x=0, y=0, relwidth=1, relheight=1,
                   width=-shadow_offset, height=-shadow_offset)

    return wrapper, card


def show_toast(parent, text, kind="success", duration=1800):
    """رسالة تأكيد صغيرة (Toast) بتظهر فوق الصفحة وتختفي لوحدها - بدل ما
    تفضل رسالة "اتحفظ" ثابتة على الشاشة. استخدمها بعد أي عملية حفظ/حذف
    ناجحة. kind: "success" أو "error" أو "info" """
    import customtkinter as ctk

    colors = {"success": SUCCESS, "error": DANGER, "info": "#1E88E5"}
    bg = colors.get(kind, SUCCESS)

    toast = ctk.CTkFrame(parent, fg_color=bg, corner_radius=RADIUS_MD)
    icon = {"success": "✔", "error": "✕", "info": "ℹ"}.get(kind, "✔")
    ctk.CTkLabel(toast, text=f"{icon}  {text}", font=FONT_NORMAL,
                 text_color="#FFFFFF").pack(padx=20, pady=10)

    # في نص أعلى الصفحة اللي الرسالة هتظهر فوقها
    toast.place(relx=0.5, rely=0.04, anchor="n")

    def fade_out():
        try:
            toast.destroy()
        except Exception:
            pass

    toast.after(duration, fade_out)
    return toast


def strip_min_max_buttons(win):
    """بيشيل زرار التصغير (-) وزرار التكبير/الاستعادة من هيدر النافذة
    (شغالة على ويندوز بس)، ومسيبة زرار الإغلاق X زي ما هو"""
    import sys
    if sys.platform != "win32":
        return

    def _apply():
        try:
            import ctypes
            win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            GWL_STYLE = -16
            WS_MINIMIZEBOX = 0x00020000
            WS_MAXIMIZEBOX = 0x00010000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            style &= ~WS_MINIMIZEBOX
            style &= ~WS_MAXIMIZEBOX
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, SWP_FRAMECHANGED = 0x2, 0x1, 0x4, 0x20
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
        except Exception:
            pass

    win.after(30, _apply)


def confirm_dialog(parent, message, on_confirm, title="تأكيد",
                    confirm_text="✔ تأكيد", cancel_text="إلغاء", danger=False):
    """نافذة تأكيد صغيرة (تأكيد/إلغاء) قبل تنفيذ إجراء حساس زي الحفظ أو
    الحذف - بترجع النافذة نفسها لو حد محتاج يتحكم فيها"""
    import customtkinter as ctk

    win = ctk.CTkToplevel(parent)
    win.title(title)
    w, h = 340, 180
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.resizable(False, False)
    win.grab_set()
    strip_min_max_buttons(win)

    ctk.CTkLabel(win, text=message, font=FONT_DIALOG_LABEL, wraplength=280,
                 justify="center").pack(pady=(28, 18), padx=16)

    btn_row = ctk.CTkFrame(win, fg_color="transparent")
    btn_row.pack(pady=(0, 18))

    def _yes():
        win.destroy()
        on_confirm()

    ctk.CTkButton(btn_row, text=confirm_text, width=120, height=38,
                  fg_color=DANGER if danger else SUCCESS,
                  font=FONT_DIALOG_LABEL, command=_yes).pack(side="right", padx=6)
    ctk.CTkButton(btn_row, text=cancel_text, width=120, height=38, fg_color="transparent",
                  border_width=1, border_color=BORDER, text_color=TEXT_DARK,
                  font=FONT_DIALOG_LABEL, command=win.destroy).pack(side="right", padx=6)
    return win
