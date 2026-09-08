# -*- coding: utf-8 -*-
"""
فحص سريع للمشروع من غير تشغيل الواجهة (headless check)

بيتعمل حاجتين:
1. compileall على كل ملفات بايثون - بيمسك أي SyntaxError فورًا
2. نسخة مؤقتة من قاعدة البيانات - بنشغّل عليها init_db() كامل
   (كل الـ CREATE TABLE / ALTER TABLE / indexes / seeding) وبعدها
   استعلامات تدقيق بسيطة، وكل ده على ملف مؤقت مكان clinic_data.db
   الحقيقي - فالفحص آمن تمامًا ومش بيلمس بيانات العيادة

التشغيل:  python scripts/check.py
يخرج بكود 0 لو كل حاجة سليمة، وكود 1 لو فيه مشكلة.
"""

import compileall
import os
import shutil
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAILED = False


def fail(message):
    global FAILED
    FAILED = True
    print(f"[FAIL] {message}")


def ok(message):
    print(f"[ OK ] {message}")


def step_compile():
    print("== 1/3 Byte-compiling all Python files ==")
    # quiet=2: اطبع الملفات اللي فيها أخطاء بس
    if compileall.compile_dir(PROJECT_ROOT, quiet=2, force=True, rx=None):
        ok("all python files compile")
    else:
        fail("compileall found syntax errors (see list above)")


def step_database():
    print("== 2/3 Running full init_db() against a throwaway DB copy ==")
    sys.path.insert(0, PROJECT_ROOT)
    os.chdir(PROJECT_ROOT)  # database.py يحسب DB_PATH من مكان الملف نفسه، بس للأمان

    import database  # noqa: E402

    tmp_dir = tempfile.mkdtemp(prefix="dentora_check_")
    real_db = database.DB_PATH
    try:
        if os.path.exists(real_db):
            tmp_db = os.path.join(tmp_dir, "clinic_data.db")
            shutil.copy2(real_db, tmp_db)
            # انسخ ملفات WAL/SHM لو موجودة عشان النسخة تكون مكتملة
            for ext in ("-wal", "-shm"):
                if os.path.exists(real_db + ext):
                    shutil.copy2(real_db + ext, tmp_db + ext)
            source = "existing clinic_data.db (copied)"
        else:
            source = "no existing db (fresh create)"
        database.DB_PATH = os.path.join(tmp_dir, "clinic_data.db")

        database.init_db()
        ok(f"init_db() completed on {source}")

        expected_tables = {
            "clinic_settings", "users", "role_permissions", "patients",
            "tooth_chart", "tooth_annotations", "appointments", "price_lists",
            "treatment_prices", "treatment_variants", "treatment_records",
            "transactions", "visits", "patient_files", "suppliers",
            "clinic_phones", "support_staff", "ui_layouts", "patient_phones",
            "message_templates", "expenses", "holidays", "labs",
            "lab_orders", "lab_transactions",
        }
        conn = database.get_connection()
        actual_tables = {
            r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        missing = expected_tables - actual_tables
        if missing:
            fail(f"missing tables after init_db: {sorted(missing)}")
        else:
            ok(f"all {len(expected_tables)} expected tables exist")

        # عمود واحد من آخر الترقيات، للتأكد إن مسار الـ migrations ماشي
        settings_cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(clinic_settings)").fetchall()}
        for col in ("theme_id", "nav_button_style", "icon_pattern",
                    "show_ribbon_labels", "require_password"):
            if col not in settings_cols:
                fail(f"clinic_settings is missing column '{col}'")
        if not FAILED:
            ok("settings migration columns present")

        # المستخدم الافتراضي لازم يكون موجود دايمًا
        users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if users_count == 0:
            fail("users table is empty - default admin was not seeded")
        else:
            ok(f"users seeded ({users_count} row(s))")
        conn.close()
    except Exception as exc:  # noqa: BLE001
        fail(f"database check raised: {type(exc).__name__}: {exc}")
    finally:
        database.DB_PATH = real_db
        shutil.rmtree(tmp_dir, ignore_errors=True)


def step_theme_and_integrations():
    print("== 3/3 Importing theme + integration modules ==")
    try:
        import theme  # noqa: E402
        presets = theme.THEME_PRESETS
        if not presets:
            fail("THEME_PRESETS is empty")
        else:
            for preset_id, preset in presets.items():
                for key in ("name", "primary", "secondary",
                            "bg_main", "card_bg", "text_dark"):
                    if key not in preset:
                        fail(f"theme preset '{preset_id}' is missing key '{key}'")
            if not FAILED:
                ok(f"theme.py imports, {len(presets)} presets validated")

        # apply_from_settings لازم تشتغل من غير توكن GUI
        theme.apply_from_settings({"primary_color": "#1E88E5",
                                   "secondary_color": "#0D47A1",
                                   "system_font_family": "Segoe UI",
                                   "content_font_family": "Segoe UI",
                                   "system_font_size": 16,
                                   "content_font_size": 16,
                                   "theme_id": "ocean_blue"})
        ok("apply_from_settings() runs headless")
    except Exception as exc:  # noqa: BLE001
        fail(f"theme check raised: {type(exc).__name__}: {exc}")

    try:
        import n8n_integration  # noqa: E402  (requests optional inside)
        ok("n8n_integration imports")
    except Exception as exc:  # noqa: BLE001
        fail(f"n8n_integration import raised: {type(exc).__name__}: {exc}")


def main():
    print(f"Dentora check - project root: {PROJECT_ROOT}")
    step_compile()
    step_database()
    step_theme_and_integrations()
    if FAILED:
        print("RESULT: FAILED")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
