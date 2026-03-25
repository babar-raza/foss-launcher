---
canonical: https://docs.aspose.org/cells/python/developer-guide/formula-calculation/
canonical_import: aspose.cells
date: '2026-03-23T13:16:22Z'
dateModified: '2026-03-23T13:16:22Z'
datePublished: '2026-03-23T13:16:22Z'
description: Developers use the `Workbook` class to manage spreadsheets and the `Cell`
  class to read or write `values` and formulas at specific coordinates.
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
page_role: workflow_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Work with Formulas with Aspose.Cells FOSS | Guide
slug: formula-calculation
title: Work with Formulas with Aspose.Cells FOSS
type: workflow_page
url: /docs.aspose.org/cells/python/developer-guide/formula-calculation/
weight: 19
---

## Overview

Aspose.Cells FOSS enables programmatic manipulation of Excel workbooks and `cells` in Python. Developers use the `Workbook` class to manage spreadsheets and the `Cell` class to read or write `values` and formulas at specific coordinates.

The library supports core spreadsheet operations including `formula` evaluation, `cell` styling, and chart creation using only the documented API surface: `Workbook`, `Cell`, `Cells`, `Chart`, and related handlers like `CSVHandler`, `JsonHandler`, and `MarkdownHandler`.

## Core Concepts

Aspose.Cells FOSS provides core classes for working with Excel workbooks and their components in Python. The `Workbook` class serves as the primary entry point for loading, creating, and managing spreadsheet files, while `Worksheet`, `Cells`, and `Cell` enable granular access to individual elements.

Formula handling relies on the `Cell` class, where the `formula` property allows setting and retrieving formulas, and `value` stores computed results. The `Cells` collection provides indexed access to `cells` using 1-based row/column coordinates via the `cell(row, column)` method.

`Chart` creation and manipulation are supported through `Chart`, `ChartCollection`, and `ChartSeries` classes. Charts are added to a worksheet using methods like `add_line()` or `add_bar()` on the `ChartCollection`, and series data is configured using `add_series()` with explicit `value` and category inputs.

Data import/export operations use dedicated handler classes: `CSVHandler` for CSV, `JsonHandler` for JSON, and `MarkdownHandler` for Markdown formats. These static methods operate directly on `Workbook` instances to serialize or deserialize content without intermediate objects.

## Implementation

Aspose.Cells FOSS enables programmatic `formula` handling in Excel files using the `Workbook` and `Cell` classes. Developers can set, read, and `clear` formulas on individual `cells` via the `formula` property and related methods.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set a formula in cell A1
worksheet.cells.cell(0, 0).formula = "=SUM(B1:B5)"

# Save the workbook
workbook.save("output.xlsx")
```

To evaluate or inspect a `cell`'s `formula`, access the `formula` property directly. Use `clear_formula()` to `remove` the `formula` while preserving the `cell`'s `value`.

```python
import aspose.cells

workbook = aspose.cells.Workbook("input.xlsx")
worksheet = workbook.worksheets[0]

# Read the formula from cell C1
formula = worksheet.cells.cell(0, 2).formula

# Clear the formula but keep the calculated value
worksheet.cells.cell(0, 2).clear_formula()

workbook.save("output.xlsx")
```

The `Cells` class provides utility methods for coordinate conversions, such as `column_index_from_string()` and `coordinate_from_string()`, which help map Excel-`style` references (e.g., "A1") to row/column indices used in the API.

```python
import aspose.cells

# Convert Excel column letter to 1-based index
col_index = aspose.cells.Cells.column_index_from_string("C")

# Convert row/column to Excel coordinate string
coord = aspose.cells.Cells.coordinate_to_string(5, 3)

print(f"Column C → index {col_index}")
print(f"Row 5, Column 3 → {coord}")
```

## Code Examples

Aspose.Cells FOSS enables programmatic manipulation of Excel workbooks and cells in Python. Using the `Workbook` and `Cell` classes, developers can create, read, and modify formulas and values directly in spreadsheet data.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set a formula in cell A1
worksheet.cells.cell(0, 0).formula = "=10+20"

# Save the workbook
workbook.save("output.xlsx")
```

The `Cells` collection provides methods to access cells by row/column indices or coordinate strings. Use `cell(row, column)` with 1-based indexing to retrieve a `Cell` instance and set its `formula` property.

```python
import aspose.cells

# Load a workbook from file
workbook = aspose.cells.Workbook("input.xlsx")
worksheet = workbook.worksheets.get_worksheet(0)

# Read and update a formula in cell B2
cell = worksheet.cells.cell(1, 1)
cell.formula = "=A1*B1"

# Save changes
workbook.save("updated.xlsx")
```

## See Also

- [Install and set up Cells FOSS](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Create all chart types in spreadsheets](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Perform core spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
- [Convert files between formats](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
- [Resolve common errors and issues](/kb.aspose.org/cells/python/how-to-fix-spreadsheets-errors-python/)
