---
page_role: howto_article
title: Getting Started
description: >
  This guide helps you get started with Aspose.Cells FOSS for Python — from
  installation to your first workbook, including system requirements, supported
  formats, and quick start examples.
type: docs
sidebar:
  open: true
---

##Getting Started with Aspose.Cells FOSS for Python

Welcome to the **Aspose.Cells FOSS for Python** Getting Started Guide!
This introduction will help you install the library, verify your environment, and start creating and exporting Excel spreadsheets in minutes.

---

## System Requirements

Ensure your environment meets the minimum requirements before installing.

### Supported Python Versions
* Python 3.7 or later (Python 3.9–3.13 recommended)

### Supported Operating Systems
* Windows (x86, x64)
* Linux (Ubuntu, CentOS, OpenSUSE, and others)
* macOS (x64, ARM64)

### No Additional Dependencies
Aspose.Cells FOSS for Python depends only on `pycryptodome>=3.15.0` and `olefile>=0.46`, both installed automatically by pip. No Microsoft Office, Excel, or native library is required.

---

## Installation

### Install via pip (recommended)

```bash
pip install aspose-cells-foss
```

Verify the installation:

```python
from aspose_cells import Workbook
print("Aspose.Cells FOSS for Python is ready.")
```

For more details see the [Installation Guide](installation/).

---

## What You Can Do with Aspose.Cells FOSS for Python

Out-of-the-box spreadsheet processing features include:

* Create new workbooks and worksheets from scratch
* Load and save XLSX and CSV files
* Read and write individual cells by address (`ws.cells["A1"].value = "x"`)
* Apply cell styles: font name, size, color (AARRGGBB hex), bold, italic, underline, strikethrough
* Set cell background fill colors
* Build column, line, bar, and pie charts with named data series
* Enter Excel-compatible formula strings (`cell.formula = "=SUM(A1:A5)"`)
* Export to XLSX, CSV, TSV, Markdown, and JSON

> **Export scope**: Aspose.Cells FOSS exports to XLSX, CSV, TSV, Markdown, and JSON only. PDF, HTML, PNG, and image formats require the commercial `aspose-cells-python` package.

---

## Basic Example

Here is a simple example that creates a workbook, writes data, and saves it as both XLSX and Markdown:

```python
from aspose_cells import Workbook, Cell

##Create a new workbook
workbook = Workbook()
ws = workbook.worksheets[0]
ws.name = "Sales"

##Write headers
ws.cells["A1"].value = "Product"
ws.cells["B1"].value = "Revenue"

##Write data
ws.cells["A2"].value = "Widget A"
ws.cells["B2"].value = 12500
ws.cells["A3"].value = "Widget B"
ws.cells["B3"].value = 8750

##Save as Excel
workbook.save("sales.xlsx")

##Export as Markdown (tables)
workbook.save_as_markdown("sales.md")

print("Files saved successfully.")
```

---

## Next Steps

Continue learning with these resources:

* **[Installation Guide](installation/)** — Detailed pip setup, virtual environments, and plugin installation
* **[Developer Guide](../developer-guide/)** — Practical tutorials covering all major features
* **[API Reference](https://reference.aspose.org/cells/python/)** — Full class and method documentation
* **[Knowledge Base](https://kb.aspose.org/cells/python/)** — Task-oriented how-to guides (charts, Markdown export, styling)
* **[Product Overview](https://products.aspose.org/cells/python/)** — Features and capabilities summary
* **[Blog: Introducing Aspose.Cells FOSS](https://blog.aspose.org/cells/python/introducing-cells-foss-python/)** — Library overview and quick start
