# -*- coding: utf-8 -*-
"""
اختبارات الـ webhooks الصادرة: HMAC، التوصيل، المهلة، إعادة المحاولة،
فلترة الأحداث، وسجل التسليم.

تشغيل:  python -c "import sys; sys.path.insert(0,'.'); import tests.webhook_tests as t; t.main()"
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

from dentora_events import build_event, dispatch_webhook, emit

FAILURES = []


def check(name, cond, extra=""):
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" ({extra})" if extra else ""))
    if not cond:
        FAILURES.append(name)


class Receiver:
    """خادم HTTP محلي بيقبض الطلبات وبيخزن (headers, raw_body)."""

    def __init__(self, response_code=200):
        self.received = queue.Queue()
        self.response_code = response_code

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(inner_self):
                length = int(inner_self.headers.get("Content-Length", 0))
                body = inner_self.rfile.read(length)
                self.received.put({
                    "headers": dict(inner_self.headers),
                    "body": body,
                })
                inner_self.send_response(self.response_code)
                inner_self.end_headers()

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}/dentora-hook"

    def wait_for_request(self, timeout=8.0):
        try:
            return self.received.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _verify_signature(req, secret):
    sig_header = req["headers"].get("X-Dentora-Signature", "")
    if not sig_header.startswith("sha256="):
        return False, f"no signature header: {sig_header}"
    expected = hmac.new(secret.encode("utf-8"), req["body"], hashlib.sha256).hexdigest()
    return (hmac.compare_digest(sig_header.removeprefix("sha256="), expected),
            f"expect {expected} got {sig_header}")


def main():
    # -------- 1) توصيل عادي عبر مسار الأحداث + HMAC صحيح --------
    secret = "test-secret-123"
    wh_id = db.add_outbound_webhook("hook-success", Receiver().url, secret=secret,
                                    event_types="*", timeout_seconds=3)
    recv = Receiver()  # actual receiver bound to url
    db.update_outbound_webhook(wh_id, url=recv.url)

    pid = db.add_patient("مريض هوك", phone="0100")
    req = recv.wait_for_request(timeout=8)
    check("استقبلنا الطلب", req is not None)
    payload = json.loads(req["body"].decode("utf-8"))
    check("body يحتوي event_id/event_type/timestamp",
          all(k in payload for k in ("event_id", "event_type", "resource", "data", "timestamp")))
    check("event_type = patient.created", payload["event_type"] == "patient.created")
    check("event_id يطابق X-Dentora-Event-Id",
          req["headers"].get("X-Dentora-Event-Id") == payload["event_id"])
    ok_sig, sig_detail = _verify_signature(req, secret)
    check("توقيع HMAC صحيح", ok_sig, sig_detail)

    time.sleep(0.5)
    deliveries = db.get_webhook_deliveries(webhook_id=wh_id)
    check("سجل تسليم delivered", deliveries and deliveries[0]["status"] == "delivered",
          str(deliveries))
    wh_after = db.get_outbound_webhook(wh_id)
    check("webhook.last_status = delivered", wh_after["last_status"] == "delivered")
    recv.close()

    # -------- 2) اتصال متزامن مباشر + كود رد 201 مسجل --------
    recv201 = Receiver(response_code=201)
    wh_sync = db.add_outbound_webhook("hook-201", recv201.url, secret="s",
                                      event_types="*", timeout_seconds=3)
    ev = build_event("test.ping", "system", {"n": 1})
    ok = dispatch_webhook(db.get_outbound_webhook(wh_sync), ev)
    check("dispatch متزامن نجح", ok is True)
    time.sleep(0.3)
    d = db.get_webhook_deliveries(webhook_id=wh_sync)
    check("http_status = 201 مسجل", d and d[0]["http_status"] == 201, str(d))
    recv201.close()

    # -------- 3) مهلة + إعادة محاولة محدودة + فشل نهائي --------
    # منفذ مغلق -> رفض اتصال فوري، وهنختبر إعادة المحاولة بـ max_attempts=3
    wh_dead = db.add_outbound_webhook("hook-dead", "http://127.0.0.1:1/dead",
                                      secret="", event_types="*",
                                      timeout_seconds=1, max_attempts=3)
    ok = dispatch_webhook(db.get_outbound_webhook(wh_dead), build_event("test.ping", "system", {}))
    check("فشل إرسال لمنفذ مغلق", ok is False)
    d = db.get_webhook_deliveries(webhook_id=wh_dead)
    check("delivery failed بعد المحاولات", d and d[0]["status"] == "failed", str(d))
    check("attempt = max_attempts (3)", d and d[0]["attempt"] == 3, str(d))
    check("سبب فشل مسجل", d and bool(d[0]["error"]), str(d))
    wh_after = db.get_outbound_webhook(wh_dead)
    check("last_status = failed", wh_after["last_status"] == "failed")

    # -------- 4) فلترة الأحداث --------
    recv_f = Receiver()
    wh_filtered = db.add_outbound_webhook("hook-payment-only", recv_f.url,
                                          secret="", event_types="payment.created",
                                          timeout_seconds=3)
    db.add_patient("مريض ثاني")  # patient.created -> مش متبعتة
    time.sleep(1.0)
    check("unrelated event لم يصل", recv_f.received.empty())
    db.add_transaction(1, "payment", 700.0)  # payment.created -> بتتوصّل
    req = recv_f.wait_for_request(timeout=8)
    check("payment.created وصل للفلتر", req is not None
          and json.loads(req["body"])["event_type"] == "payment.created")
    recv_f.close()

    # -------- 5) نشطو/تعطيل webhook --------
    recv_off = Receiver()
    wh_off = db.add_outbound_webhook("hook-disabled", recv_off.url, secret="", event_types="*")
    db.update_outbound_webhook(wh_off, enabled=False)
    db.add_patient("مريض تالت")
    time.sleep(1.0)
    check("webhook موقوف لا يستقبل", recv_off.received.empty())
    recv_off.close()

    if FAILURES:
        print("\nFAILURES:", FAILURES)
        sys.exit(1)
    print("ALL_OK")


if __name__ == "__main__":
    main()