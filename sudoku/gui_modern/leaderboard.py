"""Leaderboard persistence and presentation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
)

from .fonts import format_duration
from .models import LeaderboardEntry, Move

LEADERBOARD_PATH = Path(__file__).resolve().parent / "leaderboard.json"


class LeaderboardManager:
    """Loads, stores, and persists leaderboard entries."""

    def __init__(self, path: Path = LEADERBOARD_PATH) -> None:
        self._path = path
        self._entries: List[LeaderboardEntry] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._entries = []
            return
        try:
            data = json.loads(self._path.read_text())
        except (OSError, json.JSONDecodeError):
            self._entries = []
            return
        entries: List[LeaderboardEntry] = []
        for item in data:
            try:
                entries.append(
                    LeaderboardEntry(
                        username=item["username"],
                        difficulty=item["difficulty"],
                        elapsed_seconds=float(item["elapsed_seconds"]),
                        moves=int(item["moves"]),
                        correct=int(item.get("correct", 0)),
                        wrong=int(item.get("wrong", 0)),
                        total_moves=int(item.get("total_moves", item["moves"])),
                        timestamp=float(item.get("timestamp", 0.0)),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        self._entries = sorted(entries, key=lambda e: (e.elapsed_seconds, -e.correct, e.wrong))

    def _save(self) -> None:
        payload = [
            {
                "username": entry.username,
                "difficulty": entry.difficulty,
                "elapsed_seconds": entry.elapsed_seconds,
                "moves": entry.moves,
                "correct": entry.correct,
                "wrong": entry.wrong,
                "total_moves": entry.total_moves,
                "timestamp": entry.timestamp,
            }
            for entry in self._entries
        ]
        try:
            self._path.write_text(json.dumps(payload, indent=2))
        except OSError:
            pass

    def add_entry(self, entry: LeaderboardEntry) -> None:
        self._entries.append(entry)
        self._entries.sort(key=lambda e: (e.elapsed_seconds, -e.correct, e.wrong))
        self._save()

    @property
    def entries(self) -> List[LeaderboardEntry]:
        return list(self._entries)


class LeaderboardDialog(QDialog):
    """Modal dialog listing leaderboard standings and move history."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Leaderboard & History")
        self.resize(560, 440)

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget(self)
        layout.addWidget(self._tabs)

        self._leaderboard_table = QTableWidget(0, 7, self)
        self._leaderboard_table.setHorizontalHeaderLabels(
            ["User", "Difficulty", "Time", "Moves", "Correct", "Wrong", "Total Inputs"]
        )
        header = self._leaderboard_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self._leaderboard_table.setSelectionMode(QTableWidget.NoSelection)
        self._leaderboard_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabs.addTab(self._leaderboard_table, "Leaderboard")

        self._history_table = QTableWidget(0, 6, self)
        self._history_table.setHorizontalHeaderLabels(
            ["#", "Cell", "Value", "Prev", "Correct", "Active"]
        )
        hist_header = self._history_table.horizontalHeader()
        hist_header.setSectionResizeMode(QHeaderView.Stretch)
        self._history_table.setSelectionMode(QTableWidget.NoSelection)
        self._history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabs.addTab(self._history_table, "Move History")

    def update_leaderboard(self, entries: Sequence[LeaderboardEntry]) -> None:
        self._leaderboard_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [
                entry.username,
                entry.difficulty.title(),
                format_duration(entry.elapsed_seconds),
                str(entry.moves),
                str(entry.correct),
                str(entry.wrong),
                str(entry.total_moves),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self._leaderboard_table.setItem(row, col, item)

    def update_history(self, moves: Sequence[Move]) -> None:
        self._history_table.setRowCount(len(moves))
        for row, move in enumerate(moves):
            cell_label = f"({move.row + 1},{move.col + 1})"
            values = [
                str(move.move_id),
                cell_label,
                str(move.current) if move.current else "",
                str(move.previous) if move.previous else "",
                "Yes" if move.added_correct else ("No" if move.added_wrong else ""),
                "Yes" if move.active else "No",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self._history_table.setItem(row, col, item)


__all__ = ["LEADERBOARD_PATH", "LeaderboardManager", "LeaderboardDialog"]
