---
page_role: howto_article
title: Working with Charts
slug: chart-creation
description: >-
  Create column, line, bar, and pie charts in Excel workbooks using Python
  and Aspose.Cells FOSS â€” with named series, category data, and legend control.
type: docs
weight: 30
---

## Overview

Aspose.Cells FOSS uses a method-per-chart-type API. Instead of a generic
`add(ChartType.X, ...)` call, each chart type has its own dedicated method on
the worksheet's `charts` collection:

| Method | Chart type |
|---|---|
| `ws.charts.add_bar(top_row, left_col, bottom_row, right_col)` | Clustered column |
| `ws.charts.add_line(top_row, left_col, bottom_row, right_col)` | Line |
| `ws.charts.add_bar(top_row, left_col, bottom_row, right_col)` | Horizontal bar |
| `ws.charts.add_pie(top_row, left_col, bottom_row, right_col)` | Pie |

All four positional parameters describe the rectangular area in the sheet where
the chart will be embedded. Row and column indices are **zero-based**. Each
method returns a `Chart` object that you configure further before saving.

---

## Adding a Column Chart

The example below writes a small revenue-by-product dataset and then adds a
column chart positioned below the data.

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

##--- Data ---
ws.cells["A1"].value = "Product"
ws.cells["B1"].value = "Revenue"

products = ["Widget A", "Widget B", "Widget C", "Widget D", "Widget E"]
revenues = [12_500, 18_200, 9_800, 21_400, 15_600]

for i, (product, revenue) in enumerate(zip(products, revenues), start=2):
    ws.cells[f"A{i}"].value = product
    ws.cells[f"B{i}"].value = revenue

##--- Chart (rows 7â€“22, columns Aâ€“H, all zero-based) ---
##top_row=6, left_col=0, bottom_row=22, right_col=7
chart = ws.charts.add_bar(6, 0, 22, 7)

chart.title = "Revenue by Product"
chart.n_series.add("B2:B6", category_data="A2:A6", name="Revenue (USD)")
chart.show_legend = True
chart.legend_position = "bottom"

workbook.save("column_chart.xlsx")
print("Saved column_chart.xlsx")
```

The data occupies rows 1â€“6 (zero-based rows 0â€“5), so `top_row=6` places the
chart immediately below without overlapping the data.

---

## Adding a Line Chart

Line charts work well for showing trends over time. The call signature is
identical to `add_bar` â€” only the method name changes.

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

##--- Monthly trend data ---
ws.cells["A1"].value = "Month"
ws.cells["B1"].value = "Page Views"
ws.cells["C1"].value = "Conversions"

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
page_views   = [4_200, 5_100, 4_800, 6_300, 7_100, 6_800]
conversions  = [  210,   255,   230,   340,   390,   360]

for i, (month, pv, cv) in enumerate(zip(months, page_views, conversions), start=2):
    ws.cells[f"A{i}"].value = month
    ws.cells[f"B{i}"].value = pv
    ws.cells[f"C{i}"].value = cv

##--- Line chart below the data ---
chart = ws.charts.add_line(8, 0, 24, 8)

chart.title = "Monthly Website Metrics"
chart.n_series.add("B2:B7", category_data="A2:A7", name="Page Views")
chart.n_series.add("C2:C7", category_data="A2:A7", name="Conversions")
chart.show_legend = True
chart.legend_position = "bottom"

workbook.save("line_chart.xlsx")
print("Saved line_chart.xlsx")
```

---

## Chart Title and Legend

Set the chart title by assigning a plain string directly to `chart.title`. The
property accepts a `str` â€” do not attempt to access a sub-property such as
`.title.text`, which does not exist in this library.

```python
##Correct
chart.title = "Quarterly Sales"

##Wrong â€” raises AttributeError
##chart.title.text = "Quarterly Sales"
```

Legend visibility and position are controlled by two properties:

```python
chart.show_legend = True          # display the legend
chart.legend_position = "bottom"  # "bottom", "top", "left", "right"
```

To hide the legend entirely, set `chart.show_legend = False`. The
`legend_position` value is ignored when the legend is hidden.

---

## Data Series Configuration

Use `chart.n_series.add()` to attach data ranges to a chart. Pass all
arguments as **keyword arguments** to avoid positional-order confusion:

```python
chart.n_series.add("B2:B6", category_data="A2:A6", name="Revenue")
```

You can add multiple series to a single chart by calling `n_series.add` more
than once. Each call appends a new series:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

##Headers
ws.cells["A1"].value = "Quarter"
ws.cells["B1"].value = "North"
ws.cells["C1"].value = "South"
ws.cells["D1"].value = "East"

data = [
    ("Q1", 8_400, 6_100, 7_200),
    ("Q2", 9_200, 7_400, 8_100),
    ("Q3", 10_500, 8_900, 9_600),
    ("Q4", 11_800, 9_300, 10_200),
]

for i, row in enumerate(data, start=2):
    ws.cells[f"A{i}"].value = row[0]
    ws.cells[f"B{i}"].value = row[1]
    ws.cells[f"C{i}"].value = row[2]
    ws.cells[f"D{i}"].value = row[3]

chart = ws.charts.add_bar(6, 0, 22, 8)
chart.title = "Regional Sales by Quarter"

chart.n_series.add("B2:B5", category_data="A2:A5", name="North")
chart.n_series.add("C2:C5", category_data="A2:A5", name="South")
chart.n_series.add("D2:D5", category_data="A2:A5", name="East")

chart.show_legend = True
chart.legend_position = "bottom"

workbook.save("multi_series_chart.xlsx")
print("Saved multi_series_chart.xlsx")
```

---

## Category Data

Category labels can be set at the chart level or at the individual series level.

**Chart-level category data** applies to all series as a default:

```python
chart.category_data = "A2:A5"
```

**Series-level category data** (via the `category_data` keyword argument to
`n_series.add`) overrides the chart-level setting for that specific series:

```python
chart.n_series.add("B2:B5", category_data="A2:A5", name="Revenue")
```

When every series shares the same category range, setting `chart.category_data`
once is more concise. When series have different category ranges â€” for example,
two datasets with different time periods â€” use the per-series keyword argument
instead.

---

## Chart Positioning

The four positional parameters to every `add_*` method define a bounding
rectangle in the sheet, measured in zero-based row and column indices:

```
add_bar(top_row, left_col, bottom_row, right_col)
```

| Parameter | Meaning |
|---|---|
| `top_row` | Zero-based index of the first row occupied by the chart |
| `left_col` | Zero-based index of the leftmost column |
| `bottom_row` | Zero-based index of the last row occupied by the chart |
| `right_col` | Zero-based index of the rightmost column |

A common pattern is to place the chart directly below the data. If your data
ends at Excel row 6 (zero-based row index 5), start the chart at `top_row=6`:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

##Data in rows 1â€“5 (zero-based 0â€“4)
labels = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
values = [30, 45, 28, 60, 52]

ws.cells["A1"].value = "Category"
ws.cells["B1"].value = "Score"

for i, (label, val) in enumerate(zip(labels, values), start=2):
    ws.cells[f"A{i}"].value = label
    ws.cells[f"B{i}"].value = val

##Data ends at zero-based row 5 (Excel row 6).
##Place chart from row 6 to row 22, columns Aâ€“H (0â€“7).
chart = ws.charts.add_bar(6, 0, 22, 7)
chart.title = "Category Scores"
chart.n_series.add("B2:B6", category_data="A2:A6", name="Score")
chart.show_legend = False

workbook.save("positioned_chart.xlsx")
print("Saved positioned_chart.xlsx")
```

Make the chart tall enough to be readable: a height of at least 15 rows
(bottom_row - top_row >= 15) and a width of at least 6 columns is a reasonable
starting point.

---

## Common Mistakes

| Wrong | Right | Why |
|---|---|---|
| `ws.charts.add(ChartType.COLUMN, ...)` | `ws.charts.add_bar(...)` | There is no generic `add` method; use the dedicated method for each chart type. |
| `chart.title.text = "My Chart"` | `chart.title = "My Chart"` | `chart.title` is a plain string property, not an object with a `.text` sub-property. |
| `chart.n_series.add("B2:B5", "A2:A5", "Revenue")` | `chart.n_series.add("B2:B5", category_data="A2:A5", name="Revenue")` | The second and third parameters must be passed as keyword arguments to avoid ambiguity. |
| `chart = ws.charts.add_bar(0, 0, 15, 7)` (overlaps data) | Place `top_row` below last data row | A chart that overlaps data obscures values and causes confusing layouts. |
| `chart.legend_position = "bottom"` without `chart.show_legend = True` | Set `chart.show_legend = True` first | `legend_position` has no effect when `show_legend` is `False`. |
---

## See Also

- [API Reference](https://reference.aspose.org/cells/python/) — Full class and method documentation for `aspose_cells`
- [Knowledge Base](https://kb.aspose.org/cells/python/) — Task-oriented how-to guides
- [Product Overview](https://products.aspose.org/cells/python/) — Features and capabilities summary
- [Getting Started / Installation](https://docs.aspose.org/cells/python/getting-started/installation/) — pip install and setup
- [Blog: Python Excel Chart Tutorial](https://blog.aspose.org/cells/python/python-excel-chart-tutorial/) — Step-by-step chart creation guide
