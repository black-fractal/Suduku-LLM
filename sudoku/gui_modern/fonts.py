"""Font utilities for the modern Sudoku GUI."""
from __future__ import annotations

from typing import Optional

from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication

PRIMARY_FONT = "SF Pro Display"
FONT_FALLBACKS = ("SF Pro Text", "Helvetica Neue", "San Francisco", "Avenir Next", "Arial")

_RESOLVED_FONT: Optional[str] = None


def resolve_font_family() -> str:
    """Return the best matching font family available on the system."""
    global _RESOLVED_FONT
    if _RESOLVED_FONT:
        return _RESOLVED_FONT
    if QApplication.instance() is None:
        return PRIMARY_FONT
    families = set(QFontDatabase().families())
    for candidate in (PRIMARY_FONT, *FONT_FALLBACKS):
        if candidate in families:
            _RESOLVED_FONT = candidate
            break
    else:
        _RESOLVED_FONT = QFont().defaultFamily()
    return _RESOLVED_FONT


def font_css_family() -> str:
    """Return a CSS-safe font family string."""
    return resolve_font_family().replace('"', '\\"')


def create_font(point_size: int) -> QFont:
    """Create an antialiased QFont using the resolved family."""
    family = resolve_font_family() if QApplication.instance() else PRIMARY_FONT
    font = QFont(family, point_size)
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


def format_duration(seconds: float) -> str:
    """Format elapsed seconds as mm:ss or h:mm:ss when appropriate."""
    total_seconds = max(int(seconds), 0)
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


__all__ = [
    "PRIMARY_FONT",
    "FONT_FALLBACKS",
    "resolve_font_family",
    "font_css_family",
    "create_font",
    "format_duration",
]
