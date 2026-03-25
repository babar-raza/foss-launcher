---
canonical: https://docs.aspose.org/cells/python/developer-guide/installation/
canonical_import: aspose.cells
date: '2026-03-23T13:16:22Z'
dateModified: '2026-03-23T13:16:22Z'
datePublished: '2026-03-23T13:16:22Z'
description: It supports core spreadsheet operations including `cell` `value` and
  `formula` handling, worksheet management, and chart creation.
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

Aspose.Cells FOSS enables Python developers to create, edit, and manage Excel workbooks programmatically without requiring Microsoft Excel. It supports core spreadsheet operations including `cell` `value` and `formula` handling, worksheet management, and chart creation.

To use Aspose.Cells FOSS, ensure your environment meets the minimum requirements: Python 3.7 or higher, pycryptodome >= 3.15.0, and olefile >= 0.46. These dependencies are essential for core functionality including encryption support and file format parsing.

```python
import aspose.cells

# Create a new workbook
wb = aspose.cells.Workbook()

# Access the first worksheet
ws = wb.worksheets[0]

# Write a value to cell A1
ws.cells['A1'].value = 'Hello, Aspose.Cells FOSS!'

# Save the workbook
wb.save('output.xlsx')
```

## Key Features

Aspose.Cells FOSS provides a robust, open-source Python library for working with spreadsheet data. It supports core Excel operations including workbook creation, `cell` manipulation, and chart generation, all while maintaining compatibility with ECMA-376 standards. The library requires Python 3.7 or higher and depends on pycryptodome >= 3.15.0 and olefile >= 0.46, ensuring secure and reliable file handling.

- Create and modify Excel workbooks with the `Workbook` class, enabling programmatic generation of spreadsheets from scratch or editing of existing files.
- Read and write cell values, formulas, and comments using the `Cell` and `Cells` classes, supporting both direct indexing and coordinate-based access.
- Manage multiple worksheets with methods like `add_worksheet()`, `get_worksheet()`, and `remove_worksheet()` on the `Workbook` object.
- Generate and customize charts—including line, bar, pie, scatter, and waterfall types—using the `ChartCollection` and `Chart` classes.
- Export data to popular formats such as CSV, JSON, and Markdown using the `CSVHandler`, `JsonHandler`, and `MarkdownHandler` static methods.
- Set and persist document properties (title, author, keywords, company, etc.) for both core (Dublin Core) and extended metadata, ensuring full roundtrip fidelity in XLSX files.

## Prerequisites

Aspose.Cells FOSS requires Python 3.7 or higher. Install the package using pip with the command `pip install aspose.cells`.

The library depends on two external packages: pycryptodome version 3.15.0 or higher and olefile version 0.46 or higher. These dependencies are installed automatically when you install Aspose.Cells FOSS via pip.

```python
import aspose.cells
```

## Code Examples

Aspose.Cells FOSS requires Python 3.7 or higher and depends on pycryptodome >= 3.15.0 and olefile >= 0.46. After installing the library, you can immediately begin working with Excel files in Python using the `Workbook` class to create, load, and manipulate spreadsheets. The API supports core operations like reading and writing `cell` `values`, managing `worksheets`, and generating `charts`.

```python
import aspose.cells

# Create a new workbook
wb = aspose.cells.Workbook()

# Access the first worksheet
ws = wb.worksheets[0]

# Set a value in cell A1
ws.cells['A1'].value = 'Hello, Aspose.Cells FOSS!'

# Save the workbook
wb.save('output.xlsx')
```

## Best Practices

Ensure your environment meets the minimum requirements before installing Aspose.Cells FOSS. The library requires Python 3.7 or higher and depends on pycryptodome >= 3.15.0 and olefile >= 0.46. These dependencies are automatically installed via pip if missing, but verifying them upfront prevents runtime errors in production environments.

- Confirm Python version with `python --version` or `python3 --version`
- Install pycryptodome explicitly if your environment blocks automatic dependency resolution: `pip install pycryptodome>=3.15.0`
- Verify olefile installation: `pip show olefile` and upgrade if below 0.46
- Use virtual environments to isolate Aspose.Cells FOSS and its dependencies from system-wide packages

## Troubleshooting

If you encounter issues installing or using Aspose.Cells FOSS, verify your environment meets the minimum requirements. The library requires Python 3.7 or higher and depends on pycryptodome >= 3.15.0 and olefile >= 0.46. Missing or outdated dependencies are the most common cause of import failures.

```python
import aspose.cells

# Verify dependencies are installed
import pycryptodome
import olefile

print(f"pycryptodome version: {pycryptodome.__version__}")
print(f"olefile version: {olefile.__version__}")
```

If `import aspose.cells` raises a ModuleNotFoundError, ensure the package is installed via pip. Run `pip install aspose.cells` in your terminal or VS Code integrated terminal. For Spyder or other IDEs, confirm the Python interpreter matches the environment where you installed the package.

If `ImportError: cannot import name 'Workbook' from 'aspose.cells'` occurs, check that you are not using a conflicting package (e.g., `aspose-cells` vs `aspose.cells`). Uninstall any duplicate or outdated packages with `pip uninstall aspose-cells` before reinstalling.

When using virtual environments, `activate` the environment before installing or running scripts. In VS Code, `select` the correct interpreter via Ctrl+Shift+P → Python: Select Interpreter. In Spyder, set the Python executable path under Tools → Preferences → Python Interpreter.

## FAQ

### What are the system requirements for Aspose.Cells FOSS?

### How do I verify my Python version before installing?

Run `python --version` or `python3 --version` in your terminal to check your Python version. Ensure the output shows 3.7.x or higher. If you have multiple Python versions installed, confirm the version used by your pip command matches your target interpreter.

### Does Aspose.Cells FOSS support encryption?

Aspose.Cells FOSS supports Agile encryption only. Standard encryption and other encryption methods are not yet implemented. If you attempt to use unsupported encryption, the library raises a NotImplementedError with a `clear` message indicating the limitation.

```python
import aspose.cells

# Verify Python version compatibility
import sys
print(f"Python version: {sys.version}")

# Create a workbook to confirm installation
wb = aspose.cells.Workbook()
print("Aspose.Cells FOSS installed and working correctly.")
```

## API Reference Summary

Aspose.Cells FOSS requires Python 3.7 or higher and depends on two core packages: pycryptodome >= 3.15.0 and olefile >= 0.46. These dependencies enable secure handling of encrypted Excel files and legacy OLE2 document formats. Install the library and its dependencies using pip: `pip install aspose.cells pycryptodome olefile`.

```python
import aspose.cells

# Create a new workbook
wb = aspose.cells.Workbook()
ws = wb.worksheets[0]

# Write a value to a cell
ws.cells['A1'].value = 'Hello, Aspose.Cells FOSS!'

# Save the workbook
wb.save('output.xlsx')
```

## See Also

Aspose.Cells FOSS requires Python 3.7 or higher and depends on pycryptodome >= 3.15.0 and olefile >= 0.46. Ensure these dependencies are installed before using the library in your Python environment, whether in VS Code, Spyder, or any other Python IDE.

- [Get started with Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/getting-started/)
- [Explore the API reference](/reference.aspose.org/cells/python/api-overview/)
- [Introducing Aspose.Cells FOSS for Python](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Create all chart types in spreadsheets](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with formulas in Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
