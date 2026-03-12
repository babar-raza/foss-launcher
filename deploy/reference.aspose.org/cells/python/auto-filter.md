---
canonical: https://reference.aspose.org/cells/python/auto-filter/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: The library supports the AutoFilter class with a filter_by_color method
  that applies a color filter to a column.
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
lastmod: '2026-03-11T21:00:43Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: The library supports the AutoFilter class with a range
slug: auto-filter
title: The library supports the AutoFilter class with a range property for setting
  t...
type: reference_object_page
url: /reference.aspose.org/cells/python/auto-filter/
weight: 20
---

## Overview

Aspose.Cells FOSS -- [identifier omitted] or function purpose in 1-3 sentences.

Aspose.Cells FOSS The library supports the AutoFilter class with a range property for setting the filter range in A1 notation. The library supports the AutoFilter class with a filter_by_color method that applies a color filter to a column.

```python
aspose/cells_foss/         # [identifier omitted] source code (canonical location)
  __init__.py              # [identifier omitted] exports
  workbook.py              # Workbook entry point and save/load dispatch
  worksheet.py             # Worksheet model
  cell.py / cells.py       # Cell model and A1-keyed collection
  style.py                 # Font, fill, border, alignment, number format
  chart.py                 # Chart models and enums
  picture.py / shape.py    # Drawing objects
  table.py                 # Excel table support
  sparkline.py             # Sparkline support
  data_validation.py       # Validation models and enums
  auto_filter.py           # Filter models
  document_properties.py   # Core and extended document properties
  workbook_properties.py   # Workbook-level settings and protection
  csv_handler.py           # CSV import/export
  markdown_handler.py      # Markdown export
  json_handler.py          # JSON export
  xml_loader.py            # Workbook XML loading
  xml_saver.py             # Workbook XML saving
  xml_*_loader.py          # [identifier omitted]-specific XML loaders
  xml_*_saver.py           # [identifier omitted]-specific XML savers
examples/                  # [identifier omitted] example tests for library features
  outputfiles/             # [identifier omitted] from examples/ tests
```

## Constructor

Aspose.Cells FOSS -- [identifier omitted] signature and parameters table.

| Item | [identifier omitted] |
| --- | --- |
| The library supports the AutoFilter class with a filter_columns property that returns a dictionary mapping col_id to FilterColumn objects. |  |
| The library supports the AutoFilter class with a filter_top10 method that applies a top 10 filter to a column. |  |

## Properties

The `AutoFilter` class exposes read-only properties that reflect the current filter configuration. [identifier omitted] properties provide access to the defined range, column-specific filter settings, and sort state without allowing direct mutation.

| Name | Type | [identifier omitted] |
|------|------|-------------|
| range | str | The filter range in A1 notation (read-only). |
| filter_columns | dict | A dictionary mapping column indices to `FilterColumn` objects (read-only). |
| sort_state | object | The sort state configuration for the filtered range (read-only). |

## Methods

The `AutoFilter` class provides methods to apply, clear, and manage filters on a worksheet range. Each method operates on column indices and supports various filter types including value lists, colors, custom conditions, top 10 values, and dynamic filters. All methods are defined in the `aspose.cells_foss.auto_filter` module.

| [identifier omitted] | Return Type | [identifier omitted] |
|--------|-------------|-------------|
| `filter(col_index, values)` | `None` | Applies a filter to a specific column by index and list of values. |
| `add_filter(col_index, value)` | `None` | Adds a single filter value to a column. |
| `custom_filter(col_index, operator, value)` | `None` | Applies a custom filter with an operator and value to a column. |
| `filter_by_color(col_index, color)` | `None` | Applies a color filter to a column. |
| `filter_top10(col_index, is_top, is_percent, count)` | `None` | Applies a top 10 filter to a column. |
| `filter_dynamic(col_index, dynamic_type)` | `None` | Applies a dynamic filter (e.g., above average) to a column. |
| `clear_column_filter(col_index)` | `None` | Clears the filter for a specific column. |
| clear_all_filters() | `None` | Clears all filters applied to the auto filter range. |
| remove() | `None` | Removes the auto filter from the worksheet. |

## Example

The following example demonstrates applying and clearing auto filters using the `AutoFilter` class. It sets a filter range, adds a filter value to a column using add_filter(), and then clears all filters using clear_all_filters(). Both methods are part of the documented API surface.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Populate sample data
worksheet.cells.get("A1").value = "[identifier omitted]"
worksheet.cells.get("B1").value = "[identifier omitted]"
worksheet.cells.get("A2").value = "[identifier omitted]"
worksheet.cells.get("B2").value = "[identifier omitted]"
worksheet.cells.get("A3").value = "[identifier omitted]"
worksheet.cells.get("B3").value = "Vegetable"

# Apply auto filter to range A1:B3
worksheet.auto_filter.range = "A1:B3"

# Add a filter value to column 0 (Product column)
worksheet.auto_filter.add_filter(0, "[identifier omitted]")

# Clear all filters
worksheet.auto_filter.clear_all_filters()

# Save the workbook
workbook.save("output.xlsx")
```

## See Also

The `AutoFilter` class in Aspose.Cells FOSS provides methods to apply, modify, and remove filters on worksheet data ranges. It supports basic value filtering, color-based filtering, top 10 filtering, dynamic filters, and custom filters using operators and values. The remove() method fully removes the auto filter from the worksheet, while clear_all_filters() and clear_column_filter() reset filter states without removing the filter definition.

- [Manage cell comments with authors](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Protect workbooks and worksheets](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
- [Convert file formats](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
