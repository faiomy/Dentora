# -*- coding: utf-8 -*-
"""
Helper for sending messages via n8n webhook.
Environment variables required:
    N8N_WEBHOOK_URL - The full webhook URL to POST to.
    N8N_API_KEY     - (Optional) API key for authentication, sent as Bearer token.
"""

import os
import json
import time

try:
    import requests
except ImportError:
    requests = None

import urllib.request

# عدد المحاولات الافتراضي ووقت الانتظار بينهم (ثواني) - الانتظار بيزيد مع
# كل محاولة (backoff خطي بسيط: 2 ثواني بعد الأولى، 4 بعد التانية...)
DEFAULT_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 2


def _post_to_webhook(phone: str, message: str) -> None:
    """محاولة إرسال واحدة - بترفع استثناء لو فشلت، وبترجع لو نجحت."""
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("N8N_WEBHOOK_URL environment variable not set.")

    api_key = os.getenv("N8N_API_KEY")
    payload = json.dumps({"phone": phone, "message": message}).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Prefer requests if available; otherwise fall back to Python's stdlib urllib.
    if requests is not None:
        response = requests.post(webhook_url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        return

    req = urllib.request.Request(webhook_url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()  # read+close the response body


def send_message_via_n8n(phone: str, message: str, attempts: int = 1):
    """Send a message through n8n.

    Args:
        phone: Destination phone number (string).
        message: Message body.
        attempts: Total send attempts (each after a growing delay).
            الافتراضي محاولة واحدة بس - الصفحات اللي عايزة إعادة محاولة
            تلقائية بتنادي send_with_retries() أو تمرر attempts أكبر.

    Returns:
        (True, None) لو نجحت، أو (False, رسالة الخطأ) لو فشلت - بدل رفع
        استثناء، عشان المستدعي (اللي غالبًا شغال في thread خلفي) يعالج
        النتيجة ببساطة من غير try/except حوالين كل نداء.

    ملاحظة: الدالة دي بتعمل طلب شبكة فعلي - بتناديها في thread خلفي
    مش على الـ UI thread (شوف pages/n8n_page.py).
    """
    attempts = max(1, int(attempts))
    last_error = None
    for attempt in range(attempts):
        try:
            _post_to_webhook(phone, message)
            return True, None
        except Exception as exc:  # noqa: BLE001 - أي فشل شبكة/إعداد بيتحول لرسالة
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts - 1:
                time.sleep(RETRY_BASE_DELAY_SECONDS * (attempt + 1))
    return False, last_error


def get_n8n_webhook_status():
    """فحص جاهزية الويب هوك من غير ما يبعت حاجة - بيرجع (جاهز، رسالة توضيحية)
    للعرض في صفحة n8n عشان المستخدم يعرف لو متغيرات البيئة متظبطة ولا لأ."""
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        return False, "متغير البيئة N8N_WEBHOOK_URL مش متحدد - الإرسال مش هيشتغل"
    if requests is None and os.getenv("N8N_API_KEY"):
        return True, "الويب هوك جاهز (على urllib - مكتبة requests مش متثبتة)"
    return True, "الويب هوك جاهز للإرسال"


def send_with_retries(phone: str, message: str, attempts: int = DEFAULT_ATTEMPTS):
    """اختصار للإرسال مع 3 محاولات افتراضيًا وانتظار متزايد بينهم - ده
    المسار المستخدم من صفحة n8n جوه البرنامج."""
    return send_message_via_n8n(phone, message, attempts=attempts)
