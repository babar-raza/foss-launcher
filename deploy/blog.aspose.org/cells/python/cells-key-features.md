---
canonical: https://blog.aspose.org/cells/python/cells-key-features/
canonical_import: aspose.cells
description: 'The library supports: create chart, empowering users to visualize data
  without relying on external tools or manual intervention in Microsoft Excel. This...'
display_name: Aspose.Cells
family: cells
keywords:
- library
- supports
- create
- spreadsheets
page_role: feature_blog
platform: python
robots: index, follow
seoTitle: 'Aspose.Cells The library supports: Create Chart'
slug: cells-key-features
title: 'The library supports: Create Chart'
type: feature_blog
url: /blog.aspose.org/cells/python/cells-key-features/
weight: 17
---

## Introduction

Aspose.Cells enables developers to programmatically create and customize charts directly within spreadsheets using Python. The library supports: create chart, empowering users to visualize data without relying on external tools or manual intervention in Microsoft Excel. This capability is essential for generating dynamic reports, dashboards, and data-driven documents that require immediate insight from raw spreadsheet data.

With Aspose.Cells, you can add various chart types—including column, line, and more—to a worksheet, define data sources, and apply rich formatting such as solid or gradient fills, axis titles, and theme-based colors. The API surface provides intuitive access to chart elements like `n_series`, `plot_area`, and `title`, allowing precise control over appearance and behavior. These features make it straightforward to transform static spreadsheet data into engaging visual representations.

```python
import os
from aspose_cells import ChartType

def get_output_directory():
    return os.path.abspath(os.path.join(".", "..", "..", "..", "Data", "02_OutputDirectory"))

def run_how_to_create_custom_chart():
    # Create a new workbook and get the first worksheet
    workbook = cells.Workbook()
    worksheet = workbook.worksheets[0]

    # Populate cells with sample data
    worksheet.cells.get("A1").put_value(50)
    worksheet.cells.get("A2").put_value(100)
    worksheet.cells.get("A3").put_value(150)
    worksheet.cells.get("A4").put_value(110)
    worksheet.cells.get("B1").put_value(260)
    worksheet.cells.get("B2").put_value(12)
    worksheet.cells.get("B3").put_value(50)
    worksheet.cells.get("B4").put_value(100)

    # Add a column chart to the worksheet
    chart_index = worksheet.charts.add(ChartType.COLUMN, 5, 0, 25, 10)

    # Access the newly added chart
    chart = worksheet.charts[chart_index]

    # Add NSeries data source ranging from A1 to B4
    chart.n_series.add("A1:B4", True)

    # Set the second NSeries to be a line chart
    chart.n_series[1].type = ChartType.LINE

    # Save the workbook
    output_path = os.path.join(get_output_directory(), "outputHowToCreateCustomChart.xlsx")
    workbook.save(output_path)

    print("HowToCreateCustomChart executed successfully.")

if __name__ == "__main__":
    run_how_to_create_custom_chart()
```

## Key Highlights

Aspose.Cells empowers developers to generate professional-quality charts directly within spreadsheets using Python. The library supports: create chart functionality, enabling dynamic visualization of data without requiring Microsoft Excel. With intuitive APIs, users can define chart types, bind data ranges, and apply rich formatting — all programmatically. This capability is especially valuable for report automation, data analysis dashboards, and business intelligence workflows where consistent, embeddable visualizations are essential.

- Support for multiple chart types including column, line, bar, and pie charts via `ChartType` enumeration.
- Direct binding of worksheet cell ranges as data sources using `n_series.add()` method.
- Customization of individual series with mixed chart types (e.g., combining column and line in one chart).
- Advanced formatting of chart elements such as plot area, chart area, and data series using `FillFormat` and `CellsColor`.
- Integration with Microsoft Excel theme colors for consistent styling across enterprise documents.
- Programmatic control over chart titles, axis labels, and gradient fills for polished output.

## Getting Started

Aspose.Cells enables developers to programmatically create and customize charts within spreadsheets using Python. The library supports: create chart functionality, allowing you to generate visual representations of data directly in Excel-compatible formats. With minimal code, you can populate worksheet cells, add a chart, define its data source, and apply formatting — all without requiring Microsoft Excel.

```python
import os
from aspose_cells import ChartType

def get_output_directory():
    return os.path.abspath(os.path.join(".", "..", "..", "..", "Data", "02_OutputDirectory"))

def run_how_to_create_custom_chart():
    # Create a new workbook and get the first worksheet
    workbook = cells.Workbook()
    worksheet = workbook.worksheets[0]

    # Populate cells with sample data
    worksheet.cells.get("A1").put_value(50)
    worksheet.cells.get("A2").put_value(100)
    worksheet.cells.get("A3").put_value(150)
    worksheet.cells.get("A4").put_value(110)
    worksheet.cells.get("B1").put_value(260)
    worksheet.cells.get("B2").put_value(12)
    worksheet.cells.get("B3").put_value(50)
    worksheet.cells.get("B4").put_value(100)

    # Add a column chart to the worksheet
    chart_index = worksheet.charts.add(ChartType.COLUMN, 5, 0, 25, 10)

    # Access the newly added chart
    chart = worksheet.charts[chart_index]

    # Add NSeries data source ranging from A1 to B4
    chart.n_series.add("A1:B4", True)

    # Set the second NSeries to be a line chart
    chart.n_series[1].type = ChartType.LINE

    # Save the workbook
    output_path = os.path.join(get_output_directory(), "outputHowToCreateCustomChart.xlsx")
    workbook.save(output_path)

    print("HowToCreateCustomChart executed successfully.")

if __name__ == "__main__":
    run_how_to_create_custom_chart()
```

## See Also

Aspose.Cells enables developers to create and customize charts directly within spreadsheets using Python. The library supports: create chart functionality with support for multiple chart types, data series formatting, and axis/title configuration. Explore the examples below to learn how to build and enhance charts programmatically.

```python
import os
from aspose_cells import ChartType

def get_output_directory():
    return os.path.abspath(os.path.join(".", "..", "..", "..", "Data", "02_OutputDirectory"))

def run_how_to_create_custom_chart():
    workbook = cells.Workbook()
    worksheet = workbook.worksheets[0]

    worksheet.cells.get("A1").put_value(50)
    worksheet.cells.get("A2").put_value(100)
    worksheet.cells.get("A3").put_value(150)
    worksheet.cells.get("A4").put_value(110)
    worksheet.cells.get("B1").put_value(260)
    worksheet.cells.get("B2").put_value(12)
    worksheet.cells.get("B3").put_value(50)
    worksheet.cells.get("B4").put_value(100)

    chart_index = worksheet.charts.add(ChartType.COLUMN, 5, 0, 25, 10)
    chart = worksheet.charts[chart_index]
    chart.n_series.add("A1:B4", True)
    chart.n_series[1].type = ChartType.LINE

    output_path = os.path.join(get_output_directory(), "outputHowToCreateCustomChart.xlsx")
    workbook.save(output_path)

    print("HowToCreateCustomChart executed successfully.")

if __name__ == "__main__":
    run_how_to_create_custom_chart()
```

- How to Create a Chart in a worksheet
- How to Format Chart Series using solid and gradient fills
- How to Set Chart Titles and Axes programmatically
- How to Apply Microsoft Theme Colors to chart elements

- [No Excel required](/blog.aspose.org/cells/python/cells-foss-python/)
- [Convert spreadsheets to PDF](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Get started quickly](/docs.aspose.org/cells/python/developer-guide/getting-started/)
- [Install the library](/docs.aspose.org/cells/python/developer-guide/installation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
