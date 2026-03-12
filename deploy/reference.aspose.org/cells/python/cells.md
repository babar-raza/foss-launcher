---
canonical: https://reference.aspose.org/cells/python/cells/
canonical_import: aspose_cells_foss
date: '2026-03-11T20:08:46Z'
dateModified: '2026-03-11T20:08:46Z'
datePublished: '2026-03-11T20:08:46Z'
description: It supports operations like merging, unmerging, and page break management,
  and integrates with the `Cell` class for per-cell data handling.
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
lastmod: '2026-03-11T20:08:46Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: 'Cells: Represents a collection of cells in a worksheet | Guide'
slug: cells
title: 'Cells: Represents a collection of cells in a worksheet'
type: reference_object_page
url: /reference.aspose.org/cells/python/cells/
weight: 21
---

## Overview

The `Cells` class represents a collection of cells in a worksheet and provides methods to access, modify, and manage individual cells and cell ranges. It supports operations like merging, unmerging, and page break management, and integrates with the `Cell` class for per-cell data handling.

```python
from aspose.cells import Workbook

wb = Workbook()
ws = wb.worksheets[0]
ws.cells["A1"].put_value("[identifier omitted]")
ws.cells["A1"].value
```

```python
ws.cells.merge(0, 0, 1, 3)
ws.cells.unmerge(0, 0, 1, 3)
```

```python
ws.horizontal_page_breaks.add(19)
ws.vertical_page_breaks.add(3)
ws.horizontal_page_breaks.remove(19)
ws.horizontal_page_breaks.clear()
```

| Name | Type | [identifier omitted] |
|------|------|-------------|
| comment | Comment (read-only) | Gets the comment associated with the cell. |
| `coordinate_to_string(row, col)` | `str` | Converts row and column (1-based) to an A1 coordinate string. |

## Constructor

The `Cells` class represents a collection of cells in a worksheet. It provides access to individual cells via indexers and supports iteration over rows using iter_rows().

| Name | Type | [identifier omitted] |
|------|------|-------------|
| worksheet | Worksheet | The parent worksheet containing the cells collection |
| count | `int` | The number of cells in the collection |
| item(int) | `Cell` | Gets the cell at the specified index |
| item(str) | `Cell` | Gets the cell at the specified address (e.g., "A1") |
| iter_rows() | generator | Iterates over rows in the worksheet |
| get_cell(int, int) | `Cell` | Gets the cell at the specified row and column index |
| put_value(int, int, object) | `None` | Sets the value of the cell at the specified row and column |
| clear(int, int) | `None` | Clears the content of the cell at the specified row and column |
| copy(`Cells`) | `None` | Copies cells from another `Cells` collection |
| get_range(str) | Range | Gets the range object for the specified address |
| get_used_range(bool) | Range | Gets the range of used cells |
| get_cell(int, int) | `Cell` | Gets the cell at the specified row and column index |
| set_row_height(int, float) | `None` | Sets the height of the specified row |
| set_column_width(int, float) | `None` | Sets the width of the specified column |
| get_row_height(int) | `float` | Gets the height of the specified row |
| get_column_width(int) | `float` | Gets the width of the specified column |

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
cells = worksheet.cells
```

## Properties

The `Cells` class exposes properties that provide access to worksheet-level cell collections and iteration mechanisms. [identifier omitted] properties support standard operations for navigating and manipulating cell data in a worksheet.

| Name | Type | [identifier omitted] |
|------|------|-------------|
| cell | method | Accesses a cell by row and column (1-based). |
| iter_cols | method | Iterates over columns in the worksheet. |
| count | int | Returns the total number of cells in the collection. |
| worksheet | Worksheet | Returns the parent worksheet containing this cell collection. |

## Methods

| [identifier omitted] | Return Type | [identifier omitted] |
|--------|-------------|-------------|
| `column_index_from_string(column_letter)` | int | Converts a column letter to a 1-based index. |
| count() | int | Gets the number of cells in the collection. |

## Example

The following example demonstrates two key operations on the `Cells` collection: converting a 1-based column index to its letter equivalent using column_letter_from_index(), and clearing all cell contents in the collection using clear(). This illustrates direct manipulation of the `Cells` object within a worksheet.

```python
import aspose.cells

wb = aspose.cells.Workbook()
ws = wb.worksheets[0]

# Write sample data to columns A–C
ws.cells["A1"].put_value("Name")
ws.cells["B1"].put_value("Age")
ws.cells["C1"].put_value("[identifier omitted]")

# Convert 1-based column index to letter
letter = aspose.cells.Cells.column_letter_from_index(2)  # returns "B"

# Clear all cells in the worksheet
cells = ws.cells
cells.clear()

# Verify: column_letter_from_index returns "B" for index 2
assert letter == "B"
# Verify: all cell contents are cleared
assert cells.count == 0
```

## See Also

The `Cells` class provides methods to work with cell collections in a worksheet. Use coordinate_from_string() to parse A1-style references into (row, column) tuples, and get_cell_by_name() to retrieve a cell by its defined name reference.

- [Chart: Represents a chart in a worksheet](/reference.aspose.org/cells/python/chart/)
- [**workbook & Worksheet Protection**: Protect workbook structure and individua...](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [**workbook & Worksheet Protection**: Protect workbook structure and individua...](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with Formulas with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Spreadsheet Operations with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
