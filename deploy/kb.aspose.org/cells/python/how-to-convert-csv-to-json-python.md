---
canonical: https://kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: '[identifier omitted] can load a file into a Workbook instance and export
  it to CSV using `CSVHandler.save_csv()` or `CSVHandler.save_csv_to_string()`.'
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
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.Cells FOSS | Guide
slug: how-to-convert-csv-to-json-python
title: How to Convert File Formats with Aspose.Cells FOSS
type: howto_article
url: /kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/
weight: 13
---

## Problem

Aspose.Cells FOSS enables conversion between spreadsheet formats such as XLSX and CSV using the Workbook class and `CSVHandler` methods. [identifier omitted] can load a file into a Workbook instance and export it to CSV using `CSVHandler.save_csv()` or `CSVHandler.save_csv_to_string()`.

## Prerequisites

Aspose.Cells FOSS -- [identifier omitted] installation and input file.

- Python 3.7+ (or the supported runtime for python)
- Install via pip: `pip install aspose-cells-foss`

```python
import aspose.cells
```

## Conversion Steps

### Step 1: Load [identifier omitted] File

Use the Workbook class to load the source file. Aspose.Cells FOSS supports loading common spreadsheet formats such as XLSX, CSV, and others. The Workbook constructor accepts a file path or stream containing the source document.

### Step 2: Configure [identifier omitted] Options

Configure conversion behavior using format-specific options classes. For CSV output, use `CSVSaveOptions` to control delimiters, encoding, and other export settings. For other formats, options are applied implicitly or via format-specific save methods defined in the API surface.

### Step 3: Save to Target Format

Call the appropriate save method on the Workbook instance to write the converted file. Aspose.Cells FOSS provides static methods in `CSVHandler` for CSV export, and direct instance methods for other formats. [identifier omitted] the target file extension matches the intended output format.

## Code Example

This section demonstrates converting between common spreadsheet formats using Aspose.Cells FOSS. The example shows loading a file into a Workbook instance and saving it in a different format using the save() method. [identifier omitted] formats supported by the underlying API surface are covered, ensuring compatibility with the FOSS distribution.

```python
import aspose.cells

# Load an existing Excel file
workbook = aspose.cells.Workbook("input.xlsx")

# Save as CSV
workbook.save("output.csv", aspose.cells.SaveFormat.CSV)

# Save as PDF
workbook.save("output.pdf", aspose.cells.SaveFormat.PDF)
```

## Supported Formats

Aspose.Cells FOSS supports conversion between common spreadsheet formats using classes like Workbook, `CSVHandler`, and `CellValueHandler`. The library enables reading and writing CSV, XLSX, and other standard formats through dedicated handlers.

| Format | [identifier omitted] | [identifier omitted] |
|--------|-----------|-------|
| Excel Open XML | .xlsx | [identifier omitted] supported for read/write operations |
| CSV | .csv | [identifier omitted] via `CSVHandler` static methods |
| XML | .xml | [identifier omitted] for cell value import/export per [identifier omitted]-376 |
| Encrypted XLSX | .xlsx (encrypted) | [identifier omitted] only with Agile encryption via `CFBReader`/`CFBWriter` |

## See Also

- [Frequently asked questions](/kb.aspose.org/cells/python/faq/)
- [Cell comments support details](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Workbook and worksheet protection](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Working with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Core spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
