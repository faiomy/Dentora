# -*- coding: utf-8 -*-
"""
صفحة واتساب: تذكير المواعيد يدويًا بمساعدة البرنامج (من دون واجهة برمجية رسمية مدفوعة).
يُعِدّ البرنامج رسالة كل مريض باسمه وموعده الصحيح، ويفتح محادثة واتساب
(من نفس حساب واتساب المفتوح على جهازك - واتساب ويب أو تطبيق سطح المكتب)
برسالة جاهزة، ولا يتبقى عليك سوى الضغط على إرسال (أو تجربة الإرسال التلقائي التجريبي أدناه).
"""

from datetime import date, timedelta, datetime
from tkinter import messagebox

import customtkinter as ctk
import theme
import database as db
import whatsapp_sender as wa_sender
from pages.rtl_entry import RTLEntry
from pages.notebook_tabs import NotebookTabview

PLACEHOLDERS_HELP = ("الحقول التي تُملأ تلقائيًا: {name} الاسم - {date} التاريخ - "
                     "{day_name} اسم اليوم (السبت/الأحد...) - {time} الوقت (يُضبط "
                     "صباحًا/مساءً تلقائيًا حسب الموعد) - {doctor} الطبيب - {clinic_name} اسم العيادة\n"
                     "(في قوالب \"شكر بعد الزيارة\" فقط - إذا كانت الرسالة تُرسَل فور تسجيل دفعة مالية، "
                     "فإن {date}/{time} يأخذان تاريخ ووقت الدفعة نفسها، ويمكن استخدام {amount} أيضًا "
                     "لإدراج مبلغ الدفعة في نص الرسالة)")

# أنواع القوالب المتاحة: تأكيد فوري وقت الحجز، تذكير قبل الموعد، ورسالة شكر
# بعد انتهاء الموعد أو تسجيل دفعة
TEMPLATE_TYPE_LABELS = {
    "booking_confirmation": "تأكيد فوري عند الحجز",
    "appointment_reminder": "تذكير موعد",
    "thank_you": "شكر بعد الزيارة",
}
TEMPLATE_TYPE_BY_LABEL = {v: k for k, v in TEMPLATE_TYPE_LABELS.items()}


def _plain_checkbox(parent, text="", variable=None, command=None, **extra):
    """تشيك بوكس بمظهر موحّد في كل الصفحة: علامة صح واضحة بس من غير أي خلفية
    ملوّنة (مش أزرق ولا أي لون تاني وقت التفعيل)، وخط عادي مش Bold"""
    # ملحوظة: بعض نسخ customtkinter الحديثة بترفض fg_color="transparent"
    # في CTkCheckBox تحديدًا (بترمي ValueError)، فبنستخدم لون خلفية الكارت
    # الحقيقي theme.CARD_BG بدلها، والنتيجة البصرية نفسها (مفيش خلفية ملوّنة
    # واضحة) لأن الكارت أصلاً بنفس اللون ده
    kwargs = dict(
        font=(theme.FONT_FAMILY, theme.CONTENT_FONT_SIZE),
        text_color=theme.TEXT_DARK,
        fg_color=theme.CARD_BG,
        hover_color=theme.INPUT_SUNKEN_BG,
        checkmark_color=theme.TEXT_DARK,
        border_color=theme.BORDER,
    )
    kwargs.update(extra)
    return ctk.CTkCheckBox(parent, text=text, variable=variable, command=command, **kwargs)


class WhatsAppPage(ctk.CTkFrame):
    # ---- شكل جدول المرضى: أعمدة (العنوان، العرض بالبكسل، المفتاح) ----
    # الترتيب هنا من الشمال لليمين في الـ grid (أعلى index بيطلع أقصى اليمين،
    # فـ"الاسم" اللي هو آخر عنصر في القايمة بيبقى أول عمود يتقرا من اليمين)
    TABLE_COLUMNS = [
        ("إرسال", 120, "send"),
        ("تحديد", 70, "check"),
        ("الحالة", 110, "status"),
        ("الوقت", 110, "time"),
        ("التليفون", 160, "phone"),
        ("الاسم", 220, "name"),
    ]
    HEADER_BG = "#1B1E23"
    HEADER_TEXT = "#FFFFFF"
    ROW_BG_A = "#FFFFFF"
    ROW_BG_B = "#EEF1F6"
    GRID_LINE = "#C7CCD6"

    # فونت موحّد لكل الأزرار في الصفحة (نفس فونت "القالب المستخدم لكل
    # المرضى" لكن Bold)
    try:
        BUTTON_FONT = (theme.FONT_NORMAL[0], theme.FONT_NORMAL[1], "bold")
    except Exception:
        BUTTON_FONT = theme.FONT_NORMAL

    def __init__(self, master, current_user=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_user = current_user
        self.selected_date = date.today() + timedelta(days=1)  # افتراضيًا بكرة (قبل الموعد بـ24 ساعة)
        self.selected_template_id = None
        self.row_check_vars = {}  # appt_id -> BooleanVar (تحديد المرضى المراد إرسال الرسالة إليهم)
        self.auto_send_var = ctk.BooleanVar(value=False)
        self.use_desktop_app_var = ctk.BooleanVar(value=True)
        self.wait_seconds_var = ctk.StringVar(value="12")
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="واتساب - تذكير المواعيد", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", pady=(0, 4))
        ctk.CTkLabel(
            self, text="يُعِدّ البرنامج الرسالة باسم كل مريض وموعده، ويفتح واتساب "
                       "(من نفس الحساب المسجَّل الدخول عليه على هذا الجهاز)، وما عليك سوى الضغط على إرسال - "
                       "أو تفعيل الإرسال التلقائي التجريبي ليُرسِلها البرنامج بنفسه.",
            font=theme.FONT_SMALL, text_color=theme.TEXT_DARK, wraplength=700,
            justify="right").pack(anchor="e", pady=(0, 10))

        self.tabview = NotebookTabview(self, font=theme.FONT_NORMAL,
                                       active_fg_color=theme.TAB_ACTIVE_BG,
                                       inactive_fg_color=theme.TAB_INACTIVE_BG,
                                       border_color=theme.ACCENT_BORDER,
                                       content_fg_color=theme.CARD_BG,
                                       corner_radius=theme.TAB_RADIUS)
        self.tabview.pack(fill="both", expand=True)

        tab_templates = self.tabview.add("قوالب الرسائل")
        tab_reminders = self.tabview.add("إرسال يدوي")
        tab_reminder_settings = self.tabview.add("تذكير المواعيد")
        tab_booking = self.tabview.add("تأكيد الحجز")
        tab_payment = self.tabview.add("تأكيد الدفع والشكر")

        scroll_templates = ctk.CTkScrollableFrame(tab_templates, fg_color="transparent")
        scroll_templates.pack(fill="both", expand=True)
        self._build_templates_card(scroll_templates)

        scroll_reminders = ctk.CTkScrollableFrame(tab_reminders, fg_color="transparent")
        scroll_reminders.pack(fill="both", expand=True)
        self._build_reminders_card(scroll_reminders)

        scroll_reminder_settings = ctk.CTkScrollableFrame(tab_reminder_settings, fg_color="transparent")
        scroll_reminder_settings.pack(fill="both", expand=True)
        self._build_reminder_settings_tab(scroll_reminder_settings)

        scroll_booking = ctk.CTkScrollableFrame(tab_booking, fg_color="transparent")
        scroll_booking.pack(fill="both", expand=True)
        self._build_booking_confirmation_tab(scroll_booking)

        scroll_payment = ctk.CTkScrollableFrame(tab_payment, fg_color="transparent")
        scroll_payment.pack(fill="both", expand=True)
        self._build_payment_thankyou_tab(scroll_payment)

    # ================= قوالب الرسائل =================

    def _build_templates_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=theme.CARD_BG, corner_radius=12,
                             border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=6)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(16, 4))
        ctk.CTkLabel(header, text="قوالب الرسائل الجاهزة", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")
        ctk.CTkButton(header, text="+ قالب جديد", width=120, height=32, font=self.BUTTON_FONT,
                      fg_color=theme.PRIMARY_LIGHT,
                      command=self._open_add_template_dialog).pack(side="left")

        ctk.CTkLabel(card, text=PLACEHOLDERS_HELP, font=theme.FONT_SMALL,
                     text_color=theme.TEXT_DARK, wraplength=700,
                     justify="right").pack(anchor="e", padx=22, pady=(0, 10))

        self.templates_list_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.templates_list_frame.pack(fill="x", padx=22, pady=(0, 16))
        self._refresh_templates_list()

    def _refresh_templates_list(self):
        for w in self.templates_list_frame.winfo_children():
            w.destroy()

        templates = db.get_message_templates()
        if not templates:
            ctk.CTkLabel(self.templates_list_frame, text="لا توجد قوالب بعد. اضغط \"+ قالب جديد\".",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_DARK).pack(pady=10)
            return

        for t in templates:
            row = ctk.CTkFrame(self.templates_list_frame, fg_color=theme.BG_MAIN, corner_radius=8)
            row.pack(fill="x", pady=4)

            ctk.CTkButton(row, text="حذف", width=55, height=28, fg_color=theme.DANGER,
                          font=self.BUTTON_FONT,
                          command=lambda tid=t["id"]: self._delete_template(tid)).pack(
                side="left", padx=8, pady=8)
            ctk.CTkButton(row, text="تعديل", width=55, height=28, font=self.BUTTON_FONT,
                          fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
                          border_width=1, border_color=theme.BORDER,
                          command=lambda t=t: self._open_edit_template_dialog(t)).pack(
                side="left", padx=4, pady=8)

            preview = t["template_text"].replace("\n", "  ")
            if len(preview) > 70:
                preview = preview[:70] + "..."
            type_label = TEMPLATE_TYPE_LABELS.get(t.get("template_type"), t.get("template_type") or "")
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="right", padx=10, pady=6, fill="x", expand=True)
            name_row = ctk.CTkFrame(info, fg_color="transparent")
            name_row.pack(anchor="e")
            ctk.CTkLabel(name_row, text=t["name"], font=theme.FONT_SUBTITLE,
                         text_color=theme.TEXT_DARK, anchor="e").pack(side="right")
            ctk.CTkLabel(name_row, text=f"[{type_label}]", font=theme.FONT_SMALL,
                         text_color=theme.INPUT_LABEL_COLOR, anchor="e").pack(side="right", padx=(0, 8))
            ctk.CTkLabel(info, text=preview, font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_DARK, anchor="e").pack(anchor="e")

    def _open_template_dialog(self, title, initial_name="", initial_text="",
                               initial_type="appointment_reminder", on_save=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("420x520")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=title, font=theme.FONT_SUBTITLE).pack(pady=(16, 10))

        ctk.CTkLabel(dialog, text="نوع القالب", font=theme.FONT_NORMAL).pack(anchor="e", padx=24)
        type_menu = ctk.CTkOptionMenu(dialog, values=list(TEMPLATE_TYPE_LABELS.values()),
                                       width=370, font=self.BUTTON_FONT,
                                       fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                                       button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9))
        type_menu.set(TEMPLATE_TYPE_LABELS.get(initial_type, TEMPLATE_TYPE_LABELS["appointment_reminder"]))
        type_menu.pack(padx=24, pady=(2, 10), anchor="e")

        ctk.CTkLabel(dialog, text="اسم القالب", font=theme.FONT_NORMAL).pack(anchor="e", padx=24)
        name_entry = RTLEntry(dialog, width=370, height=38)
        theme.apply_sunken_style(name_entry)
        if initial_name:
            name_entry.insert(0, initial_name)
        name_entry.pack(padx=24, pady=(2, 10), anchor="e")

        ctk.CTkLabel(dialog, text="نص الرسالة", font=theme.FONT_NORMAL).pack(anchor="e", padx=24)
        text_box = ctk.CTkTextbox(dialog, width=370, height=160, font=theme.FONT_NORMAL)
        theme.apply_sunken_style(text_box)
        if initial_text:
            text_box.insert("1.0", initial_text)
        text_box.pack(padx=24, pady=(2, 6), anchor="e")

        ctk.CTkLabel(dialog, text=PLACEHOLDERS_HELP, font=theme.FONT_SMALL,
                     text_color=theme.TEXT_DARK, wraplength=370,
                     justify="right").pack(anchor="e", padx=24, pady=(0, 14))

        def save():
            name = name_entry.get().strip()
            text = text_box.get("1.0", "end").strip()
            template_type = TEMPLATE_TYPE_BY_LABEL.get(type_menu.get(), "appointment_reminder")
            if not name or not text:
                return
            on_save(name, text, template_type)
            dialog.destroy()
            self._refresh_templates_list()
            self._refresh_reminders_list()

        theme.make_shadowed_button(dialog, "💾 حفظ القالب", command=save,
                                    width=160, height=42, font=self.BUTTON_FONT).pack(pady=10)

    def _open_add_template_dialog(self):
        self._open_template_dialog(
            "قالب جديد",
            on_save=lambda name, text, ttype: db.add_message_template(name, text, ttype))

    def _open_edit_template_dialog(self, template):
        self._open_template_dialog(
            "تعديل القالب", initial_name=template["name"], initial_text=template["template_text"],
            initial_type=template.get("template_type", "appointment_reminder"),
            on_save=lambda name, text, ttype: db.update_message_template(
                template["id"], name, text, ttype))

    def _delete_template(self, template_id):
        db.delete_message_template(template_id)
        self._refresh_templates_list()

    # ================= تذكير المواعيد =================

    def _build_reminders_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=theme.CARD_BG, corner_radius=12,
                             border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=6)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(16, 10))
        ctk.CTkLabel(header, text="إرسال تذكير المواعيد", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")

        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.pack(fill="x", padx=22, pady=(0, 10))

        ctk.CTkButton(controls, text="بكرة (قبل الموعد بـ24 ساعة)", width=200, height=34,
                      font=self.BUTTON_FONT, fg_color=theme.ACCENT_BORDER,
                      command=self._set_tomorrow).pack(side="right", padx=4)
        ctk.CTkButton(controls, text="النهاردة", width=90, height=34, font=self.BUTTON_FONT,
                      fg_color=theme.ACCENT_BORDER,
                      command=self._set_today).pack(side="right", padx=4)

        self.date_label = ctk.CTkLabel(controls, text="", font=theme.FONT_NORMAL,
                                        text_color=theme.TEXT_DARK)
        self.date_label.pack(side="right", padx=10)

        template_row = ctk.CTkFrame(card, fg_color="transparent")
        template_row.pack(fill="x", padx=22, pady=(0, 10))
        ctk.CTkLabel(template_row, text="القالب المستخدم لكل المرضى:", font=theme.FONT_NORMAL,
                     text_color=theme.INPUT_LABEL_COLOR).pack(side="right", padx=(8, 0))

        templates = db.get_message_templates("appointment_reminder")
        template_names = [t["name"] for t in templates] or ["لا يوجد قوالب"]
        self.template_menu = ctk.CTkOptionMenu(
            template_row, values=template_names, width=220, font=self.BUTTON_FONT,
            fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
            button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
            command=lambda v: self._refresh_reminders_list())
        if template_names:
            self.template_menu.set(template_names[0])
        self.template_menu.pack(side="right")

        # ---- صف التحديد والإرسال ----
        selection_row = ctk.CTkFrame(card, fg_color="transparent")
        selection_row.pack(fill="x", padx=22, pady=(0, 8))

        ctk.CTkButton(selection_row, text="☑ تحديد الكل / إلغاء الكل", width=190, height=32,
                      fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
                      border_width=1, border_color=theme.BORDER, font=self.BUTTON_FONT,
                      command=self._toggle_select_all).pack(side="right", padx=4)

        self.send_selected_btn = ctk.CTkButton(
            selection_row, text="📤 إرسال للمحدَّدين فقط", width=160, height=34, font=self.BUTTON_FONT,
            fg_color=theme.SUCCESS, command=self._send_selected)
        self.send_selected_btn.pack(side="left", padx=4)

        self.send_all_btn = ctk.CTkButton(
            selection_row, text="📤 إرسال للجميع (حتى مَن أُرسِلت لهم رسائل سابقًا)", width=260,
            height=34, font=self.BUTTON_FONT, fg_color=theme.SUCCESS, command=self._send_all)
        self.send_all_btn.pack(side="left", padx=4)

        # ---- صف الإرسال التلقائي التجريبي ----
        auto_row = ctk.CTkFrame(card, fg_color="transparent")
        auto_row.pack(fill="x", padx=22, pady=(0, 4))

        # ملحوظة: هذا الخيار متاح ومفعَّل دائمًا بصرف النظر عن تثبيت مكتبة pyautogui؛
        # وإذا كانت المكتبة غير مثبّتة، سيتم تجاهل الضغطة التلقائية فقط مع إرسال الرسالة بشكل طبيعي
        _plain_checkbox(auto_row, text="إرسال تلقائي تجريبي (يحاول الضغط على إرسال تلقائيًا)",
                        variable=self.auto_send_var, state="normal").pack(
            side="right", padx=(4, 0))

        _plain_checkbox(auto_row, text="فتح المحادثة مباشرة من تطبيق واتساب لسطح المكتب (موصى به)",
                        variable=self.use_desktop_app_var, state="normal").pack(
            side="right", padx=(4, 12))

        ctk.CTkLabel(auto_row, text="ثانية انتظار قبل الإرسال:", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_DARK).pack(side="right", padx=(10, 4))
        wait_entry = ctk.CTkEntry(auto_row, width=50, height=28, justify="center",
                                   font=theme.FONT_SMALL, textvariable=self.wait_seconds_var)
        theme.apply_sunken_style(wait_entry)
        wait_entry.pack(side="right")

        if wa_sender.PYAUTOGUI_AVAILABLE:
            note_text = ("ملحوظة: لا يوفر واتساب إرسالًا تلقائيًا كاملًا بشكل رسمي، لذلك يحاول هذا الخيار "
                        "الضغط على Enter بعد فتح رسالة واتساب وامتلائها - وهو غير مضمون بنسبة 100%، ويتطلب "
                        "بقاء النافذة نشطة وعدم تحريك الماوس أو لوحة المفاتيح، وإذا كان الإنترنت بطيئًا فزِد "
                        "ثواني الانتظار. تجنَّب استخدام هذا الخيار لعدد كبير جدًا من الأرقام دفعة واحدة "
                        "لأن واتساب قد يعتبره رسائل مزعجة (سبام).")
        else:
            note_text = ("الخيار مفعَّل، لكن لكي يعمل فعليًا يجب تثبيت مكتبة pyautogui على "
                        "هذا الجهاز (pip install pyautogui) ثم إعادة تشغيل البرنامج. "
                        "بدون ذلك ستُفتح الرسالة جاهزة كالمعتاد وتضغط إرسال بنفسك - وهذا أضمن على أي حال.")
        ctk.CTkLabel(card, text=note_text, font=theme.FONT_SMALL, text_color=theme.TEXT_DARK,
                     wraplength=700, justify="right").pack(anchor="e", padx=22, pady=(0, 6))

        login_note = ("عند تفعيل خيار \"فتح المحادثة مباشرة من تطبيق واتساب لسطح المكتب\"، يفتح البرنامج "
                     "كل محادثة داخل تطبيق واتساب نفسه مباشرة (إن كان مثبَّتًا على الجهاز) من دون فتح "
                     "متصفح إطلاقًا - وهذا أضمن بكثير عند إرسال عدة رسائل متتالية، لأن فتح عدة "
                     "تبويبات متصفح دفعة واحدة قد يمنع بعضها من فتح واتساب فعليًا وتفتح فقط صفحة "
                     "wa.me بدون تحويل تلقائي. إذا لم يكن التطبيق مثبَّتًا، يعود البرنامج تلقائيًا "
                     "لفتح الرابط في المتصفح (واتساب ويب) كما كان يحدث سابقًا. وإذا طلب واتساب ويب "
                     "تسجيل الدخول (رمز QR) في كل مرة، فهذا يعني أن المتصفح "
                     "الافتراضي على الجهاز ليس هو نفسه الذي عليه جلسة واتساب. سجِّل دخولك مرة "
                     "واحدة في نفس المتصفح الافتراضي وسيتذكرك بعد ذلك، أو ثبِّت تطبيق واتساب "
                     "لسطح المكتب لأنه يفتح المحادثة مباشرة من دون تسجيل دخول متكرر.")
        ctk.CTkLabel(card, text=login_note, font=theme.FONT_SMALL, text_color=theme.TEXT_DARK,
                     wraplength=700, justify="right").pack(anchor="e", padx=22, pady=(0, 10))

        self.reminders_list_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.reminders_list_frame.pack(fill="x", padx=22, pady=(0, 18))

        self._update_date_label()
        self._refresh_reminders_list()

    def _set_today(self):
        self.selected_date = date.today()
        self._update_date_label()
        self._refresh_reminders_list()

    def _set_tomorrow(self):
        self.selected_date = date.today() + timedelta(days=1)
        self._update_date_label()
        self._refresh_reminders_list()

    def _update_date_label(self):
        day_name = db.get_day_name_arabic(self.selected_date.isoformat())
        self.date_label.configure(
            text=f"مواعيد يوم: {day_name} {self.selected_date.strftime('%Y/%m/%d')}")

    def _current_template(self):
        templates = db.get_message_templates("appointment_reminder")
        if not templates:
            return None
        selected_name = self.template_menu.get()
        for t in templates:
            if t["name"] == selected_name:
                return t
        return templates[0]

    def _current_appts(self):
        return db.get_appointments_for_reminder(self.selected_date.isoformat())

    def _refresh_reminders_list(self):
        for w in self.reminders_list_frame.winfo_children():
            w.destroy()

        template = self._current_template()
        appts = self._current_appts()

        if not appts:
            ctk.CTkLabel(self.reminders_list_frame, text="لا توجد مواعيد في هذا اليوم",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_DARK).pack(pady=16)
            return
        if not template:
            ctk.CTkLabel(self.reminders_list_frame, text="يجب إنشاء قالب رسالة أولًا من الأعلى",
                         font=theme.FONT_NORMAL, text_color=theme.DANGER).pack(pady=16)
            return

        clinic_name = db.get_settings()["clinic_name"]
        self._render_table(appts, template, clinic_name)

    def _get_check_var(self, appt_id):
        var = self.row_check_vars.get(appt_id)
        if var is None:
            var = ctk.BooleanVar(value=False)
            self.row_check_vars[appt_id] = var
        return var

    # ---------------- جدول حقيقي (grid) بحدود وألوان متبادلة واضحة ----------------

    def _render_table(self, appts, template, clinic_name):
        grid = ctk.CTkFrame(self.reminders_list_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True)

        grid.grid_columnconfigure(0, weight=1)  # مساحة فاضية أقصى الشمال
        for i, (_, width, _) in enumerate(self.TABLE_COLUMNS):
            grid.grid_columnconfigure(i + 1, minsize=width, weight=0)

        # هيدر الأعمدة
        ctk.CTkLabel(grid, text="", fg_color=self.HEADER_BG, corner_radius=0,
                     border_width=1, border_color=self.GRID_LINE, height=36).grid(
            row=0, column=0, sticky="nsew")
        for i, (label_text, width, key) in enumerate(self.TABLE_COLUMNS):
            ctk.CTkLabel(grid, text=label_text, font=self.BUTTON_FONT,
                         text_color=self.HEADER_TEXT, fg_color=self.HEADER_BG,
                         corner_radius=0, border_width=1, border_color=self.GRID_LINE,
                         anchor="center", height=36).grid(row=0, column=i + 1, sticky="nsew")

        for row_idx, appt in enumerate(appts, start=1):
            row_bg = self.ROW_BG_A if row_idx % 2 == 1 else self.ROW_BG_B
            self._render_table_row(grid, row_idx, row_bg, appt, template, clinic_name)

    def _render_table_row(self, grid, row_idx, row_bg, appt, template, clinic_name):
        sent = bool(appt.get("reminder_sent"))
        has_number = bool(appt.get("whatsapp_number"))
        formatted_time = db.format_time_12h(appt["appt_time"])

        filler = ctk.CTkLabel(grid, text="", fg_color=row_bg, corner_radius=0,
                               border_width=1, border_color=self.GRID_LINE, height=42)
        filler.grid(row=row_idx, column=0, sticky="nsew")

        for i, (_, width, key) in enumerate(self.TABLE_COLUMNS):
            cell = ctk.CTkFrame(grid, fg_color=row_bg, corner_radius=0,
                                 border_width=1, border_color=self.GRID_LINE, height=42)
            cell.grid(row=row_idx, column=i + 1, sticky="nsew")
            cell.grid_propagate(False)

            if key == "name":
                ctk.CTkLabel(cell, text=appt["full_name"], font=theme.FONT_NORMAL,
                             text_color=theme.TEXT_DARK, anchor="e").pack(
                    fill="both", expand=True, padx=10)

            elif key == "phone":
                phone_text = appt.get("whatsapp_number") or "بدون رقم"
                ctk.CTkLabel(cell, text=phone_text, font=theme.FONT_NORMAL,
                             text_color=theme.TEXT_DARK if has_number else theme.DANGER,
                             anchor="e").pack(fill="both", expand=True, padx=10)

            elif key == "time":
                ctk.CTkLabel(cell, text=formatted_time, font=theme.FONT_NORMAL,
                             text_color=theme.TEXT_DARK, anchor="center").pack(
                    fill="both", expand=True, padx=4)

            elif key == "status":
                status_text = "✔ أُرسلت" if sent else "لم تُرسل"
                status_color = theme.SUCCESS if sent else theme.TEXT_DARK
                ctk.CTkLabel(cell, text=status_text, font=self.BUTTON_FONT,
                             text_color=status_color, anchor="center").pack(
                    fill="both", expand=True)

            elif key == "check":
                check_var = self._get_check_var(appt["id"])
                _plain_checkbox(cell, text="", variable=check_var, width=20,
                                fg_color=row_bg,
                                state="normal" if has_number else "disabled").pack(expand=True)

            elif key == "send":
                btn_text = "↻ إعادة" if sent else "📤 إرسال"
                ctk.CTkButton(
                    cell, text=btn_text, width=max(width - 20, 60), height=30,
                    font=self.BUTTON_FONT,
                    fg_color=theme.SUCCESS if not sent else theme.CARD_BG,
                    text_color="#FFFFFF" if not sent else theme.SUCCESS,
                    border_width=1 if sent else 0, border_color=theme.SUCCESS,
                    state="normal" if has_number else "disabled",
                    command=lambda a=appt: self._send_reminder(a, template, clinic_name)
                ).pack(expand=True)

    def _toggle_select_all(self):
        appts = self._current_appts()
        eligible_ids = [a["id"] for a in appts if a.get("whatsapp_number")]
        if not eligible_ids:
            return
        all_checked = all(self._get_check_var(i).get() for i in eligible_ids)
        new_state = not all_checked
        for i in eligible_ids:
            self._get_check_var(i).set(new_state)

    def _get_wait_ms(self):
        try:
            seconds = max(3, int(self.wait_seconds_var.get() or 12))
        except Exception:
            seconds = 12
        return seconds * 1000

    def _open_whatsapp_chat(self, phone_number, message):
        """تفتح المحادثة عبر الدالة المشتركة في whatsapp_sender.py (نفسها
        تُستخدم أيضًا في حلقة الأرشفة التلقائية بـ main.py)"""
        wa_sender.open_whatsapp_chat(phone_number, message,
                                      use_desktop_app=self.use_desktop_app_var.get())

    def _send_reminder(self, appt, template, clinic_name, auto_send=None, wait_ms=None, refresh=True):
        if auto_send is None:
            auto_send = self.auto_send_var.get() and wa_sender.PYAUTOGUI_AVAILABLE
        if wait_ms is None:
            wait_ms = self._get_wait_ms()

        message = db.fill_message_template(
            template["template_text"], appt["full_name"], appt["appt_date"], appt["appt_time"],
            doctor_name=appt.get("doctor_name") or "", clinic_name=clinic_name)
        self._open_whatsapp_chat(appt["whatsapp_number"], message)
        db.mark_reminder_sent(appt["id"], True)

        if auto_send:
            wa_sender.press_enter_later(self, wait_ms)

        if refresh:
            self._refresh_reminders_list()

    def _send_batch(self, appts):
        template = self._current_template()
        if not template or not appts:
            return

        if self.auto_send_var.get() and not wa_sender.PYAUTOGUI_AVAILABLE:
            messagebox.showwarning(
                "الإرسال التلقائي غير مفعَّل فعليًا",
                "خيار \"الإرسال التلقائي التجريبي\" محدَّد، لكن مكتبة pyautogui غير "
                "مثبَّتة على هذا الجهاز، لذلك لن يضغط البرنامج زر الإرسال تلقائيًا - "
                "ستُفتح كل رسالة جاهزة وعليك الضغط على إرسال بنفسك.\n\n"
                "لتفعيل الإرسال التلقائي فعليًا: افتح موجّه الأوامر (Command Prompt) "
                "ونفِّذ الأمر التالي، ثم أعد تشغيل البرنامج:\n\n"
                "pip install pyautogui")

        clinic_name = db.get_settings()["clinic_name"]
        auto_send = self.auto_send_var.get() and wa_sender.PYAUTOGUI_AVAILABLE
        wait_ms = self._get_wait_ms()
        # فاصل زمني بين كل رسالة والأخرى حتى يأخذ التطبيق (أو المتصفح) وقته الكافي
        # ليفتح ويظهر في المقدمة قبل محاولة فتح المحادثة التالية أو الضغط على زر
        # الإرسال. عند استخدام المتصفح (وليس تطبيق سطح المكتب) يُستخدم فاصل أكبر
        # قليلًا لتفادي رفض بعض المتصفحات فتح عدة تبويبات دفعة واحدة
        use_desktop = self.use_desktop_app_var.get()
        base_gap = 700 if use_desktop else 1200
        gap_ms = (wait_ms + 1500) if auto_send else base_gap
        n = len(appts)
        for i, appt in enumerate(appts):
            is_last = (i == n - 1)
            self.after(i * gap_ms, lambda a=appt, last=is_last: self._send_reminder(
                a, template, clinic_name, auto_send=auto_send, wait_ms=wait_ms, refresh=last))

    def _send_selected(self):
        appts = self._current_appts()
        selected = [a for a in appts if a.get("whatsapp_number")
                    and self._get_check_var(a["id"]).get()]
        self._send_batch(selected)

    def _send_all(self):
        appts = [a for a in self._current_appts() if a.get("whatsapp_number")]
        self._send_batch(appts)

    # ================= الأرشفة التلقائية (تذكير قبل الموعد بساعة + بث الساعة 3 + شكر الدفعات) =================

    # ================= أدوات مشتركة لصفوف الجدول =================

    def _build_status_header(self, card, title):
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(16, 6))
        ctk.CTkLabel(header, text=title, font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")
        status_label = ctk.CTkLabel(header, text="", font=theme.FONT_SMALL, text_color=theme.SUCCESS)
        status_label.pack(side="left")
        return status_label

    def _flash_saved(self, status_label):
        try:
            status_label.configure(text="✔ تم الحفظ")
            self.after(2000, lambda: status_label.configure(text=""))
        except Exception:
            pass

    def _table_row(self, parent, var, text, command, build_control=None):
        """صف جدول واحد بحدود واضحة: التشيك بوكس والوصف في سطر لوحدهم فوق،
        وأي ضبط إضافي (قالب/وقت) في سطر منفصل تحته - كل صف بنده تحت التاني
        مش جنبه، وكل واحد فيهم في صندوق واضح الحدود لوحده"""
        row = ctk.CTkFrame(parent, fg_color=theme.BG_MAIN, corner_radius=8,
                            border_width=1, border_color=theme.BORDER)
        row.pack(fill="x", padx=22, pady=6)
        _plain_checkbox(row, text=text, variable=var, command=command).pack(
            anchor="e", padx=16, pady=(12, 6 if build_control else 12))
        if build_control:
            control_frame = ctk.CTkFrame(row, fg_color="transparent")
            control_frame.pack(fill="x", padx=16, pady=(0, 12))
            build_control(control_frame)
        return row

    # ================= تذكير المواعيد (قبل الساعة + تأكيد اليوم التالي) =================

    def _build_reminder_settings_tab(self, parent):
        card = ctk.CTkFrame(parent, fg_color=theme.CARD_BG, corner_radius=12,
                             border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=6)
        self.reminder_status_label = self._build_status_header(card, "تذكير المواعيد التلقائي")

        ctk.CTkLabel(
            card, text="هاتان الخاصيتان مستقلتان تمامًا عن بعضهما - يمكن تفعيل إحداهما وإيقاف الأخرى، "
                       "وكل تعديل هنا يُحفظ فورًا من دون زر حفظ.",
            font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
            wraplength=700, justify="right").pack(anchor="e", padx=22, pady=(0, 6))

        settings = db.get_settings()
        reminder_templates = db.get_message_templates("appointment_reminder")
        reminder_names = [t["name"] for t in reminder_templates] or ["لا يوجد قوالب تذكير"]
        current_reminder = next(
            (t["name"] for t in reminder_templates
             if t["id"] == settings.get("whatsapp_auto_reminder_template_id")), None)

        self.auto_hour_reminder_var = ctk.BooleanVar(
            value=bool(settings.get("whatsapp_hour_reminder_enabled", 1)))

        def _build_reminder_control(cf):
            ctk.CTkLabel(cf, text="القالب المستخدَم:", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=(6, 0))
            self.auto_reminder_menu = ctk.CTkOptionMenu(
                cf, values=reminder_names, width=220, font=self.BUTTON_FONT,
                fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                command=lambda _choice: self._autosave_reminders())
            self.auto_reminder_menu.set(current_reminder or reminder_names[0])
            self.auto_reminder_menu.pack(side="right")

        self._table_row(card, self.auto_hour_reminder_var,
                         "تذكير المريض قبل موعده بساعة واحدة بالضبط",
                         self._autosave_reminders, _build_reminder_control)

        batch_hour = settings.get("whatsapp_next_day_batch_hour")
        batch_minute = settings.get("whatsapp_next_day_batch_minute")
        batch_hour = 15 if batch_hour is None else int(batch_hour)
        batch_minute = 0 if batch_minute is None else int(batch_minute)

        self.auto_next_day_batch_var = ctk.BooleanVar(
            value=bool(settings.get("whatsapp_next_day_batch_enabled", 1)))

        hour_entry_holder, minute_entry_holder = {}, {}

        def _build_batch_control(cf):
            ctk.CTkLabel(cf, text="(نظام 24 ساعة)", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="right")
            self.auto_batch_minute_var = ctk.StringVar(value=f"{batch_minute:02d}")
            minute_entry = ctk.CTkEntry(cf, width=44, height=32, justify="center",
                                         font=theme.FONT_SMALL, textvariable=self.auto_batch_minute_var)
            theme.apply_sunken_style(minute_entry)
            minute_entry.pack(side="right", padx=(0, 8))
            ctk.CTkLabel(cf, text=":", font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_DARK).pack(side="right", padx=2)
            self.auto_batch_hour_var = ctk.StringVar(value=f"{batch_hour:02d}")
            hour_entry = ctk.CTkEntry(cf, width=44, height=32, justify="center",
                                       font=theme.FONT_SMALL, textvariable=self.auto_batch_hour_var)
            theme.apply_sunken_style(hour_entry)
            hour_entry.pack(side="right")
            ctk.CTkLabel(cf, text="ساعة البث:", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=(6, 4))
            hour_entry_holder["e"] = hour_entry
            minute_entry_holder["e"] = minute_entry

        self._table_row(card, self.auto_next_day_batch_var,
                         "تأكيد جماعي لكل مواعيد الغد (بنفس قالب التذكير)",
                         self._autosave_reminders, _build_batch_control)

        hour_entry = hour_entry_holder["e"]
        minute_entry = minute_entry_holder["e"]

        # لما المستخدم يكتب رقمين في خانة الساعة، ينتقل تلقائي لخانة الدقيقة
        # (ويحدد كل النص فيها عشان يقدر يكتب فوقه على طول من غير ما يمسح
        # الأول). وبنقصّر أي قيمة أطول من رقمين أو فيها حروف مش أرقام.
        # كمان كل تعديل بيحفظ نفسه تلقائيًا بعد وقفة قصيرة عن الكتابة
        def _on_hour_typed(*_):
            digits = "".join(ch for ch in self.auto_batch_hour_var.get() if ch.isdigit())[:2]
            if digits != self.auto_batch_hour_var.get():
                self.auto_batch_hour_var.set(digits)
            if len(digits) == 2:
                minute_entry.focus_set()
                minute_entry.select_range(0, "end")
            self._autosave_reminders_debounced()

        def _on_minute_typed(*_):
            digits = "".join(ch for ch in self.auto_batch_minute_var.get() if ch.isdigit())[:2]
            if digits != self.auto_batch_minute_var.get():
                self.auto_batch_minute_var.set(digits)
            self._autosave_reminders_debounced()

        self.auto_batch_hour_var.trace_add("write", _on_hour_typed)
        self.auto_batch_minute_var.trace_add("write", _on_minute_typed)
        hour_entry.bind("<FocusIn>", lambda e: hour_entry.select_range(0, "end"))
        minute_entry.bind("<FocusIn>", lambda e: minute_entry.select_range(0, "end"))
        hour_entry.bind("<FocusOut>", lambda e: self._autosave_reminders())
        minute_entry.bind("<FocusOut>", lambda e: self._autosave_reminders())

        # تنبيه ثابت لو قالب التذكير ناقص
        self.reminder_templates_warning_label = ctk.CTkLabel(
            card, text="", font=theme.FONT_SMALL, text_color=theme.DANGER,
            wraplength=700, justify="right")
        self.reminder_templates_warning_label.pack(anchor="e", padx=22, pady=(4, 6))

        # ---- إعدادات الإرسال العامة (تُطبَّق على كل الرسائل التلقائية) ----
        ctk.CTkFrame(card, fg_color=theme.BORDER, height=1).pack(fill="x", padx=22, pady=(6, 10))
        ctk.CTkLabel(card, text="إعدادات الإرسال العامة (تنطبق على كل الرسائل التلقائية)",
                     font=theme.FONT_NORMAL, text_color=theme.INPUT_LABEL_COLOR).pack(
            anchor="e", padx=22, pady=(0, 6))

        self.auto_confirm_send_var = ctk.BooleanVar(
            value=bool(settings.get("whatsapp_auto_confirm_send")))
        self._table_row(card, self.auto_confirm_send_var,
                         "ضغط إرسال تلقائيًا (بدون تدخل يدوي - يتطلب pyautogui)",
                         self._autosave_reminders)

        self.auto_use_desktop_var = ctk.BooleanVar(
            value=bool(settings.get("whatsapp_auto_use_desktop_app", 1)))
        self._table_row(card, self.auto_use_desktop_var,
                         "فتح المحادثة من تطبيق واتساب لسطح المكتب",
                         self._autosave_reminders)

        wait_row = ctk.CTkFrame(card, fg_color=theme.BG_MAIN, corner_radius=8,
                                 border_width=1, border_color=theme.BORDER)
        wait_row.pack(fill="x", padx=22, pady=6)
        wait_inner = ctk.CTkFrame(wait_row, fg_color="transparent")
        wait_inner.pack(fill="x", padx=16, pady=12)
        self.auto_wait_seconds_var = ctk.StringVar(
            value=str(settings.get("whatsapp_auto_wait_seconds") or 15))
        wait_entry = ctk.CTkEntry(wait_inner, width=50, height=28, justify="center",
                                   font=theme.FONT_SMALL, textvariable=self.auto_wait_seconds_var)
        theme.apply_sunken_style(wait_entry)
        wait_entry.pack(side="right")
        ctk.CTkLabel(wait_inner, text="ثانية انتظار قبل الإرسال:", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_DARK).pack(side="right", padx=(0, 8))
        self.auto_wait_seconds_var.trace_add("write", lambda *_: self._autosave_reminders_debounced())
        wait_entry.bind("<FocusOut>", lambda e: self._autosave_reminders())

        if not wa_sender.PYAUTOGUI_AVAILABLE:
            pg_note = ("مكتبة pyautogui غير مثبَّتة على هذا الجهاز، لذلك حتى لو فعَّلت \"ضغط إرسال "
                       "تلقائيًا\"، ستُفتح كل رسالة جاهزة وتحتاج تضغط إرسال بنفسك يدويًا. لتفعيلها "
                       "فعليًا: افتح موجّه الأوامر (Command Prompt) ونفِّذ الأمر pip install pyautogui "
                       "ثم أعد تشغيل البرنامج.")
            ctk.CTkLabel(card, text=pg_note, font=theme.FONT_SMALL, text_color=theme.DANGER,
                         wraplength=700, justify="right").pack(anchor="e", padx=22, pady=(4, 16))
        else:
            ctk.CTkLabel(card, text="", font=theme.FONT_SMALL).pack(pady=(0, 6))

        self._refresh_reminder_templates_warning()

    def _autosave_reminders_debounced(self, delay_ms=700):
        if getattr(self, "_reminder_autosave_after_id", None):
            try:
                self.after_cancel(self._reminder_autosave_after_id)
            except Exception:
                pass
        self._reminder_autosave_after_id = self.after(delay_ms, self._autosave_reminders)

    def _refresh_reminder_templates_warning(self):
        try:
            reminder_templates = db.get_message_templates("appointment_reminder")
            reminder_t = next((t for t in reminder_templates
                                if t["name"] == self.auto_reminder_menu.get()), None)
            needs_template = self.auto_hour_reminder_var.get() or self.auto_next_day_batch_var.get()
            if needs_template and not reminder_t:
                self.reminder_templates_warning_label.configure(
                    text="⚠ لازم يكون فيه قالب \"تذكير موعد\" متظبط حتى تعمل الخاصيتين دول. "
                         "أنشئه من تاب \"قوالب الرسائل\" أولًا.")
            else:
                self.reminder_templates_warning_label.configure(text="")
        except Exception:
            pass

    def _autosave_reminders(self):
        if getattr(self, "_reminder_autosave_after_id", None):
            try:
                self.after_cancel(self._reminder_autosave_after_id)
            except Exception:
                pass
            self._reminder_autosave_after_id = None

        reminder_templates = db.get_message_templates("appointment_reminder")
        reminder_t = next((t for t in reminder_templates if t["name"] == self.auto_reminder_menu.get()), None)

        try:
            wait_seconds = max(3, int(self.auto_wait_seconds_var.get() or 15))
        except Exception:
            wait_seconds = 15
        try:
            batch_hour = int(self.auto_batch_hour_var.get())
        except Exception:
            batch_hour = 15
        batch_hour = max(0, min(23, batch_hour))
        try:
            batch_minute = int(self.auto_batch_minute_var.get())
        except Exception:
            batch_minute = 0
        batch_minute = max(0, min(59, batch_minute))

        db.set_whatsapp_auto_settings(
            reminder_template_id=reminder_t["id"] if reminder_t else None,
            confirm_send=self.auto_confirm_send_var.get(),
            wait_seconds=wait_seconds,
            use_desktop_app=self.auto_use_desktop_var.get(),
            next_day_batch_hour=batch_hour,
            next_day_batch_minute=batch_minute,
            hour_reminder_enabled=self.auto_hour_reminder_var.get(),
            next_day_batch_enabled=self.auto_next_day_batch_var.get(),
        )
        self._refresh_reminder_templates_warning()
        self._flash_saved(self.reminder_status_label)

    # ================= تأكيد الحجز الفوري =================

    def _build_booking_confirmation_tab(self, parent):
        card = ctk.CTkFrame(parent, fg_color=theme.CARD_BG, corner_radius=12,
                             border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=6)
        self.booking_status_label = self._build_status_header(card, "رسالة تأكيد الحجز الفورية")

        ctk.CTkLabel(
            card, text="تُرسَل تلقائيًا لحظة تسجيل أي موعد جديد من صفحة المواعيد - قبل تذكير الساعة "
                       "بوقت طويل، وقبل تأكيد اليوم التالي أيضًا. مستقلة تمامًا عن باقي التذكيرات.",
            font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
            wraplength=700, justify="right").pack(anchor="e", padx=22, pady=(0, 6))

        settings = db.get_settings()
        booking_templates = db.get_message_templates("booking_confirmation")
        booking_names = [t["name"] for t in booking_templates] or ["لا يوجد قوالب تأكيد حجز"]
        current_booking = next(
            (t["name"] for t in booking_templates
             if t["id"] == settings.get("whatsapp_auto_booking_template_id")), None)

        def _build_booking_control(cf):
            ctk.CTkLabel(cf, text="القالب المستخدَم:", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=(6, 0))
            self.auto_booking_menu = ctk.CTkOptionMenu(
                cf, values=booking_names, width=220, font=self.BUTTON_FONT,
                fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                command=lambda _choice: self._autosave_booking())
            self.auto_booking_menu.set(current_booking or booking_names[0])
            self.auto_booking_menu.pack(side="right")

        self.auto_booking_confirmation_var = ctk.BooleanVar(
            value=bool(settings.get("whatsapp_booking_confirmation_enabled", 1)))
        self._table_row(card, self.auto_booking_confirmation_var,
                         "إرسال رسالة تأكيد فورية للمريض بمجرد تسجيل الموعد",
                         self._autosave_booking, _build_booking_control)

        self.booking_templates_warning_label = ctk.CTkLabel(
            card, text="", font=theme.FONT_SMALL, text_color=theme.DANGER,
            wraplength=700, justify="right")
        self.booking_templates_warning_label.pack(anchor="e", padx=22, pady=(4, 16))

        self._refresh_booking_templates_warning()

    def _refresh_booking_templates_warning(self):
        try:
            booking_templates = db.get_message_templates("booking_confirmation")
            booking_t = next((t for t in booking_templates
                               if t["name"] == self.auto_booking_menu.get()), None)
            if self.auto_booking_confirmation_var.get() and not booking_t:
                self.booking_templates_warning_label.configure(
                    text="⚠ يجب أن يكون هناك قالب \"تأكيد فوري عند الحجز\" مُعدّ لتعمل هذه الخاصية. "
                         "يُنشأ من تبويب \"قوالب الرسائل\" أولًا.")
            else:
                self.booking_templates_warning_label.configure(text="")
        except Exception:
            pass

    def _autosave_booking(self):
        booking_templates = db.get_message_templates("booking_confirmation")
        booking_t = next((t for t in booking_templates if t["name"] == self.auto_booking_menu.get()), None)
        db.set_whatsapp_auto_settings(booking_confirmation_enabled=self.auto_booking_confirmation_var.get())
        if booking_t:
            db.set_setting_value("whatsapp_auto_booking_template_id", booking_t["id"])
        self._refresh_booking_templates_warning()
        self._flash_saved(self.booking_status_label)

    # ================= تأكيد الدفع والشكر =================

    def _build_payment_thankyou_tab(self, parent):
        card = ctk.CTkFrame(parent, fg_color=theme.CARD_BG, corner_radius=12,
                             border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=6)
        self.payment_status_label = self._build_status_header(card, "رسالة تأكيد الدفع والشكر")

        ctk.CTkLabel(
            card, text="تُرسَل تلقائيًا فور تسجيل أي دفعة مالية في حساب أي مريض، من أي صفحة في البرنامج "
                       "(المرضى، الحسابات، إلخ) - بغض النظر عن موعده.",
            font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
            wraplength=700, justify="right").pack(anchor="e", padx=22, pady=(0, 6))

        settings = db.get_settings()
        thankyou_templates = db.get_message_templates("thank_you")
        thankyou_names = [t["name"] for t in thankyou_templates] or ["لا يوجد قوالب شكر"]
        current_thankyou = next(
            (t["name"] for t in thankyou_templates
             if t["id"] == settings.get("whatsapp_auto_thankyou_template_id")), None)

        def _build_thankyou_control(cf):
            ctk.CTkLabel(cf, text="القالب المستخدَم:", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=(6, 0))
            self.auto_thankyou_menu = ctk.CTkOptionMenu(
                cf, values=thankyou_names, width=220, font=self.BUTTON_FONT,
                fg_color=theme.INPUT_SUNKEN_BG, text_color=theme.TEXT_DARK,
                button_color=theme.darken_color(theme.INPUT_SUNKEN_BG, 0.9),
                command=lambda _choice: self._autosave_payment())
            self.auto_thankyou_menu.set(current_thankyou or thankyou_names[0])
            self.auto_thankyou_menu.pack(side="right")

        self.auto_payment_thankyou_var = ctk.BooleanVar(
            value=bool(settings.get("whatsapp_payment_thankyou_enabled", 1)))
        self._table_row(card, self.auto_payment_thankyou_var,
                         "إرسال رسالة شكر تلقائية فور تسجيل دفعة مالية في حساب المريض",
                         self._autosave_payment, _build_thankyou_control)

        self.payment_templates_warning_label = ctk.CTkLabel(
            card, text="", font=theme.FONT_SMALL, text_color=theme.DANGER,
            wraplength=700, justify="right")
        self.payment_templates_warning_label.pack(anchor="e", padx=22, pady=(4, 16))

        self._refresh_payment_templates_warning()

    def _refresh_payment_templates_warning(self):
        try:
            thankyou_templates = db.get_message_templates("thank_you")
            thankyou_t = next((t for t in thankyou_templates
                                if t["name"] == self.auto_thankyou_menu.get()), None)
            if self.auto_payment_thankyou_var.get() and not thankyou_t:
                self.payment_templates_warning_label.configure(
                    text="⚠ يجب أن يكون هناك قالب \"شكر بعد الزيارة\" مُعدّ لتعمل هذه الخاصية. "
                         "يُنشأ من تبويب \"قوالب الرسائل\" أولًا.")
            else:
                self.payment_templates_warning_label.configure(text="")
        except Exception:
            pass

    def _autosave_payment(self):
        thankyou_templates = db.get_message_templates("thank_you")
        thankyou_t = next((t for t in thankyou_templates if t["name"] == self.auto_thankyou_menu.get()), None)
        db.set_whatsapp_auto_settings(
            thankyou_template_id=thankyou_t["id"] if thankyou_t else None,
            payment_thankyou_enabled=self.auto_payment_thankyou_var.get(),
        )
        self._refresh_payment_templates_warning()
        self._flash_saved(self.payment_status_label)
