"""Virtual keypad for the modern Sudoku GUI."""
from __future__ import annotations

from typing import Dict, Set

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QPushButton,
    QGraphicsDropShadowEffect,
)

from .fonts import font_css_family
from .themes import THEMES

GRID_SIZE = 9
SECTION_SIZE = 3


class VirtualKeyboard(QFrame):
    """On-screen numeric keyboard that enables only valid candidates."""

    numberSelected = pyqtSignal(int)
    clearRequested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("VirtualKeyboard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._theme = THEMES["Aqua"]
        self._buttons: Dict[int, QPushButton] = {}

        layout = QGridLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        for index, number in enumerate(range(1, GRID_SIZE + 1)):
            button = QPushButton(str(number), self)
            button.setCursor(Qt.PointingHandCursor)
            button.setCheckable(True)
            button.clicked.connect(lambda _, n=number: self.numberSelected.emit(n))
            row = index // SECTION_SIZE
            col = index % SECTION_SIZE
            layout.addWidget(button, row, col)
            self._buttons[number] = button

        self._clear_button = QPushButton("Clear", self)
        self._clear_button.setCursor(Qt.PointingHandCursor)
        self._clear_button.clicked.connect(self.clearRequested.emit)
        layout.addWidget(self._clear_button, 3, 0, 1, SECTION_SIZE)

        self.setLayout(layout)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setOffset(0, 10)
        self._shadow.setBlurRadius(24)
        self.setGraphicsEffect(self._shadow)
        self.apply_theme(self._theme)
        self.update_options(set(), active=False, current=0)

    def apply_theme(self, theme: dict) -> None:
        self._theme = theme
        font_css = font_css_family()
        self.setStyleSheet(
            f"""
            QFrame#VirtualKeyboard {{
                background-color: {theme['keyboard_bg']};
                border-radius: 24px;
                border: 1.4px solid {theme['keyboard_border']};
            }}
            """
        )
        self._shadow.setColor(theme["keyboard_shadow"])

        button_style = f"""
            QPushButton {{
                background-color: {theme['keyboard_button_bg']};
                color: {theme['keyboard_button_text']};
                border-radius: 18px;
                border: none;
                font-family: "{font_css}";
                font-size: 15px;
                font-weight: 600;
                padding: 10px 0;
            }}
            QPushButton:hover:!disabled {{
                background-color: {theme['keyboard_button_hover']};
            }}
            QPushButton:checked {{
                background-color: {theme['keyboard_button_checked']};
                color: {theme['keyboard_button_text']};
            }}
            QPushButton:disabled {{
                background-color: {theme['keyboard_button_disabled']};
                color: {theme['text_secondary']};
            }}
        """
        for button in self._buttons.values():
            button.setStyleSheet(button_style)

        self._clear_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme['keyboard_clear_bg']};
                color: {theme['keyboard_clear_text']};
                border-radius: 18px;
                border: none;
                font-family: "{font_css}";
                font-size: 14px;
                font-weight: 600;
                padding: 8px 0;
            }}
            QPushButton:hover:!disabled {{
                background-color: {theme['keyboard_clear_hover']};
            }}
            QPushButton:disabled {{
                background-color: {theme['keyboard_button_disabled']};
                color: {theme['text_secondary']};
            }}
            """
        )

    def update_options(self, allowed: Set[int], *, active: bool, current: int) -> None:
        for number, button in self._buttons.items():
            button.setEnabled(active and number in allowed)
            button.setChecked(active and number == current)
        self._clear_button.setEnabled(active and current != 0)


__all__ = ["VirtualKeyboard"]
