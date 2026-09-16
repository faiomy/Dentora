# -*- coding: utf-8 -*-
"""Shared UI constants for the Qt version of Dentora.

Single source of truth for values displayed by multiple pages (appointment
status labels, etc.) so per-page copies cannot drift apart again. Status
definitions mirror ``theme.APPOINTMENT_STATUSES`` (the same set the CustomTk
version uses).
"""

import theme

# Appointment status key -> {label, color}. Mirrors theme.APPOINTMENT_STATUSES.
STATUSES = theme.APPOINTMENT_STATUSES


def status_key_to_label(key):
    """Arabic display label for an appointment status key.

    Example: "confirmed" -> "مؤكد". Falls back to the raw key when unknown.
    """
    info = STATUSES.get(key)
    return info["label"] if info else str(key)


# U+2066 / U+2069: LEFT-TO-RIGHT ISOLATE ... POP DIRECTIONAL ISOLATE. Wrapping a
# string in these forces it to render in its natural LTR order even inside an
# RTL-paragraph (QApplication layout direction is RightToLeft), so phone numbers
# / IDs that start with "+" (or otherwise mix directions) do not get visually
# reversed ("+2010..." must NOT display as "...2010+").
def ltr(text) -> str:
    """Wrap ``text`` in Unicode LTR isolates so it renders left-to-right
    regardless of the surrounding RTL direction context."""
    return f"\u2066{text}\u2069"


__all__ = ["STATUSES", "status_key_to_label", "ltr"]