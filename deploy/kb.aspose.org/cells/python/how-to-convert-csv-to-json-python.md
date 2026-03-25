---
canonical: https://kb.aspose.org/cells/python/convert-csv-json-python/
canonical_import: aspose.cells
date: '2026-03-22T08:56:20Z'
dateModified: '2026-03-22T08:56:20Z'
datePublished: '2026-03-22T08:56:20Z'
description: Developers can load a workbook from one format and `save` it to another
  using `CSVHandler`, `JsonHandler`, or `MarkdownHandler` methods.
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
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.Cells FOSS | Guide
slug: convert-csv-json-python
title: How to Convert File Formats with Aspose.Cells FOSS
type: howto_article
url: /kb.aspose.org/cells/python/convert-csv-json-python/
weight: 13
---

## Problem

Aspose.Cells FOSS enables conversion between spreadsheet formats using the `Workbook` class and format-specific handlers. Developers can load a workbook from one format and `save` it to another using `CSVHandler`, `JsonHandler`, or `MarkdownHandler` methods.

```python
import aspose.cells

# Load a workbook from an existing file
workbook = aspose.cells.Workbook("input.xlsx")

# Save as CSV using CSVHandler
aspose.cells.CSVHandler.save_csv(workbook, "output.csv", None)
```

## Prerequisites

To use Aspose.Cells FOSS for file format conversion in Python, ensure you have Python 3.7 or later installed. Install the package using pip with the command: pip install aspose.`cells`. The library requires no additional system dependencies and integrates cleanly into environments such as VS Code, Spyder, or Jupyter notebooks.

- Python 3.7+ runtime environment
- Install via: `pip install aspose.cells`
- No external system dependencies required

## Conversion Steps

Aspose.Cells FOSS enables programmatic conversion between spreadsheet formats using the `Workbook` class and format-specific handlers. Conversion follows a consistent pattern: load the source file into a `Workbook`, apply format-specific options if needed, and `save` to the target format using the appropriate handler method.

### Step 1: Load Source File

Initialize a `Workbook` object by loading the source file. Supported source formats include XLSX, XLS, CSV, and others. The `Workbook` constructor accepts a file path string to open the spreadsheet.

```python
import aspose.cells

workbook = aspose.cells.Workbook("source.xlsx")
```

### Step 2: Configure Conversion Options

Select the appropriate handler based on the target format. For CSV output, use `CSVHandler`; for JSON, use `JsonHandler`; for Markdown, use `MarkdownHandler`. Each handler provides static methods to `save` the workbook in the target format with optional configuration via `CSVSaveOptions`, `JsonSaveOptions`, or `MarkdownSaveOptions`.

### Step 3: Save to Target Format

Call the handler's `save` method with the `Workbook` instance and target file path. For example, use `CSVHandler.save_csv()` to export to CSV, `JsonHandler.save_json()` for JSON, or `MarkdownHandler.save_markdown()` for Markdown. All handlers write directly to disk and support optional parameters for fine-grained control.

```python
aspose.cells.CSVHandler.save_csv(workbook, "output.csv", None)
```

## Code Example

This section demonstrates converting spreadsheet data to other formats using Aspose.Cells FOSS. The `Workbook` class loads and manages Excel files, while format-specific handlers like `CSVHandler`, `JsonHandler`, and `MarkdownHandler` enable export to CSV, JSON, and Markdown respectively.

```python
import aspose.cells

# Load a workbook
workbook = aspose.cells.Workbook("input.xlsx")

# Export to CSV
aspose.cells.CSVHandler.save_csv(workbook, "output.csv", None)

# Export to JSON
aspose.cells.JsonHandler.save_json(workbook, "output.json", None)

# Export to Markdown
aspose.cells.MarkdownHandler.save_markdown(workbook, "output.md", None)
```

## Supported Formats

Aspose.Cells FOSS supports conversion between common spreadsheet formats using the `Workbook` class and format-specific handlers like `CSVHandler`, `JsonHandler`, and `MarkdownHandler`. The library enables programmatic conversion of Excel files to and from text-based formats while preserving structure and data integrity.

| Format | Extension | Notes |
|--------|-----------|-------|
| Excel (Open XML) | .xlsx | Primary input/output format; supports full workbook structure |
| CSV | .csv | Handled via `CSVHandler` static methods |
| JSON | .json | Exported via `JsonHandler.save_json()` |
| Markdown | .md | Exported via `MarkdownHandler.save_markdown()` |
| Text | .txt | Plain text export supported via `cell` `value` extraction |

## See Also

Aspose.Cells FOSS provides robust support for spreadsheet operations in Python. Developers can leverage core classes like `Workbook`, `Worksheet`, `Cells`, and `Cell` to manipulate data efficiently. The library supports common file conversions and formatting tasks through methods such as `save()` and `save()` variants.

- [Frequently asked questions](/kb.aspose.org/cells/python/faq/)
- [Python API introduction](/blog.aspose.org/cells/python/cells-foss-python/)
- [Chart creation examples](/blog.aspose.org/cells/python/create-charts-spreadsheets/)
- [Formula handling guide](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Core spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
