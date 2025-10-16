import sys
import os

# ensure local package is importable when running tests from workspace root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sudoku.core import generate, solve


def test_generate_and_solve():
    board = generate('easy')
    # ensure there are zeros
    assert any(0 in row for row in board)
    bcopy = [row[:] for row in board]
    assert solve(bcopy) is True
    # now bcopy should have no zeros
    assert all(all(cell != 0 for cell in row) for row in bcopy)
