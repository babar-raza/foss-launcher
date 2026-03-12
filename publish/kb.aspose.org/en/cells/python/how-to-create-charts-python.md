---
page_role: howto_article
title: "How to Create Charts in Excel with Python Using Aspose.Cells FOSS"
description: "Learn how to create column, line, and bar charts in Excel workbooks using Python and Aspose.Cells FOSS, including data series configuration, chart titles, and category labels."
date: 2026-03-10
lastmod: 2026-03-10
weight: 11
draft: false
type: "topic"
keywords: [
  "create chart excel python",
  "python excel chart aspose",
  "add chart to xlsx python",
  "aspose cells foss chart python",
  "python column chart excel",
  "excel chart creation python",
  "aspose cells n_series python",
  "python create workbook chart",
  "generate excel chart python",
  "add line chart excel python"
]
step1: "Install Aspose.Cells FOSS for Python via pip"
step2: "Create a workbook and populate data cells"
step3: "Add a column chart with ws.charts.add_bar()"
step4: "Configure data series with chart.n_series.add()"
step5: "Set chart title and category data"
step6: "Save the workbook to XLSX"
step7: "Create a line chart with ws.charts.add_line()"
---

Charts turn raw spreadsheet data into visual insights. **Aspose.Cells FOSS for Python** lets you create column, line, bar, and pie charts programmatically — with full control over data series, category labels, chart title, and position — without requiring Microsoft Excel.

### Why Create Charts with Aspose.Cells FOSS?

1. **No Excel required**: Build charts entirely in Python, on any OS.
2. **Method-per-type API**: Use `add_bar()`, `add_line()`, `add_bar()`, `add_pie()` — one method per chart type.
3. **Named series**: Configure each series with `name=`, `category_data=` keyword arguments.
4. **Precise placement**: Control chart bounds by cell coordinates (top_row, left_col, bottom_row, right_col).

---

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install Aspose.Cells FOSS for Python

```bash
pip install aspose-cells-foss
```

---

### Step 2: Create a Workbook and Populate Data

Create a new workbook and write numeric data plus category labels to cells:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]
ws.name = "Sales Data"

##Category labels in column A (rows 2-5, leaving row 1 for a header)
ws.cells["A1"].value = "Quarter"
ws.cells["A2"].value = "Q1"
ws.cells["A3"].value = "Q2"
ws.cells["A4"].value = "Q3"
ws.cells["A5"].value = "Q4"

##Revenue series in column B
ws.cells["B1"].value = "Revenue"
ws.cells["B2"].value = 50000
ws.cells["B3"].value = 62000
ws.cells["B4"].value = 71000
ws.cells["B5"].value = 89000

##Expense series in column C
ws.cells["C1"].value = "Expenses"
ws.cells["C2"].value = 32000
ws.cells["C3"].value = 38000
ws.cells["C4"].value = 41000
ws.cells["C5"].value = 47000
```

---

### Step 3: Add a Column Chart

Use `ws.charts.add_bar(top_row, left_col, bottom_row, right_col)` to insert a column chart. The method returns a chart object directly:

```python
##Insert a column chart occupying rows 7-22, columns 0-7
chart = ws.charts.add_bar(6, 0, 22, 7)
```

Row and column indices are zero-based.

---

### Step 4: Configure Data Series

Add each data series using `chart.n_series.add()` with keyword arguments:

```python
##Add Revenue series
chart.n_series.add("B2:B5", category_data="A2:A5", name="Revenue")

##Add Expenses series
chart.n_series.add("C2:C5", category_data="A2:A5", name="Expenses")
```

The `category_data` argument specifies the cell range for the x-axis labels. The `name` argument sets the series legend label.

---

### Step 5: Set the Chart Title and Category Data

Set the chart title as a plain string:

```python
chart.title = "Quarterly Sales vs Expenses"
chart.category_data = "A2:A5"   # x-axis labels at chart level
chart.show_legend = True
chart.legend_position = "bottom"
```

---

### Step 6: Save the Workbook

```python
workbook.save("sales_chart.xlsx")
print("Workbook with chart saved.")
```

**Complete column chart example:**

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

##Data
labels = ["Q1", "Q2", "Q3", "Q4"]
revenue = [50000, 62000, 71000, 89000]
expenses = [32000, 38000, 41000, 47000]

ws.cells["A1"].value = "Quarter"
ws.cells["B1"].value = "Revenue"
ws.cells["C1"].value = "Expenses"

for i, (label, rev, exp) in enumerate(zip(labels, revenue, expenses), start=2):
    ws.cells[f"A{i}"].value = label
    ws.cells[f"B{i}"].value = rev
    ws.cells[f"C{i}"].value = exp

chart = ws.charts.add_bar(6, 0, 22, 7)
chart.title = "Quarterly Sales vs Expenses"
chart.category_data = "A2:A5"
chart.n_series.add("B2:B5", category_data="A2:A5", name="Revenue")
chart.n_series.add("C2:C5", category_data="A2:A5", name="Expenses")
chart.show_legend = True
chart.legend_position = "bottom"

workbook.save("quarterly_chart.xlsx")
```

---

### Step 7: Create a Line Chart

The same pattern works for `add_line()`:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
revenue = [42000, 47500, 53000, 49000, 61000, 68000]

ws.cells["A1"].value = "Month"
ws.cells["B1"].value = "Revenue"

for i, (m, r) in enumerate(zip(months, revenue), start=2):
    ws.cells[f"A{i}"].value = m
    ws.cells[f"B{i}"].value = r

chart = ws.charts.add_line(8, 0, 24, 8)
chart.title = "Monthly Revenue Trend"
chart.category_data = "A2:A7"
chart.n_series.add("B2:B7", category_data="A2:A7", name="Revenue")
chart.show_legend = True

workbook.save("trend_chart.xlsx")
```

{{% /steps %}}

---

## Common Issues and Fixes

### 1. Chart appears blank or empty

**Cause**: The data range passed to `n_series.add()` does not contain values, or the cell range string is incorrect.
**Fix**: Verify the cell range matches your data. Check `ws.cells["B2"].value` is not `None`.

### 2. Category labels not showing on x-axis

**Cause**: `chart.category_data` was not set, or the range points to empty cells.
**Fix**: Set `chart.category_data = "A2:A5"` where column A contains your label strings.

### 3. Chart position overlaps data

**Cause**: The row bounds in `add_bar()` overlap with the data area.
**Fix**: Place the chart below the data: `ws.charts.add_bar(data_last_row + 2, 0, data_last_row + 18, 7)`.

### 4. `AttributeError: 'ChartCollection' object has no attribute 'add'`

**Cause**: The FOSS library uses method-per-type API, not `add(ChartType.COLUMN, ...)`.
**Fix**: Use `ws.charts.add_bar(...)`, `ws.charts.add_line(...)`, `ws.charts.add_bar(...)`, or `ws.charts.add_pie(...)`.

---

## Frequently Asked Questions

### Which chart types are supported?

Use `add_bar()`, `add_line()`, `add_bar()`, and `add_pie()` for the most common types. Check the `ChartCollection` class for the full list of available `add_*` methods.

### Can I create charts in an existing Excel file?

Yes. Load the workbook with `Workbook("existing.xlsx")`, access the target sheet, and add a chart using the appropriate `ws.charts.add_*()` method.

### How do I set the chart title?

Assign a plain string: `chart.title = "My Chart Title"`. There is no `.text` sub-property — the title is the string itself.

### Is this approach compatible with pandas?

Yes. Write pandas DataFrame values to cells in a loop, then add a chart over that data range.

---

**Related Resources:**

- [Aspose.Cells FOSS for Python — Developer Guide](https://docs.aspose.org/cells/python/developer-guide/)
- [Working with Charts](https://docs.aspose.org/cells/python/developer-guide/chart-creation/)
- [How to Export Excel to Markdown in Python](https://kb.aspose.org/cells/python/how-to-export-excel-to-markdown-python/)
- [API Reference — ChartCollection, Chart, NSeries](https://reference.aspose.org/cells/python/)
- [Product Overview](https://products.aspose.org/cells/python/) — Features and capabilities summary
- [Blog: Python Excel Chart Tutorial](https://blog.aspose.org/cells/python/python-excel-chart-tutorial/)
