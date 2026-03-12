---
canonical: https://kb.aspose.org/cells/python/how-to-load-spreadsheets-python/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: The `AutoFilterXMLLoader` and `CellValueHandler` classes assist in parsing
  autofilter and cell value data per [identifier omitted]-376 specifications.
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
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Load Files with Aspose.Cells FOSS | Guide
slug: how-to-load-spreadsheets-python
title: How to Load Files with Aspose.Cells FOSS
type: howto_article
url: /kb.aspose.org/cells/python/how-to-load-spreadsheets-python/
weight: 11
---

## Problem

Load Excel files (e.g., XLSX) into Aspose.Cells FOSS using the Workbook class, which supports reading standard spreadsheet formats via `CSVHandler` for CSV data and `CFBReader` for encrypted CFB containers. The `AutoFilterXMLLoader` and `CellValueHandler` classes assist in parsing autofilter and cell value data per [identifier omitted]-376 specifications.

## Prerequisites

To use Aspose.Cells FOSS for loading Excel files in Python, ensure you have Python 3.7 or later installed. Install the package using pip with the command pip install aspose-cells-foss>=26.3.1. After installation, import the library using import aspose.cells. The core classes for file loading include Workbook, Worksheet, and Cell.

- Python 3.7 or later
- pip package manager
- aspose-cells-foss>=26.3.1 installed via pip
- Basic familiarity with Python file handling and object-oriented programming

## Loading the File

Aspose.Cells FOSS provides the Workbook class to load spreadsheet files from file paths or streams. The Workbook constructor accepts a file path string or a file-like object, enabling flexible input sources for Python developers integrating Excel processing into their workflows.

When loading from a file path, pass the absolute or relative path directly to the Workbook constructor. For stream-based loading, provide a binary-mode file object or an in-memory `io.BytesIO` instance. The library supports standard Excel formats such as XLSX and CSV through dedicated handlers like `CSVHandler` for structured data import.

Load behavior can be fine-tuned using options classes such as `CSVLoadOptions` for CSV files. [identifier omitted] options control parsing rules like delimiter handling and data type inference, ensuring accurate representation of source data during import operations.

For encrypted files, Aspose.Cells FOSS supports Agile encryption via `AgileEncryptionParameters`. The `CFBReader` class handles reading encrypted packages in CFB format, though standard encryption remains unsupported per current implementation limits.

## Code Example

This example demonstrates loading a spreadsheet file using Aspose.Cells FOSS, inspecting its structure, and printing a summary of its contents. It uses the Workbook class to load a file, accesses the first worksheet, and iterates through its cells to extract and display basic metadata such as value and data type.

```python
import aspose.cells

# Load a spreadsheet file
workbook = aspose.cells.Workbook("sample.xlsx")

# Access the first worksheet
worksheet = workbook.worksheets[0]

# Print summary: number of rows and columns
print(f"Worksheet '{worksheet.name}' has {worksheet.cells.max_row + 1} rows and {worksheet.cells.max_column + 1} columns")

# Inspect first 5 cells in column A
for row in range(5):
    cell = worksheet.cells.get(row, 0)
    print(f"Cell A{row+1}: value='{cell.value}', type={cell.data_type}")
```

## Supported Formats

Aspose.Cells FOSS supports loading common spreadsheet and text-based file formats through the Workbook class and related handlers. The `CSVHandler` class enables loading CSV files, while native XLSX loading is handled internally using [identifier omitted]-376-compliant parsing.

| Format | [identifier omitted] | [identifier omitted] |
|--------|-----------|-------|
| Excel Open XML | .xlsx | Standard [identifier omitted] Open XML format; supports Agile encryption |
| [identifier omitted]-[identifier omitted] [identifier omitted] | .csv | Loaded via `CSVHandler.load_csv()` and `CSVHandler.load_csv_from_string()` |
| Text-based data | .txt | [identifier omitted] via CSV loading with custom delimiters |
| XML Spreadsheet | .xml | [identifier omitted]-376 compatible XML format; loaded as workbook content |
| [identifier omitted] Spreadsheet | .ods | [identifier omitted] support; limited to basic cell and formula content |
| [identifier omitted] Document Format | .pdf | Not supported for loading; only used for export |
| [identifier omitted] | .html | Not supported for loading; only used for export |

## See Also

- [Frequently asked questions](/kb.aspose.org/cells/python/faq/)
- [Cell comments with authors and rich text](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Protect workbooks and worksheets](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Core spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
