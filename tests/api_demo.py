# -*- coding: utf-8 -*-
"""
تجربة التكامل الحقيقية في الاتجاهين (Phase 18 من مواصفة "API & Integration").

تشغيل:  python -c "import sys; sys.path.insert(0,'.'); import tests.api_demo as t; t.main()"

الاتجاهات:
  (أ) "n8n -> Dentora":  httpx بيعمل HTTP حقيقي للخادم اللي شغال في thread
      خلفي، وبيفتح/يقري بيانات فعلية من قاعدة بيانات البرنامج.
  (ب) "Dentora -> n8n":  حدث patient.created بيتم توصيله لـ webhook محلي
      (Bee يستقبله ويصدق توقيع HMAC وبيطابق id المريض).
"""

import hashlib
import hmac
import http.server
import json
import sys
import threading
import time
import queue

from tests.helpers import fresh_db_path
fresh_db_path()

import database as db
db.init_db()

FAILURES = []


def check(name, cond, extra=""):
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" ({extra})" if extra else ""))
    if not cond:
        FAILURES.append(name)


def main():
    PORT = 8471
    db.set_setting_value("api_server_enabled", 1)
    db.set_setting_value("api_host", "127.0.0.1")
    db.set_setting_value("api_port", PORT)

    # إلغاء أي webhook قديمة ونضيف واحدة لاستقبال أحداث المرضى
    for w in db.list_outbound_webhooks():
        db.delete_outbound_webhook(w["id"])
    received = queue.Queue()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(inner_self):
            length = int(inner_self.headers.get("Content-Length", 0))
            body = inner_self.rfile.read(length)
            received.put({"headers": dict(inner_self.headers), "body": body})
            inner_self.send_response(200)
            inner_self.end_headers()

        def log_message(self, *args):
            pass

    recv_server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=recv_server.serve_forever, daemon=True).start()
    rhost, rport = recv_server.server_address
    webhook_url = f"http://{rhost}:{rport}/dentora-events"

    secret = "demo-secret-123"
    db.add_outbound_webhook("n8n-webhook-receiver", webhook_url, secret=secret,
                            event_types="*", timeout_seconds=3, max_attempts=3)

    # ---------- بدء الخادم الحقيقي ----------
    from api.server import start_api_server_if_enabled, stop_api_server, get_api_server
    started = start_api_server_if_enabled()
    check("خادم API شغال فعليًا (uvicorn background thread)",
          started and get_api_server().is_running, f"started={started}")
    if not started:
        print("DEMO_ABORT")
        sys.exit(1)

    # ---------- مفتاح API ----------
    key = db.generate_api_key("demo-n8n", [
        "patients.read", "patients.write", "events.read"])
    auth = {"Authorization": f"Bearer {key['raw_key']}"}

    import httpx
    base = f"http://127.0.0.1:{PORT}/api/v1"

    # ---------- الاتجاه (أ): n8n -> Dentora عبر HTTP ----------
    with httpx.Client(timeout=10) as client:
        r = client.get(f"{base}/health")
        check("health عبر HTTP حقيقي", r.status_code == 200
              and r.json()["data"]["status"] == "ok")

        r = client.get(f"{base}/patients", headers=auth)
        check("قائمة المرضى قبل", r.status_code == 200
              and r.json()["data"] == [], r.text[:200])

        created = {"full_name": "مريض من n8n", "phone": "01005556666",
                   "birth_date": "1988-02-20", "gender": "female"}
        r = client.post(f"{base}/patients", headers=auth, json=created)
        check("إنشاء مريض عبر HTTP (فاتحة) من n8n", r.status_code == 200, r.text[:200])
        patient_id = r.json()["data"]["id"]
        check("النظام أنشأه فعليًا في قاعدة البيانات",
              db.get_patient(patient_id)["full_name"] == "مريض من n8n")

        r = client.get(f"{base}/patients?search=n8n", headers=auth)
        check("بحث عبر HTTP جايب المريض", r.status_code == 200
              and any(p["id"] == patient_id for p in r.json()["data"]))

        r = client.get(f"{base}/events", headers=auth)
        check("سجل أحداث فيىمن الخادم فيه patient.created",
              any(e.get("event_type") == "patient.created" for e in r.json()["data"]))

        r = client.get(f"http://127.0.0.1:{PORT}/docs")
        check("توثيق OpenAPI/Swagger يعمل عبر HTTP", r.status_code == 200)

    # ---------- الاتجاه (ب): Dentora -> n8n عبر Webhook + HMAC ----------
    req = None
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            req = received.get(timeout=2)
            break
        except queue.Empty:
            continue
    check("حدث وصل للـ webhook (n8n استقبل الحدث)", req is not None)

    if req is not None:
        payload = json.loads(req["body"].decode("utf-8"))
        check("event_type = patient.created", payload["event_type"] == "patient.created")
        check("بيانات الحدث فيها id المريض الجديد",
              payload["data"].get("id") == patient_id, str(payload["data"])[:120])
        signed = req["headers"].get("X-Dentora-Signature", "")
        expected = "sha256=" + hmac.new(
            secret.encode(), req["body"], hashlib.sha256).hexdigest()
        check("توقيع HMAC يصدّق من جانب المستقبِل",
              hmac.compare_digest(signed, expected),
              f"expect {expected} got {signed[:40]}...")

    # ---------- توقف آمن ----------
    stop_api_server()
    time.sleep(0.5)
    check("الخادم اتوقف بأمان", not get_api_server().is_running)
    recv_server.shutdown()
    recv_server.server_close()

    if FAILURES:
        print("\nFAILURES:", FAILURES)
        sys.exit(1)
    print("ALL_OK - الاتجاهان يعملون")


if __name__ == "__main__":
    main()