# -*- coding: utf-8 -*-
"""Design system constants and helpers for the Qt UI.
Unified purple/coral design language for Dentora - one source of truth for
every color, font size and spacing metric used across all pages.

The global stylesheet in ``qt_main.py`` is generated from these values, and
the components in ``ui/components.py`` build on them as well.
"""

# ---------------------------------------------------------------------------
# Primary colors (deep purple - brand identity)
# ---------------------------------------------------------------------------
PRIMARY_900 = "#26215C"   # text on light backgrounds from the same family
PRIMARY_800 = "#3C3489"   # sidebar / active elements
PRIMARY_600 = "#534AB7"   # hover state / darker secondary elements
PRIMARY_400 = "#7F77DD"   # buttons and mid-tone elements
PRIMARY_100 = "#CECBF6"   # light backgrounds (badges, chips)
PRIMARY_50  = "#EEEDFE"   # lightest background (subtle hover)

# ---------------------------------------------------------------------------
# Accent color (warm coral - alerts / important states / primary buttons)
# ---------------------------------------------------------------------------
ACCENT_900 = "#4A1B0C"
ACCENT_600 = "#993C1D"
ACCENT_400 = "#D85A30"    # base color for primary buttons
ACCENT_100 = "#F5C4B3"
ACCENT_50  = "#FAECE7"

# ---------------------------------------------------------------------------
# Green/teal (success, completed payment, positive state)
# ---------------------------------------------------------------------------
SUCCESS_600 = "#0F6E56"
SUCCESS_400 = "#1D9E75"
SUCCESS_50  = "#E1F5EE"

# ---------------------------------------------------------------------------
# Red (error/warning)
# ---------------------------------------------------------------------------
ERROR_600 = "#A32D2D"
ERROR_400 = "#E24B4A"
ERROR_50  = "#FCEBEB"

# ---------------------------------------------------------------------------
# Amber (warning)
# ---------------------------------------------------------------------------
WARNING_400 = "#EF9F27"
WARNING_50  = "#FAEEDA"

# ---------------------------------------------------------------------------
# Neutrals
# ---------------------------------------------------------------------------
BACKGROUND = "#F7F7FB"      # page background (not pure white)
SURFACE    = "#FFFFFF"      # card background
BORDER     = "#E5E4F0"      # very light borders
TEXT_PRIMARY   = "#2C2B3A"
TEXT_SECONDARY = "#6B6980"
TEXT_MUTED     = "#9B99AC"

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
FONT_FAMILY = "Cairo"
FONT_SIZE_BASE = 10      # pt
FONT_SIZE_SM   = 9
FONT_SIZE_LG   = 12
FONT_SIZE_H1   = 18
FONT_SIZE_H2   = 14

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
RADIUS_CARD   = 16   # px - all cards
RADIUS_INPUT  = 10   # px - fields and buttons
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def adjust_color(hex_color: str, factor: float) -> str:
    """Return a lighter/darker version of *hex_color*.

    *factor* < 1 darkens the color, > 1 lightens it.
    The function works on 6-digit ``#RRGGBB`` strings.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"#{hex_color}"  # fallback - return unchanged
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


# Pre-computed hover/pressed colors for primary and secondary variants
# (computed from the new token values)
PRIMARY_HOVER = adjust_color(PRIMARY_400, 0.88)     # darker coral on hover
PRIMARY_PRESSED = adjust_color(PRIMARY_400, 0.78)   # even darker when pressed
SECONDARY_HOVER = adjust_color(PRIMARY_600, 0.88)   # purple hover
SECONDARY_PRESSED = adjust_color(PRIMARY_600, 0.78)

# Semantic aliases kept for convenience (used across pages)
PRIMARY_COLOR = PRIMARY_400
SECONDARY_COLOR = PRIMARY_600
BACKGROUND_COLOR = BACKGROUND
SURFACE_COLOR = SURFACE
TEXT_COLOR = TEXT_PRIMARY
TEXT_SECONDARY_COLOR = TEXT_SECONDARY
SUCCESS_COLOR = SUCCESS_600
ERROR_COLOR = ERROR_600
WARNING_COLOR = WARNING_400
BORDER_RADIUS = RADIUS_INPUT
SPACING = SPACING_SM
FONT_SIZE = FONT_SIZE_BASE

__all__ = [
    # Primary
    "PRIMARY_900", "PRIMARY_800", "PRIMARY_600", "PRIMARY_400",
    "PRIMARY_100", "PRIMARY_50",
    # Accent
    "ACCENT_900", "ACCENT_600", "ACCENT_400", "ACCENT_100", "ACCENT_50",
    # Success
    "SUCCESS_600", "SUCCESS_400", "SUCCESS_50",
    # Error
    "ERROR_600", "ERROR_400", "ERROR_50",
    # Warning
    "WARNING_400", "WARNING_50",
    # Neutrals
    "BACKGROUND", "SURFACE", "BORDER",
    "TEXT_PRIMARY", "TEXT_SECONDARY", "TEXT_MUTED",
    # Typography
    "FONT_FAMILY", "FONT_SIZE_BASE", "FONT_SIZE_SM", "FONT_SIZE_LG",
    "FONT_SIZE_H1", "FONT_SIZE_H2",
    # Metrics
    "RADIUS_CARD", "RADIUS_INPUT",
    "SPACING_XS", "SPACING_SM", "SPACING_MD", "SPACING_LG", "SPACING_XL",
    # Helpers / aliases
    "adjust_color",
    "PRIMARY_HOVER", "PRIMARY_PRESSED", "SECONDARY_HOVER", "SECONDARY_PRESSED",
    "PRIMARY_COLOR", "SECONDARY_COLOR", "BACKGROUND_COLOR", "SURFACE_COLOR",
    "TEXT_COLOR", "TEXT_SECONDARY_COLOR", "SUCCESS_COLOR", "ERROR_COLOR",
    "WARNING_COLOR", "BORDER_RADIUS", "SPACING", "FONT_SIZE",
]
