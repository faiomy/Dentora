# -*- coding: utf-8 -*-
"""
أيقونات مرسومة (Vector) لتابات الشريط العلوي - بدل الإيموجي، عشان تبان بنفس
الشكل والحجم على أي جهاز ويندوز مهما كان دعم الإيموجي عنده مختلف.

في البرنامج محورين مستقلين للتحكم في شكل الأيقونات:
    1) nav_button_style (classic/glass/luxury) - شكل خلفية الزرار في الشريط
       العلوي، وبيدي تأثير بسيط على رسمة الأيقونة نفسها (تنعيم/تسمين خطوط)
       عن طريق _apply_icon_style تحت.
    2) icon_pattern (outline/filled) - ده الأهم: شكل "الرسمة" نفسها لكل
       أيقونة:
       - outline: خط رفيع بلون واحد (بيتلوّن ديناميكيًا حسب حالة الزرار:
         أبيض على الشريط، لون العيادة لما يكون الزرار نشط، رمادي لو
         الصلاحية مش متاحة)
       - filled: أشكال مصمتة "ملوّنة" بلونين ثابتين مختلفين لكل أيقونة
         (زي العاملين: شخص أخضر وشخص أزرق) - الألوان دي ثابتة ومش
         بتتغيّر حسب حالة الزرار، عشان تدّي هوية بصرية ملوّنة واضحة
"""

import os
import math
from PIL import Image, ImageDraw, ImageFilter
import customtkinter as ctk

_CACHE = {}

# مجلد أيقونات الصور الجاهزة (PNG). لو الملف موجود هنا بنفس اسم الأيقونة
# (مثلاً assets/icons/calendar.png) بيتحمّل ويُستخدم بدل الرسم البرمجي.
# لو الملف مش موجود، البرنامج يرجع تلقائيًا لرسم الأيقونة بالكود (زي ما كان)
# عشان البرنامج ميوقفش أو يدّي error بسبب ملف ناقص.
_ASSETS_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "icons",
)

# نمط رسم الأيقونات الحالي (outline/filled) - بيتقرأ من إعدادات العيادة
# (icon_pattern) عند بدء التشغيل وبعد كل حفظ إعدادات، شوف set_icon_pattern
# تحت و main.py
_CURRENT_PATTERN = "outline"


def set_icon_pattern(pattern_id):
    """تُستدعى من main.py بعد قراءة/تغيير إعدادات العيادة (icon_pattern)"""
    global _CURRENT_PATTERN
    if pattern_id in ("outline", "filled", "glossy"):
        _CURRENT_PATTERN = pattern_id


def get_icon_pattern():
    return _CURRENT_PATTERN


def _canvas(size):
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def _rgba(color, alpha=255):
    """بتحوّل لون هيكس زي #1E88E5 لـ tuple (r,g,b,a) بشفافية alpha المطلوبة"""
    if isinstance(color, tuple):
        r, g, b = color[:3]
        return (r, g, b, alpha)
    c = str(color).lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    r = int(c[0:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)
    return (r, g, b, alpha)


def _load_png_icon(name, size, fill_ratio=0.94):
    """تحاول تحمّل assets/icons/{name}.png، وتقصّ الفراغ الشفاف اللي حوالين
    الرسمة نفسها (لو الصورة الأصلية فيها هوامش شفافة زيادة زي معظم أيقونات
    المواقع الجاهزة)، بعدين تكبّرها/تصغّرها عشان تملى نسبة fill_ratio من
    مساحة المربع size×size مع الحفاظ على أبعادها، وتحطها في نص المربع بالظبط.
    لو حصل أي خطأ في الحساب أو التحميل، بترجع الصورة الأصلية متمركزة في
    النص من غير أي قص - يعني في كل الأحوال الأيقونة هتفضل متمركزة صح.
    ترجع None لو الملف مش موجود أصلاً."""
    path = os.path.join(_ASSETS_ICONS_DIR, f"{name}.png")
    if not os.path.isfile(path):
        return None
    try:
        raw = Image.open(path).convert("RGBA")
    except Exception:
        return None

    canvas = _canvas(size)
    try:
        # قصّ أي هامش شفاف حوالين الرسمة عشان نحسب مساحتها الحقيقية بس
        bbox = raw.getbbox()
        content = raw.crop(bbox) if bbox else raw

        # نحسب نسبة التكبير اللي تخلّي أكبر ضلع في الرسمة يملى fill_ratio
        # من مساحة المربع، من غير ما نشوّه أبعادها الأصلية
        target = max(int(size * fill_ratio), 1)
        scale = min(target / content.width, target / content.height)
        new_w = max(int(round(content.width * scale)), 1)
        new_h = max(int(round(content.height * scale)), 1)
        content = content.resize((new_w, new_h), Image.LANCZOS)

        # نلزق الرسمة في نص المربع بالظبط (تمركز كامل، أفقيًا ورأسيًا)
        offset = ((size - new_w) // 2, (size - new_h) // 2)
        canvas.paste(content, offset, content)
        return canvas
    except Exception:
        # أي خطأ غير متوقع في الحساب - على الأقل نتمركز بالصورة الأصلية
        # كاملة في نص المربع بدل ما نفشل أو نعرض حاجة مقطوعة
        try:
            resized = raw.resize((size, size), Image.LANCZOS) if raw.size != (size, size) else raw
            canvas.paste(resized, (0, 0), resized)
            return canvas
        except Exception:
            return None


# =====================================================================
# نمط "outline" - خطوط رفيعة بسيطة بلون واحد (الشكل الأصلي/الافتراضي).
# ده النمط الوحيد اللي بيستخدم فعليًا الـ color اللي بييجي من حالة الزرار
# (نشط/غير نشط/معطّل) عشان ينسجم مع الشريط العلوي.
# =====================================================================

def _calendar_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    pad = size * 0.12
    top = size * 0.26
    d.rounded_rectangle([pad, top, size - pad, size - pad], radius=size * 0.08,
                         outline=color, width=2)
    d.line([pad, top + size * 0.14, size - pad, top + size * 0.14], fill=color, width=2)
    d.line([size * 0.3, top - size * 0.1, size * 0.3, top + size * 0.06], fill=color, width=3)
    d.line([size * 0.7, top - size * 0.1, size * 0.7, top + size * 0.06], fill=color, width=3)
    return img


def _person_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    cx = size / 2
    r = size * 0.15
    head_top = size * 0.1
    d.ellipse([cx - r, head_top, cx + r, head_top + 2 * r], outline=color, width=2)
    body_top = head_top + 2 * r + size * 0.06
    d.polygon([
        (cx - size * 0.2, body_top),
        (cx + size * 0.2, body_top),
        (cx + size * 0.34, size * 0.88),
        (cx - size * 0.34, size * 0.88),
    ], outline=color, width=2)
    return img


def _tag_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.polygon([
        (size * 0.08, size * 0.5),
        (size * 0.42, size * 0.14),
        (size * 0.88, size * 0.14),
        (size * 0.88, size * 0.5),
        (size * 0.42, size * 0.88),
    ], outline=color, width=2)
    d.ellipse([size * 0.6, size * 0.24, size * 0.74, size * 0.38], outline=color, width=2)
    return img


def _toolbox_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rectangle([size * 0.1, size * 0.4, size * 0.9, size * 0.84], outline=color, width=2)
    d.arc([size * 0.32, size * 0.12, size * 0.68, size * 0.52], start=180, end=360,
          fill=color, width=2)
    d.line([size * 0.1, size * 0.56, size * 0.9, size * 0.56], fill=color, width=2)
    return img


def _wallet_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([size * 0.08, size * 0.22, size * 0.92, size * 0.82],
                         radius=size * 0.06, outline=color, width=2)
    d.rectangle([size * 0.6, size * 0.42, size * 0.86, size * 0.64], outline=color, width=2)
    d.ellipse([size * 0.68, size * 0.49, size * 0.78, size * 0.57], fill=color)
    return img


def _factory_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rectangle([size * 0.12, size * 0.46, size * 0.88, size * 0.86], outline=color, width=2)
    d.polygon([(size * 0.12, size * 0.46), (size * 0.4, size * 0.26), (size * 0.4, size * 0.46)],
              outline=color, width=2)
    d.polygon([(size * 0.4, size * 0.46), (size * 0.65, size * 0.26), (size * 0.65, size * 0.46)],
              outline=color, width=2)
    d.rectangle([size * 0.68, size * 0.14, size * 0.78, size * 0.46], outline=color, width=2)
    return img


def _chat_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([size * 0.1, size * 0.16, size * 0.9, size * 0.66], radius=size * 0.12,
                         outline=color, width=2)
    d.polygon([(size * 0.28, size * 0.66), (size * 0.28, size * 0.86), (size * 0.48, size * 0.66)],
              fill=color)
    return img


def _gear_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    outer_r = size * 0.3
    inner_r = size * 0.14
    tooth_len = size * 0.1
    for i in range(8):
        angle = 2 * math.pi * i / 8
        x1 = cx + outer_r * math.cos(angle)
        y1 = cy + outer_r * math.sin(angle)
        x2 = cx + (outer_r + tooth_len) * math.cos(angle)
        y2 = cy + (outer_r + tooth_len) * math.sin(angle)
        d.line([x1, y1, x2, y2], fill=color, width=3)
    d.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r], outline=color, width=2)
    d.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], outline=color, width=2)
    return img


def _door_outline(size, color):
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rectangle([size * 0.26, size * 0.1, size * 0.74, size * 0.9], outline=color, width=2)
    d.ellipse([size * 0.58, size * 0.47, size * 0.65, size * 0.54], fill=color)
    d.line([size * 0.76, size * 0.5, size * 0.94, size * 0.5], fill=color, width=2)
    d.line([size * 0.86, size * 0.42, size * 0.94, size * 0.5], fill=color, width=2)
    d.line([size * 0.86, size * 0.58, size * 0.94, size * 0.5], fill=color, width=2)
    return img


def _team_outline(size, color):
    """أيقونة "العاملين" - شخصين متداخلين شوية عشان يبانوا فريق"""
    img = _canvas(size)
    d = ImageDraw.Draw(img)

    def _draw_one(cx, r, head_top, body_top, body_bottom, spread):
        d.ellipse([cx - r, head_top, cx + r, head_top + 2 * r], outline=color, width=2)
        d.polygon([
            (cx - spread, body_top),
            (cx + spread, body_top),
            (cx + spread * 1.7, body_bottom),
            (cx - spread * 1.7, body_bottom),
        ], outline=color, width=2)

    r = size * 0.13
    # الشخص اللي في الخلف (على الشمال شوية وأصغر)
    _draw_one(size * 0.36, r * 0.85, size * 0.14, size * 0.14 + 2 * r * 0.85 + size * 0.04,
              size * 0.82, size * 0.14)
    # الشخص اللي قدام (على اليمين وأكبر شوية)
    _draw_one(size * 0.62, r, size * 0.18, size * 0.18 + 2 * r + size * 0.05, size * 0.9, size * 0.17)
    return img


# =====================================================================
# نمط "filled" - أشكال مصمتة "ملوّنة" بلونين ثابتين مختلفين لكل أيقونة
# (زي العاملين: شخص أخضر وشخص أزرق). الألوان هنا ثابتة دايمًا ومش بتتلوّن
# ديناميكيًا حسب حالة الزرار - عشان الهوية اللونية تفضل واضحة ومميزة أيًا
# كان الزرار نشط ولا لأ
# =====================================================================

# لوحة الألوان الثابتة لكل أيقونة: (اللون الأساسي، اللون الثانوي)
_FILLED_PALETTE = {
    "calendar": ("#2E86DE", "#F39C12"),   # أزرق + برتقالي (يوم مميز)
    "person":   ("#2E86DE", "#16A085"),   # أزرق (الراس) + أخضر مائي (الجسم)
    "tag":      ("#F5B041", "#D35400"),   # دهبي + برتقالي غامق
    "toolbox":  ("#8D6E63", "#FFC107"),   # بني (الشنطة) + كهرماني (القفل/المقبض)
    "wallet":   ("#27AE60", "#F1C40F"),   # أخضر + دهبي (الكباس)
    "factory":  ("#5D6D7E", "#E67E22"),   # رمادي مزرق (المبنى) + برتقالي (الدخان)
    "chat":     ("#25D366", "#128C7E"),   # أخضر واتساب + أخضر غامق
    "gear":     ("#5D6D7E", "#E67E22"),   # رمادي مزرق (الترس) + برتقالي (المركز)
    "door":     ("#8D6E63", "#27AE60"),   # بني (الباب) + أخضر (سهم الخروج)
    "team":     ("#27AE60", "#2E86DE"),   # أخضر (الشخص قدام) + أزرق (الشخص وراه)
}


def _calendar_filled(size, color):
    primary, accent = _FILLED_PALETTE["calendar"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    pad = size * 0.12
    top = size * 0.26
    d.rounded_rectangle([pad, top, size - pad, size - pad], radius=size * 0.1,
                         fill=_rgba(primary, 90))
    d.rounded_rectangle([pad, top, size - pad, top + size * 0.16], radius=size * 0.06,
                         fill=_rgba(primary, 255))
    d.rounded_rectangle([size * 0.27, top - size * 0.12, size * 0.33, top + size * 0.04],
                         radius=size * 0.02, fill=_rgba(primary, 255))
    d.rounded_rectangle([size * 0.67, top - size * 0.12, size * 0.73, top + size * 0.04],
                         radius=size * 0.02, fill=_rgba(primary, 255))
    # يوم مميز بلون ثانوي مختلف
    d.rounded_rectangle([size * 0.38, size * 0.6, size * 0.62, size * 0.76],
                         radius=size * 0.04, fill=_rgba(accent, 255))
    return img


def _person_filled(size, color):
    primary, accent = _FILLED_PALETTE["person"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    cx = size / 2
    r = size * 0.16
    head_top = size * 0.08
    body_top = head_top + 2 * r + size * 0.04
    d.polygon([
        (cx - size * 0.24, body_top),
        (cx + size * 0.24, body_top),
        (cx + size * 0.38, size * 0.9),
        (cx - size * 0.38, size * 0.9),
    ], fill=_rgba(accent, 255))
    d.ellipse([cx - r, head_top, cx + r, head_top + 2 * r], fill=_rgba(primary, 255))
    return img


def _tag_filled(size, color):
    primary, accent = _FILLED_PALETTE["tag"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.polygon([
        (size * 0.08, size * 0.5),
        (size * 0.42, size * 0.14),
        (size * 0.88, size * 0.14),
        (size * 0.88, size * 0.5),
        (size * 0.42, size * 0.88),
    ], fill=_rgba(primary, 255))
    d.polygon([
        (size * 0.08, size * 0.5),
        (size * 0.42, size * 0.88),
        (size * 0.42, size * 0.7),
    ], fill=_rgba(accent, 255))
    # ثقب الشنطة (فتحة حقيقية شفافة جوه الشكل المصمت)
    d.ellipse([size * 0.6, size * 0.24, size * 0.74, size * 0.38], fill=(0, 0, 0, 0))
    return img


def _toolbox_filled(size, color):
    """شكل الشنطة - جسم مصمت بلون أساسي + مقبض/قفل بلون ثانوي مختلف"""
    primary, accent = _FILLED_PALETTE["toolbox"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([size * 0.1, size * 0.4, size * 0.9, size * 0.84], radius=size * 0.06,
                         fill=_rgba(primary, 255))
    d.rectangle([size * 0.1, size * 0.5, size * 0.9, size * 0.6], fill=_rgba(primary, 170))
    d.arc([size * 0.32, size * 0.1, size * 0.68, size * 0.54], start=180, end=360,
          fill=_rgba(accent, 255), width=int(max(size * 0.07, 3)))
    d.rounded_rectangle([size * 0.44, size * 0.58, size * 0.56, size * 0.7], radius=size * 0.02,
                         fill=_rgba(accent, 255))
    return img


def _wallet_filled(size, color):
    primary, accent = _FILLED_PALETTE["wallet"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([size * 0.08, size * 0.22, size * 0.92, size * 0.82],
                         radius=size * 0.08, fill=_rgba(primary, 130))
    d.rounded_rectangle([size * 0.08, size * 0.22, size * 0.92, size * 0.46],
                         radius=size * 0.08, fill=_rgba(primary, 255))
    d.rounded_rectangle([size * 0.6, size * 0.44, size * 0.88, size * 0.66],
                         radius=size * 0.05, fill=_rgba(accent, 255))
    d.ellipse([size * 0.68, size * 0.51, size * 0.78, size * 0.59], fill=(0, 0, 0, 0))
    return img


def _factory_filled(size, color):
    primary, accent = _FILLED_PALETTE["factory"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rectangle([size * 0.12, size * 0.46, size * 0.88, size * 0.86], fill=_rgba(primary, 255))
    d.polygon([(size * 0.12, size * 0.46), (size * 0.4, size * 0.24), (size * 0.4, size * 0.46)],
              fill=_rgba(primary, 190))
    d.polygon([(size * 0.4, size * 0.46), (size * 0.65, size * 0.24), (size * 0.65, size * 0.46)],
              fill=_rgba(primary, 255))
    d.rectangle([size * 0.68, size * 0.12, size * 0.78, size * 0.46], fill=_rgba(primary, 255))
    # شبابيك شفافة فعليًا (ثقوب) جوه جسم المصنع
    d.rectangle([size * 0.22, size * 0.58, size * 0.34, size * 0.7], fill=(0, 0, 0, 0))
    d.rectangle([size * 0.44, size * 0.58, size * 0.56, size * 0.7], fill=(0, 0, 0, 0))
    d.rectangle([size * 0.66, size * 0.58, size * 0.78, size * 0.7], fill=(0, 0, 0, 0))
    # دخان صغير بلون ثانوي فوق المدخنة
    r = size * 0.05
    d.ellipse([size * 0.73 - r, size * 0.06 - r, size * 0.73 + r, size * 0.06 + r],
              fill=_rgba(accent, 220))
    return img


def _chat_filled(size, color):
    primary, accent = _FILLED_PALETTE["chat"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([size * 0.1, size * 0.16, size * 0.9, size * 0.66], radius=size * 0.14,
                         fill=_rgba(primary, 255))
    d.polygon([(size * 0.28, size * 0.66), (size * 0.28, size * 0.86), (size * 0.48, size * 0.66)],
              fill=_rgba(primary, 255))
    # تلات نقط "بيكتب" بلون ثانوي غامق جوه الفقاعة
    cy = size * 0.41
    for cx in (size * 0.34, size * 0.5, size * 0.66):
        rr = size * 0.045
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=_rgba(accent, 255))
    return img


def _gear_filled(size, color):
    primary, accent = _FILLED_PALETTE["gear"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    outer_r = size * 0.3
    inner_r = size * 0.15
    tooth_r = size * 0.09
    for i in range(8):
        angle = 2 * math.pi * i / 8
        tx = cx + outer_r * math.cos(angle)
        ty = cy + outer_r * math.sin(angle)
        d.ellipse([tx - tooth_r, ty - tooth_r, tx + tooth_r, ty + tooth_r], fill=_rgba(primary, 255))
    d.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r], fill=_rgba(primary, 255))
    # مركز الترس بلون ثانوي مختلف بدل ما يكون ثقب شفاف
    d.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=_rgba(accent, 255))
    return img


def _door_filled(size, color):
    primary, accent = _FILLED_PALETTE["door"]
    img = _canvas(size)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([size * 0.26, size * 0.1, size * 0.74, size * 0.9], radius=size * 0.04,
                         fill=_rgba(primary, 255))
    d.rectangle([size * 0.26, size * 0.1, size * 0.34, size * 0.9], fill=_rgba(primary, 170))
    d.ellipse([size * 0.58, size * 0.47, size * 0.66, size * 0.55], fill=_rgba(accent, 255))
    # سهم الخروج بلون ثانوي مختلف (أخضر) عشان يبان واضح ومختلف عن الباب
    d.line([size * 0.78, size * 0.5, size * 0.96, size * 0.5], fill=_rgba(accent, 255),
           width=int(max(size * 0.05, 2)))
    d.polygon([(size * 0.96, size * 0.5), (size * 0.86, size * 0.4), (size * 0.86, size * 0.6)],
              fill=_rgba(accent, 255))
    return img


def _team_filled(size, color):
    """أيقونة العاملين - شخص أخضر قدام وشخص أزرق ورا، بالظبط زي المطلوب"""
    primary, accent = _FILLED_PALETTE["team"]  # primary=أخضر (قدام), accent=أزرق (ورا)
    img = _canvas(size)
    d = ImageDraw.Draw(img)

    def _draw_one(cx, r, head_top, body_top, body_bottom, spread, tone):
        d.polygon([
            (cx - spread, body_top),
            (cx + spread, body_top),
            (cx + spread * 1.7, body_bottom),
            (cx - spread * 1.7, body_bottom),
        ], fill=_rgba(tone, 220))
        d.ellipse([cx - r, head_top, cx + r, head_top + 2 * r], fill=_rgba(tone, 255))

    r = size * 0.14
    # الشخص اللي في الخلف - أزرق
    _draw_one(size * 0.35, r * 0.85, size * 0.13, size * 0.13 + 2 * r * 0.85 + size * 0.03,
              size * 0.82, size * 0.14, accent)
    # الشخص اللي قدام - أخضر
    _draw_one(size * 0.63, r, size * 0.16, size * 0.16 + 2 * r + size * 0.04, size * 0.9,
              size * 0.17, primary)
    return img


def _add_glossy_highlight(img, size):
    """بتضيف انعكاس ضوئي ناعم فوق الأيقونة (زي سطح لامع لمجسم حقيقي) -
    نفس الفكرة المستخدمة في أيقونات تصنيفات المصروفات (pages/expense_icons.py):
    بقعة إضاءة بيضاوية بيضاء شبه شفافة في الركن العلوي الشمال + لمعة صغيرة
    مركّزة فوقها، متقنّعين بقناة شفافية الأيقونة نفسها عشان الانعكاس يبان
    بس فوق أجزائها المصمتة"""
    highlight = _canvas(size)
    hd = ImageDraw.Draw(highlight)
    cx, cy = size * 0.35, size * 0.30
    rx, ry = size * 0.32, size * 0.20
    hd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(255, 255, 255, 165))
    highlight = highlight.filter(ImageFilter.GaussianBlur(size * 0.05))

    spark = _canvas(size)
    sd = ImageDraw.Draw(spark)
    scx, scy = size * 0.30, size * 0.24
    sr = size * 0.07
    sd.ellipse([scx - sr, scy - sr, scx + sr, scy + sr], fill=(255, 255, 255, 210))
    spark = spark.filter(ImageFilter.GaussianBlur(size * 0.02))
    highlight = Image.alpha_composite(highlight, spark)

    from PIL import ImageChops
    _, _, _, icon_alpha = img.split()
    _, _, _, highlight_alpha = highlight.split()
    clipped_alpha = ImageChops.multiply(highlight_alpha, icon_alpha)
    highlight.putalpha(clipped_alpha)
    return Image.alpha_composite(img, highlight)


# =====================================================================
# نمط "glossy" - نفس أشكال نمط "المعبأ الملوّن" بالظبط، بس بانعكاس ضوئي
# فوقها (_add_glossy_highlight) يوهم إنها مجسمات حقيقية لامعة مش رسمة
# مسطّحة، بنفس فكرة أيقونات تصنيفات المصروفات في صفحة المصروفات
# =====================================================================

def _calendar_glossy(size, color):
    return _add_glossy_highlight(_calendar_filled(size, color), size)


def _person_glossy(size, color):
    return _add_glossy_highlight(_person_filled(size, color), size)


def _tag_glossy(size, color):
    return _add_glossy_highlight(_tag_filled(size, color), size)


def _toolbox_glossy(size, color):
    return _add_glossy_highlight(_toolbox_filled(size, color), size)


def _wallet_glossy(size, color):
    return _add_glossy_highlight(_wallet_filled(size, color), size)


def _factory_glossy(size, color):
    return _add_glossy_highlight(_factory_filled(size, color), size)


def _chat_glossy(size, color):
    return _add_glossy_highlight(_chat_filled(size, color), size)


def _gear_glossy(size, color):
    return _add_glossy_highlight(_gear_filled(size, color), size)


def _door_glossy(size, color):
    return _add_glossy_highlight(_door_filled(size, color), size)


def _team_glossy(size, color):
    return _add_glossy_highlight(_team_filled(size, color), size)


_DRAWERS_BY_PATTERN = {
    "outline": {
        "calendar": _calendar_outline, "person": _person_outline, "tag": _tag_outline,
        "toolbox": _toolbox_outline, "wallet": _wallet_outline, "factory": _factory_outline,
        "chat": _chat_outline, "gear": _gear_outline, "door": _door_outline, "team": _team_outline,
    },
    "filled": {
        "calendar": _calendar_filled, "person": _person_filled, "tag": _tag_filled,
        "toolbox": _toolbox_filled, "wallet": _wallet_filled, "factory": _factory_filled,
        "chat": _chat_filled, "gear": _gear_filled, "door": _door_filled, "team": _team_filled,
    },
    "glossy": {
        "calendar": _calendar_glossy, "person": _person_glossy, "tag": _tag_glossy,
        "toolbox": _toolbox_glossy, "wallet": _wallet_glossy, "factory": _factory_glossy,
        "chat": _chat_glossy, "gear": _gear_glossy, "door": _door_glossy, "team": _team_glossy,
    },
}

# متبقاة للتوافق مع أي كود قديم كان بيستخدم _DRAWERS مباشرة (نمط outline)
_DRAWERS = _DRAWERS_BY_PATTERN["outline"]


def _get_drawer(name, pattern):
    drawers = _DRAWERS_BY_PATTERN.get(pattern, _DRAWERS_BY_PATTERN["outline"])
    return drawers.get(name)


# ---------------- هويات بصرية لشكل خلفية زرار الشريط (nav_button_style) ----------------
# بدل ما نرسم كل أيقونة من الصفر لكل تصميم خلفية (classic/glass/luxury)،
# بنولّد الرسمة الأساسية بتاعة النمط (outline/filled) المختار مرة واحدة،
# وبعدين بنحوّلها شكليًا بمعالجة خفيفة على قناة الشفافية (Alpha) بس عشان
# تنسجم مع خلفية الزرار الحالية:
# - classic: زي ما هي، من غير أي معالجة إضافية
# - glass: تسمين وتنعيم الخطوط (Dilate + Blur خفيف) عشان تبقى مدوّرة وناعمة
#          زي روح التصميم الزجاجي العصري
# - luxury: تسمين أقوى للخطوط (تبقى تقيلة/فخمة) + نقطة صغيرة مميزة أعلى
#           يمين كل أيقونة كـ "بصمة" بصرية فاخرة متكررة في كل الأيقونات
#           (بتتلوّن بلون العيادة حتى لو الأيقونة أصلًا "filled" ملوّنة)
def _apply_icon_style(img, style, color, size):
    if style == "glass":
        r, g, b, a = img.split()
        a = a.filter(ImageFilter.MaxFilter(3))
        a = a.filter(ImageFilter.GaussianBlur(0.4))
        return Image.merge("RGBA", (r, g, b, a))
    if style == "luxury":
        r, g, b, a = img.split()
        a = a.filter(ImageFilter.MaxFilter(5))
        out = Image.merge("RGBA", (r, g, b, a))
        d = ImageDraw.Draw(out)
        rdot = max(size * 0.05, 2)
        cx, cy = size * 0.86, size * 0.16
        d.ellipse([cx - rdot, cy - rdot, cx + rdot, cy + rdot], fill=color)
        return out
    return img


def get_icon_pil(name, size=28, color="#FFFFFF", style="classic", pattern=None):
    """زي get_icon بالظبط لكن بترجع صورة PIL خام (RGBA) مش CTkImage - مفيدة
    لما محتاجين نرسم الأيقونة يدويًا على Canvas (زي أزرار الشريط العلوي
    المرسومة فوق خلفية متدرجة) بدل ما نحطها كـ image لودجت CTk عادي.
    - color: بيتجاهله نمط "filled" (بيستخدم ألوانه الثابتة الخاصة بيه)،
      وبيُستخدم فعليًا بس في نمط "outline".
    - style: شكل خلفية زرار الشريط الحالي (classic/glass/luxury) - بيدّي
      تأثير تنعيم/تسمين بسيط بس، راجع _apply_icon_style فوق.
    - pattern: نمط رسمة الأيقونة نفسها (outline/filled). لو مش متبعت،
      بتُستخدم النمط الحالي المختار من إعدادات العيادة (get_icon_pattern) -
      إلا لو اتبعتت صراحة (مفيدة لمعرض اختيار الأنماط في صفحة الإعدادات
      عشان يعرض كل نمط بغض النظر عن المختار حاليًا)"""
    active_pattern = pattern or _CURRENT_PATTERN
    png_img = _load_png_icon(name, size)
    if png_img is not None:
        return _apply_icon_style(png_img, style, color, size)
    drawer = _get_drawer(name, active_pattern)
    if drawer is None:
        return _canvas(size)
    return _apply_icon_style(drawer(size, color), style, color, size)


def get_icon(name, size=28, color="#FFFFFF", style="classic", pattern=None):
    active_pattern = pattern or _CURRENT_PATTERN
    # الصور الجاهزة (PNG) بتتخزن في الكاش من غير اللون، لأنها بتتعرض بألوانها
    # الأصلية زي ما هي (بالظبط زي أيقونة الواتساب) - مفيش تلوين برمجي عليها.
    png_key = ("png", name, size, style)
    if png_key in _CACHE:
        return _CACHE[png_key]

    png_img = _load_png_icon(name, size)
    if png_img is not None:
        styled = _apply_icon_style(png_img, style, color, size)
        _CACHE[png_key] = ctk.CTkImage(light_image=styled, size=(size, size))
        return _CACHE[png_key]

    key = (active_pattern, name, size, color, style)
    if key not in _CACHE:
        drawer = _get_drawer(name, active_pattern)
        if drawer is None:
            img = _canvas(size)
        else:
            img = _apply_icon_style(drawer(size, color), style, color, size)
        _CACHE[key] = ctk.CTkImage(light_image=img, size=(size, size))
    return _CACHE[key]
