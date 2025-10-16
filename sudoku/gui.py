"""Simple Tkinter GUI for Sudoku."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import List

from .core import Board, generate, is_valid, solve


class SudokuGUI(tk.Frame):
    """Lightweight Tkinter interface for interacting with Sudoku boards."""

    def __init__(self, master=None) -> None:
        super().__init__(master)
        self.master = master
        self.pack()
        self.cells: List[List[tk.Entry]] = []
        self.board: Board = [[0] * 9 for _ in range(9)]
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the grid of entry widgets and control buttons."""
        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)

        for r in range(9):
            row_entries = []
            for c in range(9):
                e = tk.Entry(frame, width=2, justify='center', font=('Helvetica', 16))
                e.grid(row=r, column=c, padx=2, pady=2)
                row_entries.append(e)
            self.cells.append(row_entries)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="New", command=self.new).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Solve", command=self.solve).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Check", command=self.check).pack(side="left", padx=6)

    def new(self, difficulty: str = "easy") -> None:
        """Generate a new puzzle for the given difficulty."""
        self.board = generate(difficulty)
        self._load_board()

    def _load_board(self) -> None:
        """Populate the UI entries from ``self.board``."""
        for r in range(9):
            for c in range(9):
                val = self.board[r][c]
                e = self.cells[r][c]
                e.delete(0, tk.END)
                if val != 0:
                    e.insert(0, str(val))
                    e.config(state='disabled', disabledforeground='black')
                else:
                    e.config(state='normal')

    def _read_board(self) -> None:
        """Update ``self.board`` with the values currently entered by the user."""
        for r in range(9):
            for c in range(9):
                e = self.cells[r][c]
                txt = e.get().strip()
                self.board[r][c] = int(txt) if txt.isdigit() else 0

    def solve(self) -> None:
        self._read_board()
        bcopy = [row[:] for row in self.board]
        if solve(bcopy):
            self.board = bcopy
            self._load_board()
        else:
            messagebox.showinfo("Sudoku", "No solution found")

    def check(self) -> None:
        self._read_board()
        for r in range(9):
            for c in range(9):
                v = self.board[r][c]
                if v != 0 and not is_valid(self.board, r, c, v):
                    messagebox.showinfo("Sudoku", f"Invalid at {r+1},{c+1}")
                    return
        messagebox.showinfo("Sudoku", "Looks valid so far")


def run_app():
    root = tk.Tk()
    root.title("Sudoku")
    app = SudokuGUI(master=root)
    app.new("easy")
    root.mainloop()


if __name__ == '__main__':
    run_app()
