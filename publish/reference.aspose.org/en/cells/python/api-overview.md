---
canonical: https://reference.aspose.org/cells/python/api-overview/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: '`Shape` -- Drawing shape with fill, line, text, and font formatting.'
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
page_role: api_reference
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS API Reference | Guide
slug: api-overview
title: Aspose.Cells FOSS API Reference
type: api_reference
url: /reference.aspose.org/cells/python/api-overview/
weight: 6
---

## Overview

Aspose.Cells FOSS is an open-source Python library for creating, reading, and modifying spreadsheet files without requiring Microsoft Excel. It supports XLSX, XLS, and CSV formats for input, and adds Markdown export via `save_as_markdown()`. The library is structured around a `Workbook` root object that manages worksheets, styles, charts, and I/O.

The core entry point is `Workbook`. Each `Workbook` contains one or more `Worksheet` objects accessed via `wb.worksheets[index]`. Individual cells are reached through the `Cells` collection using A1 notation or zero-based row/column indices.

```python
from aspose_cells import Workbook

wb = Workbook()
ws = wb.worksheets[0]
ws.cells["A1"].value = "Revenue"
ws.cells["B2"].value = 42
wb.save("output.xlsx")
```

## Workbook and Worksheet

The `Workbook` class is the root object for all spreadsheet operations. It handles file loading, saving, and access to worksheets and document properties.

```python
from aspose_cells import Workbook

wb = Workbook()                      # new workbook
wb = Workbook("input.xlsx")          # open existing file
wb = Workbook("protected.xlsx", password="secret")  # open encrypted file

ws = wb.worksheets[0]                # first worksheet (0-based)
ws = wb.worksheets.add("Sheet2")     # add a named worksheet

ws.cells["A1"].put_value("Hello")    # write by A1 reference
ws.cells["A1"].value                 # read value (property, no parentheses)
ws.cells["A2"].formula = "=SUM(B1:B5)"

wb.save("output.xlsx")               # save as XLSX
wb.save("output.csv")                # auto-detects format from extension
wb.save_as_markdown("output.md")     # export as Markdown table
wb.save("output.xlsx", password="secret")  # save with AES encryption
```

## Charts

Add charts to a worksheet using the `add_*` methods on `ws.charts`. Each method takes four positional arguments: `top_row`, `left_col`, `bottom_row`, `right_col`. Access the chart by index to set its title and data series.

```python
from aspose_cells import Workbook

wb = Workbook()
ws = wb.worksheets[0]
chart_idx = ws.charts.add_line(upper_left_row=0, upper_left_col=4,
                                lower_right_row=20, lower_right_col=12)
chart = ws.charts[chart_idx]
chart.title = "Monthly Sales"
chart.n_series.add("B2:B7", category_data="A2:A7", name="Sales")

# Other add methods: add_bar, add_pie, add_area, add_scatter,
# add_waterfall, add_combo, add_stock, add_surface, add_radar,
# add_treemap, add_sunburst, add_histogram, add_funnel,
# add_box_whisker, add_map
```

## Shapes

Add drawing shapes and text boxes to a worksheet using `ws.shapes`.

```python
from aspose_cells import Workbook
from aspose_cells import MsoDrawingType, TextAlignmentType, TextAnchorType

wb = Workbook()
ws = wb.worksheets[0]

shape = ws.shapes.add(MsoDrawingType.ROUNDED_RECTANGLE, 1, 1, 5, 5)
shape.text = "Hello"
shape.fill.fore_color = "90EE90"
shape.font.bold = True
shape.text_horizontal_alignment = TextAlignmentType.CENTER
shape.text_vertical_alignment = TextAnchorType.MIDDLE

textbox = ws.shapes.add_text_box(7, 1, 11, 8)
textbox.text = "Notes"
```

## Cell Values and Styles

Read and write cell values using the `.value` property (assignment syntax). Use `get_style()` / `apply_style()` to modify formatting.

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]

# Write values
worksheet.cells["A1"].value = "Hello"
worksheet.cells["B1"].value = "World"
worksheet.cells["A2"].value = 42
worksheet.cells["B2"].value = 3.14

# Read a value
value = worksheet.cells["A1"].value
print(f"Cell A1 contains: {value}")

# Apply a style
cell = worksheet.cells["A1"]
style = cell.get_style()
style.font.is_bold = True
style.font.size = 14
style.font.color = "FF0000"   # hex RRGGBB string (no # prefix)
style.horizontal_alignment = "center"
cell.apply_style(style)

workbook.save("output.xlsx")
```

Note: when setting `font.color`, use a hex string without a `#` prefix (e.g., `"FF0000"` for red). The `#` prefix breaks XML serialisation.

## Data Validation

Add dropdown or other validation rules to a cell range using `ws.data_validations`.

```python
from aspose_cells import Workbook, DataValidationType

workbook = Workbook()
worksheet = workbook.worksheets[0]

validation = worksheet.data_validations.add("A1:A10")
validation.type = DataValidationType.LIST
validation.formula1 = '"Option1,Option2,Option3"'

workbook.save("validation.xlsx")
```

## Encryption

Save or open password-protected workbooks:

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Confidential Data"

# Save with password protection
workbook.save("protected.xlsx", password="mypassword")

# Open a password-protected file
workbook2 = Workbook("protected.xlsx", password="mypassword")
```

## Public API

The `Cells` class provides access to individual cells using A1-style notation (e.g., `"A1"`) or zero-based row/column indices. The `Cell` class represents a single cell and exposes `value`, `formula`, and `style` as read/write properties. Merging and unmerging cells is supported via `merge()` and `unmerge()` methods.

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Hello"
worksheet.cells[0, 1].value = "World"
workbook.save("output.xlsx")
```

| Class | Description |
|-------|-------------|
| [`Cells`](#) | Cell collection with A1 and (row, col) access |
| [`Cell`](#) | Represents a single cell in a worksheet |
| [`AutoFilter`](#) | Represents auto filters in a worksheet |
| [`SparklineGroup`](#) | Group of sparklines sharing a visual style |
| [`CFBReader`](#) | Reads encrypted XLSX from CFB format |
| [`CFBWriter`](#) | Writes encrypted XLSX to CFB format |
| [`CSVHandler`](#) | Handles CSV import/export operations |
| [`CellValueHandler`](#) | Handles cell value import/export per ECMA-376 |
| [`AgileEncryptionParameters`](#) | Parameters for Agile encryption |
| [`Alignment`](#) | Text alignment settings |
| [`Border`](#) | Single border line formatting |
| [`Borders`](#) | Collection of border lines |
| [`AutoFilterXMLLoader`](#) | Loads auto filter XML |
| [`AutoFilterXMLWriter`](#) | Writes auto filter XML |
| [`CSVLoadOptions`](#) | Options for loading CSV files |
| [`CSVSaveOptions`](#) | Options for saving CSV files |
| [`CalculationProperties`](#) | Calculation settings for workbook |
| [`SaveFormat`](#) | Enum: AUTO, XLSX, CSV, TSV, MARKDOWN, JSON |

## Common Patterns

```python
# Styling a cell
cell = ws.cells["A1"]
style = cell.get_style()
style.font.is_bold = True
style.font.size = 14
style.font.color = "FF0000"    # red — correct (no # prefix)
style.horizontal_alignment = "center"
style.number_format = "#,##0.00"
style.borders["bottom"].line_style = "thin"
cell.apply_style(style)
```

```python
# Conditional formatting
cf = ws.conditional_formatting.add("A1:C10")
rule = cf.add_rule()
rule.type = "cellValue"
rule.operator = "greaterThan"
rule.formula1 = "100"
rule.style.font.color = "FF0000"
```

## See Also

- [Access cells by A1 or row-column](/reference.aspose.org/cells/python/cells/)
- [Cell properties: value, formula, style](/reference.aspose.org/cells/python/cell/)
- [Frequently asked questions](/kb.aspose.org/cells/python/faq/)
- [Common issues and fixes](/kb.aspose.org/cells/python/troubleshooting/)
