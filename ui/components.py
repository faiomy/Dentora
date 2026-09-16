# -*- coding: utf-8 -*-
"""Reusable Qt UI components built on the design system.

All widgets derive their look from the ONE global stylesheet (ui/stylesheet.py,
built from ui/design.py tokens) via objectName selectors - so every button,
field, table and card looks the same everywhere, with per-kind variants.
"""

from PySide6.QtWidgets import (
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QTimeEdit,
    QFrame,
    QLabel,
    QTableView,
    QHeaderView,
    QGraphicsDropShadowEffect,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QButtonGroup,
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, QTime

from . import design


# ---------------------------------------------------------------------------
# Helper: base font
# ---------------------------------------------------------------------------

def _base_font(bold: bool = False, size: int = None) -> QFont:
    f = QFont(design.FONT_FAMILY)
    f.setPointSize(size or design.FONT_SIZE_BASE)
    f.setWeight(QFont.DemiBold if bold else QFont.Normal)
    return f


# ---------------------------------------------------------------------------
# Buttons (variants of the global QPushButton styling)
# ---------------------------------------------------------------------------

class PrimaryButton(QPushButton):
    """Primary action button (accent coral) - save / add / confirm."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(_base_font(bold=True))


class SecondaryButton(QPushButton):
    """Secondary button (transparent + border outline) - cancel / navigate."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("SecondaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(_base_font())


class DangerButton(QPushButton):
    """Destructive action button (red)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("DangerButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(_base_font(bold=True))


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

class TextInput(QLineEdit):
    """Standard text input field (global QSS: radius, border, focus ring)."""

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("TextInput")
        self.setPlaceholderText(placeholder)
        self.setFont(_base_font())

    def set_error(self, on: bool):
        """Highlight the field red to signal a validation failure."""
        self._set_error(self, on)


class ComboBox(QComboBox):
    """Styled combo box (dropdown)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ComboBox")
        self.setFont(_base_font())

    def set_error(self, on: bool):
        self._set_error(self, on)


class DateInput(QDateEdit):
    """Styled date picker using ``QDateEdit``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DateInput")
        self.setCalendarPopup(True)
        self.setFont(_base_font())

    def set_error(self, on: bool):
        self._set_error(self, on)


class TimeInput(QTimeEdit):
    """Styled 24h time picker (consistent look with the other inputs)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimeInput")
        self.setDisplayFormat("HH:mm")
        self.setFont(_base_font())

    def set_error(self, on: bool):
        self._set_error(self, on)


def _set_error(widget, on: bool):
    """Toggle the ``error`` dynamic property and repolish so the global QSS
    ``[error="true"]`` rule takes effect immediately."""
    widget.setProperty("error", bool(on))
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# Patched in below so `widget.set_error(...)` works for the input types above
# without duplicating the helper.
TextInput._set_error = staticmethod(_set_error)
ComboBox._set_error = staticmethod(_set_error)
DateInput._set_error = staticmethod(_set_error)
TimeInput._set_error = staticmethod(_set_error)


class TimeSlotBar(QWidget):
    """A row of quick-pick time chips (``QPushButton#TimeChip``) that set the
    linked :class:`TimeInput` - a fast, clutter-free way to enter appointment
    hours while still allowing free entry through the time picker itself."""

    DEFAULT_SLOTS = ("09:00", "10:00", "11:00", "12:00", "14:00", "16:00")

    def __init__(self, time_edit: TimeInput, slots=DEFAULT_SLOTS, parent=None):
        super().__init__(parent)
        self.time_edit = time_edit
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(design.SPACING_XS)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for slot in slots:
            btn = QPushButton(slot)
            btn.setObjectName("TimeChip")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda checked, s=slot: self._apply(s, checked))
            self._group.addButton(btn)
            layout.addWidget(btn)
        layout.addStretch()

    def _apply(self, slot: str, checked: bool):
        if checked:
            t = QTime.fromString(slot, "HH:mm")
            if t.isValid():
                self.time_edit.setTime(t)

    def select_slot(self, slot: str):
        """Highlight the chip matching *slot* (used when editing an existing
        appointment)."""
        for b in self._group.buttons():
            b.setChecked(b.text() == slot)

    def clear(self):
        for b in self._group.buttons():
            b.setChecked(False)


class FieldLabel(QLabel):
    """Consistent bold field label (QSS ``QLabel#FieldLabel``). Append
    ``required=True`` to render the mandatory marker."""

    def __init__(self, text: str, required: bool = False, parent=None):
        super().__init__(text + ("  *" if required else ""), parent)
        self.setObjectName("FieldLabel")


# ---------------------------------------------------------------------------
# Card / surface components
# ---------------------------------------------------------------------------

class Card(QFrame):
    """THE unified card surface used as the base for any card-like grouping
    across all pages.

    background: SURFACE, border: 1px solid BORDER,
    border-radius: RADIUS_CARD, padding: SPACING_MD (via content margins).
    Pages should put their content inside a Card instead of building
    ad-hoc frames, which is what keeps the look consistent.
    """

    def __init__(self, parent=None, shadow: bool = True, padding: bool = True):
        super().__init__(parent)
        self.setObjectName("Card")
        if padding:
            self._layout = QVBoxLayout(self)
            self._layout.setContentsMargins(
                design.SPACING_MD, design.SPACING_MD,
                design.SPACING_MD, design.SPACING_MD)
            self._layout.setSpacing(design.SPACING_SM)
        else:
            self._layout = None
        if shadow:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(18)
            effect.setOffset(0, 3)
            effect.setColor(QColor(38, 33, 92, 26))  # PRIMARY_900-based soft shadow
            self.setGraphicsEffect(effect)

    def body(self):
        """The padded inner layout - add content here."""
        return self._layout


class StatCard(Card):
    """A small card showing a label and a numeric/value display.
    Example: "Today's appointments" - ``value_label`` can be set later."""

    def __init__(self, title: str, value: str = "---", value_color: str = None, parent=None):
        super().__init__(parent, shadow=False)
        self.setObjectName("StatCard")
        layout = self.body()
        layout.setSpacing(design.SPACING_XS)
        self.title_label = QLabel(title)
        self.title_label.setFont(_base_font(bold=True, size=design.FONT_SIZE_SM))
        self.title_label.setObjectName("StatTitle")
        self.value_label = QLabel(value)
        self.value_label.setFont(_base_font(bold=True, size=design.FONT_SIZE_H2))
        self.value_label.setObjectName("StatValue")
        # Explicit per-card colors (e.g. revenue in green) are intentional and
        # static; the default is driven by the theme via QSS#StatValue.
        if value_color:
            self.value_label.setStyleSheet(f"color: {value_color}; background: transparent;")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)

    def set_value_color(self, color: str):
        """Recolor the value label at runtime (e.g. profit turns green/red
        depending on sign). Kept as an inline rule because the color depends
        on data rather than the active theme."""
        self.value_label.setStyleSheet(f"color: {color}; background: transparent;")


# ---------------------------------------------------------------------------
# Table component
# ---------------------------------------------------------------------------

class DataTable(QTableView):
    """A ready-to-use table view styled by the global QSS:
    no internal gridlines, subtle PRIMARY_50 alternating rows, header on
    BACKGROUND with small TEXT_SECONDARY text, comfortable row height and
    centered content (Arabic tabular data reads better centered)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DataTable")
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(38)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.horizontalHeader().setMinimumSectionSize(64)

    def hide_columns(self, *indices):
        """Hide technical columns (kept in the model only for lookups)."""
        for i in indices:
            self.setColumnHidden(int(i), True)

    def format_column(self, column: int, alignment=None, stretch: bool = False):
        """Per-column presentation helper (alignment / stretch)."""
        header = self.horizontalHeader()
        if alignment is not None:
            header.setSectionResizeMode(column, QHeaderView.Interactive)
            for row in range(self.model().rowCount()):
                item = self.model().item(row, column)
                if item:
                    item.setTextAlignment(alignment)

    @staticmethod
    def center_column(model, column: int):
        """Center the cells of *column* (header alignment handled globally)."""
        for row in range(model.rowCount()):
            item = model.item(row, column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)


# ---------------------------------------------------------------------------
# Simple modal dialogs (information / confirmation)
# ---------------------------------------------------------------------------

def show_info(parent, title: str, message: str):
    """Convenient wrapper for an information message box."""
    QMessageBox.information(parent, title, message)


def show_error(parent, title: str, message: str):
    """Convenient wrapper for an error message box."""
    QMessageBox.critical(parent, title, message)


def ask_confirmation(parent, title: str, message: str) -> bool:
    """Show a Yes/No confirmation dialog and return ``True`` if Yes."""
    reply = QMessageBox.question(parent, title, message, QMessageBox.Yes | QMessageBox.No)
    return reply == QMessageBox.Yes


__all__ = [
    "PrimaryButton",
    "SecondaryButton",
    "DangerButton",
    "TextInput",
    "ComboBox",
    "DateInput",
    "TimeInput",
    "TimeSlotBar",
    "FieldLabel",
    "Card",
    "StatCard",
    "DataTable",
    "show_info",
    "show_error",
    "ask_confirmation",
]
