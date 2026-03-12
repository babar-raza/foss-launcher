---
canonical: https://kb.aspose.org/cells/_index/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: The library enables reading and writing Excel-compatible formats with
  full support for cell values, formulas, and styles.
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
seoTitle: Aspose.Cells FOSS Kb _Index
slug: _index
title: Kb _Index
type: toc
url: /kb.aspose.org/cells/_index/
weight: 7
---

## Capabilities

Aspose.Cells FOSS provides core spreadsheet functionality for Python developers, supporting workbook creation, cell manipulation, and formatting through 128+ public classes. The library enables reading and writing Excel-compatible formats with full support for cell values, formulas, and styles.

- Create and modify workbooks and worksheets using the Workbook and Worksheet classes
- Read and write cell values and formulas via the `Cell` class methods value() and formula()
- Apply alignment, borders, and number formatting through `Alignment`, `Borders`, and `Border` classes
- Configure auto filters on ranges using the `AutoFilter` class and its methods like filter_columns() and sort_state()
- Import and export CSV data using `CSVHandler` with `CSVLoadOptions` and `CSVSaveOptions`
- Handle encrypted XLSX files using `CFBReader`, `CFBWriter`, and `AgileEncryptionParameters`

For cell value handling, `CellValueHandler` provides [identifier omitted]-376-compliant operations including type detection, XML formatting, and date conversion. The `CalculationProperties` class exposes workbook calculation settings such as calc_mode() and full_calc_on_load(). [identifier omitted] capabilities support robust data processing workflows in production environments where reliability and format fidelity are critical.

## Quick Install

Install Aspose.Cells FOSS using pip to access its core spreadsheet processing classes including Workbook, Worksheet, `Cell`, Style, `Alignment`, `Border`, `Borders`, `AutoFilter`, and `AgileEncryptionParameters`. The package supports reading, writing, and manipulating Excel files in Python environments.

```bash
pip install aspose-cells-foss>=26.3.1
```

After installation, verify the setup by importing the package and printing a confirmation message. This confirms that the core modules are correctly installed and accessible.

```python
import aspose.cells
print('[identifier omitted] successful')
```

## Getting Started

Aspose.Cells FOSS provides core spreadsheet functionality for Python developers, enabling workbook creation, cell manipulation, and file I/O using classes like Workbook, Worksheet, `Cell`, Style, and `Alignment`. The library supports reading and writing Excel files, applying formatting, and managing worksheet features such as auto filters and cell styles.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set a value in cell A1
worksheet.cells.get('A1').value = '[identifier omitted], Aspose.Cells FOSS!'

# Save the workbook to disk
workbook.save('output.xlsx')
```

## Developer Guide

Aspose.Cells FOSS provides core spreadsheet manipulation capabilities in Python, with 128+ public classes supporting operations like cell value handling, auto filtering, and encryption. [identifier omitted] can use `Cell` to read/write values and formulas, `Alignment` to control text alignment, and `AutoFilter` to manage filtered views via methods like filter_columns() and sort_state(). The library includes dedicated handlers for CSV import/export (`CSVHandler`) and [identifier omitted]-376-compliant cell value processing (`CellValueHandler`).

For encryption workflows, `AgileEncryptionParameters` configures [identifier omitted]-376 [identifier omitted] 2 [identifier omitted] 4 compliant settings, while `CFBReader` and `CFBWriter` handle encrypted CFB packaging—though standard encryption remains unsupported per known limitations. `AutoFilter` XML loading and writing are supported via `AutoFilterXMLLoader` and `AutoFilterXMLWriter`, enabling round-trip preservation of filter states in .xlsx files. `Border` styling is accessible through `Border` and `Borders` classes, and calculation properties are exposed via `CalculationProperties`.

## See Also

- Learn how to use the [`Cell`](Cell) class to read and write cell values and formulas in spreadsheets
- Explore [`AutoFilter`](AutoFilter) for filtering and sorting data in worksheets
- Review [`AgileEncryptionParameters`](AgileEncryptionParameters) for configuring document encryption
- Understand [`CSVHandler`](CSVHandler) for importing and exporting data in CSV format
- Reference [`Alignment`](Alignment) and [`Border`](Border) classes for cell styling and formatting
