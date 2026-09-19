# -*- coding: utf-8 -*-
"""نقاط النظام: health (بدون مصادقة) + سجل الأحداث (يتطلب events.read)."""

from datetime import datetime

from fastapi import APIRouter, Depends

import database as db
from api.config import API_PREFIX, API_VERSION
from api.security import require_scopes

router = APIRouter(prefix=API_PREFIX, tags=["system"])


@router.get("/health")
def health():
    """فحص توفر الخادم - بدون مصادقة عشان يسهل على n8n/أنظمة خارجية
    التأكد إن الخادم شغال (لا يفضح أي بيانات)."""
    return {"data": {
        "status": "ok",
        "version": API_VERSION,
        "time": datetime.now().astimezone().isoformat(),
    }, "meta": {}}


@router.get("/events")
def list_events(
    event_type: str = "",
    limit: int = 100,
    _key: dict = Depends(require_scopes("events.read")),
):
    """أحدث الأحداث المسجلة (للتشخيص والتنسيق مع الأنظمة الخارجية)."""
    rows = db.get_event_log(event_type=event_type or None, limit=max(1, min(limit, 500)))
    return {"data": rows, "meta": {"count": len(rows)}}