"""Main window orchestration for the modern Sudoku GUI."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sudoku.core import Board, Difficulty, generate, is_valid, solve

from .board import GRID_SIZE, SudokuBoard
from .fonts import font_css_family, format_duration
from .keyboard import VirtualKeyboard
from .leaderboard import LeaderboardDialog, LeaderboardManager
from .models import GameSettings, LeaderboardEntry, Move
from .session import SessionTracker
from .themes import THEMES


class SudokuMainWindow(QMainWindow):
    """Primary application window hosting the Sudoku board and UI chrome."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sudoku Studio")
        self.resize(760, 920)

        self._settings = GameSettings()
        self._board_widget = SudokuBoard(self)
        self._keyboard = VirtualKeyboard(self)
        self._status = QLabel("", self)
        self._timer_label = QLabel("00:00", self)
        self._timer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._timer = self._create_timer()
        self._elapsed_seconds = 0

        self._session = SessionTracker()
        self._leaderboard_manager = LeaderboardManager()
        self._leaderboard_dialog = LeaderboardDialog(self)
        self._username = self._prompt_username()

        self._active_cell: Optional[Tuple[int, int]] = None
        self._status_message = ""

        self._current_theme = THEMES[self._settings.theme]

        self._central = QWidget(self)
        self._central.setObjectName("CentralWidget")
        self.setCentralWidget(self._central)

        self._title_label = QLabel("Sudoku Studio", self)
        self._subtitle_label = QLabel("Islanded grids with intelligent guidance.", self)
        self._difficulty_chip = QLabel("", self)
        self._difficulty_chip.setAlignment(Qt.AlignCenter)
        self._difficulty_chip.setFixedHeight(28)

        self._buttons: List[QPushButton] = []
        self._build_ui()
        self._connect_signals()
        self._apply_settings()
        self.new_game()

    # ------------------------------------------------------------------ setup
    def _prompt_username(self) -> str:
        name = ""
        while not name:
            name, ok = QInputDialog.getText(self, "Welcome", "Enter your name to begin:")
            if not ok:
                name = "Guest"
                break
            name = name.strip()
        return name or "Guest"

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self._central)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.addWidget(self._title_label)
        title_block.addWidget(self._subtitle_label)
        header_layout.addLayout(title_block)
        header_layout.addStretch(1)
        header_layout.addWidget(self._difficulty_chip)
        layout.addLayout(header_layout)

        self._board_container = QWidget(self)
        board_layout = QVBoxLayout(self._board_container)
        board_layout.setContentsMargins(20, 20, 20, 20)
        board_layout.addWidget(self._board_widget, alignment=Qt.AlignCenter)
        self._board_container.setObjectName("BoardFrame")
        self._board_container.setAttribute(Qt.WA_StyledBackground, True)
        layout.addWidget(self._board_container)
        layout.addWidget(self._keyboard)

        controls_container = QWidget(self)
        controls_container.setObjectName("ControlsContainer")
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)

        self._undo_button = QPushButton("Undo", self)
        self._undo_button.clicked.connect(self.undo_move)
        self._undo_button.setEnabled(False)
        self._redo_button = QPushButton("Redo", self)
        self._redo_button.clicked.connect(self.redo_move)
        self._redo_button.setEnabled(False)
        btn_new = QPushButton("New Puzzle", self)
        btn_new.clicked.connect(self.new_game)
        btn_solve = QPushButton("Reveal Solution", self)
        btn_solve.clicked.connect(self.solve_board)
        btn_check = QPushButton("Smart Check", self)
        btn_check.clicked.connect(self.check_board)
        btn_settings = QPushButton("Preferences", self)
        btn_settings.clicked.connect(self.show_settings)

        for button in (
            self._undo_button,
            self._redo_button,
            btn_new,
            btn_solve,
            btn_check,
            btn_settings,
        ):
            button.setCursor(Qt.PointingHandCursor)
            controls_layout.addWidget(button)
            self._buttons.append(button)

        controls_layout.addStretch(1)
        layout.addWidget(controls_container)
        self._controls_container = controls_container

        info_layout = QHBoxLayout()
        self._status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._status.setWordWrap(True)
        info_layout.addWidget(self._status)
        info_layout.addWidget(self._timer_label)
        layout.addLayout(info_layout)

        self._menubar = QMenuBar(self)
        file_menu = self._menubar.addMenu("File")
        act_save = QAction("Save…", self)
        act_save.triggered.connect(self.save_board)
        file_menu.addAction(act_save)
        act_load = QAction("Load…", self)
        act_load.triggered.connect(self.load_board)
        file_menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)
        self.setMenuBar(self._menubar)

        self._toolbar = QToolBar("Quick Actions", self)
        self._toolbar.setMovable(False)
        self._toolbar.addAction(act_save)
        self._toolbar.addAction(act_load)
        self._toolbar.addSeparator()
        act_leaderboard = QAction("Leaderboard", self)
        act_leaderboard.triggered.connect(self._show_leaderboard)
        self._toolbar.addAction(act_leaderboard)
        self._leaderboard_action = act_leaderboard
        self.addToolBar(Qt.TopToolBarArea, self._toolbar)

    def _connect_signals(self) -> None:
        self._board_widget.cellFocused.connect(self._handle_cell_focus)
        self._board_widget.boardEdited.connect(self._handle_board_edit)
        self._keyboard.numberSelected.connect(self._handle_keyboard_number)
        self._keyboard.clearRequested.connect(self._handle_keyboard_clear)

    def _create_timer(self):
        from PyQt5.QtCore import QTimer

        timer = QTimer(self)
        timer.setInterval(1000)
        timer.timeout.connect(self._advance_timer)
        return timer

    # ---------------------------------------------------------------- theming
    def _apply_settings(self) -> None:
        theme = THEMES[self._settings.theme]
        self._current_theme = theme
        self._board_widget.apply_theme(theme)
        self._board_widget.set_font_size(self._settings.font_size)
        self._board_widget.set_live_validation(self._settings.show_errors)
        self._difficulty_chip.setText(self._settings.difficulty.title())
        self._apply_theme_to_window()
        self._refresh_keyboard_options()

    def _apply_theme_to_window(self) -> None:
        theme = self._current_theme
        font_css = font_css_family()
        self._central.setStyleSheet(
            f"""
            QWidget#CentralWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme['gradient_top']}, stop:1 {theme['gradient_bottom']});
            }}
            """
        )
        self._title_label.setStyleSheet(
            f"color: {theme['text_primary']}; font-size: 32px; font-weight: 700; font-family: '{font_css}';"
        )
        self._subtitle_label.setStyleSheet(
            f"color: {theme['text_secondary']}; font-size: 16px; font-weight: 400; font-family: '{font_css}';"
        )
        self._difficulty_chip.setStyleSheet(
            f"""
            QLabel {{
                background-color: {theme['chip_bg']};
                color: {theme['chip_text']};
                border-radius: 14px;
                padding: 4px 14px;
                font-weight: 600;
                font-family: '{font_css}';
            }}
            """
        )
        self._board_container.setStyleSheet(
            f"""
            QWidget#BoardFrame {{
                background-color: {theme['panel_bg']};
                border: 1px solid {theme['panel_border']};
                border-radius: 28px;
            }}
            """
        )
        button_style = f"""
        QPushButton {{
            background-color: {theme['button_bg']};
            color: {theme['button_text']};
            border-radius: 16px;
            border: 1px solid {theme['button_border']};
            font-family: '{font_css}';
            font-size: 16px;
            font-weight: 600;
            padding: 10px 22px;
        }}
        QPushButton:hover {{
            background-color: {theme['button_bg_hover']};
        }}
        QPushButton:pressed {{
            background-color: {theme['button_bg_pressed']};
        }}
        """
        for button in self._buttons:
            button.setStyleSheet(button_style)

        self._controls_container.setStyleSheet("QWidget#ControlsContainer { background: transparent; }")
        self._status.setStyleSheet(
            f"color: {theme['text_secondary']}; font-size: 15px; font-family: '{font_css}';"
        )
        self._timer_label.setStyleSheet(
            f"color: {theme['timer']}; font-size: 22px; font-weight: 600; font-family: '{font_css}';"
        )
        self._menubar.setStyleSheet(
            f"""
            QMenuBar {{
                background: transparent;
                color: {theme['text_primary']};
                font-family: '{font_css}';
                font-weight: 500;
            }}
            QMenuBar::item:selected {{
                background: {theme['button_bg_hover']};
            }}
            QMenu {{
                background: {theme['panel_bg']};
                color: {theme['text_primary']};
                border: 1px solid {theme['panel_border']};
            }}
            """
        )
        self._toolbar.setStyleSheet(
            f"""
            QToolBar {{
                background: transparent;
                border: 0px;
            }}
            QToolButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border-radius: 14px;
                border: 1px solid {theme['button_border']};
                font-family: '{font_css}';
                padding: 6px 12px;
            }}
            QToolButton:hover {{
                background-color: {theme['button_bg_hover']};
            }}
            """
        )
        self._keyboard.apply_theme(theme)

    # -------------------------------------------------------------- status bar
    def _set_status(self, message: str, *, error: bool = False) -> None:
        theme = self._current_theme
        color = theme["status_error"] if error else theme["status_ok"]
        font_css = font_css_family()
        self._status.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: 600; font-family: '{font_css}';"
        )
        self._status_message = message
        self._update_status_summary()

    def _update_status_summary(self) -> None:
        stats = self._session.stats()
        summary = f"Moves: {stats.moves} | Correct: {stats.correct} | Wrong: {stats.wrong}"
        if self._status_message:
            summary = f"{self._status_message}    • {summary}"
        self._status.setText(summary)

    def _update_undo_redo_state(self) -> None:
        self._undo_button.setEnabled(self._session.undo_available())
        self._redo_button.setEnabled(self._session.redo_available())

    # ---------------------------------------------------------------- session
    def _start_new_session(self, board: Board, *, difficulty: Difficulty) -> None:
        self._session.start(username=self._username, difficulty=difficulty, board=board)
        self._leaderboard_dialog.update_leaderboard(self._leaderboard_manager.entries)
        self._leaderboard_dialog.update_history(self._session.move_history())
        self._update_status_summary()
        self._update_undo_redo_state()

    def _reset_timer(self) -> None:
        self._elapsed_seconds = 0
        self._timer_label.setText("00:00")
        self._timer.start()

    def _advance_timer(self) -> None:
        self._elapsed_seconds += 1
        self._timer_label.setText(format_duration(self._elapsed_seconds))

    # ---------------------------------------------------------------- events
    def _handle_cell_focus(self, row: int, col: int) -> None:
        if row < 0 or col < 0:
            self._active_cell = None
        else:
            self._active_cell = (row, col)
        self._refresh_keyboard_options()

    def _handle_board_edit(self) -> None:
        board = self._board_widget.to_board()
        moves = self._session.record_differences(board)
        if moves:
            self._leaderboard_dialog.update_history(self._session.move_history())
            self._update_status_summary()
            self._update_undo_redo_state()
        self._refresh_keyboard_options()
        self._board_widget.refresh_subgrid_annotations()
        if self._session.check_completion(board, has_errors=self._board_widget.has_errors()):
            self._handle_completion()

    def _handle_keyboard_number(self, value: int) -> None:
        if self._active_cell is None:
            return
        row, col = self._active_cell
        if self._board_widget.is_locked(row, col):
            return
        allowed = self._board_widget.allowed_values(row, col)
        if value not in allowed:
            self._board_widget.flash_invalid(row, col)
            return
        with self._session.suspend_tracking():
            self._board_widget.cells()[row][col].setText(str(value))
        self._session.set_board_snapshot(self._board_widget.to_board())
        self._handle_board_edit()

    def _handle_keyboard_clear(self) -> None:
        if self._active_cell is None:
            return
        row, col = self._active_cell
        if self._board_widget.is_locked(row, col):
            return
        with self._session.suspend_tracking():
            self._board_widget.cells()[row][col].clear()
        self._session.set_board_snapshot(self._board_widget.to_board())
        self._handle_board_edit()

    # ---------------------------------------------------------------- actions
    def new_game(self) -> None:
        board = generate(self._settings.difficulty)
        locked = [[value != 0 for value in row] for row in board]
        self._board_widget.set_board(board, locked)
        self._board_widget.set_editable(True)
        self._difficulty_chip.setText(self._settings.difficulty.title())
        self._start_new_session(board, difficulty=self._settings.difficulty)
        self._set_status(f"New {self._settings.difficulty.title()} puzzle ready.")
        self._active_cell = None
        self._refresh_keyboard_options()
        self._reset_timer()

    def solve_board(self) -> None:
        board = self._board_widget.to_board()
        attempt = [row[:] for row in board]
        if solve(attempt):
            with self._session.suspend_tracking():
                solved_locked = [[True for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
                self._board_widget.set_board(attempt, solved_locked)
            self._board_widget.set_editable(False)
            self._session.set_board_snapshot(self._board_widget.to_board())
            self._session.mark_completed()
            self._update_undo_redo_state()
            self._refresh_keyboard_options()
            self._set_status("Puzzle solved automatically. Start a new puzzle when ready.")
            self._timer.stop()
        else:
            self._set_status("No solution found for this board.", error=True)

    def check_board(self) -> None:
        board = self._board_widget.to_board()
        invalid_cells: List[Tuple[int, int]] = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                value = board[r][c]
                if value and not is_valid(board, r, c, value):
                    invalid_cells.append((r, c))
        if invalid_cells:
            self._set_status(
                f"Conflicts spotted at {', '.join(f'({r+1},{c+1})' for r, c in invalid_cells)}.",
                error=True,
            )
            if self._settings.show_errors:
                self._board_widget.mark_errors(invalid_cells)
        else:
            self._board_widget.clear_errors()
            self._set_status("Everything looks valid so far. Keep going!")

    def show_settings(self) -> None:
        from .dialogs import SettingsDialog  # Lazy import to avoid circular dependency

        dialog = SettingsDialog(self._settings, self)
        if dialog.exec_():
            previous = self._settings.difficulty
            self._settings = dialog.updated_settings()
            self._apply_settings()
            if self._settings.difficulty != previous:
                self.new_game()
            else:
                self._set_status("Preferences updated.")

    def save_board(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Sudoku", "", "Sudoku Files (*.sdk)")
        if not path:
            return
        try:
            board = self._board_widget.to_board()
            Path(path).write_text("\n".join(" ".join(str(value) for value in row) for row in board))
            self._set_status(f"Saved to {path}")
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save board:\n{exc}")

    def load_board(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Sudoku", "", "Sudoku Files (*.sdk)")
        if not path:
            return
        try:
            lines = Path(path).read_text().splitlines()
            board: Board = []
            for line in lines:
                parts = [int(part) for part in line.split()]
                if len(parts) != GRID_SIZE:
                    raise ValueError("Each row must contain 9 numbers.")
                board.append(parts)
            if len(board) != GRID_SIZE:
                raise ValueError("The file must contain 9 rows.")
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Load Error", f"Failed to load board:\n{exc}")
            return
        locked = [[value != 0 for value in row] for row in board]
        self._board_widget.set_board(board, locked)
        self._board_widget.set_editable(True)
        self._difficulty_chip.setText("Custom")
        self._start_new_session(board, difficulty="custom")  # type: ignore[arg-type]
        self._set_status(f"Loaded from {path}")
        self._active_cell = None
        self._refresh_keyboard_options()
        self._reset_timer()

    def undo_move(self) -> None:
        move = self._session.undo()
        if not move:
            return
        with self._session.suspend_tracking():
            self._board_widget.cells()[move.row][move.col].setText(str(move.previous) if move.previous else "")
        self._session.set_board_snapshot(self._board_widget.to_board())
        self._board_widget.refresh_subgrid_annotations()
        self._leaderboard_dialog.update_history(self._session.move_history())
        self._update_status_summary()
        self._update_undo_redo_state()
        self._refresh_keyboard_options()

    def redo_move(self) -> None:
        move = self._session.redo()
        if not move:
            return
        with self._session.suspend_tracking():
            self._board_widget.cells()[move.row][move.col].setText(str(move.current) if move.current else "")
        self._session.set_board_snapshot(self._board_widget.to_board())
        self._board_widget.refresh_subgrid_annotations()
        self._leaderboard_dialog.update_history(self._session.move_history())
        self._update_status_summary()
        self._update_undo_redo_state()
        self._refresh_keyboard_options()
        if self._session.check_completion(self._board_widget.to_board(), has_errors=self._board_widget.has_errors()):
            self._handle_completion()

    def _refresh_keyboard_options(self) -> None:
        if self._session.puzzle_completed():
            self._keyboard.update_options(set(), active=False, current=0)
            return
        if self._active_cell is None:
            self._keyboard.update_options(set(), active=False, current=0)
            return
        row, col = self._active_cell
        locked = self._board_widget.is_locked(row, col)
        current_value = self._board_widget.cells()[row][col].value()
        allowed = self._board_widget.allowed_values(row, col)
        self._keyboard.update_options(allowed, active=not locked, current=current_value)

    # ----------------------------------------------------------- completion UI
    def _handle_completion(self) -> None:
        self._timer.stop()
        self._session.mark_completed()
        self._board_widget.set_editable(False)
        self._refresh_keyboard_options()
        entry = self._session.completion_entry()
        summary = (
            f"Congratulations, {entry.username}!\n\n"
            f"Time: {format_duration(entry.elapsed_seconds)}\n"
            f"Moves: {entry.moves}\n"
            f"Correct entries: {entry.correct}\n"
            f"Wrong attempts: {entry.wrong}\n"
            f"Total inputs (incl. changes): {entry.total_moves}"
        )
        QMessageBox.information(self, "Sudoku Complete", summary)
        self._leaderboard_manager.add_entry(entry)
        self._leaderboard_dialog.update_leaderboard(self._leaderboard_manager.entries)
        self._leaderboard_dialog.update_history(self._session.move_history())
        self._update_status_summary()
        self._update_undo_redo_state()

    def _show_leaderboard(self) -> None:
        self._leaderboard_dialog.update_leaderboard(self._leaderboard_manager.entries)
        self._leaderboard_dialog.update_history(self._session.move_history())
        self._leaderboard_dialog.show()
        self._leaderboard_dialog.raise_()
        self._leaderboard_dialog.activateWindow()


def run_modern_app() -> None:
    app = QApplication.instance() or QApplication([])
    window = SudokuMainWindow()
    window.show()
    app.exec_()
