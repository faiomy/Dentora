# -*- coding: utf-8 -*-
"""
صفحة إدارة المعامل:
- المعامل: إضافة/تعديل/تعطيل معامل (اسم، تليفون، عنوان، الشخص المسؤول)
- حالات المعمل: كل الشغل المُرسل للمعامل (تلقائيًا من شارت الأسنان، أو يدويًا
  من هنا)، مع إمكانية تغيير الحالة (مُرسلة/قيد التنفيذ/تم الاستلام/تم التسليم)
- حساب المعمل: المستحق لكل معمل (تكلفة الحالات مقابل المدفوع له) وتسجيل الدفعات
- إعدادات البنود: لكل بند علاجي (أساسي أو نوع فرعي) - هل يحتاج معمل؟ ومعمل مين
  افتراضيًا؟ ورمز البند عند المعمل (لو بيستخدموا ترقيم خاص بيهم)
"""

import customtkinter as ctk
from tkinter import messagebox
import theme
import database as db
from pages.rtl_entry import RTLEntry
from pages.date_auto_entry import DateAutoEntry
from pages.notebook_tabs import NotebookTabview


STATUS_LABELS = {
    "sent": "مُرسلة للمعمل",
    "in_progress": "قيد التنفيذ بالمعمل",
    "received": "تم الاستلام من المعمل",
    "delivered": "تم التسليم للمريض",
    "cancelled": "ملغاة",
}
STATUS_ORDER = ["sent", "in_progress", "received", "delivered", "cancelled"]


def _status_color(status):
    return {
        "sent": theme.WARNING,
        "in_progress": theme.PRIMARY_LIGHT,
        "received": theme.SUCCESS,
        "delivered": theme.TEXT_MUTED,
        "cancelled": theme.DANGER,
    }.get(status, theme.TEXT_MUTED)


def _lab_names(labs):
    return [l["name"] for l in labs]


def _lab_id_by_name(labs, name):
    return next((l["id"] for l in labs if l["name"] == name), None)


def _sender_options():
    """قائمة موحدة بكل من ممكن يبعت حالة للمعمل: الأطباء + العاملين المساعدين"""
    names = []
    for d in db.get_doctors():
        label = d["full_name"]
        if label not in names:
            names.append(label)
    for s in db.get_support_staff():
        if s["full_name"] not in names:
            names.append(s["full_name"])
    return names


class LabsPage(ctk.CTkFrame):
    def __init__(self, master, current_user=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_user = current_user
        self.order_status_filter = None
        self.order_lab_filter = None
        self.order_search = ""
        self.selected_account_lab_id = None
        self._build()

    # ==================== الهيكل العام ====================

    def _build(self):
        ctk.CTkLabel(self, text="المعامل", font=theme.FONT_TITLE,
                     text_color=theme.TEXT_DARK).pack(anchor="e", pady=(0, 10))

        self.tabview = NotebookTabview(self, font=theme.FONT_NAV,
                                       border_color=theme.ACCENT_BORDER,
                                       content_fg_color=theme.CARD_BG,
                                       corner_radius=theme.TAB_RADIUS)
        self.tabview.pack(fill="both", expand=True)

        tab_orders = self.tabview.add("حالات المعمل")
        tab_labs = self.tabview.add("المعامل")
        tab_accounts = self.tabview.add("حساب المعمل")
        tab_settings = self.tabview.add("إعدادات البنود العلاجية")

        self._build_orders_tab(tab_orders)
        self._build_labs_tab(tab_labs)
        self._build_accounts_tab(tab_accounts)
        self._build_settings_tab(tab_settings)

    # ==================== تاب: حالات المعمل ====================

    def _build_orders_tab(self, parent):
        filters = ctk.CTkFrame(parent, fg_color="transparent")
        filters.pack(fill="x", pady=(4, 10))

        ctk.CTkButton(filters, text="+ حالة جديدة", height=36, width=120,
                      fg_color=theme.SUCCESS,
                      command=self._open_add_order_dialog).pack(side="right", padx=4)

        labs = db.get_labs()
        lab_values = ["كل المعامل"] + _lab_names(labs)
        self.order_lab_menu = ctk.CTkOptionMenu(filters, values=lab_values, width=160,
                                                  command=self._on_order_filter_change,
                                                  **theme.optionmenu_colors())
        self.order_lab_menu.set("كل المعامل")
        self.order_lab_menu.pack(side="right", padx=4)

        status_values = ["كل الحالات"] + [STATUS_LABELS[s] for s in STATUS_ORDER]
        self.order_status_menu = ctk.CTkOptionMenu(filters, values=status_values, width=160,
                                                     command=self._on_order_filter_change,
                                                     **theme.optionmenu_colors())
        self.order_status_menu.set("كل الحالات")
        self.order_status_menu.pack(side="right", padx=4)

        self.order_search_entry = ctk.CTkEntry(filters, width=200, placeholder_text="بحث باسم المريض/البند...")
        self.order_search_entry.pack(side="right", padx=4)
        self.order_search_entry.bind("<KeyRelease>", lambda e: self._on_order_filter_change())

        self.orders_list = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.orders_list.pack(fill="both", expand=True)

        self._refresh_orders()

    def _on_order_filter_change(self, *_):
        lab_name = self.order_lab_menu.get()
        labs = db.get_labs()
        self.order_lab_filter = _lab_id_by_name(labs, lab_name) if lab_name != "كل المعامل" else None

        status_label = self.order_status_menu.get()
        self.order_status_filter = next(
            (k for k, v in STATUS_LABELS.items() if v == status_label), None)

        self.order_search = self.order_search_entry.get().strip()
        self._refresh_orders()

    def _refresh_orders(self):
        for w in self.orders_list.winfo_children():
            w.destroy()

        orders = db.get_lab_orders(lab_id=self.order_lab_filter, status=self.order_status_filter,
                                    search=self.order_search or None)
        if not orders:
            ctk.CTkLabel(self.orders_list, text="لا توجد حالات مطابقة",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED).pack(pady=30)
            return

        for order in orders:
            self._render_order_row(order)

    def _render_order_row(self, order):
        card = ctk.CTkFrame(self.orders_list, fg_color=theme.CARD_BG, corner_radius=10)
        card.pack(fill="x", pady=5, padx=2)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(10, 2))

        title = order.get("treatment_label") or "شغل معمل"
        if order.get("variant_name"):
            title += f" ({order['variant_name']})"
        if order.get("tooth_number"):
            title += f" - سن {order['tooth_number']}"
        patient_part = f"  |  المريض: {order['patient_name']}" if order.get("patient_name") else ""

        ctk.CTkLabel(top, text=f"{title}{patient_part}", font=theme.FONT_NORMAL,
                     text_color=theme.TEXT_DARK).pack(side="right")

        badge = ctk.CTkLabel(top, text=STATUS_LABELS.get(order["status"], order["status"]),
                              font=theme.FONT_SMALL, text_color="#FFFFFF",
                              fg_color=_status_color(order["status"]), corner_radius=8,
                              width=120, height=26)
        badge.pack(side="left")

        mid = ctk.CTkFrame(card, fg_color="transparent")
        mid.pack(fill="x", padx=14, pady=(0, 6))
        info_bits = [f"المعمل: {order.get('lab_name') or '-'}"]
        if order.get("lab_code"):
            info_bits.append(f"الرمز: {order['lab_code']}")
        if order.get("sent_date"):
            info_bits.append(f"تاريخ الإرسال: {order['sent_date']}")
        if order.get("received_date"):
            info_bits.append(f"تاريخ الاستلام: {order['received_date']}")
        if order.get("sent_by"):
            info_bits.append(f"المرسل: {order['sent_by']}")
        if order.get("received_by"):
            info_bits.append(f"المستلم بالمعمل: {order['received_by']}")
        if order.get("cost"):
            info_bits.append(f"التكلفة: {order['cost']:g} جنيه")
        ctk.CTkLabel(mid, text="   -   ".join(info_bits), font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED, wraplength=900,
                     justify="right").pack(anchor="e")

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkButton(actions, text="حذف", width=70, height=30, fg_color=theme.DANGER,
                      command=lambda o=order: self._delete_order(o)).pack(side="left", padx=3)
        ctk.CTkButton(actions, text="تعديل", width=70, height=30,
                      fg_color=theme.PRIMARY_LIGHT,
                      command=lambda o=order: self._open_edit_order_dialog(o)).pack(side="left", padx=3)

        # أزرار تغيير سريعة للحالة التالية المنطقية
        next_status_map = {"sent": "in_progress", "in_progress": "received", "received": "delivered"}
        next_status = next_status_map.get(order["status"])
        if next_status:
            ctk.CTkButton(actions, text=f"➜ {STATUS_LABELS[next_status]}", height=30,
                          fg_color=theme.SUCCESS,
                          command=lambda o=order, s=next_status: self._quick_set_status(o, s)
                          ).pack(side="right", padx=3)
        if order["status"] not in ("cancelled", "delivered"):
            ctk.CTkButton(actions, text="إلغاء الحالة", width=90, height=30,
                          fg_color=theme.BG_MAIN, text_color=theme.TEXT_DARK,
                          border_width=1, border_color=theme.BORDER,
                          command=lambda o=order: self._quick_set_status(o, "cancelled")
                          ).pack(side="right", padx=3)

    def _quick_set_status(self, order, status):
        db.set_lab_order_status(order["id"], status)
        self._refresh_orders()

    def _delete_order(self, order):
        if not messagebox.askyesno("تأكيد الحذف", "هل تريد حذف هذه الحالة نهائيًا؟\nسيتم حذف أي حركة مالية مرتبطة بها من حساب المعمل أيضًا."):
            return
        db.delete_lab_order(order["id"])
        self._refresh_orders()

    def _open_add_order_dialog(self):
        self._open_order_dialog(order=None)

    def _open_edit_order_dialog(self, order):
        self._open_order_dialog(order=order)

    def _open_order_dialog(self, order):
        labs = db.get_labs(active_only=True)
        if not labs:
            messagebox.showwarning("لا يوجد معامل", "لازم تضيف معمل واحد على الأقل أولاً من تاب \"المعامل\"")
            return

        is_edit = order is not None
        dialog = ctk.CTkToplevel(self)
        dialog.title("تعديل حالة معمل" if is_edit else "حالة معمل جديدة")
        dialog.geometry("460x680")
        dialog.grab_set()

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        def field_label(text):
            ctk.CTkLabel(scroll, text=text, font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(anchor="e", pady=(10, 2))

        # --- المريض (بحث + اختيار) ---
        field_label("اسم المريض (اختياري)")
        patient_entry = RTLEntry(scroll, width=400, height=38,
                                  placeholder_text="اكتب اسم المريض للبحث...")
        patient_entry.pack(fill="x")
        patient_results = ctk.CTkFrame(scroll, fg_color="transparent")
        patient_results.pack(fill="x")
        selected_patient = {"id": order["patient_id"] if is_edit else None,
                             "name": order.get("patient_name") if is_edit else None}
        if selected_patient["name"]:
            patient_entry.insert(0, selected_patient["name"])

        def search_patients(event=None):
            for w in patient_results.winfo_children():
                w.destroy()
            text = patient_entry.get().strip()
            if len(text) < 2:
                return
            matches = db.get_all_patients(search=text)[:6]
            for p in matches:
                ctk.CTkButton(
                    patient_results, text=p["full_name"], height=28, fg_color=theme.BG_MAIN,
                    text_color=theme.TEXT_DARK, anchor="e",
                    command=lambda pp=p: pick_patient(pp)).pack(fill="x", pady=1)

        def pick_patient(p):
            selected_patient["id"] = p["id"]
            selected_patient["name"] = p["full_name"]
            patient_entry.delete(0, "end")
            patient_entry.insert(0, p["full_name"])
            for w in patient_results.winfo_children():
                w.destroy()

        patient_entry.bind("<KeyRelease>", search_patients)

        # --- البند العلاجي / السن ---
        field_label("اسم البند العلاجي")
        treatment_entry = ctk.CTkEntry(scroll, width=400, height=38)
        treatment_entry.pack(fill="x")
        if is_edit:
            treatment_entry.insert(0, order.get("treatment_label") or "")

        field_label("رقم السن (اختياري)")
        tooth_entry = ctk.CTkEntry(scroll, width=400, height=38, justify="center")
        tooth_entry.pack(fill="x")
        if is_edit and order.get("tooth_number"):
            tooth_entry.insert(0, str(order["tooth_number"]))

        # --- المعمل ---
        field_label("المعمل")
        lab_names = _lab_names(labs)
        lab_menu = ctk.CTkOptionMenu(scroll, values=lab_names, width=400, **theme.optionmenu_colors())
        lab_menu.pack(fill="x")
        current_lab = next((l["name"] for l in labs if l["id"] == order["lab_id"]), lab_names[0]) if is_edit else lab_names[0]
        lab_menu.set(current_lab)

        # --- المرسل / المستلم ---
        field_label("المرسل (من العيادة)")
        sender_values = ["-- بدون تحديد --"] + _sender_options()
        sender_menu = ctk.CTkOptionMenu(scroll, values=sender_values, width=400, **theme.optionmenu_colors())
        sender_menu.pack(fill="x")
        sender_menu.set(order.get("sent_by") or "-- بدون تحديد --" if is_edit else "-- بدون تحديد --")

        field_label("المستلم بالمعمل")
        receiver_entry = ctk.CTkEntry(scroll, width=400, height=38)
        receiver_entry.pack(fill="x")
        if is_edit and order.get("received_by"):
            receiver_entry.insert(0, order["received_by"])
        else:
            selected_lab_obj = next((l for l in labs if l["name"] == current_lab), None)
            if selected_lab_obj and selected_lab_obj.get("contact_person"):
                receiver_entry.insert(0, selected_lab_obj["contact_person"])

        def on_lab_change(name):
            if receiver_entry.get().strip():
                return
            lab_obj = next((l for l in labs if l["name"] == name), None)
            if lab_obj and lab_obj.get("contact_person"):
                receiver_entry.insert(0, lab_obj["contact_person"])
        lab_menu.configure(command=on_lab_change)

        # --- الرمز عند المعمل ---
        field_label("رمز الحالة عند المعمل (اختياري)")
        code_entry = ctk.CTkEntry(scroll, width=400, height=38)
        code_entry.pack(fill="x")
        if is_edit and order.get("lab_code"):
            code_entry.insert(0, order["lab_code"])

        # --- الحالة ---
        field_label("حالة الشغل")
        status_menu = ctk.CTkOptionMenu(scroll, values=[STATUS_LABELS[s] for s in STATUS_ORDER], width=400,
                                         **theme.optionmenu_colors())
        status_menu.pack(fill="x")
        status_menu.set(STATUS_LABELS[order["status"]] if is_edit else STATUS_LABELS["sent"])

        # --- التواريخ ---
        dates_row = ctk.CTkFrame(scroll, fg_color="transparent")
        dates_row.pack(fill="x", pady=(10, 0))
        col1 = ctk.CTkFrame(dates_row, fg_color="transparent")
        col1.pack(side="right", expand=True, fill="x", padx=(4, 0))
        ctk.CTkLabel(col1, text="تاريخ الإرسال", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e")
        sent_date_entry = DateAutoEntry(col1, width=190, height=36)
        sent_date_entry.pack(fill="x")
        if is_edit and order.get("sent_date"):
            sent_date_entry.set_iso_date(order["sent_date"])

        col2 = ctk.CTkFrame(dates_row, fg_color="transparent")
        col2.pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkLabel(col2, text="التاريخ المتوقع للتسليم", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e")
        expected_date_entry = DateAutoEntry(col2, width=190, height=36)
        expected_date_entry.pack(fill="x")
        if is_edit and order.get("expected_date"):
            expected_date_entry.set_iso_date(order["expected_date"])

        # --- التكلفة ---
        field_label("تكلفة المعمل (جنيه)")
        cost_entry = ctk.CTkEntry(scroll, width=400, height=38, justify="center")
        cost_entry.pack(fill="x")
        cost_entry.insert(0, str(order["cost"]) if is_edit and order.get("cost") else "0")

        # --- ملاحظات ---
        field_label("ملاحظات")
        notes_entry = RTLEntry(scroll, width=400, height=60)
        notes_entry.pack(fill="x")
        if is_edit and order.get("notes"):
            notes_entry.insert(0, order["notes"])

        def save():
            treatment_label = treatment_entry.get().strip()
            if not treatment_label:
                messagebox.showwarning("بيانات ناقصة", "لازم تكتب اسم البند العلاجي")
                return
            try:
                tooth_number = int(tooth_entry.get().strip()) if tooth_entry.get().strip() else None
            except ValueError:
                tooth_number = None
            try:
                cost = float(cost_entry.get().strip() or 0)
            except ValueError:
                cost = 0
            lab_id = _lab_id_by_name(labs, lab_menu.get())
            sender = sender_menu.get()
            sender = "" if sender == "-- بدون تحديد --" else sender
            status_key = next(k for k, v in STATUS_LABELS.items() if v == status_menu.get())

            if is_edit:
                db.update_lab_order(
                    order["id"], lab_id=lab_id, tooth_number=tooth_number,
                    treatment_label=treatment_label, lab_code=code_entry.get().strip(),
                    status=status_key, sent_date=sent_date_entry.get_iso_date() or order.get("sent_date"),
                    expected_date=expected_date_entry.get_iso_date(),
                    sent_by=sender, received_by=receiver_entry.get().strip(),
                    cost=cost, notes=notes_entry.get())
            else:
                db.add_lab_order(
                    lab_id, patient_id=selected_patient["id"], tooth_number=tooth_number,
                    treatment_label=treatment_label, lab_code=code_entry.get().strip(),
                    status=status_key, sent_date=sent_date_entry.get_iso_date(),
                    expected_date=expected_date_entry.get_iso_date(),
                    sent_by=sender, received_by=receiver_entry.get().strip(),
                    cost=cost, notes=notes_entry.get())
            dialog.destroy()
            self._refresh_orders()

        ctk.CTkButton(scroll, text="حفظ", height=42, fg_color=theme.SUCCESS,
                      command=save).pack(fill="x", pady=(18, 4))

    # ==================== تاب: المعامل ====================

    def _build_labs_tab(self, parent):
        ctk.CTkButton(parent, text="+ معمل جديد", height=36, width=120,
                      fg_color=theme.SUCCESS,
                      command=self._open_add_lab_dialog).pack(anchor="w", pady=(4, 10))

        self.labs_list = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.labs_list.pack(fill="both", expand=True)
        self._refresh_labs()

    def _refresh_labs(self):
        for w in self.labs_list.winfo_children():
            w.destroy()
        labs = db.get_labs()
        if not labs:
            ctk.CTkLabel(self.labs_list, text="لا توجد معامل مسجلة",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED).pack(pady=30)
            return
        for lab in labs:
            card = ctk.CTkFrame(self.labs_list, fg_color=theme.CARD_BG, corner_radius=10)
            card.pack(fill="x", pady=5, padx=2)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=10)

            name_text = lab["name"] + ("" if lab["active"] else "  (معطّل)")
            ctk.CTkLabel(row, text=name_text, font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_DARK if lab["active"] else theme.TEXT_MUTED
                         ).pack(side="right")

            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.pack(side="left")
            ctk.CTkButton(btns, text="حذف", width=70, height=30, fg_color=theme.DANGER,
                          command=lambda l=lab: self._delete_lab(l)).pack(side="left", padx=3)
            toggle_text = "تعطيل" if lab["active"] else "تفعيل"
            ctk.CTkButton(btns, text=toggle_text, width=70, height=30,
                          fg_color=theme.WARNING if lab["active"] else theme.SUCCESS,
                          command=lambda l=lab: self._toggle_lab(l)).pack(side="left", padx=3)
            ctk.CTkButton(btns, text="تعديل", width=70, height=30, fg_color=theme.PRIMARY_LIGHT,
                          command=lambda l=lab: self._open_edit_lab_dialog(l)).pack(side="left", padx=3)

            details = []
            if lab.get("phone"):
                details.append(f"تليفون: {lab['phone']}")
            if lab.get("contact_person"):
                details.append(f"المسؤول: {lab['contact_person']}")
            if lab.get("address"):
                details.append(f"العنوان: {lab['address']}")
            if details:
                ctk.CTkLabel(card, text="   -   ".join(details), font=theme.FONT_SMALL,
                             text_color=theme.TEXT_MUTED, wraplength=900,
                             justify="right").pack(anchor="e", padx=14, pady=(0, 10))

    def _toggle_lab(self, lab):
        db.set_lab_active(lab["id"], not lab["active"])
        self._refresh_labs()

    def _delete_lab(self, lab):
        if not messagebox.askyesno(
                "تأكيد الحذف",
                f"هل تريد حذف معمل \"{lab['name']}\" نهائيًا؟\n"
                "سيتم حذف كل الحالات وحركات الحساب المرتبطة به.\n"
                "(الأفضل استخدام \"تعطيل\" بدل الحذف لو عندك سجل تعاملات قديم معه)"):
            return
        db.delete_lab(lab["id"])
        self._refresh_labs()
        self._refresh_orders()

    def _open_add_lab_dialog(self):
        self._open_lab_dialog(lab=None)

    def _open_edit_lab_dialog(self, lab):
        self._open_lab_dialog(lab=lab)

    def _open_lab_dialog(self, lab):
        is_edit = lab is not None
        dialog = ctk.CTkToplevel(self)
        dialog.title("تعديل معمل" if is_edit else "معمل جديد")
        dialog.geometry("380x480")
        dialog.grab_set()

        def field_label(text):
            ctk.CTkLabel(dialog, text=text, font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(anchor="e", padx=24, pady=(14, 2))

        field_label("اسم المعمل")
        name_entry = RTLEntry(dialog, width=330, height=38)
        name_entry.pack(padx=24)
        if is_edit:
            name_entry.insert(0, lab["name"])

        field_label("رقم التليفون")
        phone_entry = ctk.CTkEntry(dialog, width=330, height=38, justify="center")
        phone_entry.pack(padx=24)
        if is_edit and lab.get("phone"):
            phone_entry.insert(0, lab["phone"])

        field_label("الشخص المسؤول (المستلم الافتراضي)")
        contact_entry = RTLEntry(dialog, width=330, height=38)
        contact_entry.pack(padx=24)
        if is_edit and lab.get("contact_person"):
            contact_entry.insert(0, lab["contact_person"])

        field_label("العنوان")
        address_entry = RTLEntry(dialog, width=330, height=38)
        address_entry.pack(padx=24)
        if is_edit and lab.get("address"):
            address_entry.insert(0, lab["address"])

        field_label("ملاحظات")
        notes_entry = RTLEntry(dialog, width=330, height=60)
        notes_entry.pack(padx=24)
        if is_edit and lab.get("notes"):
            notes_entry.insert(0, lab["notes"])

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("بيانات ناقصة", "لازم تكتب اسم المعمل")
                return
            if is_edit:
                db.update_lab(lab["id"], name, phone_entry.get().strip(),
                              address_entry.get().strip(), contact_entry.get().strip(),
                              notes_entry.get())
            else:
                db.add_lab(name, phone_entry.get().strip(), address_entry.get().strip(),
                          contact_entry.get().strip(), notes_entry.get())
            dialog.destroy()
            self._refresh_labs()
            self._refresh_order_filters()

        ctk.CTkButton(dialog, text="حفظ", height=42, fg_color=theme.SUCCESS,
                      command=save).pack(padx=24, pady=18, fill="x")

    def _refresh_order_filters(self):
        labs = db.get_labs()
        self.order_lab_menu.configure(values=["كل المعامل"] + _lab_names(labs))

    # ==================== تاب: حساب المعمل ====================

    def _build_accounts_tab(self, parent):
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # عمود يمين: قائمة المعامل بالأرصدة
        left_col = ctk.CTkFrame(body, fg_color=theme.CARD_BG, corner_radius=12, width=300)
        left_col.pack(side="right", fill="y", padx=(0, 10))
        left_col.pack_propagate(False)
        ctk.CTkLabel(left_col, text="المعامل", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_DARK).pack(pady=(14, 6))
        self.labs_balance_list = ctk.CTkScrollableFrame(left_col, fg_color="transparent")
        self.labs_balance_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # عمود شمال: كشف حساب المعمل المختار
        right_col = ctk.CTkFrame(body, fg_color=theme.CARD_BG, corner_radius=12)
        right_col.pack(side="right", fill="both", expand=True)

        self.account_header = ctk.CTkLabel(right_col, text="اختر معمل من القائمة",
                                            font=theme.FONT_SUBTITLE, text_color=theme.TEXT_DARK)
        self.account_header.pack(pady=(14, 4), anchor="e", padx=16)

        self.account_balance_label = ctk.CTkLabel(right_col, text="", font=theme.FONT_NORMAL,
                                                    text_color=theme.TEXT_DARK)
        self.account_balance_label.pack(anchor="e", padx=16)

        self.add_payment_btn = ctk.CTkButton(right_col, text="+ تسجيل دفعة", height=34, width=130,
                                              fg_color=theme.SUCCESS, state="disabled",
                                              command=self._open_add_payment_dialog)
        self.add_payment_btn.pack(anchor="e", padx=16, pady=8)

        self.account_tx_list = ctk.CTkScrollableFrame(right_col, fg_color="transparent")
        self.account_tx_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._refresh_labs_balances()

    def _refresh_labs_balances(self):
        for w in self.labs_balance_list.winfo_children():
            w.destroy()
        labs = db.get_all_labs_with_balances()
        if not labs:
            ctk.CTkLabel(self.labs_balance_list, text="لا توجد معامل",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(pady=20)
            return
        for lab in labs:
            btn_color = theme.PRIMARY_LIGHT if lab["id"] == self.selected_account_lab_id else theme.BG_MAIN
            text_color = "#FFFFFF" if lab["id"] == self.selected_account_lab_id else theme.TEXT_DARK
            balance_text = f"{lab['balance']:g} جنيه" if lab["balance"] else "مسدد بالكامل"
            btn = ctk.CTkButton(
                self.labs_balance_list, text=f"{lab['name']}\n{balance_text}",
                height=52, fg_color=btn_color, text_color=text_color,
                command=lambda lid=lab["id"]: self._select_account_lab(lid))
            btn.pack(fill="x", pady=3)

    def _select_account_lab(self, lab_id):
        self.selected_account_lab_id = lab_id
        self._refresh_labs_balances()
        self._refresh_account_detail()

    def _refresh_account_detail(self):
        for w in self.account_tx_list.winfo_children():
            w.destroy()

        if not self.selected_account_lab_id:
            self.account_header.configure(text="اختر معمل من القائمة")
            self.account_balance_label.configure(text="")
            self.add_payment_btn.configure(state="disabled")
            return

        lab = db.get_lab(self.selected_account_lab_id)
        if not lab:
            self.selected_account_lab_id = None
            self._refresh_account_detail()
            return

        balance = db.get_lab_balance(lab["id"])
        self.account_header.configure(text=f"حساب: {lab['name']}")
        self.account_balance_label.configure(
            text=f"المستحق للمعمل حاليًا: {balance:g} جنيه" if balance > 0
            else ("رصيد صفر" if balance == 0 else f"مبلغ زيادة مدفوع للمعمل: {abs(balance):g} جنيه"),
            text_color=theme.DANGER if balance > 0 else theme.SUCCESS)
        self.add_payment_btn.configure(state="normal")

        txs = db.get_lab_transactions(lab["id"])
        if not txs:
            ctk.CTkLabel(self.account_tx_list, text="لا توجد حركات حساب بعد",
                         font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED).pack(pady=20)
            return

        for tx in txs:
            row = ctk.CTkFrame(self.account_tx_list, fg_color=theme.BG_MAIN, corner_radius=8)
            row.pack(fill="x", pady=3)
            is_charge = tx["tx_type"] == "charge"
            sign = "+" if is_charge else "-"
            color = theme.DANGER if is_charge else theme.SUCCESS
            label = "تكلفة شغل" if is_charge else "دفعة مسدَّدة"
            ctk.CTkLabel(row, text=f"{sign} {tx['amount']:g} جنيه", font=theme.FONT_NORMAL,
                         text_color=color, width=110).pack(side="right", padx=10, pady=8)
            desc = f"{label}"
            if tx.get("description"):
                desc += f" - {tx['description']}"
            desc += f"   ({tx['tx_date']})"
            ctk.CTkLabel(row, text=desc, font=theme.FONT_SMALL, text_color=theme.TEXT_DARK,
                         wraplength=420, justify="right").pack(side="right", padx=6)
            if tx["tx_type"] == "payment":
                ctk.CTkButton(row, text="حذف", width=54, height=26, fg_color=theme.DANGER,
                              command=lambda t=tx: self._delete_payment(t)).pack(side="left", padx=8)

    def _delete_payment(self, tx):
        if not messagebox.askyesno("تأكيد", "هل تريد حذف هذه الدفعة؟"):
            return
        db.delete_lab_transaction(tx["id"])
        self._refresh_labs_balances()
        self._refresh_account_detail()

    def _open_add_payment_dialog(self):
        if not self.selected_account_lab_id:
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("تسجيل دفعة للمعمل")
        dialog.geometry("340x300")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="المبلغ المدفوع (جنيه)", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e", padx=24, pady=(18, 2))
        amount_entry = ctk.CTkEntry(dialog, width=290, height=38, justify="center")
        amount_entry.pack(padx=24)

        ctk.CTkLabel(dialog, text="التاريخ", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e", padx=24, pady=(14, 2))
        date_entry = DateAutoEntry(dialog, width=290, height=38)
        dialog.after(50, lambda: date_entry.set_iso_date(__import__("datetime").date.today().isoformat()))
        date_entry.pack(padx=24)

        ctk.CTkLabel(dialog, text="ملاحظات (اختياري)", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(anchor="e", padx=24, pady=(14, 2))
        notes_entry = RTLEntry(dialog, width=290, height=50)
        notes_entry.pack(padx=24)

        def save():
            try:
                amount = float(amount_entry.get().strip())
            except ValueError:
                messagebox.showwarning("قيمة غير صحيحة", "اكتب مبلغ صحيح")
                return
            if amount <= 0:
                messagebox.showwarning("قيمة غير صحيحة", "المبلغ لازم يكون أكبر من صفر")
                return
            db.add_lab_transaction(self.selected_account_lab_id, "payment", amount,
                                   description=notes_entry.get(),
                                   tx_date=date_entry.get_iso_date() or None)
            dialog.destroy()
            self._refresh_labs_balances()
            self._refresh_account_detail()

        ctk.CTkButton(dialog, text="حفظ الدفعة", height=42, fg_color=theme.SUCCESS,
                      command=save).pack(padx=24, pady=18, fill="x")

    # ==================== تاب: إعدادات البنود العلاجية ====================

    def _build_settings_tab(self, parent):
        ctk.CTkLabel(
            parent, text="تحديد أي البنود العلاجية تُصنَّع في المعمل، وأي معمل هو الافتراضي "
                        "لكل بند، وذلك حتى ترسل تلقائيًا حالة إلى هذا المعمل عند تسجيل هذا العلاج "
                        "لأي مريض من شارت الأسنان.",
            font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED, wraplength=900,
            justify="right").pack(anchor="e", pady=(4, 10))

        settings = db.get_settings()
        price_list_id = settings.get("active_price_list_id") if settings else None
        self.settings_price_list_id = price_list_id

        self.settings_list = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.settings_list.pack(fill="both", expand=True)
        self._refresh_settings_tab()

    def _refresh_settings_tab(self):
        for w in self.settings_list.winfo_children():
            w.destroy()

        if not self.settings_price_list_id:
            ctk.CTkLabel(self.settings_list, text="لا توجد قائمة أسعار فعّالة حاليًا",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED).pack(pady=30)
            return

        items = db.get_treatment_items_with_lab_settings(self.settings_price_list_id)
        labs = db.get_labs(active_only=True)
        lab_values = ["بدون معمل افتراضي"] + _lab_names(labs)

        if not items:
            ctk.CTkLabel(self.settings_list, text="لا توجد بنود علاجية مسجلة",
                         font=theme.FONT_NORMAL, text_color=theme.TEXT_MUTED).pack(pady=30)
            return

        for item in items:
            row = ctk.CTkFrame(self.settings_list, fg_color=theme.CARD_BG, corner_radius=10)
            row.pack(fill="x", pady=4, padx=2)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(10, 4))

            label_text = item["label"]
            if item["is_variant"]:
                label_text = f"↳ {label_text}"
            ctk.CTkLabel(top, text=label_text, font=theme.FONT_NORMAL,
                         text_color=theme.TEXT_DARK).pack(side="right")

            requires_var = ctk.BooleanVar(value=bool(item["requires_lab"]))
            ctk.CTkCheckBox(top, text="يحتاج معمل", variable=requires_var,
                             font=theme.FONT_SMALL, **theme.checkbox_colors()).pack(side="left", padx=6)

            bottom = ctk.CTkFrame(row, fg_color="transparent")
            bottom.pack(fill="x", padx=14, pady=(0, 10))

            lab_menu = ctk.CTkOptionMenu(bottom, values=lab_values, width=200, **theme.optionmenu_colors())
            current_lab_name = next(
                (l["name"] for l in labs if l["id"] == item["default_lab_id"]), "بدون معمل افتراضي")
            lab_menu.set(current_lab_name)
            lab_menu.pack(side="right", padx=(6, 0))
            ctk.CTkLabel(bottom, text="المعمل الافتراضي:", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=(0, 4))

            code_entry = ctk.CTkEntry(bottom, width=140, height=32, justify="center",
                                       placeholder_text="رمز عند المعمل")
            if item.get("lab_code"):
                code_entry.insert(0, item["lab_code"])
            code_entry.pack(side="right", padx=(6, 10))
            ctk.CTkLabel(bottom, text="الرمز:", font=theme.FONT_SMALL,
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=(0, 4))

            def save_row(item=item, requires_var=requires_var, lab_menu=lab_menu, code_entry=code_entry):
                lab_name = lab_menu.get()
                lab_id = _lab_id_by_name(labs, lab_name) if lab_name != "بدون معمل افتراضي" else None
                if item["is_variant"]:
                    db.update_treatment_variant_lab_settings(
                        item["id"], requires_var.get(), lab_id, code_entry.get().strip())
                else:
                    db.update_treatment_price_lab_settings(
                        self.settings_price_list_id, item["treatment_key"], requires_var.get(),
                        lab_id, code_entry.get().strip())

            ctk.CTkButton(bottom, text="حفظ", width=64, height=32, fg_color=theme.SUCCESS,
                          command=save_row).pack(side="left")

    # ==================== واجهة عامة (تُستخدم من صفحات تانية) ====================

    def refresh_all(self):
        self._refresh_orders()
        self._refresh_labs()
        self._refresh_labs_balances()
        self._refresh_account_detail()
        self._refresh_settings_tab()
