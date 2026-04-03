---
canonical: https://reference.aspose.org/cells/python/chart/
canonical_import: aspose.cells
code_import: aspose.cells
date: '2026-03-27T07:02:41Z'
dateModified: '2026-03-27T07:02:41Z'
datePublished: '2026-03-27T07:02:41Z'
description: It is created via methods in `ChartCollection`, such as `add_line()`,
  `add_bar()`, or `add_box_whisker()`.
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
lastmod: '2026-03-27T07:02:41Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: 'Aspose.Cells FOSS Chart: Represents a chart in a worksheet'
slug: chart
title: 'Chart: Represents a chart in a worksheet'
type: reference_object_page
url: /reference.aspose.org/cells/python/chart/
weight: 22
---

## Overview

The `Chart` class represents a chart in a worksheet and provides methods to manage its series, `axes`, and 3D view settings. It is created via methods in `ChartCollection`, such as `add_line()`, `add_bar()`, or `add_box_whisker()`.

```python
from aspose.cells import Workbook, ChartType

workbook = Workbook()
worksheet = workbook.worksheets[0]
charts = worksheet.charts
chart = charts.add(ChartType.LINE, 5, 0, 15, 5)
chart.title = "Sample Line Chart"
workbook.save("chart.xlsx")
```

| Method | Description |
|--------|-------------|
| `add_series(values, category_data, name, chart_type, x_values)` | Adds a series to the chart. |
| `add_axis(axis_type, axis_id)` | Adds an axis to the chart and returns it. |
| `copy()` | Creates a `copy` of the chart. |
| `type` | Read-only property indicating the chart `type`. |
| `title` | Gets or sets the chart `title`. |
| `category_data` | Gets or sets the category axis data. |
| `show_legend` | Gets or sets whether the legend is shown. |
| `legend_position` | Gets or sets the legend position. |
| `axes` | Accesses the chart `axes` collection. |
| series | Accesses the chart series collection. |
| `view_3d` | Accesses 3D view settings. |

## Constructor

The `Chart` class represents a chart in a worksheet and provides methods to manage its series, `axes`, and 3D view settings. It is instantiated via the `ChartCollection.add()` method or specialized chart-`type` methods like `add_scatter()`.

| Name | Type | Description |
|------|------|-------------|
| `add_series(values, category_data, name, chart_type, x_values)` | method | Adds a series to the chart. |
| `add_axis(axis_type, axis_id)` | method | Adds an axis to the chart and returns it. |
| `copy()` | method | Creates a `copy` of the chart. |
| `type` | property (read-only) | Returns the chart `type`. |
| `title` | property | Gets or sets the chart `title`. |
| `category_data` | property | Gets or sets the category axis data. |
| `show_legend` | property | Gets or sets whether the legend is shown. |
| `legend_position` | property | Gets or sets the legend position. |
| `axes` | property (read-only) | Returns the collection of chart `axes`. |
| series | property (read-only) | Returns the collection of chart series. |
| `view_3d` | property (read-only) | Returns the 3D view settings. |
| `error_bars` | property (read-only) | Returns the `error` bars collection. |

## Properties

The `Chart` class represents a chart in a worksheet and provides `properties` to access and configure its visual and structural attributes. These `properties` control aspects such as chart `type`, `title`, legend, and category data.

| Name | Type | Description |
|------|------|-------------|
| `type` | `ChartType` | Gets the chart `type`. |
| `title` | str | Gets or sets the chart `title`. |
| `category_data` | list | Gets or sets the category axis data. |
| `show_legend` | bool | Gets or sets whether the legend is displayed. |
| `legend_position` | str | Gets or sets the legend position (e.g., 'Top', 'Bottom', 'Left', 'Right'). |

## Methods

The `Chart` class represents a chart in a worksheet and provides methods to manage its series, `axes`, and 3D view settings. Below are the methods available on the `Chart` object.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `add_series(values, category_data, name, chart_type, x_values)` | `ChartSeries` | Adds a series to the chart with the specified `values`, category data, `name`, chart `type`, and optional x-`values`. |
| `add_axis(axis_type, axis_id)` | `ChartAxis` | Adds an axis (category, `value`, or series) to the chart and returns the created axis object. |
| `copy()` | `Chart` | Creates a deep `copy` of the chart. |

```python
from aspose.cells import Workbook, DataValidationType

workbook = Workbook()
worksheet = workbook.worksheets[0]

# Add a dropdown list validation to A1:A10
validation = worksheet.data_validations.add("A1:A10")
validation.type = DataValidationType.LIST
validation.formula1 = '",,"'

workbook.save("validation.xlsx")
```

## Example

The following example demonstrates creating a chart, adding a series, and configuring its `title` and legend using the `Chart` class. It uses the canonical import `aspose.cells` and operates on a new workbook with sample data.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Populate sample data
worksheet.cells["A1"].value = "Category"
worksheet.cells["B1"].value = "Value"
worksheet.cells["A2"].value = "A"
worksheet.cells["B2"].value = 10
worksheet.cells["A3"].value = "B"
worksheet.cells["B3"].value = 20
worksheet.cells["A4"].value = "C"
worksheet.cells["B4"].value = 30

# Add a column chart
chart = worksheet.charts.add_bar(5, 0, 15, 8)
chart.type = aspose.cells.ChartType.COLUMN

# Add a series to the chart
series_index = chart.n_series.add("B2:B4", True)
series = chart.n_series[series_index]
series.name = "=B1"

# Configure chart title and legend
chart.title.value = "Sample Chart"
chart.show_legend = True

# Save the workbook
workbook.save("chart_example.xlsx")
```

## See Also

- [Worksheet object reference](/cells/python/worksheet/)
- [Introduction to Cells FOSS for Python](/cells/python/cells-foss-python/)
- [Create all chart types in spreadsheets](/cells/python/create-charts-spreadsheets/)
- [Working with formulas in FOSS](/cells/python/developer-guide/formula-calculation/)
- [Essential spreadsheet operations](/cells/python/developer-guide/spreadsheet-operations/)
