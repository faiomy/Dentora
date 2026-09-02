# -*- coding: utf-8 -*-
"""
بيولّد ملف أيقونة (assets/app_icon.ico) من لوجو العيادة المحفوظ في قاعدة
البيانات، عشان نستخدمه كأيقونة لملف الـ exe النهائي.

شغّليه قبل ما تعملي بناء الـ exe (build_exe.bat بيعمل ده تلقائي بالفعل):
    python make_icon.py
"""

import os
import sqlite3
from PIL import Image, ImageDraw

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "clinic_data.db")
ICON_OUTPUT = os.path.join(APP_ROOT, "assets", "app_icon.ico")
ICON_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def get_logo_path():
    """بيقرأ مسار اللوجو المحفوظ في الإعدادات، لو قاعدة البيانات موجودة أصلاً"""
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT logo_path FROM clinic_settings WHERE id = 1").fetchone()
        conn.close()
        if row and row[0] and os.path.exists(row[0]):
            return row[0]
    except Exception:
        pass
    return None


def make_default_icon():
    """لو مفيش لوجو متسجل، نرسم أيقونة سن بسيطة كبديل افتراضي"""
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    primary = (30, 136, 229, 255)  # أزرق البرنامج الافتراضي
    d.ellipse([8, 8, size - 8, size - 8], fill=primary)
    cx = size // 2
    d.ellipse([cx - 55, 60, cx + 55, 150], fill="white")
    d.polygon([(cx - 45, 130), (cx, 210), (cx + 45, 130)], fill="white")
    return img


def main():
    os.makedirs(os.path.join(APP_ROOT, "assets"), exist_ok=True)

    logo_path = get_logo_path()
    if logo_path:
        print(f"لاقيت لوجو العيادة: {logo_path}")
        img = Image.open(logo_path).convert("RGBA")
        # نخلي الصورة مربعة (نضيف هامش شفاف) عشان الأيقونة متتشوهش
        w, h = img.size
        side = max(w, h)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(img, ((side - w) // 2, (side - h) // 2))
        img = square
    else:
        print("مفيش لوجو متسجل في قاعدة البيانات - هستخدم أيقونة افتراضية")
        img = make_default_icon()

    img.save(ICON_OUTPUT, format="ICO", sizes=ICON_SIZES)
    print(f"تم إنشاء الأيقونة بنجاح: {ICON_OUTPUT}")


if __name__ == "__main__":
    main()
