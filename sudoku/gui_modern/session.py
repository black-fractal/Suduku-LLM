"""Domain-level session tracking for the modern Sudoku GUI."""
from __future__ import annotations

from contextlib import contextmanager
from time import monotonic
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from sudoku.core import Board, solve, is_valid

from .models import LeaderboardEntry, Move, SessionStats

GRID_SIZE = 9


class SessionTracker:
    """Tracks puzzle state, moves, undo/redo stacks, and statistics."""

    def __init__(self) -> None:
        self.username: str = "Guest"
        self.difficulty: str = "easy"
        self.solution: Optional[Board] = None

        self._stats = SessionStats()
        self._move_history: List[Move] = []
        self._undo_stack: List[Move] = []
        self._redo_stack: List[Move] = []
        self._board_snapshot: Board = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self._next_move_id = 1
        self._tracking_enabled = False
        self._tracking_suspensions = 0
        self._puzzle_completed = False
        self._start_time = monotonic()

    # ------------------------------------------------------------------ setup
    def start(self, *, username: str, difficulty: str, board: Board) -> None:
        self.username = username or "Guest"
        self.difficulty = difficulty
        self.solution = self._compute_solution(board)
        self._stats = SessionStats()
        self._move_history.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._next_move_id = 1
        self._board_snapshot = [row[:] for row in board]
        self._tracking_enabled = True
        self._tracking_suspensions = 0
        self._puzzle_completed = False
        self._start_time = monotonic()

    def set_board_snapshot(self, board: Board) -> None:
        self._board_snapshot = [row[:] for row in board]

    def _compute_solution(self, board: Board) -> Optional[Board]:
        candidate = [row[:] for row in board]
        if solve(candidate):
            return candidate
        return None

    # -------------------------------------------------------------------- util
    def board_snapshot(self) -> Board:
        return [row[:] for row in self._board_snapshot]

    def stats(self) -> SessionStats:
        return SessionStats(
            moves=self._stats.moves,
            correct=self._stats.correct,
            wrong=self._stats.wrong,
        )

    def elapsed_seconds(self) -> float:
        return monotonic() - self._start_time

    def move_history(self) -> List[Move]:
        return list(self._move_history)

    def total_input_actions(self) -> int:
        return len([move for move in self._move_history if move.active and move.current != 0])

    def tracking_active(self) -> bool:
        return self._tracking_enabled and self._tracking_suspensions == 0 and not self._puzzle_completed

    def puzzle_completed(self) -> bool:
        return self._puzzle_completed

    @contextmanager
    def suspend_tracking(self):
        self._tracking_suspensions += 1
        try:
            yield
        finally:
            self._tracking_suspensions = max(0, self._tracking_suspensions - 1)

    # --------------------------------------------------------------- move flow
    def record_differences(self, board: Board) -> List[Move]:
        """Record differences compared to the last snapshot."""
        if not self.tracking_active():
            self.set_board_snapshot(board)
            return []

        diffs: List[Tuple[int, int, int, int]] = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                previous = self._board_snapshot[r][c]
                current = board[r][c]
                if previous != current:
                    diffs.append((r, c, previous, current))

        if not diffs:
            return []

        moves = [self._create_move(r, c, previous, current) for r, c, previous, current in diffs]
        self._board_snapshot = [row[:] for row in board]
        return moves

    def _create_move(self, row: int, col: int, previous: int, current: int) -> Move:
        added_move = 1 if current != previous and current != 0 else 0
        added_correct = 0
        added_wrong = 0
        if added_move and self.solution:
            target = self.solution[row][col]
            if current == target:
                added_correct = 1
            else:
                added_wrong = 1
        move = Move(
            row=row,
            col=col,
            previous=previous,
            current=current,
            timestamp=monotonic(),
            move_id=self._next_move_id,
            added_move=added_move,
            added_correct=added_correct,
            added_wrong=added_wrong,
        )
        self._next_move_id += 1
        self._move_history.append(move)
        self._undo_stack.append(move)
        self._redo_stack.clear()
        self._mutate_stats(move, add=True)
        return move

    def undo(self) -> Optional[Move]:
        if not self._undo_stack:
            return None
        move = self._undo_stack.pop()
        move.active = False
        self._redo_stack.append(move)
        self._mutate_stats(move, add=False)
        self._tracking_enabled = True
        self._puzzle_completed = False
        return move

    def redo(self) -> Optional[Move]:
        if not self._redo_stack:
            return None
        move = self._redo_stack.pop()
        move.active = True
        self._undo_stack.append(move)
        self._mutate_stats(move, add=True)
        return move

    def clear_redo(self) -> None:
        self._redo_stack.clear()

    def undo_available(self) -> bool:
        return bool(self._undo_stack)

    def redo_available(self) -> bool:
        return bool(self._redo_stack)

    def _mutate_stats(self, move: Move, *, add: bool) -> None:
        factor = 1 if add else -1
        self._stats.moves = max(0, self._stats.moves + factor * move.added_move)
        self._stats.correct = max(0, self._stats.correct + factor * move.added_correct)
        self._stats.wrong = max(0, self._stats.wrong + factor * move.added_wrong)

    # -------------------------------------------------------------- completion
    def mark_completed(self) -> None:
        self._puzzle_completed = True
        self._tracking_enabled = False

    def completion_entry(self) -> LeaderboardEntry:
        return LeaderboardEntry(
            username=self.username,
            difficulty=self.difficulty,
            elapsed_seconds=self.elapsed_seconds(),
            moves=self._stats.moves,
            correct=self._stats.correct,
            wrong=self._stats.wrong,
            total_moves=self.total_input_actions(),
            timestamp=monotonic(),
        )

    def check_completion(self, board: Board, *, has_errors: bool) -> bool:
        if self._puzzle_completed:
            return False
        if has_errors:
            return False
        if any(0 in row for row in board):
            return False

        if self.solution:
            if board != self.solution:
                return False
        else:
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    value = board[r][c]
                    if value == 0:
                        return False
                    board[r][c] = 0
                    if not is_valid(board, r, c, value):
                        board[r][c] = value
                        return False
                    board[r][c] = value

        self.mark_completed()
        return True


__all__ = ["SessionTracker"]
