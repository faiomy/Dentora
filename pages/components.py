# -*- coding: utf-8 -*-
"""
مكتبة المكونات المشتركة (Design System) - عناصر واجهة موحّدة لكل صفحات البرنامج

الهدف: كل صفحة تستخدم نفس شكل الهيدر والكروت والأزرار ورسايل الحالات الفارغة،
بدل ما كل صفحة كانت بتبني حاجاتها بنفسها بألوان وأحجام متفرقة - وده اللي كان
بيخلي شكل البرنامج يختلف من صفحة لصفحة.

كل مكون هنا مبني على نفس توكنز theme.py (ألوان الثيم الحالي، الفونطات، أنصاف
الأقطار)، فأي تغيير في الثيم بينعكس عليها تلقائيًا وقت بناء الصفحة.

ملحوظة عن النصوص العربية: كل المكونات هنا بتعكس النصوص زي ما هي (من غير
theme.rtl_fix). سبب كده إن صفحة الأسعار وثّقت عمليًا إن قلب ترتيب الكلمات
كان بيعكس معنى الجمل المعروضة، والهيدرات والعناوين بتترسم صح من غير قلب.
rtl_fix فضلت موجودة في theme.py للنصوص القصيرة اللي اتأكدنا إن شكلها بيتحسن
بها (زرار بعنصرين)، والقرار فيها بيبقى لكل صفحة على حدة زي ما هي قبل كده.
"""

import tkinter as tk

import customtkinter as ctk

import theme


# ---------------- الهيدر الموحّد لكل صفحة ----------------

class PageHeader(ctk.CTkFrame):
    """هيدر صفحة موحّد: عنوان الصفحة يمين + مساحة للأزرار/الأدوات على الشمال.

    بديل النسخ المتفرقة اللي كانت كل صفحة بتعملها بنفسها
    (CTkFrame شفاف + CTkLabel بفونط FONT_TITLE). الأزرار بتتحط بـ
    pack(side="left") زي المعتاد بعد إنشاء الهيدر.
    """

    def __init__(self, master, title, subtitle=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(title_row, text=title, font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(side="right")
        if subtitle:
            ctk.CTkLabel(title_row, text=subtitle, font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=(8, 0))
        # صف الأدوات (أزرار الصفحة) - فاضي افتراضيًا ويتحط فيه إيه اللي الصفحة عايزاه
        self.actions_row = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_row.pack(fill="x", pady=(6, 0))

    def add_action(self, text, command, kind="primary", width=140, height=36):
        """بيرجّع زرار جاهز متحط في صف الأدوات - بيوحّد مقاس أزرار الهيدر كلها.

        kind: primary (لون الثيم الأساسي) / accent (لون حد الثيم) / subtle (حد رفيع) / danger
        """
        if kind == "primary":
            btn = theme.make_shadowed_button(self.actions_row, text, command=command,
                                             width=width, height=height,
                                             font=theme.FONT_SUBTITLE)
        elif kind == "accent":
            btn = ctk.CTkButton(self.actions_row, text=text, command=command,
                                width=width, height=height, fg_color=theme.ACCENT_BORDER,
                                hover_color=theme.darken_color(theme.ACCENT_BORDER, 0.9),
                                font=theme.FONT_SUBTITLE, corner_radius=theme.RADIUS_MD,
                                cursor="hand2")
        elif kind == "danger":
            btn = ctk.CTkButton(self.actions_row, text=text, command=command,
                                width=width, height=height, fg_color=theme.DANGER,
                                hover_color=theme.darken_color(theme.DANGER, 0.9),
                                font=theme.FONT_SUBTITLE, corner_radius=theme.RADIUS_MD,
                                cursor="hand2")
        else:  # subtle
            btn = ctk.CTkButton(self.actions_row, text=text, command=command,
                                width=width, height=height,
                                fg_color=theme.CARD_BG, text_color=theme.TEXT_DARK,
                                hover_color=theme.BG_MAIN,
                                border_width=1, border_color=theme.BORDER,
                                font=theme.FONT_SUBTITLE, corner_radius=theme.RADIUS_MD,
                                cursor="hand2")
        btn.pack(side="left", padx=(6, 0))
        return btn


# ---------------- الكارت الموحّد ----------------

class SectionCard(ctk.CTkFrame):
    """كارت أبيض بحواف مستديرة - الحاوية الموحّدة لأي مجموعة محتوى في الصفحة.

    نفس شكل الكروت اللي كانت بتتعمل يدوي بـ
    CTkFrame(fg_color=theme.CARD_BG, corner_radius=12) في أكتر من صفحة،
    بس هنا بمقاس موحّد وبدعم اختياري لعنوان داخلي.
    """

    def __init__(self, master, title=None, padded=True, **kwargs):
        kwargs.setdefault("fg_color", theme.CARD_BG)
        kwargs.setdefault("corner_radius", theme.RADIUS_LG)
        super().__init__(master, **kwargs)

        self.body = self
        if title:
            ctk.CTkLabel(self, text=title, font=theme.FONT_SUBTITLE,
                         text_color=theme.TEXT_DARK).pack(
                anchor="e", padx=self._pad_x(), pady=(16, 8))
        if not padded:
            self.body = None

    def _pad_x(self):
        return 20


def card(parent, **kwargs):
    """نسخة مختصرة من SectionCard من غير عنوان - للكروت البسيطة
    (بتستبدل CTkFrame(fg_color=theme.CARD_BG, corner_radius=12) المتكرر)."""
    kwargs.setdefault("fg_color", theme.CARD_BG)
    kwargs.setdefault("corner_radius", theme.RADIUS_LG)
    return ctk.CTkFrame(parent, **kwargs)


def inner_row(parent, **kwargs):
    """صف/صندوق داخلي داخل كارت - نفس الشكل اللي كان بيتعمل بـ
    CTkFrame(fg_color=theme.BG_MAIN, corner_radius=8/10) في صفحات
    الحسابات والمصروفات (صف أفتح من الكارت الأبيض حوالينه)."""
    kwargs.setdefault("fg_color", theme.BG_MAIN)
    kwargs.setdefault("corner_radius", theme.RADIUS_SM)
    return ctk.CTkFrame(parent, **kwargs)


# ---------------- بطاقة الرقم الموحّدة ----------------

class StatCard(ctk.CTkFrame):
    """بطاقة إحصائية: عنوان صغير مكتوم + قيمة كبيرة ملوّنة - نفس الشكل
    اللي كان في كارت ملخص حسابات العيادة (الإيرادات/المصروفات/الصافي)،
    ومتاحة هنا عشان أي صفحة تانية محتاجة تعرض أرقام ملخصة تستخدم نفسها."""

    def __init__(self, master, label, value_text, value_color=None, **kwargs):
        kwargs.setdefault("fg_color", theme.BG_MAIN)
        kwargs.setdefault("corner_radius", theme.RADIUS_MD)
        super().__init__(master, **kwargs)
        ctk.CTkLabel(self, text=label, font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_MUTED).pack(pady=(16, 4))
        ctk.CTkLabel(self, text=value_text, font=theme.FONT_TITLE,
                     text_color=value_color or theme.TEXT_DARK).pack(pady=(0, 16))


# ---------------- صف حقل إدخال موحّد ----------------

class FormFieldRow(ctk.CTkFrame):
    """صف "عنوان حقل + ودجت الإدخال" بأسلوب الإعدادات: العنوان يمين بفونط
    وفونط لون ثابت، ومساحة فاضية على الشمال تحط فيها ودجت الإدخال بنفسك."""

    def __init__(self, master, label, label_font=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=label, font=label_font or theme.FONT_NORMAL,
                     text_color=theme.INPUT_LABEL_COLOR, anchor="e").pack(
            side="right", padx=(0, 10))

    def add_widget(self, widget, padx=0):
        widget.pack(side="left", padx=(padx, 0))
        return widget

    def add_entry(self, width=220, height=34, **entry_kwargs):
        entry = ctk.CTkEntry(self, width=width, height=height, **entry_kwargs)
        theme.apply_sunken_style(entry)
        entry.pack(side="left", padx=(8, 0))
        return entry


# ---------------- زرار الشريط الموحّد ----------------

def toolbar_button(parent, text, command, kind="primary", width=120, height=34):
    """زرار مصغّر لشريط الفلاتر/الأدوات جوه الصفحة (زي أزرار اليوم/الشهر/السنة
    في حسابات العيادة) - مقاس ولون موحّد بدل الأحجام المتفرقة."""
    if kind == "primary":
        return ctk.CTkButton(parent, text=text, command=command, width=width,
                             height=height, fg_color=theme.PRIMARY_LIGHT,
                             hover_color=theme.darken_color(theme.PRIMARY_LIGHT, 0.9),
                             font=theme.FONT_SMALL, corner_radius=theme.RADIUS_SM,
                             cursor="hand2")
    if kind == "accent":
        return ctk.CTkButton(parent, text=text, command=command, width=width,
                             height=height, fg_color=theme.ACCENT_BORDER,
                             hover_color=theme.darken_color(theme.ACCENT_BORDER, 0.9),
                             font=theme.FONT_SMALL, corner_radius=theme.RADIUS_SM,
                             cursor="hand2")
    if kind == "danger":
        return ctk.CTkButton(parent, text=text, command=command, width=width,
                             height=height, fg_color=theme.DANGER,
                             hover_color=theme.darken_color(theme.DANGER, 0.9),
                             font=theme.FONT_SMALL, corner_radius=theme.RADIUS_SM,
                             cursor="hand2")
    # subtle
    return ctk.CTkButton(parent, text=text, command=command, width=width,
                         height=height, fg_color=theme.CARD_BG,
                         text_color=theme.TEXT_DARK, hover_color=theme.BG_MAIN,
                         border_width=1, border_color=theme.BORDER,
                         font=theme.FONT_SMALL, corner_radius=theme.RADIUS_SM,
                         cursor="hand2")


# ---------------- الحالة الفارغة الموحّدة ----------------

def empty_state(parent, text, icon=None, pady=40):
    """رسالة "مفيش بيانات" موحّدة الشكل - بنفس أسلوب الرسايل المتفرقة
    اللي كانت في الصفحات (نص مكتوم في نص المساحة)، مع أيقونة اختيارية."""
    box = ctk.CTkFrame(parent, fg_color="transparent")
    box.pack(fill="x", pady=pady)
    if icon:
        ctk.CTkLabel(box, text=icon, font=(theme.FONT_FAMILY, 30)).pack()
    ctk.CTkLabel(box, text=text, font=theme.FONT_NORMAL,
                 text_color=theme.TEXT_MUTED, justify="center",
                 wraplength=420).pack(pady=(6, 0))
    return box


# ---------------- التلميح الموحّد ----------------

class Tooltip:
    """تلميح صغير بيظهر عند عمل hover على أي widget.

    ده نقل حرفي لكلاس _Tooltip من pages/patients_page.py (كان بيتستدعى
    من صفحة المصروفات كمان) - بقا مكتبة مشتركة بدل ما يعيش جوه ملف
    صفحة المرضى. _Tooltip هناك فضل اسم موجود للتوافق.
    """

    def __init__(self, widget, text, font_size=10):
        self.widget = widget
        self.text = text
        self.font_size = font_size
        self.tip = None
        # add="+" عشان الحدث ده ميلغيش أي ربط تاني موجود على نفس الودجت
        # (زي تأثير الـ hover بتاع أزرار الأيقونات الزجاجية)
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2 - 30
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg="#1B1E23", fg="#FFFFFF",
                 font=(theme.CONTENT_FONT_FAMILY, self.font_size), padx=8, pady=4,
                 borderwidth=0).pack()

    def _hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None
