---
page_role: howto_article
description: >-
  Export Excel spreadsheets from Python to XLSX, CSV, TSV, Markdown, and JSON
  using Aspose.Cells FOSS â€” with stream support and zero Office dependency.
title: Spreadsheet Format Export for Python
type: docs
slug: "spreadsheet-format-conversion"
---

Aspose.Cells FOSS for Python provides straightforward export from Excel workbooks to every format the FOSS library supports. A single `workbook.save()` call handles the full output pipeline â€” XLSX, CSV, TSV, Markdown, or JSON â€” preserving cell values and formulas without requiring Microsoft Office.

## Installation and Setup

```bash
pip install aspose-cells-foss
```

Import the core classes:

```python
from aspose_cells import Workbook, SaveFormat, Cell
from aspose_cells import MarkdownHandler, MarkdownSaveOptions
from aspose_cells import CSVSaveOptions
```

## Supported Output Formats

| Format | SaveFormat Constant | Notes |
|---|---|---|
| XLSX | `SaveFormat.XLSX` | Default format; preserves styles, formulas, charts |
| CSV | `SaveFormat.CSV` | Comma-separated; first sheet only by default |
| TSV | `SaveFormat.TSV` | Tab-separated values |
| Markdown | `SaveFormat.MARKDOWN` | Generates standard Markdown tables |
| JSON | `SaveFormat.JSON` | Structured JSON representation of sheet data |

> **Important**: Aspose.Cells FOSS does **not** support export to PDF, HTML, PNG, TIFF, DOCX, or PPTX. These are available in the commercial `aspose-cells-python` package only.

---

## Usage Examples

### Save to XLSX

The default format when saving with a `.xlsx` extension:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]
ws.cells["A1"].value = "Product"
ws.cells["B1"].value = "Revenue"
ws.cells["A2"].value = "Widget A"
ws.cells["B2"].value = 12500
ws.cells["A3"].value = "Widget B"
ws.cells["B3"].value = 8750

workbook.save("report.xlsx")
```

### Save to CSV

```python
from aspose_cells import Workbook, Cell, SaveFormat

workbook = Workbook()
ws = workbook.worksheets[0]
ws.cells["A1"].value = "Name"
ws.cells["B1"].value = "Age"
ws.cells["A2"].value = "Alice"
ws.cells["B2"].value = 30
ws.cells["A3"].value = "Bob"
ws.cells["B3"].value = 25

workbook.save("data.csv", SaveFormat.CSV)
```

### Save to Markdown

Export tabular data as Markdown tables â€” useful for documentation and README generation:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]
ws.cells["A1"].value = "First name"
ws.cells["B1"].value = "Age"
ws.cells["A2"].value = "Alice"
ws.cells["B2"].value = 30
ws.cells["A3"].value = "Bob"
ws.cells["B3"].value = 25

workbook.save_as_markdown("data.md")
```

Output is a standard Markdown table:

```
| First name | Age |
|---|---|
| Alice | 30 |
| Bob | 25 |
```

### Markdown with Options

Use `MarkdownSaveOptions` for fine-grained control:

```python
from aspose_cells import Workbook, Cell, MarkdownSaveOptions

workbook = Workbook()
ws = workbook.worksheets[0]
ws.cells["A1"].value = "City"
ws.cells["B1"].value = "Population"
ws.cells["A2"].value = "London"
ws.cells["B2"].value = 9000000

options = MarkdownSaveOptions()
options.default_alignment = "center"
options.include_worksheet_name = False
options.header_level = 3
options.worksheet_index = 0

workbook.save_as_markdown("cities.md", options)
```

### Markdown to String (in-memory)

Generate a Markdown string without writing to disk:

```python
from aspose_cells import Workbook, Cell, MarkdownHandler

workbook = Workbook()
ws = workbook.worksheets[0]
ws.cells["A1"].value = "Key"
ws.cells["B1"].value = "Value"
ws.cells["A2"].value = "version"
ws.cells["B2"].value = "26.3.0"

md_string = MarkdownHandler.save_markdown_to_string(workbook)
print(md_string)
```

### Save to JSON

Export workbook data as structured JSON for API pipelines:

```python
from aspose_cells import Workbook, Cell, SaveFormat

workbook = Workbook()
ws = workbook.worksheets[0]
ws.cells["A1"].value = "Name"
ws.cells["B1"].value = "Score"
ws.cells["A2"].value = "Alice"
ws.cells["B2"].value = 95.5
ws.cells["A3"].value = "Bob"
ws.cells["B3"].value = 88.0

workbook.save("data.json", SaveFormat.JSON)
```

### Load a CSV and Save as XLSX

```python
from aspose_cells import Workbook, SaveFormat

workbook = Workbook()
workbook.load_csv("input.csv")
workbook.save("output.xlsx", SaveFormat.XLSX)
```

---

## Tips and Best Practices

### Markdown Export
- Use `worksheet_index = -1` in `MarkdownSaveOptions` to export all sheets as separate Markdown tables in one file.
- Use `MarkdownHandler.save_markdown_to_string(wb)` for in-memory use cases such as API responses.

### CSV Export
- CSV export writes the first worksheet by default. To export a specific sheet, use `CSVSaveOptions` with a sheet index.
- Special characters (commas, newlines) in cell values are automatically quoted.

### JSON Export
- JSON export uses cell addresses as keys. Suitable for data interchange; complex formulas are stored as their string expressions.

---

## Common Issues and Resolutions

| Issue | Resolution |
|---|---|
| **`ModuleNotFoundError: No module named 'aspose_cells'`** | Run `pip install aspose-cells-foss` and confirm the virtual environment is active |
| **`AttributeError` on `SaveFormat.PDF`** | PDF export is not in the FOSS library; use `SaveFormat.MARKDOWN` or `SaveFormat.XLSX` instead |
| **Empty Markdown output** | Ensure at least one cell in the sheet has a value before saving |
| **Encoding issues in Markdown** | Use `MarkdownHandler.save_markdown_to_string()` for in-memory string output with full encoding control |

---

## Frequently Asked Questions

**Which output formats does Aspose.Cells FOSS support?**
XLSX, CSV, TSV, Markdown, and JSON.

**Can I convert to PDF?**
No. PDF export requires the commercial `aspose-cells-python` package. Aspose.Cells FOSS exports only to XLSX, CSV, TSV, Markdown, and JSON.

**Can I load an existing XLSX and re-save it as Markdown?**
Yes. `Workbook("existing.xlsx")` loads the file, and `workbook.save_as_markdown("output.md")` exports it.

**Is stream-based Markdown output supported?**
Yes. Use `MarkdownHandler.save_markdown_to_string(workbook)` to get the Markdown as a Python string without any file I/O.

**What Python versions are supported?**
Python 3.7 and later.
---

## See Also

- [API Reference](https://reference.aspose.org/cells/python/) — Full class and method documentation for `aspose_cells`
- [Knowledge Base](https://kb.aspose.org/cells/python/) — Task-oriented how-to guides
- [Product Overview](https://products.aspose.org/cells/python/) — Features and capabilities summary
- [Getting Started / Installation](https://docs.aspose.org/cells/python/getting-started/installation/) — pip install and setup
- [Blog: Introducing Aspose.Cells FOSS](https://blog.aspose.org/cells/python/introducing-cells-foss-python/) — Library overview and quick start
