---
canonical: https://reference.aspose.org/cells/python/cells/
canonical_import: aspose.cells
code_import: aspose.cells
date: '2026-03-27T07:02:41Z'
dateModified: '2026-03-27T07:02:41Z'
datePublished: '2026-03-27T07:02:41Z'
description: The `Cell` class represents a single `cell` and exposes `properties`
  and methods to manipulate its `value`, `formula`, `style`, and `comment`.
display_name: Aspose.Cells FOSS
family: cells
keywords:
- cells python
- python cells in excel
- python cells vscode
- cell python docx
- cell python spyder
- aspose cells python
- code cells python
- voronoi cells python
lastmod: '2026-03-27T07:02:41Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS Cells
slug: cells
title: Cells
type: reference_object_page
url: /reference.aspose.org/cells/python/cells/
weight: 20
---

## Overview

The `Workbook` class represents an Excel workbook and provides methods to create, load, and manage `worksheets`, while `Cells` represents a collection of `cells` in a worksheet and enables access to individual `cells` by row/column indices or A1-`style` coordinates. The `Cell` class represents a single `cell` and exposes `properties` and methods to manipulate its `value`, `formula`, `style`, and `comment`.

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Test"
workbook.save("output.xlsx")
```

| Class | Methods | Properties |
|-------|---------|------------|
| `Workbook` | `add_worksheet()`, `get_worksheet()`, `remove_worksheet()`, `unprotect()`, `create_worksheet()` | `worksheets`, `file_path`, `properties`, `document_properties`, `protection` |
| `Cells` | `cell()`, `column_index_from_string()`, `column_letter_from_index()`, `coordinate_from_string()`, `coordinate_to_string()` | — |
| `Cell` | `is_empty()`, `clear_value()`, `clear_formula()`, `clear()`, `set_comment()` | `value`, `formula`, `style`, `comment`, `data_type` |
| `Chart` | `add_series()`, `add_axis()`, `copy()` | `type`, `title`, `category_data`, `show_legend`, `legend_position` |
| `ChartAxis` | `copy()` | — |
| `ChartCollection` | `add()`, `add_line()`, `add_bar()`, `add_pie()`, `add_area()` | `count` |
| `CSVHandler` | `save_csv()`, `save_csv_to_string()`, `load_csv()`, `load_csv_from_string()` | — |
| `JsonHandler` | `save_json()`, `save_json_to_dict()` | — |
| `MarkdownHandler` | `save_markdown()`, `save_markdown_to_string()` | — |

## Constructor

The `Cells` class represents a collection of `cells` in a worksheet and provides methods to access individual `cells` by row/column index or coordinate string. It includes static utility methods for converting between column letters, indices, and coordinate strings.

| Name | Type | Description |
|------|------|-------------|
| `__init__(worksheet)` | Constructor | Initializes a new instance of the `Cells` class for the specified worksheet. |
| `cell(row, column)` | Method | Accesses a `cell` by 1-based row and column index. |
| `column_index_from_string(column)` | Static method | Converts a column letter (e.g., "A") to a 0-based index. |
| `column_letter_from_index(column_index)` | Static method | Converts a 0-based column index to its letter representation. |
| `coordinate_from_string(coord)` | Static method | Parses a coordinate string (e.g., "A1") into (row, column) tuple (1-based). |
| `coordinate_to_string(row, column)` | Static method | Converts 1-based row and column indices to a coordinate string (e.g., "A1"). |

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
cells = worksheet.cells

# Access cell using coordinate string
cell = cells["A1"]
cell.value = "Test"

# Access cell using 1-based row/column index
cell = cells.cell(1, 1)
print(cell.value)
```

## Properties

The `Cells` class represents a collection of `cells` in a worksheet and provides access to individual `cells` via row and column indices. It exposes `properties` that describe the structure and state of the `cell` collection.

| Name | Type | Description |
|------|------|-------------|
| `count` | int | The total number of `cells` in the collection. |
| worksheet | `Worksheet` | The worksheet that contains this `cell` collection. |
| max_row | int | The highest row index (0-based) that contains a `cell`. |
| max_column | int | The highest column index (0-based) that contains a `cell`. |
| row_count | int | The number of rows in the collection. |
| column_count | int | The number of columns in the collection. |

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Test"
worksheet.cells["B2"].value = 100

cell_count = worksheet.cells.count
max_row = worksheet.cells.max_row
max_column = worksheet.cells.max_column

print(f"Cells: {cell_count}, Max Row: {max_row}, Max Col: {max_column}")
```

## Methods

The `Cells` class represents a collection of `cells` in a worksheet and provides methods to access, manipulate, and convert `cell` coordinates. It includes instance methods for `cell` access and static utility methods for coordinate conversions.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `cell(row, column)` | `Cell` | Accesses a `cell` by 1-based row and column index. |
| `column_index_from_string(column)` | `int` | Converts a column letter (e.g., "A") to a 0-based index. |
| `column_letter_from_index(column_index)` | `str` | Converts a 0-based column index to its letter representation (e.g., 0 → "A"). |
| `coordinate_from_string(coord)` | `Tuple[int, int]` | Parses a coordinate string (e.g., "A1") into (row, column) 1-based indices. |
| `coordinate_to_string(row, column)` | `str` | Converts 1-based row and column indices to a coordinate string (e.g., (1, 1) → "A1"). |

The `ChartAxis` class represents a chart axis (category, `value`, or series) and supports axis duplication via the `copy()` method.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `copy()` | `ChartAxis` | Creates a duplicate of the axis object. |

The `MarkdownHandler.save_markdown()` method is part of the public API and exports a workbook to a Markdown file.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `save_markdown(workbook, file_path, options)` | `None` | Saves the workbook to a Markdown file at the specified path. |
| `save_markdown_to_string(workbook, options)` | `str` | Exports the workbook to a Markdown string. |

```python
from aspose.cells import Workbook, MarkdownHandler

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Header"
worksheet.cells["A2"].value = "Data"

MarkdownHandler.save_markdown(workbook, "output.md", None)
```

## Example

The following example demonstrates creating a workbook, adding a worksheet using `create_worksheet()`, populating `cells`, and exporting to CSV using `CSVHandler.save_csv()`. This illustrates core workbook and `cell` operations in Aspose.Cells FOSS.

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()

# Create a new worksheet named 'Data'
worksheet = workbook.create_worksheet('Data')

# Access the Cells collection and set values
worksheet.cells['A1'].value = 'Product'
worksheet.cells['B1'].value = 'Sales'
worksheet.cells['A2'].value = 'Widget'
worksheet.cells['B2'].value = 1250

# Save the workbook as CSV
aspose.cells.CSVHandler.save_csv(workbook, 'output.csv')
```

## See Also

- [Install and set up Cells FOSS](/cells/python/cells-foss-python/)
- [Create all chart types in spreadsheets](/cells/python/create-charts-spreadsheets/)
- [Work with formulas in spreadsheets](/cells/python/developer-guide/formula-calculation/)
- [Perform common spreadsheet operations](/cells/python/developer-guide/spreadsheet-operations/)
- [Convert file formats easily](/cells/python/convert-csv-json-python/)
