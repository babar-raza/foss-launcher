---
canonical: https://kb.aspose.org/cells/python/how-to-save-spreadsheets-python/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: Use `wb.save("output.xlsx")` to write a workbook to disk. The output
  format is inferred from the file extension. Use `wb.save_as_markdown("output.md")`
  to export tabular data as Markdown.
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
seoTitle: How to Save Files with Aspose.Cells FOSS | Guide
slug: how-to-save-spreadsheets-python
title: How to Save Files with Aspose.Cells FOSS
type: howto_article
url: /kb.aspose.org/cells/python/how-to-save-spreadsheets-python/
weight: 12
---

## Problem

Save a workbook created or modified with Aspose.Cells FOSS to disk in XLSX, CSV, or Markdown format. The `Workbook.save()` method writes the file and infers the format from the file extension. Use `save_as_markdown()` for Markdown export.

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells.get("A1").put_value("Product")
workbook.save("output.xlsx")
```

## Prerequisites

To use Aspose.Cells FOSS for saving files in Python, ensure your environment meets the following requirements.

- Python 3.7 or later installed on your system
- Install Aspose.Cells FOSS using: `pip install aspose-cells-foss>=26.3.1`
- Import the library with `from aspose_cells import Workbook` to access `Workbook` and `Worksheet` classes
- A valid workbook instance loaded from a file or created programmatically

## Saving the File

Aspose.Cells FOSS provides straightforward methods to save workbooks to various formats. Call `save()` on a `Workbook` instance with the desired output file path. The format is inferred from the extension: `.xlsx` produces an Excel Open XML file, `.csv` produces a comma-separated values file, and `.md` is not supported by `save()` — use `save_as_markdown()` instead.

```python
from aspose_cells import Workbook

# Load or create a workbook
workbook = Workbook("input.xlsx")

# Save as XLSX
workbook.save("output.xlsx")

# Save as CSV
workbook.save("output.csv")

# Export as Markdown
workbook.save_as_markdown("output.md")
```

## Code Example

This example creates a workbook, writes sample data using the correct `get().put_value()` pattern, and saves the result to both XLSX and Markdown formats.

```python
from aspose_cells import Workbook

# Create a new workbook and get the first worksheet
workbook = Workbook()
worksheet = workbook.worksheets[0]

# Populate sample data using the correct put_value pattern
worksheet.cells.get("A1").put_value("Product")
worksheet.cells.get("B1").put_value("Sales")
worksheet.cells.get("A2").put_value("Apples")
worksheet.cells.get("B2").put_value(120)
worksheet.cells.get("A3").put_value("Bananas")
worksheet.cells.get("B3").put_value(95)

# Save to XLSX
workbook.save("output.xlsx")

# Export to Markdown
workbook.save_as_markdown("output.md")

print("Saved output.xlsx and output.md")
```

## Output Options

Aspose.Cells FOSS supports saving workbooks to multiple formats. Format selection is determined by the file extension passed to `save()`, or by calling the dedicated `save_as_markdown()` method.

| Format | Method / Extension | Notes |
|--------|-------------------|-------|
| XLSX | `wb.save("file.xlsx")` | Default Excel Open XML format; supports styles, charts, and formulas |
| CSV | `wb.save("file.csv")` | Comma-separated values; single-sheet export |
| Markdown | `wb.save_as_markdown("file.md")` | Exports first worksheet as a Markdown table |

## See Also

- [Learn how to load files](/kb.aspose.org/cells/python/how-to-load-spreadsheets-python/)
- [Frequently asked questions](/kb.aspose.org/cells/python/faq/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
