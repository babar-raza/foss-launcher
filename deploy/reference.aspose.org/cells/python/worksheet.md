---
canonical: https://reference.aspose.org/cells/python/worksheet/
canonical_import: aspose.cells
date: '2026-03-23T13:16:22Z'
dateModified: '2026-03-23T13:16:22Z'
datePublished: '2026-03-23T13:16:22Z'
description: It is accessed through the `Cells` collection of a worksheet.
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
lastmod: '2026-03-23T13:16:22Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: 'Cell: Represents a single cell in a worksheet | Guide'
slug: worksheet
title: 'Cell: Represents a single cell in a worksheet'
type: reference_object_page
url: /reference.aspose.org/cells/python/worksheet/
weight: 22
---

## Overview

The `Cell` class represents a single `cell` in a worksheet and provides methods to read or `modify` its `value`, `formula`, `style`, and `comment`. It is accessed through the `Cells` collection of a worksheet.

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
cell = worksheet.cells["A1"]
cell.value = "Hello, World!"
workbook.save("output.xlsx")
```

| Method | Description |
|--------|-------------|
| `is_empty()` | Checks if the `cell` is empty. |
| `clear_value()` | Clears the `value` of the `cell` (sets it to None). |
| `clear_formula()` | Clears the `formula` of the `cell`. |
| `clear()` | Clears the `cell` (`value`, `formula`, `style`). |
| `set_comment(text, author, width, height)` | Sets a `comment` on the `cell`. |

| Property | Type | Description |
|----------|------|-------------|
| `value` | Any | Gets or sets the `cell` `value`. |
| `formula` | str | Gets or sets the `cell` `formula`. |
| `style` | `Style` | Gets or sets the `cell` `style`. |
| `comment` | Comment | Gets the `cell` `comment` (read-only). |
| `data_type` | [identifier omitted] | Gets the `cell` data `type` (read-only). |

## Constructor

The `Cell` class represents a single `cell` in a worksheet. Instantiate a `Cell` by accessing it through the `Cells` collection of a worksheet using 1-based row and column indices.

```python
import aspose.cells

wb = aspose.cells.Workbook()
ws = wb.worksheets[0]
cell = ws.cells.cell(1, 1)  # 1-based row, column
cell.value = "Hello, World!"
print(cell.value)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| row | int | 1-based row index |
| column | int | 1-based column index |
| `cells` | `Cells` | Parent `Cells` collection |
| worksheet | `Worksheet` | Parent worksheet |
| workbook | `Workbook` | Parent workbook |

## Properties

The `Cell` class exposes `properties` that define its content, formatting, and metadata. These `properties` allow reading and writing `values`, formulas, styles, and comments. All property access is read-write except where explicitly marked as read-only.

| Name | Type | Description |
|------|------|-------------|
| `value` | object | The `cell` `value` (string, number, boolean, or None). |
| `formula` | str | The `cell` `formula` (e.g., "=A1+B1"). |
| `style` | `Style` | The `cell` `style` object. |
| `comment` | str | The `cell` `comment` text (read-only). |
| `data_type` | CellValueType | The data `type` of the `cell` `value` (read-only). |

```python
import aspose.cells

wb = aspose.cells.Workbook()
ws = wb.worksheets[0]
cell = ws.cells["A1"]
cell.value = 42
cell.formula = "=A1*2"
print(cell.data_type)
```

## Methods

The `Cell` class provides methods to inspect and `modify` individual `cell` contents in a worksheet. Methods include checking emptiness, clearing `values` or formulas, and setting comments.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `is_empty()` | bool | Checks if the `cell` is empty. |
| `clear_value()` | None | Clears the `value` of the `cell` (sets it to None). |
| `clear_formula()` | None | Clears the `formula` of the `cell`. |
| `clear()` | None | Clears the `value` and `formula` of the `cell`. |
| `set_comment(text, author, width, height)` | None | Sets a `comment` on the `cell` with optional author, width, and height. |

The `Chart` class supports adding data series and `axes` to `charts`. Use `add_series()` to plot data and `add_axis()` to define chart `axes`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `add_series(values, category_data, name, chart_type, x_values)` | None | Convenience method to `add` a series to the chart. |
| `add_axis(axis_type, axis_id)` | `ChartAxis` | Adds an axis to the chart and returns it. |
| `copy()` | `Chart` | Copies the chart to a new instance. |

The `JsonHandler` class enables exporting workbooks to JSON format. Use `save_json()` to write to a file or `save_json_to_dict()` to obtain a dictionary for further processing.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `save_json(workbook, file_path: str, options: Optional[JsonSaveOptions])` | None | Saves a workbook to a JSON file. |
| `save_json_to_dict(workbook, options: Optional[JsonSaveOptions])` | Dict[str, Any] | Converts a workbook to a JSON-serializable dictionary. |

```python
import aspose.cells

wb = aspose.cells.Workbook()
ws = wb.worksheets[0]
ws.cells['A1'].value = 'Hello'
ws.cells['A2'].value = 'World'

# Save to JSON file
aspose.cells.JsonHandler.save_json(wb, 'output.json')

# Convert to dictionary
json_dict = aspose.cells.JsonHandler.save_json_to_dict(wb)
print(json_dict['worksheets'][0]['name'])
```

## Example

The following example demonstrates creating a workbook, adding data to a `cell`, and exporting the workbook to JSON using Aspose.Cells FOSS. It uses the canonical import path and covers both `JsonHandler.save_json_to_dict()` and `ChartAxis` functionality through related API surface.

```python
import aspose.cells

# Create a new workbook
wb = aspose.cells.Workbook()
ws = wb.worksheets[0]

# Add data to a cell
ws.cells['A1'].value = 'Product'
ws.cells['A2'].value = 'Sales'
ws.cells['B1'].value = 'Q1'
ws.cells['B2'].value = 1500

# Export workbook to JSON dictionary
json_dict = aspose.cells.JsonHandler.save_json_to_dict(wb)

# Verify structure
assert 'worksheets' in json_dict
assert len(json_dict['worksheets']) > 0
assert 'data' in json_dict['worksheets'][0]

print('JSON export successful')
```

## See Also

The `Cell` class represents a single `cell` in a worksheet. Related classes include those for managing collections of `cells`, `charts`, and workbook-level operations.

```python
import aspose.cells

# Create a new workbook and access a cell
wb = aspose.cells.Workbook()
ws = wb.worksheets[0]
cell = ws.cells.cell(0, 0)  # 1-based indexing
cell.value = "Hello, World!"
print(cell.value)
```

- [Install and set up Cells FOSS](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Create all chart types in spreadsheets](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas in spreadsheets](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
- [Convert file formats easily](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
