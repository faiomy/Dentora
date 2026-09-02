# -*- coding: utf-8 -*-
"""
طبقة قاعدة البيانات - برنامج إدارة العيادة
يستخدم SQLite لأن ملف قاعدة البيانات هذا يمكن وضعه في مجلد مشترك على الشبكة
حتى يتمكن أكثر من جهاز من القراءة والكتابة فيه (network share).
"""

import sqlite3
import os
from datetime import datetime, timedelta
from datetime import date as _dt_date
from pages import teething_timeline

# مسار قاعدة البيانات - ممكن تتغير لمسار على الشبكة (مجلد مشترك) بدل المسار المحلي
# مثال لو هتحط الملف على مجلد مشترك: r"\\SERVER-PC\ClinicShare\clinic_data.db"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clinic_data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """إنشاء كل الجداول لو مش موجودة"""
    conn = get_connection()
    cur = conn.cursor()

    # إعدادات العيادة (اسم، لوجو، ألوان)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clinic_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            clinic_name TEXT NOT NULL DEFAULT 'عيادتي',
            logo_path TEXT,
            primary_color TEXT NOT NULL DEFAULT '#1E88E5',
            secondary_color TEXT NOT NULL DEFAULT '#0D47A1'
        )
    """)
    cur.execute("SELECT COUNT(*) FROM clinic_settings")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO clinic_settings (id, clinic_name, logo_path, primary_color, secondary_color)
            VALUES (1, 'عيادتي', NULL, '#1E88E5', '#0D47A1')
        """)

    # ترقية جدول الإعدادات القديم (إذا كانت هناك قاعدة بيانات أُنشئت قبل إضافة إعدادات الخط)
    # من غير ما نمسح أي بيانات موجودة
    cur.execute("PRAGMA table_info(clinic_settings)")
    existing_cols = {row[1] for row in cur.fetchall()}
    font_columns = {
        "system_font_family": "TEXT NOT NULL DEFAULT 'Segoe UI'",
        "content_font_family": "TEXT NOT NULL DEFAULT 'Segoe UI'",
        "system_font_size": "INTEGER NOT NULL DEFAULT 16",
        "content_font_size": "INTEGER NOT NULL DEFAULT 16",
    }
    for col, definition in font_columns.items():
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE clinic_settings ADD COLUMN {col} {definition}")

    extra_settings_cols = {
        "language": "TEXT NOT NULL DEFAULT 'ar'",
        "active_price_list_id": "INTEGER",
        "require_password": "INTEGER NOT NULL DEFAULT 0",
        "mini_calendar_width": "INTEGER NOT NULL DEFAULT 260",
        "weekly_holidays": "TEXT NOT NULL DEFAULT '3,4'",
        "schedule_start_hour": "INTEGER NOT NULL DEFAULT 0",
        "schedule_end_hour": "INTEGER NOT NULL DEFAULT 24",
        "clinic_address": "TEXT",
        "tax_card_number": "TEXT",
        # ---- إعدادات الأرشفة التلقائية لرسائل واتساب (تذكير قبل الموعد
        # بساعة + شكر بعد انتهاء الموعد الفعلي بساعتين) ----
        # كل نوع رسالة تلقائية بقى ليه تشيك بوكس مستقل تمامًا عن التاني -
        # مفيش مفتاح رئيسي واحد بيتحكم في الكل، كل واحد فيهم شغال لوحده
        "whatsapp_hour_reminder_enabled": "INTEGER NOT NULL DEFAULT 1",
        "whatsapp_next_day_batch_enabled": "INTEGER NOT NULL DEFAULT 1",
        # عمود قديم كان بيتحكم في الاتنين مع بعض - سايبينه موجود لأي كود
        # قديم لسه بيقرأه، لكن مبقاش بيُستخدم في القرار الفعلي للإرسال
        "whatsapp_auto_archive_enabled": "INTEGER NOT NULL DEFAULT 1",
        "whatsapp_auto_reminder_template_id": "INTEGER",
        "whatsapp_auto_thankyou_template_id": "INTEGER",
        "whatsapp_auto_booking_template_id": "INTEGER",
        "whatsapp_auto_confirm_send": "INTEGER NOT NULL DEFAULT 0",
        "whatsapp_auto_wait_seconds": "INTEGER NOT NULL DEFAULT 15",
        "whatsapp_auto_use_desktop_app": "INTEGER NOT NULL DEFAULT 1",
        # تفعيل رسالة الشكر التلقائية فور تسجيل دفعة مالية - مفعّلة افتراضيًا
        # (مستقلة عن باقي الأرشفة، لأنها بتتحكم في نوع رسالة معيّن بس)
        "whatsapp_payment_thankyou_enabled": "INTEGER NOT NULL DEFAULT 1",
        # موعد بث تذكير مواعيد الغد اليومي - افتراضيًا 3:00 الظهر، وقابل للتعديل من صفحة واتساب
        "whatsapp_next_day_batch_hour": "INTEGER NOT NULL DEFAULT 15",
        "whatsapp_next_day_batch_minute": "INTEGER NOT NULL DEFAULT 0",
        # ---- خاصية "تذكرني" في شاشة تسجيل الدخول ----
        "remember_login": "INTEGER NOT NULL DEFAULT 0",
        "remembered_username": "TEXT",
        "remembered_password": "TEXT",
        # ---- إظهار/إخفاء المسمى النصي تحت أيقونات الشريط العلوي ----
        "show_ribbon_labels": "INTEGER NOT NULL DEFAULT 1",
        # ---- تفعيل رسالة تأكيد فورية للمريض بمجرد حجز الموعد (مش هي نفسها
        # تذكير الساعة قبل الموعد - دي بتتبعت لحظة الحجز على طول) ----
        "whatsapp_booking_confirmation_enabled": "INTEGER NOT NULL DEFAULT 1",
        # ---- الثيم الجاهز المختار (لوحة ألوان كاملة) - راجع THEME_PRESETS في theme.py ----
        "theme_id": "TEXT NOT NULL DEFAULT 'ocean_blue'",
        # ---- شكل تصميم أزرار الشريط العلوي الرئيسي: classic / glass / luxury ----
        "nav_button_style": "TEXT NOT NULL DEFAULT 'classic'",
        # ---- نمط رسم أيقونات الشريط العلوي الرئيسية (شكل الرسمة نفسها،
        # مستقل عن nav_button_style اللي بيتحكم بس في شكل خلفية الزرار):
        # outline / filled / bold ----
        "icon_pattern": "TEXT NOT NULL DEFAULT 'outline'",
    }
    cur.execute("PRAGMA table_info(clinic_settings)")
    existing_cols2 = {row[1] for row in cur.fetchall()}
    for col, definition in extra_settings_cols.items():
        if col not in existing_cols2:
            cur.execute(f"ALTER TABLE clinic_settings ADD COLUMN {col} {definition}")

    # المستخدمين (نظام الصلاحيات - مدير / طبيب / سكرتارية)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('manager', 'doctor', 'secretary')),
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    cur.execute("PRAGMA table_info(users)")
    users_cols = {row[1] for row in cur.fetchall()}
    users_new_cols = {
        "phone": "TEXT", "specialty": "TEXT", "work_days": "TEXT",
        "birth_date": "TEXT", "address": "TEXT",
        "photo_path": "TEXT", "national_id": "TEXT", "national_id_photo_path": "TEXT",
        "salary": "REAL NOT NULL DEFAULT 0",
        "income_percent": "REAL NOT NULL DEFAULT 0",
        "start_date": "TEXT",
        "annual_raise_percent": "REAL NOT NULL DEFAULT 0",
        # تخصيصات المظهر الشخصية لكل مستخدم (ثيم/شكل أزرار/نمط أيقونات/خط) -
        # كل عمود منهم NULL افتراضيًا يعني "خليه زي إعداد العيادة العام"،
        # وأي قيمة محفوظة فيه معناها المستخدم ده اختار تفضيل شخصي بتاعه هو
        # بس، عشان أكتر من شخص يقدروا يستخدموا نفس الجهاز وكل واحد يشوف
        # المظهر اللي يريحه من غير ما يأثر على زمايله
        "theme_id": "TEXT", "nav_button_style": "TEXT", "icon_pattern": "TEXT",
        "system_font_family": "TEXT", "content_font_family": "TEXT",
    }
    for col, definition in users_new_cols.items():
        if col not in users_cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        # حساب مدير افتراضي - يُفترض تغييره بعد أول تشغيل
        cur.execute("""
            INSERT INTO users (username, password, full_name, role)
            VALUES ('admin', 'admin123', 'مدير العيادة', 'manager')
        """)

    # صلاحيات كل نوع حساب (المدير هو الوحيد القادر على تعديلها)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role TEXT NOT NULL,
            permission_key TEXT NOT NULL,
            allowed INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (role, permission_key)
        )
    """)
    cur.execute("SELECT COUNT(*) FROM role_permissions")
    if cur.fetchone()[0] == 0:
        default_permissions = [
            # (role, permission_key, allowed)
            ("manager", "view_patients", 1), ("manager", "edit_patients", 1),
            ("manager", "view_appointments", 1), ("manager", "edit_appointments", 1),
            ("manager", "view_accounts", 1), ("manager", "edit_accounts", 1),
            ("manager", "manage_prices", 1), ("manager", "manage_settings", 1),
            ("manager", "manage_users", 1),
            ("manager", "manage_expenses", 1), ("manager", "view_clinic_accounts", 1),
            ("manager", "manage_whatsapp", 1),

            ("doctor", "view_patients", 1), ("doctor", "edit_patients", 1),
            ("doctor", "view_appointments", 1), ("doctor", "edit_appointments", 1),
            ("doctor", "view_accounts", 1), ("doctor", "edit_accounts", 0),
            ("doctor", "manage_prices", 0), ("doctor", "manage_settings", 0),
            ("doctor", "manage_users", 0),
            ("doctor", "manage_expenses", 0), ("doctor", "view_clinic_accounts", 0),
            ("doctor", "manage_whatsapp", 0),

            ("secretary", "view_patients", 1), ("secretary", "edit_patients", 1),
            ("secretary", "view_appointments", 1), ("secretary", "edit_appointments", 1),
            ("secretary", "view_accounts", 1), ("secretary", "edit_accounts", 1),
            ("secretary", "manage_prices", 0), ("secretary", "manage_settings", 0),
            ("secretary", "manage_users", 0),
            ("secretary", "manage_expenses", 1), ("secretary", "view_clinic_accounts", 0),
            ("secretary", "manage_whatsapp", 1),
        ]
        cur.executemany(
            "INSERT INTO role_permissions (role, permission_key, allowed) VALUES (?, ?, ?)",
            default_permissions)

    # ترقية: إذا أُضيفت صلاحيات جديدة في نسخة أحدث ولم تكن موجودة بعد في قاعدة بيانات قديمة
    new_permission_defaults = {
        "manage_expenses": {"manager": 1, "doctor": 0, "secretary": 1},
        "view_clinic_accounts": {"manager": 1, "doctor": 0, "secretary": 0},
        "manage_staff": {"manager": 1, "doctor": 0, "secretary": 0},
        "manage_whatsapp": {"manager": 1, "doctor": 0, "secretary": 1},
        "manage_labs": {"manager": 1, "doctor": 1, "secretary": 1},
    }
    for perm_key, role_defaults in new_permission_defaults.items():
        for role, allowed in role_defaults.items():
            exists = cur.execute(
                "SELECT 1 FROM role_permissions WHERE role = ? AND permission_key = ?",
                (role, perm_key)).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO role_permissions (role, permission_key, allowed) VALUES (?, ?, ?)",
                    (role, perm_key, allowed))

    # المرضى
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT,
            birth_date TEXT,
            gender TEXT,
            address TEXT,
            medical_notes TEXT,
            allergies TEXT,
            created_at TEXT
        )
    """)

    # ترقية جدول المرضى (صورة شخصية، الوظيفة، رقم الأسرة) لو الجدول جه من نسخة أقدم
    cur.execute("PRAGMA table_info(patients)")
    patient_cols = {row[1] for row in cur.fetchall()}
    patient_new_cols = {
        "profile_photo_path": "TEXT",
        "occupation": "TEXT",
        "family_id": "TEXT",
        "nationality": "TEXT",
        "discount_percent": "REAL NOT NULL DEFAULT 0",
    }
    for col, definition in patient_new_cols.items():
        if col not in patient_cols:
            cur.execute(f"ALTER TABLE patients ADD COLUMN {col} {definition}")

    # مخطط الأسنان (Odontogram) - حالة بزوغ/وجود كل سن لكل مريض بمعيار FDI.
    # "status" بقى بيخزن حالة البزوغ (present/primary_present/unerupted/
    # missing/impacted) بدل القيمة الافتراضية القديمة "healthy" (لسه
    # بتتقرا كمرادف لـ"present" للتوافق مع بيانات قديمة)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tooth_chart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            tooth_number INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'healthy',
            notes TEXT,
            updated_at TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
            UNIQUE(patient_id, tooth_number)
        )
    """)

    # ترقية جدول خريطة الأسنان: عمود بيحدد هل الحالة دي متولدة تلقائيًا من
    # الجدول الزمني العالمي للتسنين (1) أو حددها الطبيب يدويًا (0) - عشان
    # أي توليد تلقائي لاحق (لما يتغير تاريخ الميلاد مثلاً) ميبوظش تعديل يدوي
    cur.execute("PRAGMA table_info(tooth_chart)")
    tooth_chart_cols = {row[1] for row in cur.fetchall()}
    if "auto_generated" not in tooth_chart_cols:
        cur.execute("ALTER TABLE tooth_chart ADD COLUMN auto_generated INTEGER NOT NULL DEFAULT 0")

    # المواعيد
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            appt_date TEXT NOT NULL,
            appt_time TEXT NOT NULL,
            doctor_name TEXT,
            status TEXT NOT NULL DEFAULT 'confirmed',
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    # ترقية جدول المواعيد لإضافة مدة الموعد (لو الجدول جه من نسخة أقدم)
    cur.execute("PRAGMA table_info(appointments)")
    appt_cols = {row[1] for row in cur.fetchall()}
    if "duration_minutes" not in appt_cols:
        cur.execute("ALTER TABLE appointments ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 30")
    if "color" not in appt_cols:
        cur.execute("ALTER TABLE appointments ADD COLUMN color TEXT")
    if "reminder_sent" not in appt_cols:
        cur.execute("ALTER TABLE appointments ADD COLUMN reminder_sent INTEGER NOT NULL DEFAULT 0")
    # تتبُّع منفصل للأرشفة التلقائية (تذكير قبل الموعد بساعة، وشكر بعد
    # انتهائه الفعلي بساعتين) حتى لا تختلط بالتذكير اليدوي (reminder_sent
    # أعلاه الخاص بإرسال يوم قبل الموعد يدويًا من شاشة واتساب)
    if "auto_reminder_1h_sent" not in appt_cols:
        cur.execute("ALTER TABLE appointments ADD COLUMN auto_reminder_1h_sent INTEGER NOT NULL DEFAULT 0")
    if "thank_you_sent" not in appt_cols:
        cur.execute("ALTER TABLE appointments ADD COLUMN thank_you_sent INTEGER NOT NULL DEFAULT 0")
    # تتبُّع رسالة "تذكير مواعيد الغد" اللي بتتبعت تلقائيًا الساعة 3 الظهر يوميًا
    if "next_day_reminder_sent" not in appt_cols:
        cur.execute("ALTER TABLE appointments ADD COLUMN next_day_reminder_sent INTEGER NOT NULL DEFAULT 0")

    # قوائم الأسعار (تقدر تعمل أكتر من قائمة وتختار الفعالة منهم)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    # هل جدول أسعار المعالجات موجود بالصيغة القديمة (قائمة واحدة فقط، من دون price_list_id)؟
    cur.execute("PRAGMA table_info(treatment_prices)")
    tp_cols = {row[1] for row in cur.fetchall()}
    needs_price_migration = bool(tp_cols) and "price_list_id" not in tp_cols
    if needs_price_migration:
        cur.execute("ALTER TABLE treatment_prices RENAME TO treatment_prices_old")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS treatment_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price_list_id INTEGER NOT NULL,
            treatment_key TEXT NOT NULL,
            label TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            commission_percent REAL NOT NULL DEFAULT 0,
            color TEXT,
            FOREIGN KEY (price_list_id) REFERENCES price_lists(id) ON DELETE CASCADE,
            UNIQUE(price_list_id, treatment_key)
        )
    """)
    cur.execute("PRAGMA table_info(treatment_prices)")
    tp_cols2 = {row[1] for row in cur.fetchall()}
    if "color" not in tp_cols2:
        cur.execute("ALTER TABLE treatment_prices ADD COLUMN color TEXT")
    if "symbol_key" not in tp_cols2:
        cur.execute("ALTER TABLE treatment_prices ADD COLUMN symbol_key TEXT")

    # الألوان الافتراضية لكل نوع علاج (تقدر تغيرها من صفحة الأسعار)
    DEFAULT_TREATMENT_COLORS = {
        "decay": "#E53935", "filled": "#1E88E5", "root_canal": "#FB8C00",
        "post": "#6D4C41", "implant": "#00897B",
        "calculus": "#9E9D24", "extracted": "#9E9E9E",
        # "crown" (تركيب تاج/طربوش) اتشال من هنا عمدًا - سعره ولونه بقوا
        # مقتصرين على الأنواع الفرعية الخاصة به فقط (زيركونيا/بورسلين/إيماكس)
    }

    cur.execute("SELECT COUNT(*) FROM price_lists")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO price_lists (name) VALUES (?)", ("القائمة الافتراضية",))
        default_list_id = cur.lastrowid
        default_prices = [
            ("decay", "علاج تسوس", 150, 40),
            ("filled", "حشو", 200, 40),
            ("root_canal", "علاج عصب", 500, 50),
            ("crown", "تركيب تاج", 0, 0),
            ("post", "دعامة", 400, 45),
            ("implant", "زراعة", 3500, 60),
            ("calculus", "إزالة جير", 150, 30),
            ("extracted", "خلع", 100, 40),
        ]
        cur.executemany("""
            INSERT INTO treatment_prices (price_list_id, treatment_key, label, price, commission_percent, color)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(default_list_id, k, l, p, c, DEFAULT_TREATMENT_COLORS.get(k)) for k, l, p, c in default_prices])

        # إذا كانت هناك قائمة قديمة (نسخة أقدم من البرنامج)، نستورد أسعارها الحقيقية فوق الافتراضية
        if needs_price_migration:
            old_rows = cur.execute(
                "SELECT treatment_key, label, price FROM treatment_prices_old").fetchall()
            for key, label, price in old_rows:
                cur.execute("""
                    INSERT INTO treatment_prices (price_list_id, treatment_key, label, price, commission_percent, color)
                    VALUES (?, ?, ?, ?, 0, ?)
                    ON CONFLICT(price_list_id, treatment_key)
                    DO UPDATE SET price = excluded.price, label = excluded.label
                """, (default_list_id, key, label, price, DEFAULT_TREATMENT_COLORS.get(key)))

    if needs_price_migration:
        cur.execute("DROP TABLE IF EXISTS treatment_prices_old")

    # ترقية: نتأكد أن كل قوائم الأسعار الموجودة تحتوي على أنواع العلاج الجديدة (دعامة/جير)
    # ولون افتراضي لأي صف ليس له لون بعد
    all_lists = cur.execute("SELECT id FROM price_lists").fetchall()
    for (list_id,) in all_lists:
        for key, default_label in [("post", "دعامة"), ("calculus", "إزالة جير")]:
            exists = cur.execute(
                "SELECT 1 FROM treatment_prices WHERE price_list_id = ? AND treatment_key = ?",
                (list_id, key)).fetchone()
            if not exists:
                cur.execute("""
                    INSERT INTO treatment_prices (price_list_id, treatment_key, label, price, commission_percent, color)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (list_id, key, default_label, 0, 0, DEFAULT_TREATMENT_COLORS.get(key)))
        # تلوين أي صفوف قديمة من دون لون محدد
        rows_no_color = cur.execute(
            "SELECT treatment_key FROM treatment_prices WHERE price_list_id = ? AND (color IS NULL OR color = '')",
            (list_id,)).fetchall()
        for (tkey,) in rows_no_color:
            fallback_color = DEFAULT_TREATMENT_COLORS.get(tkey, "#1E88E5")
            cur.execute(
                "UPDATE treatment_prices SET color = ? WHERE price_list_id = ? AND treatment_key = ?",
                (fallback_color, list_id, tkey))

    # نتأكد أن هناك قائمة أسعار فعّالة محدَّدة في الإعدادات
    row = cur.execute("SELECT active_price_list_id FROM clinic_settings WHERE id = 1").fetchone()
    if row and row[0] is None:
        first_list = cur.execute("SELECT id FROM price_lists ORDER BY id LIMIT 1").fetchone()
        if first_list:
            cur.execute("UPDATE clinic_settings SET active_price_list_id = ? WHERE id = 1",
                        (first_list[0],))

    # الأنواع الفرعية/الخامات لكل بند معالجة (مثلاً تحت "تركيب تاج": زيركونيا، بورسلين، إيماكس...)
    # كل نوع فرعي له سعره ولونه الخاص، ومرتبط بقائمة أسعار معينة زي البند الأساسي
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treatment_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price_list_id INTEGER NOT NULL,
            treatment_key TEXT NOT NULL,
            variant_name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            commission_percent REAL NOT NULL DEFAULT 0,
            color TEXT,
            FOREIGN KEY (price_list_id) REFERENCES price_lists(id) ON DELETE CASCADE
        )
    """)

    # ترقية: البند الأساسي "تركيب تاج/طربوش" ملوش سعر أو لون افتراضي بقى -
    # السعر أصبح مقتصرًا على الأنواع الفرعية الخاصة به. وبشكل عام، أي بند علاجي
    # أصبحت له أنواع فرعية معرَّفة، يُصفَّر سعره ولونه الأساسي أيضًا لأن السعر
    # الحقيقي أصبح داخل الأنواع الفرعية فقط
    cur.execute("""
        UPDATE treatment_prices SET price = 0, color = NULL
        WHERE treatment_key = 'crown'
           OR treatment_key IN (SELECT DISTINCT treatment_key FROM treatment_variants)
    """)

    # سجل المعالجات التي تمت فعليًا لكل مريض (تاريخ كامل، وليس فقط الحالة الحالية)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treatment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            tooth_number INTEGER,
            treatment_key TEXT,
            treatment_label TEXT,
            price REAL NOT NULL DEFAULT 0,
            treatment_date TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    cur.execute("PRAGMA table_info(treatment_records)")
    tr_cols = {row[1] for row in cur.fetchall()}
    tr_new_cols = {
        "doctor_name": "TEXT",
        "commission_percent": "REAL NOT NULL DEFAULT 0",
        "commission_amount": "REAL NOT NULL DEFAULT 0",
        "surfaces": "TEXT",
        "variant_name": "TEXT",
        "variant_color": "TEXT",
        # جدول سجل المعالجات الجديد (شكل إكسيل) - خصم على مستوى كل معالجة
        # ومبلغ مدفوع مُدخَل يدويًا (لسه مش مربوط فعليًا بحساب المريض/transactions،
        # ده هيتضاف لاحقًا؛ حاليًا حقل مستقل بيتسجل جنب السجل بس)
        "discount_amount": "REAL NOT NULL DEFAULT 0",
        "discount_percent": "REAL NOT NULL DEFAULT 0",
        "paid_amount": "REAL NOT NULL DEFAULT 0",
    }
    for col, definition in tr_new_cols.items():
        if col not in tr_cols:
            cur.execute(f"ALTER TABLE treatment_records ADD COLUMN {col} {definition}")

    # حساب المريض (المستحقات والمدفوعات)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            tx_type TEXT NOT NULL CHECK (tx_type IN ('charge', 'payment')),
            amount REAL NOT NULL,
            description TEXT,
            tx_date TEXT NOT NULL,
            related_treatment_id INTEGER,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)
    # تتبُّع رسالة الشكر التلقائية اللي بتتبعت فور تسجيل دفعة مالية (تخص صفوف
    # الدفعات tx_type='payment' بس - باقي الصفوف "charge" بتفضل قيمتها 0 من غير استخدام)
    cur.execute("PRAGMA table_info(transactions)")
    tx_cols = {row[1] for row in cur.fetchall()}
    if "thank_you_sent" not in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN thank_you_sent INTEGER NOT NULL DEFAULT 0")

    # زيارات المتابعة (ملاحظات كل زيارة)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            visit_date TEXT NOT NULL,
            notes TEXT,
            doctor_name TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)
    visits_cols = {r[1] for r in cur.execute("PRAGMA table_info(visits)").fetchall()}
    if "doctor_name" not in visits_cols:
        cur.execute("ALTER TABLE visits ADD COLUMN doctor_name TEXT")

    # ملفات المريض (صور، أشعة، مستندات) - بدون حد أقصى
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            title TEXT,
            added_date TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    # الموردين
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            notes TEXT
        )
    """)

    # أرقام تليفونات العيادة (ممكن أكتر من رقم)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clinic_phones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT NOT NULL
        )
    """)

    # العاملون الذين ليس لهم حساب دخول في البرنامج (مساعدو أطباء/خدمات مساعدة)
    # - عكس الأطباء والسكرتارية اللي ليهم حساب فعلي في جدول users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_type TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            notes TEXT,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    cur.execute("PRAGMA table_info(support_staff)")
    support_cols = {row[1] for row in cur.fetchall()}
    support_new_cols = {
        "specialty": "TEXT", "work_days": "TEXT",
        "birth_date": "TEXT", "address": "TEXT",
        "photo_path": "TEXT", "national_id": "TEXT", "national_id_photo_path": "TEXT",
        "salary": "REAL NOT NULL DEFAULT 0",
        "income_percent": "REAL NOT NULL DEFAULT 0",
        "start_date": "TEXT",
        "annual_raise_percent": "REAL NOT NULL DEFAULT 0",
    }
    for col, definition in support_new_cols.items():
        if col not in support_cols:
            cur.execute(f"ALTER TABLE support_staff ADD COLUMN {col} {definition}")

    # تخزين عام لأي "شكل واجهة" المستخدم عدّله بنفسه (بالسحب والإزاحة) -
    # زي ترتيب ومقاسات حقول فورم بيانات المريض
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ui_layouts (
            layout_key TEXT PRIMARY KEY,
            layout_json TEXT NOT NULL
        )
    """)

    # أرقام تليفونات إضافية للمريض (منها رقم واتساب مخصوص لاستخدامه لاحقًا
    # مع ربط البرنامج بواتساب)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_phones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            phone_number TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT 'آخر',
            is_whatsapp INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    # قوالب رسائل جاهزة (تأكيد موعد، تهنئة، إلخ) - نص به حقول فارغة تُملأ تلقائيًا
    # تلقائي لكل مريض ({name}, {date}, {time}, {doctor}, {clinic_name})
    cur.execute("""
        CREATE TABLE IF NOT EXISTS message_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            template_text TEXT NOT NULL,
            template_type TEXT NOT NULL DEFAULT 'appointment_reminder'
        )
    """)
    cur.execute("SELECT COUNT(*) FROM message_templates WHERE template_type = 'appointment_reminder'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO message_templates (name, template_text, template_type) VALUES (?, ?, ?)
        """, (
            "تذكير موعد افتراضي",
            "مرحبًا {name} 🌟\n"
            "بنذكّرك بموعدك في {clinic_name} يوم {date} الساعة {time}.\n"
            "لو محتاج تأجيل أو عندك أي استفسار، كلمنا.\n"
            "في انتظارك ❤️",
            "appointment_reminder",
        ))

    # قالب افتراضي لرسالة تأكيد الحجز التي تُرسَل فورًا لحظة تسجيل الموعد
    cur.execute("SELECT COUNT(*) FROM message_templates WHERE template_type = 'booking_confirmation'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO message_templates (name, template_text, template_type) VALUES (?, ?, ?)
        """, (
            "رسالة تأكيد حجز افتراضية",
            "أهلًا بك يا {name} 🌷\n"
            "تم تأكيد حجز موعدك في {clinic_name} يوم {day_name} الموافق {date}"
            " الساعة {time} مع د. {doctor}.\n"
            "في انتظارك، ولو احتجت أي تعديل تقدر تتواصل معانا 🌟",
            "booking_confirmation",
        ))

    # قالب افتراضي لرسالة الشكر التي تُرسَل تلقائيًا بعد انتهاء الموعد الفعلي بساعتين
    cur.execute("SELECT COUNT(*) FROM message_templates WHERE template_type = 'thank_you'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO message_templates (name, template_text, template_type) VALUES (?, ?, ?)
        """, (
            "رسالة شكر افتراضية",
            "شكرًا لك يا {name} 🌷\n"
            "يسعدنا ثقتك في {clinic_name} وفي متابعة د. {doctor} لحالتك.\n"
            "نتمنى لك دوام الصحة والعافية، ونحن دائمًا في خدمتك 🌟",
            "thank_you",
        ))

    # مصروفات العيادة (خامات، مرتبات، خدمات، صيانة...)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT NOT NULL,
            supplier_id INTEGER,
            notes TEXT,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
        )
    """)

    # أيام إجازة محددة بعينها (غير الإجازة الأسبوعية الثابتة)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday_date TEXT UNIQUE NOT NULL,
            note TEXT
        )
    """)

    # ---------------- المعامل (Labs) ----------------

    # بيانات المعامل نفسها (اسم المعمل، تليفون، عنوان، الشخص المسؤول اللي
    # بيستلم الشغل هناك افتراضيًا)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS labs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            contact_person TEXT,
            notes TEXT,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    # حالات/طلبات الشغل المرسلة للمعمل - كل حالة مرتبطة (لو حصلت من شارت
    # الأسنان تلقائيًا) بسجل معالجة معيّن لمريض معيّن وسن معيّن
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lab_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lab_id INTEGER NOT NULL,
            patient_id INTEGER,
            treatment_record_id INTEGER,
            tooth_number INTEGER,
            treatment_key TEXT,
            treatment_label TEXT,
            variant_name TEXT,
            lab_code TEXT,
            status TEXT NOT NULL DEFAULT 'sent'
                CHECK (status IN ('sent', 'in_progress', 'received', 'delivered', 'cancelled')),
            sent_date TEXT,
            expected_date TEXT,
            received_date TEXT,
            delivered_date TEXT,
            sent_by TEXT,
            received_by TEXT,
            cost REAL NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE SET NULL,
            FOREIGN KEY (treatment_record_id) REFERENCES treatment_records(id) ON DELETE SET NULL
        )
    """)

    # حساب كل معمل (المستحق عليه/له) - نفس فكرة transactions بتاعة حساب
    # المريض بالظبط بس على مستوى المعمل
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lab_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lab_id INTEGER NOT NULL,
            tx_type TEXT NOT NULL CHECK (tx_type IN ('charge', 'payment')),
            amount REAL NOT NULL DEFAULT 0,
            tx_date TEXT NOT NULL,
            description TEXT,
            related_order_id INTEGER,
            FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE,
            FOREIGN KEY (related_order_id) REFERENCES lab_orders(id) ON DELETE CASCADE
        )
    """)

    # ترقية: إضافة إعدادات المعمل الافتراضي لكل بند علاجي (أساسي وفرعي) -
    # هل البند ده أصلاً محتاج معمل؟ ولو محتاج، معمل مين افتراضيًا؟ ورمز
    # البند عند المعمل (لو بيستخدموا ترقيم/تشفير خاص بيهم)
    for table_name in ("treatment_prices", "treatment_variants"):
        cur.execute(f"PRAGMA table_info({table_name})")
        existing_cols = {row[1] for row in cur.fetchall()}
        lab_new_cols = {
            "requires_lab": "INTEGER NOT NULL DEFAULT 0",
            "default_lab_id": "INTEGER",
            "lab_code": "TEXT",
        }
        for col, definition in lab_new_cols.items():
            if col not in existing_cols:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {definition}")

    # البنود اللي بطبيعتها بتتصنّع في المعمل - نفعّل "يحتاج معمل" ليها
    # تلقائيًا كترقية أولى (المستخدم يقدر يغيّرها بعدين من شاشة المعامل)
    LAB_DEFAULT_TREATMENT_KEYS = ("crown", "post", "implant")
    cur.execute(
        f"""UPDATE treatment_prices SET requires_lab = 1
            WHERE treatment_key IN ({",".join("?" * len(LAB_DEFAULT_TREATMENT_KEYS))})
              AND requires_lab = 0""",
        LAB_DEFAULT_TREATMENT_KEYS)
    cur.execute(
        f"""UPDATE treatment_variants SET requires_lab = 1
            WHERE treatment_key IN ({",".join("?" * len(LAB_DEFAULT_TREATMENT_KEYS))})
              AND requires_lab = 0""",
        LAB_DEFAULT_TREATMENT_KEYS)

    conn.commit()
    conn.close()


# ---------------- إعدادات العيادة ----------------

def get_settings():
    conn = get_connection()
    row = conn.execute("SELECT * FROM clinic_settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def get_effective_settings(user_id=None):
    """بترجع نسخة من إعدادات العيادة العامة (get_settings) بعد ما تُدمج فيها
    أي تخصيصات مظهر شخصية للمستخدم المحدد (ثيم/شكل أزرار/نمط أيقونات/خط) -
    لو المستخدم مختارش تفضيل شخصي لحاجة معينة (يعني العمود NULL عنده)،
    بيفضل ياخد إعداد العيادة العام زي ما هو. من غير user_id، بترجع إعدادات
    العيادة العامة زي ما هي من غير أي تعديل (نفس get_settings تمامًا)"""
    settings = get_settings()
    if not settings or not user_id:
        return settings
    conn = get_connection()
    row = conn.execute(
        "SELECT theme_id, nav_button_style, icon_pattern, "
        "system_font_family, content_font_family FROM users WHERE id = ?",
        (user_id,)).fetchone()
    conn.close()
    if not row:
        return settings
    merged = dict(settings)
    for key in ("theme_id", "nav_button_style", "icon_pattern",
                "system_font_family", "content_font_family"):
        value = row[key]
        if value:
            merged[key] = value
    return merged


def update_settings(clinic_name=None, logo_path=None, primary_color=None, secondary_color=None,
                     system_font_family=None, content_font_family=None,
                     system_font_size=None, content_font_size=None, language=None,
                     require_password=None, clinic_address=None, tax_card_number=None):
    conn = get_connection()
    current = get_settings()
    conn.execute("""
        UPDATE clinic_settings
        SET clinic_name = ?, logo_path = ?, primary_color = ?, secondary_color = ?,
            system_font_family = ?, content_font_family = ?,
            system_font_size = ?, content_font_size = ?, language = ?, require_password = ?,
            clinic_address = ?, tax_card_number = ?
        WHERE id = 1
    """, (
        clinic_name if clinic_name is not None else current["clinic_name"],
        logo_path if logo_path is not None else current["logo_path"],
        primary_color if primary_color is not None else current["primary_color"],
        secondary_color if secondary_color is not None else current["secondary_color"],
        system_font_family if system_font_family is not None else current["system_font_family"],
        content_font_family if content_font_family is not None else current["content_font_family"],
        system_font_size if system_font_size is not None else current["system_font_size"],
        content_font_size if content_font_size is not None else current["content_font_size"],
        language if language is not None else current["language"],
        (1 if require_password else 0) if require_password is not None else current["require_password"],
        clinic_address if clinic_address is not None else current["clinic_address"],
        tax_card_number if tax_card_number is not None else current["tax_card_number"],
    ))
    conn.commit()
    conn.close()


def set_require_password(value):
    """تشغيل/إيقاف طلب كلمة المرور عند تسجيل الدخول (يتحكم فيها المدير من الإعدادات)"""
    conn = get_connection()
    conn.execute("UPDATE clinic_settings SET require_password = ? WHERE id = 1", (1 if value else 0,))
    conn.commit()
    conn.close()


def set_remembered_login(username, remember, password=None):
    """بتحفظ اسم المستخدم وكلمة المرور (لو remember=True) عشان يترشّح
    المستخدم تلقائيًا وتتملى كلمة المرور تلقائيًا في حقلها في المرة الجاية.
    لو remember=False بتلغي التذكير وتمسح البيانات المحفوظة كلها"""
    conn = get_connection()
    conn.execute(
        "UPDATE clinic_settings SET remember_login = ?, remembered_username = ?, remembered_password = ? "
        "WHERE id = 1",
        (1 if remember else 0, username if remember else None, password if remember else None)
    )
    conn.commit()
    conn.close()


def set_setting_value(column_name, value):
    """تحديث عمود واحد بس في جدول الإعدادات - دالة عامة تُستخدم لأي إعداد
    بسيط (رقم/نص) مالوش دالة مخصصة له. ملحوظة: column_name لازم يكون اسم
    عمود حقيقي موجود بالفعل في الجدول (بيُستخدم من كود داخلي بس، مش من
    مدخلات المستخدم مباشرة) عشان مفيش تحقق إضافي هنا"""
    conn = get_connection()
    conn.execute(f"UPDATE clinic_settings SET {column_name} = ? WHERE id = 1", (value,))
    conn.commit()
    conn.close()


def set_theme(theme_id):
    """بتحفظ الثيم المختار، وكمان تحدّث primary_color/secondary_color في
    نفس الوقت عشان أي كود قديم بيقرا الألوان دي مباشرة من الإعدادات (زي
    شريط التنقل العلوي) يفضل شغال متوافق مع الثيم الجديد من غير ما نلمسه"""
    import theme as _theme
    preset = _theme.THEME_PRESETS.get(theme_id)
    if not preset:
        return
    conn = get_connection()
    conn.execute(
        "UPDATE clinic_settings SET theme_id = ?, primary_color = ?, secondary_color = ? WHERE id = 1",
        (theme_id, preset["primary"], preset["secondary"]))
    conn.commit()
    conn.close()


def set_nav_button_style(style_id):
    """بتحفظ تصميم أزرار الشريط العلوي المختار (classic / glass / luxury)"""
    conn = get_connection()
    conn.execute("UPDATE clinic_settings SET nav_button_style = ? WHERE id = 1", (style_id,))
    conn.commit()
    conn.close()


def set_icon_pattern(pattern_id):
    """بتحفظ نمط رسم أيقونات الشريط العلوي المختار (outline / filled / bold) -
    ده شكل الرسمة نفسها، مستقل تمامًا عن nav_button_style"""
    conn = get_connection()
    conn.execute("UPDATE clinic_settings SET icon_pattern = ? WHERE id = 1", (pattern_id,))
    conn.commit()
    conn.close()


# ---------------- تخصيصات المظهر الشخصية لكل مستخدم ----------------
# نفس فكرة set_theme/set_nav_button_style/set_icon_pattern فوق بالظبط، لكن
# بتحفظ في صف المستخدم نفسه في جدول users بدل صف العيادة العام، عشان كل
# مستخدم يقدر يخصّص شكل البرنامج زي ما يريحه من غير ما يأثر على غيره لو
# أكتر من شخص بيستخدموا نفس الجهاز

def set_user_theme(user_id, theme_id):
    conn = get_connection()
    conn.execute("UPDATE users SET theme_id = ? WHERE id = ?", (theme_id, user_id))
    conn.commit()
    conn.close()


def set_user_nav_button_style(user_id, style_id):
    conn = get_connection()
    conn.execute("UPDATE users SET nav_button_style = ? WHERE id = ?", (style_id, user_id))
    conn.commit()
    conn.close()


def set_user_icon_pattern(user_id, pattern_id):
    conn = get_connection()
    conn.execute("UPDATE users SET icon_pattern = ? WHERE id = ?", (pattern_id, user_id))
    conn.commit()
    conn.close()


def set_user_fonts(user_id, system_font_family=None, content_font_family=None):
    conn = get_connection()
    current = conn.execute(
        "SELECT system_font_family, content_font_family FROM users WHERE id = ?",
        (user_id,)).fetchone()
    conn.execute(
        "UPDATE users SET system_font_family = ?, content_font_family = ? WHERE id = ?",
        (system_font_family if system_font_family is not None else current["system_font_family"],
         content_font_family if content_font_family is not None else current["content_font_family"],
         user_id))
    conn.commit()
    conn.close()


def reset_user_appearance(user_id):
    """بتمسح كل التخصيصات الشخصية للمستخدم وترجّعه يستخدم إعدادات مظهر
    العيادة العامة تاني (زي ما كان قبل ما يخصص أي حاجة لنفسه)"""
    conn = get_connection()
    conn.execute("""
        UPDATE users
        SET theme_id = NULL, nav_button_style = NULL, icon_pattern = NULL,
            system_font_family = NULL, content_font_family = NULL
        WHERE id = ?
    """, (user_id,))
    conn.commit()
    conn.close()


def set_show_ribbon_labels(value):
    """تشغيل/إيقاف إظهار المسمى النصي (اسم الصفحة) تحت أيقونات الشريط
    العلوي. لو متوقفة، بتظهر الأيقونة لوحدها من غير كتابة"""
    conn = get_connection()
    conn.execute("UPDATE clinic_settings SET show_ribbon_labels = ? WHERE id = 1", (1 if value else 0,))
    conn.commit()
    conn.close()


def set_mini_calendar_width(width):
    """بتحفظ عرض الكالندر الشهري الصغير اللي على اليمين في صفحة المواعيد"""
    conn = get_connection()
    conn.execute("UPDATE clinic_settings SET mini_calendar_width = ? WHERE id = 1", (int(width),))
    conn.commit()
    conn.close()


def get_weekly_holidays():
    """بترجع مجموعة أرقام أيام الأسبوع اللي إجازة ثابتة (0=الاثنين ... 6=الأحد، زي date.weekday())"""
    settings = get_settings()
    raw = settings["weekly_holidays"] or ""
    return {int(x) for x in raw.split(",") if x.strip().isdigit()}


def set_weekly_holidays(weekday_numbers):
    """بتحفظ أيام الأسبوع اللي هتبقى إجازة ثابتة كل أسبوع (لستة أرقام من 0 لـ 6)"""
    conn = get_connection()
    value = ",".join(str(n) for n in sorted(set(weekday_numbers)))
    conn.execute("UPDATE clinic_settings SET weekly_holidays = ? WHERE id = 1", (value,))
    conn.commit()
    conn.close()


def get_holiday_dates():
    """بترجع مجموعة التواريخ (كنصوص YYYY-MM-DD) اللي اتحددت كإجازة بعينها"""
    conn = get_connection()
    rows = conn.execute("SELECT holiday_date FROM holidays").fetchall()
    conn.close()
    return {r["holiday_date"] for r in rows}


def add_holiday_date(holiday_date, note=None):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO holidays (holiday_date, note) VALUES (?, ?)",
                 (holiday_date, note))
    conn.commit()
    conn.close()


def remove_holiday_date(holiday_date):
    conn = get_connection()
    conn.execute("DELETE FROM holidays WHERE holiday_date = ?", (holiday_date,))
    conn.commit()
    conn.close()


def set_schedule_hours(start_hour, end_hour):
    """تحفظ نطاق الساعات المتاحة في صفحة المواعيد (المدير وحده يمكنه تغييرها)"""
    start_hour = max(0, min(int(start_hour), 23))
    end_hour = max(start_hour + 1, min(int(end_hour), 24))
    conn = get_connection()
    conn.execute("UPDATE clinic_settings SET schedule_start_hour = ?, schedule_end_hour = ? WHERE id = 1",
                 (start_hour, end_hour))
    conn.commit()
    conn.close()


def is_holiday(d):
    """d: كائن date. تُعيد True إذا كان هذا اليوم إجازة (سواء إجازة أسبوعية ثابتة أو يوم مُحدَّد بمفرده)"""
    if d.weekday() in get_weekly_holidays():
        return True
    return d.isoformat() in get_holiday_dates()


# ---------------- المرضى ----------------

def add_patient(full_name, phone="", birth_date="", gender="", address="", medical_notes="",
                 allergies="", occupation="", family_id="", nationality=""):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO patients (full_name, phone, birth_date, gender, address, medical_notes,
                               allergies, occupation, family_id, nationality, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (full_name, phone, birth_date, gender, address, medical_notes, allergies,
          occupation, family_id or None, nationality, datetime.now().strftime("%Y-%m-%d %H:%M")))
    patient_id = cur.lastrowid
    conn.commit()
    conn.close()

    # أول ما يتعمل ملف مريض جديد وعنده تاريخ ميلاد، بنولّد له تلقائيًا
    # خريطة أسنان مبدئية تتناسب مع عمره بناءً على الجدول الزمني العالمي
    # للتسنين (أي سن دائم لسه معاهوش بيبان "لبني موجود" أو "لم يبزغ بعد"
    # حسب الحالة الطبيعية لعمره، وأي تعديل بعد كده من الطبيب بيتفضّل عليها)
    if birth_date:
        try:
            generate_age_based_tooth_chart(patient_id, birth_date)
        except Exception:
            pass
    return patient_id


def update_patient(patient_id, **fields):
    if not fields:
        return
    conn = get_connection()
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [patient_id]
    conn.execute(f"UPDATE patients SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()

    # لو اتضاف/اتصحح تاريخ الميلاد بعد إنشاء الملف ولسه مفيش خريطة أسنان
    # اتولدت خالص للمريض ده (يعني ملفه اتعمل من غير تاريخ ميلاد وقتها)،
    # نولّدها له دلوقتي تلقائيًا - من غير ما نلمس أي خريطة موجودة فعلاً
    new_birth_date = fields.get("birth_date")
    if new_birth_date and not get_tooth_presence(patient_id):
        try:
            generate_age_based_tooth_chart(patient_id, new_birth_date)
        except Exception:
            pass


def delete_patient(patient_id):
    conn = get_connection()
    conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()


def get_all_patients(search=""):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM patients ORDER BY full_name").fetchall()
    conn.close()
    patients = [dict(r) for r in rows]

    search = (search or "").strip()
    if not search:
        return patients

    search_lower = search.lower()
    results = []
    for p in patients:
        haystack_parts = [
            p.get("full_name") or "",
            p.get("phone") or "",
            p.get("occupation") or "",
            p.get("address") or "",
            p.get("nationality") or "",
            str(p.get("id") or ""),
            f"{p.get('id', 0):06d}",
        ]
        age = calculate_age(p.get("birth_date"))
        if age is not None:
            haystack_parts.append(str(age))
        haystack = " ".join(haystack_parts).lower()
        if search_lower in haystack:
            results.append(p)
    return results


def get_family_members(family_id, exclude_patient_id=None):
    if not family_id:
        return []
    conn = get_connection()
    if exclude_patient_id:
        rows = conn.execute(
            "SELECT * FROM patients WHERE family_id = ? AND id != ? ORDER BY full_name",
            (family_id, exclude_patient_id)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM patients WHERE family_id = ? ORDER BY full_name", (family_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_family_ids():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT family_id FROM patients WHERE family_id IS NOT NULL AND family_id != '' "
        "ORDER BY family_id").fetchall()
    conn.close()
    return [r[0] for r in rows]


def set_profile_photo(patient_id, file_path):
    conn = get_connection()
    conn.execute("UPDATE patients SET profile_photo_path = ? WHERE id = ?", (file_path, patient_id))
    conn.commit()
    conn.close()


# ---------------- ملفات المريض (صور/أشعة/مستندات) ----------------

def add_patient_file(patient_id, file_path, title="", added_date=None):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO patient_files (patient_id, file_path, title, added_date)
        VALUES (?, ?, ?, ?)
    """, (patient_id, file_path, title, added_date or datetime.now().strftime("%Y-%m-%d")))
    file_id = cur.lastrowid
    conn.commit()
    conn.close()
    return file_id


def get_patient_files(patient_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM patient_files WHERE patient_id = ? ORDER BY added_date DESC, id DESC",
        (patient_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_patient_file(file_id):
    conn = get_connection()
    row = conn.execute("SELECT file_path FROM patient_files WHERE id = ?", (file_id,)).fetchone()
    conn.execute("DELETE FROM patient_files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
    return row["file_path"] if row else None


def get_patient(patient_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def calculate_age(birth_date_iso):
    """بتحسب السن بالسنين من تاريخ ميلاد بصيغة YYYY-MM-DD. بترجع None لو التاريخ فاضي/غلط"""
    if not birth_date_iso:
        return None
    try:
        y, m, d = map(int, str(birth_date_iso).split("-"))
        born = _dt_date(y, m, d)
        today = _dt_date.today()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return age if age >= 0 else None
    except Exception:
        return None


def calculate_current_salary(base_salary, start_date_iso, annual_raise_percent):
    """تحسب المرتب الثابت الحالي بعد تطبيق نسبة الزيادة السنوية تلقائيًا عن
    كل سنة كاملة مرّت من تاريخ استلام العمل - تُطبَّق الزيادة على الأجر الثابت
    فقط (وليس على نسبة الطبيب من الدخل، لأنها نسبة من الإيراد وليست رقمًا ثابتًا)"""
    base_salary = base_salary or 0
    if not base_salary or not start_date_iso or not annual_raise_percent:
        return round(base_salary, 2)
    try:
        y, m, d = map(int, str(start_date_iso).split("-"))
        start = _dt_date(y, m, d)
    except Exception:
        return round(base_salary, 2)
    today = _dt_date.today()
    years_completed = today.year - start.year - ((today.month, today.day) < (start.month, start.day))
    years_completed = max(years_completed, 0)
    current = base_salary * ((1 + annual_raise_percent / 100) ** years_completed)
    return round(current, 2)


# ---------------- مخطط الأسنان ----------------

def set_tooth_status(patient_id, tooth_number, status, notes=""):
    """محتفظين بيها للتوافق - بتحدّث الحالة والملاحظة مع بعض، وبتعتبر
    الحالة دي تعديل يدوي (auto_generated=0)"""
    conn = get_connection()
    conn.execute("""
        INSERT INTO tooth_chart (patient_id, tooth_number, status, notes, auto_generated, updated_at)
        VALUES (?, ?, ?, ?, 0, ?)
        ON CONFLICT(patient_id, tooth_number)
        DO UPDATE SET status = excluded.status, notes = excluded.notes,
                      auto_generated = 0, updated_at = excluded.updated_at
    """, (patient_id, tooth_number, status, notes, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()


def get_tooth_chart(patient_id):
    """بيرجع dict: {tooth_number: {'status':.., 'notes':..}}"""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tooth_chart WHERE patient_id = ?", (patient_id,)).fetchall()
    conn.close()
    return {r["tooth_number"]: {"status": r["status"], "notes": r["notes"]} for r in rows}


def set_tooth_note(patient_id, tooth_number, note):
    """ملاحظة حرة على السن (منفصلة عن حالة البزوغ ورموز العلاجات) - بتحافظ
    على حالة البزوغ المسجلة زي ما هي (مش بتصفّرها لـ'healthy')"""
    conn = get_connection()
    conn.execute("""
        INSERT INTO tooth_chart (patient_id, tooth_number, status, notes, updated_at)
        VALUES (?, ?, 'healthy', ?, ?)
        ON CONFLICT(patient_id, tooth_number)
        DO UPDATE SET notes = excluded.notes, updated_at = excluded.updated_at
    """, (patient_id, tooth_number, note, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()


def get_tooth_notes(patient_id):
    """تُعيد dict: {tooth_number: note_text} للأسنان التي لها ملاحظة فقط"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tooth_number, notes FROM tooth_chart WHERE patient_id = ? AND notes IS NOT NULL AND notes != ''",
        (patient_id,)).fetchall()
    conn.close()
    return {r["tooth_number"]: r["notes"] for r in rows}


# ---------------- حالة بزوغ السن (odontogram presence) ----------------

def get_tooth_presence(patient_id):
    """بترجع dict: {tooth_number: {'status':.., 'auto': bool, 'notes':..}}
    لكل الأسنان اللي ليها حالة بزوغ محفوظة (سواء متولدة تلقائيًا من جدول
    التسنين أو محددة يدويًا من الطبيب). القيمة القديمة 'healthy' بتترجم
    تلقائيًا لـ'present' (نفس المعنى، اسم أوضح)"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tooth_number, status, auto_generated, notes FROM tooth_chart WHERE patient_id = ?",
        (patient_id,)).fetchall()
    conn.close()
    result = {}
    for r in rows:
        status = r["status"] or "present"
        if status == "healthy":
            status = "present"
        result[r["tooth_number"]] = {
            "status": status, "auto": bool(r["auto_generated"]), "notes": r["notes"]}
    return result


def set_tooth_presence(patient_id, tooth_number, status, auto=False):
    """يحفظ/يحدّث حالة بزوغ سن معين (موجود / لبني لم يسقط / لم يبزغ بعد /
    مفقود / مطمور) من غير ما يمسح أي ملاحظة حرة مكتوبة على نفس السن.
    auto=True تعني الحالة دي متولدة تلقائيًا من جدول التسنين (ممكن تتحدث
    لاحقًا تلقائيًا)، وauto=False تعني الطبيب حددها يدويًا (بتفضل زي ما هي
    ومحدّش هيغيّرها تلقائيًا تاني إلا لو الطبيب نفسه غيّرها)"""
    conn = get_connection()
    conn.execute("""
        INSERT INTO tooth_chart (patient_id, tooth_number, status, auto_generated, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(patient_id, tooth_number)
        DO UPDATE SET status = excluded.status, auto_generated = excluded.auto_generated,
                      updated_at = excluded.updated_at
    """, (patient_id, tooth_number, status, 1 if auto else 0, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()


def generate_age_based_tooth_chart(patient_id, birth_date, variation_months=0, overwrite_manual=False):
    """بيولّد خريطة أسنان مبدئية للمريض بناءً على عمره الحالي بالشهور
    والجدول الزمني العالمي للتسنين (WHO/ADA)، مع هامش "تفاوت طبيعي"
    بالشهور بيوسّع نطاق الأعمار القياسية عشان يراعي اختلاف الأشخاص عن
    المتوسط العالمي. بيتخطى أي سن اتعدّل يدويًا قبل كده (auto_generated=0)
    إلا لو overwrite_manual=True صراحةً، عشان مايبوظش تعديل الطبيب.
    بترجع True لو اتولدت الخريطة فعلاً (يعني تاريخ الميلاد كان صحيح)"""
    age_months = teething_timeline.age_in_months(birth_date)
    if age_months is None:
        return False
    chart = teething_timeline.generate_chart(age_months, variation_months)
    existing = get_tooth_presence(patient_id)
    for tooth_number, status in chart.items():
        prior = existing.get(tooth_number)
        if prior and not prior["auto"] and not overwrite_manual:
            continue
        set_tooth_presence(patient_id, tooth_number, status, auto=True)
    return True


def get_active_tooth_conditions(patient_id):
    """
    تحسب الحالة الحالية الفعلية لكل سن بناءً على تاريخ المعالجات:
    تُعيد dict: {tooth_number: {treatment_key: record_dict}}
    كل "إعادة إلى السليم" تمسح كل الرموز المسجَّلة قبلها لنفس السن (تصفير)،
    وأي معالجة من نفس النوع بعد ذلك تستبدل القديمة (كحشو جديد بدل القديم).
    """
    records = get_treatment_records(patient_id)  # الأحدث أولاً
    records_asc = list(reversed(records))  # نعيدها بترتيب زمني تصاعدي حتى تُطبَّق بشكل صحيح

    per_tooth = {}
    for r in records_asc:
        tooth = r["tooth_number"]
        if tooth is None:
            continue
        if r["treatment_key"] == "healthy":
            per_tooth[tooth] = {}
        else:
            per_tooth.setdefault(tooth, {})
            per_tooth[tooth][r["treatment_key"]] = r
    return per_tooth


# ---------------- المواعيد ----------------

def add_appointment(patient_id, appt_date, appt_time, doctor_name="", status="confirmed",
                     notes="", duration_minutes=30):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO appointments (patient_id, appt_date, appt_time, doctor_name, status, notes, duration_minutes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (patient_id, appt_date, appt_time, doctor_name, status, notes, duration_minutes))
    appt_id = cur.lastrowid
    conn.commit()
    conn.close()
    return appt_id


def update_appointment_status(appt_id, status):
    conn = get_connection()
    conn.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appt_id))
    conn.commit()
    conn.close()


def update_appointment_color(appt_id, color):
    conn = get_connection()
    conn.execute("UPDATE appointments SET color = ? WHERE id = ?", (color, appt_id))
    conn.commit()
    conn.close()


def update_appointment(appt_id, appt_date=None, appt_time=None, duration_minutes=None,
                        doctor_name=None, notes=None):
    """تعديل موعد موجود: الساعة/المدة/اليوم الذي يقع فيه/الطبيب/الملاحظات"""
    conn = get_connection()
    current = conn.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,)).fetchone()
    if not current:
        conn.close()
        return
    conn.execute("""
        UPDATE appointments
        SET appt_date = ?, appt_time = ?, duration_minutes = ?, doctor_name = ?, notes = ?
        WHERE id = ?
    """, (
        appt_date if appt_date is not None else current["appt_date"],
        appt_time if appt_time is not None else current["appt_time"],
        duration_minutes if duration_minutes is not None else current["duration_minutes"],
        doctor_name if doctor_name is not None else current["doctor_name"],
        notes if notes is not None else current["notes"],
        appt_id,
    ))
    conn.commit()
    conn.close()


def update_appointment_details(appt_id, appt_date, appt_time, duration_minutes,
                                doctor_name=None, notes=None):
    """نفس update_appointment، لكن بترتيب معاملات ثابت (تاريخ/وقت/مدة) - مستخدمة
    من نافذة تعديل الموعد في التقويم"""
    update_appointment(appt_id, appt_date=appt_date, appt_time=appt_time,
                        duration_minutes=duration_minutes, doctor_name=doctor_name, notes=notes)


def delete_appointment(appt_id):
    conn = get_connection()
    conn.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
    conn.commit()
    conn.close()


def get_appointments(date_filter=None):
    conn = get_connection()
    if date_filter:
        rows = conn.execute("""
            SELECT appointments.*, patients.full_name, patients.phone
            FROM appointments JOIN patients ON appointments.patient_id = patients.id
            WHERE appt_date = ?
            ORDER BY appt_time
        """, (date_filter,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT appointments.*, patients.full_name, patients.phone
            FROM appointments JOIN patients ON appointments.patient_id = patients.id
            ORDER BY appt_date, appt_time
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------- قوائم الأسعار ----------------

def get_price_lists():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM price_lists ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_price_list(name, copy_from_list_id=None):
    conn = get_connection()
    cur = conn.execute("INSERT INTO price_lists (name) VALUES (?)", (name,))
    new_id = cur.lastrowid
    if copy_from_list_id:
        rows = conn.execute(
            "SELECT treatment_key, label, price, commission_percent, color FROM treatment_prices "
            "WHERE price_list_id = ?", (copy_from_list_id,)).fetchall()
        for r in rows:
            conn.execute("""
                INSERT INTO treatment_prices (price_list_id, treatment_key, label, price, commission_percent, color)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_id, r["treatment_key"], r["label"], r["price"], r["commission_percent"], r["color"]))
        variant_rows = conn.execute(
            "SELECT treatment_key, variant_name, price, commission_percent, color FROM treatment_variants "
            "WHERE price_list_id = ?", (copy_from_list_id,)).fetchall()
        for r in variant_rows:
            conn.execute("""
                INSERT INTO treatment_variants (price_list_id, treatment_key, variant_name, price, commission_percent, color)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_id, r["treatment_key"], r["variant_name"], r["price"], r["commission_percent"], r["color"]))
    conn.commit()
    conn.close()
    return new_id


def delete_price_list(price_list_id):
    conn = get_connection()
    conn.execute("DELETE FROM price_lists WHERE id = ?", (price_list_id,))
    conn.commit()
    conn.close()


def set_active_price_list(price_list_id):
    conn = get_connection()
    conn.execute("UPDATE clinic_settings SET active_price_list_id = ? WHERE id = 1", (price_list_id,))
    conn.commit()
    conn.close()


def get_treatment_prices(price_list_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM treatment_prices WHERE price_list_id = ? ORDER BY label",
        (price_list_id,)).fetchall()
    conn.close()
    return {r["treatment_key"]: dict(r) for r in rows}


def get_price_for(treatment_key, price_list_id=None):
    if price_list_id is None:
        settings = get_settings()
        price_list_id = settings["active_price_list_id"] if settings else None
        if price_list_id is None:
            return None
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM treatment_prices WHERE treatment_key = ? AND price_list_id = ?",
        (treatment_key, price_list_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_treatment_price(price_list_id, treatment_key, label, price, commission_percent=0,
                            color=None, symbol_key=None):
    conn = get_connection()
    if color is None:
        existing = conn.execute(
            "SELECT color FROM treatment_prices WHERE price_list_id = ? AND treatment_key = ?",
            (price_list_id, treatment_key)).fetchone()
        color = existing["color"] if existing and existing["color"] else "#1E88E5"
    if symbol_key is None:
        existing_symbol = conn.execute(
            "SELECT symbol_key FROM treatment_prices WHERE price_list_id = ? AND treatment_key = ?",
            (price_list_id, treatment_key)).fetchone()
        symbol_key = existing_symbol["symbol_key"] if existing_symbol and existing_symbol["symbol_key"] else None
    conn.execute("""
        INSERT INTO treatment_prices (price_list_id, treatment_key, label, price, commission_percent, color, symbol_key)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(price_list_id, treatment_key)
        DO UPDATE SET label = excluded.label, price = excluded.price,
                      commission_percent = excluded.commission_percent, color = excluded.color,
                      symbol_key = excluded.symbol_key
    """, (price_list_id, treatment_key, label, price, commission_percent, color, symbol_key))
    conn.commit()
    conn.close()


def delete_treatment_price(price_list_id, treatment_key):
    conn = get_connection()
    conn.execute("DELETE FROM treatment_prices WHERE price_list_id = ? AND treatment_key = ?",
                 (price_list_id, treatment_key))
    conn.execute("DELETE FROM treatment_variants WHERE price_list_id = ? AND treatment_key = ?",
                 (price_list_id, treatment_key))
    conn.commit()
    conn.close()


# ---------------- الأنواع الفرعية/الخامات لكل بند معالجة ----------------

def get_treatment_variants(price_list_id, treatment_key):
    if not price_list_id:
        return []
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM treatment_variants WHERE price_list_id = ? AND treatment_key = ? ORDER BY variant_name",
        (price_list_id, treatment_key)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_treatment_variants(price_list_id):
    """بترجع كل الأنواع الفرعية لكل بنود قائمة أسعار معينة، متجمعة حسب البند"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM treatment_variants WHERE price_list_id = ? ORDER BY treatment_key, variant_name",
        (price_list_id,)).fetchall()
    conn.close()
    grouped = {}
    for r in rows:
        grouped.setdefault(r["treatment_key"], []).append(dict(r))
    return grouped


def add_treatment_variant(price_list_id, treatment_key, variant_name, price=0, commission_percent=0, color=None):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO treatment_variants (price_list_id, treatment_key, variant_name, price, commission_percent, color)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (price_list_id, treatment_key, variant_name, price, commission_percent, color))
    variant_id = cur.lastrowid
    conn.commit()
    conn.close()
    return variant_id


def update_treatment_variant(variant_id, variant_name, price, commission_percent=0, color=None):
    conn = get_connection()
    conn.execute("""
        UPDATE treatment_variants
        SET variant_name = ?, price = ?, commission_percent = ?, color = ?
        WHERE id = ?
    """, (variant_name, price, commission_percent, color, variant_id))
    conn.commit()
    conn.close()


def delete_treatment_variant(variant_id):
    conn = get_connection()
    conn.execute("DELETE FROM treatment_variants WHERE id = ?", (variant_id,))
    conn.commit()
    conn.close()


# ---------------- سجل المعالجات ----------------

def add_treatment_record(patient_id, tooth_number, treatment_key, treatment_label, price,
                          notes="", treatment_date=None, doctor_name="",
                          commission_percent=0, commission_amount=0, surfaces=None,
                          variant_name=None, variant_color=None):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO treatment_records
            (patient_id, tooth_number, treatment_key, treatment_label, price, treatment_date,
             notes, doctor_name, commission_percent, commission_amount, surfaces,
             variant_name, variant_color)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (patient_id, tooth_number, treatment_key, treatment_label, price,
          treatment_date or datetime.now().strftime("%Y-%m-%d"), notes,
          doctor_name, commission_percent, commission_amount, surfaces,
          variant_name, variant_color))
    record_id = cur.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_treatment_records(patient_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT tr.*,
               (SELECT l.name FROM lab_orders lo
                JOIN labs l ON l.id = lo.lab_id
                WHERE lo.treatment_record_id = tr.id
                ORDER BY lo.id DESC LIMIT 1) AS lab_name
        FROM treatment_records tr
        WHERE tr.patient_id = ?
        ORDER BY tr.treatment_date DESC, tr.id DESC
    """, (patient_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# الأعمدة المسموح تعديلها من جدول \"سجل المعالجات\" (شكل إكسيل) في ملف المريض
TREATMENT_RECORD_EDITABLE_FIELDS = {
    "treatment_date", "treatment_label", "doctor_name", "price",
    "discount_amount", "discount_percent", "paid_amount", "notes",
}


def update_treatment_record_fields(record_id, **fields):
    """تحديث حقل واحد أو أكتر من سجل معالجة (تعديل مباشر من الجدول في ملف المريض).
    بيقبل بس الحقول الموجودة في TREATMENT_RECORD_EDITABLE_FIELDS حماية من تعديل
    حقول حساسة زي patient_id بالغلط."""
    fields = {k: v for k, v in fields.items() if k in TREATMENT_RECORD_EDITABLE_FIELDS}
    if not fields:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [record_id]
    conn.execute(f"UPDATE treatment_records SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_treatment_record(record_id):
    """تحذف سجل المعالجة، وتحذف معه أي حركة مالية (فاتورة) مرتبطة به حتى يبقى الحساب مضبوطًا،
    وأي حالة معمل كانت اتبعتت تلقائيًا بسبب المعالجة دي (وحساباتها في حساب المعمل)"""
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE related_treatment_id = ?", (record_id,))
    lab_order_ids = [r[0] for r in conn.execute(
        "SELECT id FROM lab_orders WHERE treatment_record_id = ?", (record_id,)).fetchall()]
    for order_id in lab_order_ids:
        conn.execute("DELETE FROM lab_transactions WHERE related_order_id = ?", (order_id,))
    conn.execute("DELETE FROM lab_orders WHERE treatment_record_id = ?", (record_id,))
    conn.execute("DELETE FROM treatment_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


# ==================== المعامل (Labs) ====================

# ---------------- بيانات المعامل ----------------

def get_labs(active_only=False):
    conn = get_connection()
    query = "SELECT * FROM labs"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY name"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_lab(lab_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM labs WHERE id = ?", (lab_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_lab(name, phone="", address="", contact_person="", notes=""):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO labs (name, phone, address, contact_person, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (name, phone, address, contact_person, notes))
    lab_id = cur.lastrowid
    conn.commit()
    conn.close()
    return lab_id


def update_lab(lab_id, name, phone="", address="", contact_person="", notes=""):
    conn = get_connection()
    conn.execute("""
        UPDATE labs SET name = ?, phone = ?, address = ?, contact_person = ?, notes = ?
        WHERE id = ?
    """, (name, phone, address, contact_person, notes, lab_id))
    conn.commit()
    conn.close()


def set_lab_active(lab_id, active):
    conn = get_connection()
    conn.execute("UPDATE labs SET active = ? WHERE id = ?", (1 if active else 0, lab_id))
    conn.commit()
    conn.close()


def delete_lab(lab_id):
    conn = get_connection()
    conn.execute("DELETE FROM labs WHERE id = ?", (lab_id,))
    conn.commit()
    conn.close()


# ---------------- حالات/طلبات المعمل ----------------

def add_lab_order(lab_id, patient_id=None, treatment_record_id=None, tooth_number=None,
                   treatment_key=None, treatment_label=None, variant_name=None, lab_code="",
                   status="sent", sent_date=None, expected_date=None, sent_by="", received_by="",
                   cost=0, notes=""):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO lab_orders
            (lab_id, patient_id, treatment_record_id, tooth_number, treatment_key,
             treatment_label, variant_name, lab_code, status, sent_date, expected_date,
             sent_by, received_by, cost, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (lab_id, patient_id, treatment_record_id, tooth_number, treatment_key,
          treatment_label, variant_name, lab_code, status,
          sent_date or datetime.now().strftime("%Y-%m-%d"), expected_date,
          sent_by, received_by, cost, notes))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    if cost:
        _sync_lab_order_charge(order_id)
    return order_id


def _sync_lab_order_charge(order_id):
    """بتزامن حركة الحساب (charge) الخاصة بتكلفة الحالة دي في حساب المعمل - بتتحدث
    تلقائيًا لو اتغيرت التكلفة، وبتتشال لو اتصفرت"""
    conn = get_connection()
    order = conn.execute("SELECT * FROM lab_orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return
    order = dict(order)
    existing = conn.execute(
        "SELECT id FROM lab_transactions WHERE related_order_id = ? AND tx_type = 'charge'",
        (order_id,)).fetchone()
    if order["cost"] and order["cost"] > 0:
        desc = order["treatment_label"] or "شغل معمل"
        if order["variant_name"]:
            desc += f" ({order['variant_name']})"
        if order["tooth_number"]:
            desc += f" - سن {order['tooth_number']}"
        if existing:
            conn.execute("UPDATE lab_transactions SET amount = ?, description = ? WHERE id = ?",
                         (order["cost"], desc, existing["id"]))
        else:
            conn.execute("""
                INSERT INTO lab_transactions (lab_id, tx_type, amount, tx_date, description, related_order_id)
                VALUES (?, 'charge', ?, ?, ?, ?)
            """, (order["lab_id"], order["cost"],
                  order["sent_date"] or datetime.now().strftime("%Y-%m-%d"), desc, order_id))
    elif existing:
        conn.execute("DELETE FROM lab_transactions WHERE id = ?", (existing["id"],))
    conn.commit()
    conn.close()


def update_lab_order(order_id, lab_id=None, tooth_number=None, treatment_label=None,
                      variant_name=None, lab_code=None, status=None, sent_date=None,
                      expected_date=None, received_date=None, delivered_date=None,
                      sent_by=None, received_by=None, cost=None, notes=None):
    conn = get_connection()
    current = conn.execute("SELECT * FROM lab_orders WHERE id = ?", (order_id,)).fetchone()
    if not current:
        conn.close()
        return
    current = dict(current)
    updated = {
        "lab_id": lab_id if lab_id is not None else current["lab_id"],
        "tooth_number": tooth_number if tooth_number is not None else current["tooth_number"],
        "treatment_label": treatment_label if treatment_label is not None else current["treatment_label"],
        "variant_name": variant_name if variant_name is not None else current["variant_name"],
        "lab_code": lab_code if lab_code is not None else current["lab_code"],
        "status": status if status is not None else current["status"],
        "sent_date": sent_date if sent_date is not None else current["sent_date"],
        "expected_date": expected_date if expected_date is not None else current["expected_date"],
        "received_date": received_date if received_date is not None else current["received_date"],
        "delivered_date": delivered_date if delivered_date is not None else current["delivered_date"],
        "sent_by": sent_by if sent_by is not None else current["sent_by"],
        "received_by": received_by if received_by is not None else current["received_by"],
        "cost": cost if cost is not None else current["cost"],
        "notes": notes if notes is not None else current["notes"],
    }
    conn.execute("""
        UPDATE lab_orders SET lab_id = ?, tooth_number = ?, treatment_label = ?, variant_name = ?,
            lab_code = ?, status = ?, sent_date = ?, expected_date = ?, received_date = ?,
            delivered_date = ?, sent_by = ?, received_by = ?, cost = ?, notes = ?
        WHERE id = ?
    """, (updated["lab_id"], updated["tooth_number"], updated["treatment_label"],
          updated["variant_name"], updated["lab_code"], updated["status"], updated["sent_date"],
          updated["expected_date"], updated["received_date"], updated["delivered_date"],
          updated["sent_by"], updated["received_by"], updated["cost"], updated["notes"], order_id))
    conn.commit()
    conn.close()
    _sync_lab_order_charge(order_id)


def set_lab_order_status(order_id, status):
    """بتحدث حالة الطلب، وبتملى تاريخ الاستلام/التسليم تلقائيًا أول ما توصله الحالة دي"""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    if status == "received":
        conn.execute("""UPDATE lab_orders SET status = ?,
                         received_date = COALESCE(received_date, ?) WHERE id = ?""",
                     (status, today, order_id))
    elif status == "delivered":
        conn.execute("""UPDATE lab_orders SET status = ?,
                         received_date = COALESCE(received_date, ?),
                         delivered_date = COALESCE(delivered_date, ?) WHERE id = ?""",
                     (status, today, today, order_id))
    else:
        conn.execute("UPDATE lab_orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


def delete_lab_order(order_id):
    conn = get_connection()
    conn.execute("DELETE FROM lab_transactions WHERE related_order_id = ?", (order_id,))
    conn.execute("DELETE FROM lab_orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()


def get_lab_orders(lab_id=None, status=None, patient_id=None, search=None):
    conn = get_connection()
    query = """
        SELECT lo.*, l.name AS lab_name, p.full_name AS patient_name
        FROM lab_orders lo
        LEFT JOIN labs l ON l.id = lo.lab_id
        LEFT JOIN patients p ON p.id = lo.patient_id
        WHERE 1 = 1
    """
    params = []
    if lab_id:
        query += " AND lo.lab_id = ?"
        params.append(lab_id)
    if status:
        query += " AND lo.status = ?"
        params.append(status)
    if patient_id:
        query += " AND lo.patient_id = ?"
        params.append(patient_id)
    if search:
        query += " AND (p.full_name LIKE ? OR lo.treatment_label LIKE ? OR lo.lab_code LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    query += " ORDER BY lo.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_lab_order(order_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT lo.*, l.name AS lab_name, p.full_name AS patient_name
        FROM lab_orders lo
        LEFT JOIN labs l ON l.id = lo.lab_id
        LEFT JOIN patients p ON p.id = lo.patient_id
        WHERE lo.id = ?
    """, (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------- حساب المعمل (المستحق عليه/له) ----------------

def add_lab_transaction(lab_id, tx_type, amount, description="", tx_date=None):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO lab_transactions (lab_id, tx_type, amount, tx_date, description)
        VALUES (?, ?, ?, ?, ?)
    """, (lab_id, tx_type, amount, tx_date or datetime.now().strftime("%Y-%m-%d"), description))
    tx_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def delete_lab_transaction(tx_id):
    conn = get_connection()
    conn.execute("DELETE FROM lab_transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()


def get_lab_transactions(lab_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM lab_transactions WHERE lab_id = ? ORDER BY tx_date DESC, id DESC",
        (lab_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_lab_balance(lab_id):
    """المبلغ المستحق للمعمل على العيادة (إجمالي التكاليف - إجمالي المدفوع)"""
    conn = get_connection()
    charges = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM lab_transactions WHERE lab_id = ? AND tx_type = 'charge'",
        (lab_id,)).fetchone()[0]
    payments = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM lab_transactions WHERE lab_id = ? AND tx_type = 'payment'",
        (lab_id,)).fetchone()[0]
    conn.close()
    return (charges or 0) - (payments or 0)


def get_all_labs_with_balances():
    labs = get_labs()
    for lab in labs:
        lab["balance"] = get_lab_balance(lab["id"])
        open_orders = get_lab_orders(lab_id=lab["id"])
        lab["open_orders_count"] = sum(
            1 for o in open_orders if o["status"] not in ("delivered", "cancelled"))
    return labs


# ---------------- إعدادات المعمل الافتراضي لكل بند علاجي ----------------

def update_treatment_price_lab_settings(price_list_id, treatment_key, requires_lab,
                                         default_lab_id, lab_code=""):
    conn = get_connection()
    conn.execute("""
        UPDATE treatment_prices SET requires_lab = ?, default_lab_id = ?, lab_code = ?
        WHERE price_list_id = ? AND treatment_key = ?
    """, (1 if requires_lab else 0, default_lab_id, lab_code, price_list_id, treatment_key))
    conn.commit()
    conn.close()


def update_treatment_variant_lab_settings(variant_id, requires_lab, default_lab_id, lab_code=""):
    conn = get_connection()
    conn.execute("""
        UPDATE treatment_variants SET requires_lab = ?, default_lab_id = ?, lab_code = ?
        WHERE id = ?
    """, (1 if requires_lab else 0, default_lab_id, lab_code, variant_id))
    conn.commit()
    conn.close()


def get_treatment_items_with_lab_settings(price_list_id):
    """بترجع كل البنود العلاجية (الأساسية + الأنواع الفرعية) لقائمة أسعار معينة
    مع إعدادات المعمل الخاصة بكل بند - عشان شاشة إعدادات المعامل"""
    conn = get_connection()
    base_rows = conn.execute("""
        SELECT id, treatment_key, NULL AS variant_id, label, requires_lab, default_lab_id, lab_code
        FROM treatment_prices WHERE price_list_id = ? ORDER BY label
    """, (price_list_id,)).fetchall()
    variant_rows = conn.execute("""
        SELECT id, treatment_key, id AS variant_id, variant_name AS label,
               requires_lab, default_lab_id, lab_code
        FROM treatment_variants WHERE price_list_id = ? ORDER BY treatment_key, variant_name
    """, (price_list_id,)).fetchall()
    conn.close()
    items = []
    for r in base_rows:
        d = dict(r)
        d["is_variant"] = False
        items.append(d)
    for r in variant_rows:
        d = dict(r)
        d["is_variant"] = True
        items.append(d)
    return items


def get_doctor_commissions_summary(start_date=None, end_date=None):
    """إجمالي عمولة كل طبيب من كل المرضى، ممكن تحدد فترة تاريخ اختياري"""
    conn = get_connection()
    query = "SELECT doctor_name, COUNT(*) as treatments_count, SUM(commission_amount) as total_commission " \
            "FROM treatment_records WHERE doctor_name IS NOT NULL AND doctor_name != ''"
    params = []
    if start_date:
        query += " AND treatment_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND treatment_date <= ?"
        params.append(end_date)
    query += " GROUP BY doctor_name ORDER BY total_commission DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------- حساب المريض ----------------

def add_transaction(patient_id, tx_type, amount, description="", tx_date=None,
                     related_treatment_id=None):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO transactions (patient_id, tx_type, amount, description, tx_date, related_treatment_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (patient_id, tx_type, amount, description,
          tx_date or datetime.now().strftime("%Y-%m-%d"), related_treatment_id))
    tx_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def delete_transaction(tx_id):
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()


def get_transactions(patient_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE patient_id = ? ORDER BY tx_date DESC, id DESC",
        (patient_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_patient_balance(patient_id):
    conn = get_connection()
    charges = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE patient_id = ? AND tx_type = 'charge'",
        (patient_id,)).fetchone()[0]
    payments = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE patient_id = ? AND tx_type = 'payment'",
        (patient_id,)).fetchone()[0]
    conn.close()
    return {"total_charges": charges, "total_paid": payments, "balance": charges - payments}


# ---------------- زيارات المتابعة ----------------

def add_visit(patient_id, notes, visit_date=None, doctor_name=None):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO visits (patient_id, visit_date, notes, doctor_name) VALUES (?, ?, ?, ?)
    """, (patient_id, visit_date or datetime.now().strftime("%Y-%m-%d"), notes, doctor_name))
    visit_id = cur.lastrowid
    conn.commit()
    conn.close()
    return visit_id


def get_visits(patient_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM visits WHERE patient_id = ? ORDER BY visit_date DESC, id DESC",
        (patient_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_visit(visit_id):
    conn = get_connection()
    conn.execute("DELETE FROM visits WHERE id = ?", (visit_id,))
    conn.commit()
    conn.close()


def update_visit(visit_id, notes, doctor_name=None):
    conn = get_connection()
    conn.execute("UPDATE visits SET notes = ?, doctor_name = ? WHERE id = ?",
                 (notes, doctor_name, visit_id))
    conn.commit()
    conn.close()


def update_visit_fields(visit_id, **fields):
    """تحديث حقل واحد أو أكتر من زيارة معيّنة دفعة واحدة (زي
    update_treatment_record_fields) - مستخدمة في الجدول القابل للتعديل
    المباشر (visits_table.py) عشان تقدر تحدّث أي عمود (تاريخ/طبيب/ملاحظات)
    لوحده من غير ما تحتاج تبعت باقي الحقول"""
    if not fields:
        return
    allowed = {"visit_date", "notes", "doctor_name"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE visits SET {set_clause} WHERE id = ?",
                 (*fields.values(), visit_id))
    conn.commit()
    conn.close()


def get_treatment_records_range(patient_id, start_date, end_date):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM treatment_records
        WHERE patient_id = ? AND treatment_date >= ? AND treatment_date <= ?
        ORDER BY treatment_date, id
    """, (patient_id, start_date, end_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_transactions_range(patient_id, start_date, end_date, tx_type=None):
    conn = get_connection()
    query = "SELECT * FROM transactions WHERE patient_id = ? AND tx_date >= ? AND tx_date <= ?"
    params = [patient_id, start_date, end_date]
    if tx_type:
        query += " AND tx_type = ?"
        params.append(tx_type)
    query += " ORDER BY tx_date, id"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------- المستخدمين والصلاحيات ----------------

ROLE_LABELS = {"manager": "مدير", "doctor": "طبيب", "secretary": "سكرتارية"}

PERMISSION_LABELS = {
    "view_patients": "عرض المرضى",
    "edit_patients": "إضافة/تعديل المرضى",
    "view_appointments": "عرض المواعيد",
    "edit_appointments": "إضافة/تعديل المواعيد",
    "view_accounts": "عرض حسابات المرضى",
    "edit_accounts": "تعديل حسابات المرضى (دفعات/خصومات)",
    "manage_prices": "إدارة قوائم الأسعار",
    "manage_settings": "إدارة إعدادات العيادة",
    "manage_users": "إدارة المستخدمين والصلاحيات",
    "manage_expenses": "إدارة الخامات والمصروفات والموردين",
    "view_clinic_accounts": "عرض تقرير حسابات العيادة (الإيرادات/المصروفات)",
    "manage_staff": "إدارة العاملين (أطباء/مساعدين/سكرتارية/خدمات مساعدة)",
    "manage_whatsapp": "إرسال رسائل واتساب وإدارة القوالب",
    "manage_labs": "إدارة المعامل (الحالات المرسلة/الحسابات/الإعدادات)",
}


def authenticate_user(username, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ? AND active = 1",
        (username, password)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_doctors():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM users WHERE role = 'doctor' AND active = 1 ORDER BY full_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_user(username, password, full_name, role, phone="", specialty="", work_days=""):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO users (username, password, full_name, role, phone, specialty, work_days)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username, password, full_name, role, phone, specialty, work_days))
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def update_user(user_id, **fields):
    if not fields:
        return
    conn = get_connection()
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    conn.execute(f"UPDATE users SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()


def deactivate_user(user_id):
    conn = get_connection()
    conn.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_role_permissions(role):
    conn = get_connection()
    rows = conn.execute(
        "SELECT permission_key, allowed FROM role_permissions WHERE role = ?", (role,)).fetchall()
    conn.close()
    return {r["permission_key"]: bool(r["allowed"]) for r in rows}


def has_permission(role, permission_key):
    if role == "manager":
        return True  # المدير لديه كل الصلاحيات دائمًا
    perms = get_role_permissions(role)
    return perms.get(permission_key, False)


def set_role_permission(role, permission_key, allowed):
    conn = get_connection()
    conn.execute("""
        INSERT INTO role_permissions (role, permission_key, allowed) VALUES (?, ?, ?)
        ON CONFLICT(role, permission_key) DO UPDATE SET allowed = excluded.allowed
    """, (role, permission_key, 1 if allowed else 0))
    conn.commit()
    conn.close()


def get_full_permissions_matrix():
    """بيرجع dict: {role: {permission_key: bool}}"""
    matrix = {}
    for role in ["manager", "doctor", "secretary"]:
        matrix[role] = get_role_permissions(role)
    return matrix


# ---------------- الموردين ----------------

def add_supplier(name, phone="", notes=""):
    conn = get_connection()
    cur = conn.execute("INSERT INTO suppliers (name, phone, notes) VALUES (?, ?, ?)",
                        (name, phone, notes))
    supplier_id = cur.lastrowid
    conn.commit()
    conn.close()
    return supplier_id


def get_suppliers():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_supplier(supplier_id):
    conn = get_connection()
    conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    conn.commit()
    conn.close()


# ---------------- المصروفات ----------------

EXPENSE_CATEGORIES = ["مستهلكات", "خامات", "مرتبات", "كهرباء ومرافق", "صيانة", "إيجار", "أخرى"]


def add_expense(category, item_name, amount, expense_date=None, supplier_id=None, notes=""):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO expenses (category, item_name, amount, expense_date, supplier_id, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (category, item_name, amount, expense_date or datetime.now().strftime("%Y-%m-%d"),
          supplier_id, notes))
    expense_id = cur.lastrowid
    conn.commit()
    conn.close()
    return expense_id


def delete_expense(expense_id):
    conn = get_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def get_expenses(start_date=None, end_date=None, category=None):
    conn = get_connection()
    query = """
        SELECT expenses.*, suppliers.name as supplier_name
        FROM expenses LEFT JOIN suppliers ON expenses.supplier_id = suppliers.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND expense_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND expense_date <= ?"
        params.append(end_date)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY expense_date DESC, expenses.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expenses_by_category(start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT category, SUM(amount) as total FROM expenses WHERE 1=1"
    params = []
    if start_date:
        query += " AND expense_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND expense_date <= ?"
        params.append(end_date)
    query += " GROUP BY category ORDER BY total DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------- حسابات العيادة الإجمالية (إيرادات/مصروفات/ربح) ----------------

def get_clinic_financials(start_date, end_date):
    conn = get_connection()
    revenue = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) FROM transactions
        WHERE tx_type = 'payment' AND tx_date >= ? AND tx_date <= ?
    """, (start_date, end_date)).fetchone()[0]

    total_expenses = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) FROM expenses
        WHERE expense_date >= ? AND expense_date <= ?
    """, (start_date, end_date)).fetchone()[0]

    conn.close()
    return {
        "revenue": revenue,
        "expenses": total_expenses,
        "profit": revenue - total_expenses,
    }


# ---------------- شكل الواجهة المخصص (Layout) ----------------

def get_ui_layout(layout_key):
    """تُعيد dict {field_key: {x,y,w,h}} أو None إذا لم يوجد شكل محفوظ بعد"""
    import json
    conn = get_connection()
    row = conn.execute("SELECT layout_json FROM ui_layouts WHERE layout_key = ?",
                        (layout_key,)).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["layout_json"])
    except Exception:
        return None


def save_ui_layout(layout_key, layout_dict):
    import json
    conn = get_connection()
    conn.execute("""
        INSERT INTO ui_layouts (layout_key, layout_json) VALUES (?, ?)
        ON CONFLICT(layout_key) DO UPDATE SET layout_json = excluded.layout_json
    """, (layout_key, json.dumps(layout_dict, ensure_ascii=False)))
    conn.commit()
    conn.close()


def reset_ui_layout(layout_key):
    conn = get_connection()
    conn.execute("DELETE FROM ui_layouts WHERE layout_key = ?", (layout_key,))
    conn.commit()
    conn.close()


# ---------------- أرقام تليفونات المريض ----------------

def add_patient_phone(patient_id, phone_number, label="آخر", is_whatsapp=False):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO patient_phones (patient_id, phone_number, label, is_whatsapp)
        VALUES (?, ?, ?, ?)
    """, (patient_id, phone_number, label, 1 if is_whatsapp else 0))
    phone_id = cur.lastrowid
    conn.commit()
    conn.close()
    return phone_id


def get_patient_phones(patient_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM patient_phones WHERE patient_id = ? ORDER BY id",
                         (patient_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_patient_phone(phone_id):
    conn = get_connection()
    conn.execute("DELETE FROM patient_phones WHERE id = ?", (phone_id,))
    conn.commit()
    conn.close()


def get_whatsapp_number(patient_id):
    """بترجع رقم الواتساب المخصوص لو موجود، وإلا التليفون الأساسي"""
    conn = get_connection()
    row = conn.execute(
        "SELECT phone_number FROM patient_phones WHERE patient_id = ? AND is_whatsapp = 1 LIMIT 1",
        (patient_id,)).fetchone()
    conn.close()
    if row:
        return row["phone_number"]
    patient = get_patient(patient_id)
    return patient["phone"] if patient else None


# ---------------- أرقام تليفونات العيادة ----------------

def get_clinic_phones():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM clinic_phones ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_clinic_phone(phone_number):
    conn = get_connection()
    cur = conn.execute("INSERT INTO clinic_phones (phone_number) VALUES (?)", (phone_number,))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_clinic_phone(phone_id, phone_number):
    conn = get_connection()
    conn.execute("UPDATE clinic_phones SET phone_number = ? WHERE id = ?", (phone_number, phone_id))
    conn.commit()
    conn.close()


def delete_clinic_phone(phone_id):
    conn = get_connection()
    conn.execute("DELETE FROM clinic_phones WHERE id = ?", (phone_id,))
    conn.commit()
    conn.close()


# ---------------- العاملون من دون حساب دخول (مساعدون/خدمات مساعدة) ----------------

def get_support_staff(staff_type=None):
    conn = get_connection()
    if staff_type:
        rows = conn.execute(
            "SELECT * FROM support_staff WHERE staff_type = ? AND active = 1 ORDER BY full_name",
            (staff_type,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM support_staff WHERE active = 1 ORDER BY full_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_support_staff(staff_type, full_name, phone="", notes="", specialty="", work_days=""):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO support_staff (staff_type, full_name, phone, notes, specialty, work_days)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (staff_type, full_name, phone, notes, specialty, work_days))
    staff_id = cur.lastrowid
    conn.commit()
    conn.close()
    return staff_id


def update_support_staff(staff_id, **fields):
    if not fields:
        return
    conn = get_connection()
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [staff_id]
    conn.execute(f"UPDATE support_staff SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()


def set_support_staff_active(staff_id, active):
    conn = get_connection()
    conn.execute("UPDATE support_staff SET active = ? WHERE id = ?", (1 if active else 0, staff_id))
    conn.commit()
    conn.close()


# ---------------- قوالب رسائل واتساب ----------------

def get_message_templates(template_type=None):
    conn = get_connection()
    if template_type:
        rows = conn.execute(
            "SELECT * FROM message_templates WHERE template_type = ? ORDER BY id",
            (template_type,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM message_templates ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_message_template(name, template_text, template_type="appointment_reminder"):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO message_templates (name, template_text, template_type) VALUES (?, ?, ?)
    """, (name, template_text, template_type))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_message_template(template_id, name, template_text, template_type=None):
    conn = get_connection()
    if template_type is not None:
        conn.execute(
            "UPDATE message_templates SET name = ?, template_text = ?, template_type = ? WHERE id = ?",
            (name, template_text, template_type, template_id))
    else:
        conn.execute("UPDATE message_templates SET name = ?, template_text = ? WHERE id = ?",
                     (name, template_text, template_id))
    conn.commit()
    conn.close()


def delete_message_template(template_id):
    conn = get_connection()
    conn.execute("DELETE FROM message_templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()


# ---------------- تذكير المواعيد عن طريق واتساب (يدوي بمساعدة البرنامج) ----------------

def get_appointments_for_reminder(target_date):
    """
    المواعيد المؤكدة في يوم معين (افتراضيًا بكرة = قبل الموعد بـ24 ساعة)، كل
    موعد معاه رقم الواتساب المناسب للمريض (رقم واتساب مخصوص لو محدد، وإلا
    رقم التليفون الأساسي)
    """
    appts = get_appointments(date_filter=target_date)
    result = []
    for a in appts:
        if a["status"] == "cancelled":
            continue
        a = dict(a)
        a["whatsapp_number"] = get_whatsapp_number(a["patient_id"])
        result.append(a)
    return result


def mark_reminder_sent(appt_id, sent=True):
    conn = get_connection()
    conn.execute("UPDATE appointments SET reminder_sent = ? WHERE id = ?",
                 (1 if sent else 0, appt_id))
    conn.commit()
    conn.close()


# ---------------- الأرشفة التلقائية (تذكير قبل الموعد بساعة + شكر بعد انتهائه بساعتين) ----------------

def get_appointment_datetime(appt):
    """بترجع datetime كامل لبداية الموعد الفعلي من appt_date + appt_time
    (appt_time مخزَّن بصيغة 24 ساعة HH:MM). ترجع None لو التاريخ/الوقت غير صالح"""
    try:
        return datetime.strptime(f"{appt['appt_date']} {appt['appt_time']}", "%Y-%m-%d %H:%M")
    except Exception:
        return None


def get_appointment_end_datetime(appt):
    """بترجع datetime لنهاية الموعد الفعلي = وقت البداية + مدة الموعد (duration_minutes)"""
    start = get_appointment_datetime(appt)
    if start is None:
        return None
    try:
        duration = int(appt.get("duration_minutes") or 30)
    except Exception:
        duration = 30
    return start + timedelta(minutes=duration)


def get_appointments_due_for_auto_reminder(now=None):
    """المواعيد التي حان وقت تذكيرها التلقائي الآن (وصلنا لساعة واحدة أو أقل
    قبل بداية الموعد الفعلي، والموعد لسه لم يحن بعد، ولم يُرسَل له تذكير تلقائي من قبل)"""
    now = now or datetime.now()
    conn = get_connection()
    rows = conn.execute("""
        SELECT appointments.*, patients.full_name, patients.phone
        FROM appointments JOIN patients ON appointments.patient_id = patients.id
        WHERE appointments.status != 'cancelled' AND appointments.auto_reminder_1h_sent = 0
    """).fetchall()
    conn.close()

    due = []
    for r in rows:
        a = dict(r)
        start = get_appointment_datetime(a)
        if start is None:
            continue
        remind_at = start - timedelta(hours=1)
        if remind_at <= now < start:
            a["whatsapp_number"] = get_whatsapp_number(a["patient_id"])
            due.append(a)
    return due


def get_appointments_due_for_thank_you(now=None):
    """المواعيد التي حان وقت إرسال رسالة الشكر لها الآن (مرّ ساعتان أو أكثر
    على انتهاء الموعد الفعلي، ولم تُرسَل رسالة شكر من قبل)"""
    now = now or datetime.now()
    conn = get_connection()
    rows = conn.execute("""
        SELECT appointments.*, patients.full_name, patients.phone
        FROM appointments JOIN patients ON appointments.patient_id = patients.id
        WHERE appointments.status != 'cancelled' AND appointments.thank_you_sent = 0
    """).fetchall()
    conn.close()

    due = []
    for r in rows:
        a = dict(r)
        end = get_appointment_end_datetime(a)
        if end is None:
            continue
        thank_at = end + timedelta(hours=2)
        if now >= thank_at:
            a["whatsapp_number"] = get_whatsapp_number(a["patient_id"])
            due.append(a)
    return due


def mark_auto_reminder_1h_sent(appt_id, sent=True):
    conn = get_connection()
    conn.execute("UPDATE appointments SET auto_reminder_1h_sent = ? WHERE id = ?",
                 (1 if sent else 0, appt_id))
    conn.commit()
    conn.close()


def mark_thank_you_sent(appt_id, sent=True):
    conn = get_connection()
    conn.execute("UPDATE appointments SET thank_you_sent = ? WHERE id = ?",
                 (1 if sent else 0, appt_id))
    conn.commit()
    conn.close()


def debug_next_day_batch_appointments(now=None):
    """أداة تشخيص فقط: بترجع كل مواعيد الغد زي ما هي بالظبط في قاعدة
    البيانات (من غير أي فلترة على next_day_reminder_sent أو status)، عشان
    نقدر نفرّق بسرعة بين \"مفيش مواعيد لبكرة\" و\"فيه مواعيد بس already
    متعلّمة كمُرسَلة\" و\"فيه مواعيد بس ملغية\""""
    now = now or datetime.now()
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    conn = get_connection()
    rows = conn.execute("""
        SELECT appointments.id, appointments.appt_date, appointments.appt_time,
               appointments.status, appointments.next_day_reminder_sent, patients.full_name
        FROM appointments JOIN patients ON appointments.patient_id = patients.id
        WHERE appointments.appt_date = ?
    """, (tomorrow,)).fetchall()
    conn.close()
    return tomorrow, [dict(r) for r in rows]


def get_appointments_due_for_next_day_batch(now=None, batch_hour=15, batch_minute=0):
    """المواعيد بتاريخ الغد اللي محتاجة تاخد رسالة التذكير اليومية الجماعية.
    البث ده بيبدأ من الساعة/الدقيقة المحددة في الإعدادات (batch_hour:batch_minute
    - افتراضيًا 3:00 الظهر، وقابلة للتعديل) ولحد آخر اليوم، ولسه محتاجة تتبعت
    (next_day_reminder_sent = 0) - المواعيد اللي هتتبعتلها الرسالة دلوقتي، هتاخد
    كمان تذكيرها المستقل قبل موعدها بساعة زي العادة"""
    now = now or datetime.now()
    if (now.hour, now.minute) < (batch_hour, batch_minute):
        return []
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    conn = get_connection()
    rows = conn.execute("""
        SELECT appointments.*, patients.full_name, patients.phone
        FROM appointments JOIN patients ON appointments.patient_id = patients.id
        WHERE appointments.status != 'cancelled' AND appointments.next_day_reminder_sent = 0
              AND appointments.appt_date = ?
    """, (tomorrow,)).fetchall()
    conn.close()

    due = []
    for r in rows:
        a = dict(r)
        a["whatsapp_number"] = get_whatsapp_number(a["patient_id"])
        due.append(a)
    return due


def mark_next_day_reminder_sent(appt_id, sent=True):
    conn = get_connection()
    conn.execute("UPDATE appointments SET next_day_reminder_sent = ? WHERE id = ?",
                 (1 if sent else 0, appt_id))
    conn.commit()
    conn.close()


def get_pending_payment_thank_yous():
    """الدفعات المالية (tx_type='payment') اللي اتسجلت لتوها في حساب أي مريض
    ولسه ما اتبعتلهاش رسالة شكر تلقائية على واتساب"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT transactions.*, patients.full_name, patients.phone
        FROM transactions JOIN patients ON transactions.patient_id = patients.id
        WHERE transactions.tx_type = 'payment' AND transactions.thank_you_sent = 0
    """).fetchall()
    conn.close()

    due = []
    for r in rows:
        t = dict(r)
        t["whatsapp_number"] = get_whatsapp_number(t["patient_id"])
        due.append(t)
    return due


def mark_transaction_thank_you_sent(tx_id, sent=True):
    conn = get_connection()
    conn.execute("UPDATE transactions SET thank_you_sent = ? WHERE id = ?",
                 (1 if sent else 0, tx_id))
    conn.commit()
    conn.close()


def set_whatsapp_auto_settings(enabled=None, reminder_template_id=None, thankyou_template_id=None,
                                confirm_send=None, wait_seconds=None, use_desktop_app=None,
                                payment_thankyou_enabled=None, next_day_batch_hour=None,
                                next_day_batch_minute=None, booking_confirmation_enabled=None,
                                hour_reminder_enabled=None, next_day_batch_enabled=None):
    """حفظ إعدادات الأرشفة التلقائية لواتساب (تُقرأ من صفحة واتساب وتُستخدم
    من الحلقة الخلفية في main.py). كل نوع رسالة (تذكير الساعة/تأكيد الغد/
    تأكيد الحجز/الشكر بعد الدفع) ليه تشيك بوكس تفعيل مستقل بيتحفظ لوحده"""
    conn = get_connection()
    current = get_settings()
    conn.execute("""
        UPDATE clinic_settings SET
            whatsapp_auto_archive_enabled = ?,
            whatsapp_auto_reminder_template_id = ?,
            whatsapp_auto_thankyou_template_id = ?,
            whatsapp_auto_confirm_send = ?,
            whatsapp_auto_wait_seconds = ?,
            whatsapp_auto_use_desktop_app = ?,
            whatsapp_payment_thankyou_enabled = ?,
            whatsapp_next_day_batch_hour = ?,
            whatsapp_next_day_batch_minute = ?,
            whatsapp_booking_confirmation_enabled = ?,
            whatsapp_hour_reminder_enabled = ?,
            whatsapp_next_day_batch_enabled = ?
        WHERE id = 1
    """, (
        (1 if enabled else 0) if enabled is not None else current["whatsapp_auto_archive_enabled"],
        reminder_template_id if reminder_template_id is not None
            else current["whatsapp_auto_reminder_template_id"],
        thankyou_template_id if thankyou_template_id is not None
            else current["whatsapp_auto_thankyou_template_id"],
        (1 if confirm_send else 0) if confirm_send is not None else current["whatsapp_auto_confirm_send"],
        wait_seconds if wait_seconds is not None else current["whatsapp_auto_wait_seconds"],
        (1 if use_desktop_app else 0) if use_desktop_app is not None
            else current["whatsapp_auto_use_desktop_app"],
        (1 if payment_thankyou_enabled else 0) if payment_thankyou_enabled is not None
            else current["whatsapp_payment_thankyou_enabled"],
        next_day_batch_hour if next_day_batch_hour is not None
            else current["whatsapp_next_day_batch_hour"],
        next_day_batch_minute if next_day_batch_minute is not None
            else current["whatsapp_next_day_batch_minute"],
        (1 if booking_confirmation_enabled else 0) if booking_confirmation_enabled is not None
            else current["whatsapp_booking_confirmation_enabled"],
        (1 if hour_reminder_enabled else 0) if hour_reminder_enabled is not None
            else current["whatsapp_hour_reminder_enabled"],
        (1 if next_day_batch_enabled else 0) if next_day_batch_enabled is not None
            else current["whatsapp_next_day_batch_enabled"],
    ))
    conn.commit()
    conn.close()


ARABIC_DAY_NAMES = {
    0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
    4: "الجمعة", 5: "السبت", 6: "الأحد",
}


def get_day_name_arabic(appt_date):
    """بيرجع اسم اليوم بالعربي (السبت، الأحد...) من تاريخ بصيغة YYYY-MM-DD"""
    try:
        d = datetime.strptime(appt_date, "%Y-%m-%d")
        return ARABIC_DAY_NAMES.get(d.weekday(), "")
    except Exception:
        return ""


def format_time_12h(appt_time):
    """
    بيحول وقت الموعد لصيغة 12 ساعة مع صباحًا/مساءً حسب الوقت الفعلي.
    بيقبل الوقت مخزّن بصيغة 24 ساعة (14:30) أو 12 ساعة مع AM/PM (02:30 PM)،
    ولو الصيغة غريبة بيرجع النص الأصلي زي ما هو من غير ما يبوّظه.
    """
    if not appt_time:
        return ""
    raw = appt_time.strip()
    parsed = None
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
            break
        except Exception:
            continue
    if parsed is None:
        return raw
    hour12 = parsed.hour % 12
    if hour12 == 0:
        hour12 = 12
    period = "صباحًا" if parsed.hour < 12 else "مساءً"
    return f"{hour12:02d}:{parsed.minute:02d} {period}"


def fill_message_template(template_text, patient_name, appt_date, appt_time,
                           doctor_name="", clinic_name=""):
    """بيستبدل {name}/{date}/{day_name}/{time}/{doctor}/{clinic_name} بالبيانات الفعلية للمريض والموعد"""
    try:
        formatted_date = datetime.strptime(appt_date, "%Y-%m-%d").strftime("%Y/%m/%d")
    except Exception:
        formatted_date = appt_date
    day_name = get_day_name_arabic(appt_date)
    formatted_time = format_time_12h(appt_time)
    return (template_text
            .replace("{name}", patient_name or "")
            .replace("{date}", formatted_date)
            .replace("{day_name}", day_name)
            .replace("{time}", formatted_time)
            .replace("{doctor}", doctor_name or "")
            .replace("{clinic_name}", clinic_name or ""))


def fill_payment_thank_you_template(template_text, patient_name, amount, clinic_name="", doctor_name=""):
    """بيستبدل {name}/{amount}/{clinic_name}/{doctor}/{date}/{day_name}/{time} في
    رسالة الشكر اللي بتتبعت تلقائيًا فور تسجيل دفعة مالية في حساب المريض.
    {date}/{day_name}/{time} بتاخد قيمتها من تاريخ ووقت تسجيل الدفعة نفسه (دلوقتي)،
    و{amount} بيتحط بدل مبلغ الدفعة (بدون أي وحدة عملة - تقدر تضيفها في نص القالب نفسه)"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    formatted_date = now.strftime("%Y/%m/%d")
    day_name = get_day_name_arabic(today_str)
    formatted_time = format_time_12h(now.strftime("%H:%M"))
    try:
        amount_text = f"{float(amount):,.2f}".rstrip("0").rstrip(".")
    except Exception:
        amount_text = str(amount)
    return (template_text
            .replace("{name}", patient_name or "")
            .replace("{amount}", amount_text)
            .replace("{date}", formatted_date)
            .replace("{day_name}", day_name)
            .replace("{time}", formatted_time)
            .replace("{doctor}", doctor_name or "")
            .replace("{clinic_name}", clinic_name or ""))


def build_whatsapp_link(phone_number, message_text):
    """تبني رابط wa.me جاهزًا يفتح محادثة واتساب برسالة معبَّأة مسبقًا (عبر المتصفح / واتساب ويب)"""
    import urllib.parse
    digits = "".join(ch for ch in (phone_number or "") if ch.isdigit())
    # إذا كان الرقم مصريًا ويبدأ بصفر (01...)، نحوّله إلى الصيغة الدولية (2 01...)
    if digits.startswith("0") and len(digits) == 11:
        digits = "2" + digits
    encoded_text = urllib.parse.quote(message_text)
    return f"https://wa.me/{digits}?text={encoded_text}"


def build_whatsapp_desktop_link(phone_number, message_text):
    """تبني رابط بروتوكول whatsapp:// الذي يفتح تطبيق واتساب لسطح المكتب مباشرة
    (من دون المرور بصفحة متصفح وسيطة)، وهو أضمن عند إرسال عدة رسائل متتالية"""
    import urllib.parse
    digits = "".join(ch for ch in (phone_number or "") if ch.isdigit())
    if digits.startswith("0") and len(digits) == 11:
        digits = "2" + digits
    encoded_text = urllib.parse.quote(message_text)
    return f"whatsapp://send?phone={digits}&text={encoded_text}"
