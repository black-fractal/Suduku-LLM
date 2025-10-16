"""Shared data models used by the modern Sudoku GUI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from sudoku.core import Board, Difficulty


@dataclass
class GameSettings:
    difficulty: Difficulty = "easy"
    font_size: int = 16
    show_errors: bool = True
    theme: str = "Aqua"


@dataclass
class Move:
    row: int
    col: int
    previous: int
    current: int
    timestamp: float
    move_id: int
    added_move: int
    added_correct: int
    added_wrong: int
    active: bool = True


@dataclass
class SessionStats:
    moves: int = 0
    correct: int = 0
    wrong: int = 0


@dataclass
class LeaderboardEntry:
    username: str
    difficulty: str
    elapsed_seconds: float
    moves: int
    correct: int
    wrong: int
    total_moves: int
    timestamp: float


BoardDiff = List[Tuple[int, int, int, int]]


__all__ = [
    "GameSettings",
    "Move",
    "SessionStats",
    "LeaderboardEntry",
    "BoardDiff",
]
