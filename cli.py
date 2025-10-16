"""Command-line interface for Sudoku generation and solving."""
from __future__ import annotations

import argparse
import sys
from typing import List, Sequence

from sudoku.core import Difficulty, generate, solve

DIFFICULTIES: Sequence[Difficulty] = ("easy", "medium", "hard")


def print_board(board: Sequence[Sequence[int]]) -> None:
    """Render a Sudoku board as an ASCII grid."""

    def cell_str(value: int) -> str:
        return f"{value if value != 0 else '.' :^3}"

    segment = "───────────"
    top = f"┌{segment}┬{segment}┬{segment}┐"
    middle = f"├{segment}┼{segment}┼{segment}┤"
    bottom = f"└{segment}┴{segment}┴{segment}┘"

    print(top)
    for row_index, row in enumerate(board):
        cells = [cell_str(value) for value in row]
        print(f"│{' '.join(cells[0:3])}│{' '.join(cells[3:6])}│{' '.join(cells[6:9])}│")
        if row_index in (2, 5):
            print(middle)
    print(bottom)


def read_board_from_stdin() -> List[List[int]]:
    """Read a board definition from standard input."""
    print("Enter 9 lines, each 9 digits (use 0 or . for blanks):")
    board: List[List[int]] = []
    while len(board) < 9:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        line = line.replace(".", "0")
        row = [int(ch) for ch in line if ch.isdigit()]
        if len(row) != 9:
            print("Each line must contain 9 digits; try again")
            continue
        board.append(row)
    if len(board) != 9:
        raise SystemExit("Incomplete board")
    return board


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate a new Sudoku puzzle and print it."""
    board = generate(args.difficulty)
    print(f"Generated ({args.difficulty}):")
    print_board(board)


def cmd_solve(_args: argparse.Namespace) -> None:
    """Solve a board provided via standard input."""
    board = read_board_from_stdin()
    print("Input board:")
    print_board(board)
    attempt = [row[:] for row in board]
    if solve(attempt):
        print("\nSolved:")
        print_board(attempt)
    else:
        print("No solution found")


def cmd_demo(args: argparse.Namespace) -> None:
    """Generate and immediately solve a puzzle for demonstration."""
    board = generate(args.difficulty)
    print(f"Demo puzzle ({args.difficulty}):")
    print_board(board)
    solution = [row[:] for row in board]
    solve(solution)
    print("\nSolution:")
    print_board(solution)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    common_difficulty = dict(
        metavar="difficulty",
        choices=DIFFICULTIES,
        help="Puzzle difficulty (default: %(default)s)",
    )

    generate_parser = subparsers.add_parser("generate", help="Generate a new puzzle")
    generate_parser.add_argument("difficulty", nargs="?", default="easy", **common_difficulty)
    generate_parser.set_defaults(func=cmd_generate)

    solve_parser = subparsers.add_parser("solve", help="Solve a puzzle read from stdin")
    solve_parser.set_defaults(func=cmd_solve)

    demo_parser = subparsers.add_parser("demo", help="Generate a puzzle and show its solution")
    demo_parser.add_argument("difficulty", nargs="?", default="easy", **common_difficulty)
    demo_parser.set_defaults(func=cmd_demo)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
