# -*- coding: utf-8 -*-
"""
مصادقة مفاتيح الـ API + فرض النطاقات (scopes).

- Bearer token في هيدر Authorization (مثال: Authorization: Bearer dentora_...).
- المفتاح بيتخزن في قاعدة البيانات كـ SHA-256 بس (شوف generate_api_key في
  database.py). مقارنة آمنة ضد التوقيت عبر hmac.compare_digest.
- كل endpoint بيعلن النطاقات اللي محتاجها، وأي طلب من مفتاح موثّق معندهوش
  النطاق دا بيرجع 403 insufficient_scope.

قاعدة حاسمة (زي موثّقة في الوثائق): الـ delete مش متضمن في الـ write أبدًا.
"""

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)

import database as db

_bearer = HTTPBearer(auto_error=False)


def _hash_key(raw_key):
    return db._hash_api_key(raw_key)


def get_api_key(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    """دالة dependent محورية: بتتحقق من هيدر Bearer وبتترجع المفتاح.

    Returns:
        dict: صف api_keys (id, name, scopes list, enabled, ...).

    أخطاء محتملة (حسب Format الخطأ الموحّد):
        401 missing_api_key / invalid_api_key
        403 api_key_disabled
    """
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key",
                    "message": "هيدر Authorization: Bearer <key> مطلوب."},
        )
    key_hash = _hash_key(creds.credentials)
    key = db.get_api_key_by_hash(key_hash)
    if not key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_api_key",
                    "message": "مفتاح API غير صالح."},
        )
    if not key.get("enabled"):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail={"code": "api_key_disabled",
                    "message": "مفتاح API موقوف. فعّله من إعدادات البرنامج."},
        )
    key["scopes"] = [
        s.strip() for s in (key.get("scopes") or "").split(",") if s.strip()
    ]
    db.record_api_key_usage(key["id"])
    return key


def require_scopes(*needed):
    """صانع dependent بيضمن إن المفتاح الموثّق عنده النطاقات المطلوبة كلها."""
    def _guard(key: dict = Depends(get_api_key)):
        missing = [s for s in needed if s not in key.get("scopes", [])]
        if missing:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={"code": "insufficient_scope",
                        "message": "المفتاح معندهوش الصلاحيات المطلوبة.",
                        "details": {"required": list(needed), "missing": missing}},
            )
        return key
    return _guard