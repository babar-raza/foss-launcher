---
canonical: https://reference.aspose.org/cells/python/cells/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: It is accessed via `Worksheet.cells` and integrates with the `Workbook`
  root object for file I/O and worksheet management.
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
seoTitle: '`cells` -- Cell collection with A1 and (row, col) access | Guide'
slug: cells
title: '`cells` -- Cell collection with A1 and (row, col) access'
type: reference_object_page
url: /reference.aspose.org/cells/python/cells/
weight: 20
---

## Overview

The `cells` module provides a collection of `Cell` objects representing spreadsheet cells, supporting both A1-style string keys and (row, col) integer indexing. It is accessed via `Worksheet.cells` and integrates with the `Workbook` root object for file I/O and worksheet management.

```python
import aspose_cells

wb = aspose.cells.Workbook()
ws = wb.worksheets[0]
ws.cells["A1"].value = "Revenue"
ws.cells[1, 1].value = 42
```

## Constructor

The `Cells` class provides a collection of `Cell` objects with both A1-style and (row, col)-style access. It is exposed as the `cells` property on `Worksheet` instances and supports indexing via string keys like "A1" or integer tuples like (0, 0).

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
cells = worksheet.cells
```

| Name | Type | Description |
|------|------|-------------|
| `cells` | `Cells` | `Cell` collection with A1 and (row, col) access |
| `SaveFormat` | Enum | Enum for controlling output format (XLSX, CSV, TSV, MARKDOWN, JSON) |

## Properties

The `cells` collection provides access to individual `Cell` objects via A1-style keys or (row, col) indices. Each `Cell` exposes formatting and content properties through its style and other read-only attributes.

| Name | Type | Description |
|------|------|-------------|
| `value` | str | The cell value (assign directly: `ws.cells["A1"].value = x`) |
| `formula` | str | The cell formula (assign directly: `ws.cells["A2"].formula = "=SUM(A1:A5)"`) |
| `style` | `Style` | Cell formatting: font, fill, borders, number format, alignment |
| `comment` | str | The cell comment |
| `data_type` | str | The cell data type |

## AutoFilter Properties

The `AutoFilter` object is accessed via `worksheet.auto_filter`. It provides properties to inspect and configure filtering behavior on a worksheet range.

| Property | Type | Description |
|----------|------|-------------|
| `range` | `str` | The cell range to which the auto filter is applied (e.g., "A1:D10"). |
| `filter_columns` | `list` | The list of column filter settings. |
| `sort_state` | `dict` | The current sort state configuration. |

## Example

The following example demonstrates basic cell manipulation and shape creation using Aspose.Cells FOSS. It sets cell values, applies font styling, and adds a rounded rectangle shape with text and fill formatting. This covers the `Cell` class for cell representation and the `Shape` class for drawing objects.

```python
from aspose_cells import Workbook, MsoDrawingType

# Create a new workbook and access the first worksheet
workbook = Workbook()
worksheet = workbook.worksheets[0]

# Set and style a cell
worksheet.cells["A1"].value = "Styled Cell"
style = worksheet.cells["A1"].get_style()
style.font.bold = True
style.font.color = "#FF0000"
worksheet.cells["A1"].apply_style(style)

# Add a rounded rectangle shape with text and fill
shape = worksheet.shapes.add(MsoDrawingType.ROUNDED_RECTANGLE, 1, 1, 5, 5)
shape.text = "Hello Shape"
shape.fill.fore_color = "90EE90"

# Save the workbook
workbook.save("example.xlsx")
```

## See Also

The `Cells` class represents a collection of cells in a worksheet and supports both A1-style and (row, col)-style access. Related classes include `Cell` for individual cell operations and `SparklineGroup` for managing sparkline visual styles.

- [Explore the API reference](/reference.aspose.org/cells/python/api-overview/)
- [Learn about conditional formatting](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Apply rules-based formatting](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
