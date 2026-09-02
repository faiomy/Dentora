# -*- coding: utf-8 -*-
"""
شريط الصور والملفات (الأشعة والمستندات) الخاص بالمريض - بدون حد أقصى للعدد.
كل ملف بيتحفظ نسخة منه جوه مجلد البرنامج (assets/patient_files/<patient_id>)
عشان لو المريض حذف الملف الأصلي من مكانه، النسخة في البرنامج تفضل موجودة.
"""

import os
import sys
import shutil
import time
import subprocess
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

import theme
import database as db

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATIENT_FILES_DIR = os.path.join(APP_ROOT, "assets", "patient_files")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


def open_with_default_app(path):
    """يفتح الملف بالبرنامج الافتراضي المرتبط بيه على جهاز المستخدم"""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])
    except Exception:
        pass


class PatientFilesStrip(ctk.CTkFrame):
    def __init__(self, master, patient_id, vertical=False, **kwargs):
        # بناخد نسخة من العرض المُمرَّر (لو موجود) عشان نحسب عليه مقاسات
        # الصور/العناوين جوه السايد بار كنسبة، مش أرقام ثابتة منفصلة عن
        # عرض الحاوية - عشان لو العرض اتغيّر تاني يفضل كل حاجة متناسقة
        # وما يحصلش تقطيع في النص (زي ما كان بيحصل لما العرض الفعلي للعنصر
        # يبقى مختلف عن الأرقام المكتوبة يدويًا لعرض/التفاف النص)
        self._configured_width = kwargs.get("width", 285 if vertical else None)
        super().__init__(master, fg_color=theme.CARD_BG, corner_radius=12, **kwargs)
        self.patient_id = patient_id
        self.vertical = vertical
        # مهم جدًا: لازم نمنع الفريم إنه "يقلّص" نفسه على مقاس الأولاد اللي
        # جواه (زي الهيدر والسكرول فريم) *قبل* ما نبدأ نبني الأولاد دول في
        # _build(). لو استنينا وسيبنا اللي بيستخدم الكلاس (زي patients_page)
        # يعمل pack_propagate(False) بعد ما الفريم اتبنى، يبقى يكون الوقت
        # فات: الفريم يكون خلاص قلّص نفسه على مقاس الأولاد (بيرجع أصغر بكتير
        # من الـ width اللي واخده في الكونستركتور)، وتعطيل الـ propagate في
        # اللحظة دي هيجمّد نفس المقاس الصغير الغلط ده بدل المقاس الصح. عشان
        # كده لازم نعطّل الـ propagate هنا، فورًا، قبل _build().
        self.pack_propagate(False)
        self._build()
        self.refresh()

        # الحل الجذري لمشكلة "السايد بار بيتعرض أصغر من المكتوب في الكود
        # والكلام جواه بيتقطع": بدل ما نعتمد على رقم عرض ثابت مكتوب يدويًا
        # (اللي بيفترض إن العرض المطلوب هيتعرض بالظبط زي ما هو، وده مش
        # مضمون على كل الأجهزة - خصوصًا لما شاشة الجهاز شغالة بنسبة تكبير
        # مختلفة في إعدادات ويندوز)، بنراقب العرض الفعلي اللي اتعرض بيه
        # الفريم على الشاشة لحظة بلحظة (Configure event) وبنعيد حساب عرض
        # الصور/التفاف النص على أساس العرض الحقيقي ده. كده مهما اختلف
        # العرض الفعلي عن الرقم المكتوب في الكود لأي سبب، النص هيتظبط
        # عليه صح ومش هيتقطع تاني.
        self._last_measured_width = None
        self._resize_after_id = None
        if self.vertical:
            self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        new_width = event.width
        if new_width < 60:
            return
        if self._last_measured_width is not None and abs(new_width - self._last_measured_width) < 8:
            return
        self._last_measured_width = new_width
        self._configured_width = new_width
        if self._resize_after_id is not None:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
        # تأخير بسيط (debounce) عشان لو الحدث اتكرر كذا مرة سريع أثناء رسم
        # الواجهة أول مرة، نعيد الرسم مرة واحدة بس بالعرض الصحيح النهائي
        self._resize_after_id = self.after(80, self.refresh)

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(12, 6))
        if self.vertical:
            ctk.CTkLabel(header, text="🖼 الصور والأشعة", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_DARK).pack(anchor="e")
            ctk.CTkButton(header, text="+ إضافة", width=90, height=28, font=theme.FONT_SMALL,
                          fg_color=theme.HEADER_GRAD_END, hover_color=theme.HEADER_GRAD_START,
                          text_color="#FFFFFF", border_width=0,
                          command=self._add_files).pack(anchor="e", pady=(4, 0))
        else:
            ctk.CTkLabel(header, text="الصور والملفات (الأشعة وغيرها)", font=theme.FONT_SUBTITLE,
                         text_color=theme.TEXT_DARK).pack(side="right")
            ctk.CTkButton(header, text="+ إضافة صورة / ملف", width=170, height=34,
                          fg_color=theme.HEADER_GRAD_END, hover_color=theme.HEADER_GRAD_START,
                          text_color="#FFFFFF", border_width=0,
                          command=self._add_files).pack(side="left")

        if self.vertical:
            # سايد بار رأسي: الصور فوق بعض بسكرول رأسي منفصل عن باقي الصفحة
            self.strip = ctk.CTkScrollableFrame(self, fg_color=theme.BG_MAIN, corner_radius=10)
            self.strip.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        else:
            self.strip = ctk.CTkScrollableFrame(self, orientation="horizontal", fg_color=theme.BG_MAIN,
                                                 height=175, corner_radius=10)
            self.strip.pack(fill="x", padx=16, pady=(0, 16))

    def _vertical_thumb_max_w(self):
        """عرض الصورة المصغّرة/التفاف العنوان جوه السايد بار الرأسي، محسوب
        كنسبة من عرض السايد بار الفعلي (مش رقم ثابت منفصل عنه) عشان يفضل
        النص مظبوط ومش بيتقطع مهما اتغيّر عرض السايد بار من بره"""
        width = self._configured_width or 285
        return max(int(width * 0.685), 90)

    def refresh(self):
        for w in self.strip.winfo_children():
            w.destroy()

        files = db.get_patient_files(self.patient_id)
        if not files:
            empty_wrap = self._vertical_thumb_max_w() if self.vertical else 150
            ctk.CTkLabel(self.strip, text="لا توجد صور\nأو ملفات مضافة بعد" if self.vertical
                         else "لا توجد صور أو ملفات مضافة بعد",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
                         wraplength=empty_wrap, justify="center").pack(padx=10, pady=40)
            return

        for f in files:
            self._render_card(f)

    def _render_card(self, f):
        if self.vertical:
            card = ctk.CTkFrame(self.strip, fg_color=theme.CARD_BG, corner_radius=10,
                                 border_width=1, border_color=theme.BORDER)
            card.pack(fill="x", padx=4, pady=5)
            thumb_max_w = self._vertical_thumb_max_w()
            thumb_h = int(thumb_max_w * 0.846)  # بنفس نسبة الارتفاع/العرض الأصلية (165/195)
        else:
            card = ctk.CTkFrame(self.strip, fg_color=theme.CARD_BG, corner_radius=10,
                                 width=130, height=155, border_width=1, border_color=theme.BORDER)
            card.pack(side="right", padx=6, pady=6)
            card.pack_propagate(False)
            thumb_max_w = 130
            thumb_h = 90

        thumb_frame = ctk.CTkFrame(card, fg_color=theme.BG_MAIN, corner_radius=8, height=thumb_h,
                                    cursor="hand2")
        thumb_frame.pack(fill="x", padx=6, pady=(6, 4))
        thumb_frame.pack_propagate(False)

        ext = os.path.splitext(f["file_path"])[1].lower()
        thumb_widget = None
        if ext in IMAGE_EXTENSIONS and os.path.exists(f["file_path"]):
            try:
                img = Image.open(f["file_path"])
                img.thumbnail((thumb_max_w, thumb_h - 10))
                ctk_img = ctk.CTkImage(light_image=img, size=img.size)
                thumb_widget = ctk.CTkLabel(thumb_frame, image=ctk_img, text="")
                thumb_widget.pack(expand=True)
            except Exception:
                thumb_widget = ctk.CTkLabel(thumb_frame, text="🖼️", font=(theme.FONT_FAMILY, 32))
                thumb_widget.pack(expand=True)
        else:
            thumb_widget = ctk.CTkLabel(thumb_frame, text="📄", font=(theme.FONT_FAMILY, 32))
            thumb_widget.pack(expand=True)

        title = f["title"] or os.path.basename(f["file_path"])
        title_lbl = ctk.CTkLabel(card, text=title, font=theme.FONT_SMALL, text_color=theme.TEXT_DARK,
                                  wraplength=thumb_max_w if self.vertical else 110, justify="center")
        title_lbl.pack()
        ctk.CTkLabel(card, text=f["added_date"], font=(theme.FONT_FAMILY, 10),
                     text_color=theme.TEXT_MUTED).pack(pady=(0, 4))

        for w in (card, thumb_frame, thumb_widget, title_lbl):
            w.bind("<Button-1>", lambda e, path=f["file_path"]: open_with_default_app(path))

        del_btn = ctk.CTkButton(card, text="✕", width=22, height=22, corner_radius=11,
                                 fg_color=theme.DANGER, hover_color="#B71C1C",
                                 font=(theme.FONT_FAMILY, 11),
                                 command=lambda fid=f["id"]: self._delete_file(fid))
        if self.vertical:
            del_btn.place(relx=1.0, x=-4, y=4, anchor="ne")
        else:
            del_btn.place(x=104, y=2)

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="اختر صورة أو ملفًا (يمكن اختيار أكثر من ملف في المرة الواحدة)"
        )
        if not paths:
            return

        dest_dir = os.path.join(PATIENT_FILES_DIR, str(self.patient_id))
        os.makedirs(dest_dir, exist_ok=True)

        for p in paths:
            unique_name = f"{int(time.time() * 1000)}_{os.path.basename(p)}"
            dest = os.path.join(dest_dir, unique_name)
            try:
                shutil.copy(p, dest)
            except Exception:
                continue
            default_title = os.path.splitext(os.path.basename(p))[0]
            db.add_patient_file(self.patient_id, dest, title=default_title)

        self.refresh()

    def _delete_file(self, file_id):
        path = db.delete_patient_file(file_id)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        self.refresh()
