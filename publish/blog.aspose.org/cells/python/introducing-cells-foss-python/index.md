---
canonical: https://blog.aspose.org/cells/python/introducing-cells-foss-python/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: Aspose.Cells FOSS is a lightweight, dependency-free Python library for creating, reading, and modifying Excel files without Microsoft Excel — MIT licensed.
display_name: Aspose.Cells FOSS
family: cells
keywords:
- python excel library
- create excel python
- aspose cells foss python
- python xlsx library
- python openpyxl alternative
lastmod: '2026-03-11T11:59:24Z'
page_role: blog_announcement
platform: python
reading_time: 2
robots: index, follow
seoTitle: Introducing Aspose.Cells FOSS for Python — Open-Source Excel Library
slug: introducing-cells-foss-python
title: Introducing Aspose.Cells FOSS for Python
type: blog_announcement
url: /blog.aspose.org/cells/python/introducing-cells-foss-python/
weight: 16
---

## Introduction

Aspose.Cells FOSS is a lightweight Python library for creating, reading, and modifying Excel files (`.xlsx` format) without requiring Microsoft Excel. It is released under the MIT License and available on PyPI as `aspose-cells-foss`.

Install it with:

```bash
pip install aspose-cells-foss
```

## What It Can Do

The library covers the full range of spreadsheet operations:

- **Create and edit workbooks**: create new workbooks or modify existing `.xlsx` files using the `Workbook` and `Worksheet` classes
- **Cell operations**: read and write cell values, formulas, and styles
- **Styling**: apply fonts, colors, borders, number formats, and alignment
- **Multiple worksheets**: add, remove, and manage worksheets
- **Data validation**: define dropdown lists, number ranges, and custom validation rules
- **Comments**: add cell comments with author metadata
- **Hyperlinks**: link to URLs, emails, files, and internal references
- **Auto-filters**: filter data ranges with `AutoFilter`
- **Conditional formatting**: apply rules-based formatting to highlight cell values
- **Charts**: create 16 chart types — Line, Bar, Pie, Area, Scatter, Waterfall, Combo, Stock, Surface, Radar, Treemap, Sunburst, Histogram, Funnel, Box & Whisker, and Map
- **Pictures**: embed images (JPEG, PNG) anchored to cells
- **Drawing shapes**: add rectangles, ovals, arrows, text boxes, and 30+ preset shapes
- **Sparklines**: embed mini Line, Column, and Win-Loss charts inside cells
- **Excel tables**: create structured tables (`ListObject`) with auto-filter and column headers
- **Page breaks**: add horizontal and vertical page breaks
- **Merge cells**: merge and unmerge cell ranges
- **Password protection**: protect files with AES encryption
- **Export formats**: save as XLSX, CSV, or Markdown

## Quick Start

```python
from aspose_cells import Workbook

# Create a new workbook
workbook = Workbook()
worksheet = workbook.worksheets[0]

# Write values
worksheet.cells["A1"].put_value("Hello")
worksheet.cells["B1"].put_value("World")
worksheet.cells["A2"].put_value(42)

# Save
workbook.save("output.xlsx")
```

Reading an existing file:

```python
from aspose_cells import Workbook

workbook = Workbook("input.xlsx")
worksheet = workbook.worksheets[0]
value = worksheet.cells["A1"].value
print(f"A1: {value}")
```

## See Also

- [Creating Charts in Python](/blog.aspose.org/cells/python/creating-charts-python/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Load spreadsheets](/kb.aspose.org/cells/python/how-to-load-spreadsheets-python/)
- [Save spreadsheets](/kb.aspose.org/cells/python/how-to-save-spreadsheets-python/)
