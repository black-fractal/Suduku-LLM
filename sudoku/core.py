"""Core Sudoku generator and solver."""
from __future__ import annotations

import random
from typing import Iterable, List, Optional, Tuple, Literal

Board = List[List[int]]
Difficulty = Literal["easy", "medium", "hard"]

GRID_SIZE = 9
BOX_SIZE = 3

__all__ = ["Board", "Difficulty", "is_valid", "solve", "generate"]


def _find_empty(board: Board) -> Optional[Tuple[int, int]]:
    """Return the coordinates of the first empty cell (denoted by 0)."""
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if board[r][c] == 0:
                return r, c
    return None


def is_valid(board: Board, row: int, col: int, num: int) -> bool:
    """Return True if ``num`` can be placed at ``(row, col)``."""
    # Row (ignore the cell itself)
    for c in range(GRID_SIZE):
        if c != col and board[row][c] == num:
            return False
    # Column (ignore the cell itself)
    for r in range(GRID_SIZE):
        if r != row and board[r][col] == num:
            return False
    # Box
    br, bc = BOX_SIZE * (row // BOX_SIZE), BOX_SIZE * (col // BOX_SIZE)
    for r in range(br, br + BOX_SIZE):
        for c in range(bc, bc + BOX_SIZE):
            if (r != row or c != col) and board[r][c] == num:
                return False
    return True


def solve(board: Board) -> bool:
    """Solve ``board`` in-place using recursive backtracking."""
    empty = _find_empty(board)
    if not empty:
        return True
    r, c = empty
    for num in range(1, GRID_SIZE + 1):
        if is_valid(board, r, c, num):
            board[r][c] = num
            if solve(board):
                return True
            board[r][c] = 0
    return False


def _fill_board(board: Board) -> bool:
    """Populate the entire board with a complete valid Sudoku solution."""
    empty = _find_empty(board)
    if not empty:
        return True
    r, c = empty
    nums = list(range(1, GRID_SIZE + 1))
    random.shuffle(nums)
    for num in nums:
        if is_valid(board, r, c, num):
            board[r][c] = num
            if _fill_board(board):
                return True
            board[r][c] = 0
    return False


def _all_cells() -> Iterable[Tuple[int, int]]:
    """Yield the coordinates of every cell in the grid."""
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            yield r, c


def generate(difficulty: Difficulty = "easy") -> Board:
    """Generate a Sudoku puzzle for the requested ``difficulty``."""
    difficulty_map = {
        "easy": 36,
        "medium": 46,
        "hard": 54,
    }
    try:
        removals = difficulty_map[difficulty]
    except KeyError as exc:
        raise ValueError(f"Unknown difficulty '{difficulty}'. Expected one of {tuple(difficulty_map)}") from exc

    board: Board = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    _fill_board(board)

    cells = list(_all_cells())
    random.shuffle(cells)
    removed = 0
    for r, c in cells:
        if removed >= removals:
            break
        backup = board[r][c]
        board[r][c] = 0
        # Quick solvability check: ensure puzzle remains solvable after removal.
        copy_board = [row[:] for row in board]
        if not solve(copy_board):
            board[r][c] = backup
            continue
        removed += 1

    return board
