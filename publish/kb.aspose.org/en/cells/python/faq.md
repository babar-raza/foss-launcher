---
canonical: https://kb.aspose.org/cells/python/faq/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: Frequently asked questions about Aspose.Cells FOSS for Python — installation,
  reading cell values, saving formats, adding charts, and common API mistakes.
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
page_role: faq
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS FAQ | Guide
slug: faq
title: Aspose.Cells FOSS FAQ
type: faq
url: /kb.aspose.org/cells/python/faq/
weight: 8
---

## Frequently Asked Questions

### How do I install Aspose.Cells FOSS?

Install it from PyPI using pip:

```python
pip install aspose-cells-foss>=26.3.1
```

After installation, verify it works:

```python
from aspose_cells import Workbook
wb = Workbook()
print("Installation successful")
```

### How do I read a cell value?

Use the `.value` property — it is a property, not a method. Do not add parentheses.

```python
from aspose_cells import Workbook

wb = Workbook("input.xlsx")
ws = wb.worksheets[0]

# Correct: .value is a property (no parentheses)
val = ws.cells["A1"].value
print(val)

# Also correct: access by row, column index (0-based)
val2 = ws.cells[0, 0].value
print(val2)
```

### How do I write a cell value or formula?

Assign to `.value` or `.formula` directly. Both are properties, not methods.

```python
from aspose_cells import Workbook

wb = Workbook()
ws = wb.worksheets[0]

# Write a value
ws.cells["A1"].value = "Product"
ws.cells["B1"].value = 100

# Write a formula
ws.cells["C1"].formula = "=SUM(A1:B1)"

wb.save("output.xlsx")
```

Alternatively, use `cells.get(address).put_value(value)` when you have a string cell address:

```python
ws.cells.get("A1").put_value("Product")
ws.cells.get("B1").put_value(100)
```

### Does Aspose.Cells FOSS support PDF export?

No. PDF export is not available in the FOSS edition. The supported save formats are:

- **XLSX** — `wb.save("output.xlsx")`
- **CSV** — `wb.save("output.csv")`
- **Markdown** — `wb.save_as_markdown("output.md")`

### How do I load a CSV file?

Use `LoadOptions` with `LoadFormat.CSV` as the second argument to `Workbook`:

```python
from aspose_cells import Workbook, LoadOptions, LoadFormat

opts = LoadOptions(LoadFormat.CSV)
wb = Workbook("data.csv", opts)
ws = wb.worksheets[0]
val = ws.cells["A1"].value
```

### How do I add a chart?

Use one of the `add_*` methods on `ws.charts`. Each method takes positional arguments for the chart's bounding box: `top_row`, `left_col`, `bottom_row`, `right_col`.

```python
from aspose_cells import Workbook

wb = Workbook()
ws = wb.worksheets[0]

# Add data
ws.cells["A1"].value = "Month"
ws.cells["B1"].value = "Sales"
ws.cells["A2"].value = "Jan"
ws.cells["B2"].value = 1200
ws.cells["A3"].value = "Feb"
ws.cells["B3"].value = 1500

# Add a bar chart (top_row, left_col, bottom_row, right_col)
chart_idx = ws.charts.add_bar(5, 0, 20, 8)
chart = ws.charts[chart_idx]
chart.title = "Monthly Sales"
chart.n_series.add("B2:B3", True)

wb.save("output.xlsx")
```

### Why does `cell.value()` raise a TypeError?

Because `.value` is a property, not a method. Calling `cell.value()` attempts to call the returned value as a function, which raises `TypeError`. Always use assignment or direct attribute access:

```python
# Wrong — raises TypeError
cell.value("Hello")
cell.formula("=SUM(A1:A5)")
val = cell.value()

# Correct
cell.value = "Hello"
cell.formula = "=SUM(A1:A5)"
val = cell.value
```

### What file formats can be loaded?

| Format | Extension | How to load |
|--------|-----------|-------------|
| Excel 2007–2019 | .xlsx | `Workbook("file.xlsx")` |
| Excel 97–2003 | .xls | `Workbook("file.xls")` |
| CSV | .csv | `Workbook("file.csv", LoadOptions(LoadFormat.CSV))` |

## See Also

Aspose.Cells FOSS is licensed under the MIT License. Review the full license terms in the [LICENSE](https://github.com/aspose-cells-foss/aspose-cells-python/blob/main/License/license.txt) file. For installation and basic usage, see the [README](https://github.com/aspose-cells-foss/aspose-cells-python/blob/main/README.md) and the [examples directory](https://github.com/aspose-cells-foss/aspose-cells-python/tree/main/examples).

- [Convert file formats](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
- [Fix common errors](/kb.aspose.org/cells/python/how-to-fix-spreadsheets-errors-python/)
- [Load files](/kb.aspose.org/cells/python/how-to-load-spreadsheets-python/)
- [Optimize performance](/kb.aspose.org/cells/python/how-to-optimize-spreadsheets-python/)
- [Save files](/kb.aspose.org/cells/python/how-to-save-spreadsheets-python/)
