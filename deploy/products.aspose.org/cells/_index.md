---
canonical: https://products.aspose.org/cells/_index/
canonical_import: aspose.cells
date: '2026-03-23T13:16:22Z'
dateModified: '2026-03-23T13:16:22Z'
datePublished: '2026-03-23T13:16:22Z'
description: It enables developers to programmatically manage workbooks, `worksheets`,
  and `cells` using the canonical `import aspose.cells` module.
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

Aspose.Cells FOSS provides a Python-native API for creating, editing, and converting Excel files without requiring Microsoft Excel. It enables developers to programmatically manage workbooks, `worksheets`, and `cells` using the canonical `import aspose.cells` module.

Key capabilities include `cell` `value` and `formula` manipulation, comprehensive styling (fonts, number formats, alignment), multi-worksheet management, and chart generation for line, bar, pie, scatter, and other supported types. The library supports AES encryption via the Agile scheme and workbook/worksheet `protection` features.

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Set a cell value
worksheet.cells["A1"].value = "Hello, Excel!"

# Save with Agile encryption
params = aspose.cells.AgileEncryptionParameters()
workbook.save("output.xlsx", params)
```

## Key Features

Aspose.Cells FOSS is a pure Python library for working with Excel files without requiring Microsoft Excel. It supports core spreadsheet operations including reading, writing, and modifying workbooks and `worksheets`, with full support for `cell` styling, formulas, and multiple `worksheets`. The library is licensed under the MIT License and requires Python 3.7+ with pycryptodome >= 3.15.0 and olefile >= 0.46 as dependencies.

- Create and edit Excel workbooks and worksheets using the `Workbook` and `Worksheet` classes.
- Read and write cell values, formulas, and styles with the `Cell` and `Cells` classes.
- Apply workbook and worksheet protection to secure sensitive data using built-in protection features.
- Save files with AES encryption using the Agile encryption scheme for secure document handling.
- Export data to common formats including CSV, JSON, and Markdown using dedicated handler classes.

## Quick Start

Aspose.Cells FOSS is a permissively licensed Python library for working with Excel files. It supports creating, editing, and converting spreadsheets using the canonical `aspose.cells` module. The library is distributed under the MIT License and requires Python 3.7+ with pycryptodome >= 3.15.0 and olefile >= 0.46 as dependencies.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Write a value to cell A1
worksheet.cells.cell(0, 0).value = "Hello, Aspose.Cells FOSS!"

# Save the workbook
workbook.save("output.xlsx")
```

## See Also

Aspose.Cells FOSS requires Python 3.7 or higher and depends on pycryptodome >= 3.15.0 and olefile >= 0.46. The library is licensed under the MIT License and supports core Excel features including workbook and worksheet `protection` and AES encryption using the Agile scheme.

- [Explore real-world use cases](/kb.aspose.org/cells/python/developer-guide/use-cases/)
- [Discover the Python API introduction](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Create all chart types in spreadsheets](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas effectively](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform common spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
