---
canonical: https://docs.aspose.org/cells/_index/
canonical_import: aspose.cells
code_import: aspose.cells
date: '2026-03-25T14:37:09Z'
dateModified: '2026-03-25T14:37:09Z'
datePublished: '2026-03-25T14:37:09Z'
description: Developers can `add` new `worksheets` with `create_worksheet()` or `add_worksheet()`,
  access individual `cells` through `Cells.cell(row, column)`, and...
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
seoTitle: Aspose.Cells FOSS Docs _Index
slug: _index
title: Docs _Index
type: toc
url: /docs.aspose.org/cells/_index/
weight: 2
---

## Capabilities

This section covers the core spreadsheet processing capabilities of Aspose.Cells FOSS for Python, focusing on workbook management, `cell` manipulation, and data export formats supported by the documented API surface.

- Create and manage workbooks and worksheets using the `Workbook` and `Worksheet` classes
- Read and write cell values, formulas, and comments via the `Cell` and `Cells` classes
- Export workbooks to CSV, JSON, and Markdown using `CSVHandler`, `JsonHandler`, and `MarkdownHandler`
- Add and configure charts (line, bar, pie, area, scatter, combo, waterfall, box-whisker) using `ChartCollection` and `Chart` classes

The `Workbook` class serves as the primary entry point for loading, creating, and manipulating Excel-like structures. Developers can `add` new `worksheets` with `create_worksheet()` or `add_worksheet()`, access individual `cells` through `Cells.cell(row, column)`, and `modify` `cell` content using `Cell.value`, `Cell.formula`, and `Cell.set_comment()`. Export operations are handled by static methods in dedicated handler classes: `CSVHandler.load_csv()` and `save_csv()` for tabular data interchange, `JsonHandler.save_json()` for structured data export, and `MarkdownHandler.save_markdown()` for documentation-friendly output.

## Quick Install

This section covers installation and setup for Aspose.Cells FOSS, the Python API for spreadsheet creation, reading, and conversion. Use pip to install the package, then verify the installation by importing the core `Workbook` class.

```bash
pip install aspose-cells
```

After installation, verify the setup by running `import aspose.cells` in your Python environment. Confirm success by instantiating a `Workbook` object: `workbook = aspose.cells.Workbook()`. This confirms the library is correctly installed and ready for use in Python `cells` (e.g., in VS Code, Spyder, or Jupyter).

## Getting Started

This section covers the Python API for spreadsheet creation, reading, and conversion using Aspose.Cells FOSS. The core functionality centers on the `Workbook` class for managing files and the `Worksheet`/`Cells`/`Cell` hierarchy for data manipulation.

Key operations include loading and saving workbooks, accessing and modifying `cell` `values` and formulas, managing `worksheets`, and creating `charts` using supported types like LINE, BAR, PIE, and AREA.

## Developer Guide

This section covers the Python API for spreadsheet creation, reading, and conversion using Aspose.Cells FOSS. Developers work directly with core classes like `Workbook`, `Worksheet`, `Cells`, and `Cell` to manipulate spreadsheet data, apply formatting, and manage workbook structure.

Use `Workbook` to load, create, and manage multi-sheet workbooks; `add` or `remove` `worksheets` via `add_worksheet()` and `remove_worksheet()`. Access individual `cells` through `Cells.cell(row, column)` (1-based indexing) and set `values`, formulas, or styles. The `CSVHandler`, `JsonHandler`, and `MarkdownHandler` classes support exporting workbook data to structured text formats.

Charts are created using `ChartCollection` methods like `add_line()`, `add_bar()`, and `add_pie()`, with series and `axes` configured via `ChartSeries`, `ChartAxis`, and related types. All operations respect the canonical import `import aspose.cells` and use only the documented API surface.

## See Also

This section covers the Python API for spreadsheet creation, reading, and conversion in Aspose.Cells FOSS. It includes core classes for workbook management, `cell` operations, and chart generation.

- Working with `Workbook` and `Worksheet` — create, load, and manage spreadsheet files and sheets
- Cell manipulation with `Cell` and `Cells` — read, write, and clear cell values and formulas
- Chart creation using `Chart`, `ChartCollection`, and `ChartType` — generate line, bar, pie, and other supported chart types
- Data export via `CSVHandler`, `JsonHandler`, and `MarkdownHandler` — convert workbooks to CSV, JSON, and Markdown formats
