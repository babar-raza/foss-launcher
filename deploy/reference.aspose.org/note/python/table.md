---
page_role: howto_article
linkTitle: "Table / TableRow / TableCell"
title: "Table, TableRow, TableCell — Aspose.Note FOSS for Python API Reference"
description: "API reference for Table, TableRow, and TableCell classes in aspose-note v26.2. Represents table structures in OneNote documents."
categories:
  - Class
layout: "reference"
---

## Class: Table

**Package**: `aspose.note`
**Import**: `from aspose.note import Table`
**Inherits**: `CompositeNode`

`Table` represents a table within an `OutlineElement`. It holds a list of `TableRow` children and exposes column widths and border visibility.

### Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `ColumnWidths` | `list[float]` | Read | Width of each column in points; length equals the number of columns |
| `BordersVisible` | `bool` | Read | Whether table borders are rendered in OneNote |
| `Tags` | `list[NoteTag]` | Read | OneNote tags attached to this table |

### Inherited from CompositeNode / Node

`FirstChild`, `LastChild`, `GetChildNodes(Type)`, `for row in table`, `ParentNode`, `Document`

---

## Class: TableRow

**Package**: `aspose.note`
**Import**: `from aspose.note import TableRow`
**Inherits**: `CompositeNode`

`TableRow` is a single row within a `Table`. Its direct children are `TableCell` nodes.

### Usage

```python
rows = table.GetChildNodes(TableRow)
for row in rows:
    cells = row.GetChildNodes(TableCell)
```

---

## Class: TableCell

**Package**: `aspose.note`
**Import**: `from aspose.note import TableCell`
**Inherits**: `CompositeNode`

`TableCell` is a single cell within a `TableRow`. It can contain `RichText`, `Image`, and other content nodes.

### Usage

```python
for cell in row.GetChildNodes(TableCell):
    text = " ".join(rt.Text for rt in cell.GetChildNodes(RichText))
```

---

## Usage Examples

### Read all tables — full traversal

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
for t_num, table in enumerate(doc.GetChildNodes(Table), start=1):
    print(f"\nTable {t_num}  cols={len(table.ColumnWidths)}  widths={table.ColumnWidths}")
    for r_num, row in enumerate(table.GetChildNodes(TableRow), start=1):
        cells = row.GetChildNodes(TableCell)
        row_data = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in cells
        ]
        print(f"  Row {r_num}: {row_data}")
```

### Export tables to CSV

```python
import csv, io
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
buf = io.StringIO()
writer = csv.writer(buf)

for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        values = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in row.GetChildNodes(TableCell)
        ]
        writer.writerow(values)
    writer.writerow([])

csv_text = buf.getvalue()
print(csv_text)
```

### Count rows and columns

```python
from aspose.note import Document, Table, TableRow, TableCell

doc = Document("MyNotes.one")
for i, table in enumerate(doc.GetChildNodes(Table), start=1):
    rows = table.GetChildNodes(TableRow)
    cols = len(rows[0].GetChildNodes(TableCell)) if rows else 0
    print(f"Table {i}: {len(rows)} row(s) x {cols} column(s)")
```

### Tables with images in cells

Cells can contain `Image` nodes alongside or instead of `RichText`:

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText, Image

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        for cell in row.GetChildNodes(TableCell):
            texts = cell.GetChildNodes(RichText)
            images = cell.GetChildNodes(Image)
            if images:
                print(f"  Cell with {len(images)} image(s) and {len(texts)} text(s)")
```

### Inspect tags on a table

```python
from aspose.note import Document, Table

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    for tag in table.Tags:
        print(f"Table tag: {tag.label!r}  completed={tag.completed}")
```

---

## DOM Position

```
OutlineElement
  └── Table
        └── TableRow (0..n)
              └── TableCell (0..n)
                    ├── RichText (0..n)
                    └── Image (0..n)
```

`Table` is always a child of `OutlineElement`. Use `table.ParentNode` to access the containing `OutlineElement`.

---

## See Also

- [RichText](richtext/) — text content within cells
- [Image](image/) — image content within cells
- [Table Parsing Developer Guide](https://docs.aspose.org/note/python/developer-guide/tables/)
- [How to Parse Tables (KB)](https://kb.aspose.org/note/python/how-to-parse-onenote-tables-python/)
- [Blog: Parse OneNote Tables in Python](https://blog.aspose.org/note/python/parse-onenote-tables-python/)
