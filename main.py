# -*- coding: utf-8 -*-
"""
البرنامج الرئيسي لإدارة العيادة
شغِّل هذا الملف لفتح البرنامج: python main.py
"""

import os
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFilter

import theme
import database as db
from pages.n8n_page import N8nPage
from pages import icons
from pages.patients_page import PatientsPage
from pages.appointments_page import AppointmentsPage
from pages.settings_page import SettingsPage
from pages.prices_page import PricesPage
from pages.materials_page import MaterialsPage
from pages.clinic_accounts_page import ClinicAccountsPage
from pages.staff_page import StaffPage
from pages.labs_page import LabsPage

# بنعطّل الـ DPI awareness التلقائي بتاع customtkinter (ده اللي بيسبب مشكلة إن
# عناصر الواجهة (زي مساحة الصور والأشعة في ملف المريض) تظهر أصغر من حجمها
# المكتوب في الكود وبيتقطع النص جواها - المشكلة بتظهر لما شاشة الجهاز شغالة
# بنسبة تكبير غير 100% في إعدادات ويندوز (زي 125% أو 150%، وده شائع جدًا على
# شاشات اللاب توب)، لأن customtkinter بيحاول يحسب نسبة تصغير/تكبير خاصة بيه
# فوق نسبة ويندوز، فبيحصل تعارض والحجم النهائي بيبقى غلط. تعطيل الميزة دي
# بيخلي كل الأحجام (width/height) المكتوبة في الكود تتعرض كما هي بالظبط.
ctk.deactivate_automatic_dpi_awareness()

ctk.set_appearance_mode("system")


def _attach_gradient_background(header_frame):
    """بترسم تدرج لوني رأسي ناعم (زي هيدرات الثيمات الشهيرة) خلف محتوى أي
    هيدر، من غير ما تغيّر طريقة ترتيب العناصر جواه (لسه بتتحط بـ pack زي
    ما هي). بترجع الـ Canvas عشان ممكن نحدّث ألوانه لو الثيم اتغيّر وقت التشغيل"""
    canvas = tk.Canvas(header_frame, highlightthickness=0, bd=0)
    canvas.place(x=0, y=0, relwidth=1, relheight=1)

    def _redraw(event=None):
        theme.draw_vertical_gradient(canvas, header_frame.winfo_width(),
                                      header_frame.winfo_height(),
                                      theme.HEADER_GRAD_START, theme.HEADER_GRAD_END)

    header_frame.bind("<Configure>", _redraw)
    header_frame.after(50, _redraw)
    return canvas


def _make_accent_divider(parent):
    """خط حد مميز رفيع بلون مختلف واضح (accent_border) تحت أي هيدر - جزء
    من هوية الثيم الحقيقية (زي حدود ثيمات ويندوز/أوفيس الملوّنة)"""
    return ctk.CTkFrame(parent, fg_color=theme.ACCENT_BORDER, height=3, corner_radius=0)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# أيقونة "Dentora" (اسم البرنامج نفسه) - ثابتة ومش بتتغير، بعكس لوجو العيادة اللي
# بيحطه صاحب العيادة من صفحة الإعدادات. لازم يكون الملف ده موجود في assets/dentora_icon.png
DENTORA_ICON_PATH = os.path.join(APP_ROOT, "assets", "dentora_icon.png")


def _strip_light_background(img, threshold=235, alpha_threshold=12):
    """بتشيل بس الخلفية البيضاء/الفاتحة المتصلة بحواف الصورة (زي حلقة أو
    مربع أبيض حوالين لوجو PNG)، وتخليها شفافة تمامًا - من غير ما تلمس أي
    تفاصيل بيضاء جوه الرسمة نفسها (زي سماعة واتساب البيضاء وسط الفقاعة
    الخضرا) لأنها مش متصلة بحواف الصورة أصلاً (محاطة باللون الأخضر من كل
    الاتجاهات). بتستخدم Flood Fill يبدأ من حواف الصورة الأربعة، وبيمشي بس
    جوه البكسلات "شبه بيضاء" أو "شبه شفافة" المتصلة ببعض. بترجع صورة RGBA
    جديدة"""
    from collections import deque
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    def is_bgish(p):
        r, g, b, a = p
        return a <= alpha_threshold or (r >= threshold and g >= threshold and b >= threshold)

    visited = bytearray(w * h)
    dq = deque()

    def seed(x, y):
        idx = y * w + x
        if not visited[idx] and is_bgish(px[x, y]):
            visited[idx] = 1
            dq.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    while dq:
        x, y = dq.popleft()
        r, g, b, a = px[x, y]
        px[x, y] = (r, g, b, 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if not visited[idx] and is_bgish(px[nx, ny]):
                    visited[idx] = 1
                    dq.append((nx, ny))

    return img


def _make_circular_badge(pil_img, diameter, shadow=True):
    """
    بيحوّل أي صورة لوجو لبادچ دائري نظيف:
    - اللوجو نفسه مقصوص بشكل دائرة ومتوسط في المنتصف
    - ظل خفيف تحت البادچ لإحساس بالعمق
    من غير أي حلقة ملوّنة/ذهبية أو حلقة فاصلة حوالين اللوجو - اللوجو
    نفسه بس هو الظاهر على كانفاس شفاف بالكامل حواليه.
    بيرجع صورة PIL (RGBA) جاهزة للتحويل لـ CTkImage
    """
    pad = 10 if shadow else 2
    canvas_size = diameter + pad * 2
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    if shadow:
        shadow_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.ellipse([pad - 2, pad + 4, pad + diameter + 2, pad + diameter + 9],
                   fill=(15, 25, 40, 100))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(4))
        canvas = Image.alpha_composite(canvas, shadow_layer)

    img = pil_img.convert("RGBA")
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w - side) // 2 + side, (h - side) // 2 + side))
    img = img.resize((diameter, diameter), Image.LANCZOS)

    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter, diameter], fill=255)
    circular_logo = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    circular_logo.paste(img, (0, 0), mask)

    canvas.paste(circular_logo, (pad, pad), circular_logo)
    return canvas


_dentora_ico_cache_path = None


def _get_dentora_ico_path():
    """
    بيحوّل لوجو Dentora (PNG) لملف .ico حقيقي ويحفظه مرة واحدة بجانب الأصل.
    ده لازم لأن iconphoto لوحدها مش دايمًا بتظبط الأيقونة الصغيرة اللي في
    عنوان نافذة Toplevel على ويندوز - محتاجين iconbitmap بملف .ico فعلي.
    """
    global _dentora_ico_cache_path
    if _dentora_ico_cache_path and os.path.exists(_dentora_ico_cache_path):
        return _dentora_ico_cache_path
    if not os.path.exists(DENTORA_ICON_PATH):
        return None
    try:
        ico_path = os.path.join(os.path.dirname(DENTORA_ICON_PATH), "dentora_icon.ico")
        img = Image.open(DENTORA_ICON_PATH).convert("RGBA")
        img.save(ico_path, format="ICO",
                 sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        _dentora_ico_cache_path = ico_path
        return ico_path
    except Exception:
        return None


def _set_window_icon(window, image_path):
    """
    بتحط لوجو Dentora كأيقونة للنافذة (فوق يسار شريط العنوان + الـ taskbar).
    بنحاول بطريقتين مع بعض (iconphoto بالـ PNG و iconbitmap بملف .ico حقيقي)
    عشان نضمن ظهورها في عنوان النافذة نفسه، مش بس التاسك بار.
    وبنعيد المحاولة كذا مرة بفواصل زمنية مختلفة لإصلاح مشكلة معروفة في
    CustomTkinter/Windows بترجّع الأيقونة الافتراضية بعد جزء من الثانية.
    """
    if not image_path or not os.path.exists(image_path):
        return
    ico_path = _get_dentora_ico_path()

    def _apply():
        try:
            img = Image.open(image_path)
            photo = ImageTk.PhotoImage(img)
            window._app_icon_photo_ref = photo
            window.iconphoto(True, photo)
        except Exception:
            pass
        if ico_path:
            try:
                window.iconbitmap(ico_path)
            except Exception:
                pass

    _apply()
    for delay_ms in (100, 300, 600, 1200):
        window.after(delay_ms, _apply)


class LoginScreen(ctk.CTkToplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        settings = db.get_settings()
        # اسم النافذة وأيقونتها بيبقوا دايمًا باسم البرنامج "Dentora" الثابت،
        # مش اسم العيادة، عشان تفضل هوية البرنامج نفسه واضحة في شريط العنوان
        self.title("تسجيل الدخول - Dentora")
        self.geometry("400x580")
        self.resizable(False, False)
        self.configure(fg_color=theme.BG_MAIN)
        self.on_success = on_success
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))
        _set_window_icon(self, DENTORA_ICON_PATH)
        self._main_icon_photo = None
        self._clinic_icon_photo = None
        self._password_visible = False
        self.remember_var = ctk.BooleanVar(value=bool(settings.get("remember_login", 0)))
        self._build(settings)
        self._center_on_screen()

    def _center_on_screen(self):
        """بتخلي شاشة تسجيل الدخول تفتح في منتصف الشاشة تمامًا (أفقيًا ورأسيًا)"""
        self.update_idletasks()
        win_w = 400
        win_h = self.winfo_reqheight()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - win_w) // 2)
        y = max(0, (screen_h - win_h) // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def _build(self, settings):
        # شريط علوي ملوَّن بلون العيادة، وفوقه أيقونتان:
        # 1) أيقونة "Dentora" الرئيسية الكبيرة - ثابتة، دي هوية البرنامج نفسه
        # 2) أيقونة العيادة الفرعية - بتتغيّر حسب لوجو العيادة المسجَّل من الإعدادات،
        #    وبتظهر كبادچ متراكب على حافة الأيقونة الرئيسية (أسلوب شعارات فاخر)
        MAIN_ICON_D = 100
        SUB_ICON_D = 58

        # نجهّز صورتَي البادچ الأول عشان نعرف مقاساتهم بالظبط، ونحسب على أساسهم
        # مساحة العرض بالبكسل (بدل النسب) عشان محدش يتقطع من حواف المنطقة
        main_badge = None
        try:
            main_pil = Image.open(DENTORA_ICON_PATH)
            main_badge = _make_circular_badge(main_pil, MAIN_ICON_D, shadow=True)
        except Exception:
            main_badge = None

        sub_badge = None
        logo_path = settings.get("logo_path")
        if logo_path and os.path.exists(logo_path):
            try:
                clinic_pil = Image.open(logo_path)
                sub_badge = _make_circular_badge(clinic_pil, SUB_ICON_D, shadow=True)
            except Exception:
                sub_badge = None

        margin = 12
        main_w, main_h = main_badge.size if main_badge else (MAIN_ICON_D + 20, MAIN_ICON_D + 20)
        main_cx, main_cy = margin + main_w // 2, margin + main_h // 2
        zone_w, zone_h = margin + main_w, margin + main_h

        sub_cx = sub_cy = 0
        if sub_badge:
            sub_w, sub_h = sub_badge.size
            # مركز الأيقونة الفرعية على حافة الأيقونة الرئيسية (اتجاه قطري لأسفل ناحية اليمين)
            diag_offset = int((MAIN_ICON_D / 2) * 0.72)
            sub_cx, sub_cy = main_cx + diag_offset, main_cy + diag_offset
            zone_w = max(zone_w, sub_cx + sub_w // 2 + margin)
            zone_h = max(zone_h, sub_cy + sub_h // 2 + margin)

        # اسم البرنامج "Dentora" في الهيدر + اسم العيادة جنبه بين علامتي تنصيص.
        # الفونت هنا ثابت (رقم صريح) ومش مرتبط بأي إعداد ثيم ممكن يتغيّر لاحقًا
        HEADER_NAME_FONT = (theme.FONT_FAMILY, 22, "bold")
        clinic_name = (settings.get("clinic_name") or "").strip()
        header_text = f'Dentora - "{clinic_name}"' if clinic_name else "Dentora"

        # بنحسب ارتفاع سطر/سطرين النص مقدمًا (بدل ما نسيب pack يحسبه) عشان
        # هنرسم كل حاجة يدويًا على الكانفاس نفسه، مش عناصر CTk منفصلة فوقه
        text_wrap_w = 340
        tk_font = tkfont.Font(family=HEADER_NAME_FONT[0], size=HEADER_NAME_FONT[1], weight="bold")
        text_lines = 2 if tk_font.measure(header_text) > text_wrap_w else 1
        line_h = int(HEADER_NAME_FONT[1] * 1.5)
        text_block_h = line_h * text_lines

        top_pad, mid_gap, bottom_pad = 14, 6, 12
        header_h = top_pad + zone_h + mid_gap + text_block_h + bottom_pad

        # الهيدر بالكامل (اللوجوهات + النص) بيترسم على نفس الكانفاس المتدرج
        # (تدرج الخلفية) مباشرة - بدل ما تتحط عناصر CTk (فريمات/ليبلز) فوقه
        # بـ fg_color="transparent"، لإن الشفافية بتاعة CTk بتتحسب من لون
        # الودجت الأب المُعرَّف (اللي هو لون صلب واحد)، مش من الرسمة الفعلية
        # للتدرج اللي فوقها - وده كان بيظهر كمربع/خلفية صلدة منفصلة خلف كل
        # لوجو والنص بدل ما يبانوا شفافين فعلاً فوق التدرج. الرسم المباشر على
        # نفس الكانفاس بيضمن إن مفيش أي خلفية تانية غير التدرج نفسه
        header = ctk.CTkFrame(self, fg_color=settings["primary_color"], corner_radius=0,
                               height=header_h)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_canvas = tk.Canvas(header, highlightthickness=0, bd=0)
        header_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self._main_icon_photo = None
        self._clinic_icon_photo = None

        def _redraw_login_header(event=None):
            header_canvas.delete("all")
            w = header.winfo_width()
            h = header.winfo_height()
            if w <= 1 or h <= 1:
                return
            theme.draw_vertical_gradient(header_canvas, w, h, theme.HEADER_GRAD_START, theme.HEADER_GRAD_END)

            zone_x0 = (w - zone_w) / 2  # نوسّط منطقة اللوجوهات أفقيًا
            zone_y0 = top_pad

            if main_badge:
                self._main_icon_photo = ImageTk.PhotoImage(main_badge)
                header_canvas.create_image(zone_x0 + main_cx, zone_y0 + main_cy,
                                            image=self._main_icon_photo, tags="loginheader")
            else:
                header_canvas.create_text(zone_x0 + main_cx, zone_y0 + main_cy, text="🦷",
                                           font=(theme.FONT_FAMILY, 44), fill="#FFFFFF",
                                           tags="loginheader")

            if sub_badge:
                self._clinic_icon_photo = ImageTk.PhotoImage(sub_badge)
                header_canvas.create_image(zone_x0 + sub_cx, zone_y0 + sub_cy,
                                            image=self._clinic_icon_photo, tags="loginheader")

            text_y = top_pad + zone_h + mid_gap + text_block_h / 2
            header_canvas.create_text(w / 2, text_y, text=header_text, font=HEADER_NAME_FONT,
                                       fill="#FFFFFF", width=text_wrap_w, justify="center",
                                       tags="loginheader")

        header.bind("<Configure>", _redraw_login_header)
        header.after(50, _redraw_login_header)

        _make_accent_divider(self).pack(fill="x")

        card = ctk.CTkFrame(self, fg_color=theme.CARD_BG, corner_radius=14)
        card.pack(fill="both", expand=True, padx=24, pady=(20, 24))

        users = [u for u in db.get_all_users() if u["active"]]
        if not users:
            ctk.CTkLabel(card, text="لا يوجد مستخدمون مفعَّلون. راجع قاعدة البيانات.",
                         font=theme.FONT_NORMAL, wraplength=300).pack(pady=30)
            return

        self.user_map = {
            f"{u['full_name']} ({db.ROLE_LABELS.get(u['role'], u['role'])})": u for u in users
        }
        names = list(self.user_map.keys())

        self.require_password = bool(settings.get("require_password", 1))

        # لو خاصية "تذكرني" مفعّلة ومتسجل اسم مستخدم سابق، بنرشّه تلقائي في القايمة
        remembered_username = settings.get("remembered_username")
        self._remembered_username = remembered_username
        default_name = names[0]
        if remembered_username:
            for display_name, u in self.user_map.items():
                if u["username"] == remembered_username:
                    default_name = display_name
                    break

        # نفس فونت عناوين أيام الأسبوع في صفحة المواعيد (نفس العائلة والحجم المعتمدين
        # في الثيم)، عشان القايمة المنسدلة واختيار المستخدم الظاهر يبقوا متناسقين
        dropdown_font = (theme.CONTENT_FONT_FAMILY, theme.CONTENT_FONT_SIZE, "bold")

        ctk.CTkLabel(card, text="المستخدم",
                     font=(theme.FONT_FAMILY, theme.CONTENT_FONT_SIZE, "bold"),
                     text_color=theme.INPUT_LABEL_COLOR, anchor="e").pack(fill="x", padx=32, pady=(24, 2))
        self.user_var = ctk.StringVar(value=default_name)
        user_menu = ctk.CTkOptionMenu(card, values=names, variable=self.user_var, height=40,
                                       fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                                       button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                                       font=dropdown_font, dropdown_font=dropdown_font,
                                       command=lambda _v: self._on_user_selection_changed())
        user_menu.pack(fill="x", padx=32, pady=(2, 16))

        self.password_entry = None
        self.toggle_eye_btn = None
        if self.require_password:
            ctk.CTkLabel(card, text="كلمة المرور",
                         font=(theme.FONT_FAMILY, theme.CONTENT_FONT_SIZE, "bold"),
                         text_color=theme.INPUT_LABEL_COLOR, anchor="e").pack(fill="x", padx=32)

            pw_row = ctk.CTkFrame(card, fg_color="transparent")
            pw_row.pack(fill="x", padx=32, pady=(2, 4))
            self.password_entry = ctk.CTkEntry(pw_row, show="*", height=46, justify="right",
                                                font=theme.FONT_NORMAL)
            theme.apply_sunken_style(self.password_entry)
            self.password_entry.pack(side="right", fill="x", expand=True)
            self.password_entry.bind("<Return>", lambda e: self._try_login())

            self.toggle_eye_btn = ctk.CTkButton(
                pw_row, text="👁", width=46, height=46, font=(theme.FONT_FAMILY, 15),
                fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                hover_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                command=self._toggle_password_visibility)
            self.toggle_eye_btn.pack(side="left", padx=(6, 0))
        else:
            ctk.CTkLabel(card, text="تسجيل الدخول بدون كلمة مرور مفعّل حاليًا",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(pady=(8, 6))

        # صندوق "تذكرني" - لو متفعّل، هيترشّح نفس المستخدم تلقائيًا في المرة
        # الجاية (من غير حفظ كلمة المرور لأسباب أمنية)
        self.remember_checkbox = ctk.CTkCheckBox(
            card, text="تذكرني", variable=self.remember_var,
            font=(theme.FONT_FAMILY, theme.CONTENT_FONT_SIZE), text_color=theme.TEXT_DARK,
            fg_color=theme.CARD_BG, hover_color=theme.INPUT_SUNKEN_BG,
            checkmark_color=theme.TEXT_DARK, border_color=theme.BORDER,
            checkbox_width=20, checkbox_height=20)
        self.remember_checkbox.pack(anchor="e", padx=32, pady=(2, 4))

        self.error_label = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL,
                                         text_color=theme.DANGER)
        self.error_label.pack(pady=4)

        # زرار الدخول (أخضر - أساسي) وزرار الخروج (أحمر - ثانوي) جنب بعض، وبنفس
        # أسلوب الظل (make_shadowed_button) عشان يبقوا متناسقين بصريًا.
        # المقاس: ارتفاعهم أصغر 20% من الأصل (48 -> ~38)، ومساحتهم مجتمعين
        # (الزرارين + المسافة بينهم) = نص عرض السطر الأفقي بس (عرض الكارت)،
        # ومتوسطين في النص مع مسافة بينية معقولة
        buttons_row = ctk.CTkFrame(card, fg_color="transparent")
        buttons_row.pack(pady=(16, 10))

        LOGIN_DIALOG_W = 400
        CARD_PADX = 24
        card_content_w = LOGIN_DIALOG_W - 2 * CARD_PADX
        half_line_w = card_content_w // 2
        btn_gap = 16
        btn_w = (half_line_w - btn_gap) // 2
        btn_h = int(48 * 0.8)  # تصغير رأسي 20%

        login_wrapper = theme.make_shadowed_button(
            buttons_row, "دخول", command=self._try_login, width=btn_w, height=btn_h,
            font=theme.FONT_SUBTITLE)
        login_wrapper.pack(side="right", padx=(btn_gap // 2, 0))

        exit_wrapper = theme.make_shadowed_button(
            buttons_row, "خروج", command=lambda: os._exit(0), width=btn_w, height=btn_h,
            fg_color=theme.DANGER, font=theme.FONT_SUBTITLE)
        exit_wrapper.pack(side="left", padx=(0, btn_gap // 2))

        # مؤشر الكتابة يتحط تلقائيًا في صندوق كلمة السر لما الشاشة تظهر. بنعيد
        # المحاولة كذا مرة بفواصل زمنية مختلفة (مش مرة واحدة) عشان نضمن إنها
        # تتحط فعليًا مهما كان توقيت ظهور النافذة واستلامها الـ grab من الويندوز
        if self.password_entry is not None:
            self._focus_password_field()
            for delay_ms in (80, 200, 400, 700):
                self.after(delay_ms, self._focus_password_field)

    def _on_user_selection_changed(self):
        """لو المستخدم غيّر الاختيار من القايمة، بنفضّي حقل كلمة المرور عشان
        المستخدم الجديد يكتب كلمة مروره هو"""
        if self.password_entry is None:
            return
        self.password_entry.delete(0, "end")

    def _focus_password_field(self):
        try:
            self.lift()
            self.focus_force()
            self.password_entry.focus_force()
            self.password_entry.icursor("end")
        except Exception:
            pass

    def _toggle_password_visibility(self):
        self._password_visible = not self._password_visible
        self.password_entry.configure(show="" if self._password_visible else "*")
        self.toggle_eye_btn.configure(text="🙈" if self._password_visible else "👁")

    def _try_login(self):
        selected = self.user_map.get(self.user_var.get())
        if not selected:
            return

        if not self.require_password:
            # الباسورد متوقف من إعدادات العيادة أصلًا - الدخول مباشرة
            db.set_remembered_login(selected["username"], self.remember_var.get())
            self.destroy()
            self.on_success(selected)
            return

        password = self.password_entry.get() if self.password_entry is not None else ""
        user = db.authenticate_user(selected["username"], password)
        if user:
            # لو "تذكرني" مفعّلة، بنحفظ اسم المستخدم المختار بس (من غير كلمة المرور)
            # عشان يترشّح تلقائيًا في المرة الجاية. لو مش مفعّلة، بنمسح الترشيح
            db.set_remembered_login(user["username"], self.remember_var.get())
            self.destroy()
            self.on_success(user)
        else:
            self.error_label.configure(text="كلمة المرور غلط، حاول تاني")


class ClinicApp(ctk.CTk):
    RIBBON_ITEMS = [
        ("appointments", "calendar", "المواعيد", "view_appointments"),
        ("patients", "person", "المرضى", "view_patients"),
        ("prices", "tag", "الإجراءات", "manage_prices"),
        ("staff", "team", "طاقم العمل", "manage_staff"),
        ("materials", "toolbox", "المصروفات", "manage_expenses"),
        ("accounts", "wallet", "الحسابات", "view_clinic_accounts"),
        ("labs", "factory", "المعامل", "manage_labs"),
        ("n8n", "gear", "تكامل n8n", "always"),
        ("settings", "gear", "الإعدادات", "always"),
    ]

    def __init__(self):
        super().__init__()

        db.init_db()
        self.settings = db.get_settings()
        theme.apply_from_settings(self.settings)
        icons.set_icon_pattern(self.settings.get("icon_pattern", "outline"))

        # اسم النافذة وأيقونتها بيبقوا دايمًا باسم البرنامج "Dentora" الثابت + اسم
        # العيادة جنبه - بنفس منطق شاشة تسجيل الدخول بالظبط، عشان هوية البرنامج
        # تفضل واضحة في كل حتة (مش اسم/لوجو العيادة المتغيّر بس)
        clinic_name = (self.settings.get("clinic_name") or "").strip()
        self.title(f'Dentora - "{clinic_name}"' if clinic_name else "Dentora")
        _set_window_icon(self, DENTORA_ICON_PATH)
        self.geometry("1200x750")
        self.minsize(1000, 650)
        self._maximize_window()
        self.configure(fg_color=theme.BG_MAIN)

        self.current_page = None
        self.nav_buttons = {}
        self.current_user = None

        self.withdraw()  # مخفي لحد ما يدخل المستخدم بنجاح
        LoginScreen(self, on_success=self._on_login_success)

    def _maximize_window(self):
        """تكبّر نافذة البرنامج لتملأ الشاشة بالكامل (Full Screen). بنجرب أكتر
        من طريقة لأن حالة "zoomed" أحيانًا ما بتثبتش من أول مرة على ويندوز -
        خصوصًا لو اتنادت والنافذة لسه مخفية (withdraw) قبل ما تتعرض فعليًا."""
        try:
            self.state("zoomed")  # ويندوز، وبعض توزيعات لينكس
            return
        except Exception:
            pass
        try:
            self.attributes("-zoomed", True)  # لينكس (بعض مديري النوافذ)
            return
        except Exception:
            pass
        try:
            # آخر حل احتياطي: نطابق حجم النافذة مع حجم الشاشة بالكامل يدويًا
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        except Exception:
            pass

    def _apply_window_icon(self):
        """[محتفظ بيها للتوافق لو أي كود تاني بينادي عليها] - بتحط أيقونة
        البرنامج الثابتة (Dentora) على النافذة، بدل ما كانت بتحط لوجو العيادة"""
        _set_window_icon(self, DENTORA_ICON_PATH)

    def _logout(self):
        """Log out the current user and show the login screen again."""
        self.withdraw()
        LoginScreen(self, on_success=self._on_login_success)

    def _on_login_success(self, user):
        self.current_user = user
        self.deiconify()
        self._maximize_window()
        self.update_idletasks()

        # لازم نطبّق تفضيلات المظهر الشخصية بتاعة المستخدم اللي دخل بنجاح
        # (لو عنده أي تخصيص محفوظ)، عشان أكتر من شخص يقدروا يستخدموا نفس
        # الجهاز وكل واحد يشوف الثيم/الخط اللي يريحه هو، من غير ما يأثر
        # على تفضيلات زمايله
        self.settings = db.get_effective_settings(user["id"])
        theme.apply_from_settings(self.settings)
        icons.set_icon_pattern(self.settings.get("icon_pattern", "outline"))
        self.configure(fg_color=theme.BG_MAIN)

        self._build_sidebar()
        self._build_content_area()
        self.show_page("appointments")
        # WhatsApp auto-archive removed - replaced by n8n integration
        # (API key stored in environment variable N8N_API_KEY)

    def _can_access(self, permission_key):
        if permission_key is None:
            return False
        if permission_key == "always":
            return True
        return db.has_permission(self.current_user["role"], permission_key)

    # ---------------- الشريط العلوي (Ribbon) ----------------
    # الهيدر بالكامل (اللوجو/اسم العيادة/المستخدم + كل أزرار الأيقونات)
    # بيتترسم يدويًا فوق نفس Canvas التدرج بتاع الهيدر (مش ودجتس CTk منفصلة
    # فوقه) - لأن أي CTkFrame/CTkButton، حتى لو fg_color="transparent"،
    # بيرسم خلفيته بلون صلب واحد بيغطي التدرج اللي وراه (شوف ctk_frame.py:
    # fg_color="transparent" بيترسم بـ self._bg_color اللي هو لون صلب محسوب،
    # مش تمرير حقيقي للي مرسوم عليه Canvas تاني). فبدل ما نكرر المشكلة دي في
    # كل عنصر، بنرسم كل حاجة (اللوجو/النصوص/الأزرار) مباشرة على نفس الـ
    # Canvas اللي فيه التدرج، فيبقى فعليًا خلفية واحدة متدرجة من غير أي
    # "إطارات" أو "بقع" صلبة فوقها.

    NAV_BAR_HEIGHT = 62
    NAV_BTN_GAP = 8

    def _build_top_nav(self):
        primary = self.settings["primary_color"]

        self.nav_bar = ctk.CTkFrame(self, height=self.NAV_BAR_HEIGHT, fg_color=primary, corner_radius=0)
        if hasattr(self, "content_area") and self.content_area.winfo_exists():
            self.nav_bar.pack(side="top", fill="x", before=self.content_area)
        else:
            self.nav_bar.pack(side="top", fill="x")
        self.nav_bar.pack_propagate(False)

        self.nav_canvas = tk.Canvas(self.nav_bar, highlightthickness=0, bd=0)
        self.nav_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.nav_bar.bind("<Configure>", self._redraw_nav_bar)
        self.nav_bar.after(50, self._redraw_nav_bar)

        # بدل ما نعتمد على <Enter>/<Leave> منفصلة لكل عنصر جوه الزرار
        # (الخلفية + الأيقونة + النص)، اللي بيسببوا "رعشة"/تهنيج لما الماوس
        # يعدي من فوق الخلفية على الأيقونة (لأنهم عناصر Canvas مختلفة حتى
        # لو بنفس التاج، فبيتسجل Leave يليه Enter فورًا كل ما الماوس يهتز
        # شعرة فوق حدود الأيقونة، وده بيعمل إنشاء/حذف متكرر جدًا للعناصر)،
        # بنستخدم Motion واحد على مستوى الـ Canvas كله، وبنحسب إحنا فين
        # الماوس بالنسبة لمربعات الأزرار المحفوظة، ومنغيّرش حاجة إلا لما
        # الزرار المستهدف نفسه يتغيّر - فبيبقى فيه رسم واحد بس عند الدخول
        # وواحد بس عند الخروج، مش عشرات المرات في الثانية
        self._hovered_nav_key = None
        self.nav_canvas.bind("<Motion>", self._on_nav_motion)
        self.nav_canvas.bind("<Leave>", self._on_nav_canvas_leave)
        # الضغط بقى محسوب بنفس طريقة الهوفر (إحداثيات الماوس على مربعات
        # الأزرار المحفوظة)، مش عن طريق tag_bind على كل زرار لوحده - لأن
        # طبقة تظليل الهوفر (الشكل الشفاف اللي بيترسم فوق الزرار) كانت
        # بتمنع حدث الضغط إنه يوصل للطبقة اللي تحتها، فكانت الأزرار بتوقف
        # عن الاستجابة للكليك بمجرد ما تحصلها هوفر (يعني كل مرة تقريبًا!)
        self.nav_canvas.bind("<Button-1>", self._on_nav_click)

        self.nav_divider = _make_accent_divider(self)
        if hasattr(self, "content_area") and self.content_area.winfo_exists():
            self.nav_divider.pack(side="top", fill="x", before=self.content_area)
        else:
            self.nav_divider.pack(side="top", fill="x")

    def _redraw_nav_bar(self, event=None):
        """بيرسم خلفية الهيدر المتدرجة بالكامل، وفوقها اللوجو/النصوص/كل
        أزرار الشريط - كل ده على نفس الـ Canvas عشان الخلفية تفضل تدرج
        متصل من غير أي مساحات صلبة. بتتنادى أول مرة، وكل مرة يتغيّر فيها
        حجم النافذة، وكل مرة تتغيّر فيها الصفحة النشطة (لتحديث تظليل التاب)"""
        if not hasattr(self, "nav_canvas") or not self.nav_canvas.winfo_exists():
            return
        canvas = self.nav_canvas
        w = self.nav_bar.winfo_width()
        h = self.nav_bar.winfo_height()
        if w <= 1 or h <= 1:
            return
        canvas.delete("all")
        self._nav_img_refs = []  # مرجع دائم يمنع صور الأيقونات من الاختفاء (garbage collection)
        theme.draw_vertical_gradient(canvas, w, h, theme.HEADER_GRAD_START, theme.HEADER_GRAD_END)
        self._draw_nav_logo(canvas, h)
        self._draw_nav_buttons(canvas, w, h)

    def _draw_nav_logo(self, canvas, h):
        """بيرسم لوجو Dentora + اسم البرنامج/العيادة/المستخدم مباشرة على
        الـ Canvas (من غير أي خلفية خاصة بيهم) - فيفضل التدرج بتاع الهيدر
        بادي كامل من وراهم، بدل اللوحة الصلبة اللي كانت موجودة قبل كده"""
        from PIL import ImageTk
        cy = h / 2
        x = 16

        # الشريط بقى أقصر من قبل (هوامش الأزرار اتقللت)، فبنحسب مقاس
        # اللوجو والخطوط هنا كنسبة من ارتفاع الشريط الفعلي بدل مقاسات
        # ثابتة، عشان اللوجو/الاسم يفضلوا متناسقين وما يخرجوش برة حدود
        # الشريط لما يبقى أقصر
        scale = max(0.55, min(1.0, h / 104))
        if os.path.exists(DENTORA_ICON_PATH):
            try:
                img = Image.open(DENTORA_ICON_PATH).convert("RGBA")
                logo_h = max(int(48 * scale), 22)
                ratio = img.width / img.height if img.height else 1
                logo_w = max(int(logo_h * ratio), 1)
                img = img.resize((logo_w, logo_h), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._nav_img_refs.append(photo)
                canvas.create_image(x, cy, anchor="w", image=photo, tags="navcontent")
                x += logo_w + 10
            except Exception:
                pass

        title_font = (theme.FONT_TITLE[0], max(int(theme.FONT_TITLE[1] * scale), 12), "bold")
        subtitle_font = (theme.FONT_SUBTITLE[0], max(int(theme.FONT_SUBTITLE[1] * scale), 11), "bold")
        small_font = (theme.FONT_SMALL[0], max(int(theme.FONT_SMALL[1] * scale), 10))

        clinic_name = (self.settings.get("clinic_name") or "").strip()
        role_label = db.ROLE_LABELS.get(self.current_user["role"], self.current_user["role"])
        lines = [("Dentora", title_font, "#FFFFFF")]
        if clinic_name:
            lines.append((clinic_name, subtitle_font, "#EAF2FF"))
        lines.append((f"{self.current_user['full_name']} - {role_label}", small_font, "#E3F2FD"))

        # نحسب ارتفاع كل سطر تقريبيًا من حجم الخط عشان نرص السطور فوق بعض
        # ونوسّطهم رأسيًا كمجموعة واحدة في نص ارتفاع الهيدر (زي ما كانوا
        # بيتوسّطوا تلقائيًا لما كانوا جوه إطار بـ pack)
        line_heights = [max(int(font[1] * 1.35), 14) for _, font, _ in lines]
        total_h = sum(line_heights)
        y = cy - total_h / 2
        for (text, font, color), lh in zip(lines, line_heights):
            canvas.create_text(x, y + lh / 2, anchor="w", text=text, font=font,
                                fill=color, tags="navcontent")
            y += lh

    def _draw_nav_buttons(self, canvas, w, h):
        self.nav_buttons = {}
        self._nav_button_bounds = []  # [(key, x1, y1, x2, y2, enabled), ...] لحساب الهوفر بالماوس
        icon_size = self._ribbon_icon_size()
        show_labels = bool(self.settings.get("show_ribbon_labels", 1))
        btn_w, btn_h = self.RIBBON_BTN_WIDTH, self.RIBBON_BTN_HEIGHT
        y1 = (h - btn_h) / 2
        y2 = y1 + btn_h
        x_cursor = w - 14

        items = list(self.RIBBON_ITEMS) + [("exit", "door", "خروج", True)]
        extra_gap_before = {"exit": 10}  # فاصل زيادة قبل زرار الخروج عشان يبان منفصل شوية

        for key, icon_name, label, permission in items:
            x_cursor -= extra_gap_before.get(key, 0)
            x2 = x_cursor
            x1 = x2 - btn_w
            enabled = True if key == "exit" else self._can_access(permission)
            self._draw_one_nav_button(canvas, key, icon_name, label, x1, y1, x2, y2,
                                       enabled, icon_size, show_labels)
            if key != "exit":
                self.nav_buttons[key] = (x1, y1, x2, y2)
            self._nav_button_bounds.append((key, x1, y1, x2, y2, enabled))
            x_cursor = x1 - self.NAV_BTN_GAP

        # لو الماوس أصلًا واقف فوق الشريط وقت إعادة الرسم (مثلاً بعد تغيير
        # حجم النافذة)، لازم نعيد حساب/رسم حالة الهوفر على المربعات الجديدة
        # بدل ما تفضل حالة الهوفر القديمة (المرسومة على إحداثيات قديمة) زي
        # ما هي أو تختفي فجأة
        self._hovered_nav_key = None
        self.nav_canvas.after_idle(self._sync_nav_hover_to_pointer)

    def _sync_nav_hover_to_pointer(self):
        if not hasattr(self, "nav_canvas") or not self.nav_canvas.winfo_exists():
            return
        try:
            x = self.nav_canvas.winfo_pointerx() - self.nav_canvas.winfo_rootx()
            y = self.nav_canvas.winfo_pointery() - self.nav_canvas.winfo_rooty()
        except Exception:
            return
        self._update_nav_hover(x, y)

    def _find_nav_button_at(self, x, y):
        for key, x1, y1, x2, y2, enabled in getattr(self, "_nav_button_bounds", []):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return key
        return None

    def _update_nav_hover(self, x, y):
        """المصدر الوحيد لرسم/مسح تظليل الهوفر - بيتنادى من Motion على
        الـ Canvas كله، وبيغيّر حاجة بصريًا بس لو الزرار اللي تحت الماوس
        اتغيّر فعلًا (مش عند كل حركة بكسل واحد)، عشان يمنع الرعشة والتهنيج"""
        if not hasattr(self, "nav_canvas") or not self.nav_canvas.winfo_exists():
            return
        key = self._find_nav_button_at(x, y)
        if key == self._hovered_nav_key:
            return
        canvas = self.nav_canvas
        if self._hovered_nav_key is not None:
            canvas.delete(f"navhover_{self._hovered_nav_key}")
        self._hovered_nav_key = key
        if key is not None:
            style = self.settings.get("nav_button_style", "classic")
            hover_color = theme.NAV_LUXURY_GOLD if style == "luxury" else "#FFFFFF"
            hover_radius = {"glass": 15, "luxury": 7}.get(style, 9)
            for bkey, x1, y1, x2, y2, enabled in self._nav_button_bounds:
                if bkey == key:
                    hover_pts = theme.rounded_rect_points(x1 + 1, y1 + 1, x2 - 1, y2 - 1, hover_radius)
                    canvas.create_polygon(hover_pts, smooth=True, fill="", outline=hover_color,
                                           width=2, tags=(f"navhover_{key}", "navcontent"))
                    break
            canvas.configure(cursor="hand2")
        else:
            canvas.configure(cursor="")

    def _on_nav_motion(self, event):
        self._update_nav_hover(event.x, event.y)

    def _on_nav_canvas_leave(self, _event=None):
        self._update_nav_hover(-1, -1)

    def _on_nav_click(self, event):
        key = self._find_nav_button_at(event.x, event.y)
        if key is None:
            return
        enabled = True
        for bkey, x1, y1, x2, y2, benabled in getattr(self, "_nav_button_bounds", []):
            if bkey == key:
                enabled = benabled
                break
        if enabled:
            self.show_page(key)
        else:
            self._show_blocked(key)

    def _draw_one_nav_button(self, canvas, key, icon_name, label, x1, y1, x2, y2,
                              enabled, icon_size, show_labels):
        from PIL import ImageTk
        tag = f"navbtn_{key}"
        active = (key == getattr(self, "_active_nav_key", None))
        style = self.settings.get("nav_button_style", "classic")

        if style == "glass":
            icon_color = self._draw_nav_btn_bg_glass(canvas, tag, x1, y1, x2, y2, active, enabled)
        elif style == "luxury":
            icon_color = self._draw_nav_btn_bg_luxury(canvas, tag, x1, y1, x2, y2, active, enabled)
        else:
            icon_color = self._draw_nav_btn_bg_classic(canvas, tag, x1, y1, x2, y2, active, enabled)

        cx = (x1 + x2) / 2
        if show_labels and label:
            icon_cy = y1 + (y2 - y1 - 24) / 2
            label_y = y2 - 12
        else:
            icon_cy = (y1 + y2) / 2
            label_y = None

        icon_img = self._icon_pil_for(icon_name, icon_size, icon_color, style)
        if icon_img is not None:
            photo = ImageTk.PhotoImage(icon_img)
            self._nav_img_refs.append(photo)
            canvas.create_image(cx, icon_cy, image=photo, tags=(tag, "navcontent"))

        if label_y is not None:
            text_color = icon_color
            canvas.create_text(cx, label_y, text=label, font=theme.FONT_SMALL,
                                fill=text_color, tags=(tag, "navcontent"))

        # ملحوظة: تظليل الهوفر (outline أبيض عند مرور الماوس) والضغط بالكليك
        # بقوا بيتحسبوا مركزيًا بإحداثيات الماوس في _update_nav_hover و
        # _on_nav_click (مربوطين على الـ Canvas كله)، مش هنا لكل عنصر لوحده:
        # 1) لو ربطنا Enter/Leave على كل عنصر (خلفية/أيقونة/نص) لوحده، كانت
        #    بتحصل رعشة/تهنيج كل ما الماوس يعدي من فوق حواف الأيقونة جوه
        #    الزرار (Tkinter بيعتبرهم دخول/خروج متكرر رغم إنهم نفس التاج).
        # 2) وطبقة تظليل الهوفر الشفافة اللي بترتسم فوق الزرار كانت بتمنع
        #    حدث الـ Button-1 المربوط بالتاج إنه يوصل لعناصر الزرار اللي
        #    تحتها - فكان الكليك بيبقى شغال من غير هوفر بس بيقف تمامًا وقت
        #    وجود الهوفر (يعني الغالبية العظمى من محاولات الكليك الحقيقية)

    def _draw_nav_btn_bg_classic(self, canvas, tag, x1, y1, x2, y2, active, enabled):
        """التصميم الكلاسيكي الأصلي: كارت بلون التدرج/أبيض + ظل وبرواز رفيع"""
        if active:
            bg_color = theme.CARD_BG
            icon_color = self.settings["primary_color"]
        else:
            t = max(0.0, min(1.0, ((y1 + y2) / 2) / max(self.nav_bar.winfo_height(), 1)))
            bg_color = theme._lerp_color(theme.HEADER_GRAD_START, theme.HEADER_GRAD_END, t)
            icon_color = "#FFFFFF" if enabled else "#D8D8D8"

        pts = theme.rounded_rect_points(x1, y1, x2, y2, 10)
        shadow_pts = theme.rounded_rect_points(x1 + 1, y1 + 2, x2 + 1, y2 + 2, 10)
        shadow_color = theme.darken_color(bg_color, 0.65)
        canvas.create_polygon(shadow_pts, smooth=True, fill=shadow_color, outline=shadow_color,
                               tags=(tag, "navcontent"))

        frame_color = theme.BORDER if active else theme.lighten_color(bg_color, 0.35)
        canvas.create_polygon(pts, smooth=True, fill=bg_color, outline=frame_color, width=1,
                               tags=(tag, "navcontent"))
        return icon_color

    def _nav_style_img_cache(self, cache_name):
        cache = getattr(self, cache_name, None)
        if cache is None:
            cache = {}
            setattr(self, cache_name, cache)
        return cache

    def _draw_nav_btn_bg_glass(self, canvas, tag, x1, y1, x2, y2, active, enabled):
        """تصميم زجاجي عصري (Glassmorphism): كارت شفاف بحواف مضيئة، بيتشكّل
        بصورة PIL بقناة ألفا حقيقية عشان يبان شفاف فعلًا فوق تدرج الهيدر"""
        from PIL import ImageTk
        w, h = int(round(x2 - x1)), int(round(y2 - y1))
        cache = self._nav_style_img_cache("_nav_glass_img_cache")
        key = (w, h, active, enabled)
        img = cache.get(key)
        if img is None:
            img = theme.make_glass_nav_card(w, h, radius=16, active=active, enabled=enabled)
            cache[key] = img
        photo = ImageTk.PhotoImage(img)
        self._nav_img_refs.append(photo)
        canvas.create_image(x1, y1, anchor="nw", image=photo, tags=(tag, "navcontent"))
        # منطقة شفافة بالكامل فوق الصورة عشان الهوفر/الكليك يتحسبوا صح
        # (الحساب أصلًا بيتم بإحداثيات مربعات الأزرار المحفوظة، مش بعنصر
        # الكانفاس نفسه، فمفيش داعي لمضلّع إضافي هنا)
        if active:
            return self.settings["primary_color"]
        return "#FFFFFF" if enabled else "#DCE3EE"

    def _draw_nav_btn_bg_luxury(self, canvas, tag, x1, y1, x2, y2, active, enabled):
        """تصميم فاخر بحواف ذهبية: كارت غامق متدرج + برواز ذهبي رفيع، وشريط
        ذهبي صغير أسفل الزرار النشط - إحساس شعار/بادچ رسمي فخم"""
        from PIL import ImageTk
        w, h = int(round(x2 - x1)), int(round(y2 - y1))
        cache = self._nav_style_img_cache("_nav_luxury_img_cache")
        key = (w, h, active, enabled)
        img = cache.get(key)
        if img is None:
            img = theme.make_luxury_nav_card(w, h, radius=8, active=active, enabled=enabled)
            cache[key] = img
        photo = ImageTk.PhotoImage(img)
        self._nav_img_refs.append(photo)
        canvas.create_image(x1, y1, anchor="nw", image=photo, tags=(tag, "navcontent"))
        if active:
            return theme.NAV_LUXURY_GOLD
        return "#F3E9CE" if enabled else "#8A8478"

    # مسار أيقونة واتساب الرسمية (PNG) التي تحل محل الأيقونة المرسومة برمجيًا
    WHATSAPP_ICON_PATH = os.path.join(APP_ROOT, "assets", "whatsapp_icon.png")

    def _whatsapp_icon_pil(self, size=26):
        """تحمّل أيقونة واتساب الرسمية من assets/whatsapp_icon.png وتُبقيها
        بنفس شكلها ولونها الأخضر المميز دائمًا (بدلًا من تلوينها حسب حالة
        الزر، على عكس باقي أيقونات الشريط). بترجع صورة PIL خام (RGBA) - مش
        CTkImage - عشان ترتسم مباشرة على Canvas الهيدر. النتيجة مخزّنة
        مؤقتًا (cache) لكل حجم مطلوب. لو الملف مش موجود، بترجع لرسمها
        برمجيًا كخطة احتياطية حتى لا يتعطل شريط التنقل.

        أي خلفية بيضاء/فاتحة جدًا حوالين شكل الفقاعة والسماعة في ملف
        الصورة الأصلي بتتشال (تتحول لشفافة) عشان يبان بس شكل الفقاعة
        والسماعة نفسهم مباشرة فوق خلفية الزرار، من غير أي مربع/دائرة
        بيضاء خلفهم"""
        if not hasattr(self, "_whatsapp_icon_pil_cache"):
            self._whatsapp_icon_pil_cache = {}
        if size in self._whatsapp_icon_pil_cache:
            return self._whatsapp_icon_pil_cache[size]

        try:
            img = Image.open(self.WHATSAPP_ICON_PATH).convert("RGBA")
            img = _strip_light_background(img)
            img = img.resize((size, size), Image.LANCZOS)
        except Exception:
            img = self._draw_whatsapp_icon_fallback_pil(size)

        self._whatsapp_icon_pil_cache[size] = img
        return img

    def _draw_whatsapp_icon_fallback_pil(self, size=26):
        """ترسم أيقونة واتساب (فقاعة خضراء بلونها المميز + سماعة بيضاء) برمجيًا -
        تُستخدم فقط احتياطيًا لو تعذّر تحميل ملف assets/whatsapp_icon.png"""
        scale = 4
        s = size * scale
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        green = (37, 211, 102, 255)  # #25D366 - أخضر واتساب المميز

        margin = s * 0.03
        draw.ellipse([margin, margin, s - margin, s - margin], fill=green)
        tail = [(s * 0.20, s * 0.87), (s * 0.05, s * 0.99), (s * 0.29, s * 0.79)]
        draw.polygon(tail, fill=green)

        white = (255, 255, 255, 255)
        cx, cy = s * 0.50, s * 0.49
        handset = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        hd = ImageDraw.Draw(handset)
        bw, bh = s * 0.085, s * 0.34
        hd.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2],
                              radius=bw / 2, fill=white)
        r = s * 0.10
        hd.ellipse([cx - r, cy - bh / 2 - r * 0.9, cx + r, cy - bh / 2 + r * 1.1], fill=white)
        hd.ellipse([cx - r, cy + bh / 2 - r * 1.1, cx + r, cy + bh / 2 + r * 0.9], fill=white)
        handset = handset.rotate(-45, resample=Image.BICUBIC, center=(cx, cy))
        img.alpha_composite(handset)

        return img.resize((size, size), Image.LANCZOS)

    def _icon_pil_for(self, icon_name, size, color, style="classic"):
        """تُعيد صورة PIL الخام للأيقونة المناسبة: لون ثابت لأيقونة واتساب،
        وإلا الأيقونة المعتادة الملوَّنة حسب حالة الزر وحسب التصميم (style)
        المختار حاليًا لشريط التنقل (classic/glass/luxury)"""
        if icon_name == "chat":
            return self._whatsapp_icon_pil(size)
        return icons.get_icon_pil(icon_name, size=size, color=color, style=style)

    # مقاسات زرار الشريط العلوي - ثابتة عشان نحسب عليها مقاس الأيقونة
    RIBBON_BTN_WIDTH = 66
    RIBBON_BTN_HEIGHT = 54

    def _ribbon_icon_size(self):
        """بتحسب أنسب مقاس للأيقونة عشان تملى مساحة الزرار قد الإمكان،
        سواء كان فيه مسمى نصي تحتها ولا لأ. لو حصل أي خطأ في الحساب،
        بترجع مقاس افتراضي آمن بدل ما تكسّر الواجهة"""
        try:
            show_labels = bool(self.settings.get("show_ribbon_labels", 1))
            w, h = self.RIBBON_BTN_WIDTH, self.RIBBON_BTN_HEIGHT
            if show_labels:
                # لازم نسيب مساحة تحت الأيقونة للمسمى النصي + مسافات الزرار
                available_h = h - 26
            else:
                # مفيش مسمى نصي خالص - الأيقونة تقدر تملى الزرار تقريبًا
                available_h = h - 12
            available_w = w - 14
            size = max(min(available_h, available_w), 16)
            return int(size)
        except Exception:
            return 26

    def _show_blocked(self, key):
        message = "لا تملك صلاحية الوصول إلى هذا الجزء. تواصل مع مدير العيادة إذا احتجت صلاحية إضافية."
        popup = ctk.CTkToplevel(self)
        popup.title("تنبيه")
        popup.geometry("320x150")
        popup.grab_set()
        ctk.CTkLabel(popup, text=message, font=theme.FONT_NORMAL, wraplength=280,
                     justify="center").pack(expand=True, padx=20)

    def _highlight_active_nav(self, active_key):
        self._active_nav_key = active_key
        if hasattr(self, "nav_canvas"):
            self._redraw_nav_bar()
        # Update sidebar active state
        if hasattr(self, "sidebar_buttons"):
            for k, btn in self.sidebar_buttons.items():
                if k == active_key:
                    btn.configure(fg_color=theme.PRIMARY_LIGHT, text_color="#FFFFFF")
                else:
                    btn.configure(fg_color="transparent", text_color=theme.TEXT_DARK)

    # ---------------- منطقة المحتوى ----------------

    def _build_content_area(self):
        self.content_area = ctk.CTkFrame(self, fg_color=theme.BG_MAIN, corner_radius=0)
        self.content_area.pack(side="right", fill="both", expand=True, padx=24, pady=(12, 16))

    def _build_sidebar(self):
        # Sidebar container (fixed width, RTL layout)
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=theme.CARD_BG, width=240, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        # Branding (logo + app name)
        logo_label = ctk.CTkLabel(self.sidebar_frame, text="Dentora", font=theme.FONT_TITLE,
                                   text_color=theme.TEXT_DARK)
        logo_label.pack(pady=12)

        # Navigation buttons
        self.sidebar_buttons = {}
        for key, icon_name, label, permission in self.RIBBON_ITEMS:
            btn = ctk.CTkButton(self.sidebar_frame, text=label, width=200, height=44,
                                 fg_color="transparent", hover_color=theme.BG_MAIN,
                                 anchor="w", corner_radius=0,
                                 command=lambda k=key: self.show_page(k))
            # Icon
            icon_img = self._icon_pil_for(icon_name, 24, theme.PRIMARY_LIGHT)
            if icon_img:
                ctk_img = ctk.CTkImage(light_image=icon_img, size=icon_img.size)
                btn.configure(image=ctk_img)
                btn._icon_image = ctk_img  # keep reference
            btn.pack(pady=2, padx=10, fill="x")
            self.sidebar_buttons[key] = btn

        # Spacer to push user section to bottom
        spacer = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        spacer.pack(expand=True, fill="both")

        # User info and logout
        user_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        user_frame.pack(side="bottom", fill="x", pady=10)
        self.user_label = ctk.CTkLabel(user_frame,
                                        text=f"{self.current_user['full_name']} ({self.current_user['role']})",
                                        font=theme.FONT_SMALL, text_color=theme.TEXT_DARK)
        self.user_label.pack(pady=4)
        logout_btn = ctk.CTkButton(user_frame, text="تسجيل خروج", fg_color=theme.ACCENT_BORDER,
                                   hover_color=theme.ACCENT_BORDER, command=self._logout)
        logout_btn.pack(pady=4)
    def show_page(self, page_key, open_patient_id=None):
        if page_key == "exit":
            self.destroy()
            return

        permission = next((p for k, i, l, p in self.RIBBON_ITEMS if k == page_key), None)
        if not self._can_access(permission):
            self._show_blocked(page_key)
            return

        if self.current_page is not None:
            self.current_page.destroy()

        self._highlight_active_nav(page_key)

        if page_key == "patients":
            self.current_page = PatientsPage(self.content_area, current_user=self.current_user)
            if open_patient_id:
                self.current_page.show_detail(open_patient_id)
        elif page_key == "appointments":
            self.current_page = AppointmentsPage(self.content_area, current_user=self.current_user)
        elif page_key == "prices":
            self.current_page = PricesPage(self.content_area)
        elif page_key == "staff":
            self.current_page = StaffPage(self.content_area, current_user=self.current_user)
        elif page_key == "materials":
            self.current_page = MaterialsPage(self.content_area)
        elif page_key == "accounts":
            self.current_page = ClinicAccountsPage(self.content_area)
        elif page_key == "labs":
            self.current_page = LabsPage(self.content_area, current_user=self.current_user)
        elif page_key == "n8n":
            self.current_page = N8nPage(self.content_area)
        elif page_key == "settings":
            self.current_page = SettingsPage(self.content_area, current_user=self.current_user,
                                              on_settings_changed=self._reload_settings)
        else:
            return

        self.current_page.pack(fill="both", expand=True)

    def _reload_settings(self):
        """بعد حفظ الإعدادات، نعيد تحميل شريط التنقل بالكامل حتى يظهر الاسم/الشعار/اللون/الخط الجديد.
        بنحافظ على التاب المفتوحة حاليًا في صفحة الإعدادات (بدل ما ترجع دايمًا
        لأول تاب)، وبنمسح خط الفاصل القديم قبل ما نرسم واحد جديد بلون الثيم
        الجديد - عشان خطوط الثيمات القديمة ما تفضلش متراكمة فوق بعض"""
        prev_tab = None
        if isinstance(self.current_page, SettingsPage) and hasattr(self.current_page, "tabview"):
            try:
                prev_tab = self.current_page.tabview.get()
            except Exception:
                prev_tab = None

        self.settings = db.get_effective_settings(self.current_user["id"] if self.current_user else None)
        theme.apply_from_settings(self.settings)
        icons.set_icon_pattern(self.settings.get("icon_pattern", "outline"))
        clinic_name = (self.settings.get("clinic_name") or "").strip()
        self.title(f'Dentora - "{clinic_name}"' if clinic_name else "Dentora")
        _set_window_icon(self, DENTORA_ICON_PATH)

        # لازم نعيد تلوين خلفية النافذة الرئيسية ومنطقة المحتوى كمان -
        # دول اتلوّنوا مرة واحدة بس وقت الإنشاء (fg_color=theme.BG_MAIN)
        # ومبيتحدثوش تاني تلقائيًا، فلو مقفلناش الكود ده هنا هيفضل شكل
        # الشاشة (الخلفية العامة) ثابت بلون الثيم القديم حتى لو الشريط
        # العلوي والكروت الداخلية اتغيّرت فعلاً - وده اللي بيدي إحساس إن
        # "الثيم مش بيستجيب"
        self.configure(fg_color=theme.BG_MAIN)
        try:
            self.content_area.configure(fg_color=theme.BG_MAIN)
        except Exception:
            pass

        if hasattr(self, "sidebar_frame"):
            self.sidebar_frame.destroy()
        self._build_sidebar()

        self.show_page("settings")
        if prev_tab:
            try:
                self.current_page.tabview.set(prev_tab)
            except Exception:
                pass


if __name__ == "__main__":
    app = ClinicApp()
    app.mainloop()
