---
canonical: https://reference.aspose.org/cells/python/api-overview/
canonical_import: aspose_cells_foss
date: '2026-03-11T20:08:46Z'
dateModified: '2026-03-11T20:08:46Z'
datePublished: '2026-03-11T20:08:46Z'
description: It supports cell-level operations, styling, and worksheet-level features
  including auto-filtering.
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
lastmod: '2026-03-11T20:08:46Z'
page_role: api_reference
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS API Reference | Guide
slug: api-overview
title: Aspose.Cells FOSS API Reference
type: api_reference
url: /reference.aspose.org/cells/python/api-overview/
weight: 6
---

## Overview

Aspose.Cells FOSS provides core spreadsheet manipulation capabilities in Python, enabling programmatic creation, reading, and editing of Excel-compatible files. It supports cell-level operations, styling, and worksheet-level features including auto-filtering.

The `AutoFilter.range` property sets the filter range, and `AutoFilter.custom_filter` applies a custom filter to a specific column.

| [identifier omitted] | Type | [identifier omitted] |
|-------|------|-------------|
| `AgileEncryptionParameters` | class | Parameters for Agile encryption |
| `Alignment` | class | Text alignment settings |
| `AutoFilter` | class | [identifier omitted] auto filters in a worksheet |
| `AutoFilterXMLLoader` | class | XML loader for auto filter data |
| `AutoFilterXMLWriter` | class | XML writer for auto filter data |
| `Border` | class | [identifier omitted] border edge definition |
| `Borders` | class | Collection of border edges |
| `CFBReader` | class | Reads encrypted XLSX from CFB format |
| `CFBWriter` | class | Writes encrypted XLSX to CFB format |
| `CSVHandler` | class | Handles CSV import/export |
| `CSVLoadOptions` | class | Options for loading CSV files |
| `CSVSaveOptions` | class | Options for saving CSV files |
| `CalculationProperties` | class | Calculation-related workbook properties |
| `Cell` | class | [identifier omitted] a single cell in a worksheet |
| `CellValueHandler` | class | Handles cell value import/export per [identifier omitted]-376 |
| `ChartType` | enum | [identifier omitted] chart types (LINE, BAR, PIE, etc.) |

## Public API

The `AutoFilter` class enables filtering operations on worksheet data. It exposes a read-only range property that defines the filtered data range, and methods to apply, clear, and query filters. The `range(value)` setter configures the data range to which filters apply, while filter_columns() returns a dictionary of column indices to filter criteria. [identifier omitted] filters for specific columns are applied via `custom_filter(column_index, criteria)`, supporting complex filtering logic per column.

| [identifier omitted] | Type | [identifier omitted] |
|-------|------|-------------|
| `AgileEncryptionParameters` | class | [identifier omitted] encryption parameters for Agile XLSX encryption |
| `Alignment` | class | Defines text alignment options for cell styling |
| `AutoFilter` | class | [identifier omitted] auto filters in a worksheet |
| `AutoFilterXMLLoader` | class | Loads auto filter XML data |
| `AutoFilterXMLWriter` | class | Writes auto filter XML data |
| `Border` | class | [identifier omitted] a single border of a cell |
| `Borders` | class | Collection of cell borders |
| `CFBReader` | class | Reads encrypted XLSX from [identifier omitted] File [identifier omitted] format |
| `CFBWriter` | class | Writes encrypted XLSX to [identifier omitted] File [identifier omitted] format |
| `CSVHandler` | class | Handles CSV import/export operations |
| `CSVLoadOptions` | class | Options for loading CSV files |
| `CSVSaveOptions` | class | Options for saving files as CSV |
| `CalculationProperties` | class | [identifier omitted] workbook calculation settings |
| `Cell` | class | [identifier omitted] a single cell in a worksheet |
| `CellValueHandler` | class | Handles cell value import/export per [identifier omitted]-376 |
| `ChartType` | enum | [identifier omitted] chart types: LINE, BAR, PIE, AREA, BOX_WHISKER, WATERFALL, COMBO, SCATTER, STOCK, SURFACE |

```python
import aspose.cells

# Create workbook and worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set up sample data
worksheet.cells.put_value("A1", "[identifier omitted]")
worksheet.cells.put_value("B1", "[identifier omitted]")
worksheet.cells.put_value("A2", "[identifier omitted]")
worksheet.cells.put_value("B2", 100)
worksheet.cells.put_value("A3", "[identifier omitted]")
worksheet.cells.put_value("B3", 150)

# Apply auto filter to range A1:B3
worksheet.auto_filter.range = "A1:B3"

# Apply custom filter to column 0 (Product) for 'Apple'
worksheet.auto_filter.custom_filter(0, "[identifier omitted]")
```

## Common Patterns

`AutoFilter` enables filtering data in a worksheet. Set the range of cells to filter using the range property, then apply filters via methods like custom_filter for column-specific criteria.

```python
import aspose.cells

workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells.put_value("A1", "[identifier omitted]")
worksheet.cells.put_value("B1", "[identifier omitted]")
worksheet.cells.put_value("A2", "[identifier omitted]")
worksheet.cells.put_value("B2", 100)
worksheet.cells.put_value("A3", "[identifier omitted]")
worksheet.cells.put_value("B3", 150)

auto_filter = worksheet.auto_filter
auto_filter.range = "A1:B3"
auto_filter.custom_filter(0, "=[identifier omitted]")

workbook.save("filtered.xlsx")
```

`Cell` value handling follows [identifier omitted]-376 standards. Use `CellValueHandler` static methods to parse, format, or validate values during import/export workflows.

| [identifier omitted] | [identifier omitted] |
|--------|-------------|
| `CellValueHandler.get_cell_type(value)` | Returns the cell type for a given value |
| `CellValueHandler.format_value_for_xml(value, cell_type)` | Formats a value for XML serialization |
| `CellValueHandler.parse_value_from_xml(value_str, cell_type, shared_strings)` | Parses a value from XML string |
| `CellValueHandler.excel_serial_to_datetime(serial_date)` | Converts Excel serial date to datetime |
| `CellValueHandler.is_error_value(value)` | Checks if value is an Excel error |

## See Also

Review the following resources to get started with Aspose.Cells FOSS for Python. The library supports core Excel operations including cell manipulation, styling, and filtering via the `AutoFilter` class. For example, `AutoFilter.range` sets the filter range, and `AutoFilter.custom_filter` applies a custom filter to a specific column.

- [Frequently asked questions](/kb.aspose.org/cells/python/faq/)
- [Common issues and fixes](/kb.aspose.org/cells/python/troubleshooting/)
- [Protect workbook and worksheet structure](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [New protection features explained](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Using formulas effectively](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
