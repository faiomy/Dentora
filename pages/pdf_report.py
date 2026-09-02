# -*- coding: utf-8 -*-
"""
توليد كشف حساب PDF للمريض (بنود العلاج + التكلفة + المدفوع) خلال فترة زمنية محددة،
مع لوجو العيادة وتوقيع الطبيب في الآخر.

ملحوظة: الجزء ده بيستخدم مكتبات (fpdf2, arabic_reshaper, python-bidi) عشان يرسم
العربي صح في ملف PDF. لازم تتثبت زي باقي المكتبات:
    pip install fpdf2 arabic-reshaper python-bidi
"""

import os
from datetime import datetime

import database as db

# خط عربي من ويندوز نفسه (موجود على كل أجهزة ويندوز) بيدعم رسم الحروف العربية في الـ PDF
WINDOWS_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
]

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "assets", "reports")


def _load_pdf_libs():
    """
    بنستورد مكتبات الـ PDF هنا جوه الدالة بس (مش فوق في أول الملف) عشان لو المستخدم
    لسه ما ثبتش pip install fpdf2 arabic-reshaper python-bidi، البرنامج كله يفضل
    شغال عادي وميقعش، وبس وقت ما يحاول يطبع كشف حساب هيظهرله رسالة واضحة.
    """
    from fpdf import FPDF
    import arabic_reshaper
    from bidi.algorithm import get_display
    return FPDF, arabic_reshaper, get_display


def _find_font():
    for path in WINDOWS_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def generate_account_statement(patient_id, start_date, end_date):
    """بيرجع مسار ملف الـ PDF بعد ما يتولد. كل الأرقام هنا بتتحسب من نفس
    جدول "سجل المعالجات" الموحّد في تاب الحسابات وبس (مفيش أي مصدر تاني
    زي حركات "دفعة" عامة مش مرتبطة بمعالجة معيّنة) - عشان الكشف المطبوع
    يطابق اللي شايفاه بالظبط في الجدول نفسه، خانة "المدفوع" بالذات."""
    FPDF, arabic_reshaper, get_display = _load_pdf_libs()

    def _rtl(text):
        """يجهز أي نص عربي عشان يترسم صح (متصل ومن اليمين لليسار) جوه الـ PDF"""
        if text is None:
            return ""
        text = str(text)
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text

    patient = db.get_patient(patient_id)
    settings = db.get_settings()
    records = db.get_treatment_records_range(patient_id, start_date, end_date)

    gross_charges = sum(r["price"] for r in records)
    total_discount = sum(float(r.get("discount_amount") or 0) for r in records)
    # المستحق الفعلي بعد الخصم - نفس الحساب بالظبط اللي في db.get_patient_balance
    # وكارت "ملخص الحسابات"، عشان رقم "المتبقي" في الكشف المطبوع يطابق
    # صفحة الحسابات دايمًا
    total_charges = gross_charges - total_discount
    # المدفوع بيتحسب من عمود "المدفوع" في جدول سجل المعالجات نفسه لكل بند
    # (مش من أي حركة "دفعة" عامة منفصلة) - عشان يطابق بالظبط اللي شايفاه
    # في الجدول، بما فيه صف "الإجمالي" بتاعه
    total_paid = sum(float(r.get("paid_amount") or 0) for r in records)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    font_path = _find_font()
    font_name = "Arial"
    if font_path:
        pdf.add_font(font_name, "", font_path)
        pdf.set_font(font_name, size=12)
    else:
        # لو الخط مش موجود (مش هيحصل على ويندوز عادي)، استخدم خط افتراضي كحل أخير
        pdf.set_font("Helvetica", size=12)
        font_name = "Helvetica"

    page_right = 210 - 15  # حافة الصفحة اليمنى بعد الهامش (A4 عرضها 210مم)
    page_width = page_right - 15

    # اللوجو والعنوان
    if settings.get("logo_path") and os.path.exists(settings["logo_path"]):
        try:
            pdf.image(settings["logo_path"], x=15, y=12, w=22)
        except Exception:
            pass

    pdf.set_font(font_name, size=18)
    pdf.set_xy(15, 14)
    pdf.cell(page_width, 10, txt=_rtl(settings["clinic_name"]), align="C")

    pdf.set_font(font_name, size=11)
    pdf.set_xy(15, 26)
    pdf.cell(page_width, 6, txt=_rtl("كشف حساب مريض"), align="C")
    pdf.ln(16)

    # بيانات المريض والفترة
    pdf.set_font(font_name, size=11)
    info_lines = [
        f"اسم المريض: {patient['full_name']}",
        f"رقم الملف: {patient_id:06d}",
        f"التليفون: {patient['phone'] or '-'}",
        f"الفترة من {start_date} إلى {end_date}",
        f"تاريخ الطباعة: {datetime.now().strftime('%Y-%m-%d')}",
    ]
    for line in info_lines:
        pdf.set_x(15)
        pdf.cell(page_width, 7, txt=_rtl(line), align="R")
        pdf.ln(7)
    pdf.ln(4)

    # جدول بنود العلاج - التاريخ أول خانة (أقصى اليمين)، وآخر 3 خانات
    # (أقصى الشمال) هي القيمة والخصم والمدفوع، على الترتيب
    col_widths = {"date": 25, "tooth": 18, "item": 55, "doctor": 30,
                  "price": 20, "discount": 17, "paid": 15}
    row_height = 8
    order = ["date", "tooth", "item", "doctor", "price", "discount", "paid"]

    def draw_row_rtl(y, cells, header=False, fill=False):
        pdf.set_font(font_name, size=10)
        if fill:
            pdf.set_fill_color(230, 236, 245)

        cur_x = page_right
        for key in order:
            w = col_widths[key]
            cur_x -= w
            pdf.set_xy(cur_x, y)
            pdf.cell(w, row_height, txt=_rtl(cells.get(key, "")), border=1, align="C", fill=fill)

    header_cells = {"date": "التاريخ", "tooth": "السن", "item": "بند العلاج",
                     "doctor": "الطبيب", "price": "القيمة", "discount": "الخصم",
                     "paid": "المدفوع"}
    y = pdf.get_y()
    draw_row_rtl(y, header_cells, header=True, fill=True)
    y += row_height

    if not records:
        pdf.set_xy(15, y)
        pdf.cell(page_width, 8, txt=_rtl("لا توجد بنود علاج في هذه الفترة"), align="C")
        y += 10
    else:
        for r in records:
            if y > 265:  # صفحة جديدة لو قربنا من الآخر
                pdf.add_page()
                y = 20
                draw_row_rtl(y, header_cells, header=True, fill=True)
                y += row_height
            cells = {
                "date": r["treatment_date"],
                "tooth": str(r["tooth_number"] or "-"),
                "item": r["treatment_label"],
                "doctor": r["doctor_name"] or "-",
                "price": f"{r['price']:g}",
                "discount": f"{(r.get('discount_amount') or 0):g}",
                "paid": f"{(r.get('paid_amount') or 0):g}",
            }
            draw_row_rtl(y, cells)
            y += row_height

    y += 6
    pdf.set_xy(15, y)
    pdf.set_font(font_name, size=12)
    pdf.cell(page_width, 8, txt=_rtl(f"إجمالي بنود العلاج (قبل الخصم): {gross_charges:g} جنيه"), align="R")
    y += 8
    if total_discount:
        pdf.set_xy(15, y)
        pdf.cell(page_width, 8, txt=_rtl(f"إجمالي الخصومات: {total_discount:g} جنيه"), align="R")
        y += 8
    pdf.set_xy(15, y)
    pdf.cell(page_width, 8, txt=_rtl(f"إجمالي المعالجات (بعد الخصم): {total_charges:g} جنيه"), align="R")
    y += 8
    pdf.set_xy(15, y)
    pdf.cell(page_width, 8, txt=_rtl(f"إجمالي المدفوع خلال الفترة: {total_paid:g} جنيه"), align="R")
    y += 8
    pdf.set_xy(15, y)
    pdf.set_font(font_name, size=13)
    remaining = total_charges - total_paid
    pdf.cell(page_width, 8, txt=_rtl(f"المتبقي المستحق: {remaining:g} جنيه"), align="R")
    y += 20

    # ---- توقيعان بدل توقيع الطبيب: "الحسابات" على اليمين، و"يعتمد" مع
    # مكان توقيع المدير على الشمال ----
    sig_y = max(y, 245)
    half_width = page_width / 2
    pdf.set_font(font_name, size=11)

    # يمين: توقيع الحسابات
    pdf.set_xy(15 + half_width, sig_y)
    pdf.cell(half_width, 8, txt=_rtl("الحسابات: ......................."), align="C")

    # شمال: يعتمد + توقيع المدير تحتها
    pdf.set_xy(15, sig_y)
    pdf.set_font(font_name, size=12)
    pdf.cell(half_width, 8, txt=_rtl("يعتمد"), align="C")
    pdf.set_xy(15, sig_y + 10)
    pdf.set_font(font_name, size=11)
    pdf.cell(half_width, 8, txt=_rtl("توقيع المدير: ......................."), align="C")

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"statement_{patient_id}_{start_date}_{end_date}.pdf".replace(":", "-")
    output_path = os.path.join(REPORTS_DIR, filename)
    pdf.output(output_path)
    return output_path
