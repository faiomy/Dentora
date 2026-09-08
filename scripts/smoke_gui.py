# -*- coding: utf-8 -*-
"""
فحص دخاني اختياري للواجهة (GUI smoke test) - بيبنِي كل صفحة فعليًا جوه
نافذة Tk حقيقية (مخفية) على نسخة مؤقتة من قاعدة البيانات، وبيتأكد إن
البناء نفسه بينجح من غير أي خطأ.

ده بيمسك أخطاء الـ runtime اللي compileall مش بيقدر يشوفها
(زي تمرير argument مش مدعوم لوidget).

التشغيل:  python scripts/smoke_gui.py   (على جهاز فيه واجهة رسومية)
"""

import os
import sys
import tempfile
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import database as db  # noqa: E402

# قاعدة بيانات مؤقتة - الفحص مش بيلمس clinic_data.db الحقيقية
_tmp = tempfile.mkdtemp(prefix="dentora_smoke_")
db.DB_PATH = os.path.join(_tmp, "clinic_data.db")
db.init_db()

import customtkinter as ctk  # noqa: E402
import theme  # noqa: E402

theme.apply_from_settings({"primary_color": "#00695C", "secondary_color": "#004D40",
                           "theme_id": "clean_medical"})
ctk.set_appearance_mode("light")

from pages.clinic_accounts_page import ClinicAccountsPage  # noqa: E402
from pages.materials_page import MaterialsPage  # noqa: E402
from pages.labs_page import LabsPage  # noqa: E402
from pages.staff_page import StaffPage  # noqa: E402
from pages.prices_page import PricesPage  # noqa: E402
from pages.settings_page import SettingsPage  # noqa: E402
from pages.patients_page import PatientsPage  # noqa: E402
from pages.appointments_page import AppointmentsPage  # noqa: E402
from pages.n8n_page import N8nPage  # noqa: E402

USER = {"id": 1, "username": "admin", "full_name": "مدير", "role": "manager"}

PAGES = [
    ("ClinicAccounts", lambda: ClinicAccountsPage(root)),
    ("Materials", lambda: MaterialsPage(root)),
    ("Labs", lambda: LabsPage(root, current_user=USER)),
    ("Staff", lambda: StaffPage(root, current_user=USER)),
    ("Prices", lambda: PricesPage(root)),
    ("Settings", lambda: SettingsPage(root, current_user=USER, on_settings_changed=None)),
    ("Patients", lambda: PatientsPage(root, current_user=USER)),
    ("Appointments", lambda: AppointmentsPage(root, current_user=USER)),
    ("N8n", lambda: N8nPage(root)),
]

failed = []
root = ctk.CTk()
root.withdraw()
for name, factory in PAGES:
    try:
        page = factory()
        root.update_idletasks()
        page.destroy()
        print("OK  ", name)
    except Exception as exc:  # noqa: BLE001
        failed.append(name)
        print("FAIL", name, "->", type(exc).__name__, exc)
        traceback.print_exc(limit=3)
root.destroy()

if failed:
    print("RESULT: FAILED -", ", ".join(failed))
    sys.exit(1)
print("RESULT: ALL PAGES CONSTRUCT SUCCESSFULLY")
