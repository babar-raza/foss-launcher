# Aspose.Cells FOSS for Python

A library for reading and writing spreadsheet files in Python.

## Features

- Supports reading and writing XLSX spreadsheet files with full fidelity
- Handles large spreadsheets with streaming mode for memory efficiency
- Convert spreadsheets between XLSX, CSV, and other formats easily
- Provides a Workbook class for working with Excel workbooks
- Provides a Worksheet class for working with individual sheets

## Installation

```bash
pip install aspose-cells-foss
```

## Quick Start

```python
from aspose.cells import Workbook

wb = Workbook()
wb.load("input.xlsx")
ws = wb.worksheets[0]
ws.set_value("A1", "Hello, World!")
wb.save("output.xlsx")
```

## API Overview

Use the `Workbook` class to open and save Excel files. Use `Worksheet` to
access individual sheets within a workbook.
