"""Run the Sudoku GUI."""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the Sudoku GUI")
    parser.add_argument(
        "--modern",
        action="store_true",
        help="Launch the modern-styled interface",
    )
    args = parser.parse_args()

    if args.modern:
        from sudoku.gui_modern import run_modern_app

        run_modern_app()
    else:
        from sudoku.gui import run_app as run_classic

        run_classic()


if __name__ == '__main__':
    main()
