---
canonical: https://reference.aspose.org/cells/python/cell/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:46:42Z'
dateModified: '2026-03-11T11:46:42Z'
datePublished: '2026-03-11T11:46:42Z'
description: It exposes properties to read and write value, `formula`, and style,
  plus methods `put_value()`, `get_style()`, and `apply_style()`.
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
lastmod: '2026-03-11T11:46:42Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: 'Cell class: value, formula, style properties | Aspose.Cells FOSS Guide'
slug: cell
title: 'Cell: value, formula, and style'
type: reference_object_page
url: /reference.aspose.org/cells/python/cell/
weight: 21
---

## Overview

The `Cell` class represents a single cell in a worksheet and provides access to its core attributes. It exposes read/write properties for `value`, `formula`, and `style`, along with helper methods `put_value()`, `get_style()`, and `apply_style()`.

| Name | Kind | Description |
|------|------|-------------|
| `value` | property | Gets or sets the cell's value |
| `formula` | property | Gets or sets the cell's formula string |
| `style` | property | Gets the cell's `Style` object (read-only) |
| `comment` | property | Gets the cell's comment (read-only) |
| `data_type` | property | Gets the cell's data type (read-only) |
| `put_value(val)` | method | Sets the cell's value from a Python scalar |
| `get_style()` | method | Returns a mutable copy of the cell's style |
| `apply_style(style)` | method | Applies a modified `Style` object back to the cell |

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Hello"
worksheet.cells["B1"].formula = "=A1"
```

## Constructor

The `Cell` class constructor is not exposed publicly. Cells are obtained through the `Cells` collection of a worksheet using A1 notation or zero-based row/column indices.

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | Constructor is not public; cells are accessed via `worksheet.cells["A1"]` or `worksheet.cells[row, col]` |

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
cell = worksheet.cells["A1"]
```

## Properties

The `Cell` class exposes the following properties. `value` and `formula` are read/write; `style`, `comment`, and `data_type` are read-only (use `get_style()` / `apply_style()` to modify style).

| Name | Type | Read/Write | Description |
|------|------|-----------|-------------|
| `value` | object | read/write | The cell's current value (string, int, float, bool, datetime, or None) |
| `formula` | str | read/write | The cell's formula string, including the leading `=` |
| `style` | `Style` | read-only | The cell's style object; modify via `get_style()` / `apply_style()` |
| `comment` | str | read-only | The cell's comment text |
| `data_type` | str | read-only | The cell's data type identifier |

## Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `put_value(val)` | None | Sets the cell's value to the given scalar |
| `get_style()` | `Style` | Returns a mutable copy of the cell's style for editing |
| `apply_style(style)` | None | Applies a modified `Style` object to the cell |

## Example

The following example demonstrates reading and writing cell properties using the `Cell` class. Note that `value` and `formula` are properties accessed with assignment syntax, not method calls.

```python
from aspose_cells import Workbook

# Create a new workbook and access the first worksheet
workbook = Workbook()
worksheet = workbook.worksheets[0]

# Set a cell value using property assignment
cell_a1 = worksheet.cells["A1"]
cell_a1.value = "Hello World"

# Set a formula using property assignment
cell_b1 = worksheet.cells["B1"]
cell_b1.formula = "=LEN(A1)"

# Read cell properties using the property (no parentheses)
value = cell_a1.value
formula = cell_b1.formula

print(f"Value: {value}")
print(f"Formula: {formula}")

# Modify style via get_style / apply_style
style = cell_a1.get_style()
style.font.bold = True
style.font.size = 14
cell_a1.apply_style(style)

workbook.save("output.xlsx")
```

## See Also

- [Worksheet reference](/reference.aspose.org/cells/python/worksheet/)
- [Aspose.Cells FOSS API Reference](/reference.aspose.org/cells/python/api-overview/)
- [Work with Formulas with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
