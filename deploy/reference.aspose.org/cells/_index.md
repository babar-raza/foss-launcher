---
canonical: https://reference.aspose.org/cells/_index/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:29:20Z'
dateModified: '2026-03-11T11:29:20Z'
datePublished: '2026-03-11T11:29:20Z'
description: Developers can read, write, and modify Excel files using classes like
  `Workbook`, `Worksheet`, and `Cell`, along with supporting utilities for formatting,...
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
lastmod: '2026-03-11T11:29:20Z'
page_role: toc
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Cells FOSS Table of Contents
slug: _index
title: Table of Contents
type: toc
url: /reference.aspose.org/cells/_index/
weight: 5
---

## Capabilities

Aspose.Cells FOSS provides `core` spreadsheet manipulation capabilities through a focused set of classes. Developers can read, write, and modify Excel files using classes like `Workbook`, `Worksheet`, and `Cell`, along with supporting utilities for formatting, filtering, and data handling.

- Read and write CSV files using `CSVHandler` with configurable `CSVLoadOptions` and `CSVSaveOptions`
- Apply cell alignment and border formatting via `Alignment`, `Border`, and `Borders`
- Configure auto filters on worksheet ranges using `AutoFilter` and its methods range(), `filter_columns()`, and sort_state()
- Handle encrypted XLSX files with `CFBReader` and `CFBWriter`, supporting Agile encryption via `AgileEncryptionParameters`
- Process cell values per ECMA-376 using `CellValueHandler` for type detection, formatting, and parsing

The library supports loading and writing autofilter data in XML `format` for .xlsx files through `AutoFilterXMLLoader` and `AutoFilterXMLWriter`. For encryption, `CFBReader` and `CFBWriter` enable reading and writing encrypted packages in CFB `format`, while `AgileEncryptionParameters` defines encryption settings per ECMA-376 Part 2, Section 4. `Cell` value operations follow ECMA-376 specifications, with `CellValueHandler` providing static methods like `get_cell_type()`, `format_value_for_xml()`, and `excel_serial_to_datetime()`.

## Quick Install

Install Aspose.Cells FOSS using pip to access `core` spreadsheet functionality including `Cell`, `AutoFilter`, `CSVHandler`, and `AgileEncryptionParameters` classes.

```bash
pip install aspose-cells-foss>=26.3.1
```

After installation, verify the package loads correctly by importing `aspose.cells` and printing a confirmation message.

```python
import aspose.cells
print('Installation successful')
```

## Getting Started

Aspose.Cells FOSS provides `core` spreadsheet functionality for Python developers. It includes classes like `Workbook`, `Worksheet`, `Cell`, `Alignment`, `AutoFilter`, and `CSVHandler` to read, write, and manipulate spreadsheet data. The library supports CSV import/export via `CSVHandler`, `cell` value formatting via `CellValueHandler`, and encryption parameters via `AgileEncryptionParameters`.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set a cell value and formula
worksheet.cells.get('A1').value = 'Hello'
worksheet.cells.get('A2').formula = '=A1&" World"'

# Save as CSV
aspose.cells.CSVHandler.save_csv(workbook, 'output.csv', None)
```

## Developer Guide

The Developer Guide for Aspose.Cells FOSS covers `core` operations for reading, writing, and manipulating spreadsheet data using the official API surface. Developers can work with individual `cells` via the `Cell` class to set values and formulas, and apply formatting using `Alignment` and `border` classes. `AutoFilter` functionality is accessible through `AutoFilter`, which supports filtering and sorting state management on worksheet ranges.

For data interchange, Aspose.Cells FOSS provides `CSVHandler` for loading and saving CSV content, supporting both file paths and string inputs. The `CellValueHandler` class offers utilities for parsing and formatting `cell` values per ECMA-376, including type detection and date conversion. Encryption workflows use `AgileEncryptionParameters` and CFB-based handlers (`CFBReader`, `CFBWriter`) for reading and writing encrypted XLSX files, though only Agile encryption is currently supported per known limitations.

## See Also

Aspose.Cells FOSS provides `core` spreadsheet functionality through classes like `Cell`, `AutoFilter`, `Alignment`, and `CalculationProperties`. For CSV operations, use `CSVHandler` with `CSVLoadOptions` and `CSVSaveOptions`. Encryption support is limited to Agile encryption via `AgileEncryptionParameters`, `CFBReader`, and `CFBWriter`.

- Learn about [cell manipulation with `Cell`](#cell-class-reference)
- Explore [auto-filtering features using `AutoFilter`](#autofilter-reference)
- Review [CSV import/export with `CSVHandler`](#csv-handling-reference)
- Understand [encryption parameters for XLSX files using `AgileEncryptionParameters`](#encryption-reference)
