# -*- coding: utf-8 -*-
"""
دورة حياة خادم الـ API.

- pyreach: الخادم بيتشغّل في thread خلفي (daemon) عشان ميجمدش حلقات
  الأحداث بتاعة PySide6 أبدًا.
- المينى: بـ 127.0.0.1:8100 افتراضيًا (محلي فقط). عشان الوصول من الشبكة
  المحلية، المستخدم لازم يحدد host زي 0.0.0.0 صراحةً من إعدادات البرنامج.
- stop عن طريق setting `server.should_exit = True` - اللي uvicorn بيراقبه
  في loop بتاعه (السيغنالز مش بتتثبت جوه thread خلفي أصلاً، شوف
  uvicorn.Server.capture_signals).
"""

import sys
import threading

import uvicorn

from api.config import API_PREFIX, DEFAULT_HOST, DEFAULT_PORT
from api.app import app as _fastapi_app


def _ensure_sys_path():
    """عشان `python -m api` يشتغل حتى لو الجلسة مش من جوا مجلد المشروع"""
    import os
    root = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
    if root not in sys.path:
        sys.path.insert(0, root)


_ensure_sys_path()


def _read_server_settings():
    import database as db
    s = db.get_settings() or {}
    return {
        "enabled": bool(s.get("api_server_enabled")),
        "host": s.get("api_host") or DEFAULT_HOST,
        "port": int(s.get("api_port") or DEFAULT_PORT),
    }


class ApiServer:
    def __init__(self, host=None, port=None):
        self.host = host or DEFAULT_HOST
        self.port = port or DEFAULT_PORT
        self._server = None
        self._thread = None

    @property
    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def url(self):
        return f"http://{self.host}:{self.port}{API_PREFIX}"

    def start(self) -> bool:
        """بيبدأ الخادم في thread خلفي وبيستنى جاهزيته (timeout 8 ثواني)."""
        if self.is_running:
            return True
        config = uvicorn.Config(
            _fastapi_app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run,
            name="dentora-api-server",
            daemon=True,
        )
        self._thread.start()
        try:
            started = self._server.started.wait(timeout=8)
        except Exception:
            started = True
        return bool(started or self.is_running)

    def stop(self):
        server = self._server
        self._server = None
        if server is not None:
            server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=8)
            self._thread = None


_state = {"server": None}


def get_api_server() -> ApiServer:
    if _state["server"] is None:
        _state["server"] = ApiServer()
    return _state["server"]


def sync_server_with_settings():
    """بيقرا إعدادات الخادم الحالية وبيقفّلها مع مثيل الخادم."""
    s = _read_server_settings()
    srv = get_api_server()
    srv.host = s["host"]
    srv.port = s["port"]
    return srv


def start_api_server_if_enabled() -> bool:
    """المفروض تتدعى عند فتح البرنامج (بعد init_db وحالياً في qt_main)."""
    s = _read_server_settings()
    if not s["enabled"]:
        return False
    srv = get_api_server()
    srv.host = s["host"]
    srv.port = s["port"]
    srv.start()
    return srv.is_running


def restart_api_server() -> bool:
    """إعادة تشغيل باعدادات حاليًة (بيتندى من لوحة "الوصول API" بعد تغيير
    host/port/تفعيل)."""
    s = _read_server_settings()
    srv = get_api_server()
    srv.host = s["host"]
    srv.port = s["port"]
    srv.stop()
    srv.start()
    return srv.is_running


def stop_api_server():
    if _state.get("server") is not None:
        _state["server"].stop()


def is_api_server_running() -> bool:
    srv = _state.get("server")
    return bool(srv and srv.is_running)