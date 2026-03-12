---
canonical: https://products.aspose.org/cells/_index/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: It enables developers to build spreadsheet-driven applications using
  pure Python, supporting core operations like cell value management, formula evaluation,...
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
page_role: landing
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Cells FOSS | Guide
slug: _index
title: Aspose.Cells FOSS
type: landing
url: /products.aspose.org/cells/_index/
weight: 1
---

## Overview

Aspose.Cells FOSS is a Python library for creating, reading, and modifying Excel files (.xlsx format) without requiring [identifier omitted] Excel. It enables developers to build spreadsheet-driven applications using pure Python, supporting core operations like cell value management, formula evaluation, and file I/O.

Key capabilities include adding and managing multiple worksheets, applying rich cell styling (fonts, borders, alignment), inserting cell comments with author and rich text, and applying auto-filters to data ranges. The library also supports opening and saving password-protected workbooks using AES encryption, and provides a clean API for programmatic workbook manipulation.

## Key Features

Aspose.Cells FOSS enables Python developers to generate, read, and modify Excel workbooks programmatically—without requiring [identifier omitted] Excel. It supports core spreadsheet operations including cell value and formula handling, multi-sheet management, and rich styling.

- Save workbooks with AES-256 encryption using a password to protect sensitive data.
- Create and modify charts—including line, bar, pie, scatter, combo, waterfall, and treemap—directly in worksheets.
- Insert hyperlinks to external URLs, email addresses, local files, or internal worksheet references.
- Apply auto-filters to data ranges for dynamic sorting and filtering of spreadsheet content.

## Quick Start

Install Aspose.Cells FOSS to work with Excel files in Python without [identifier omitted] Excel. Use Workbook to create, open, or decrypt protected files, then manipulate cells, styles, and worksheets directly.

```python
import aspose.cells

# Create or open a workbook
wb = aspose.cells.Workbook()  # new workbook
wb = aspose.cells.Workbook("input.xlsx")  # open existing file
wb = aspose.cells.Workbook("protected.xlsx", password="mypassword")  # open encrypted file

# Access worksheet and cell
ws = wb.worksheets[0]
ws.cells["A1"].value = "[identifier omitted]"
ws.cells["A2"].formula = "=SUM(B1:B5)"

# Apply auto-filter to data range
ws.auto_filter.range("A1:C10")

# Save with encryption or plain format
wb.save("output.xlsx")
wb.save("secure.xlsx", password="mypassword")
```

`Add` shapes, text boxes, and styled cells to enhance your spreadsheets. The library supports rich formatting including fonts, borders, alignment, and auto-filters for data ranges.

## See Also

Aspose.Cells FOSS enables Python developers to work with Excel files programmatically without [identifier omitted] Excel. It supports core spreadsheet features including cell styling with fonts, colors, borders, number formats, and alignment, data validation rules like dropdown lists and number ranges, and conditional formatting with rules-based logic. The library integrates naturally with common Python workflows and is compatible with tools that use openpyxl-style operations.

- [Use Cases](/kb.aspose.org/cells/python/developer-guide/use-cases/)
- [The library supports adding and managing cell comments with author and rich text](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [The library supports workbook and worksheet protection](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with Formulas with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Spreadsheet Operations with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
