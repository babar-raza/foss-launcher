---
canonical: https://reference.aspose.org/cells/python/cell/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:46:42Z'
dateModified: '2026-03-11T11:46:42Z'
datePublished: '2026-03-11T11:46:42Z'
description: It exposes methods and properties to read and write value, `formula`,
  and style.
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
seoTitle: 'Cell provides methods: value, value, formula, formula, style | Guide'
slug: cell
title: 'Cell provides methods: value, value, formula, formula, style'
type: reference_object_page
url: /reference.aspose.org/cells/python/cell/
weight: 21
---

## Overview

The `Cell` class represents a single `cell` in a worksheet and provides access to its `core` attributes. It exposes methods and properties to read and write value, `formula`, and style.

| Name | Type | Description |
|------|------|-------------|
| value() | method | Gets or sets the `cell`'s value |
| `formula()` | method | Gets or sets the `cell`'s `formula` |
| style() | method | Gets the `cell`'s style |
| value | property | Read-only value of the `cell` |
| `formula` | property | Read-only `formula` of the `cell` |
| style | property | Read-only style of the `cell` |
| `comment` | property | Read-only `comment` of the `cell` |
| `data_type` | property | Read-only data type of the `cell` |
| put_value() | method | Sets the `cell`'s value |
| `get_style()` | method | Gets the `cell`'s style |
| `apply_style()` | method | Applies a style to the `cell` |

The `ChartAxis` class represents a chart axis (`category`, value, or series).

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Hello"
worksheet.cells["B1"].formula = "=A1"
```

## Constructor

The `Cell` class in Aspose.Cells FOSS represents a single `cell` in a worksheet. It provides methods to `get` and set the `cell`'s value, `formula`, and style. The constructor is not exposed directly; `cells` are obtained through the `Cells` collection of a worksheet.

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | Constructor is not public; `cells` are accessed via `worksheet.cells[index]` or `worksheet.cells[name]` |

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
cell = worksheet.cells["A1"]
```

## Properties

The `Cell` class exposes read-only properties that provide direct access to `core` `cell` attributes. These properties reflect the underlying data stored in the `cell` and are populated when the `cell` is retrieved from a worksheet.

| Name | Type | Description |
|------|------|-------------|
| value | str | The `cell` value. |
| `formula` | str | The `cell` `formula`. |
| style | `Style` | The `cell` style object. |
| `comment` | str | The `cell` `comment`. |
| `data_type` | str | The `cell` data type. |

## Methods

The `Cell` class exposes methods to `get` and set `core` `cell` properties. Each method corresponds directly to a read-only property and supports both retrieval and assignment via overloading.

| Method | Return Type | Description |
|--------|-------------|-------------|
| value() | str | Gets the `cell` value. |
| `value(val)` | None | Sets the `cell` value to val. |
| `formula()` | str | Gets the `cell` `formula`. |
| `formula(val)` | None | Sets the `cell` `formula` to val. |
| style() | `Style` | Gets the `cell` style. |

The `CFBWriter` class supports writing encrypted XLSX files in Compound File Binary (CFB) `format`. It is used internally when saving workbooks with encryption enabled.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `write(file_path, encryption_info_xml, encrypted_package, package_size)` | None | Writes encrypted XLSX content to the specified file path in CFB `format`. |

The `ChartView3D` class represents chart-level 3D view settings. It is used to configure perspective, rotation, and other 3D rendering parameters for supported chart types.

## Example

The following example demonstrates reading and writing `cell` properties using the `Cell` class. It sets a value and `formula`, then retrieves them along with the `cell`'s style. This uses only canonical imports and methods defined in the API surface.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set a cell value and formula
cell = worksheet.cells["A1"]
cell.value("Hello World")
cell.formula("=LEN(A1)")

# Retrieve cell properties
value = cell.value()
formula = cell.formula()
style = cell.style()

# Output results
print(f"Value: {value}")
print(f"Formula: {formula}")
print(f"Style type: {type(style).__name__}")
```

## See Also

- [Cfbreader: Reads encrypted XLSX from CFB format](/reference.aspose.org/cells/python/worksheet/)
- [Aspose.Cells FOSS API Reference](/reference.aspose.org/cells/python/api-overview/)
- [**conditional Formatting**: Apply rules-based formatting](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [**conditional Formatting**: Apply rules-based formatting](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with Formulas with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
