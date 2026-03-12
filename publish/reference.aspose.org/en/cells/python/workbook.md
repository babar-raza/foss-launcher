---
page_role: reference_object_page
title: "Workbook — Aspose.Cells FOSS for Python API Reference"
description: "API reference for the Workbook class in aspose-cells-foss. Constructor, worksheets collection, save methods, encryption, and document properties."
canonical: https://reference.aspose.org/cells/python/workbook/
url: /reference.aspose.org/cells/python/workbook/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Cells FOSS
family: cells
platform: python
canonical_import: aspose_cells_foss
robots: index, follow
seoTitle: "Workbook Class — Aspose.Cells FOSS for Python API Reference"
keywords:
  - aspose cells workbook python
  - python excel workbook class
  - open excel file python
  - save excel file python
  - workbook worksheets python
  - python excel encryption
type: reference_object_page
draft: false
weight: 10
---

The `Workbook` class is the root object for all spreadsheet operations in aspose-cells-foss. It manages worksheets, handles file I/O, and provides access to document properties.

**Package**: `aspose_cells`

```python
from aspose_cells import Workbook
```

---

## Constructor

```python
Workbook(path=None, password=None)
```

| Parameter | Type | Description |
|---|---|---|
| `path` | `str \| None` | File path to open. Pass `None` (or omit) to create an empty workbook. |
| `password` | `str \| None` | Decryption password for AES-encrypted files. Only required when opening a protected file. |

**Examples**:

```python
from aspose_cells import Workbook

# Create a new empty workbook
wb = Workbook()

# Open an existing XLSX file
wb = Workbook("report.xlsx")

# Open an AES-encrypted file
wb = Workbook("protected.xlsx", password="secret")
```

---

## Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `worksheets` | `WorksheetCollection` | Read | Ordered collection of worksheets. Access by index (`wb.worksheets[0]`) or add via `wb.worksheets.add(name)`. |
| `document_properties` | `DocumentProperties` | Read | Core and custom document metadata (title, author, subject, custom key-value pairs). |

---

## Methods

### save

```python
wb.save(path, password=None)
```

Save the workbook to a file. The output format is determined automatically from the file extension.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Destination file path. Use `.xlsx`, `.xls`, or `.csv` extension. |
| `password` | `str \| None` | If provided, the output file is encrypted with AES using this password. |

**Examples**:

```python
wb.save("output.xlsx")        # XLSX — default format
wb.save("output.xls")         # XLS — legacy binary format
wb.save("output.csv")         # CSV — first worksheet only
wb.save("protected.xlsx", password="secret")  # encrypted XLSX
```

### save_as_markdown

```python
wb.save_as_markdown(path)
```

Export the first worksheet as a GitHub-flavored Markdown table.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Destination `.md` file path. |

```python
wb.save_as_markdown("output.md")
```

### worksheets (WorksheetCollection methods)

| Method | Signature | Description |
|---|---|---|
| `add` | `(name: str) -> Worksheet` | Append a new worksheet with the given name and return it. |
| `__getitem__` | `[index: int] -> Worksheet` | Return the worksheet at zero-based `index`. |
| `__len__` | `() -> int` | Number of worksheets in this workbook. |

---

## Usage Examples

### Basic Workbook Workflow

```python
from aspose_cells import Workbook

wb = Workbook()
ws = wb.worksheets[0]
ws.name = "Sales"

ws.cells["A1"].put_value("Quarter")
ws.cells["B1"].put_value("Revenue")
ws.cells["A2"].put_value("Q1")
ws.cells["B2"].put_value(42000)
ws.cells["A3"].put_value("Q2")
ws.cells["B3"].put_value(58000)
ws.cells["B4"].formula = "=SUM(B2:B3)"

wb.save("sales.xlsx")
```

### Add Multiple Worksheets

```python
from aspose_cells import Workbook

wb = Workbook()
wb.worksheets[0].name = "Summary"
ws2 = wb.worksheets.add("Details")
ws3 = wb.worksheets.add("Charts")

print(len(wb.worksheets))   # 3
wb.save("multi-sheet.xlsx")
```

### Open, Modify, and Re-save

```python
from aspose_cells import Workbook

wb = Workbook("existing.xlsx")
ws = wb.worksheets[0]
ws.cells["C1"].put_value("Updated")
wb.save("existing.xlsx")    # overwrite in place
```

### Encrypt on Save

```python
from aspose_cells import Workbook

wb = Workbook("report.xlsx")
wb.save("report-secure.xlsx", password="MyPassword123")
```

---

## See Also

- [Cells Python API Reference home](/reference.aspose.org/cells/python/)
- [Worksheet class reference](/reference.aspose.org/cells/python/worksheet/)
- [Cell class reference](/reference.aspose.org/cells/python/cell/)
- [Getting Started](/docs.aspose.org/cells/python/getting-started/)
- [Developer Guide](/docs.aspose.org/cells/python/developer-guide/)
- [Knowledge Base](/kb.aspose.org/cells/python/)
