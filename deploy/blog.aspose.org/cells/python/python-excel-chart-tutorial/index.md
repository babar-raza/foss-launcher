---
page_role: howto_article
title: "How to Create Excel Charts from Python Data Using Aspose.Cells FOSS"
seoTitle: "Create Excel Charts in Python — Aspose.Cells FOSS for Python Tutorial"
description: "Learn how to build column, line, and bar charts inside Excel workbooks from Python using Aspose.Cells FOSS — with named data series, category labels, and legend control. No Microsoft Office required."
date: "2026-03-10"
draft: false
author: "Aspose Team"
summary: "Aspose.Cells FOSS for Python provides a method-per-type chart API that makes it straightforward to embed column, line, and bar charts in XLSX workbooks programmatically. This post walks through the API from install to a complete chart example."
tags: ["aspose.cells", "python", "excel", "charts", "open-source", "xlsx", "data-visualization"]
categories: ["Aspose.Cells FOSS"]
---

## Why Build Charts Programmatically?

Automated reporting pipelines often need charts embedded in Excel workbooks — quarterly summaries, ML result dashboards, or operational metrics. Doing this without Microsoft Excel means no licensing cost and no GUI interaction.

**Aspose.Cells FOSS for Python** provides a clean, Pythonic chart API: one method per chart type, a plain string for the title, and keyword-argument-based series configuration. The entire API is covered below.

---

## Install

```bash
pip install aspose-cells-foss
```

Import the classes you need:

```python
from aspose_cells import Workbook, Cell
```

Charts are accessed via `ws.charts` — no separate chart module import is required.

---

## The Chart API at a Glance

| What you want | How to do it |
|---|---|
| Add a column chart | `ws.charts.add_bar(top_row, left_col, bottom_row, right_col)` |
| Add a line chart | `ws.charts.add_line(top_row, left_col, bottom_row, right_col)` |
| Add a bar chart | `ws.charts.add_bar(top_row, left_col, bottom_row, right_col)` |
| Add a pie chart | `ws.charts.add_pie(top_row, left_col, bottom_row, right_col)` |
| Set the title | `chart.title = "My Chart"` (plain string — not `.title.text`) |
| Set x-axis categories | `chart.category_data = "A2:A6"` |
| Add a named series | `chart.n_series.add("B2:B6", category_data="A2:A6", name="Revenue")` |
| Show legend | `chart.show_legend = True` |
| Set legend position | `chart.legend_position = "bottom"` |

All row and column indices are **zero-based**. The `add_*` methods return the `Chart` object directly (not an index).

---

## Column Chart — Step by Step

Let's build a column chart showing quarterly revenue and expenses.

### Step 1: Create the workbook and write data

```python
from aspose_cells import Workbook, Cell

wb = Workbook()
ws = wb.worksheets[0]
ws.name = "Q1-Q4 Report"

##Headers
ws.cells["A1"].value = "Quarter"
ws.cells["B1"].value = "Revenue"
ws.cells["C1"].value = "Expenses"

##Data
quarters = ["Q1", "Q2", "Q3", "Q4"]
revenue  = [50000, 62000, 71000, 89000]
expenses = [32000, 38000, 41000, 47000]

for i, (q, r, e) in enumerate(zip(quarters, revenue, expenses), start=2):
    ws.cells[f"A{i}"].value = q
    ws.cells[f"B{i}"].value = r
    ws.cells[f"C{i}"].value = e
```

### Step 2: Add the chart

Position the chart below the data (row 7 onward, spanning columns 0-8):

```python
chart = ws.charts.add_bar(6, 0, 22, 8)
```

### Step 3: Configure title and legend

```python
chart.title = "Quarterly Revenue vs Expenses"
chart.show_legend = True
chart.legend_position = "bottom"
```

### Step 4: Add data series

Each series needs a value range, category range, and a name:

```python
chart.category_data = "A2:A5"
chart.n_series.add("B2:B5", category_data="A2:A5", name="Revenue")
chart.n_series.add("C2:C5", category_data="A2:A5", name="Expenses")
```

### Step 5: Save

```python
wb.save("quarterly_report.xlsx")
print("Chart saved to quarterly_report.xlsx")
```

**Full example in one block:**

```python
from aspose_cells import Workbook, Cell

wb = Workbook()
ws = wb.worksheets[0]
ws.name = "Q1-Q4 Report"

##Data
ws.cells["A1"].value = "Quarter"
ws.cells["B1"].value = "Revenue"
ws.cells["C1"].value = "Expenses"

data = [("Q1", 50000, 32000), ("Q2", 62000, 38000),
        ("Q3", 71000, 41000), ("Q4", 89000, 47000)]
for i, (q, r, e) in enumerate(data, start=2):
    ws.cells[f"A{i}"].value = q
    ws.cells[f"B{i}"].value = r
    ws.cells[f"C{i}"].value = e

chart = ws.charts.add_bar(6, 0, 22, 8)
chart.title = "Quarterly Revenue vs Expenses"
chart.category_data = "A2:A5"
chart.n_series.add("B2:B5", category_data="A2:A5", name="Revenue")
chart.n_series.add("C2:C5", category_data="A2:A5", name="Expenses")
chart.show_legend = True
chart.legend_position = "bottom"

wb.save("quarterly_report.xlsx")
```

---

## Line Chart — Monthly Trend

The same pattern works for `add_line()`:

```python
from aspose_cells import Workbook, Cell

wb = Workbook()
ws = wb.worksheets[0]

months  = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
actuals = [42000, 47500, 53000, 49000, 61000, 68000]
targets = [45000, 45000, 50000, 55000, 60000, 65000]

ws.cells["A1"].value = "Month"
ws.cells["B1"].value = "Actual"
ws.cells["C1"].value = "Target"

for i, (m, a, t) in enumerate(zip(months, actuals, targets), start=2):
    ws.cells[f"A{i}"].value = m
    ws.cells[f"B{i}"].value = a
    ws.cells[f"C{i}"].value = t

chart = ws.charts.add_line(8, 0, 24, 8)
chart.title = "Monthly Revenue — Actual vs Target"
chart.category_data = "A2:A7"
chart.n_series.add("B2:B7", category_data="A2:A7", name="Actual")
chart.n_series.add("C2:C7", category_data="A2:A7", name="Target")
chart.show_legend = True
chart.legend_position = "right"

wb.save("monthly_trend.xlsx")
```

---

## Pie Chart — Market Share

```python
from aspose_cells import Workbook, Cell

wb = Workbook()
ws = wb.worksheets[0]

segments = ["Product A", "Product B", "Product C", "Product D"]
shares   = [40, 25, 20, 15]

ws.cells["A1"].value = "Segment"
ws.cells["B1"].value = "Share %"
for i, (s, v) in enumerate(zip(segments, shares), start=2):
    ws.cells[f"A{i}"].value = s
    ws.cells[f"B{i}"].value = v

chart = ws.charts.add_pie(6, 0, 20, 7)
chart.title = "Market Share by Product"
chart.category_data = "A2:A5"
chart.n_series.add("B2:B5", category_data="A2:A5", name="Share")
chart.show_legend = True
chart.legend_position = "right"

wb.save("market_share.xlsx")
```

---

## Common Mistakes to Avoid

| Wrong | Right |
|---|---|
| `ws.charts.add(ChartType.COLUMN, 5, 0, 15, 5)` | `ws.charts.add_bar(5, 0, 15, 5)` |
| `chart.title.text = "Revenue"` | `chart.title = "Revenue"` |
| `chart.n_series.add("B2:B5", True)` (positional) | `chart.n_series.add("B2:B5", category_data="A2:A5", name="Revenue")` |
| `from aspose.cells.charts import ChartType` | Not needed — use `ws.charts.add_bar()` directly |
| `chart.n_series.category_data = "A2:A5"` | `chart.category_data = "A2:A5"` (chart level) |

---

## Resources

- [Aspose.Cells FOSS for Python — Installation](https://docs.aspose.org/cells/python/getting-started/installation/)
- [Developer Guide — Chart Creation](https://docs.aspose.org/cells/python/developer-guide/chart-creation/)
- [API Reference — ChartCollection, Chart, NSeries](https://reference.aspose.org/cells/python/)
- [Knowledge Base — How to Create Charts in Python](https://kb.aspose.org/cells/python/how-to-create-charts-python/)
- [Product Overview](https://products.aspose.org/cells/python/) — Features and capabilities summary
- [Blog: Introducing Aspose.Cells FOSS](https://blog.aspose.org/cells/python/introducing-cells-foss-python/) — Library overview and quick start
- [GitHub Repository](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python)
