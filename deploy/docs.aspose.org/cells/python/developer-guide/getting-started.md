---
canonical: https://docs.aspose.org/cells/python/developer-guide/getting-started/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: By the end of this guide, you will be able to install the library and
  begin working with `core` spreadsheet features using Python 3.7 or higher.
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
lastmod: '2026-03-11T11:59:24Z'
page_role: workflow_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS Getting Started
slug: getting-started
title: Getting Started
type: workflow_page
url: /docs.aspose.org/cells/python/developer-guide/getting-started/
weight: 4
---

## Overview

Aspose.Cells FOSS enables Python developers to read, write, and manipulate Excel files without requiring Microsoft Excel. By the end of this guide, you will be able to install the library and begin working with `core` spreadsheet features using Python 3.7 or higher.

The library supports key spreadsheet operations including `cell` value and `formula` handling, styling, auto filtering, and charting. For example, the `AutoFilter` class provides programmatic control over worksheet `filters`, with methods like range(), `filter_columns()`, and sort_state().

```bash
pip install aspose-cells-foss>=26.3.1
```

```python
import aspose.cells
print('Installation successful')
```

## Prerequisites

Aspose.Cells FOSS requires Python 3.7 or later. Install the package using pip with the command `pip install aspose-cells-foss>=26.3.1`. The library depends on `pycryptodome >= 3.15.0` for encryption-related operations.

```bash
pip install aspose-cells-foss>=26.3.1
```

```python
import aspose.cells
print('Installation successful')
```

After installation, verify the setup by importing `aspose.cells`. The `FilterColumn` class is part of the auto-filtering API and can be initialized to define filtering criteria for specific columns.

## First Steps

Install Aspose.Cells FOSS using pip to begin working with spreadsheet files in Python. The library provides a minimal, focused API for reading, writing, and manipulating Excel-compatible formats without external dependencies like openpyxl or pandas. After installation, verify the setup by importing the package and printing a success message.

```bash
pip install aspose-cells-foss>=26.3.1
```

```python
import aspose.cells
print('Installation successful')
```

Create a new workbook and access the first worksheet to begin editing. The `Workbook` class serves as the entry point, and `worksheets[0]` retrieves the default worksheet. This pattern mirrors common spreadsheet workflows where operations start on the first sheet.

```python
import aspose.cells

workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]
```

Set a `cell` value using the `Cell` class and assign it to a worksheet `cell` by `address`. The value() method writes data into the `cell`, and the `formula()` method can store Excel formulas. This demonstrates basic read-write interaction with the `core` `cell` model.

```python
cell = aspose.cells.Cell("Hello, Aspose.Cells FOSS!")
worksheet.cells["A1"] = cell
```

Save the workbook to disk in XLSX `format`. The save() method writes the file using the library’s native XML-based engine, supporting standard Excel formats without requiring Microsoft Excel to be installed. This completes the simplest end-to-end workflow.

```python
workbook.save("output.xlsx")
```

## Code Example

This example demonstrates reading and evaluating formulas in a spreadsheet using Aspose.Cells FOSS. It creates a workbook with `cells` containing basic formulas, then reads the computed values. The lightweight evaluator supports CONCATENATE, CONCAT, TEXT, and IF functions at read time for `cells` without cached values. It also shows how to retrieve `filter` values from an auto-filtered range.

```python
from aspose.cells import Workbook, Cell

# Create a new workbook and get the first worksheet
workbook = Workbook()
worksheet = workbook.worksheets[0]

# Set up cells with formulas
worksheet.cells["A1"].value = "Hello"
worksheet.cells["B1"].value = "World"
worksheet.cells["A2"].formula = "=CONCAT(A1, \" \", B1)"
worksheet.cells["B2"].formula = "=IF(A2=\"Hello World\", \"Match\", \"No Match\")"

# Force calculation to evaluate formulas
workbook.calculate_formula()

# Read computed values
concat_result = worksheet.cells["A2"].value
if_result = worksheet.cells["B2"].value
print(f"CONCAT result: {concat_result}")
print(f"IF result: {if_result}")

# Apply auto filter and get filter values
worksheet.auto_filter.range = "A1:B2"
filter_cols = worksheet.auto_filter.filter_columns
print(f"Number of filtered columns: {len(filter_cols)}")
```

## Next Steps

Explore how Aspose.Cells FOSS processes formulas and `filters` in spreadsheets. A lightweight evaluator resolves `cell` references and defined names, and supports basic formulas like CONCATENATE, CONCAT, TEXT, and IF at read time for `cells` without cached values.

- Review the `AutoFilter` class to understand how to apply and inspect filter criteria, including retrieving custom filter lists via `filter_columns()`.
- Study the `Cell` class to read and write cell values, formulas, and styles programmatically.
- Consult the `CellValueHandler` class for parsing and formatting cell values per ECMA-376, including date conversion and error detection.

## See Also

Install Aspose.Cells FOSS for Python using pip to `get` started with spreadsheet processing. The library supports `core` Excel operations including `cell` manipulation, styling, and auto-filtering via the `AutoFilter` class. For encryption workflows, `AgileEncryptionParameters` and `CFBReader`/`CFBWriter` provide limited support for Agile encryption. Review the installation guide and full API reference to explore features like `CellValueHandler` for ECMA-376-compliant value parsing and formatting.

```bash
pip install aspose-cells-foss>=26.3.1
```

```python
import aspose.cells
print('Installation successful')
```

- [Install the library](/docs.aspose.org/cells/python/developer-guide/installation/)
- [Frequently asked questions](/kb.aspose.org/cells/python/faq/)
- [Common issues and fixes](/kb.aspose.org/cells/python/troubleshooting/)
- [Full API reference](/reference.aspose.org/cells/python/api-overview/)
- [Conditional formatting guide](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
