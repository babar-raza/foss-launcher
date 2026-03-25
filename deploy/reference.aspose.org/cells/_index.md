---
canonical: https://reference.aspose.org/cells/_index/
canonical_import: aspose.cells
code_import: aspose.cells
date: '2026-03-24T18:12:26Z'
dateModified: '2026-03-24T18:12:26Z'
datePublished: '2026-03-24T18:12:26Z'
description: You can `add`, `remove`, and access individual `worksheets` via `add_worksheet()`,
  `remove_worksheet()`, and `get_worksheet()`. `Cell`-level operations are...
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
lastmod: '2026-03-24T18:12:26Z'
page_role: toc
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Cells FOSS Reference _Index
slug: _index
title: Reference _Index
type: toc
url: /reference.aspose.org/cells/_index/
weight: 5
---

## Capabilities

This section covers the core spreadsheet processing capabilities of Aspose.Cells FOSS for Python, including workbook management, `cell` operations, and chart creation using the documented API surface.

The `Workbook` class enables creation, loading, and manipulation of Excel files. You can `add`, `remove`, and access individual `worksheets` via `add_worksheet()`, `remove_worksheet()`, and `get_worksheet()`. `Cell`-level operations are handled through the `Cell` and `Cells` classes, supporting `value` and `formula` read/write, clearing, and `comment` management.

`Chart` support includes line, bar, pie, area, scatter, combo, waterfall, and box-whisker types via the `ChartCollection` and `Chart` classes. Charts can be added with `add_line()`, `add_bar()`, `add_pie()`, and other `type`-specific methods, with series and axis configuration through `ChartSeries`, `ChartAxis`, and related objects.

- Create and edit Excel workbooks and worksheets
- Read/write cell values, formulas, and comments
- Apply cell styling and formatting
- Add and configure charts (line, bar, pie, scatter, combo, waterfall, etc.)
- Export to CSV, JSON, and Markdown formats using `CSVHandler`, `JsonHandler`, and `MarkdownHandler`

## Quick Install

This section covers installation and setup for Aspose.Cells FOSS, the Python API for spreadsheet creation, reading, and conversion. The library supports core Excel operations including workbook management, `cell` manipulation, and chart generation using the canonical `aspose.cells` module.

```bash
pip install aspose-cells
```

After installation, verify the setup by importing the library and creating a new `Workbook` instance. Use `import aspose.cells` — no aliases or alternative paths are valid. Confirm that `Workbook()` initializes without errors and that `worksheets` collection is accessible.

## Getting Started

This section covers the Python API for spreadsheet creation, reading, and conversion using Aspose.Cells FOSS. The core functionality centers on the `Workbook` class for managing files and the `Worksheet`/`Cells`/`Cell` hierarchy for data manipulation.

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()

# Access the first worksheet
worksheet = workbook.worksheets[0]

# Write a value to cell A1
worksheet.cells.cell(0, 0).value = "Hello, Aspose.Cells FOSS!"

# Save to XLSX
workbook.save("output.xlsx")
```

## Developer Guide

This section covers the core Python API for spreadsheet creation, reading, and conversion using Aspose.Cells FOSS. It focuses on the primary classes developers use to manipulate Excel files programmatically.

The `Workbook` class serves as the entry point for loading, creating, and managing Excel files. Use `add_worksheet()` or `create_worksheet()` to `add` new sheets, and `get_worksheet()` to access existing ones. The `worksheets` property provides indexed access to all sheets in the workbook.

`Cell`-level operations are handled via the `Cell` and `Cells` classes. Access individual `cells` using `Cells.cell(row, column)` (1-based indexing), then set or read `value`, `formula`, or `style`. Use `clear()`, `clear_value()`, or `clear_formula()` to reset `cell` contents as needed.

Export to non-Excel formats is supported through dedicated handler classes: `CSVHandler` for CSV, `JsonHandler` for JSON, and `MarkdownHandler` for Markdown. Each provides static methods to `save` to file or string representations.

## See Also

This section covers the Python API for spreadsheet creation, reading, and conversion in Aspose.Cells FOSS. It includes core classes for workbook management, `cell` operations, and chart generation.

- [`Workbook`](#) — Create, load, and manage Excel workbooks with multiple worksheets.
- [`Cell`](#) — Read and write cell values, formulas, and comments.
- [`Chart`](#) — Add and configure charts including line, bar, pie, and scatter types.
- [`CSVHandler`](#) — Import and export data using CSV format with configurable options.
- [`JsonHandler`](#) — Export workbook data to JSON format or dictionaries.
