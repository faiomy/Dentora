# -*- coding: utf-8 -*-
"""
حزمة Dentora API - واجهة برمجة تطبيقات لعيادة الأسنان.

الاستيراد بيضيف مجلد المشروع لـ sys.path (زي qt_main.py) عشان `database`
و`dentora_events` يتستوردوا من أي مكان ينعَت منه الحزمة.
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)