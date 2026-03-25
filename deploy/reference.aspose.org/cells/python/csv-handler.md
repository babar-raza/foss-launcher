---
canonical: https://reference.aspose.org/cells/python/csv-handler/
canonical_import: aspose.cells
date: '2026-03-22T08:56:20Z'
dateModified: '2026-03-22T08:56:20Z'
datePublished: '2026-03-22T08:56:20Z'
description: It works with `CSVSaveOptions` for export configuration and `CSVLoadOptions`
  for import settings, enabling programmatic control over CSV file handling in...
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
lastmod: '2026-03-22T08:56:20Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS Csv Handler
slug: csv-handler
title: Csv Handler
type: reference_object_page
url: /reference.aspose.org/cells/python/csv-handler/
weight: 22
---

## Overview

The `CSVHandler` class provides static methods to import and export workbook data to and from CSV format. It works with `CSVSaveOptions` for export configuration and `CSVLoadOptions` for import settings, enabling programmatic control over CSV file handling in Aspose.Cells FOSS.

```python
from aspose.cells import Workbook, CSVHandler, CSVSaveOptions

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Name"
worksheet.cells["B1"].value = "Score"
worksheet.cells["A2"].value = "Alice"
worksheet.cells["B2"].value = 95

options = CSVSaveOptions()
CSVHandler.save_csv(workbook, "output.csv", options)
```

| Method | Description |
|--------|-------------|
| `save_csv(workbook, file_path, options)` | Exports a workbook to a CSV file using specified options |
| `save_csv_to_string(workbook, options)` | Exports a workbook to a CSV string using specified options |
| `load_csv(workbook, file_path, options)` | Imports data from a CSV file into a workbook using specified options |
| `load_csv_from_string(workbook, csv_content, options)` | Imports data from a CSV string into a workbook using specified options |

## Constructor

The `Cell` class represents a single `cell` in a worksheet. It provides methods to manipulate `cell` content, including clearing formulas. Use `Cell.clear_formula()` to `remove` a `formula` and set it to `None`.

```python
import aspose.cells

# Create a workbook and access a worksheet
wb = aspose.cells.Workbook()
ws = wb.worksheets[0]

# Set a formula in a cell
ws.cells['A1'].formula = '=SUM(B1:B10)'

# Clear the formula
ws.cells['A1'].clear_formula()
```

| Method | Description |
|--------|-------------|
| `clear_formula()` | Clears the `formula` of the `cell` (sets it to None). |
| `is_empty()` | Checks if the `cell` is empty. |
| `clear_value()` | Clears the `cell` `value`. |
| `clear()` | Clears both `value` and `formula`. |
| `set_comment(text, author, width, height)` | Sets a `comment` on the `cell`. |
| `value` | Gets or sets the `cell` `value`. |
| `formula` | Gets or sets the `cell` `formula`. |
| `style` | Gets the `cell` `style`. |
| `comment` | Gets the `cell` `comment` (read-only). |
| `data_type` | Gets the `cell` data `type` (read-only). |

## Properties

The `Cell` class exposes `properties` that provide read-only or read-write access to `cell` data and metadata. These `properties` are essential for inspecting or modifying individual `cell` contents in Aspose.Cells FOSS.

| Name | Type | Description |
|------|------|-------------|
| `value` | Any | The raw `value` stored in the `cell`. |
| `formula` | str | The `formula` string assigned to the `cell`. |
| `style` | `Style` | The formatting `style` applied to the `cell`. |
| `comment` | str | The `comment` text attached to the `cell` (read-only). |
| `data_type` | str | The `type` of data stored (e.g., 'String', 'Double', 'Bool') (read-only). |

The `CSVSaveOptions` and `CSVLoadOptions` classes configure CSV import and export behavior. They are used with `CSVHandler.save_csv()` and `CSVHandler.load_csv()` methods respectively.

| Name | Type | Description |
|------|------|-------------|
| separator | str | The character used to separate fields in the CSV output. |
| encoding | str | The character encoding for the CSV file (e.g., 'utf-8'). |
| has_header_row | bool | Indicates whether the first row should be treated as column headers. |
| format_strategy | int | Controls how numeric `values` are formatted during export. |

```python
from aspose.cells import Workbook, CSVHandler, CSVSaveOptions

# Create a workbook and set a value
workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Test"

# Configure CSV export options
options = CSVSaveOptions()
options.separator = ","
options.encoding = "utf-8"
options.has_header_row = True

# Save to CSV using the public API
CSVHandler.save_csv(workbook, "output.csv", options)
```

## Methods

The `CSVHandler`, `JsonHandler`, and `MarkdownHandler` classes provide static methods for exporting workbook data to text-based formats. Each handler supports saving to a file or returning data as a string. The `MarkdownHandler.save_markdown()` method is part of the public API and exports workbook content to Markdown format.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `CSVHandler.save_csv(workbook, file_path: str, options: Optional[CSVSaveOptions]) -> None` | `None` | Saves the workbook to a CSV file using specified export options. |
| `CSVHandler.save_csv_to_string(workbook, options: Optional[CSVSaveOptions]) -> str` | `str` | Exports the workbook to a CSV string using specified export options. |
| `CSVHandler.load_csv(workbook, file_path: str, options: Optional[CSVLoadOptions]) -> None` | `None` | Loads data from a CSV file into the workbook using specified import options. |
| `CSVHandler.load_csv_from_string(workbook, csv_content: str, options: Optional[CSVLoadOptions]) -> None` | `None` | Loads data from a CSV string into the workbook using specified import options. |
| `JsonHandler.save_json(workbook, file_path: str, options: Optional[JsonSaveOptions]) -> None` | `None` | Exports the workbook to a JSON file using specified options. |
| `JsonHandler.save_json_to_dict(workbook, options: Optional[JsonSaveOptions]) -> Dict[str, Any]` | `Dict[str, Any]` | Exports the workbook to a Python dictionary in JSON-compatible format. |
| `MarkdownHandler.save_markdown(workbook, file_path: str, options: Optional[MarkdownSaveOptions]) -> None` | `None` | Exports the workbook to a Markdown file using specified options. |
| `MarkdownHandler.save_markdown_to_string(workbook, options: Optional[MarkdownSaveOptions]) -> str` | `str` | Exports the workbook to a Markdown string using specified options. |

```python
from aspose.cells import Workbook, MarkdownHandler, MarkdownSaveOptions

# Create a workbook and populate data
workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Header"
worksheet.cells["A2"].value = "Data"

# Export to Markdown
MarkdownHandler.save_markdown(workbook, "output.md", MarkdownSaveOptions())
```

## Example

The following example demonstrates saving a workbook to JSON format using the `JsonHandler.save_json()` method, which is part of the public API for Aspose.Cells FOSS. It creates a workbook, populates a worksheet with sample data, and exports the data to a JSON file.

## See Also

The `CSVHandler` class provides static methods for importing and exporting CSV data. Related handlers for other formats include `JsonHandler` and `MarkdownHandler`. The `CSVLoadOptions` and `CSVSaveOptions` classes configure import and export behavior respectively.

```python
from aspose.cells import Workbook, CSVHandler, CSVLoadOptions, CSVSaveOptions

# Load CSV with options
workbook = Workbook()
options = CSVLoadOptions()
CSVHandler.load_csv(workbook, "input.csv", options)

# Save CSV with options
save_options = CSVSaveOptions()
CSVHandler.save_csv(workbook, "output.csv", save_options)
```

- [Reference the Cells object model](/reference.aspose.org/cells/python/cells/)
- [Introduction to Aspose.Cells FOSS for Python](/blog.aspose.org/cells/python/cells-foss-python/)
- [Create all chart types in spreadsheets](/blog.aspose.org/cells/python/create-charts-spreadsheets/)
- [Work with formulas in spreadsheets](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform common spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
