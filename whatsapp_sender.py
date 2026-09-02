# -*- coding: utf-8 -*-
"""
دوال مشتركة لفتح محادثة واتساب وإرسال رسالة جاهزة فيها.
تُستخدم من مكانين:
1) صفحة واتساب اليدوية (whatsapp_page.py) عند الضغط على زر "إرسال".
2) حلقة الأرشفة التلقائية في main.py (تذكير قبل الموعد بساعة + شكر بعد
   انتهائه بساعتين)، بحيث لا يتكرر نفس الكود مرتين.
"""

import os
import sys
import subprocess
import webbrowser

import database as db

# محاولة استيراد pyautogui - تُستخدم فقط لضغط زر الإرسال تلقائيًا بعد فتح
# المحادثة. في حال عدم تثبيتها، تُفتح المحادثة جاهزة وتحتاج ضغطة إرسال يدوية،
# ولا يتعطل عمل البرنامج بسبب ذلك.
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False


def open_whatsapp_chat(phone_number, message, use_desktop_app=True):
    """تفتح محادثة واتساب برسالة جاهزة لرقم معيّن.
    لو use_desktop_app=True: تحاول فتح تطبيق واتساب لسطح المكتب مباشرة عبر
    بروتوكول whatsapp:// (الأضمن عند إرسال عدة رسائل متتالية لأنه لا يعتمد
    على تبويبات متصفح متعددة). لو فشلت المحاولة (التطبيق غير مثبَّت) أو كان
    الخيار غير مفعَّل، تُفتح صفحة wa.me في المتصفح كخطة احتياطية (واتساب ويب)."""
    if use_desktop_app:
        desktop_link = db.build_whatsapp_desktop_link(phone_number, message)
        try:
            if sys.platform.startswith("win"):
                os.startfile(desktop_link)
            elif sys.platform == "darwin":
                subprocess.run(["open", desktop_link], check=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["xdg-open", desktop_link], check=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            # التطبيق غير مثبَّت على الأرجح - نكمل بالطريقة الاحتياطية عبر المتصفح
            pass

    web_link = db.build_whatsapp_link(phone_number, message)
    # فتح المحادثة في تبويب جديد بدلًا من أن يحل محل التبويب السابق، حتى تبقى
    # كل محادثة ظاهرة بمفردها عند إرسال عدة رسائل متتالية
    webbrowser.open_new_tab(web_link)


def press_enter_later(tk_widget, wait_ms):
    """تجدول ضغطة Enter تلقائية بعد wait_ms ملي ثانية باستخدام حلقة أحداث
    tkinter الخاصة بـ tk_widget (أي ويدجت أو نافذة عندها after())، حتى تُرسَل
    الرسالة فعليًا من دون تدخل يدوي. لا تفعل شيئًا لو pyautogui غير متاحة."""
    if not PYAUTOGUI_AVAILABLE:
        return
    tk_widget.after(wait_ms, lambda: pyautogui.press("enter"))
