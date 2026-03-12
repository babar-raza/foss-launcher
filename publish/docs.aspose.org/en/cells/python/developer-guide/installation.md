---
canonical: https://docs.aspose.org/cells/python/developer-guide/installation/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: To begin using the library, install it via pip with `pip install aspose-cells-foss>=26.3.1`.
  The library requires Python 3.7 or higher.
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
lastmod: '2026-03-11T11:59:24Z'
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

Aspose.Cells FOSS enables Python developers to read, write, and manipulate spreadsheet files without requiring Microsoft Excel. To begin using the library, install it via pip with `pip install aspose-cells-foss>=26.3.1`. The library requires Python 3.7 or higher.

Once installed, you can work with `core` spreadsheet features such as `cell` value handling, auto `filters`, and `alignment`. For example, the `CellValueHandler` class provides static methods to parse and `format` `cell` values per ECMA-376, while `AutoFilter` exposes methods like `filter_columns()` to retrieve `filter` values.

## Key Features

- Supports reading and writing encrypted XLSX files using the CFB format via `CFBReader` and `CFBWriter`, enabling secure handling of protected workbooks.
- Provides `AutoFilter` to manage filtering logic in worksheets, including retrieving custom filter criteria through `filter_columns()`.
- Enables precise cell manipulation with the `Cell` class, allowing value and formula assignment and retrieval for data-driven workflows.
- Includes `AgileEncryptionParameters` for configuring modern encryption settings compatible with Microsoft Excel standards.
- Offers `CSVHandler`, `CSVLoadOptions`, and `CSVSaveOptions` to streamline import and export of comma-separated data for interoperability with pandas and other tools.

## Prerequisites

Aspose.Cells FOSS requires Python 3.7 or later. Install the package using pip with the command `pip install aspose-cells-foss`. No additional system dependencies are required beyond a standard Python runtime.

```bash
pip install aspose-cells-foss>=26.3.1
```

```python
import aspose_cells
print('Installation successful')
```

After installation, verify the setup by importing `aspose.cells` and printing a confirmation message. The library provides `core` spreadsheet functionality including `cell` manipulation via `Cell`, worksheet management, and auto-`filter` support via `AutoFilter`.

## Code Examples

Aspose.Cells FOSS supports reading and writing Excel files with basic formula evaluation. The lightweight evaluator computes results for simple formulas at read time when cached values are absent. Supported functions include CONCATENATE, CONCAT, TEXT, and IF. This enables immediate access to computed values without requiring Excel to recalculate.

```python
from aspose_cells import Workbook

# Create a new workbook and set up a formula
workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = 10
worksheet.cells["B1"].value = 20
worksheet.cells["C1"].formula = "=SUM(A1:B1)"

# Force calculation to ensure formula is evaluated
workbook.calculate_formula()

# Read the computed value
print(f"Result of formula in C1: {worksheet.cells['C1'].value}")

# Save the workbook
workbook.save("output.xlsx")
```

## Best Practices

When using Aspose.Cells FOSS in Python, ensure formulas are evaluated correctly by understanding its lightweight evaluator. It resolves `cell` references and defined names at read time for `cells` lacking cached values, supporting CONCATENATE, CONCAT, TEXT, and IF functions only. This means complex or unsupported formulas may not compute as expected during file loading.

- Verify formula support by testing with known functions: CONCATENATE, CONCAT, TEXT, IF
- Avoid relying on formulas with external references or unsupported functions like VLOOKUP or SUM
- Use `CalculationProperties` to inspect calculation behavior when loading workbooks
- For critical computations, pre-calculate values in Excel before saving to avoid evaluator limitations

## Troubleshooting

### Common Installation and Import Issues

If `pip install aspose-cells-foss` fails with a connection or permission `error`, verify your network access and Python environment. Use `pip install aspose-cells-foss>=26.3.1` to ensure compatibility with the latest FOSS release. Confirm installation by running `import aspose_cells` followed by `print('Installation successful')` in a Python interpreter.

If `ImportError: cannot import name 'Workbook' from 'aspose.cells'` occurs, ensure no conflicting package like openpyxl is shadowing the module. Uninstall openpyxl if installed separately, then reinstall `aspose-cells-foss`. Avoid naming your script `aspose.py` or `cells.py`, which can cause import resolution conflicts.

### Unsupported Encryption Features

Attempting to use non-Agile encryption (e.g., XOR or standard Office encryption) raises `NotImplementedError: Standard encryption is not yet supported`. Aspose.Cells FOSS only supports Agile encryption for XLSX files. Use `AgileEncryptionParameters` to configure encryption when saving workbooks.

### `Chart` Type Limitations

Creating unsupported chart types (e.g., `ChartType.SURFACE` or `ChartType.BOX_WHISKER`) raises `NotImplementedError: Unsupported chart type for creation`. Only LINE, BAR, PIE, AREA, and STOCK chart types are supported for creation in Aspose.Cells FOSS.

```python
import aspose_cells
print('Installation successful')
```

## FAQ

### What modules are included in the Aspose.Cells FOSS package?

The `aspose-cells-foss` package includes all modules needed to read, write, and manipulate Excel-compatible spreadsheet files in Python. Core functionality covers workbook and worksheet management, cell value and formula handling, chart creation (LINE, BAR, PIE, AREA, STOCK types), styling, auto-filtering, CSV/JSON/Markdown export, and Agile-encrypted file support. No external dependencies beyond `pycryptodome` are required.

### Which chart types are supported?

Aspose.Cells FOSS supports creating charts of types LINE, BAR, PIE, AREA, and STOCK via the `ChartType` enumeration. Unsupported types such as SURFACE or BOX_WHISKER raise `NotImplementedError`. Use `ws.charts.add()` with a supported `ChartType` value to add charts programmatically.

### How do I add page breaks for print layout?

Use `ws.horizontal_page_breaks.add(row_index)` and `ws.vertical_page_breaks.add(col_index)` to insert print breaks. Remove individual breaks with `.remove(index)` or clear all with `.clear()`.

```python
ws.horizontal_page_breaks.add(19)   # break before row 20 (0-based)
ws.vertical_page_breaks.add(3)      # break before column D (0-based)
ws.horizontal_page_breaks.remove(19)
ws.horizontal_page_breaks.clear()
```

## API Reference Summary

The `AutoFilter` class provides programmatic control over filtered views in a worksheet. Use `filter_columns()` to access the collection of `FilterColumn` instances, each representing a column's `filter` criteria. The range() property returns the `cell` range to which the auto `filter` applies, and sort_state() exposes sorting configuration for the filtered data.

The `FilterColumn` class enables setting `filter` conditions per column. Initialize a new instance using `FilterColumn()` and apply it via `AutoFilter.filter_columns().add()`. This allows developers to programmatically define `filter` logic, such as value equality or wildcard matches, directly in Python scripts for Excel automation workflows.

For encrypted files, `CFBReader` and `CFBWriter` handle reading and writing the Compound File Binary (CFB) container. Note that standard encryption is not yet supported in Aspose.Cells FOSS; only Agile encryption is available. Use read_encryption_info() and read_encrypted_package() to extract encrypted content, and write() to persist encrypted output with `AgileEncryptionParameters`.

`Cell`-level operations rely on the `Cell` class to read or set values, formulas, and styles. Use the `value` and `formula` properties to `get` or assign `cell` content, and `style` to retrieve formatting. The `CellValueHandler` class supports ECMA-376-compliant value parsing and formatting, with static methods like `get_cell_type()` and `excel_serial_to_datetime()` for type conversion.

## See Also

After installing Aspose.Cells FOSS, explore `core` functionality like page break management and `cell` operations. Use `horizontal_page_breaks` and vertical_page_breaks to control printing layout, and work with individual `cells` via the `Cell` class to read or set values and formulas. For encryption workflows, `CFBReader` and `CFBWriter` handle CFB-`format` encrypted files, while `AgileEncryptionParameters` configures encryption settings. The `AutoFilter` class enables filtering and sorting on worksheet ranges.

- [Get up and running quickly](/docs.aspose.org/cells/python/developer-guide/getting-started/)
- [Apply conditional formatting rules](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Conditional formatting guide](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
