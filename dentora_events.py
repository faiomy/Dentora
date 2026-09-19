# -*- coding: utf-8 -*-
"""
طبقة أحداث العيادة + الـ webhooks الصادرة (لـ Dentora API).

مسؤولية الموديول ده:
  * تسجيل الأحداث (event_log) - كل حدث بيتسجل حتى لو مفيش webhooks.
  * تنفيذ الـ webhooks الصادرة بصورة غير متزامنة (thread خلفي) مع:
      - توقيع HMAC-SHA256 للـ payload (header X-Dentora-Signature خاصة).
      - إعادة محاولة محدودة + مهلة زمنية لكل محاولة.
      - تسجيل كل محاولة في جدول webhook_deliveries.

ملاحظات معمارية:
  * الموديول ده متعمد برة مجلد api/ عشان database.py يقدر يستدعيه من غير
    ما يستورد FastAPI خالص (database.py بيحمّل dentora_events بشكل كسول
    جوه `_emit_event` فمفيش استيراد دائري).
  * الـ webhooks هنا بيبعتوا "أحداث موحّدة موقّعة" - وظيفة مختلفة عن
    n8n_integration.py اللي بيبعت رسايل واتساب عادية (الكود ده محفوظ زي ما هو).
"""

import hashlib
import hmac
import json
import threading
import time
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone

# ------------------------------------------------------------
# نطاقات الصلاحيات (scopes) لمفاتيح الـ API - مرجع موحّد لـ:
# الـ API (api/security.py) + لوحة الإعدادات (ui/settings_page.py).
# جزء read / write / delete لكل مورد مستقل تمامًا، والـ delete
# مش متضمن في الـ write إطلاقًا.
# ------------------------------------------------------------
SCOPES = {
    "patients.read": "عرض المرضى",
    "patients.write": "إنشاء/تعديل المرضى",
    "patients.delete": "حذف المرضى",
    "appointments.read": "عرض المواعيد",
    "appointments.write": "إنشاء/تعديل/إلغاء المواعيد",
    "appointments.delete": "حذف المواعيد",
    "visits.read": "عرض زيارات المتابعة",
    "visits.write": "إنشاء/تعديل زيارات المتابعة",
    "visits.delete": "حذف زيارات المتابعة",
    "financials.read": "عرض الحسابات والحركات",
    "financials.write": "تسجيل حركات مالية (دفعات/خصومات)",
    "financials.delete": "حذف حركات مالية",
    "odontogram.read": "عرض خريطة الأسنان",
    "odontogram.write": "تعديل خريطة الأسنان",
    "events.read": "قراءة سجل الأحداث (للتصحيح والتشخيص)",
}

RESOURCE_SCOPES = {
    "patients": ("patients.read", "patients.write", "patients.delete"),
    "appointments": ("appointments.read", "appointments.write", "appointments.delete"),
    "visits": ("visits.read", "visits.write", "visits.delete"),
    "financials": ("financials.read", "financials.write", "financials.delete"),
    "odontogram": ("odontogram.read", "odontogram.write"),
}

# الأحداث اللي بتبتعت من طبقة قاعدة البيانات (+ حدث اختبار يدوي)
EVENT_TYPES = (
    "patient.created", "patient.updated",
    "appointment.created", "appointment.updated", "appointment.cancelled",
    "visit.created", "visit.updated",
    "payment.created",
    "test.ping",
)

_UA = "Dentora-API/1.0"


def _now_iso():
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def build_event(event_type, resource, data):
    """بيبني قاموس الحدث الموحّد اللي بيتسجل ويتنبعت للـ webhooks"""
    return {
        "event_id": uuid.uuid4().hex,
        "event_type": event_type,
        "resource": resource,
        "data": data,
        "timestamp": _now_iso(),
    }


def _webhook_matches(webhook, event_type):
    types = [t.strip() for t in (webhook.get("event_types") or "").split(",") if t.strip()]
    return "*" in types or event_type in types


def emit(event_type, resource, data):
    """نقطة الإخراج الرئيسية للأحداث (بتتندى من database.py بعد الـ commit).

    بتسجل الحدث في event_log دايمًا، وبتبعت نسخة لكل webhook صادر مفعّل
    بيستنى النوع ده. الإرسال بيتم في thread خلفي عشان ميمنعشش عملية
    قاعدة البيانات الأصلية. أي فشل هنا - حتى لو الجداول مش موجودة لسه -
    بيتم تجاهله بصمت (الاستدعاء الأساسي مش هيتعطل أبدًا بسبب الأحداث).
    """
    try:
        import database as db
        event = build_event(event_type, resource, data)
        db.log_event_entry(event_type, json.dumps(event, ensure_ascii=True))
        for webhook in db.get_outbound_webhooks_for_event(event_type):
            if not _webhook_matches(webhook, event_type):
                continue
            t = threading.Thread(
                target=dispatch_webhook,
                args=(webhook, event),
                name=f"dentora-webhook-{event['event_id'][:8]}",
                daemon=True,
            )
            t.start()
    except Exception:
        pass


def _sign(secret, body):
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def dispatch_webhook(webhook, event):
    """بيبع حدث واحد لـ webhook واحد مع إعادة محاولة محدودة وتوقيع HMAC.

    - بديهيًا يمكن استدعاؤها مباشرة (متزامنة) في الاختبارات.
    - من emit() بتتندى في thread خلفي.
    """
    import database as db

    url = webhook.get("url") or ""
    if not url:
        return
    secret = webhook.get("secret") or ""
    max_attempts = max(1, int(webhook.get("max_attempts") or 3))
    timeout = max(1, int(webhook.get("timeout_seconds") or 10))

    body = json.dumps(event, ensure_ascii=True).encode("utf-8")
    signature = _sign(secret, body) if secret else ""

    delivery_id = None
    last_error = ""
    last_http = None
    for attempt in range(1, max_attempts + 1):
        if delivery_id is None:
            delivery_id = db.add_webhook_delivery(webhook["id"], event.get("event_type", ""))
        headers = {
            "Content-Type": "application/json",
            "User-Agent": _UA,
            "X-Dentora-Event-Id": str(event.get("event_id", "")),
            "X-Dentora-Timestamp": str(event.get("timestamp", "")),
        }
        if signature:
            headers["X-Dentora-Signature"] = "sha256=" + signature
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                last_http = resp.status
                db.update_webhook_delivery(
                    delivery_id, attempt, "delivered", http_status=last_http)
                db.update_webhook_last_status(webhook["id"], "delivered")
                return True
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < max_attempts:
                time.sleep(attempt)  # backoff بسيط: 1,2,3...
    db.update_webhook_delivery(
        delivery_id, attempt, "failed", http_status=last_http, error=last_error)
    db.update_webhook_last_status(webhook["id"], "failed", error=last_error)
    return False