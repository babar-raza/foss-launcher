---
page_role: reference_home
linkTitle: "aspose.cells (Python)"
title: "Aspose.Cells FOSS for Python — API Reference"
description: "Complete API reference for Aspose.Cells FOSS for Python. Covers the Workbook, Worksheet, Cells, Cell, Style, Font, Fill, Chart, SaveFormat, and MarkdownHandler classes."
summary: "Public API surface of Aspose.Cells FOSS for Python (package: aspose-cells-foss, import: aspose_cells), organized by module, class, method, property, and enumeration."
canonical: https://reference.aspose.org/cells/python/
url: /reference.aspose.org/cells/python/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Cells FOSS
family: cells
platform: python
canonical_import: aspose_cells_foss
robots: index, follow
seoTitle: "Aspose.Cells FOSS for Python API Reference — Workbook, Worksheet, Cell"
draft: false
type: reference_home
weight: 1
categories:
  - API Reference
layout: "reference-home"
---

## Package Information

| | |
|---|---|
| **PyPI package** | `aspose-cells-foss` |
| **Python import** | `from aspose_cells import ...` |
| **Version** | 26.3.0 |
| **License** | MIT |
| **Python requirement** | >= 3.7 |
| **Dependencies** | `pycryptodome>=3.15.0`, `olefile>=0.46` |

---

## Modules

| Module | Description |
|---|---|
| [aspose_cells](#aspose_cells) | Core spreadsheet API: workbooks, worksheets, cells, styles, charts, format handlers |

> **Note**: There is no `aspose.pydrawing` module in Aspose.Cells FOSS. Colors are expressed as 8-digit AARRGGBB hex strings (e.g., `"FFFF0000"` for opaque red).

---

## aspose_cells

### Classes

| Class | Description |
|---|---|
| `Workbook` | Entry point for creating, loading, and saving spreadsheet files |
| `Worksheet` | Represents a single sheet; provides access to cells, charts, and pictures |
| `Cells` | Dictionary-like collection of `Cell` objects within a `Worksheet` |
| `Cell` | Represents an individual cell; value, formula, and style |
| `Style` | Cell formatting container: font and fill |
| `Font` | Font properties: name, size, color (AARRGGBB hex), bold, italic, underline, strikethrough |
| `Fill` | Background fill for a cell style |
| `SaveFormat` | Enumeration of supported output formats |
| `MarkdownHandler` | Utility class for Markdown export operations |
| `MarkdownSaveOptions` | Options for `save_as_markdown()` |
| `JsonSaveOptions` | Options for JSON export |
| `CSVSaveOptions` | Options for CSV export |
| `CSVLoadOptions` | Options for CSV import |
| `ChartCollection` | Collection of charts in a worksheet |
| `Chart` | Represents a chart object |
| `NSeries` | Data series collection on a chart |

---

### Workbook

**Constructors**

| Signature | Description |
|---|---|
| `Workbook()` | Create a new empty workbook (XLSX format) |
| `Workbook(file_path: str)` | Load a workbook from a file path |
| `Workbook(file_path: str, password: str)` | Load a password-protected workbook |

**Key Properties**

| Property | Type | Description |
|---|---|---|
| `worksheets` | list | Access worksheets by index: `workbook.worksheets[0]` |

**Key Methods**

| Method | Return | Description |
|---|---|---|
| `save(file_path)` | None | Save to file; format inferred from extension |
| `save(file_path, save_format)` | None | Save with explicit SaveFormat |
| `save_as_csv(file_path, options=None)` | None | Save as CSV |
| `save_as_markdown(file_path, options=None)` | None | Save as Markdown tables |
| `save_as_json(file_path, options=None)` | None | Save as JSON |
| `load_csv(file_path, options=None)` | None | Load CSV data into the workbook |
| `add_worksheet(name=None)` | Worksheet | Add a new worksheet |
| `get_worksheet(index_or_name)` | Worksheet | Get worksheet by index or name |
| `remove_worksheet(index_or_name)` | None | Remove a worksheet |
| `copy_worksheet(index_or_name_or_ws)` | Worksheet | Copy an existing worksheet |
| `protect(password=None, lock_structure=True)` | None | Password-protect the workbook |
| `unprotect(password=None)` | None | Remove workbook protection |
| `is_protected()` | bool | Check if the workbook is protected |

---

### Worksheet

**Key Properties**

| Property | Type | Description |
|---|---|---|
| `name` | str | Worksheet tab name |
| `cells` | Cells | All cells in this worksheet |
| `charts` | ChartCollection | All charts in this worksheet |

---

### Cells

`Cells` supports dictionary-style access by cell address string.

**Access Patterns**

```python
# Read a cell value
value = ws.cells["A1"].value

# Set a cell value directly
ws.cells["A1"].value = "Hello"

# Assign a Cell object
from aspose_cells import Cell
ws.cells["A1"] = Cell(42)
ws.cells["A2"] = Cell(3.14)
ws.cells["A3"] = Cell("Hello World")
ws.cells["A4"] = Cell(None, "=SUM(A1:A3)")   # formula cell
```

---

### Cell

**Constructor**

| Signature | Description |
|---|---|
| `Cell(value=None)` | Create a cell with a value (int, float, str, or None) |
| `Cell(value, formula)` | Create a formula cell (value is typically None) |

**Key Properties**

| Property | Type | Description |
|---|---|---|
| `value` | Any | Cell value (str, int, float, or None) |
| `formula` | str | Formula string (e.g., `"=SUM(A1:A5)"`) |
| `style` | Style | Cell style (font, fill) |

---

### Style

| Property | Type | Description |
|---|---|---|
| `font` | Font | Font settings for this style |
| `fill` | Fill | Background fill settings |

---

### Font

Colors are expressed as **8-digit AARRGGBB hex strings** without a `#` prefix.
Examples: `"FFFF0000"` = opaque red, `"FF0000FF"` = opaque blue, `"FF000000"` = black.

| Property | Type | Default | Description |
|---|---|---|---|
| `name` | str | Calibri | Font family name |
| `size` | float | 11 | Font size in points |
| `color` | str | FF000000 | 8-digit AARRGGBB hex color string |
| `bold` | bool | False | Bold text |
| `italic` | bool | False | Italic text |
| `underline` | bool | False | Underlined text |
| `strikethrough` | bool | False | Strikethrough text |

**Constructor**

```python
Font(name="Calibri", size=11, color="FF000000",
     bold=False, italic=False, underline=False, strikethrough=False)
```

---

### Fill

| Method | Description |
|---|---|
| `set_solid_fill(color)` | Solid background; `color` is an 8-digit AARRGGBB hex string |
| `set_pattern_fill(pattern_type, fg_color, bg_color)` | Patterned fill |
| `set_no_fill()` | Remove background fill |

---

### MarkdownHandler

| Method | Return | Description |
|---|---|---|
| `MarkdownHandler.save_markdown_to_string(workbook)` | str | Export workbook to a Markdown string in memory |

---

### MarkdownSaveOptions

| Property | Type | Default | Description |
|---|---|---|---|
| `default_alignment` | str | left | Column alignment: left, right, or center |
| `include_worksheet_name` | bool | True | Whether to include the sheet name as a heading |
| `header_level` | int | 2 | Markdown heading level (1-6) |
| `worksheet_index` | int | 0 | Sheet index to export; -1 exports all sheets |

---

### ChartCollection

Charts are added using dedicated per-type methods. Row and column indices are **zero-based**.

| Method | Return | Description |
|---|---|---|
| `add_bar(top_row, left_col, bottom_row, right_col)` | Chart | Add a column (vertical bar) chart |
| `add_line(top_row, left_col, bottom_row, right_col)` | Chart | Add a line chart |
| `add_pie(top_row, left_col, bottom_row, right_col)` | Chart | Add a pie chart |

---

### Chart

| Property | Type | Description |
|---|---|---|
| `title` | str | Chart title as a plain string (not `.title.text`) |
| `category_data` | str | Cell range for x-axis category labels |
| `n_series` | NSeries | Data series collection |
| `show_legend` | bool | Whether to display the legend |
| `legend_position` | str | Legend position: right, bottom, left, or top |

---

### NSeries

| Method | Description |
|---|---|
| `add(data_range, category_data=None, name=None)` | Add a named data series |

---

## SaveFormat Enumeration

| Constant | Output Format |
|---|---|
| `SaveFormat.XLSX` | Excel Open XML (default) |
| `SaveFormat.CSV` | Comma-separated values |
| `SaveFormat.TSV` | Tab-separated values |
| `SaveFormat.MARKDOWN` | Markdown tables |
| `SaveFormat.JSON` | JSON-structured data |

> **Note**: `SaveFormat.PDF`, `SaveFormat.HTML`, `SaveFormat.PNG`, `SaveFormat.TIFF`, `SaveFormat.DOCX`, and `SaveFormat.PPTX` are **not available** in Aspose.Cells FOSS. These formats require the commercial `aspose-cells-python` package.

---

## Code Examples

### Create, style, and save a workbook

```python
from aspose_cells import Workbook, Cell

wb = Workbook()
ws = wb.worksheets[0]

ws.cells["A1"].value = "Revenue Report"
ws.cells["A2"].value = 125000

ws.cells["A1"].style.font.bold = True
ws.cells["A1"].style.font.size = 14
ws.cells["A1"].style.font.color = "FF1E64C8"   # Blue (AARRGGBB, no #)

wb.save("report.xlsx")
```

### Export to Markdown in memory

```python
from aspose_cells import Workbook, Cell, MarkdownHandler

wb = Workbook()
ws = wb.worksheets[0]
ws.cells["A1"].value = "Name"
ws.cells["B1"].value = "Score"
ws.cells["A2"].value = "Alice"
ws.cells["B2"].value = 95

md = MarkdownHandler.save_markdown_to_string(wb)
print(md)
```

### Build a line chart

```python
from aspose_cells import Workbook, Cell

wb = Workbook()
ws = wb.worksheets[0]

for i, (m, v) in enumerate([("Jan", 50), ("Feb", 80), ("Mar", 120)], start=2):
    ws.cells[f"A{i}"].value = m
    ws.cells[f"B{i}"].value = v

chart = ws.charts.add_line(5, 0, 18, 7)
chart.title = "Monthly Trend"
chart.category_data = "A2:A4"
chart.n_series.add("B2:B4", category_data="A2:A4", name="Sales")

wb.save("trend.xlsx")
```

---

## Related Resources

- [Developer Guide](https://docs.aspose.org/cells/python/developer-guide/) — Tutorials for all core features
- [Getting Started / Installation](https://docs.aspose.org/cells/python/getting-started/installation/) — pip install and setup
- [Knowledge Base](https://kb.aspose.org/cells/python/) — Task-oriented how-to guides
- [Product Overview](https://products.aspose.org/cells/python/) — Features and capabilities summary
- [GitHub Repository](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python)
- [Blog: Introducing Aspose.Cells FOSS](https://blog.aspose.org/cells/python/introducing-cells-foss-python/) — Library overview and quick start
