---
page_role: howto_article
description: >-
  Parse tables in Microsoft OneNote .one files in Python using Aspose.Note FOSS.
  Covers Table, TableRow, TableCell, column widths, cell text, and nested content.
title: Table Parsing — Aspose.Note FOSS for Python
type: docs
weight: 40
---

Tables in OneNote documents are exposed as a three-level hierarchy: `Table → TableRow → TableCell`. Each cell can contain `RichText`, `Image`, and other content nodes. This page covers every table parsing pattern supported by Aspose.Note FOSS for Python.

---

## Basic Table Iteration

Retrieve all tables in the document and read their cell text:

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")

for table_num, table in enumerate(doc.GetChildNodes(Table), start=1):
    print(f"\nTable {table_num}: {len(table.ColumnWidths)} column(s)")
    for r, row in enumerate(table.GetChildNodes(TableRow), start=1):
        cells = row.GetChildNodes(TableCell)
        values = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in cells
        ]
        print(f"  Row {r}: {values}")
```

---

## Table Properties

| Property | Type | Description |
|---|---|---|
| `ColumnWidths` | `list[float]` | Width of each column in points |
| `BordersVisible` | `bool` | Whether table borders are displayed |
| `Tags` | `list[NoteTag]` | OneNote tags attached to the table |

```python
from aspose.note import Document, Table

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    print(f"Columns: {len(table.ColumnWidths)}")
    print(f"Widths (pts): {table.ColumnWidths}")
    print(f"Borders visible: {table.BordersVisible}")
```

---

## Export Table to CSV

Convert a table to CSV format:

```python
import csv
import io
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
    writer.writerow([])  # blank line between tables

print(output.getvalue())
```

---

## Extract Tables Per Page

Scope table extraction to individual pages:

```python
from aspose.note import Document, Page, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
for page_num, page in enumerate(doc.GetChildNodes(Page), start=1):
    tables = page.GetChildNodes(Table)
    if not tables:
        continue
    title = (
        page.Title.TitleText.Text
        if page.Title and page.Title.TitleText
        else f"Page {page_num}"
    )
    print(f"\n=== {title} ({len(tables)} table(s)) ===")
    for t, table in enumerate(tables, start=1):
        print(f"  Table {t}:")
        for row in table.GetChildNodes(TableRow):
            cells = row.GetChildNodes(TableCell)
            row_text = [
                " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
                for cell in cells
            ]
            print(f"    {row_text}")
```

---

## Cell Content Beyond Plain Text

Table cells can contain `Image` and other `CompositeNode` content alongside `RichText`:

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText, Image

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        for cell in row.GetChildNodes(TableCell):
            texts = [rt.Text for rt in cell.GetChildNodes(RichText) if rt.Text]
            images = cell.GetChildNodes(Image)
            print(f"  Cell texts: {texts}  images: {len(images)}")
```

---

## Count and Summarize Tables

Gather statistics about all tables in a document:

```python
from aspose.note import Document, Table, TableRow, TableCell

doc = Document("MyNotes.one")
tables = doc.GetChildNodes(Table)
print(f"Total tables: {len(tables)}")

for i, table in enumerate(tables, start=1):
    rows = table.GetChildNodes(TableRow)
    if rows:
        cols = len(rows[0].GetChildNodes(TableCell))
    else:
        cols = 0
    print(f"  Table {i}: {len(rows)} row(s) x {cols} column(s)  widths={table.ColumnWidths}")
```

---

## Inspect Tags on Tables

Tables support `NoteTag` items directly:

```python
from aspose.note import Document, Table

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    for tag in table.Tags:
        print(f"Table tag: {tag.label}  shape={tag.shape}  completed={tag.completed}")
```

---

## DOM Position of Tables

Tables appear as children of `OutlineElement` nodes within `Outline` containers on each `Page`. The hierarchy is:

```
Page
  └── Outline
        └── OutlineElement
              └── Table
                    └── TableRow
                          └── TableCell
                                └── RichText / Image
```

You can also reach tables via `GetChildNodes(Table)` at any ancestor node level — it searches the full subtree.

---

## Tips

- `table.ColumnWidths` reflects the stored column widths in points; the number of entries equals the number of columns.
- Cell content is not always purely `RichText` — always check for `Image` nodes as well if full fidelity matters.
- Use `table.GetChildNodes(TableRow)` rather than iterating `for row in table` if you need a typed list rather than a generic iterator.
- `BordersVisible` reflects the OneNote user's display preference at save time; it does not affect content extraction.

---

## See Also

- [How-to: Parse Tables (KB)](https://kb.aspose.org/note/python/how-to-parse-onenote-tables-python/)
- [Blog: Parse OneNote Tables in Python](https://blog.aspose.org/note/python/parse-onenote-tables-python/)
- [API Reference — Table](https://reference.aspose.org/note/python/table/)
