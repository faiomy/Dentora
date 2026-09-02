# -*- coding: utf-8 -*-
"""
سكريبت تشخيصي مستقل - شغّله من نفس مجلد main.py و database.py بالأمر:
    python debug_next_day_batch.py

بيوريك بالظبط ليه بث "تذكير مواعيد الغد" مش لاقي مواعيد، من غير ما نخمّن.
مبيغيّرش ولا حرف في قاعدة البيانات، بس بيقرأ ويعرض.
"""
import sqlite3
from datetime import datetime, timedelta

import database as db

now = datetime.now()
tomorrow = (now.date() + timedelta(days=1)).isoformat()

print("=" * 60)
print(f"دلوقتي: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"تاريخ 'بكرة' اللي بيدور عليه البرنامج: {tomorrow}")
print("=" * 60)

settings = db.get_settings()
print("\n--- إعدادات الأرشفة التلقائية الحالية ---")
print(f"  whatsapp_auto_archive_enabled     = {settings.get('whatsapp_auto_archive_enabled')}")
print(f"  whatsapp_next_day_batch_hour      = {settings.get('whatsapp_next_day_batch_hour')}")
print(f"  whatsapp_next_day_batch_minute    = {settings.get('whatsapp_next_day_batch_minute')}")
print(f"  whatsapp_auto_reminder_template_id = {settings.get('whatsapp_auto_reminder_template_id')}")

conn = sqlite3.connect(db.DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("\n--- كل المواعيد المسجّلة بتاريخ بكرة (بغض النظر عن أي شرط) ---")
rows = cur.execute("""
    SELECT appointments.id, appointments.appt_date, appointments.appt_time,
           appointments.status, appointments.next_day_reminder_sent,
           patients.full_name, patients.phone
    FROM appointments JOIN patients ON appointments.patient_id = patients.id
    WHERE appointments.appt_date = ?
""", (tomorrow,)).fetchall()

if not rows:
    print(f"  🔴 مفيش أي موعد في جدول appointments بتاريخ {tomorrow} خالص.")
    print("     يعني المشكلة إن الموعد أصلاً متسجّل بتاريخ مختلف، أو مش محفوظ.")
    print("     افتح صفحة المواعيد وتأكد من تاريخ اليوم اللي حاجزله الموعد فعليًا.")
else:
    for r in rows:
        print(f"  موعد #{r['id']}: {r['full_name']} - الساعة {r['appt_time']} "
              f"- الحالة: {r['status']} - تليفون: {r['phone'] or 'غير مسجل'} "
              f"- next_day_reminder_sent: {r['next_day_reminder_sent']}")
        problems = []
        if r["status"] == "cancelled":
            problems.append("❌ الموعد ملغي (status = cancelled) - عشان كده مش بيتحسب")
        if r["next_day_reminder_sent"] == 1:
            problems.append("❌ next_day_reminder_sent = 1 بالفعل - يعني الرسالة اتبعتت (أو اتعلّمت "
                             "كمُرسَلة) قبل كده، فمش هتتبعت تاني")
        wa_number = db.get_whatsapp_number(
            cur.execute("SELECT patient_id FROM appointments WHERE id = ?", (r["id"],)).fetchone()[0])
        if not wa_number:
            problems.append("❌ المريض مالوش رقم واتساب أو تليفون مسجل خالص")
        if problems:
            for p in problems:
                print(f"      {p}")
        else:
            print("      ✅ الموعد ده لازم يتبعتله البث - لو لسه مش واصل، جرب زرار "
                  "'حفظ إعدادات الأرشفة التلقائية' تاني عشان تتأكد إنها اتسجّلت")

conn.close()

print("\n--- نفس النتيجة اللي بيشوفها البرنامج فعليًا وقت التيك ---")
due = db.get_appointments_due_for_next_day_batch(
    batch_hour=int(settings.get("whatsapp_next_day_batch_hour") or 15),
    batch_minute=int(settings.get("whatsapp_next_day_batch_minute") or 0),
)
print(f"  عدد المواعيد اللي هتتبعتلها الرسالة دلوقتي: {len(due)}")
for a in due:
    print(f"    - {a['full_name']} ({a['appt_time']}) -> واتساب: {a.get('whatsapp_number')}")

print("\n" + "=" * 60)
print("خلصنا. ابعت النتيجة اللي طلعت هنا وأنا أقولك بالظبط المشكلة فين.")
