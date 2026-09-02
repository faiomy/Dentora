# -*- coding: utf-8 -*-
"""
NotebookTabview: الشكل الموحّد الرسمي لأي مجموعة تابات في البرنامج كله
(صفحات: العاملين، المعامل، الواتس أب، الإعدادات - وأي صفحة تانية هتتضاف
بعد كدا). أي تاب جديدة في أي صفحة المفروض تستخدم الودجت دي عشان الشكل
يفضل متسق في كل حتة.

مواصفات الشكل الموحّد:
- كل التابات بنفس المقاس بالظبط (نفس العرض والارتفاع)، ومقاسها بيتحسب
  تلقائيًا ليكون أصغر مساحة ممكنة تستوعب أطول نص تاب من بينها - يعني
  التابات مش بتتمدد لتملأ عرض الشريط، عشان استغلال المساحة وعدم إهدارها
  في تابات أكبر من النص جواها من غير داعي.
- التابات بتترص من يمين الصفحة لشمالها (RTL) أو من الشمال لليمين (LTR)
  حسب لغة البرنامج المختارة في الإعدادات - تلقائيًا، من غير ما الصفحة
  المستخدمة للودجت تحدد أي حاجة زيادة (تقدر تجبر اتجاه معيّن يدويًا لو
  احتجت عن طريق تمرير rtl=True/False صراحة).
- خلفية كل تاب متدرجة (تدرج رأسي ناعم) مش لون مصمت واحد، ولون التاب
  المفعّلة (المفتوحة) مختلف بوضوح عن باقي التابات المقفولة، وبيتحدد
  تلقائيًا من ثيم البرنامج الحالي (theme.TAB_ACTIVE_GRAD_* /
  TAB_INACTIVE_GRAD_*) عشان يفضل متسق مع باقي شكل البرنامج.
- التاب المفعّلة زواياها العلوية مستديرة بس وحوافها السفلية مستقيمة
  ومندمجة تمامًا مع إطار المحتوى تحتها من غير أي خط حد سفلي يفصل بينهم
  (شكل فاصل الكشكول الورقي الحقيقي). التابات المقفولة مستديرة بالكامل
  وليها حد رفيع واضح عشان تبان "خلف" التاب المفتوحة.
- كل النصوص جوه التابات (المفعّلة والمقفولة) بلون أسود صريح وBold دايمًا،
  بغض النظر عن حالة التاب - عشان تبقى واضحة فوق أي تدرج لوني فاتح.

ملحوظة تقنية: شريط التابات كله عبارة عن Canvas واحد بس (بالظبط زي شريط
الأيقونات الرئيسي فوق - main.py: self.nav_canvas) بيترسم عليه كل التابات
كصور PIL متدرجة + نصوصها، بدل ما نستخدم عدة widgets منفصلة لكل تاب. الحيلة
عشان مساحة "الاندماج" (اللي التاب المفعّلة بتدخل فيها جوه صندوق المحتوى)
تفضل شكلها سليم في كل الحالات: بنرسم أول حاجة مستطيل بلون حدود الصندوق
نفسه (border_color) في شريط الاندماج ده، وبعدين بنرسم التابات فوقه - فأي
حتة مفيهاش تاب (تابات مقفولة، أو فراغات) بتبان بنفس لون حدود الصندوق
بالظبط، وكأنها امتداد طبيعي له، والتاب المفعّلة بتغطي مكانها بلونها
الخاص وتندمج بصريًا مع محتواها.

الاستخدام مطابق لـ CTkTabview في نفس الحاجات المستخدمة بالمشروع:
    tv = NotebookTabview(self)
    tv.pack(fill="both", expand=True)
    tab_a = tv.add("اسم التاب")
    ...
    tv.tab("اسم التاب")   # لو محتاج ترجع للفريم تاني
    tv.set("اسم التاب")   # تفتح تاب معين برمجيًا
    tv.get()              # اسم التاب المفتوحة حاليًا
"""

import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

import theme
import database as db


class NotebookTabview(ctk.CTkFrame):
    OVERLAP = 8          # قد ايه التاب المفتوحة بتدخل جوه إطار المحتوى عشان تختفي أي حدود بينهم
    SIDE_PAD = 4         # مسافة بسيطة من حافة الشريط لأول/آخر تاب
    TAB_GAP = 3          # مسافة رفيعة بين كل تاب واللي جنبها
    H_TEXT_PAD = 14      # حشو أفقي (يمين وشمال) حوالين نص التاب - أقل مساحة تستوعب النص
    V_TEXT_PAD = 7       # حشو رأسي (فوق وتحت) حوالين نص التاب
    TAB_RADIUS = 9

    def __init__(self, master, border_color=None, content_fg_color=None,
                 active_fg_color=None, inactive_fg_color=None,
                 text_color=None, active_text_color=None, font=None,
                 command=None, corner_radius=None, fg_color="transparent",
                 bar_bg_color=None, rtl=None, **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)

        self.border_color = border_color or theme.BORDER
        self.content_fg_color = content_fg_color or theme.CARD_BG
        # النصوص كلها بقت أسود صريح Bold ثابت دايمًا (مطلب موحّد لكل
        # التابات) - البارامترين القديمين اتسابوا في التوقيع بس للتوافق
        # مع أي كود قديم بيمررهم، وبيتجاهلوا فعليًا
        self.text_color = "#000000"
        self.active_text_color = "#000000"
        self.font = font or theme.FONT_NAV
        self.bold_font = (self.font[0], self.font[1], "bold")
        self.corner_radius = corner_radius if corner_radius is not None else self.TAB_RADIUS
        self._external_command = command
        self._bar_bg_color = bar_bg_color or theme.BG_MAIN

        if rtl is None:
            try:
                rtl = (db.get_settings().get("language") or "ar") != "en"
            except Exception:
                rtl = True
        self.rtl = rtl

        self._names = []
        self._frames = {}
        self._tab_rects = {}     # name -> (x1, y1, x2, y2) لتحديد أماكن الكليك
        self._current = None
        self._img_refs = []      # مراجع دائمة للصور عشان الـ garbage collector ما يمسحهاش الصور المرسومة
        self._tab_h = self._measure_tab_height()
        self._pending_layout = False

        # إطار المحتوى (شكل صندوق بحد واضح بلون الثيم) - بيتحط أول حاجة
        # عشان يبقى تحت شريط التابات في ترتيب التراكب (z-order)
        self.body_shell = ctk.CTkFrame(self, fg_color=self.border_color,
                                        corner_radius=self.corner_radius,
                                        width=10, height=10)
        self.body_shell.place(x=0, y=self._tab_h)
        self.body = ctk.CTkFrame(self.body_shell, fg_color=self.content_fg_color,
                                  corner_radius=max(self.corner_radius - 3, 0),
                                  width=10, height=10)
        self.body.place(x=2, y=2)

        # شريط التابات: Canvas واحد بيغطي عرض الصفحة كله - بيترسم عليه كل
        # التابات دفعة واحدة في كل مرة (زي شريط الأيقونات الرئيسي بالظبط)
        self.tab_canvas = tk.Canvas(self, height=self._tab_h + self.OVERLAP,
                                     highlightthickness=0, bd=0, bg=self._bar_bg_color)
        self.tab_canvas.place(x=0, y=0, relwidth=1)
        self.tab_canvas.bind("<Button-1>", self._on_canvas_click)
        self.tab_canvas.bind("<Motion>", self._on_canvas_motion)
        self.tab_canvas.bind("<Leave>", lambda e: self.tab_canvas.configure(cursor=""))

        # بنعيد رسم الشريط عند أي تغيير في المقاس (Configure) وكمان أول
        # ما الودجت فعليًا يبان على الشاشة (Map) - عشان نضمن قيمة عرض
        # صحيحة حتى لو الصفحة اتبنت جوّانيًا قبل ما تتحط على الشاشة فعليًا
        # (زي ما بيحصل في main.py: الصفحة بتتبني الأول وبعدين تتعمللها
        # pack بعد كدا)
        self.bind("<Configure>", self._sync_body_geometry, add="+")
        self.bind("<Configure>", lambda e: self._request_layout(), add="+")
        self.bind("<Map>", lambda e: self._request_layout(), add="+")
        self.body_shell.bind("<Configure>", self._sync_inner_body_geometry, add="+")

    def _measure_tab_height(self):
        """أقل ارتفاع ممكن يستوعب سطر النص المستخدم في التابات + حشو رأسي بسيط"""
        try:
            f = tkfont.Font(family=self.bold_font[0], size=self.bold_font[1], weight="bold")
            text_h = f.metrics("linespace")
        except Exception:
            text_h = 20
        return max(int(text_h + self.V_TEXT_PAD * 2), 26)

    def _sync_body_geometry(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return
        shell_h = max(h - self._tab_h, 10)
        self.body_shell.configure(width=w, height=shell_h)

    def _sync_inner_body_geometry(self, event=None):
        w = self.body_shell.winfo_width()
        h = self.body_shell.winfo_height()
        if w <= 1 or h <= 1:
            return
        self.body.configure(width=max(w - 4, 10), height=max(h - 4, 10))

    # ---------------- API متوافقة مع CTkTabview ----------------

    def add(self, name):
        if name in self._frames:
            return self._frames[name]

        frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self._frames[name] = frame
        self._names.append(name)

        if self._current is None:
            self._current = name
            frame.place(x=0, y=0, relwidth=1, relheight=1)

        self._request_layout()
        return frame

    def tab(self, name):
        return self._frames.get(name)

    def get(self):
        return self._current

    def set(self, name):
        if name not in self._frames:
            return
        if name != self._current:
            if self._current in self._frames:
                self._frames[self._current].place_forget()
            self._current = name
            self._frames[name].place(x=0, y=0, relwidth=1, relheight=1)
        self._layout_tabs()
        if self._external_command:
            try:
                self._external_command()
            except Exception:
                pass

    # ---------------- التوزيع والرسم ----------------

    def _request_layout(self):
        """بنجمع كل طلبات إعادة الرسم المتتالية (مثلاً 5 نداءات add() ورا
        بعض) في رسمة واحدة بس بعدين، بدل ما نرسم الشريط 5 مرات فاضية وهو
        لسه بيتبني، وده كمان بيدي فرصة لـ Tk إنه يخلّص حساب المقاس الحقيقي
        للصفحة قبل أول رسمة فعلية"""
        if self._pending_layout:
            return
        self._pending_layout = True
        self.after_idle(self._layout_tabs)

    def _tab_widths(self):
        try:
            f = tkfont.Font(family=self.bold_font[0], size=self.bold_font[1], weight="bold")
            return {name: int(f.measure(name) + self.H_TEXT_PAD * 2) for name in self._names}
        except Exception:
            return {name: 90 for name in self._names}

    def _layout_tabs(self):
        self._pending_layout = False
        canvas = self.tab_canvas
        n = len(self._names)
        if n == 0:
            canvas.delete("all")
            return

        self.update_idletasks()
        bar_w = canvas.winfo_width()
        if bar_w <= 1:
            self.after(30, self._request_layout)
            return

        canvas.delete("all")
        self._img_refs.clear()
        self._tab_rects.clear()

        widths = self._tab_widths()
        h_closed = self._tab_h
        h_open = self._tab_h + self.OVERLAP

        # شريط الاندماج: مستطيل بلون حدود صندوق المحتوى بيغطي عرض الشريط
        # كله في منطقة الـ OVERLAP - أي حتة مفيهاش تاب مفتوحة فوقها هتبان
        # بنفس لون الصندوق بالظبط (امتداد طبيعي ليه)، والتاب المفعّلة
        # هتغطي مكانها بلونها الخاص فوق المستطيل ده
        canvas.create_rectangle(0, h_closed, bar_w, h_closed + self.OVERLAP,
                                 fill=self.border_color, outline="")

        # كل التابات بنفس مقاس أصغر تاب يستوعب أطول نص من بينها (مش
        # بتتمدد لتملأ عرض الشريط)، وبتترص من يمين الشريط لشماله (RTL) أو
        # من الشمال لليمين (LTR) حسب لغة البرنامج المختارة في الإعدادات
        x = bar_w - self.SIDE_PAD if self.rtl else self.SIDE_PAD

        for name in self._names:
            w = widths[name]
            is_active = name == self._current
            h = h_open if is_active else h_closed
            if self.rtl:
                x1, x2 = x - w, x
            else:
                x1, x2 = x, x + w

            self._draw_tab(canvas, name, x1, 0, x2, h, is_active)
            self._tab_rects[name] = (x1, 0, x2, h)

            if self.rtl:
                x -= (w + self.TAB_GAP)
            else:
                x += (w + self.TAB_GAP)

    def _draw_tab(self, canvas, name, x1, y1, x2, y2, is_active):
        from PIL import ImageTk
        w, h = int(round(x2 - x1)), int(round(y2 - y1))
        if w <= 0 or h <= 0:
            return

        if is_active:
            img = theme.rounded_top_gradient_pil(
                w, h, theme.TAB_ACTIVE_GRAD_TOP, theme.TAB_ACTIVE_GRAD_BOTTOM,
                radius=self.corner_radius)
        else:
            img = theme._rounded_gradient_pil(
                w, h, theme.TAB_INACTIVE_GRAD_TOP, theme.TAB_INACTIVE_GRAD_BOTTOM,
                radius=self.corner_radius, border_color=self.border_color, border_width=1)

        photo = ImageTk.PhotoImage(img)
        self._img_refs.append(photo)
        canvas.create_image(int(x1), int(y1), anchor="nw", image=photo, tags=("tab", name))

        # النص دايمًا في نص ارتفاع الجزء "المرئي" الأساسي (self._tab_h) مش
        # الارتفاع الكامل اللي بيشمل الـ overlap الداخل في المحتوى، عشان
        # يفضل متمركز بصريًا زي التابات المقفولة بالظبط
        canvas.create_text((x1 + x2) / 2, y1 + self._tab_h / 2, text=name,
                            font=self.bold_font, fill="#000000", tags=("tab", name))

    def _on_canvas_click(self, event):
        for name, (x1, y1, x2, y2) in self._tab_rects.items():
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.set(name)
                return

    def _on_canvas_motion(self, event):
        for name, (x1, y1, x2, y2) in self._tab_rects.items():
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.tab_canvas.configure(cursor="hand2")
                return
        self.tab_canvas.configure(cursor="")
