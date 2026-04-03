---
canonical: https://reference.aspose.org/cells/_index/
canonical_import: aspose.cells
code_import: aspose.cells
date: '2026-03-27T07:02:41Z'
dateModified: '2026-03-27T07:02:41Z'
datePublished: '2026-03-27T07:02:41Z'
description: The library enables programmatic creation, modification, and conversion
  of Excel-compatible files using the `Workbook` and `Worksheet` classes.
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
lastmod: '2026-03-27T07:02:41Z'
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

Aspose.Cells FOSS provides core spreadsheet processing capabilities for Python developers. The library enables programmatic creation, modification, and conversion of Excel-compatible files using the `Workbook` and `Worksheet` classes.

`Cell`-level operations are supported via the `Cell` and `Cells` classes, allowing read/write access to `values`, formulas, styles, and comments. The `Cells` class includes utility methods for coordinate conversions between row/column indices and A1-`style` references.

`Chart` generation and customization are available through the `Chart`, `ChartCollection`, and `ChartSeries` classes, supporting line, bar, pie, area, scatter, and combo chart types. Charts can be added to `worksheets` with configurable `axes`, legends, and 3D view settings.

Data import and export to non-Excel formats is handled by dedicated handler classes: `CSVHandler` for comma-separated `values`, `JsonHandler` for JSON serialization, and `MarkdownHandler` for Markdown output. All handlers provide both file and string-based operations.

## Quick Install

This section covers installation and setup for Aspose.Cells FOSS, the Python API for spreadsheet creation, reading, and conversion. The library supports core Excel operations via the `Workbook`, `Worksheet`, `Cell`, and `Cells` classes.

```bash
pip install aspose.cells
```

After installation, verify the setup by importing the module and creating a new workbook. Run `import aspose.cells` followed by `wb = aspose.cells.Workbook()` in a Python environment such as VS Code, Spyder, or a terminal. No additional configuration is required.

## Getting Started

This section covers the foundational usage of Aspose.Cells FOSS for Python, focusing on workbook creation and basic `cell` manipulation. The `Workbook` class serves as the entry point for loading or creating Excel files, while `Worksheet`, `Cells`, and `Cell` provide access to spreadsheet structure and data.

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()

# Access the first worksheet
worksheet = workbook.worksheets[0]

# Write a value to cell A1
cells = worksheet.cells
cells.cell(0, 0).value = "Hello, Aspose.Cells FOSS!"

# Save the workbook
workbook.save("output.xlsx")
```

## Developer Guide

This section covers the Python API for spreadsheet creation, reading, and conversion using Aspose.Cells FOSS. It focuses on core classes like `Workbook`, `Worksheet`, `Cells`, and `Cell` for programmatic spreadsheet manipulation.

Use `Workbook` to load, create, and manage spreadsheet files. `Add` or `remove` `worksheets` via `add_worksheet()` and `remove_worksheet()`, then access individual `cells` through the `Cells` collection using 1-based indexing. Read or write `cell` `values` and formulas directly via the `Cell` class.

Export data to alternative formats using dedicated handlers: `CSVHandler` for CSV import/export, `JsonHandler` for JSON serialization, and `MarkdownHandler` for Markdown output. These static methods operate on `Workbook` instances and support optional configuration objects where available.

## See Also
