---
canonical: https://docs.aspose.org/cells/python/developer-guide/installation/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: It supports core spreadsheet operations such as cell value and formula
  handling, styling, auto-filtering, and chart creation for supported types.
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
page_role: workflow_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS Installation
slug: installation
summary: ''
title: Installation
type: workflow_page
url: /docs.aspose.org/cells/python/developer-guide/installation/
weight: 3
---

## Overview

Aspose.Cells FOSS enables Python developers to create, read, and modify Excel files without requiring [identifier omitted] Excel. It supports core spreadsheet operations such as cell value and formula handling, styling, auto-filtering, and chart creation for supported types.

To use Aspose.Cells FOSS, ensure your environment meets the minimum requirements: Python 3.7 or higher, pycryptodome >= 3.15.0, and olefile >= 0.46. [identifier omitted] dependencies are necessary for runtime encryption and legacy file format support.

```bash
pip install aspose-cells-foss>=26.3.1
```

```python
import aspose.cells
print('[identifier omitted] successful')
```

## Key Features

- Create and edit Excel files in XLSX format with full support for workbooks and multiple worksheets.
- Read and write cell values and formulas using the `Cell` class for precise data manipulation.
- Apply comprehensive styling including fonts, borders, number formats, and alignment options like `Alignment`.
- Use `AutoFilter` to apply and manage filtering and sorting logic directly on worksheet data.
- Handle encrypted XLSX files using CFB-based encryption with `CFBReader` and `CFBWriter` components.
- Parse and format cell values per ECMA-376 standards using `CellValueHandler` for interoperability.

## Prerequisites

Aspose.Cells FOSS requires Python 3.7 or higher and two runtime dependencies: pycryptodome >= 3.15.0 and olefile >= 0.46. [identifier omitted] dependencies are automatically installed when you install the package via pip.

```bash
pip install aspose-cells-foss>=26.3.1
```

```python
import aspose.cells
print('[identifier omitted] successful')
```

## Code Examples

Aspose.Cells FOSS requires Python 3.7 or higher to run. Before installing, verify your Python version with `python --version`. The library depends on two runtime packages: pycryptodome >= 3.15.0 and olefile >= 0.46. [identifier omitted] are automatically installed when you run the pip command below, but you can install them manually if needed.

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Write a value into cell A1
cell = worksheet.cells.get("A1")
cell.value = "[identifier omitted], Aspose.Cells FOSS!"

# Save the workbook as an XLSX file
workbook.save("output.xlsx")
```

## Best Practices

[identifier omitted] your environment meets Aspose.Cells FOSS requirements before installation. The library requires Python 3.7 or higher, and two runtime dependencies: pycryptodome >= 3.15.0 and olefile >= 0.46. [identifier omitted] dependencies are automatically installed via pip when you install aspose-cells-foss, but verify them manually if using offline or constrained environments.

- Confirm Python version with `python --version` or `python3 --version`.
- Install Aspose.Cells FOSS using `pip install aspose-cells-foss>=26.3.1`.
- Verify installation by running `import aspose.cells` without errors.
- Check dependency versions with `pip show pycryptodome olefile` if troubleshooting.

## Troubleshooting

### [identifier omitted] installation issues

### Python version too low

Aspose.Cells FOSS requires Python 3.7 or higher. If you encounter an import error or syntax error during installation, verify your Python version using `python --version`. [identifier omitted] to Python 3.7+ if needed, as older versions lack features required by the library.

The library depends on pycryptodome >= 3.15.0 for encryption operations. If you see an ImportError for [identifier omitted] or [identifier omitted], install or upgrade pycryptodome using `pip install pycryptodome>=3.15.0`. This ensures compatibility with Agile encryption features used internally by Aspose.Cells FOSS.

### [identifier omitted] olefile dependency

olefile >= 0.46 is required to parse [identifier omitted] compound files, such as legacy XLS formats. If you encounter errors related to olefile during file loading, run `pip install olefile>=0.46`. This dependency is essential for reading older Excel formats and encrypted workbooks.

### [identifier omitted] with openpyxl

Aspose.Cells FOSS does not depend on openpyxl, but installing both libraries in the same environment can cause import conflicts due to overlapping module names. To avoid issues, use virtual environments: `python -m venv env && source env/bin/activate && pip install aspose-cells-foss`. If you previously used `pip install openpyxl`, ensure clean isolation before installing Aspose.Cells FOSS.

## FAQ

### [identifier omitted] Python version do I need for Aspose.Cells FOSS?

Aspose.Cells FOSS requires Python 3.7 or higher. [identifier omitted] your environment meets this minimum version to avoid compatibility issues during installation or runtime.

### [identifier omitted] dependencies must be installed alongside Aspose.Cells FOSS?

The library depends on two runtime packages: pycryptodome >= 3.15.0 and olefile >= 0.46. [identifier omitted] are automatically installed via pip when you run `pip install aspose-cells-foss>=26.3.1`, but verify them manually if installing from source.

### [identifier omitted] Aspose.Cells FOSS require openpyxl?

No, Aspose.Cells FOSS does not require openpyxl. It is a standalone library and does not depend on openpyxl, pandas, or other third-party Excel libraries. You can install aspose-cells-foss independently using `pip install aspose-cells-foss>=26.3.1`.

## API Reference Summary

Aspose.Cells FOSS requires Python 3.7 or higher to run. [identifier omitted] your environment meets this minimum version before installation. The library also depends on two specific packages: pycryptodome >= 3.15.0 for encryption support and olefile >= 0.46 for handling [identifier omitted] structured storage. [identifier omitted] dependencies are automatically installed when you run the pip command below.

```bash
pip install aspose-cells-foss>=26.3.1
```

After installation, verify the setup by importing the package and printing a success message. The import path is `aspose.cells` (note the dot, not underscore). This confirms all runtime dependencies—including pycryptodome and olefile—were correctly resolved.

```python
import aspose.cells
print('[identifier omitted] successful')
```

## See Also

Aspose.Cells FOSS requires Python 3.7 or higher, pycryptodome >= 3.15.0, and olefile >= 0.46 as runtime dependencies. [identifier omitted] these are installed before using the library to avoid import or runtime errors.

- [Get started with basic usage](/docs.aspose.org/cells/python/developer-guide/getting-started/)
- [Add and manage cell comments](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Protect workbooks and worksheets](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
