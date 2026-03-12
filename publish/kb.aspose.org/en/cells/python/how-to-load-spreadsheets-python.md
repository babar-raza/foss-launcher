---
canonical: https://kb.aspose.org/cells/python/how-to-load-spreadsheets-python/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: The `Workbook` class loads spreadsheet files from disk or stream. Pass
  a file path to load XLSX or XLS files directly, or use `LoadOptions` with `LoadFormat.CSV`
  to load CSV files.
display_name: Aspose.Cells FOSS
family: cells
keywords:
- python
- python openpyxl
- openpyxl pandas
- openpyxl in python
- openpyxl documentation
- install openpyxl
- openpyxl cell
- openpyxl pip
lastmod: '2026-03-11T11:59:24Z'
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Load Files with Aspose.Cells FOSS | Guide
slug: how-to-load-spreadsheets-python
title: How to Load Files with Aspose.Cells FOSS
type: howto_article
url: /kb.aspose.org/cells/python/how-to-load-spreadsheets-python/
weight: 11
---

## Problem

Load spreadsheet files (XLSX, XLS, CSV) into Aspose.Cells FOSS for programmatic manipulation. The `Workbook` class accepts a file path or a file-like stream and returns an in-memory workbook ready for reading or editing.

```python
from aspose_cells import Workbook

# Load an XLSX file
workbook = Workbook("input.xlsx")
worksheet = workbook.worksheets[0]
```

## Prerequisites

To load files using Aspose.Cells FOSS in Python, ensure you have Python 3.7 or later installed. Install the library using pip with the command `pip install aspose-cells-foss>=26.3.1`. After installation, import the library using `from aspose_cells import Workbook`.

- Python 3.7 or later
- pip package manager
- aspose-cells-foss>=26.3.1 installed via pip
- Basic understanding of Python file handling

## Loading the File

Aspose.Cells FOSS loads spreadsheet data from file paths or streams using the `Workbook` class. Pass a local file path directly to the constructor, or provide a file-like object (e.g., `io.BytesIO`) for in-memory loading. To load CSV files, use `LoadOptions` together with `LoadFormat.CSV`.

```python
from aspose_cells import Workbook

# Load from file path (XLSX or XLS)
workbook = Workbook("data.xlsx")

# Load from stream (e.g., BytesIO)
import io
with open("data.xlsx", "rb") as f:
    stream = io.BytesIO(f.read())
    workbook = Workbook(stream)
```

When loading CSV files, pass a `LoadOptions` object set to `LoadFormat.CSV` as the second argument to the `Workbook` constructor.

## Code Example

This example demonstrates loading an XLSX file and a CSV file, then reading a cell value from each.

```python
from aspose_cells import Workbook, LoadOptions, LoadFormat

# Load an XLSX workbook from a file path
workbook = Workbook("input.xlsx")
worksheet = workbook.worksheets[0]

# Read a cell value using the .value property
val = worksheet.cells["A1"].value
print(f"A1 value: {val}")

# Load a CSV file using LoadOptions
opts = LoadOptions(LoadFormat.CSV)
csv_workbook = Workbook("data.csv", opts)
csv_worksheet = csv_workbook.worksheets[0]

# Read from the CSV-sourced workbook
csv_val = csv_worksheet.cells["A1"].value
print(f"CSV A1 value: {csv_val}")
```

## Supported Formats

Aspose.Cells FOSS supports loading files in several common spreadsheet and data interchange formats. All supported formats can be loaded via the `Workbook` class constructor.

| Format | Extension | Notes |
|--------|-----------|-------|
| Excel 2007–2019 | .xlsx | Standard Office Open XML format |
| Excel 97–2003 | .xls | Binary BIFF format |
| CSV | .csv | Comma-separated values; use `LoadOptions(LoadFormat.CSV)` |

## See Also

- [How to Save Files with Aspose.Cells FOSS](/kb.aspose.org/cells/python/how-to-save-spreadsheets-python/)
- [Aspose.Cells FOSS FAQ](/kb.aspose.org/cells/python/faq/)
- [Work with Formulas with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
