# -*- coding: utf-8 -*-
"""Design system constants and helpers for the Qt UI.
Unified design language for Dentora - one source of truth for every color,
font size and spacing metric used across all pages.

The global stylesheet in ``qt_main.py`` is generated from these values, and
the components in ``ui/components.py`` build on them as well.

Theming: the module defaults are a sane light palette, but the whole palette
becomes *theme aware* at runtime via :func:`apply_theme`, which loads an
existing theme preset from ``theme.THEME_PRESETS`` (plus an optional dark-mode
flag and an optional custom brand color) and rewrites every token in place.
Everything that renders from these tokens (the single global stylesheet, and
any inline style resolved at build time) therefore reflects the active theme.
"""

# ---------------------------------------------------------------------------
# Brand families (recomputed by apply_theme from the active preset/custom brand)
# ---------------------------------------------------------------------------
PRIMARY_900 = "#26215C"   # text on light backgrounds from the same family
PRIMARY_800 = "#3C3489"   # sidebar / active elements
PRIMARY_600 = "#534AB7"   # hover state / darker secondary elements
PRIMARY_400 = "#7F77DD"   # buttons and mid-tone elements
PRIMARY_100 = "#CECBF6"   # light backgrounds (badges, chips)
PRIMARY_50  = "#EEEDFE"   # lightest background (subtle hover)

# ---------------------------------------------------------------------------
# Accent color (primary actions / emphasis). Follows the brand color.
# ---------------------------------------------------------------------------
ACCENT_900 = "#4A1B0C"
ACCENT_600 = "#993C1D"
ACCENT_400 = "#D85A30"    # base color for primary buttons
ACCENT_100 = "#F5C4B3"
ACCENT_50  = "#FAECE7"

# ---------------------------------------------------------------------------
# Green/teal (success, completed payment, positive state) - fixed semantics
# ---------------------------------------------------------------------------
SUCCESS_600 = "#0F6E56"
SUCCESS_400 = "#1D9E75"
SUCCESS_50  = "#E1F5EE"

# ---------------------------------------------------------------------------
# Red (error/warning) - fixed semantics
# ---------------------------------------------------------------------------
ERROR_600 = "#A32D2D"
ERROR_400 = "#E24B4A"
ERROR_50  = "#FCEBEB"

# ---------------------------------------------------------------------------
# Amber (warning) - fixed semantics
# ---------------------------------------------------------------------------
WARNING_400 = "#EF9F27"
WARNING_50  = "#FAEEDA"

# ---------------------------------------------------------------------------
# Neutrals (recomputed by apply_theme)
# ---------------------------------------------------------------------------
BACKGROUND = "#F7F7FB"      # page background (not pure white)
SURFACE    = "#FFFFFF"      # card background
BORDER     = "#E5E4F0"      # very light borders
TEXT_PRIMARY   = "#2C2B3A"
TEXT_SECONDARY = "#6B6980"
TEXT_MUTED     = "#9B99AC"

# ---------------------------------------------------------------------------
# Typography (static - fonts loaded at startup)
# ---------------------------------------------------------------------------
FONT_FAMILY = "Cairo"
FONT_SIZE_BASE = 10      # pt
FONT_SIZE_SM   = 9
FONT_SIZE_LG   = 12
FONT_SIZE_H1   = 18
FONT_SIZE_H2   = 14

# ---------------------------------------------------------------------------
# Metrics (static)
# ---------------------------------------------------------------------------
RADIUS_CARD   = 16   # px - all cards
RADIUS_INPUT  = 10   # px - fields and buttons
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32

# Current theme state (useful for tooling/debugging)
CURRENT_THEME_ID = None
CURRENT_DARK = False


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


def mix(color: str, target: str, t: float) -> str:
    """Linearly interpolate between two ``#RRGGBB`` colors.

    ``t`` in ``0..1``: ``0`` returns *color*, ``1`` returns *target*.
    Used to derive tints (toward white) and shades (toward black) that stay
    within the same hue family.
    """
    c = color.lstrip("#")
    tar = target.lstrip("#")
    if len(c) != 6 or len(tar) != 6:
        return color
    try:
        r = int(c[0:2], 16) + int((int(tar[0:2], 16) - int(c[0:2], 16)) * t)
        g = int(c[2:4], 16) + int((int(tar[2:4], 16) - int(c[2:4], 16)) * t)
        b = int(c[4:6], 16) + int((int(tar[4:6], 16) - int(c[4:6], 16)) * t)
    except ValueError:
        return color
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# Initial-derived hover/pressed colors (recomputed by apply_theme).
# ``factor``-based darkening approximates a mix toward black.
PRIMARY_HOVER = adjust_color(PRIMARY_400, 0.88)     # darker coral on hover
PRIMARY_PRESSED = adjust_color(PRIMARY_400, 0.78)   # even darker when pressed
SECONDARY_HOVER = adjust_color(PRIMARY_600, 0.88)   # purple hover
SECONDARY_PRESSED = adjust_color(PRIMARY_600, 0.78)

# Semantic aliases kept for convenience (used across pages). These are also
# recomputed by apply_theme.
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


def apply_theme(theme_id=None, dark=False, primary=None, secondary=None):
    """Rewrite the module palette from the referenced theme preset.

    Parameters
    ----------
    theme_id: optional str
        Key into ``theme.THEME_PRESETS``. Falls back to the module default
        light palette if unknown/None.
    dark: bool
        Use dark neutral surfaces derived from the preset's ``bg_main`` /
        ``card_bg`` (the dedicated ``dark_*`` presets already carry dark
        surface values) and adjust the light tints so chips/badges stay
        subtle on dark backgrounds.
    primary / secondary: optional str
        Explicit brand colors (e.g. a custom brand color saved in
        ``clinic_settings``) that override the preset's primary/secondary.
    """
    import theme as _theme

    global PRIMARY_900, PRIMARY_800, PRIMARY_600, PRIMARY_400, PRIMARY_100, PRIMARY_50
    global ACCENT_900, ACCENT_600, ACCENT_400, ACCENT_100, ACCENT_50
    global SUCCESS_50, ERROR_50, WARNING_50
    global BACKGROUND, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED
    global PRIMARY_HOVER, PRIMARY_PRESSED, SECONDARY_HOVER, SECONDARY_PRESSED
    global PRIMARY_COLOR, SECONDARY_COLOR, BACKGROUND_COLOR, SURFACE_COLOR
    global TEXT_COLOR, TEXT_SECONDARY_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR
    global CURRENT_THEME_ID, CURRENT_DARK

    final_theme_id = theme_id
    if final_theme_id not in _theme.THEME_PRESETS:
        final_theme_id = _theme.DEFAULT_THEME_ID
    preset = _theme.THEME_PRESETS.get(final_theme_id, {})

    brand_primary = primary or preset.get("primary") or PRIMARY_400
    brand_secondary = secondary or preset.get("secondary") or PRIMARY_600

    # Neutral surfaces come from the preset (dark presets carry dark values).
    BACKGROUND = preset.get("bg_main", "#F7F7FB")
    SURFACE = preset.get("card_bg", "#FFFFFF")
    BORDER = preset.get("border", "#E5E4F0")
    TEXT_PRIMARY = preset.get("text_dark", "#2C2B3A")
    TEXT_SECONDARY = preset.get("text_muted", "#6B6980")
    TEXT_MUTED = mix(TEXT_SECONDARY, SURFACE, 0.30)

    # Brand family derived from the chosen primary.
    PRIMARY_400 = brand_primary
    PRIMARY_600 = mix(brand_primary, "#000000", 0.28)
    PRIMARY_800 = mix(brand_primary, "#000000", 0.50)
    PRIMARY_900 = mix(brand_primary, "#000000", 0.62)
    ACCENT_400 = brand_primary
    ACCENT_600 = mix(brand_primary, "#000000", 0.30)
    ACCENT_900 = mix(brand_primary, "#000000", 0.58)

    if dark:
        tint_base = SURFACE
        PRIMARY_100 = mix(brand_primary, tint_base, 0.52)
        PRIMARY_50 = mix(brand_primary, tint_base, 0.70)
        ACCENT_100 = mix(brand_primary, tint_base, 0.48)
        ACCENT_50 = mix(brand_primary, tint_base, 0.72)
        SUCCESS_50 = mix(SUCCESS_600, tint_base, 0.72)
        ERROR_50 = mix(ERROR_600, tint_base, 0.72)
        WARNING_50 = mix(WARNING_400, tint_base, 0.72)
        # In dark mode, page titles should read light rather than near-black.
        if TEXT_PRIMARY and TEXT_PRIMARY.startswith("#"):
            _lum = (int(TEXT_PRIMARY[1:3], 16) + int(TEXT_PRIMARY[3:5], 16) + int(TEXT_PRIMARY[5:7], 16)) / 3
            if _lum < 140:  # very dark text on a dark bg -> swap to light text
                TEXT_PRIMARY = "#E8EAED"
    else:
        PRIMARY_100 = mix(brand_primary, "#FFFFFF", 0.72)
        PRIMARY_50 = mix(brand_primary, "#FFFFFF", 0.86)
        ACCENT_100 = mix(brand_primary, "#FFFFFF", 0.66)
        ACCENT_50 = mix(brand_primary, "#FFFFFF", 0.85)
        SUCCESS_50 = mix(SUCCESS_600, "#FFFFFF", 0.78)
        ERROR_50 = mix(ERROR_600, "#FFFFFF", 0.78)
        WARNING_50 = mix(WARNING_400, "#FFFFFF", 0.75)

    PRIMARY_HOVER = mix(PRIMARY_400, "#000000", 0.12)
    PRIMARY_PRESSED = mix(PRIMARY_400, "#000000", 0.22)
    SECONDARY_HOVER = mix(PRIMARY_600, "#000000", 0.12)
    SECONDARY_PRESSED = mix(PRIMARY_600, "#000000", 0.22)

    # Refresh semantic aliases so old call sites keep working.
    PRIMARY_COLOR = PRIMARY_400
    SECONDARY_COLOR = PRIMARY_600
    BACKGROUND_COLOR = BACKGROUND
    SURFACE_COLOR = SURFACE
    TEXT_COLOR = TEXT_PRIMARY
    TEXT_SECONDARY_COLOR = TEXT_SECONDARY
    SUCCESS_COLOR = SUCCESS_600
    ERROR_COLOR = ERROR_600
    WARNING_COLOR = WARNING_400

    CURRENT_THEME_ID = final_theme_id
    CURRENT_DARK = bool(dark)


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
    "adjust_color", "mix", "apply_theme",
    "PRIMARY_HOVER", "PRIMARY_PRESSED", "SECONDARY_HOVER", "SECONDARY_PRESSED",
    "PRIMARY_COLOR", "SECONDARY_COLOR", "BACKGROUND_COLOR", "SURFACE_COLOR",
    "TEXT_COLOR", "TEXT_SECONDARY_COLOR", "SUCCESS_COLOR", "ERROR_COLOR",
    "WARNING_COLOR", "BORDER_RADIUS", "SPACING", "FONT_SIZE",
    "CURRENT_THEME_ID", "CURRENT_DARK",
]