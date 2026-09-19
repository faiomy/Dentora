# -*- coding: utf-8 -*-
"""إعدادات عامة للـ Dentora API (ثوابت مش بتتغير في أغلب الأحيان)."""

API_VERSION = "1.0.0"
API_PREFIX = "/api/v1"
APP_TITLE = "Dentora API"
APP_DESCRIPTION = (
    "واجهة برمجة تطبيقات لعيادة الأسنان - للمزامنة والتكامل مع أنظمة خارجية "
    "(مثل n8n). المصدر الوحيد للبيانات هو قاعدة بيانات SQLite بتاعة البرنامج "
    "على نفس الجهاز/الشبكة."
)

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

# المينى المساعد: قيم افتراضية لخادم الـ API (تتقرأ من clinic_settings)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8100