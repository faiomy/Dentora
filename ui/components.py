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
    QFrame,
    QLabel,
    QTableView,
    QHeaderView,
    QGraphicsDropShadowEffect,
    QMessageBox,
    QVBoxLayout,
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt

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


class ComboBox(QComboBox):
    """Styled combo box (dropdown)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ComboBox")
        self.setFont(_base_font())


class DateInput(QDateEdit):
    """Styled date picker using ``QDateEdit``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DateInput")
        self.setCalendarPopup(True)
        self.setFont(_base_font())


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

    def __init__(self, title: str, value: str = "---", parent=None):
        super().__init__(parent, shadow=False)
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            design.SPACING_MD, design.SPACING_MD,
            design.SPACING_MD, design.SPACING_MD)
        layout.setSpacing(design.SPACING_XS)
        self.title_label = QLabel(title)
        self.title_label.setFont(_base_font(bold=True, size=design.FONT_SIZE_SM))
        self.title_label.setStyleSheet(
            f"color: {design.TEXT_SECONDARY}; background: transparent;")
        self.value_label = QLabel(value)
        self.value_label.setFont(_base_font(bold=True, size=design.FONT_SIZE_H2))
        self.value_label.setStyleSheet(
            f"color: {design.PRIMARY_900}; background: transparent;")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


# ---------------------------------------------------------------------------
# Table component
# ---------------------------------------------------------------------------

class DataTable(QTableView):
    """A ready-to-use table view styled by the global QSS:
    no internal gridlines, subtle PRIMARY_50 alternating rows, header on
    BACKGROUND with small TEXT_SECONDARY text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DataTable")
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionsClickable(True)


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
    "Card",
    "StatCard",
    "DataTable",
    "show_info",
    "show_error",
    "ask_confirmation",
]
