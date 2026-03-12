---
canonical: https://docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: This page covers essential data operations including reading and writing
  cell values and formulas via the `Cell` class, applying alignment and border...
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
lastmod: '2026-03-11T21:00:43Z'
page_role: workflow_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Spreadsheet Operations with Aspose.Cells FOSS | Guide
slug: spreadsheet-operations
title: Spreadsheet Operations with Aspose.Cells FOSS
type: workflow_page
url: /docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/
weight: 18
---

## Overview

Aspose.Cells FOSS enables Python developers to perform core spreadsheet operations on Excel files using a clean, object-oriented API. This page covers essential data operations including reading and writing cell values and formulas via the `Cell` class, applying alignment and border formatting, managing auto filters with `AutoFilter`, and handling CSV import/export through `CSVHandler`. The API surface supports [identifier omitted]-376-compliant cell value handling via `CellValueHandler` and Agile encryption parameters via `AgileEncryptionParameters`.

## Working with Data

Aspose.Cells FOSS provides core data manipulation capabilities through the `Cell`, `AutoFilter`, and `CSVHandler` classes. [identifier omitted] can read and write cell values and formulas, apply alignment and styling, and filter or export data using CSV formats.

### Reading and Writing `Cell` [identifier omitted]

Use the `Cell` class to access or assign cell content. The value() method retrieves the current value, while `value(val)` sets it. [identifier omitted] are handled similarly via formula() and `formula(val)`. The data_type property indicates the stored type.

```python
import aspose.cells

workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]
cell = worksheet.cells.get("A1")
cell.value("[identifier omitted], [identifier omitted]!")
print(cell.value())
```

### Applying `Alignment` and [identifier omitted]

`Alignment` settings are applied via the `Alignment` class and assigned to a cell's style. Horizontal and vertical alignment options include left, center, right, justify, and distributed. Use set_horizontal_alignment() and set_vertical_alignment() on the cell's style object.

```python
import aspose.cells

workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]
cell = worksheet.cells.get("B2")
cell.style.set_horizontal_alignment("center")
cell.style.set_vertical_alignment("center")
workbook.save("aligned.xlsx")
```

### Filtering and Exporting Data

The `AutoFilter` class enables filtering on worksheet ranges. Use filter_columns() to inspect active filters and filter() to apply criteria. For data export, `CSVHandler.save_csv()` writes the workbook to CSV format, supporting optional `CSVSaveOptions`.

```python
import aspose.cells

workbook = aspose.cells.Workbook("input.xlsx")
worksheet = workbook.worksheets[0]
auto_filter = worksheet.auto_filter
auto_filter.filter(0, "=[identifier omitted]")
aspose.cells.CSVHandler.save_csv(workbook, "output.csv", None)
```

## Code Examples

Aspose.Cells FOSS enables core spreadsheet operations in Python, including reading, writing, and manipulating cell data, styles, and autofilters. [identifier omitted] the Workbook, Worksheet, `Cell`, Style, and `AutoFilter` classes, developers can build robust data workflows for Excel-compatible formats.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Write a value and formula to cells
worksheet.cells.get("A1").value = "[identifier omitted]"
worksheet.cells.get("A2").formula = "=B1+B2"

# Apply horizontal center alignment to A1
style = worksheet.cells.get("A1").style
style.set_horizontal_alignment("center")
worksheet.cells.get("A1").style = style

# Save the workbook
workbook.save("output.xlsx")
```

```python
import aspose.cells

# Load an existing workbook
workbook = aspose.cells.Workbook("input.xlsx")
worksheet = workbook.worksheets[0]

# Apply an autofilter to a range
autofilter = worksheet.auto_filter
autofilter.range = "A1:D10"

# Filter column 2 (B) for values equal to 'Active'
autofilter.filter(1, "[identifier omitted]")

# Save the filtered workbook
workbook.save("filtered_output.xlsx")
```

## Notes and Best Practices

When using Aspose.Cells FOSS for spreadsheet operations in Python, prioritize memory efficiency and correct resource handling, especially when processing large workbooks or integrating with tools like openpyxl or pandas. The Workbook and Worksheet classes manage internal resources that require explicit cleanup to avoid leaks.

- Call `Workbook.dispose()` after completing all operations to release unmanaged resources and prevent memory leaks.
- Avoid holding multiple Workbook instances simultaneously; reuse or dispose of them promptly in long-running processes.
- For batch operations, process files sequentially rather than loading all into memory at once, especially when working with large datasets typical in openpyxl or pandas workflows.
- When saving files, prefer `Workbook.save()` with explicit file paths over in-memory streams unless streaming is strictly required.

## See Also

Aspose.Cells FOSS provides core spreadsheet operations through classes like Workbook, Worksheet, `Cell`, Style, `Alignment`, `Borders`, and `AutoFilter`. For data import/export, use `CSVHandler` with `CSVLoadOptions` and `CSVSaveOptions`. Encryption workflows leverage `AgileEncryptionParameters`, `CFBReader`, and `CFBWriter`. `Cell` value handling follows [identifier omitted]-376 via `CellValueHandler`.

- [The library supports adding and managing cell comments with author and rich text](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [The library supports workbook and worksheet protection](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with Formulas with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [How to Convert File Formats with Aspose.Cells FOSS](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
- [How to Fix Common Errors with Aspose.Cells FOSS](/kb.aspose.org/cells/python/how-to-fix-spreadsheets-errors-python/)
