---
canonical: https://docs.aspose.org/cells/_index/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: With 128+ public classes, the API supports common operations like cell
  manipulation, formatting, and data validation using only the methods and properties...
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
page_role: toc
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Cells FOSS Docs _Index
slug: _index
title: Docs _Index
type: toc
url: /docs.aspose.org/cells/_index/
weight: 2
---

## Capabilities

Aspose.Cells FOSS provides core spreadsheet functionality for Python developers, enabling programmatic creation, reading, and editing of Excel-compatible files. With 128+ public classes, the API supports common operations like cell manipulation, formatting, and data validation using only the methods and properties defined in its documented surface.

Key capabilities include reading and writing cell values and formulas via the `Cell` class, applying alignment and border styles through `Alignment` and `Borders`, and managing worksheet-level features like auto filters using `AutoFilter`. The library also supports CSV import/export via `CSVHandler` and [identifier omitted]-376-compliant cell value handling with `CellValueHandler`.

- Create and modify workbooks and worksheets
- Read/write cell values, formulas, and comments using `Cell`
- Apply cell styling: fonts, number formats, borders, and alignment (`Alignment`, `Borders`)
- Configure auto filters and sorting via `AutoFilter`
- Import/export CSV data with `CSVHandler` and `CSVLoadOptions`/`CSVSaveOptions`
- Handle encrypted XLSX files using `AgileEncryptionParameters`, `CFBReader`, and `CFBWriter`

## Quick Install

Install Aspose.Cells FOSS using pip to access its core spreadsheet functionality, including Workbook, Worksheet, `Cell`, Style, `Alignment`, `Border`, `Borders`, `AutoFilter`, and 128+ other classes.

```bash
pip install aspose-cells-foss>=26.3.1
```

After installation, verify the package loads correctly by importing `aspose.cells` and printing a confirmation message.

```python
import aspose.cells
print('[identifier omitted] successful')
```

## Getting Started

Aspose.Cells FOSS provides core spreadsheet functionality for Python developers, enabling workbook creation, cell manipulation, and formatting using classes like Workbook, Worksheet, `Cell`, Style, and `Alignment`. The library supports reading and writing Excel files, applying cell styles, and managing worksheet structure through a clean, object-oriented API.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set a value in cell A1
worksheet.cells.get('A1').value = '[identifier omitted], Aspose.Cells FOSS!'

# Save the workbook
workbook.save('output.xlsx')
```

## Developer Guide

Aspose.Cells FOSS provides core spreadsheet manipulation capabilities in Python, with 128+ public classes supporting operations like cell value handling, auto-filtering, and encryption. [identifier omitted] can work with `Cell`, `AutoFilter`, `Alignment`, and `AgileEncryptionParameters` to read, write, and format Excel-compatible files using [identifier omitted]-376-compliant operations.

The library supports CSV import/export via `CSVHandler` and `CSVLoadOptions`/`CSVSaveOptions`, enabling seamless integration with data pipelines. For encryption, `AgileEncryptionParameters` configures [identifier omitted]-376 [identifier omitted] 2 [identifier omitted] 4–compliant Agile encryption, while `CFBReader` and `CFBWriter` handle CFB container I/O for encrypted XLSX files. `Cell` value parsing and formatting follow [identifier omitted]-376 standards through `CellValueHandler`, including datetime conversion and error value detection.

[identifier omitted] and formatting are handled via `Alignment`, `Border`, and `Borders`, allowing precise control over cell appearance. Auto-filtering is managed through `AutoFilter`, which exposes filter_columns, sort_state, and range() to define and query filtered views. [identifier omitted] classes integrate directly with Workbook and Worksheet to support production-grade Excel workflows in Python.

## See Also

Aspose.Cells FOSS provides core spreadsheet functionality for Python developers, including cell manipulation via `Cell`, styling with `Alignment` and `Border`, and data handling through `AutoFilter`, `CSVHandler`, and `CellValueHandler`. The API supports encryption via `AgileEncryptionParameters` and CFB I/O with `CFBReader` and `CFBWriter`.

- Workbook and Worksheet fundamentals
- Cell value and formula operations
- Data validation and filtering
- CSV import and export
- Encryption and security
