# -*- coding: utf-8 -*-
"""
رسمات أيقونات ملوّنة (PIL) لتبويبات تصنيفات المصروفات.

Canvas في Tkinter بيرسم النص بلون واحد بس (fill) حتى لو الحرف نفسه إيموجي
ملوّن أصلاً - يعني معتمدين على إيموجي النظام كان هيدّي شكل أحادي اللون
دايمًا (وأحيانًا شكل متقطّع/مشوّه لو الإيموجي مركّب من أكتر من حرف
يونيكود مش مدعوم من الخط). عشان كده كل أيقونة هنا بترسم يدويًا بأشكال PIL
بسيطة بألوان ثابتة، فبتطلع ملوّنة ونظيفة بنفس الشكل مهما كان النظام أو
الخط المتاح.

كل دالة بترجع PIL.Image بصيغة RGBA (خلفية شفافة) مربّعة الشكل، جاهزة
تتحط في GlassIconButton(icon_image=...).
"""

import math
from PIL import Image, ImageDraw, ImageChops, ImageFilter


def _new_canvas(size):
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def _add_glossy_highlight(img, size):
    """بتضيف انعكاس ضوئي ناعم فوق الأيقونة (زي سطح لامع لمجسم حقيقي)
    بدل الشكل المسطّح العادي - بترسم بقعة إضاءة بيضاوية بيضاء شبه شفافة
    في الركن العلوي الشمال، وبتقصّها بحيث تبان بس فوق أجزاء الأيقونة
    الفعلية (متقنّعة بقناة الشفافية بتاعتها) مش برّه شكلها في المربع
    الشفاف حواليها"""
    highlight = _new_canvas(size)
    hd = ImageDraw.Draw(highlight)
    cx, cy = size * 0.35, size * 0.30
    rx, ry = size * 0.32, size * 0.20
    hd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(255, 255, 255, 165))
    highlight = highlight.filter(ImageFilter.GaussianBlur(size * 0.05))

    # بقعة إضاءة تانية أصغر وأقوى (لمعة مركّزة) فوق البقعة الكبيرة
    spark = _new_canvas(size)
    sd = ImageDraw.Draw(spark)
    scx, scy = size * 0.30, size * 0.24
    sr = size * 0.07
    sd.ellipse([scx - sr, scy - sr, scx + sr, scy + sr], fill=(255, 255, 255, 210))
    spark = spark.filter(ImageFilter.GaussianBlur(size * 0.02))
    highlight = Image.alpha_composite(highlight, spark)

    _, _, _, icon_alpha = img.split()
    _, _, _, highlight_alpha = highlight.split()
    clipped_alpha = ImageChops.multiply(highlight_alpha, icon_alpha)
    highlight.putalpha(clipped_alpha)
    return Image.alpha_composite(img, highlight)


def draw_gear(size=200):
    """أيقونة ترس للصيانة - رمادي مزرق بحافة غامقة"""
    color, dark = "#6B8CAE", "#3E5670"
    img = _new_canvas(size)
    cx = cy = size / 2
    body_r = size * 0.29
    hole_r = size * 0.125
    n_teeth = 8
    tooth_w = size * 0.17
    tooth_h = size * 0.15
    outline_w = max(2, size // 55)

    for i in range(n_teeth):
        angle_deg = i * (360 / n_teeth)
        tooth = _new_canvas(size)
        td = ImageDraw.Draw(tooth)
        tx0 = cx - tooth_w / 2
        ty0 = cy - body_r - tooth_h * 0.62
        td.rounded_rectangle([tx0, ty0, tx0 + tooth_w, ty0 + tooth_h],
                              radius=tooth_w * 0.28, fill=color, outline=dark, width=outline_w)
        tooth = tooth.rotate(-angle_deg, resample=Image.BICUBIC, center=(cx, cy))
        img = Image.alpha_composite(img, tooth)

    draw = ImageDraw.Draw(img)
    draw.ellipse([cx - body_r, cy - body_r, cx + body_r, cy + body_r],
                 fill=color, outline=dark, width=outline_w)

    # ثقب الترس في النص (شفاف)
    hole_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(hole_mask).ellipse(
        [cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r], fill=255)
    r, g, b, a = img.split()
    a = ImageChops.subtract(a, hole_mask)
    img = Image.merge("RGBA", (r, g, b, a))
    draw = ImageDraw.Draw(img)
    draw.ellipse([cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r], outline=dark, width=outline_w)
    return img


def draw_wrench(size=200):
    """أيقونة مفتاح صيانة (سباك/ميكانيكي) للصيانة - فولاذي رمادي بحواف
    غامقة، بدل شكل الترس القديم"""
    metal, dark = "#98A9B5", "#4B5D68"
    img = _new_canvas(size)
    draw = ImageDraw.Draw(img)
    outline_w = max(2, size // 55)
    s = size
    cx = s / 2

    # المقبض (العمود الأساسي)
    handle_w = s * 0.16
    handle_top = s * 0.36
    handle_bottom = s * 0.86
    draw.rounded_rectangle(
        [cx - handle_w / 2, handle_top, cx + handle_w / 2, handle_bottom],
        radius=handle_w * 0.45, fill=metal, outline=dark, width=outline_w)

    # رأس المفتاح (حلقة بفتحة على شكل C) فوق المقبض
    head_cy = s * 0.22
    outer_r = s * 0.21
    inner_r = s * 0.12
    draw.ellipse([cx - outer_r, head_cy - outer_r, cx + outer_r, head_cy + outer_r],
                 fill=metal, outline=dark, width=outline_w)

    # ثقب الحلقة الداخلي (شفاف)
    hole_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(hole_mask).ellipse(
        [cx - inner_r, head_cy - inner_r, cx + inner_r, head_cy + inner_r], fill=255)
    r, g, b, a = img.split()
    a = ImageChops.subtract(a, hole_mask)
    img = Image.merge("RGBA", (r, g, b, a))

    # فتحة الفك (الجزء المقصوص من الحلقة) ناحية المقبض تحت الرأس مباشرة
    wedge_w = handle_w * 1.1
    wedge_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(wedge_mask).rectangle(
        [cx - wedge_w / 2, head_cy, cx + wedge_w / 2, head_cy + outer_r * 1.2], fill=255)
    r, g, b, a = img.split()
    a = ImageChops.subtract(a, wedge_mask)
    img = Image.merge("RGBA", (r, g, b, a))

    # حافة داخلية رفيعة لفم الفك عشان يوضّح سمك المعدن
    draw2 = ImageDraw.Draw(img)
    draw2.ellipse([cx - inner_r, head_cy - inner_r, cx + inner_r, head_cy + inner_r],
                  outline=dark, width=max(1, outline_w // 2))

    # ميل بسيط للمفتاح كله (شكل الأدوات المائلة المعتاد في الأيقونات)
    img = img.rotate(-38, resample=Image.BICUBIC, center=(cx, s / 2))
    return img


def draw_cart(size=200):
    """أيقونة عربة تسوق للخامات/المستلزمات - سماوي بعجل غامق"""
    basket, dark, wheel = "#2FB6C4", "#1B7A85", "#2E3A46"
    img = _new_canvas(size)
    draw = ImageDraw.Draw(img)
    outline_w = max(2, size // 55)

    # جسم السلة (شبه منحرف)
    top_w, bottom_w, h = size * 0.58, size * 0.40, size * 0.30
    top_y, cx = size * 0.28, size / 2
    x0, x1 = cx - top_w / 2, cx + top_w / 2
    x2, x3 = cx - bottom_w / 2, cx + bottom_w / 2
    y1 = top_y + h
    draw.polygon([(x0, top_y), (x1, top_y), (x3, y1), (x2, y1)],
                 fill=basket, outline=dark, width=outline_w)
    # خطوط السلة الأفقية
    for t in (0.34, 0.62):
        yy = top_y + h * t
        xa = x0 + (x2 - x0) * t
        xb = x1 + (x3 - x1) * t
        draw.line([(xa, yy), (xb, yy)], fill=dark, width=max(1, outline_w // 2))

    # ذراع الدفع
    draw.line([(x0 - size * 0.10, size * 0.16), (x0, top_y)], fill=dark, width=outline_w)
    draw.line([(x0 - size * 0.20, size * 0.16), (x0 - size * 0.10, size * 0.16)],
              fill=dark, width=outline_w)

    # العجلات
    wheel_r = size * 0.065
    for wx in (x2 + wheel_r * 0.4, x3 - wheel_r * 0.4):
        wy = y1 + wheel_r * 0.9
        draw.ellipse([wx - wheel_r, wy - wheel_r, wx + wheel_r, wy + wheel_r],
                      fill=wheel, outline=dark, width=max(1, outline_w // 2))
    return img


def draw_cash(size=200):
    """أيقونة رزمة فلوس للمرتبات - أخضر مع شريط بنفسجي حوالين الرزمة"""
    bill, bill_dark, band = "#3FAE64", "#1F7A3E", "#8B5E2C"
    img = _new_canvas(size)
    draw = ImageDraw.Draw(img)
    outline_w = max(2, size // 60)

    w, h = size * 0.56, size * 0.36
    cx, cy = size / 2, size / 2

    # 3 ورقات مكدّسة بإزاحة بسيطة توحي بسمك الرزمة
    for i, offset in enumerate((10, 5, 0)):
        off = size * 0.018 * (2 - i)
        x0, y0 = cx - w / 2 - off, cy - h / 2 + off
        x1, y1 = cx + w / 2 - off, cy + h / 2 + off
        draw.rounded_rectangle([x0, y0, x1, y1], radius=size * 0.03,
                                fill=bill, outline=bill_dark, width=outline_w)

    # الورقة العلوية بتفاصيلها (دائرة العملة في النص + خطوط جانبية)
    x0, y0 = cx - w / 2, cy - h / 2
    x1, y1 = cx + w / 2, cy + h / 2
    draw.rounded_rectangle([x0, y0, x1, y1], radius=size * 0.03,
                            fill=bill, outline=bill_dark, width=outline_w)
    coin_r = h * 0.30
    draw.ellipse([cx - coin_r, cy - coin_r, cx + coin_r, cy + coin_r],
                 outline=bill_dark, width=outline_w)

    # شريط الربط المائل حوالين الرزمة
    band_w = size * 0.12
    draw.polygon([
        (cx - band_w / 2, y0 - size * 0.02), (cx + band_w / 2, y0 - size * 0.02),
        (cx + band_w / 2, y1 + size * 0.02), (cx - band_w / 2, y1 + size * 0.02),
    ], fill=band)
    return img


def draw_bolt(size=200):
    """أيقونة صاعقة للكهرباء والمرافق - أصفر/برتقالي"""
    fill, dark = "#FFC93C", "#D98A12"
    img = _new_canvas(size)
    draw = ImageDraw.Draw(img)
    outline_w = max(2, size // 60)
    s = size
    pts = [
        (s * 0.56, s * 0.10), (s * 0.30, s * 0.56), (s * 0.46, s * 0.56),
        (s * 0.40, s * 0.90), (s * 0.72, s * 0.42), (s * 0.54, s * 0.42),
    ]
    draw.polygon(pts, fill=fill, outline=dark, width=outline_w)
    return img


def draw_building(size=200):
    """أيقونة مبنى للإيجار - رمادي دافئ بشبابيك سماوية"""
    facade, dark, window = "#B08B6B", "#7A5C42", "#BEE3F0"
    img = _new_canvas(size)
    draw = ImageDraw.Draw(img)
    outline_w = max(2, size // 60)

    w, h = size * 0.52, size * 0.62
    x0, y0 = size / 2 - w / 2, size * 0.22
    x1, y1 = size / 2 + w / 2, y0 + h
    draw.rectangle([x0, y0, x1, y1], fill=facade, outline=dark, width=outline_w)

    # باب
    door_w, door_h = w * 0.26, h * 0.22
    dx0 = size / 2 - door_w / 2
    dy0 = y1 - door_h
    draw.rectangle([dx0, dy0, dx0 + door_w, y1], fill=dark)

    # شبابيك 3x2
    rows, cols = 3, 2
    pad_x, pad_y = w * 0.14, h * 0.10
    cell_w = (w - pad_x * 2) / cols
    cell_h = (h * 0.62 - pad_y * (rows - 1)) / rows
    win_w, win_h = cell_w * 0.62, cell_h * 0.62
    start_y = y0 + h * 0.10
    for r in range(rows):
        for c in range(cols):
            wx0 = x0 + pad_x + c * cell_w + (cell_w - win_w) / 2
            wy0 = start_y + r * (cell_h + pad_y)
            draw.rectangle([wx0, wy0, wx0 + win_w, wy0 + win_h], fill=window, outline=dark,
                            width=max(1, outline_w // 2))
    return img


def draw_box(size=200):
    """أيقونة صندوق كرتوني لتصنيف \"أخرى\" - بني/كرميل بشريط لاصق غامق"""
    top_face, left_face, right_face, dark = "#D9A55C", "#B9803A", "#C99049", "#8A5F26"
    img = _new_canvas(size)
    draw = ImageDraw.Draw(img)
    outline_w = max(2, size // 60)
    cx, cy = size / 2, size / 2
    hw, hh = size * 0.30, size * 0.16  # نصف عرض/ارتفاع المعين العلوي
    body_h = size * 0.30

    top_pts = [(cx, cy - hh - body_h * 0.35), (cx + hw, cy - body_h * 0.35),
               (cx, cy + hh - body_h * 0.35), (cx - hw, cy - body_h * 0.35)]
    left_pts = [top_pts[3], top_pts[2], (top_pts[2][0], top_pts[2][1] + body_h),
                (top_pts[3][0], top_pts[3][1] + body_h)]
    right_pts = [top_pts[2], top_pts[1], (top_pts[1][0], top_pts[1][1] + body_h),
                 (top_pts[2][0], top_pts[2][1] + body_h)]

    draw.polygon(left_pts, fill=left_face, outline=dark, width=outline_w)
    draw.polygon(right_pts, fill=right_face, outline=dark, width=outline_w)
    draw.polygon(top_pts, fill=top_face, outline=dark, width=outline_w)

    # شريط لاصق عمودي فوق الصندوق
    tape_w = size * 0.06
    draw.line([(cx, top_pts[0][1] + hh * 0.15), (cx, top_pts[2][1] + body_h)],
              fill=dark, width=int(tape_w))
    return img


def draw_tissue(size=200):
    """أيقونة رول مناديل/مستلزمات استهلاكية - أزرق فاتح وأبيض"""
    tube, tube_dark, paper = "#8FD3E8", "#4FA6C2", "#F4FBFD"
    img = _new_canvas(size)
    draw = ImageDraw.Draw(img)
    outline_w = max(2, size // 60)

    w, h = size * 0.40, size * 0.52
    x0, y0 = size / 2 - w / 2, size * 0.30
    x1, y1 = size / 2 + w / 2, y0 + h
    draw.rounded_rectangle([x0, y0, x1, y1], radius=w * 0.5, fill=paper, outline=tube_dark,
                            width=outline_w)

    # الفتحة العلوية (الأنبوبة الداخلية)
    top_ry = h * 0.10
    draw.ellipse([x0, y0 - top_ry, x1, y0 + top_ry], fill=tube, outline=tube_dark, width=outline_w)
    inner_r = w * 0.16
    draw.ellipse([size / 2 - inner_r, y0 - top_ry * 0.6, size / 2 + inner_r, y0 + top_ry * 0.6],
                 fill=tube_dark)

    # ورقة منديل بارزة من فوق
    flap_w = w * 0.5
    fx0 = size / 2 - flap_w / 2
    draw.line([(fx0, y0 - top_ry * 1.4), (fx0 + flap_w * 0.35, y0 - top_ry * 3.0)],
              fill=tube_dark, width=max(1, outline_w // 2))
    draw.line([(fx0 + flap_w, y0 - top_ry * 1.4), (fx0 + flap_w * 0.65, y0 - top_ry * 3.0)],
              fill=tube_dark, width=max(1, outline_w // 2))
    return img


# تجميعة الرسّامين متاحة بالاسم عشان صفحة المصروفات تستخدمها بسهولة حسب
# اسم التصنيف
CATEGORY_ICON_DRAWERS = {
    "مستهلكات": draw_tissue,
    "خامات": draw_cart,
    "مرتبات": draw_cash,
    "كهرباء ومرافق": draw_bolt,
    "صيانة": draw_wrench,
    "إيجار": draw_building,
    "أخرى": draw_box,
}


def get_category_icon(category_name, size=200):
    drawer = CATEGORY_ICON_DRAWERS.get(category_name, draw_box)
    img = drawer(size)
    return _add_glossy_highlight(img, size)
