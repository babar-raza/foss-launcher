---
canonical: https://reference.aspose.org/cells/python/filter-column/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: The library supports the FilterColumn class with an add_custom_filter
  method that appends a custom filter criterion to the column.
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
seoTitle: The library supports the FilterColumn class with a
slug: filter-column
title: The library supports the FilterColumn class with a custom_filters property
  th...
type: reference_object_page
url: /reference.aspose.org/cells/python/filter-column/
weight: 21
---

## Overview

Aspose.Cells FOSS -- [identifier omitted] or function purpose in 1-3 sentences.

Aspose.Cells FOSS The library supports the FilterColumn class with a custom_filters property that returns a list of custom filter criteria tuples. The library supports the FilterColumn class with an add_custom_filter method that appends a custom filter criterion to the column.

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

The `FilterColumn` class in Aspose.Cells FOSS is instantiated via its constructor, which accepts no arguments. It is typically obtained through the filter_columns property of an `AutoFilter` instance. The class provides properties and methods for configuring column-specific filters, including color, custom, dynamic, top 10, and button visibility controls.

```python
from aspose.cells import Workbook, AutoFilter

workbook = Workbook()
worksheet = workbook.worksheets[0]
auto_filter = worksheet.auto_filter
filter_column = auto_filter.filter_columns[0]
```

| Parameter | Type | [identifier omitted] |
|-----------|------|-------------|
| (none) | — | [identifier omitted] takes no parameters; instance is obtained via `AutoFilter.filter_columns[index]` |

## Properties

The `FilterColumn` class exposes several properties to configure filtering behavior for individual columns in an auto-filtered range. [identifier omitted] properties allow programmatic control over custom, color, dynamic, and top 10 filters, as well as the visibility of the filter button. Each property has a corresponding setter that accepts structured data as defined in the API surface.

| Name | Type | [identifier omitted] |
|------|------|-------------|
| custom_filters | list[tuple] | Returns a list of custom filter criteria tuples. |
| color_filter | dict | Gets or sets color-based filter settings. [identifier omitted] a dictionary with 'color' and 'cell_color' keys on set. |
| dynamic_filter | dict | Gets or sets dynamic filter settings. [identifier omitted] a dictionary with 'type' and 'value' keys on set. |
| top10_filter | dict | Gets or sets top 10 filter settings. [identifier omitted] a dictionary with 'top', 'percent', and 'val' keys on set. |
| filter_button | bool | Gets or sets whether the filter button is visible for the column. |

## Methods

The `FilterColumn` class provides methods to manage filtering behavior for individual columns in an auto-filter. [identifier omitted] methods allow programmatic control over filter criteria, including custom filters, color filters, dynamic filters, and top 10 filters. Each method operates on the column's filter state and integrates with the `AutoFilter.filter_columns` collection.

| [identifier omitted] | Return Type | [identifier omitted] |
|--------|-------------|-------------|
| `add_filter(value)` | None | Appends a filter value to the column's filter list. |
| `add_custom_filter(criterion)` | None | Appends a custom filter criterion to the column. |
| clear_filters() | None | Clears all filter settings for the column. |
| filter_button() | bool | Gets or sets visibility of the filter button. |
| color_filter() | dict or None | Gets or sets color-based filter settings. |
| dynamic_filter() | dict or None | Gets or sets dynamic filter settings. |
| top10_filter() | dict or None | Gets or sets top 10 filter settings. |
| custom_filters() | list[tuple] | Returns a list of custom filter criteria tuples. |

## Example

The following example demonstrates how to configure a `FilterColumn` using its filter_button, color_filter, and custom_filters properties. It creates a new workbook, adds sample data, applies an auto filter, and configures column filtering behavior.

## See Also

The `FilterColumn` class provides programmatic control over column-level filtering in Aspose.Cells FOSS. It supports standard value filters via add_filter(), custom filters via custom_filters and add_custom_filter(), and advanced filters including color, dynamic, and top 10 criteria. The filter_button property controls UI visibility of the filter dropdown.

- [The library supports adding and managing cell comments with author and rich text](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [The library supports workbook and worksheet protection](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with Formulas with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Spreadsheet Operations with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
- [How to Convert File Formats with Aspose.Cells FOSS](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
