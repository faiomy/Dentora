# -*- coding: utf-8 -*-
"""
سكريبت لمرة واحدة: بيصفّر علامة next_day_reminder_sent لكل مواعيد الغد،
عشان تقدر تعيد اختبار خاصية "تأكيد مواعيد اليوم التالي" من غير ما تستنى
يوم كامل أو تعمل مواعيد تجريبية جديدة.

طريقة الاستخدام:
1. حط الملف ده في نفس مجلد main.py و database.py
2. افتح Command Prompt في نفس المجلد
3. نفّذ: python reset_next_day_flag.py
"""
import sqlite3
import os
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clinic_data.db")

tomorrow = (date.today() + timedelta(days=1)).isoformat()

conn = sqlite3.connect(DB_PATH)
cur = conn.execute(
    "SELECT id, appt_time FROM appointments WHERE appt_date = ?", (tomorrow,))
rows = cur.fetchall()

if not rows:
    print(f"مفيش مواعيد مسجَّلة بتاريخ الغد ({tomorrow}).")
else:
    conn.execute(
        "UPDATE appointments SET next_day_reminder_sent = 0 WHERE appt_date = ?", (tomorrow,))
    conn.commit()
    print(f"تم تصفير العلامة لـ {len(rows)} موعد بتاريخ الغد ({tomorrow}):")
    for r in rows:
        print(f"  - موعد رقم {r[0]} الساعة {r[1]}")
    print("\nهيتم اعتبارهم غير مُرسَلين تاني، وهيتبعتلهم البث في المعاد المحدد في إعدادات واتساب.")

conn.close()
