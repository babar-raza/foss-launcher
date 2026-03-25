---
canonical: https://blog.aspose.org/cells/python/introducing-cells-foss-python/
canonical_import: aspose.cells
date: '2026-03-23T13:16:22Z'
dateModified: '2026-03-23T13:16:22Z'
datePublished: '2026-03-23T13:16:22Z'
description: It provides a clean, object-oriented API for creating, editing, and converting
  spreadsheet data without requiring Microsoft Excel. The library centers on...
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
lastmod: '2026-03-23T13:16:22Z'
page_role: blog_announcement
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS Introducing Cells Foss Python
slug: introducing-cells-foss-python
title: Introducing Cells Foss Python
type: blog_announcement
url: /blog.aspose.org/cells/python/introducing-cells-foss-python/
weight: 16
---

## Introduction

Aspose.Cells FOSS brings robust Excel file handling to Python developers. It provides a clean, object-oriented API for creating, editing, and converting spreadsheet data without requiring Microsoft Excel. The library centers on core classes like `Workbook`, `Worksheet`, and `Cell`, enabling programmatic control over spreadsheets in environments such as VS Code, Spyder, or any Python IDE.

Key capabilities include reading and writing `cell` `values` and formulas, managing multiple `worksheets`, and generating `charts` using supported types like LINE, BAR, PIE, and AREA. Export functionality covers CSV, JSON, and Markdown formats via dedicated handlers: `CSVHandler`, `JsonHandler`, and `MarkdownHandler`. This makes Aspose.Cells FOSS ideal for automation workflows involving data export, reporting, and integration with tools like pandas or Jupyter notebooks.

## Key Highlights

Aspose.Cells FOSS delivers a focused, open-source Python API for working with spreadsheet data. Built around core classes like `Workbook`, `Worksheet`, `Cell`, and `Cells`, it enables developers to programmatically create, read, and `modify` Excel-compatible files using standard Python tooling such as VS Code or Spyder.

- The `Workbook` class provides programmatic control over Excel workbooks, supporting operations like adding, removing, and accessing worksheets via `add_worksheet()` and `get_worksheet()`.
- Cell-level manipulation is handled by the `Cell` class, which exposes methods such as `is_empty()`, `clear_value()`, and `set_comment()` for granular data control.
- The `Cells` collection offers convenient utilities like `column_index_from_string()` and `coordinate_from_string()` to translate between human-readable and programmatic cell references.
- Export to modern data formats is supported via static handlers: `CSVHandler` for CSV I/O, `JsonHandler` for JSON export, and `MarkdownHandler` for Markdown output.
- Chart creation and customization is available through the `ChartCollection` and `Chart` classes, supporting line, bar, pie, area, and scatter chart types via dedicated methods like `add_line()` and `add_bar()`.

## Getting Started

Aspose.Cells FOSS enables programmatic Excel file handling in Python. Developers can create workbooks, manipulate `cells` via the `Workbook` and `Cell` classes, and export data to formats like CSV, JSON, and Markdown using dedicated handler classes.

```python
import aspose.cells

# Create a new workbook and add a worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Write a value to cell A1
cell = worksheet.cells.cell(0, 0)
cell.value = "Hello, Aspose.Cells FOSS!"

# Save to XLSX
workbook.save("output.xlsx")
```

## See Also

- [Create all chart types](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
- [Convert file formats](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
- [Fix common errors](/kb.aspose.org/cells/python/how-to-fix-spreadsheets-errors-python/)
