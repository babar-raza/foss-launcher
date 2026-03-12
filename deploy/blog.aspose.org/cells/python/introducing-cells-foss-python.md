---
canonical: https://blog.aspose.org/cells/python/introducing-cells-foss-python/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: This feature enhances data documentation and collaboration by allowing
  comments to include formatted text and identify their author, making it easier to...
display_name: Aspose.Cells FOSS
family: cells
keywords:
- python
- python openpyxl
- openpyxl pandas
- openpyxl in python
- openpyxl documentation
- install openpyxl
- openpyxl cell
- openpyxl pip
lastmod: '2026-03-11T21:00:43Z'
page_role: blog_announcement
platform: python
reading_time: 1
robots: index, follow
seoTitle: The library supports adding and managing cell comments with
slug: introducing-cells-foss-python
title: The library supports adding and managing cell comments with author and rich
  text
type: blog_announcement
url: /blog.aspose.org/cells/python/introducing-cells-foss-python/
weight: 16
---

## Introduction

Aspose.Cells FOSS now supports adding and managing cell comments with author and rich text, enabling developers to embed detailed annotations directly in spreadsheets. This feature enhances data documentation and collaboration by allowing comments to include formatted text and identify their author, making it easier to track feedback and context within Excel files.

In addition to cell comments, the library provides robust workbook and worksheet protection capabilities, including password-based security for both workbook structure and individual sheets. It also supports merging and unmerging cells, a common operation for creating professional report layouts and organizing data visually.

```python
from aspose_cells_foss import Workbook

wb = Workbook()
ws = wb.worksheets[0]
ws.cells.merge(0, 0, 1, 3)          # merge 1 row × 3 cols from A1
ws.cells.unmerge(0, 0, 1, 3)

wb.save("merged_cells.xlsx")
```

## Key Highlights

- Add and manage cell comments with author and rich text formatting using the `Cell.comment` property.
- Create hyperlinks to URLs, email addresses, local files, and internal worksheet references via `Worksheet.hyperlinks.add()`.
- Apply auto-filters to data ranges using the `AutoFilter` class to sort and filter rows interactively.
- Embed sparklines (LINE, COLUMN, WIN_LOSS) directly into cells to visualize trends without full charts.
- Define print areas and insert manual page breaks to control layout for printing.
- Protect workbooks and worksheets with passwords, and merge/unmerge cells for flexible layout design.

```python
from aspose.cells import Workbook, Worksheet

# Create workbook and access worksheet
workbook = Workbook()
worksheet = workbook.worksheets[0]

# Add hyperlink to URL
worksheet.hyperlinks.add("A1", "https://example.com")

# Add sparkline group
from aspose.cells import SparklineType
group = worksheet.sparkline_groups.add(
    sparkline_type=SparklineType.LINE,
    data_range="B2:D2",
    is_vertical=False,
    location_range="E2"
)

# Set print area
worksheet.page_setup.print_area = "A1:H40"

# Save the workbook
workbook.save("output.xlsx")
```

## Getting Started

Aspose.Cells FOSS enables Python developers to programmatically create, edit, and protect Excel workbooks with minimal code. You can apply auto-filters to data ranges, embed images between cells, and secure files with workbook or worksheet password protection—all using the canonical `aspose.cells` API. The library integrates cleanly into existing Python workflows, including those built around openpyxl or pandas.

```python
from aspose.cells import Workbook

# Create a new workbook and access the first worksheet
wb = Workbook()
ws = wb.worksheets[0]

# Apply auto-filter to A1:C10 range
ws.auto_filter.range("A1:C10")

# Embed an image between cells B2 and D4
ws.shapes.add_picture_between_cells("image.png", "B2", "D4")

# Protect workbook structure and the worksheet with a password
wb.settings.protect(password="pw")
ws.protect(password="pw")

# Save the protected workbook
wb.save("output.xlsx")
```

## See Also

Aspose.Cells FOSS provides robust spreadsheet capabilities for Python developers. It supports document properties like title, author, and subject as shown in the code example below. The library also enables manual page breaks, conditional formatting, and cell comment management with author and rich text support. [identifier omitted] features make it a strong alternative to openpyxl in python workflows, especially for projects requiring programmatic Excel generation and editing without external dependencies.

```python
wb.document_properties.title = "My [identifier omitted]"
wb.document_properties.author = "[identifier omitted] [identifier omitted]"
wb.document_properties.subject = "Q4 [identifier omitted]"
```

- [Protect workbooks and worksheets](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Get started with Aspose.Cells FOSS](/products.aspose.org/cells/_index/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Core spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
- [Convert file formats](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
