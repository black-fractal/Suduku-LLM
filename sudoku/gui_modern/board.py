"""Board widgets for the modern Sudoku GUI."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, List, Optional, Sequence, Set, Tuple

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QIntValidator
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)

from sudoku.core import Board, is_valid

from .fonts import create_font, font_css_family
from .themes import THEMES

GRID_SIZE = 9
SECTION_SIZE = 3


class SubgridWidget(QFrame):
    """Rounded island container for a 3x3 Sudoku subsection."""

    def __init__(self, index: int, parent=None) -> None:
        super().__init__(parent)
        self._index = index
        self._color = QColor("#ffffff")
        self._theme = THEMES["Aqua"]
        self._layout = QGridLayout()
        self._layout.setSpacing(4)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self.setLayout(self._layout)
        self.setObjectName(f"Subgrid_{index}")
        self.setAttribute(Qt.WA_StyledBackground, True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setOffset(0, 8)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(shadow)

    def grid_layout(self) -> QGridLayout:
        return self._layout

    def set_theme(self, theme: dict, color: QColor) -> None:
        self._theme = theme
        self._color = color
        base = QColor(color)
        base = base.lighter(112) if not theme["is_dark"] else base.darker(110)
        self.setStyleSheet(
            f"""
            QFrame#{self.objectName()} {{
                background-color: {base.name()};
                border-radius: 20px;
                border: 1.4px solid {theme['subgrid_border']};
            }}
            """
        )
        effect = self.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setColor(theme["subgrid_shadow"])


class SudokuCell(QLineEdit):
    """Stylised cell widget that enforces board constraints."""

    focused = pyqtSignal(int, int)
    valueCommitted = pyqtSignal(int)

    def __init__(self, board: "SudokuBoard", row: int, col: int, parent=None) -> None:
        super().__init__(parent)
        self._board = board
        self.row = row
        self.col = col
        self._locked = False
        self._section_color = QColor("#ffffff")
        self._theme = THEMES["Aqua"]
        self._highlight_role: Optional[str] = None
        self._subgrid_correct = False
        self._font_point_size = 20
        self._live_validation = True

        self.setAlignment(Qt.AlignCenter)
        self.setMaxLength(1)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.IBeamCursor)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)

        self.setFont(create_font(self._font_point_size))
        self.setValidator(QIntValidator(1, GRID_SIZE, self))
        self._apply_style()

    def set_theme(self, theme: dict, section_color: QColor) -> None:
        self._theme = theme
        self._section_color = section_color
        self._apply_style()

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self.setReadOnly(locked)
        self.setProperty("locked", locked)
        self._apply_style()

    def set_highlight(self, role: Optional[str]) -> None:
        self._highlight_role = role
        self._apply_style()

    def set_subgrid_correct(self, status: bool) -> None:
        if self._subgrid_correct != status:
            self._subgrid_correct = status
            self._apply_style()

    def set_live_validation(self, enabled: bool) -> None:
        self._live_validation = enabled

    def update_font(self, point_size: int) -> None:
        self._font_point_size = point_size
        self.setFont(create_font(point_size))
        self._apply_style()

    def value(self) -> int:
        text = self.text().strip()
        return int(text) if text else 0

    # -- Qt event overrides -------------------------------------------------
    def focusInEvent(self, event) -> None:  # type: ignore[override]
        super().focusInEvent(event)
        self.focused.emit(self.row, self.col)
        self.selectAll()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if self._locked:
            event.ignore()
            return
        key = event.key()
        modifiers = event.modifiers()
        if key in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_0, Qt.Key_Space):
            self._commit_value(0)
            event.accept()
            return
        if Qt.Key_1 <= key <= Qt.Key_9:
            self._commit_value(key - Qt.Key_0)
            event.accept()
            return
        if modifiers & Qt.KeypadModifier and Qt.Key_0 <= key <= Qt.Key_9:
            digit = key - Qt.Key_0
            self._commit_value(digit)
            event.accept()
            return
        navigation = {
            Qt.Key_Left: (0, -1),
            Qt.Key_Right: (0, 1),
            Qt.Key_Up: (-1, 0),
            Qt.Key_Down: (1, 0),
        }
        if key in navigation:
            self._board.focus_relative(self.row, self.col, *navigation[key])
            event.accept()
            return
        if key in (Qt.Key_Tab, Qt.Key_Return, Qt.Key_Enter):
            self._board.focus_next(self.row, self.col)
            event.accept()
            return
        if key == Qt.Key_Backtab:
            self._board.focus_previous(self.row, self.col)
            event.accept()
            return
        super().keyPressEvent(event)

    def _commit_value(self, digit: int) -> None:
        if self._locked:
            return
        if digit == 0:
            self.clear()
        else:
            allowed = self._board.allowed_values(self.row, self.col)
            if digit not in allowed:
                if self._live_validation:
                    self._board.flash_invalid(self.row, self.col)
                return
            self.setText(str(digit))
        self.valueCommitted.emit(self.value())

    def _apply_style(self) -> None:
        theme = self._theme
        border_color = theme["cell_border"]
        value = self.value()
        if self._locked:
            base = QColor(theme["locked_cell_bg"])
        else:
            base = QColor(theme["entry_bg"]) if value else QColor(self._section_color)
            if not value:
                base = base.lighter(118 if not theme["is_dark"] else 130)

        if self._highlight_role == "error":
            fill = theme["error_fill_dark"] if theme["is_dark"] else theme["error_fill"]
            base = QColor(fill)
            border_color = theme["cell_border_error"]
        elif self._highlight_role == "focused":
            border_color = theme["cell_border_focus"]
            factor = 112 if self._locked else (120 if not theme["is_dark"] else 140)
            base = base.lighter(factor)
        elif self._highlight_role in {"peer", "family"}:
            border_color = theme["cell_border_peer"]
            factor = 108 if self._locked else (112 if not theme["is_dark"] else 128)
            base = base.lighter(factor)

        if self._subgrid_correct and value:
            text_color = theme["subgrid_correct_text"]
        else:
            text_color = theme["cell_locked_text"] if self._locked else theme["cell_text"]

        font_css = font_css_family()
        self.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {base.name()};
                border-radius: 14px;
                border: 1.6px solid {border_color};
                color: {text_color};
                font-family: "{font_css}";
                font-size: {self._font_point_size}pt;
                font-weight: 600;
                padding: 4px 0;
                selection-background-color: {theme['selection']};
                selection-color: {theme['cell_text']};
            }}
            """
        )


class SudokuBoard(QFrame):
    """9x9 grid of themed Sudoku cells arranged into subgrid islands."""

    cellFocused = pyqtSignal(int, int)
    boardEdited = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._theme = THEMES["Aqua"]
        self._section_palette = [QColor(code) for code in self._theme["section_colors"]]
        self._cells: List[List[SudokuCell]] = []
        self._subgrids: List[List[SubgridWidget]] = []
        self._locked_map: List[List[bool]] = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        self._focused: Optional[Tuple[int, int]] = None
        self._error_cells: Set[Tuple[int, int]] = set()
        self._loading = False

        outer_layout = QGridLayout()
        outer_layout.setSpacing(12)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        for subgrid_row in range(SECTION_SIZE):
            row_widgets: List[SubgridWidget] = []
            for subgrid_col in range(SECTION_SIZE):
                index = subgrid_row * SECTION_SIZE + subgrid_col
                subgrid = SubgridWidget(index, self)
                row_widgets.append(subgrid)
                outer_layout.addWidget(subgrid, subgrid_row, subgrid_col)
            self._subgrids.append(row_widgets)

        for r in range(GRID_SIZE):
            cell_row: List[SudokuCell] = []
            for c in range(GRID_SIZE):
                cell = SudokuCell(self, r, c, self)
                cell.focused.connect(self._on_focus)
                cell.textChanged.connect(self._on_cell_value_changed)
                cell_row.append(cell)
                subgrid = self._subgrids[r // SECTION_SIZE][c // SECTION_SIZE]
                subgrid.grid_layout().addWidget(cell, r % SECTION_SIZE, c % SECTION_SIZE)
            self._cells.append(cell_row)

        self.setLayout(outer_layout)
        self.apply_theme(self._theme)

    # -- Public API ---------------------------------------------------------
    def cells(self) -> Sequence[Sequence[SudokuCell]]:
        return self._cells

    def is_locked(self, row: int, col: int) -> bool:
        return self._locked_map[row][col]

    def set_board(self, board: Board, locked: Sequence[Sequence[bool]]) -> None:
        self._loading = True
        self._locked_map = [[bool(cell_locked) for cell_locked in row] for row in locked]
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self._cells[r][c]
                cell.blockSignals(True)
                cell.setText(str(board[r][c]) if board[r][c] else "")
                cell.set_locked(self._locked_map[r][c])
                cell.set_subgrid_correct(False)
                cell.set_highlight(None)
                cell.blockSignals(False)
        self.refresh_subgrid_annotations()
        self._loading = False
        self.clear_highlight()
        self.boardEdited.emit()

    def to_board(self) -> Board:
        return [[cell.value() for cell in row] for row in self._cells]

    def apply_theme(self, theme: dict) -> None:
        self._theme = theme
        self._section_palette = [QColor(code) for code in theme["section_colors"]]
        for subgrid_row in range(SECTION_SIZE):
            for subgrid_col in range(SECTION_SIZE):
                index = subgrid_row * SECTION_SIZE + subgrid_col
                color = self._section_palette[index]
                self._subgrids[subgrid_row][subgrid_col].set_theme(theme, color)
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                index = (r // SECTION_SIZE) * SECTION_SIZE + (c // SECTION_SIZE)
                self._cells[r][c].set_theme(theme, self._section_palette[index])
        self._refresh_highlights()

    def set_font_size(self, point_size: int) -> None:
        for row in self._cells:
            for cell in row:
                cell.update_font(point_size)

    def set_live_validation(self, enabled: bool) -> None:
        if not enabled:
            self.clear_errors()
        for row in self._cells:
            for cell in row:
                cell.set_live_validation(enabled)

    def clear_highlight(self) -> None:
        self._focused = None
        self._error_cells.clear()
        self._refresh_highlights()
        self.cellFocused.emit(-1, -1)

    def mark_errors(self, cells: Sequence[Tuple[int, int]]) -> None:
        self._error_cells = set(cells)
        self._refresh_highlights()

    def clear_errors(self) -> None:
        self._error_cells.clear()
        self._refresh_highlights()

    def flash_invalid(self, row: int, col: int) -> None:
        self._error_cells.add((row, col))
        self._refresh_highlights()

        def remove_flash() -> None:
            if (row, col) in self._error_cells:
                self._error_cells.remove((row, col))
                self._refresh_highlights()

        QTimer.singleShot(260, remove_flash)

    def allowed_values(self, row: int, col: int) -> Set[int]:
        if self._locked_map[row][col]:
            return set()
        board = self.to_board()
        board[row][col] = 0
        allowed = {value for value in range(1, GRID_SIZE + 1) if is_valid(board, row, col, value)}
        current = self._cells[row][col].value()
        if current and is_valid(board, row, col, current):
            allowed.add(current)
        return allowed

    def has_errors(self) -> bool:
        return bool(self._error_cells)

    def set_editable(self, enabled: bool) -> None:
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self._locked_map[r][c]:
                    continue
                self._cells[r][c].setReadOnly(not enabled)

    def refresh_subgrid_annotations(self) -> None:
        board = self.to_board()
        correct_cells: Set[Tuple[int, int]] = set()
        for base_row in range(0, GRID_SIZE, SECTION_SIZE):
            for base_col in range(0, GRID_SIZE, SECTION_SIZE):
                coords = [
                    (base_row + dr, base_col + dc)
                    for dr in range(SECTION_SIZE)
                    for dc in range(SECTION_SIZE)
                ]
                values = [board[r][c] for r, c in coords]
                if 0 in values or len(set(values)) != GRID_SIZE:
                    continue
                if all(is_valid(board, r, c, board[r][c]) for r, c in coords):
                    correct_cells.update(coords)
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self._cells[r][c].set_subgrid_correct((r, c) in correct_cells)

    # -- Focus helpers ------------------------------------------------------
    def focus_relative(self, row: int, col: int, drow: int, dcol: int) -> None:
        new_row = (row + drow) % GRID_SIZE
        new_col = (col + dcol) % GRID_SIZE
        self._cells[new_row][new_col].setFocus()

    def focus_next(self, row: int, col: int) -> None:
        new_row, new_col = row, col + 1
        if new_col >= GRID_SIZE:
            new_col = 0
            new_row = (row + 1) % GRID_SIZE
        self._cells[new_row][new_col].setFocus()

    def focus_previous(self, row: int, col: int) -> None:
        new_row, new_col = row, col - 1
        if new_col < 0:
            new_col = GRID_SIZE - 1
            new_row = (row - 1) % GRID_SIZE
        self._cells[new_row][new_col].setFocus()

    # -- Internal event handlers -------------------------------------------
    def _on_focus(self, row: int, col: int) -> None:
        self._focused = (row, col)
        self._refresh_highlights()
        self.cellFocused.emit(row, col)

    def _on_cell_value_changed(self) -> None:
        if self._loading:
            return
        board = self.to_board()
        self._error_cells.clear()
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                value = board[r][c]
                if value == 0:
                    continue
                board[r][c] = 0
                if not is_valid(board, r, c, value):
                    self._error_cells.add((r, c))
                board[r][c] = value
        self.refresh_subgrid_annotations()
        self._refresh_highlights()
        self.boardEdited.emit()

    def _refresh_highlights(self) -> None:
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self._cells[r][c]
                role: Optional[str] = None
                if (r, c) in self._error_cells:
                    role = "error"
                elif self._focused:
                    fr, fc = self._focused
                    if (r, c) == (fr, fc):
                        role = "focused"
                    elif r == fr or c == fc:
                        role = "peer"
                    elif (r // SECTION_SIZE, c // SECTION_SIZE) == (fr // SECTION_SIZE, fc // SECTION_SIZE):
                        role = "family"
                cell.set_highlight(role)


__all__ = ["SudokuBoard", "SudokuCell", "SubgridWidget", "GRID_SIZE", "SECTION_SIZE"]
