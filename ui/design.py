# -*- coding: utf-8 -*-
"""Design system constants and helpers for the Qt UI.
Provides a centralized palette, typography, spacing, and utility functions.
"""

# Primary palette (deep navy) and secondary (modern blue)
PRIMARY_COLOR = "#003366"      # Deep navy
SECONDARY_COLOR = "#0066CC"    # Modern blue

# Background / surface colors
BACKGROUND_COLOR = "#F5F5F5"   # Very light gray / off‑white
SURFACE_COLOR = "#FFFFFF"      # White

# Text colors
TEXT_COLOR = "#333333"          # Dark neutral gray
TEXT_SECONDARY_COLOR = "#777777"  # Muted gray

# Semantic colors
SUCCESS_COLOR = "#28A745"      # Green (success)
ERROR_COLOR = "#DC3545"        # Red (error)
WARNING_COLOR = "#FFC107"      # Amber / orange (warning)
INFO_COLOR = "#007BFF"         # Blue (information)

# Typography
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 12  # base font size in points
FONT_BOLD = "bold"

# Layout metrics
BORDER_RADIUS = 8  # px
SPACING = 8        # base spacing in px

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def adjust_color(hex_color: str, factor: float) -> str:
    """Return a lighter/darker version of *hex_color*.

    *factor* < 1 darkens the color, > 1 lightens it.
    The function works on 6‑digit ``#RRGGBB`` strings.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"#{hex_color}"  # fallback – return unchanged
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"

# Pre‑computed hover/pressed colors for primary and secondary variants
PRIMARY_HOVER = adjust_color(PRIMARY_COLOR, 0.90)
PRIMARY_PRESSED = adjust_color(PRIMARY_COLOR, 0.80)
SECONDARY_HOVER = adjust_color(SECONDARY_COLOR, 0.90)
SECONDARY_PRESSED = adjust_color(SECONDARY_COLOR, 0.80)

__all__ = [
    "PRIMARY_COLOR",
    "SECONDARY_COLOR",
    "BACKGROUND_COLOR",
    "SURFACE_COLOR",
    "TEXT_COLOR",
    "TEXT_SECONDARY_COLOR",
    "SUCCESS_COLOR",
    "ERROR_COLOR",
    "WARNING_COLOR",
    "INFO_COLOR",
    "FONT_FAMILY",
    "FONT_SIZE",
    "FONT_BOLD",
    "BORDER_RADIUS",
    "SPACING",
    "adjust_color",
    "PRIMARY_HOVER",
    "PRIMARY_PRESSED",
    "SECONDARY_HOVER",
    "SECONDARY_PRESSED",
]
