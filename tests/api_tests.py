# -*- coding: utf-8 -*-
"""
مجموعة اختبارات شاملة لطبقة الـ API (بدون خادم شبكة حقيقي - TestClient).

تشغيل:  python tests/api_tests.py
نتيجة نجاح: آخر سطر "ALL_OK"

يغطي:
  * المصادقة: بدون مفتاح / مفتاح خاطئ / مفتاح موقوف / مفتاح صالح.
  * النطاقات: read/write/delete مستقلة + أن الـ delete مش متضمن في الـ write.
  * CRUD كامل للمرضى والمواعيد (بيشمل الإلغاء) والزيارات والحسابات.
  * خريطة الأسنان (قراءة + تعديل سن + معالجة بتحصيل مالي).
  * حالات الخطأ: 404 للموارد غير الموجودة + 422 validation بأجسام غير صحيحة.
  * التشفير: سجل الأحداث + pagination + الحقول غير القابلة للتسريب.
"""

import sys

from tests.helpers import ROOT, fresh_db_path
fresh_db_path()

import database as db
db.init_db()

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

FAILURES = []


def check(name, cond, extra=""):
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" ({extra})" if extra else ""))
    if not cond:
        FAILURES.append(name)


def main():
    # ---------- الصحة بدون مصادقة ----------
    r = client.get("/api/v1/health")
    check("health بدون مصادقة", r.status_code == 200 and r.json()["data"]["status"] == "ok",
          r.text[:200])

    # ---------- مصادقة ----------
    r = client.get("/api/v1/patients")
    check("مفقود المفتاح -> 401", r.status_code == 401)
    check("كود missing_api_key", r.json()["error"]["code"] == "missing_api_key")

    r = client.get("/api/v1/patients", headers={"Authorization": "Bearer wrong"})
    check("مفتاح خاطئ -> 401", r.status_code == 401)
    check("كود invalid_api_key", r.json()["error"]["code"] == "invalid_api_key")

    full = db.generate_api_key("full",
        ["patients.read", "patients.write", "patients.delete",
         "appointments.read", "appointments.write", "appointments.delete",
         "visits.read", "visits.write", "visits.delete",
         "financials.read", "financials.write", "financials.delete",
         "odontogram.read", "odontogram.write", "events.read"])
    H = {"Authorization": f"Bearer {full['raw_key']}"}

    r = client.get("/api/v1/patients", headers=H)
    check("مفتاح صالح -> 200", r.status_code == 200 and "data" in r.json())
    check("تفويض data+meta", "meta" in r.json())

    # مفتاح ثم تعطيله
    db.update_api_key_fields(full["id"], enabled=False)
    r = client.get("/api/v1/patients", headers=H)
    check("مفتاح موقوف -> 403", r.status_code == 403)
    check("كود api_key_disabled", r.json()["error"]["code"] == "api_key_disabled",
          r.text[:200])
    db.update_api_key_fields(full["id"], enabled=True)

    # ---------- نطاقات مستقلة ----------
    ro = db.generate_api_key("ro", ["patients.read"])
    ROH = {"Authorization": f"Bearer {ro['raw_key']}"}
    wo = db.generate_api_key("wo", ["patients.write"])
    WOH = {"Authorization": f"Bearer {wo['raw_key']}"}
    doke = db.generate_api_key("doke", ["patients.delete"])
    DOH = {"Authorization": f"Bearer {doke['raw_key']}"}

    check("read يقرأ قائمة", client.get("/api/v1/patients", headers=ROH).status_code == 200)
    check("read لا يكتب -> 403",
          client.post("/api/v1/patients", headers=ROH, json={"full_name": "X"}).status_code == 403)

    r = client.post("/api/v1/patients", headers=WOH, json={"full_name": "نطاق-كتابة"})
    _scoped_pid = r.json()["data"]["id"]
    check("write يكتب", r.status_code == 200)
    check("write لا يقرأ -> 403",
          client.get("/api/v1/patients", headers=WOH).status_code == 403)
    check("write لا يحذف -> 403 (delete مش ضمن write)",
          client.delete(f"/api/v1/patients/{_scoped_pid}", headers=WOH).status_code == 403)
    check("delete-only يحذف",
          client.delete(f"/api/v1/patients/{_scoped_pid}", headers=DOH).status_code == 200)
    check("delete-only لا يقرأ -> 403",
          client.get(f"/api/v1/patients/{_scoped_pid}", headers=DOH).status_code == 403)

    # ---------- CRUD مريض ----------
    r = client.post("/api/v1/patients", headers=H, json={
        "full_name": "مريض تجريبي", "phone": "01001234567",
        "birth_date": "1992-03-15", "gender": "male", "address": "القاهرة"})
    check("إنشاء مريض", r.status_code == 200, r.text[:200])
    pid = r.json()["data"]["id"]

    r = client.get(f"/api/v1/patients/{pid}", headers=H)
    check("قراءة مريض", r.status_code == 200 and r.json()["data"]["full_name"] == "مريض تجريبي")

    r = client.patch(f"/api/v1/patients/{pid}", headers=H, json={"phone": "01009999"})
    check("تعديل مريض (patch)", r.status_code == 200 and r.json()["data"]["phone"] == "01009999")

    r = client.get(f"/api/v1/patients/{pid + 9999}", headers=H)
    check("مريض غير موجود -> 404", r.status_code == 404)
    check("كود patient_not_found", r.json()["error"]["code"] == "patient_not_found")

    # ---------- pagination + search ----------
    for i in range(12):
        client.post("/api/v1/patients", headers=H, json={"full_name": f"تبويب-{i}"})
    r = client.get("/api/v1/patients?page=1&page_size=5", headers=H)
    check("pagination meta", r.status_code == 200 and r.json()["meta"]["page"] == 1
          and r.json()["meta"]["page_size"] == 5)
    r2 = client.get("/api/v1/patients?page=2&page_size=5", headers=H)
    check("pagination صفحات", r.json()["meta"]["pages"] == r2.json()["meta"]["pages"])

    # ---------- مواعيد ----------
    r = client.post("/api/v1/appointments", headers=H,
                    json={"patient_id": pid, "appt_date": "2026-10-01", "appt_time": "09:30",
                          "duration_minutes": 30})
    check("إنشاء موعد", r.status_code == 200, r.text[:200])
    aid = r.json()["data"]["id"]

    r = client.post("/api/v1/appointments", headers=H,
                    json={"patient_id": 999999999, "appt_date": "2026-10-01",
                          "appt_time": "10:00"})
    check("موعد لمريض غير موجود -> 404", r.status_code == 404)

    r = client.get("/api/v1/appointments?appt_date=2026-10-01", headers=H)
    check("قائمة مواعيد بفilter تاريخ", r.status_code == 200 and r.json()["data"])

    r = client.post(f"/api/v1/appointments/{aid}/cancel", headers=H)
    check("إلغاء موعد", r.status_code == 200 and r.json()["data"]["status"] == "cancelled",
          r.text[:200])

    r = client.patch(f"/api/v1/appointments/{aid}", headers=H, json={"notes": "بعد الإلغاء"})
    check("تعديل موعد", r.status_code == 200)

    # ---------- زيارات متابعة ----------
    r = client.post(f"/api/v1/patients/{pid}/visits", headers=H,
                    json={"notes": "متابعة بعد الحشو", "doctor_name": "د. أحمد"})
    check("إنشاء زيارة", r.status_code == 200)
    vid = r.json()["data"]["id"]
    r = client.get(f"/api/v1/patients/{pid}/visits", headers=H)
    check("قائمة الزيارات", r.status_code == 200 and len(r.json()["data"]) == 1)
    r = client.patch(f"/api/v1/visits/{vid}", headers=H, json={"notes": "تحديث"})
    check("تعديل زيارة", r.status_code == 200 and r.json()["data"]["notes"] == "تحديث")
    r = client.delete(f"/api/v1/visits/{vid}", headers=H)
    check("حذف زيارة", r.status_code == 200)

    # ---------- حسابات / حركات مالية ----------
    r = client.post(f"/api/v1/patients/{pid}/transactions", headers=H,
                    json={"tx_type": "charge", "amount": 1500.0, "description": "حشو تجميلي"})
    check("تحصيل charge", r.status_code == 200, r.text[:200])
    cid = r.json()["data"]["id"]
    r = client.post(f"/api/v1/patients/{pid}/transactions", headers=H,
                    json={"tx_type": "payment", "amount": 500.0, "description": "دفعة أولى"})
    check("تسجيل payment", r.status_code == 200)
    pid_tx = r.json()["data"]["id"]

    r = client.get(f"/api/v1/patients/{pid}/financials", headers=H)
    check("كشف الحسابات", r.status_code == 200 and len(r.json()["data"]["transactions"]) == 2)

    r = client.get(f"/api/v1/patients/{pid}/balance", headers=H)
    bal = r.json()["data"]
    check("الرصيد بعد الدفع", r.status_code == 200 and bal["balance"] == 1000.0,
          f"balance={bal}")

    r = client.patch(f"/api/v1/transactions/{cid}", headers=H, json={"amount": 1200.0})
    check("تعديل قيمة حركة", r.status_code == 200 and r.json()["data"]["amount"] == 1200.0)

    r = client.post(f"/api/v1/patients/{pid}/transactions", headers=H,
                    json={"tx_type": "refund", "amount": 5})
    check("نوع حركة ممنوع -> 422", r.status_code == 422)
    check("كود validation_error", r.json()["error"]["code"] == "validation_error")

    r = client.delete(f"/api/v1/transactions/{pid_tx}", headers=H)
    check("حذف حركة", r.status_code == 200)

    # ---------- خريطة الأسنان ----------
    r = client.patch(f"/api/v1/patients/{pid}/odontogram/tooth/16",
                     headers=H, json={"status": "missing", "notes": "خلع قديم"})
    check("تعديل سن", r.status_code == 200)
    r = client.get(f"/api/v1/patients/{pid}/odontogram", headers=H)
    check("قراءة الشارت", r.status_code == 200 and "presence" in r.json()["data"])

    r = client.put(f"/api/v1/patients/{pid}/odontogram/annotation/16",
                   headers=H, json={"note_text": "سن طبية مخلوعة", "doctor_name": "د. سارة"})
    check("إضافة annotation", r.status_code == 200)
    r = client.delete(f"/api/v1/patients/{pid}/odontogram/annotation/16", headers=H)
    check("حذف annotation", r.status_code == 200)

    r = client.post(f"/api/v1/patients/{pid}/odontogram/treatments", headers=H,
                    json={"tooth_number": 26, "treatment_key": "crown", "price": 800.0})
    check("تسجيل معالجة على سن (~سجل + charge)", r.status_code == 200, r.text[:200])

    # ---------- سجل الأحداث ----------
    r = client.get("/api/v1/events", headers=H)
    types = [e["event_type"] for e in r.json()["data"]]
    check("الأحداث من سجل", r.status_code == 200)
    check("حدث patient.created مسجل", "patient.created" in types)
    check("حدث appointment.cancelled مسجل", "appointment.cancelled" in types)
    check("حدث payment.created مسجل", "payment.created" in types)

    # أحداث بدون صلاحية events.read
    r = client.get("/api/v1/events", headers=ROH)
    check("events بدون صلاحية -> 403", r.status_code == 403)

    # ---------- تسريب البيانات المحسّنة ----------
    listed = db.list_api_keys()
    check("مفاتيح API مش بتفضح الـ hash", all("sha256$" not in str(k.get("key_preview", ""))
                                              for k in listed))
    full_row = next((k for k in listed if k["name"] == "full"), None)
    check("المعاينة مقصوصة ومش النص الكامل",
          full_row is not None
          and full_row.get("key_preview") != full["raw_key"]
          and len(full_row.get("key_preview", "")) < len(full["raw_key"]))
    stored_hash = db._hash_api_key(full["raw_key"])
    check("المفتاح بيتخزن hash ويترجع به",
          db.get_api_key_by_hash(stored_hash) is not None
          and db.get_api_key_by_hash(stored_hash)["id"] == full["id"])

    if FAILURES:
        print("\nFAILURES:", FAILURES)
        sys.exit(1)
    print("ALL_OK")


if __name__ == "__main__":
    main()