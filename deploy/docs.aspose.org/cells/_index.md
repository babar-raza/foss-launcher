---
canonical: https://docs.aspose.org/cells/_index/
canonical_import: aspose.cells
code_import: aspose.cells
date: '2026-03-24T16:59:43Z'
dateModified: '2026-03-24T16:59:43Z'
datePublished: '2026-03-24T16:59:43Z'
description: The library enables programmatic creation, reading, and manipulation
  of Excel-compatible files using the `Workbook`, `Worksheet`, and `Cell` classes.
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
lastmod: '2026-03-24T16:59:43Z'
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

This section covers the core spreadsheet processing capabilities of Aspose.Cells FOSS for Python. The library enables programmatic creation, reading, and manipulation of Excel-compatible files using the `Workbook`, `Worksheet`, and `Cell` classes.

- Create and manage workbooks with `Workbook` and `Worksheet` classes
- Read and write cell values, formulas, and comments using `Cell` and `Cells`
- Export data to CSV, JSON, and Markdown formats via `CSVHandler`, `JsonHandler`, and `MarkdownHandler`
- Add and configure charts (line, bar, pie, area, scatter, combo, waterfall) using `ChartCollection` and `Chart`

Aspose.Cells FOSS supports agile encryption for securing workbooks and provides methods to `unprotect` files when the password is known. The `AgileEncryptionParameters` class defines encryption settings compliant with ECMA-376 Part 2, Section 4.

## Quick Install

This section covers installation and setup for Aspose.Cells FOSS, the Python API for spreadsheet creation, reading, and conversion. The library supports core Excel operations including workbook management, `cell` manipulation, and chart generation using the canonical `aspose.cells` module.

```bash
pip install aspose-cells
```

After installation, verify the setup by importing the library and creating a new workbook. The only valid import path is `import aspose.cells`. Confirm successful installation by instantiating the `Workbook` class and accessing its `worksheets` collection.

## Getting Started

This section covers the Python API for spreadsheet creation, reading, and conversion using Aspose.Cells FOSS. The core functionality centers on the `Workbook` class for managing files and the `Worksheet`/`Cells`/`Cell` hierarchy for data manipulation.

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()

# Access the first worksheet
worksheet = workbook.worksheets[0]

# Write a value to cell A1
cell = worksheet.cells.cell(0, 0)
cell.value = "Hello, Aspose.Cells FOSS!"

# Save to file
workbook.save("output.xlsx")
```

## Developer Guide

This section covers the Python API for spreadsheet creation, reading, and conversion using Aspose.Cells FOSS. Developers work directly with core classes like `Workbook`, `Worksheet`, `Cells`, and `Cell` to manipulate spreadsheet data, apply formatting, and manage workbook structure.

Use `Workbook` to load, create, and manage multi-sheet workbooks; `add` or `remove` sheets via `add_worksheet()` and `remove_worksheet()`. Access individual `cells` through `Cells.cell(row, column)` (1-based indexing) and set `values`, formulas, or styles. The `CSVHandler`, `JsonHandler`, and `MarkdownHandler` classes support exporting workbook data to text-based formats.

Charts are created using `ChartCollection` methods like `add_line()`, `add_bar()`, and `add_pie()`. Each chart supports series, `axes`, and 3D view settings via `ChartSeries`, `ChartAxis`, and `ChartView3D`. `Cell`-level operations include reading `value`, `formula`, and `data_type`, and setting comments with `set_comment()`.

## See Also

This section covers the Python API for spreadsheet creation, reading, and conversion in Aspose.Cells FOSS. It includes core classes for workbook management, `cell` operations, and data export to CSV, JSON, and Markdown formats.

- [`Workbook`](#) — Create, load, and manage Excel workbooks with multiple worksheets.
- [`Cell`](#) — Read and write cell values, formulas, and comments.
- [`CSVHandler`](#) — Import and export data using CSV format with configurable options.
- [`JsonHandler`](#) — Export workbook data to JSON or a JSON-serializable dictionary.
- [`MarkdownHandler`](#) — Export workbook data to Markdown format.
