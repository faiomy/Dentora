# -*- coding: utf-8 -*-
"""
خلية حقل قابلة للسحب (تغيير المكان) وتغيير المقاس (بمقبض في الزاوية)،
تستخدم في وضع "تعديل الشكل" بس. في الوضع العادي بتكون مقفولة (مش قابلة للسحب).
"""

import customtkinter as ctk
import theme

GRIP_SIZE = 16


class DraggableCell(ctk.CTkFrame):
    def __init__(self, parent, field_key, x, y, w, h, edit_mode_getter, on_change, **kwargs):
        # في نسخ الـ customtkinter الحديثة، width/height لازم تتحدد وقت إنشاء
        # الودجت مش في place() - عكس الإصدارات الأقدم
        super().__init__(parent, fg_color=theme.BG_MAIN, corner_radius=8,
                          width=w, height=h, **kwargs)
        self.field_key = field_key
        self.edit_mode_getter = edit_mode_getter
        self.on_change = on_change

        self.place(x=x, y=y)

        self._drag_start = None
        self.bind("<ButtonPress-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)
        self.bind("<ButtonRelease-1>", self._end_drag)
        self.configure(cursor="fleur")

        # مقبض تغيير المقاس - مثلث صغير في الركن (يمين-تحت بصريًا)
        self.grip = ctk.CTkLabel(self, text="◢", font=(theme.FONT_FAMILY, 12),
                                  text_color=theme.TEXT_MUTED, cursor="bottom_right_corner",
                                  width=GRIP_SIZE, height=GRIP_SIZE)
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        self._resize_start = None
        self.grip.bind("<ButtonPress-1>", self._start_resize)
        self.grip.bind("<B1-Motion>", self._do_resize)
        self.grip.bind("<ButtonRelease-1>", self._end_resize)

        self._refresh_edit_look()

    def _refresh_edit_look(self):
        if self.edit_mode_getter():
            self.configure(border_width=2, border_color=theme.ACCENT_BORDER)
            self.grip.configure(text_color=theme.ACCENT_BORDER)
        else:
            self.configure(border_width=0)
            self.grip.configure(text_color=theme.TEXT_MUTED)

    # ---------------- السحب (تغيير المكان) ----------------

    def _start_drag(self, event):
        if not self.edit_mode_getter():
            return
        self._drag_start = (event.x, event.y)

    def _do_drag(self, event):
        if not self.edit_mode_getter() or self._drag_start is None:
            return
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        new_x = max(self.winfo_x() + dx, 0)
        new_y = max(self.winfo_y() + dy, 0)
        self.place(x=new_x, y=new_y)

    def _end_drag(self, event):
        if not self.edit_mode_getter():
            return
        self._drag_start = None
        self.on_change(self.field_key, self.winfo_x(), self.winfo_y(),
                        self.winfo_width(), self.winfo_height())

    # ---------------- تغيير المقاس ----------------

    def _start_resize(self, event):
        if not self.edit_mode_getter():
            return
        self._resize_start = (event.x_root, event.y_root, self.winfo_width(), self.winfo_height())

    def _do_resize(self, event):
        if not self.edit_mode_getter() or self._resize_start is None:
            return
        sx, sy, sw, sh = self._resize_start
        new_w = max(sw + (event.x_root - sx), 70)
        new_h = max(sh + (event.y_root - sy), 40)
        # تغيير المقاس بيبقى بـ configure() مش place()، لأن place() في النسخ
        # الحديثة من customtkinter بترفض width/height خالص
        self.configure(width=new_w, height=new_h)

    def _end_resize(self, event):
        if not self.edit_mode_getter():
            return
        self._resize_start = None
        self.on_change(self.field_key, self.winfo_x(), self.winfo_y(),
                        self.winfo_width(), self.winfo_height())
