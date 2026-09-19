# -*- coding: utf-8 -*-
"""فحص دخاني للواجهة PySide6 (ui/) - بدون شاشة حقيقية (offscreen).

التشغيل:  python -m tests.ui_smoke

بيغطي:
  * بناء كل صفحات MainWindow على قاعدة بيانات مؤقتة.
  * عدم وجود تحذيرات "QLayout: Attempting to add QLayout" (خلية البطاقات).
  * بطاقات إحصائيات الداشبورد فيها قيم فعلية مش "---".
  * حقل تاريخ المواعيد بيعرض تاريخ اليوم مش 2000-01-01.
  * أسماء القايمة الجانبية عربي نضيف من غير حروف لاتينية مدسوسة.
  * صفحة المعامل (labs) موجودة في الستاك والتنقل شغال.
  * حفظ صورة PNG لكل صفحة للمراجعة البصرية.
"""

import os
import re
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# قاعدة بيانات مؤقتة - الفحص مش بيلمس clinic_data.db الحقيقية
from tests.helpers import fresh_db_path  # noqa: E402

fresh_db_path()

import database as db  # noqa: E402

db.init_db()

from PySide6.QtCore import QDate, Qt, qInstallMessageHandler  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

FAILURES = []
LAYOUT_WARNINGS = []


def _message_handler(mode, context, message):
    if "QLayout" in message:
        LAYOUT_WARNINGS.append(message)


qInstallMessageHandler(_message_handler)

app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setLayoutDirection(Qt.RightToLeft)

try:
    from qt_main import apply_font, load_fonts
    apply_font(app, load_fonts())
except Exception:
    pass  # الخطوط تحسين للصور - مش شرط نجاح الفحص

from ui.main_window import MainWindow, NAV_ITEMS  # noqa: E402
from ui.components import StatCard  # noqa: E402
from ui.appointments_page import AppointmentsPage  # noqa: E402

SHOTS_DIR = os.path.join(tempfile.mkdtemp(prefix="dentora_ui_shots_"))


def check(name, cond, extra=""):
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" ({extra})" if extra else ""))
    if not cond:
        FAILURES.append(name)


def main():
    # مريض وموعد حقيقيين عشان الداشبورد يعرض أرقام مش أصفار/شرط
    pid = db.add_patient(full_name="مريض الفحص", phone="+201090277993",
                         birth_date="1990-05-01", gender="male")
    db.add_appointment(patient_id=pid, doctor_name="د. تجربة",
                       appt_date=QDate.currentDate().toString("yyyy-MM-dd"),
                       appt_time="10:00", status="confirmed")

    win = MainWindow({"id": 1, "username": "admin",
                      "full_name": "مستخدم الفحص", "role": "admin"})
    win.resize(1280, 800)
    win.show()
    app.processEvents()

    check("عدد صفحات الستاك = عدد عناصر القايمة",
          win.stack.count() == len(NAV_ITEMS),
          f"stack={win.stack.count()} nav={len(NAV_ITEMS)}")

    labs_idx = None
    for i in range(win.stack.count()):
        w = win.stack.widget(i)
        if w.__class__.__name__ == "LabsPage":
            labs_idx = i
    check("صفحة المعامل (LabsPage) موجودة في الستاك", labs_idx is not None)

    # لقطات + مراجعة كل صفحة
    for i in range(win.stack.count()):
        win.stack.setCurrentIndex(i)
        w = win.stack.widget(i)
        if hasattr(w, "refresh"):
            try:
                w.refresh()
            except Exception as exc:
                check(f"refresh صفحة {w.__class__.__name__}",
                      False, repr(exc))
                continue
        app.processEvents()
        shot = os.path.join(SHOTS_DIR, f"check_{i}_{w.__class__.__name__}.png")
        ok = win.grab().save(shot)
        check(f"بناء وعرض {w.__class__.__name__}", ok and os.path.exists(shot),
              os.path.basename(shot))

    # ---- فحوصات الباجات الخمسة ----
    dash = win.page_widgets["dashboard"]
    stat_values = [c.value_label.text() for c in dash.findChildren(StatCard)]
    check("بطاقات إحصائيات الداشبورد مش فاضية (مش ---)",
          bool(stat_values) and all(v != "---" for v in stat_values),
          str(stat_values))

    appt = win.page_widgets["appointments"]
    today = QDate(QDate.currentDate().year(), QDate.currentDate().month(),
                  QDate.currentDate().day())
    check("حقل تاريخ المواعيد = تاريخ اليوم (مش 2000-01-01)",
          appt.date_edit.date() == today, appt.date_edit.date().toString())

    bad_labels = [label for _, label, _, _ in NAV_ITEMS
                  if re.search(r"[A-Za-z]", label)]
    check("أسماء القايمة الجانبية عربي نضيف", not bad_labels, str(bad_labels))

    check("مفيش تحذيرات QLayout متكررة", not LAYOUT_WARNINGS,
          str(LAYOUT_WARNINGS[:2]))

    print(f"\nاللقطات في: {SHOTS_DIR}")
    if FAILURES:
        print("FAILURES:", FAILURES)
        sys.exit(1)
    print("ALL_OK")


if __name__ == "__main__":
    main()
