---
canonical: https://kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: Convert a CSV file to JSON using Aspose.Cells FOSS. Load the CSV with
  `Workbook` and `LoadOptions(LoadFormat.CSV)`, iterate rows and cells to build a
  Python list of dicts, then write to JSON with `json.dump()`.
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
seoTitle: How to Convert CSV to JSON with Aspose.Cells FOSS | Guide
slug: how-to-convert-csv-to-json-python
title: How to Convert CSV to JSON with Aspose.Cells FOSS
type: howto_article
url: /kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/
weight: 13
---

## Problem

Convert a CSV file to JSON using Aspose.Cells FOSS in Python. Load the CSV with `Workbook` and `LoadOptions(LoadFormat.CSV)`, read each row and cell to build a Python list of dictionaries, then serialize to JSON using the standard `json` module.

## Prerequisites

To convert CSV to JSON using Aspose.Cells FOSS in Python, ensure your environment meets the following requirements.

- Python 3.7 or later installed
- Install Aspose.Cells FOSS via `pip install aspose-cells-foss>=26.3.1`
- Import the library using `from aspose_cells import Workbook, LoadOptions, LoadFormat`
- Basic familiarity with Python file handling and the standard `json` module

## Conversion Steps

### Step 1: Load the CSV File

Use the `Workbook` class with `LoadOptions(LoadFormat.CSV)` to load the CSV file. This initializes the in-memory representation of the spreadsheet data.

```python
from aspose_cells import Workbook, LoadOptions, LoadFormat

opts = LoadOptions(LoadFormat.CSV)
workbook = Workbook("data.csv", opts)
worksheet = workbook.worksheets[0]
```

### Step 2: Read Headers and Rows

Iterate over the worksheet cells to extract the header row and each data row. Use the `.value` property (not a method call) to read each cell's content.

```python
max_row = worksheet.cells.max_data_row + 1   # +1 because max_data_row is 0-based inclusive
max_col = worksheet.cells.max_data_column + 1

# Read the header row (row 0)
headers = []
for col in range(max_col):
    cell_val = worksheet.cells[0, col].value
    headers.append(str(cell_val) if cell_val is not None else f"col{col}")
```

### Step 3: Build a List of Dicts and Serialize to JSON

Iterate the remaining rows, build a dict per row keyed by the header names, then use `json.dump()` to write the JSON file.

```python
import json

rows = []
for row in range(1, max_row):
    record = {}
    for col in range(max_col):
        cell_val = worksheet.cells[row, col].value
        record[headers[col]] = cell_val
    rows.append(record)

with open("output.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, default=str)

print(f"Converted {len(rows)} rows to output.json")
```

## Code Example

The complete end-to-end example combining all three steps:

```python
import json
from aspose_cells import Workbook, LoadOptions, LoadFormat

# Step 1: Load CSV
opts = LoadOptions(LoadFormat.CSV)
workbook = Workbook("data.csv", opts)
worksheet = workbook.worksheets[0]

max_row = worksheet.cells.max_data_row + 1
max_col = worksheet.cells.max_data_column + 1

# Step 2: Extract headers from row 0
headers = []
for col in range(max_col):
    cell_val = worksheet.cells[0, col].value
    headers.append(str(cell_val) if cell_val is not None else f"col{col}")

# Step 3: Build list of dicts from remaining rows
rows = []
for row in range(1, max_row):
    record = {}
    for col in range(max_col):
        cell_val = worksheet.cells[row, col].value
        record[headers[col]] = cell_val
    rows.append(record)

# Step 4: Write JSON
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, default=str)

print(f"Converted {len(rows)} rows to output.json")
```

## Supported Formats

Aspose.Cells FOSS supports loading CSV files and exporting to JSON via the approach shown above. The library also supports direct save to other formats.

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV (input) | .csv | Load with `LoadOptions(LoadFormat.CSV)` |
| JSON (output) | .json | Built with Python `json.dump()` after iterating cells |
| XLSX (input/output) | .xlsx | Standard Excel Open XML format |
| Markdown (output) | .md | Use `wb.save_as_markdown("file.md")` |

## See Also

- [How to Fix Common Errors with Aspose.Cells FOSS](/kb.aspose.org/cells/python/how-to-fix-spreadsheets-errors-python/)
- [Aspose.Cells FOSS FAQ](/kb.aspose.org/cells/python/faq/)
- [Work with Formulas with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
