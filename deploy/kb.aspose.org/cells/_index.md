---
canonical: https://kb.aspose.org/cells/_index/
canonical_import: aspose.cells
date: '2026-03-22T08:56:20Z'
dateModified: '2026-03-22T08:56:20Z'
datePublished: '2026-03-22T08:56:20Z'
description: The library centers around the `Workbook` class for file management and
  the `Worksheet`/`Cells`/`Cell` hierarchy for granular data operations.
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

Aspose.Cells FOSS provides core spreadsheet functionality for Python developers, enabling programmatic creation, manipulation, and export of Excel-compatible files. The library centers around the `Workbook` class for file management and the `Worksheet`/`Cells`/`Cell` hierarchy for granular data operations.

Key capabilities include reading and writing `cell` `values` and formulas via the `Cell` class, managing multiple `worksheets` through `Workbook.worksheets`, and exporting data to CSV, JSON, and Markdown formats using `CSVHandler`, `JsonHandler`, and `MarkdownHandler`. `Chart` creation and customization are supported for line, bar, pie, area, and scatter chart types via the `ChartCollection` and `Chart` classes.

- Create and modify workbooks with `Workbook` and `Worksheet` objects
- Read/write cell values, formulas, and comments using `Cell` and `Cells`
- Export to CSV, JSON, and Markdown with static handler methods
- Add and configure charts (line, bar, pie, area, scatter) via `ChartCollection`

## Quick Install

Install Aspose.Cells FOSS using pip to access core Excel file handling via the `Workbook`, `Cell`, `Cells`, `Chart`, and `CSVHandler` classes.

```bash
pip install aspose.cells
```

After installation, verify the setup by importing the library and instantiating a `Workbook`. No additional configuration is required.

```python
import aspose.cells

workbook = aspose.cells.Workbook()
```

## Getting Started

Aspose.Cells FOSS provides core spreadsheet functionality for Python developers. Use the `Workbook` class to create and manipulate Excel files, and the `Cell` and `Cells` classes to access and `modify` individual `cells` or `ranges`. The library supports CSV, JSON, and Markdown export via `CSVHandler`, `JsonHandler`, and `MarkdownHandler`.

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()

# Access the first worksheet and set a cell value
worksheet = workbook.worksheets[0]
worksheet.cells.cell(0, 0).value = "Hello, Aspose.Cells FOSS!"

# Save as XLSX
workbook.save("output.xlsx")
```

## Developer Guide

The Developer Guide for Aspose.Cells FOSS covers core operations for working with Excel files in Python. Use the `Workbook` class to load, create, and manage spreadsheets, and access individual `Worksheet` objects via the `worksheets` collection. `Cell`-level manipulation is handled through the `Cells` collection and `Cell` class, supporting `value` assignment, `formula` evaluation, and `comment` management.

Data interchange formats are supported via dedicated handler classes: `CSVHandler` for CSV import/export, `JsonHandler` for JSON export, and `MarkdownHandler` for Markdown export. `Chart` creation and modification use the `ChartCollection`, `Chart`, and `ChartSeries` classes, with supported types including LINE, BAR, PIE, AREA, and SCATTER. Encryption is limited to Agile mode using `AgileEncryptionParameters` and cipher algorithms like AES_128, AES_192, and AES_256.

```python
import aspose.cells

# Create a new workbook and add a worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set a cell value and formula
cell = worksheet.cells.cell(0, 0)
cell.value = "Total"
cell = worksheet.cells.cell(1, 0)
cell.formula = "=A1*2"

# Save to XLSX
workbook.save("output.xlsx")
```

## See Also

- Learn how to use the [`Workbook`](#) class to create and manage Excel files in Python
- Explore [`Cell`](#) and [`Cells`](#) operations for reading and writing data in spreadsheets
- Review [`Chart`](#) and [`ChartCollection`](#) classes for visualizing data in Python cells
- Understand [`CSVHandler`](#), [`JsonHandler`](#), and [`MarkdownHandler`](#) for exporting data to common formats
