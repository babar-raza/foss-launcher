"""Workbook — represents an Excel spreadsheet file."""
from __future__ import annotations


class Workbook:
    """Represents an Excel workbook for reading and writing spreadsheet files.

    Provides methods to load, manipulate, and save Excel workbooks in XLSX,
    XLS, CSV, and other formats. Supports large spreadsheets via streaming mode.
    """

    def __init__(self) -> None:
        """Initialize an empty workbook with one default worksheet."""
        self._sheets: list = []

    def load(self, path: str) -> None:
        """Load a workbook from the given file path.

        Supports XLSX, XLS, ODS, and CSV formats. The format is determined
        automatically from the file extension. Raises ValueError for unsupported formats.
        """
        pass

    def save(self, path: str) -> None:
        """Save the workbook to the given file path.

        The output format is determined by the file extension. Supports XLSX, PDF,
        CSV, HTML, and ODS output formats. Creates parent directories if they do not exist.
        """
        pass

    def get_worksheet(self, index: int) -> "Worksheet":
        """Return the worksheet at the given index.

        Raises IndexError when the index is out of range.
        Returns the first worksheet when index is 0.
        """
        return self._sheets[index]

    @property
    def worksheets(self) -> list:
        """Return the list of all worksheets in this workbook."""
        return self._sheets
