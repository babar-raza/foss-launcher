---
canonical: https://blog.aspose.org/cells/python/creating-charts-python/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: Create bar charts, line charts, pie charts, and more directly inside Excel files from Python using Aspose.Cells FOSS — no Excel installation required.
display_name: Aspose.Cells FOSS
family: cells
keywords:
- python excel charts
- create chart python excel
- aspose cells python chart
- bar chart python xlsx
- python openpyxl chart alternative
lastmod: '2026-03-11T11:59:24Z'
page_role: feature_blog
platform: python
reading_time: 2
robots: index, follow
seoTitle: Create Charts in Excel Files with Python — Aspose.Cells FOSS
slug: creating-charts-python
title: Creating Charts in Excel Files with Python
type: feature_blog
url: /blog.aspose.org/cells/python/creating-charts-python/
weight: 17
---

## Introduction

Aspose.Cells FOSS supports creating charts directly inside Excel `.xlsx` files from Python. The library includes 16 chart types — Line, Bar, Pie, Area, Scatter, Waterfall, Combo, Stock, Surface, Radar, Treemap, Sunburst, Histogram, Funnel, Box & Whisker, and Map — all generated without installing Microsoft Excel.

Charts are added via `worksheet.charts.add_*()` methods that accept a bounding box defined by `(upper_left_row, upper_left_column, lower_right_row, lower_right_column)` as zero-based indices. Series data is added via `chart.n_series.add()`.

## Creating a Bar Chart

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]

# Write data
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
sales  = [100, 150, 120, 180, 200, 170]
for i, (m, s) in enumerate(zip(months, sales), 2):
    worksheet.cells[f"A{i}"].value = m
    worksheet.cells[f"B{i}"].value = s

# Add a bar chart anchored to rows 0-20, columns 4-12
chart = worksheet.charts.add_bar(0, 4, 20, 12)
chart.title = "Monthly Sales"
chart.n_series.add("B2:B7", category_data="A2:A7", name="Sales")

workbook.save("bar_chart.xlsx")
```

## Creating a Line Chart

```python
from aspose_cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
sales  = [100, 150, 120, 180, 200, 170]
for i, (m, s) in enumerate(zip(months, sales), 2):
    worksheet.cells[f"A{i}"].value = m
    worksheet.cells[f"B{i}"].value = s

# Line chart anchored to rows 0-20, columns 4-12
chart = worksheet.charts.add_line(0, 4, 20, 12)
chart.title = "Monthly Sales"
chart.n_series.add("B2:B7", category_data="A2:A7", name="Sales")

workbook.save("line_chart.xlsx")
```

## Key Highlights

- 16 chart types available: Line, Bar, Pie, Area, Scatter, Waterfall, Combo, Stock, Surface, Radar, Treemap, Sunburst, Histogram, Funnel, Box & Whisker, and Map
- Charts are positioned using a bounding box of zero-based row and column indices
- Series data and category labels are specified using Excel-style range strings (`"B2:B7"`)
- No Microsoft Excel, COM automation, or native dependency is required

## See Also

- [Introducing Aspose.Cells FOSS for Python](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
- [Convert file formats](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
