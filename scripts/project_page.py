# -*- coding: utf-8 -*-
"""
بيبني صفحة HTML مستقلة (ملف واحد من غير أي dependencies خارجية)
بتلخّص مشروع Dentora: إحصائيات، مراحل الشغل، معرض الثemes، المعمار،
وأوامر التشغيل. الصفحة بتُستخدم في تبويب المعاينة (Preview) -
وضع htmlPath: ملف ثابت من غير سيرفر ولا port.

إعادة التوليد:  python scripts/project_page.py
المخرجات:       .freebuff/project_overview.html
"""

import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

OUTPUT_PATH = os.path.join(PROJECT_ROOT, ".freebuff", "project_overview.html")


def git_commits():
    """آخر 16 commit (هي شغل المرحلة الحالية) - لو git مش متاح برجّع قائمة فاضية"""
    try:
        out = subprocess.run(
            ["git", "log", "--oneline", "-16", "--no-decorate"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8",
            timeout=10, check=True).stdout
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def project_stats():
    import theme  # pure python - آمن من غير GUI
    presets = theme.THEME_PRESETS

    with open(os.path.join(PROJECT_ROOT, "database.py"), encoding="utf-8") as f:
        db_src = f.read()
    tables = len(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", db_src))
    indexes = len(re.findall(r"CREATE INDEX IF NOT EXISTS", db_src))

    py_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ("ui", "__pycache__", ".git",
                                                 ".freebuff", "dist", "build",
                                                 "assets", "scripts")]
        for fn in files:
            if fn.endswith(".py"):
                py_files.append(os.path.join(root, fn))
    loc = sum(len(open(p, encoding="utf-8", errors="ignore").readlines())
              for p in py_files)

    commits = git_commits()
    return {
        "themes": presets,
        "theme_count": len(presets),
        "tables": tables,
        "indexes": indexes,
        "loc": loc,
        "commits": commits,
    }


PAGES = [
    ("المواعيد", "Appointments", "تقويم يومي بالساعات، حالات موعد، مدة ولون، إجازات وساعات عمل"),
    ("المرضى", "Patients", "ملف كامل: صور، مستندات، أرقام متعددة، عائلات، خصومات"),
    ("خريطة الأسنان", "Odontogram", "FDI كامل، حالات بزوغ، ملحوظات بالطبيب، توليد حسب العمر"),
    ("الإجراءات", "Procedures", "قوائم أسعار، أنواع فرعية، ألوان ورموز على الشарт"),
    ("طاقم العمل", "Staff", "صلاحيات مدير/طبيب/سكرتaria، رواتب وعمولات وزيادات"),
    ("حسابات العيادة", "Accounts", "إيرادات ومصروفات وصافي أي فترة، وعمولات الأطباء"),
    ("المعامل", "Labs", "طلبات الشغل بحالات، وح حساب مستحقات كل معمل"),
    ("المصروفات", "Expenses", "تصنيفات بتبويبات أيقونية، مورد، وإجمالي لكل تصنيف"),
    ("تكامل n8n", "WhatsApp", "إرسال عبر webhook في الخلفية، 3 محاولات، سجل كامل، retry عند الفتح"),
]

PHASES = [
    ("Phase 0", "الأساس", "commit للعمل المعلّق، سكript فحص headless، وREADME محيّن"),
    ("Phase 1", "نظام التصميم", "مكوّنات مشتركة موحّدة: هيدر، كروت، أزرار، حالات فارغة - 8 صفحات اتحملت"),
    ("Phase 2", "الثemes", "معاينة حية للثيم قبل التطبيق، و5 ثيمات جديدة (30 إجمالًا)"),
    ("Phase 3", "الـBackend", "14 index لاستعلامات ساخنة، وn8n في الخلفية بretry وسجل تسليم"),
    ("Phase 4", "الاختبار", "فحص دخاني بيبنِي كل الـ9 صفحات في نافذة Tk حقيقية على قاعدة مؤقتة"),
]

ARCH_ROWS = [
    ("main.py", "الواجهة الرئيسية: CustomTkinter، تسجيل دخول، شريط تنقل، بناء الصفحات"),
    ("pages/", "9 صفحات، ودجتات (خريطة أسنان، تقويم مصغّر، جداول)، ومكتبة المكونات المشتركة"),
    ("database.py", "SQLite + WAL: 25 جدول، ترقيات تلقائية، PBKDF2، صلاحيات، سجل n8n"),
    ("theme.py", "30 ثيم جاهz، تدرجات هيدر، 3 شكلات أزرar، خطوط عرب، ومعاينة حية"),
    ("n8n_integration.py", "Webhook sender مع retry/backoff، وسجل تسليم في قاعدة البيانات"),
    ("scripts/", "check.py فحص headless، وsmoke_gui.py فحص كل الصفحات في نافذة مخفية"),
]


def build_html(stats):
    # صفوف الثemes - كل ثem كارت فيه دواير ألوانه
    theme_cards = []
    for tid, p in stats["themes"].items():
        theme_cards.append(
            f'<div class="tcard">'
            f'<div class="dots">'
            f'<span class="dot" style="background:{p["primary"]}" title="primary"></span>'
            f'<span class="dot" style="background:{p["secondary"]}" title="secondary"></span>'
            f'<span class="dot" style="background:{p["bg_main"]};border:1px solid #ddd" title="background"></span>'
            f'<span class="dot" style="background:{p.get("accent_border", p["secondary"])}" title="accent"></span>'
            f'</div>'
            f'<div class="tname">{p["name"]}</div>'
            f'<div class="tid">{tid}</div>'
            f'</div>')
    themes_html = "\n".join(theme_cards)

    commits_html = "\n".join(
        f'<li><code>{c.split(" ", 1)[0]}</code> {c.split(" ", 1)[1] if " " in c else ""}</li>'
        for c in stats["commits"]) or "<li>git غير متاح</li>"

    pages_html = "\n".join(
        f'<tr><td class="pname">{ar}</td><td class="pen">{en}</td><td>{desc}</td></tr>'
        for ar, en, desc in PAGES)

    phases_html = "\n".join(
        f'<div class="phase"><div class="ph">{pid}</div><div class="pt">{title}</div>'
        f'<div class="pd">{desc}</div></div>'
        for pid, title, desc in PHASES)

    arch_html = "\n".join(
        f'<tr><td class="file">{f}</td><td>{d}</td></tr>' for f, d in ARCH_ROWS)

    html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dentora - نظرة عامة على المشروع</title>
<style>
  :root { --ink:#1b2430; --muted:#5d6b7a; --line:#e3e8ee; --card:#ffffff; --bg:#f2f5f8; --accent:#00695c; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:"Segoe UI", Tahoma, system-ui, sans-serif; background:var(--bg); color:var(--ink); line-height:1.7; }
  .wrap { max-width:1080px; margin:0 auto; padding:0 24px 64px; }
  header { background:linear-gradient(135deg,#0b3d36 0%,#00695c 55%,#00897b 100%); color:#fff; padding:48px 24px 40px; }
  header .wrap { padding-bottom:0; }
  h1 { font-size:34px; font-weight:800; }
  .sub { opacity:.92; margin-top:6px; font-size:16px; }
  .badges { margin-top:16px; display:flex; gap:8px; flex-wrap:wrap; }
  .badge { background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.25); border-radius:20px; padding:4px 14px; font-size:13px; }
  h2 { font-size:21px; margin:42px 0 14px; padding-inline-start:12px; border-inline-start:4px solid var(--accent); }
  .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }
  .stat { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; text-align:center; }
  .stat .num { font-size:30px; font-weight:800; color:var(--accent); }
  .stat .lbl { color:var(--muted); font-size:13px; margin-top:2px; }
  .phases { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; }
  .phase { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; }
  .ph { display:inline-block; background:var(--accent); color:#fff; border-radius:8px; padding:2px 10px; font-size:12px; font-weight:700; }
  .pt { font-weight:700; margin:8px 0 4px; }
  .pd { color:var(--muted); font-size:13.5px; }
  table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); border-radius:12px; overflow:hidden; }
  th, td { padding:10px 14px; text-align:right; border-bottom:1px solid var(--line); font-size:14px; vertical-align:top; }
  th { background:#eef3f1; font-size:13px; }
  tr:last-child td { border-bottom:none; }
  .pname { font-weight:700; white-space:nowrap; }
  .pen { color:var(--muted); direction:ltr; text-align:left; font-size:12.5px; white-space:nowrap; }
  .file { font-family:Consolas, monospace; direction:ltr; text-align:left; color:var(--accent); font-weight:600; white-space:nowrap; }
  .themes { display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:10px; }
  .tcard { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; }
  .dots { display:flex; gap:6px; margin-bottom:8px; }
  .dot { width:22px; height:22px; border-radius:50%; display:inline-block; }
  .tname { font-size:13px; font-weight:700; }
  .tid { font-size:11px; color:var(--muted); direction:ltr; text-align:right; font-family:Consolas, monospace; }
  ul.commits { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 30px; }
  ul.commits li { padding:4px 0; font-size:13.5px; border-bottom:1px dashed var(--line); }
  ul.commits li:last-child { border-bottom:none; }
  code { font-family:Consolas, monospace; background:#eef3f1; border-radius:5px; padding:1px 7px; font-size:12.5px; direction:ltr; display:inline-block; }
  .cmds { background:#14231f; color:#d9efe9; border-radius:12px; padding:20px 24px; direction:ltr; text-align:left; }
  .cmds .c { display:block; padding:5px 0; font-family:Consolas, monospace; font-size:13.5px; }
  .cmds .c::before { content:"$ "; color:#6fae9f; }
  footer { margin-top:44px; color:var(--muted); font-size:13px; text-align:center; }
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1>&#129463; Dentora</h1>
    <div class="sub">نظام إدارة عيادة أسنان كامل - برنامج سطح مكتب لويندوز، عربي RTL بالكامل</div>
    <div class="badges">
      <span class="badge">Python + CustomTkinter</span>
      <span class="badge">SQLite + WAL</span>
      <span class="badge">n8n / WhatsApp</span>
      <span class="badge">PyInstaller EXE</span>
    </div>
  </div>
</header>
<div class="wrap">

  <h2>إحصائيات المشروع</h2>
  <div class="stats">
    <div class="stat"><div class="num">9</div><div class="lbl">صفحات كاملة</div></div>
    <div class="stat"><div class="num">__THEMES__</div><div class="lbl">ثيم جاهz</div></div>
    <div class="stat"><div class="num">__TABLES__</div><div class="lbl">جدول في قاعدة البيانات</div></div>
    <div class="stat"><div class="num">__INDEXES__</div><div class="lbl">index لاستعلامات سريعة</div></div>
    <div class="stat"><div class="num">__LOC__</div><div class="lbl">سطر Python</div></div>
  </div>

  <h2>مراحل الشغل (تنفيذ كامل)</h2>
  <div class="phases">
__PHASES__
  </div>

  <h2>الصفحات</h2>
  <table>
    <tr><th>الصفحة</th><th>English</th><th>الوصف</th></tr>
__PAGES__
  </table>

  <h2>ال معمار</h2>
  <table>
    <tr><th>Module</th><th>الوصف</th></tr>
__ARCH__
  </table>

  <h2>معرض الثemes (كل الثemes الجاهza)</h2>
  <div class="themes">
__THEME_CARDS__
  </div>

  <h2>آخر الـCommits (شغل المرحلة دي)</h2>
  <ul class="commits">
__COMMITS__
  </ul>

  <h2>تشغيل البرنامج</h2>
  <div class="cmds">
    <span class="c">pip install -r requirements.txt</span>
    <span class="c">python main.py</span>
    <span class="c">python scripts/check.py&nbsp;&nbsp;&nbsp;&nbsp;# فحص headless</span>
    <span class="c">python scripts/smoke_gui.py&nbsp;&nbsp;# فحص كل الصفحات</span>
    <span class="c">python scripts/project_page.py&nbsp;&nbsp;# تحديث الصفحة دي</span>
  </div>

  <footer>صفحة مولّدة تلقائيًا بواسطة scripts/project_page.py - آخر تحديث: __DATE__</footer>
</div>
</body>
</html>"""
    html = (html
            .replace("__THEMES__", str(stats["theme_count"]))
            .replace("__TABLES__", str(stats["tables"]))
            .replace("__INDEXES__", str(stats["indexes"]))
            .replace("__LOC__", f"{stats['loc']:,}")
            .replace("__PHASES__", phases_html)
            .replace("__PAGES__", pages_html)
            .replace("__ARCH__", arch_html)
            .replace("__THEME_CARDS__", themes_html)
            .replace("__COMMITS__", commits_html)
            .replace("__DATE__", __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")))
    return html


def main():
    stats = project_stats()
    html = build_html(stats)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"written: {OUTPUT_PATH}")
    print(f"themes: {stats['theme_count']} | tables: {stats['tables']} | "
          f"indexes: {stats['indexes']} | loc: {stats['loc']:,} | "
          f"commits listed: {len(stats['commits'])}")


if __name__ == "__main__":
    main()
