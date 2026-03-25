---
canonical: https://reference.aspose.org/cells/_index/
canonical_import: aspose.cells
code_import: aspose.cells
date: '2026-03-25T14:37:09Z'
dateModified: '2026-03-25T14:37:09Z'
datePublished: '2026-03-25T14:37:09Z'
description: The API provides classes to create, read, and manipulate Excel-compatible
  workbooks and their components using the canonical `aspose.cells` import.
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
lastmod: '2026-03-25T14:37:09Z'
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

This section covers the core spreadsheet operations supported by Aspose.Cells FOSS for Python. The API provides classes to create, read, and manipulate Excel-compatible workbooks and their components using the canonical `aspose.cells` import.

- Create and manage workbooks and worksheets using the `Workbook` and `Worksheet` classes
- Read and write cell values, formulas, and comments via the `Cell` and `Cells` classes
- Export data to CSV, JSON, and Markdown formats using `CSVHandler`, `JsonHandler`, and `MarkdownHandler`
- Add and configure charts (line, bar, pie, area, scatter, combo, waterfall, box-whisker) through the `ChartCollection` and `Chart` classes

## Quick Install

This section covers installation and setup for Aspose.Cells FOSS, the Python API for spreadsheet creation, reading, and conversion. The library supports core Excel operations including workbook management, `cell` manipulation, and chart generation using the canonical `aspose.cells` module.

```bash
pip install aspose-cells
```

After installation, verify the setup by importing the module and creating a new workbook. Use `import aspose.cells` to confirm the package loads without errors.

## Getting Started

This section covers the Python API for spreadsheet creation, reading, and conversion using Aspose.Cells FOSS. The core functionality centers on the `Workbook` class for managing files and the `Worksheet`, `Cell`, and `Cells` classes for interacting with individual `cells` and collections.

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()

# Access the first worksheet
worksheet = workbook.worksheets[0]

# Write a value to cell A1
cell = worksheet.cells.cell(0, 0)
cell.value = "Hello, Aspose.Cells FOSS!"

# Save the workbook
workbook.save("output.xlsx")
```

## Developer Guide

This section covers the core Python API for spreadsheet creation, reading, and conversion in Aspose.Cells FOSS. It focuses on the primary classes developers use to manipulate Excel-like data: `Workbook` for file-level operations, `Worksheet` and `Cells` for `cell`-level access, and handler classes for exporting to structured formats like CSV, JSON, and Markdown.

Use `Workbook` to load, create, and manage spreadsheet files. `Add` or `remove` `worksheets` via `add_worksheet()` and `remove_worksheet()`, then access individual `cells` through the `Cells` collection using 1-based indexing. The `Cell` class provides direct read/write access to `value`, `formula`, and `style`. For structured data exchange, use `CSVHandler`, `JsonHandler`, and `MarkdownHandler` to import/export data without requiring Excel installed.

- Create and manage workbooks and worksheets with `Workbook` and `Worksheet`
- Read/write cell data using `Cell` and `Cells` with 1-based row/column indexing
- Export to CSV, JSON, and Markdown using `CSVHandler`, `JsonHandler`, and `MarkdownHandler`
- Apply styling, formulas, and basic charting via `Chart`, `ChartCollection`, and `ChartType`

## See Also

This section covers the Python API for spreadsheet creation, reading, and conversion in Aspose.Cells FOSS. It includes core classes for workbook management, `cell` operations, and chart generation.

- [`Workbook`](#reference-workbook) — Create, load, and manage Excel workbooks with multiple worksheets.
- [`Cell`](#reference-cell) — Read and write cell values, formulas, and comments.
- [`Chart`](#reference-chart) — Add and configure charts including line, bar, pie, and scatter types.
- [`CSVHandler`](#reference-csvhandler) — Import and export data using CSV format.
- [`JsonHandler`](#reference-jsonhandler) — Export workbook data to JSON format.
