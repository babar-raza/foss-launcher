---
canonical: https://products.aspose.org/cells/_index/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: It provides a lightweight, dependency-free alternative to tools like
  openpyxl for programmatic spreadsheet manipulation in production environments.
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

Aspose.Cells FOSS is a Python library for creating, reading, and modifying Excel files (.xlsx format) without requiring Microsoft Excel. It provides a lightweight, dependency-free alternative to tools like openpyxl for programmatic spreadsheet manipulation in production environments.

Key capabilities include managing multiple worksheets — add, remove, rename, and organize them as needed — and enforcing data integrity through validation rules such as dropdown lists, number ranges, and custom formulas. The library supports core Excel operations like cell value assignment, formula evaluation, and saving to XLSX or CSV formats.

## Key Features

- Create & Edit Excel Files: Build new workbooks from scratch or update existing .xlsx files using the `Workbook` class and `Worksheet` APIs.
- Charts: Generate and modify charts including line, bar, pie, scatter, combo, waterfall, and treemap types directly in Python.
- Comments: Attach cell comments with author metadata and rich text formatting using the `Cell.comment` property.

```python
from aspose_cells import Workbook

# Create a new workbook
workbook = Workbook()
worksheet = workbook.worksheets[0]

# Set cell value and add a comment
worksheet.cells["A1"].value = "Report Data"
worksheet.cells["A1"].comment = "Source: Q3 Sales"

# Save the file
workbook.save("output.xlsx")
```

## Quick Start

Install Aspose.Cells FOSS to start working with spreadsheets in Python. The library supports core operations like reading and writing cell values and formulas, adding and managing tables with styles and auto-filters, and creating hyperlinks to URLs, emails, files, and internal references.

```bash
pip install aspose-cells-foss>=26.3.1
```

```python
import aspose_cells

wb = aspose.cells.Workbook()
ws = wb.worksheets[0]
ws.cells["A1"].value = "Hello"
ws.cells["A2"].formula = "=SUM(B1:B5)"
wb.save("output.xlsx")
```

## See Also

Aspose.Cells FOSS supports comprehensive styling, shapes, and auto-filtering for Python developers. Apply fonts, colors, borders, number formats, and alignment using the `Style` and `Alignment` classes. Add shapes, text boxes, and pictures with hyperlinks via Shapes and Pictures collections. Filter data ranges using `AutoFilter` on worksheets.

- [Explore real-world applications](/kb.aspose.org/cells/python/developer-guide/use-cases/)
- [Apply dynamic formatting rules](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Master conditional formatting](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas efficiently](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
