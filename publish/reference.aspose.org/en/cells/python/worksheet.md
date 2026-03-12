---
canonical: https://reference.aspose.org/cells/python/worksheet/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: Worksheet represents a single sheet in an Aspose.Cells FOSS Workbook.
  It provides access to cells, charts, shapes, and auto-filter controls for that sheet.
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
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: 'Worksheet — Single sheet access for cells, charts, and filters | Guide'
slug: worksheet
title: 'Worksheet — Single sheet in an Aspose.Cells FOSS Workbook'
type: reference_object_page
url: /reference.aspose.org/cells/python/worksheet/
weight: 22
---

## Overview

`Worksheet` represents a single sheet within a `Workbook`. It provides access to the cell collection, chart collection, picture collection, shapes collection, and the auto-filter for that sheet. Worksheets are accessed by index or name from `workbook.worksheets`.

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]

worksheet.cells["A1"].value = "Hello"
worksheet.cells["A2"].formula = "=A1"
workbook.save("output.xlsx")
```

## Properties

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | The worksheet tab name. Assign to rename the sheet. |
| `cells` | `Cells` | The cell collection for this sheet. Supports A1-style and (row, col) indexing. |
| `charts` | `ChartCollection` | The collection of charts embedded in this sheet. |
| `shapes` | collection | The collection of shapes (text boxes, pictures, rectangles, etc.) in this sheet. |
| `auto_filter` | `AutoFilter` | The auto-filter object for this sheet. Use `auto_filter.range` to set the filter range. |

## Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `protect(password=None)` | `None` | Password-protects the worksheet, preventing edits. |
| `unprotect(password=None)` | `None` | Removes protection from the worksheet. |

## Example

The following example creates a worksheet, sets values and a formula, applies a style to a header cell, and saves the workbook.

```python
from aspose_cells import Workbook

workbook = Workbook()
ws = workbook.worksheets[0]
ws.name = "Sales"

# Set header and data values
ws.cells["A1"].value = "Month"
ws.cells["B1"].value = "Revenue"
ws.cells["A2"].value = "January"
ws.cells["B2"].value = 12500
ws.cells["A3"].value = "February"
ws.cells["B3"].value = 14800

# Add a SUM formula
ws.cells["B4"].formula = "=SUM(B2:B3)"

# Apply bold styling to the header row
style = ws.cells["A1"].get_style()
style.font.bold = True
ws.cells["A1"].apply_style(style)
style2 = ws.cells["B1"].get_style()
style2.font.bold = True
ws.cells["B1"].apply_style(style2)

workbook.save("sales_report.xlsx")
```

## See Also

- [Access cell data and formulas](/reference.aspose.org/cells/python/cell/)
- [Apply conditional formatting rules](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Work with spreadsheet formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform core spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
