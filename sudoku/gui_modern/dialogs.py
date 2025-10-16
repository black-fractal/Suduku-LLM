"""Dialog components for the modern Sudoku GUI."""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .models import GameSettings


class SettingsDialog(QDialog):
    """Allows the player to adjust difficulty, fonts, and theme options."""

    def __init__(self, settings: GameSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._difficulty = QComboBox(self)
        self._difficulty.addItems(["easy", "medium", "hard"])
        self._difficulty.setCurrentText(settings.difficulty)
        self._font_size = QSpinBox(self)
        self._font_size.setRange(12, 24)
        self._font_size.setValue(settings.font_size)
        self._show_errors = QCheckBox("Live validation hints", self)
        self._show_errors.setChecked(settings.show_errors)
        self._theme = QComboBox(self)
        self._theme.addItems(["Aqua", "Midnight"])
        self._theme.setCurrentText(settings.theme)
        self._build_layout()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Difficulty:", self))
        layout.addWidget(self._difficulty)
        layout.addWidget(QLabel("Font size:", self))
        layout.addWidget(self._font_size)
        layout.addWidget(self._show_errors)
        layout.addWidget(QLabel("Theme:", self))
        layout.addWidget(self._theme)

        buttons = QHBoxLayout()
        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel", self)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def updated_settings(self) -> GameSettings:
        return GameSettings(
            difficulty=self._difficulty.currentText(),  # type: ignore[arg-type]
            font_size=int(self._font_size.value()),
            show_errors=self._show_errors.isChecked(),
            theme=self._theme.currentText(),
        )


__all__ = ["SettingsDialog"]
