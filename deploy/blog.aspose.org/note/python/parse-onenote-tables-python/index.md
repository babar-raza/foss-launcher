---
page_role: howto_article
title: "Parse OneNote Tables in Python — Extract Structured Data from .one Files"
seoTitle: "How to Extract Table Data from OneNote .one Files Using Python"
description: "Learn how to parse and extract table data from Microsoft OneNote .one files using Aspose.Note FOSS for Python. Covers row iteration, cell text, column widths, and CSV export."
date: "2026-03-10"
draft: false
author: "Aspose"
summary: "OneNote lets you embed tables directly in pages. Aspose.Note FOSS for Python exposes every table as a typed object hierarchy — Table, TableRow, TableCell — making it easy to extract structured data programmatically."
tags: ["onenote", "python", "tables", "data-extraction", "open-source", "csv"]
categories: ["Aspose.Note"]
---

## Parse OneNote Tables in Python

Microsoft OneNote lets users embed structured tables directly in pages — perfect for task lists, schedules, comparison matrices, and data collection forms. Aspose.Note FOSS for Python makes it possible to extract all of this tabular data programmatically, with no Microsoft Office installation required.

### Install

```bash
pip install aspose-note
```

---

## Load the Document and Find Tables

`GetChildNodes(Table)` performs a recursive search across the entire document and returns every table as a `Table` object:

```python
from aspose.note import Document, Table

doc = Document("MyNotes.one")
tables = doc.GetChildNodes(Table)
print(f"Found {len(tables)} table(s)")
```

---

## Read Cell Values

Tables follow a three-level hierarchy: `Table → TableRow → TableCell`. Each cell contains `RichText` nodes whose `.Text` gives the plain-text content:

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")

for t_num, table in enumerate(doc.GetChildNodes(Table), start=1):
    print(f"\nTable {t_num}:")
    for r_num, row in enumerate(table.GetChildNodes(TableRow), start=1):
        cells = row.GetChildNodes(TableCell)
        row_values = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in cells
        ]
        print(f"  Row {r_num}: {row_values}")
```

---

## Inspect Column Widths

`Table.ColumnWidths` returns the stored width of each column in points:

```python
from aspose.note import Document, Table

doc = Document("MyNotes.one")
for i, table in enumerate(doc.GetChildNodes(Table), start=1):
    print(f"Table {i}: {len(table.ColumnWidths)} column(s)")
    print(f"  Widths (pts): {table.ColumnWidths}")
    print(f"  Borders visible: {table.BordersVisible}")
```

---

## Export All Tables to CSV

Convert every table in the document to CSV format:

```python
import csv, io
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
output = io.StringIO()
writer = csv.writer(output)

for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        values = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in row.GetChildNodes(TableCell)
        ]
        writer.writerow(values)
    writer.writerow([])   # blank row between tables

with open("tables.csv", "w", encoding="utf-8", newline="") as f:
    f.write(output.getvalue())

print("Saved tables.csv")
```

---

## Export Tables to a Python Dict / JSON

```python
import json
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
result = []

for table in doc.GetChildNodes(Table):
    rows = []
    for row in table.GetChildNodes(TableRow):
        cells = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in row.GetChildNodes(TableCell)
        ]
        rows.append(cells)
    result.append({"rows": rows, "column_widths": table.ColumnWidths})

print(json.dumps(result, indent=2))
```

---

## Use the First Row as Headers

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")

for table in doc.GetChildNodes(Table):
    rows = table.GetChildNodes(TableRow)
    if not rows:
        continue

    def row_text(row):
        return [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in row.GetChildNodes(TableCell)
        ]

    headers = row_text(rows[0])
    print("Headers:", headers)
    for row in rows[1:]:
        record = dict(zip(headers, row_text(row)))
        print("  Record:", record)
```

---

## What the Library Supports for Tables

| Feature | Supported |
|---|---|
| `Table.ColumnWidths` | Yes — column widths in points |
| `Table.BordersVisible` | Yes |
| `Table.Tags` | Yes — OneNote tags on tables |
| Cell text via `RichText` | Yes |
| Cell images via `Image` | Yes |
| Merged cells (rowspan/colspan metadata) | Not exposed in public API |
| Write/edit tables and save to `.one` | No |

---

## Next Steps

- [Table Parsing Developer Guide](https://docs.aspose.org/note/python/developer-guide/tables/)
- [How-to: Parse Tables (KB)](https://kb.aspose.org/note/python/how-to-parse-tables-onenote-python/)
- [How-to: Extract Text](https://kb.aspose.org/note/python/how-to-extract-text-from-onenote-python/)
- [API Reference — Table](https://reference.aspose.org/note/python/table/)
