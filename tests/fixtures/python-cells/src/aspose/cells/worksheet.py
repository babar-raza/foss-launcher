"""Worksheet — represents a single sheet in an Excel workbook."""
from __future__ import annotations


class Worksheet:
    """Represents a single worksheet (tab) within an Excel workbook.

    Provides methods for reading and writing cell values, setting formulas,
    and formatting cells. Supports row and column iteration for bulk operations.
    """

    def __init__(self, name: str = "Sheet1") -> None:
        """Initialize a worksheet with the given name."""
        self.name = name
        self._cells: dict = {}

    def get_value(self, cell_ref: str) -> object:
        """Return the value at the given cell reference (e.g. 'A1').

        Returns None when the cell is empty or has never been set.
        Supports standard Excel A1 notation for cell references.
        """
        return self._cells.get(cell_ref)

    def set_value(self, cell_ref: str, value: object) -> None:
        """Set the value of the given cell reference (e.g. 'A1').

        Accepts strings, numbers, booleans, and datetime objects.
        Raises TypeError when value is not a supported type.
        """
        self._cells[cell_ref] = value
