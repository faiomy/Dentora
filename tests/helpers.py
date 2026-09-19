# -*- coding: utf-8 -*-
"""مصادر مشتركة لاختبارات Dentora API."""
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def fresh_db_path():
    """مجلد مؤقت لقاعدة بيانات اختبارية - لازم يتستدعى قبل استيراد database."""
    tmp = tempfile.mkdtemp(prefix="dentora_test_")
    env_path = os.path.join(tmp, "clinic.db")
    os.environ["DENTORA_DB_PATH"] = env_path
    return env_path


def make_full_scope_key(db, prefix="test", extra=()):
    from dentora_events import SCOPES
    scopes = list(SCOPES.keys()) + list(extra)
    return db.generate_api_key(prefix, scopes)


def make_scope_key(db, *scopes, prefix="test"):
    return db.generate_api_key(prefix, list(scopes))