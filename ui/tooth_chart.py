# -*- coding: utf-8 -*-
"""Qt odontogram (dental chart) for the patient profile.

Functional, painter-native port of the legacy CustomTk dental chart
(``pages/tooth_chart_widget.py``): it renders the 32 permanent FDI tooth
positions, the per-tooth *presence* status saved in ``tooth_chart``, any
*treatment records* registered on a tooth (drawn through the shared tooth
symbol library ``pages.tooth_symbols`` via a small Tk-canvas-compatible
painter adapter, so the exact same symbol functions are reused), plus free
tooth notes and doctor annotations.

Clicking a tooth opens a dialog to change its presence status / note, record
a follow-up annotation, or add a new treatment - which, exactly like the
legacy chart, also creates the matching financial charge so the odontogram
and the patient account stay in sync.

All data operations reuse the existing ``database`` module; nothing here is
static or sample data.
"""

from datetime import date

from PySide6.QtCore import Qt, QRectF, QRect, QPointF, Signal
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QPolygonF,
    QStandardItemModel,
    QStandardItem,
    QFont,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDialog,
    QFormLayout,
    QComboBox,
    QPlainTextEdit,
    QLineEdit,
    QDoubleSpinBox,
    QDialogButtonBox,
    QFrame,
    QInputDialog,
)

import database as db
from . import design
from .components import (
    DataTable,
    PrimaryButton,
    SecondaryButton,
    FieldLabel,
    Card,
    show_info,
    show_error,
)
from .constants import ltr
from pages import tooth_symbols
from pages.teething_timeline import (
    UPPER_ROW,
    LOWER_ROW,
    PRESENCE_CHOICES,
    PRESENCE_LABELS,
)

# اضافي رموز عرض للبنود اللي ليها رسمة خاصة على السن (مش مجرد رمز توضيحي):
# التاج بيتشال بنفس منطق اللون الفرعي، والخلع بيدعم الشبح الكامل
_TREATMENT_SYMBOL = dict(tooth_symbols.BUILTIN_DISPLAY_SYMBOLS)
_TREATMENT_SYMBOL.setdefault("crown", "dome_cap")
_TREATMENT_SYMBOL.setdefault("extracted", "x_mark")

# لون ذهبي ثابت لتركيب التاج لما مايكونش لون فرعي محدد
_CROWN_DEFAULT_COLOR = "#C7A052"

# ترتيب رسم رموز المعالجات على السن الواحد (من الأسفل فوق بعضها)
_TREATMENT_DRAW_ORDER = ("decay", "filled", "root_canal", "calculus", "post",
                         "implant", "crown", "extracted")

# ألوان حالات البزوغ (مطابقة لمنطق الألوان القديم في شارت الأسنان)
_PRESENCE_STYLE = {
    "present":        {"fill": "#FFFFFF",      "border": design.PRIMARY_400,  "dashed": False},
    "primary_present": {"fill": "#FFF6E7",     "border": design.WARNING_400,  "dashed": False},
    "unerupted":      {"fill": "#EEEEF2",      "border": design.TEXT_MUTED,   "dashed": True},
    "missing":        {"fill": design.ERROR_50, "border": design.ERROR_400,   "dashed": False},
    "impacted":       {"fill": design.WARNING_50, "border": design.WARNING_400, "dashed": True},
}

_M = 8        # الهامش الخارجي حول الرسمة
_TITLE_H = 20  # ارتفاع عنوان "الفك العلوي / السفلي"


class _PainterAdapter:
    """Tk-canvas-compatible drawing facade over a QPainter.

    ``pages.tooth_symbols`` draws its symbols against a Tk canvas API
    (``create_line`` / ``create_oval`` / ``create_polygon`` /
    ``create_rectangle`` / ``create_arc`` with ``fill`` / ``outline`` /
    ``width`` / ``style`` kwargs). This tiny adapter exposes the same method
    names on top of Qt primitives so the whole symbol library is reused
    unchanged for the Qt odontogram.
    """

    def __init__(self, painter: QPainter):
        self._p = painter

    # -- helpers -------------------------------------------------------
    def _pen(self, color, width=1, dash=False):
        pen = QPen(QColor(color or "#000000"), max(1, int(width or 1)))
        if dash:
            pen.setStyle(Qt.DashLine)
        return pen

    def _brush(self, fill):
        if fill and fill != "":
            return QBrush(QColor(fill))
        return QBrush(Qt.NoBrush)

    # -- canvas API mirrored from Tk ----------------------------------
    def create_line(self, *coords, **kw):
        pen = self._pen(kw.get("fill", "#000000"), kw.get("width", 1))
        self._p.setPen(pen)
        pts = [QPointF(float(coords[i]), float(coords[i + 1]))
               for i in range(0, len(coords) - 1, 2)]
        if len(pts) == 2:
            self._p.drawLine(pts[0], pts[1])
        elif len(pts) > 2:
            self._p.drawPolyline(QPolygonF(pts))

    def create_oval(self, x1, y1, x2, y2, **kw):
        rect = QRectF(x1, y1, x2 - x1, y2 - y1)
        outline = kw.get("outline", kw.get("fill") or "#000000")
        self._p.setBrush(self._brush(kw.get("fill")))
        self._p.setPen(self._pen(outline, kw.get("width", 1)))
        self._p.drawEllipse(rect)

    def create_rectangle(self, x1, y1, x2, y2, **kw):
        rect = QRectF(x1, y1, x2 - x1, y2 - y1)
        outline = kw.get("outline", kw.get("fill") or "#000000")
        self._p.setBrush(self._brush(kw.get("fill")))
        self._p.setPen(self._pen(outline, kw.get("width", 1)))
        self._p.drawRect(rect)

    def create_polygon(self, *pts, **kw):
        poly = QPolygonF([QPointF(float(pts[i]), float(pts[i + 1]))
                         for i in range(0, len(pts) - 1, 2)])
        outline = kw.get("outline", kw.get("fill") or "#000000")
        self._p.setBrush(self._brush(kw.get("fill")))
        self._p.setPen(self._pen(outline, kw.get("width", 1)))
        self._p.drawPolygon(poly)

    def create_arc(self, x1, y1, x2, y2, **kw):
        rect = QRectF(x1, y1, x2 - x1, y2 - y1)
        outline = kw.get("outline", kw.get("fill") or "#000000")
        self._p.setBrush(self._brush(kw.get("fill")))
        self._p.setPen(self._pen(outline, kw.get("width", 1)))
        start = int(float(kw.get("start", 0)) * 16)
        extent = int(float(kw.get("extent", 360)) * 16)
        if str(kw.get("style", "pieslice")).lower() == "chord":
            self._p.drawChord(rect, start, extent)
        elif str(kw.get("style", "pieslice")).lower() == "arc":
            self._p.drawArc(rect, start, extent)
        else:
            self._p.drawPie(rect, start, extent)


def _tooth_shape(rect: QRectF) -> QPainterPath:
    """Morar-ish silhouette (crown + two root lobes) used for every tooth."""
    w, h = rect.width(), rect.height()
    path = QPainterPath()
    path.setFillRule(Qt.WindingFill)
    crown = QRectF(rect.left() + w * 0.10, rect.top() + h * 0.14, w * 0.80, h * 0.50)
    path.addRoundedRect(crown, w * 0.16, w * 0.16)
    path.addEllipse(QRectF(rect.left() + w * 0.14, rect.top() + h * 0.30, w * 0.34, h * 0.66))
    path.addEllipse(QRectF(rect.left() + w * 0.52, rect.top() + h * 0.30, w * 0.34, h * 0.66))
    return path


class ToothChartView(QWidget):
    """Paint-only widget showing the 32 FDI teeth for one patient.

    State is (re)loaded from ``database`` on every :meth:`refresh`; a tooth
    click emits :attr:`toothClicked` with the FDI number.
    """

    toothClicked = Signal(int)

    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.setMinimumSize(720, 330)
        self.setMouseTracking(True)
        self._hover = None
        self._cell_rects = {}
        self._presence = {}
        self._conditions = {}
        self._annotations = {}
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        self._presence = db.get_tooth_presence(self.patient_id)
        self._conditions = db.get_active_tooth_conditions(self.patient_id)
        self._annotations = db.get_tooth_annotations_map(self.patient_id)
        self.update()

    # ------------------------------------------------------------------
    def _tooth_has_marker(self, tooth):
        p = self._presence.get(tooth)
        if p and (p.get("notes") or "").strip():
            return True
        return tooth in self._annotations

    # ------------------------------------------------------------------
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(design.SURFACE))

        w = self.width()
        avail_w = w - _M * 2
        top_area = self.height() - _M * 2
        if avail_w <= 0:
            return

        cell_w = avail_w / 16.0
        row_h = (top_area - _TITLE_H * 2 - _M) / 2.0
        tooth_w = cell_w * 0.78
        tooth_h = row_h * 0.86

        self._cell_rects = {}
        self._paint_row(painter, UPPER_ROW, True,
                        _M, _M + _TITLE_H + (row_h - tooth_h) / 2,
                        avail_w, tooth_w, tooth_h, "الفك العلوي")
        lower_y = _M + _TITLE_H * 2 + _M + row_h + (row_h - tooth_h) / 2
        self._paint_row(painter, LOWER_ROW, False,
                        _M, lower_y, avail_w, tooth_w, tooth_h, "الفك السفلي")

    def _paint_row(self, painter, teeth, is_upper, x0, y0, avail_w,
                   tooth_w, tooth_h, title):
        font = QFont(design.FONT_FAMILY, int(design.FONT_SIZE_SM))
        painter.setFont(font)
        painter.setPen(QColor(design.TEXT_SECONDARY))
        ty = y0 - 16 if is_upper else y0 + tooth_h + 6
        painter.drawText(QRect(x0, int(ty), int(avail_w), _TITLE_H),
                         Qt.AlignCenter, title)

        for i, tooth_num in enumerate(teeth):
            cell = avail_w / 16.0
            cx = x0 + i * cell + (cell - tooth_w) / 2
            cy = y0
            rect = QRectF(cx, cy, tooth_w, tooth_h)
            self._cell_rects[tooth_num] = rect
            painter.save()
            if not is_upper:
                painter.translate(rect.center())
                painter.rotate(180)
                painter.translate(-rect.center())

            status = (self._presence.get(tooth_num) or {}).get("status")
            style = _PRESENCE_STYLE.get(status, _PRESENCE_STYLE["present"])
            conditions = self._conditions.get(tooth_num) or {}
            is_extracted = "extracted" in conditions

            shape = _tooth_shape(rect)
            if is_extracted:
                painter.setBrush(QBrush(QColor("#F0EFF3")))
                pen = QPen(QColor("#B7B4C4"), 1.6)
                pen.setStyle(Qt.SolidLine)
                painter.setPen(pen)
                painter.drawPath(shape)
            else:
                painter.setBrush(QBrush(QColor(style["fill"])))
                painter.setPen(self._pen(style["border"], 1.6, style["dashed"]))
                painter.drawPath(shape)

            # حجم وسط السن (مكان رسم رموز المعالجات)
            r = min(tooth_w * 0.22, tooth_h * 0.20)
            center = rect.center()

            if is_extracted:
                self._draw_glyph(painter, "x_mark", center, r * 1.35, "#9B99AC")
            else:
                for key in _TREATMENT_DRAW_ORDER:
                    record = conditions.get(key)
                    if not record:
                        continue
                    if key == "crown":
                        color = (record.get("variant_color") or _CROWN_DEFAULT_COLOR)
                        self._draw_glyph(painter, "dome_cap",
                                         QPointF(center.x(), center.y() - tooth_h * 0.12),
                                         min(tooth_w * 0.42, tooth_h * 0.30), color)
                    else:
                        symbol = _TREATMENT_SYMBOL.get(key)
                        if symbol:
                            self._draw_glyph(painter, symbol, center, r,
                                             tooth_symbols.BUILTIN_TREATMENT_COLORS.get(key, "#1E88E5"))

            painter.restore()

            # الرقم داخل جزء التاج من السن (بيتطبع في إطار إحداثيات غير مدوّر)
            painter.setFont(font)
            painter.setPen(QColor(design.TEXT_SECONDARY))
            nr = QRect(int(cx), int(cy + tooth_h - 11), int(tooth_w), 12)
            painter.drawText(nr, Qt.AlignCenter, str(tooth_num))

            # علامة ملاحظة/طبيب على السن
            if self._tooth_has_marker(tooth_num):
                painter.setPen(QPen(QColor(design.ACCENT_400), 0))
                painter.setBrush(QBrush(QColor(design.ACCENT_400)))
                painter.drawEllipse(QPointF(cx + 3, cy + 2), 2.6, 2.6)

            # تمييز السن المعلّق عليه المؤشر
            if self._hover == tooth_num:
                painter.setPen(QPen(QColor(design.PRIMARY_600), 2.0))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 6, 6)

    def _pen(self, color, width=1.0, dash=False):
        pen = QPen(QColor(color), width)
        pen.setStyle(Qt.DashLine if dash else Qt.SolidLine)
        return pen

    def _draw_glyph(self, painter, symbol_key, center, radius, color):
        adapter = _PainterAdapter(painter)
        tooth_symbols.draw_symbol(adapter, symbol_key, center.x(), center.y(),
                                  radius, color)

    # ------------------------------------------------------------------
    def _tooth_at(self, pos) -> int:
        for tooth_num, rect in self._cell_rects.items():
            if rect.adjusted(-3, -3, 3, 3).contains(pos):
                return tooth_num
        return None

    def mouseMoveEvent(self, event):
        tooth = self._tooth_at(event.position())
        if tooth != self._hover:
            self._hover = tooth
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, _event):
        if self._hover is not None:
            self._hover = None
            self.update()
        super().leaveEvent(_event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            tooth = self._tooth_at(event.position())
            if tooth is not None:
                self.toothClicked.emit(tooth)
        super().mousePressEvent(event)


class ToothDetailsDialog(QDialog):
    """One tooth's details: presence status + free note, doctor annotation,
    and adding a new treatment (with its matching financial charge)."""

    def __init__(self, patient_id, tooth_number, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.tooth_number = tooth_number
        self.setWindowTitle(f"سن رقم {tooth_number}")
        self.setModal(True)
        self.resize(560, 640)
        self._price_list_id = None
        self._price_items = []
        self._crown_variants = []
        self._build_ui()
        self._load_options()
        self.reload()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(design.SPACING * 2)

        title = QLabel(f"السن رقم {self.tooth_number}")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(design.SPACING_SM)

        self.presence_combo = QComboBox()
        self.presence_combo.addItems([PRESENCE_LABELS[k] for k in PRESENCE_CHOICES])
        self._presence_keys = list(PRESENCE_CHOICES)
        form.addRow(FieldLabel("حالة السن"), self.presence_combo)

        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("ملاحظة حرة على السن (اختياري)")
        self.note_edit.setFixedHeight(56)
        form.addRow(FieldLabel("الملاحظة"), self.note_edit)
        root.addLayout(form)

        anno_title = QLabel("ملحوظة الطبيب")
        anno_title.setObjectName("SectionTitle")
        root.addWidget(anno_title)
        anno_form = QFormLayout()
        anno_form.setSpacing(design.SPACING_SM)
        self.doctor_combo = QComboBox()
        self.doctor_combo.addItem("")
        for d in db.get_doctors():
            self.doctor_combo.addItem(str(d.get("full_name") or ""))
        anno_form.addRow(FieldLabel("الطبيب"), self.doctor_combo)
        self.annotation_edit = QPlainTextEdit()
        self.annotation_edit.setPlaceholderText("ملحوظة مفصّلة (تاريخ اليوم تُحفظ تلقائيًا)")
        self.annotation_edit.setFixedHeight(60)
        anno_form.addRow(FieldLabel("النص"), self.annotation_edit)
        root.addLayout(anno_form)

        tx_title = QLabel("إضافة معالجة")
        tx_title.setObjectName("SectionTitle")
        root.addWidget(tx_title)

        tx_card = Card(parent=self, padding=True)
        tx_card.setMinimumHeight(150)
        tx_form = QFormLayout(tx_card)
        tx_form.setSpacing(design.SPACING_SM)

        self.treatment_combo = QComboBox()
        self.treatment_combo.currentIndexChanged.connect(self._on_treatment_changed)
        tx_form.addRow(FieldLabel("العلاج"), self.treatment_combo)

        self.variant_combo = QComboBox()
        self.variant_combo.currentIndexChanged.connect(self._on_variant_changed)
        tx_form.addRow(FieldLabel("النوع الفرعي"), self.variant_combo)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 10_000_000)
        self.price_spin.setDecimals(2)
        self.price_spin.setSingleStep(10)
        tx_form.addRow(FieldLabel("السعر"), self.price_spin)

        self.tx_notes = QLineEdit()
        self.tx_notes.setPlaceholderText("ملاحظات المعالجة (اختياري)")
        tx_form.addRow(FieldLabel("ملاحظات"), self.tx_notes)

        add_tx_btn = PrimaryButton("إضافة معالجة")
        add_tx_btn.clicked.connect(self._add_treatment)
        tx_form.addRow("", add_tx_btn)
        root.addWidget(tx_card)

        rec_title = QLabel("معالجات مسجّلة على هذا السن")
        rec_title.setObjectName("SectionTitle")
        root.addWidget(rec_title)
        self.records_table = DataTable()
        self.records_model = QStandardItemModel()
        self.records_model.setHorizontalHeaderLabels(
            ["التاريخ", "المعالجة", "المبلغ", "الطبيب"])
        self.records_table.setModel(self.records_model)
        self.records_table.configure_columns(stretch=1)
        root.addWidget(self.records_table, stretch=1)

        buttons = QDialogButtonBox()
        save_btn = buttons.addButton("حفظ الحالة", QDialogButtonBox.AcceptRole)
        close_btn = buttons.addButton("إغلاق", QDialogButtonBox.RejectRole)
        save_btn.clicked.connect(self._save)
        close_btn.clicked.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    def _load_options(self):
        settings = db.get_settings()
        self._price_list_id = settings.get("active_price_list_id") if settings else None
        items = db.get_treatment_prices(self._price_list_id) if self._price_list_id else {}
        self._price_items = []
        for key, row in items.items():
            self._price_items.append({
                "key": key,
                "label": str(row.get("label") or key),
                "price": float(row.get("price") or 0),
            })
        for item in sorted(self._price_items, key=lambda i: i["label"]):
            self.treatment_combo.addItem(f"{item['label']} ({ltr(str(item['price']))})", item)
        self._crown_variants = (
            db.get_treatment_variants(self._price_list_id, "crown") if self._price_list_id else [])
        for v in self._crown_variants:
            self.variant_combo.addItem(
                f"{v['variant_name']} ({ltr(str(v['price']))})", v)
        self._on_treatment_changed()

    # ------------------------------------------------------------------
    def reload(self):
        presence = db.get_tooth_presence(self.patient_id).get(self.tooth_number)
        status = (presence or {}).get("status")
        if status in self._presence_keys:
            self.presence_combo.setCurrentIndex(self._presence_keys.index(status))
        self.note_edit.setPlainText((presence or {}).get("notes") or "")

        annotation = db.get_tooth_annotation(self.patient_id, self.tooth_number)
        if annotation:
            doctor = annotation.get("doctor_name") or ""
            idx = self.doctor_combo.findText(doctor)
            if idx >= 0:
                self.doctor_combo.setCurrentIndex(idx)
            self.annotation_edit.setPlainText(annotation.get("note_text") or "")

        self._reload_records()

    def _reload_records(self):
        records = [r for r in db.get_treatment_records(self.patient_id)
                   if r.get("tooth_number") == self.tooth_number]
        records.sort(key=lambda r: (r.get("treatment_date") or "", r.get("id") or 0))
        self.records_model.removeRows(0, self.records_model.rowCount())
        for r in records:
            self.records_model.appendRow([QStandardItem(v) for v in (
                str(r.get("treatment_date") or ""),
                str(r.get("treatment_label") or ""),
                ltr(str(r.get("price") or 0)),
                str(r.get("doctor_name") or ""),
            )])

    # ------------------------------------------------------------------
    def _current_treatment(self):
        idx = self.treatment_combo.currentIndex()
        if idx < 0:
            return None
        return self.treatment_combo.itemData(idx)

    def _on_treatment_changed(self):
        item = self._current_treatment()
        is_crown = bool(item and item["key"] == "crown")
        self.variant_combo.setVisible(is_crown)
        self.price_spin.setValue(item["price"] if item else 0)
        if item and item["key"] == "crown" and self.variant_combo.count():
            self.variant_combo.setCurrentIndex(0)

    def _on_variant_changed(self):
        item = self._current_treatment()
        if not item or item["key"] != "crown":
            return
        idx = self.variant_combo.currentIndex()
        if idx >= 0:
            self.price_spin.setValue(float(self.variant_combo.itemData(idx).get("price") or 0))

    def _add_treatment(self):
        item = self._current_treatment()
        if not item:
            show_info(self, "لا يوجد علاج", "اختر علاجًا من قائمة أسعار العيادة أولًا.")
            return
        key = item["key"]
        label = item["label"]
        price = round(self.price_spin.value(), 2)
        notes = self.tx_notes.text().strip()
        doctor = self.doctor_combo.currentText().strip()
        variant = None
        if key == "crown":
            idx = self.variant_combo.currentIndex()
            if idx >= 0:
                variant = self.variant_combo.itemData(idx)
        try:
            record_id = db.add_treatment_record(
                self.patient_id, self.tooth_number, key, label, price,
                notes=notes, doctor_name=doctor,
                variant_name=(variant["variant_name"] if variant else None),
                variant_color=(variant.get("color") if variant else None))
            if price > 0:
                db.add_transaction(self.patient_id, "charge", price,
                                   description=label, related_treatment_id=record_id)
        except Exception as exc:  # pragma: no cover - defensive
            show_error(self, "تعذّر الحفظ", f"حدث خطأ أثناء حفظ المعالجة:\n{exc}")
            return
        self.tx_notes.clear()
        self._reload_records()

    def _save(self):
        status = self._presence_keys[self.presence_combo.currentIndex()]
        notes = self.note_edit.toPlainText().strip()
        doctor = self.doctor_combo.currentText().strip()
        annotation = self.annotation_edit.toPlainText().strip()
        try:
            db.set_tooth_status(self.patient_id, self.tooth_number, status, notes)
            if annotation:
                db.upsert_tooth_annotation(
                    self.patient_id, self.tooth_number,
                    date.today().isoformat(), doctor, annotation)
            else:
                db.delete_tooth_annotation(self.patient_id, self.tooth_number)
        except Exception as exc:  # pragma: no cover - defensive
            show_error(self, "تعذّر الحفظ", f"حدث خطأ أثناء الحفظ:\n{exc}")
            return
        self.accept()


class ToothChartWidget(QWidget):
    """Full odontogram for a patient: interactive view + legend + auto-chart."""

    def __init__(self, patient_id, birth_date=None, on_changed=None, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.birth_date = birth_date or ""
        self._on_changed = on_changed
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(design.SPACING_MD)

        self.chart_label = QLabel("خريطة الأسنان (حسب ترقيم FDI)")
        self.chart_label.setObjectName("SectionTitle")
        root.addWidget(self.chart_label)

        self.view = ToothChartView(self.patient_id)
        self.view.toothClicked.connect(self._open_tooth)
        root.addWidget(self.view)

        root.addWidget(self._build_legend())

        actions = QHBoxLayout()
        actions.setSpacing(design.SPACING_SM)
        self.auto_btn = SecondaryButton("إعادة توليد الشارت حسب العمر")
        self.auto_btn.setToolTip("يبني خريطة مبدئية من جدول التسنين (WHO/ADA) حسب عمر المريض")
        self.auto_btn.setEnabled(bool(self.birth_date))
        self.auto_btn.clicked.connect(self._auto_generate)
        actions.addWidget(self.auto_btn)
        actions.addStretch()
        help_label = QLabel("اضغط على أي سن لعرض تفاصيلها / تعديلها")
        help_label.setObjectName("PageSubtitle")
        actions.addWidget(help_label)
        root.addLayout(actions)

    def _build_legend(self):
        legend = QHBoxLayout()
        legend.setSpacing(design.SPACING_LG)
        for status_key in PRESENCE_CHOICES:
            style = _PRESENCE_STYLE.get(status_key, _PRESENCE_STYLE["present"])
            chip = QFrame()
            chip.setFixedSize(14, 14)
            chip.setStyleSheet(
                f"background:{style['fill']};border:1.5px solid {style['border']};"
                f"border-radius:3px;")
            legend.addWidget(chip)
            legend.addWidget(QLabel(PRESENCE_LABELS[status_key]))
        marker = QFrame()
        marker.setFixedSize(14, 14)
        marker.setStyleSheet(
            f"background:{design.ACCENT_400};border-radius:7px;")
        legend.addWidget(marker)
        legend.addWidget(QLabel("ملاحظة / ملحوظة طبيب"))
        legend.addStretch()
        wrap = QFrame()
        wrap.setLayout(legend)
        return wrap

    # ------------------------------------------------------------------
    def refresh(self):
        self.view.refresh()

    def set_birth_date(self, birth_date):
        self.birth_date = birth_date or ""
        self.auto_btn.setEnabled(bool(self.birth_date))

    # ------------------------------------------------------------------
    def _open_tooth(self, tooth_number):
        dlg = ToothDetailsDialog(self.patient_id, tooth_number, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()
            if self._on_changed:
                self._on_changed()

    def _auto_generate(self):
        if not self.birth_date:
            return
        import pages.teething_timeline as tl
        variation = 0
        try:
            variation, ok = QInputDialog.getInt(
                self, "هامش التفاوت",
                "مدة التفاوت الطبيعي بالشهور حول أعمار التسنين القياسية (0-24):",
                0, 0, 24, 1)
            if not ok:
                return
        except Exception:
            variation = 0
        try:
            generated = db.generate_age_based_tooth_chart(
                self.patient_id, self.birth_date, variation_months=variation)
        except Exception as exc:  # pragma: no cover - defensive
            show_error(self, "تعذّر التوليد", f"حدث خطأ:\n{exc}")
            return
        self.refresh()
        if generated:
            show_info(self, "تم التوليد",
                      "حُدّثت خريطة الأسنان حسب عمر المريض. الحالات اللي عدّلها الطبيب يدويًا بقيت زي ما هي.")
        else:
            show_info(self, "تعذّر التوليد", "تاريخ ميلاد غير صحيح أو خريطة فارغة.")