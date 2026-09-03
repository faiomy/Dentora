# -*- coding: utf-8 -*-
"""Reusable Qt UI components built on the design system.
This module provides a small library of styled widgets that can be used
throughout the Dentora Qt UI. All widgets pull their colors, spacing, and
font settings from ``ui.design``.
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
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt

from . import design

# ---------------------------------------------------------------------------
# Helper: base font
# ---------------------------------------------------------------------------

def _base_font(bold: bool = False, size: int = None) -> QFont:
    f = QFont(design.FONT_FAMILY)
    f.setPointSize(size or design.FONT_SIZE)
    f.setWeight(QFont.Bold if bold else QFont.Normal)
    return f

# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

class PrimaryButton(QPushButton):
    """Button with the primary (deep navy) styling."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(_base_font(bold=True))
        self.setStyleSheet(
            f"""
            QPushButton#PrimaryButton {{
                background-color: {design.PRIMARY_COLOR};
                color: #FFFFFF;
                border: none;
                border-radius: {design.BORDER_RADIUS}px;
                padding: {design.SPACING}px {design.SPACING * 2}px;
            }}
            QPushButton#PrimaryButton:hover {{
                background-color: {design.PRIMARY_HOVER};
            }}
            QPushButton#PrimaryButton:pressed {{
                background-color: {design.PRIMARY_PRESSED};
            }}
            """
        )


class SecondaryButton(QPushButton):
    """Button with the secondary (modern blue) styling."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("SecondaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(_base_font(bold=True))
        self.setStyleSheet(
            f"""
            QPushButton#SecondaryButton {{
                background-color: {design.SECONDARY_COLOR};
                color: #FFFFFF;
                border: none;
                border-radius: {design.BORDER_RADIUS}px;
                padding: {design.SPACING}px {design.SPACING * 2}px;
            }}
            QPushButton#SecondaryButton:hover {{
                background-color: {design.SECONDARY_HOVER};
            }}
            QPushButton#SecondaryButton:pressed {{
                background-color: {design.SECONDARY_PRESSED};
            }}
            """
        )


class DangerButton(QPushButton):
    """Button for destructive actions (red)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("DangerButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(_base_font(bold=True))
        self.setStyleSheet(
            f"""
            QPushButton#DangerButton {{
                background-color: {design.ERROR_COLOR};
                color: #FFFFFF;
                border: none;
                border-radius: {design.BORDER_RADIUS}px;
                padding: {design.SPACING}px {design.SPACING * 2}px;
            }}
            QPushButton#DangerButton:hover {{
                background-color: {design.adjust_color(design.ERROR_COLOR, 0.9)};
            }}
            QPushButton#DangerButton:pressed {{
                background-color: {design.adjust_color(design.ERROR_COLOR, 0.8)};
            }}
            """
        )

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

class TextInput(QLineEdit):
    """Standard text input field with consistent styling."""

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("TextInput")
        self.setPlaceholderText(placeholder)
        self.setFont(_base_font())
        self.setStyleSheet(
            f"""
            QLineEdit#TextInput {{
                background-color: {design.SURFACE_COLOR};
                border: 1px solid #cccccc;
                border-radius: {design.BORDER_RADIUS}px;
                padding: {design.SPACING}px;
                color: {design.TEXT_COLOR};
            }}
            QLineEdit#TextInput:focus {{
                border: 1px solid {design.PRIMARY_COLOR};
            }}
            """
        )


class ComboBox(QComboBox):
    """Styled combo box (dropdown)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ComboBox")
        self.setFont(_base_font())
        self.setStyleSheet(
            f"""
            QComboBox#ComboBox {{
                background-color: {design.SURFACE_COLOR};
                border: 1px solid #cccccc;
                border-radius: {design.BORDER_RADIUS}px;
                padding: {design.SPACING}px;
                color: {design.TEXT_COLOR};
            }}
            QComboBox#ComboBox:focus {{
                border: 1px solid {design.PRIMARY_COLOR};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            """
        )


class DateInput(QDateEdit):
    """Styled date picker using ``QDateEdit``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DateInput")
        self.setCalendarPopup(True)
        self.setFont(_base_font())
        self.setStyleSheet(
            f"""
            QDateEdit#DateInput {{
                background-color: {design.SURFACE_COLOR};
                border: 1px solid #cccccc;
                border-radius: {design.BORDER_RADIUS}px;
                padding: {design.SPACING}px;
                color: {design.TEXT_COLOR};
            }}
            QDateEdit#DateInput:focus {{
                border: 1px solid {design.PRIMARY_COLOR};
            }}
            """
        )

# ---------------------------------------------------------------------------
# Card / surface components
# ---------------------------------------------------------------------------

class Card(QFrame):
    """Base surface with optional drop‑shadow.
    Use for grouping related UI elements.
    """

    def __init__(self, parent=None, shadow: bool = True):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {design.SURFACE_COLOR};
                border: 1px solid #e0e0e0;
                border-radius: {design.BORDER_RADIUS}px;
            }}
            """
        )
        if shadow:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(12)
            effect.setOffset(0, 2)
            effect.setColor(QColor(0, 0, 0, 30))
            self.setGraphicsEffect(effect)


class StatCard(Card):
    """A small card showing a label and a numeric/value display.
    Example: "Today's appointments" – ``value_label`` can be set later.
    """

    def __init__(self, title: str, value: str = "---", parent=None):
        super().__init__(parent, shadow=False)
        self.setObjectName("StatCard")
        # Layout with two labels
        from PySide6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(design.SPACING, design.SPACING, design.SPACING, design.SPACING)
        layout.setSpacing(design.SPACING // 2)
        self.title_label = QLabel(title)
        self.title_label.setFont(_base_font(bold=True, size=design.FONT_SIZE))
        self.title_label.setStyleSheet(f"color: {design.TEXT_SECONDARY_COLOR};")
        self.value_label = QLabel(value)
        self.value_label.setFont(_base_font(bold=True, size=design.FONT_SIZE + 4))
        self.value_label.setStyleSheet(f"color: {design.TEXT_COLOR};")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)

# ---------------------------------------------------------------------------
# Table component
# ---------------------------------------------------------------------------

class DataTable(QTableView):
    """A ready‑to‑use table view with a clean flat style.
    Consumers should set a model (e.g., ``QStandardItemModel``) as needed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DataTable")
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setStyleSheet(
            f"""
            QTableView#DataTable {{
                background-color: {design.SURFACE_COLOR};
                alternate-background-color: #fafafa;
                selection-background-color: {design.PRIMARY_HOVER};
                gridline-color: #e0e0e0;
                border: none;
                font-size: {design.FONT_SIZE}pt;
            }}
            QHeaderView::section {{
                background-color: {design.BACKGROUND_COLOR};
                padding: {design.SPACING}px;
                border: none;
                font-weight: bold;
                font-size: {design.FONT_SIZE}pt;
            }}
            """
        )

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
