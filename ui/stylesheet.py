# -*- coding: utf-8 -*-
"""Global application stylesheet for the Qt UI.

Builds ONE QSS string from ``ui/design.py`` tokens, applied once at the
QApplication level (see qt_main.py). Every button, field, table, tab, list,
checkbox, scrollbar and the sidebar are covered here - no widget falls back
to the OS-native look.
"""

from . import design


def build_global_stylesheet() -> str:
    d = design
    qss = f"""
/* ============ base ============ */
QWidget {{
    background-color: {d.BACKGROUND};
    color: {d.TEXT_PRIMARY};
    font-family: "{d.FONT_FAMILY}";
    font-size: {d.FONT_SIZE_BASE}pt;
}}
QMainWindow, QDialog {{ background-color: {d.BACKGROUND}; }}
QToolTip {{
    background-color: {d.PRIMARY_900};
    color: #FFFFFF;
    border: none;
    padding: 6px 10px;
    border-radius: {d.RADIUS_INPUT}px;
    font-family: "{d.FONT_FAMILY}";
}}

QLabel {{ background: transparent; color: {d.TEXT_PRIMARY}; }}
QLabel#PageTitle {{
    font-size: {d.FONT_SIZE_H1}pt;
    font-weight: 600;
    color: {d.PRIMARY_900};
    background: transparent;
}}
QLabel#PageSubtitle {{
    font-size: {d.FONT_SIZE_BASE}pt;
    color: {d.TEXT_SECONDARY};
    background: transparent;
}}
QLabel#SectionTitle {{
    font-size: {d.FONT_SIZE_H2}pt;
    font-weight: 600;
    color: {d.PRIMARY_900};
    background: transparent;
}}

/* ============ cards ============ */
QFrame#Card, QFrame#StatCard {{
    background-color: {d.SURFACE};
    border: 1px solid {d.BORDER};
    border-radius: {d.RADIUS_CARD}px;
}}

/* ============ buttons (defaults + named kinds) ============ */
QPushButton {{
    background-color: {d.PRIMARY_600};
    color: #FFFFFF;
    border: none;
    border-radius: {d.RADIUS_INPUT}px;
    padding: {d.SPACING_SM + 2}px {d.SPACING_MD}px;
    font-family: "{d.FONT_FAMILY}";
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {d.SECONDARY_HOVER}; }}
QPushButton:pressed {{ background-color: {d.SECONDARY_PRESSED}; }}
QPushButton:focus {{ outline: none; border: 1px solid {d.PRIMARY_400}; }}
QPushButton:disabled {{ background-color: {d.PRIMARY_100}; color: {d.TEXT_MUTED}; }}

QPushButton#PrimaryButton, QPushButton:default {{
    background-color: {d.ACCENT_400};
    color: #FFFFFF;
}}
QPushButton#PrimaryButton:hover, QPushButton:default:hover {{
    background-color: {d.adjust_color(d.ACCENT_400, 0.88)};
}}
QPushButton#PrimaryButton:pressed, QPushButton:default:pressed {{
    background-color: {d.adjust_color(d.ACCENT_400, 0.78)};
}}
QPushButton#PrimaryButton:disabled {{ background-color: {d.ACCENT_100}; color: {d.ACCENT_600}; }}

QPushButton#SecondaryButton {{
    background-color: transparent;
    color: {d.TEXT_SECONDARY};
    border: 1px solid {d.BORDER};
}}
QPushButton#SecondaryButton:hover {{
    background-color: {d.PRIMARY_50};
    color: {d.PRIMARY_600};
    border: 1px solid {d.PRIMARY_100};
}}
QPushButton#SecondaryButton:pressed {{ background-color: {d.PRIMARY_100}; }}
QPushButton#SecondaryButton:disabled {{ color: {d.TEXT_MUTED}; border: 1px solid {d.BORDER}; background: transparent; }}

QPushButton#DangerButton {{
    background-color: {d.ERROR_400};
    color: #FFFFFF;
}}
QPushButton#DangerButton:hover {{ background-color: {d.adjust_color(d.ERROR_400, 0.88)}; }}
QPushButton#DangerButton:pressed {{ background-color: {d.ERROR_600}; }}

/* ============ inputs ============ */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
QTimeEdit, QDateEdit, QComboBox {{
    background-color: {d.SURFACE};
    border: 1px solid {d.BORDER};
    border-radius: {d.RADIUS_INPUT}px;
    padding: {d.SPACING_SM + 1}px {d.SPACING_SM + 2}px;
    color: {d.TEXT_PRIMARY};
    selection-background-color: {d.PRIMARY_100};
    selection-color: {d.TEXT_PRIMARY};
    font-family: "{d.FONT_FAMILY}";
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover,
QDoubleSpinBox:hover, QTimeEdit:hover, QDateEdit:hover, QComboBox:hover {{
    border: 1px solid {d.PRIMARY_100};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QTimeEdit:focus, QDateEdit:focus, QComboBox:focus {{
    border: 1px solid {d.PRIMARY_400};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {d.BACKGROUND};
    color: {d.TEXT_MUTED};
    border: 1px solid {d.BORDER};
}}
QLineEdit[echoMode="2"] {{ font-weight: 600; letter-spacing: 2px; }}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    width: 0px; height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {d.TEXT_SECONDARY};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {d.SURFACE};
    border: 1px solid {d.BORDER};
    border-radius: {d.RADIUS_INPUT}px;
    selection-background-color: {d.PRIMARY_100};
    selection-color: {d.TEXT_PRIMARY};
    outline: none;
    padding: 4px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 16px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {d.TEXT_SECONDARY};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {d.TEXT_SECONDARY};
}}

/* ============ tables ============ */
QTableWidget, QTableView {{
    background-color: {d.SURFACE};
    alternate-background-color: {d.PRIMARY_50};
    gridline-color: transparent;
    border: 1px solid {d.BORDER};
    border-radius: {d.RADIUS_INPUT}px;
    selection-background-color: {d.PRIMARY_100};
    selection-color: {d.TEXT_PRIMARY};
    outline: none;
    font-family: "{d.FONT_FAMILY}";
    font-size: {d.FONT_SIZE_BASE}pt;
}}
QTableWidget::item, QTableView::item {{ padding: 6px; border: none; }}
QTableWidget::item:selected, QTableView::item:selected {{ background-color: {d.PRIMARY_100}; }}
QHeaderView::section {{
    background-color: {d.BACKGROUND};
    color: {d.TEXT_SECONDARY};
    padding: {d.SPACING_SM + 2}px {d.SPACING_SM}px;
    border: none;
    border-bottom: 1px solid {d.BORDER};
    font-family: "{d.FONT_FAMILY}";
    font-size: {d.FONT_SIZE_SM}pt;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background-color: {d.BACKGROUND};
    border: none;
}}

/* ============ lists ============ */
QListWidget {{
    background-color: {d.SURFACE};
    border: 1px solid {d.BORDER};
    border-radius: {d.RADIUS_INPUT}px;
    padding: {d.SPACING_XS}px;
    outline: none;
    font-size: {d.FONT_SIZE_BASE}pt;
}}
QListWidget::item {{
    padding: {d.SPACING_SM}px {d.SPACING_SM + 2}px;
    border-radius: {d.RADIUS_INPUT - 4}px;
    color: {d.TEXT_PRIMARY};
}}
QListWidget::item:hover {{ background-color: {d.PRIMARY_50}; }}
QListWidget::item:selected {{ background-color: {d.PRIMARY_600}; color: #FFFFFF; }}

/* ============ tabs ============ */
QTabWidget::pane {{
    border: 1px solid {d.BORDER};
    border-radius: {d.RADIUS_CARD}px;
    background-color: {d.SURFACE};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {d.TEXT_SECONDARY};
    padding: {d.SPACING_SM + 2}px {d.SPACING_MD}px;
    border: none;
    font-family: "{d.FONT_FAMILY}";
    font-size: {d.FONT_SIZE_BASE}pt;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {d.PRIMARY_600};
    border-bottom: 3px solid {d.ACCENT_400};
}}
QTabBar::tab:hover:!selected {{ color: {d.PRIMARY_400}; }}

/* ============ checkboxes ============ */
QCheckBox {{
    background: transparent;
    color: {d.TEXT_PRIMARY};
    spacing: {d.SPACING_XS + 2}px;
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border: 1px solid {d.BORDER};
    border-radius: 5px;
    background-color: {d.SURFACE};
}}
QCheckBox::indicator:hover {{ border: 1px solid {d.PRIMARY_400}; }}
QCheckBox::indicator:checked {{
    background-color: {d.PRIMARY_400};
    border: 1px solid {d.PRIMARY_400};
}}

/* ============ scrollbars ============ */
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {d.BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {d.TEXT_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 9px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {d.BORDER};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {d.TEXT_MUTED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ============ menus / message boxes ============ */
QMenu {{
    background-color: {d.SURFACE};
    border: 1px solid {d.BORDER};
    border-radius: {d.RADIUS_INPUT}px;
    padding: {d.SPACING_XS}px;
}}
QMenu::item {{
    padding: {d.SPACING_SM}px {d.SPACING_LG}px;
    border-radius: {d.RADIUS_INPUT - 5}px;
}}
QMenu::item:selected {{ background-color: {d.PRIMARY_50}; color: {d.PRIMARY_600}; }}
QMessageBox {{ background-color: {d.SURFACE}; }}
QMessageBox QPushButton {{ min-width: 84px; }}

/* ============ sidebar ============ */
QWidget#sidebar {{
    background-color: {d.PRIMARY_800};
}}
QWidget#sidebar QLabel {{
    color: #FFFFFF;
    background: transparent;
}}
QWidget#sidebar QLabel#sidebarLogo {{
    font-size: {d.FONT_SIZE_H1 + 2}pt;
    font-weight: 600;
    padding: {d.SPACING_LG}px {d.SPACING_MD}px {d.SPACING_MD}px;
}}
QWidget#sidebar QLabel#sidebarUser {{
    color: {d.PRIMARY_100};
    font-size: {d.FONT_SIZE_SM + 1}pt;
    padding: {d.SPACING_SM}px;
    background: transparent;
}}
QWidget#sidebar QPushButton#NavButton {{
    background-color: transparent;
    color: {d.PRIMARY_100};
    border: none;
    border-radius: 0px;
    text-align: right;
    padding: 0px {d.SPACING_MD + 4}px;
    font-weight: 600;
    font-size: {d.FONT_SIZE_BASE + 1}pt;
}}
QWidget#sidebar QPushButton#NavButton:hover {{
    background-color: {d.PRIMARY_600};
    color: #FFFFFF;
}}
QWidget#sidebar QPushButton#NavButton:checked {{
    background-color: {d.PRIMARY_600};
    color: #FFFFFF;
    border-right: 3px solid {d.ACCENT_400};
    padding-right: {d.SPACING_MD + 1}px;
}}
QWidget#sidebar QPushButton#LogoutButton {{
    background-color: transparent;
    color: {d.ACCENT_100};
    border: 1px solid {d.ACCENT_600};
    border-radius: {d.RADIUS_INPUT}px;
    margin: {d.SPACING_MD}px;
    padding: {d.SPACING_SM + 2}px;
    font-weight: 600;
}}
QWidget#sidebar QPushButton#LogoutButton:hover {{
    background-color: {d.ACCENT_600};
    color: #FFFFFF;
    border: 1px solid {d.ACCENT_600};
}}

/* ============ settings category list ============ */
QListWidget#SettingsCategories {{
    background-color: {d.SURFACE};
    border: 1px solid {d.BORDER};
    border-radius: {d.RADIUS_CARD}px;
    padding: {d.SPACING_SM}px;
}}
QListWidget#SettingsCategories::item {{
    padding: {d.SPACING_SM + 2}px {d.SPACING_MD}px;
    margin: 2px 0px;
    border-radius: {d.RADIUS_INPUT - 3}px;
}}
QListWidget#SettingsCategories::item:selected {{
    background-color: {d.PRIMARY_600};
    color: #FFFFFF;
}}
"""
    return qss
