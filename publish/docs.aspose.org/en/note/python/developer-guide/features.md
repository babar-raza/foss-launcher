---
page_role: howto_article
description: >-
  A complete reference of features available in Aspose.Note FOSS for Python v26.2.
  All features are verified against the repository source code, README, and example files.
title: Features Overview — Aspose.Note FOSS for Python
type: docs
---

Aspose.Note FOSS for Python (package `aspose-note`, version 26.2) provides a Python API for reading Microsoft OneNote `.one` section files and exporting them to PDF. All features listed below are verified against the repository source code, README, and example scripts.

## Installation and Setup

Install from PyPI:

```bash
pip install aspose-note
```

For PDF export support (requires ReportLab):

```bash
pip install "aspose-note[pdf]"
```

Requirements: Python 3.10 or later. No Microsoft Office installation required.

---

## Features and Capabilities

### .one File Loading

Load Microsoft OneNote section files from a file path or any binary stream (file handle, `io.BytesIO`, HTTP response body, cloud storage stream).

- `Document.FileFormat` is available but always returns `FileFormat.OneNote2010` in v26.2 — it is a hardcoded constant, not detected from the file
- Stream-based loading eliminates disk I/O for in-memory or network workflows
- `LoadOptions.LoadHistory` flag controls whether page history is included in the DOM

```python
from aspose.note import Document

##From a file path
doc = Document("notebook.one")

##From a binary stream
with open("notebook.one", "rb") as f:
    doc = Document(f)
```

---

### Document DOM Traversal

The full OneNote document is exposed as a tree of typed Python objects. Every node inherits from `Node` or `CompositeNode`:

- **`Document`** — root; exposes `DisplayName`, `CreationTime`, `Count()`, `FileFormat`
- **`Page`** — direct child of `Document`; exposes `Title`, `Author`, `CreationTime`, `LastModifiedTime`, `Level`
- **`Title`** — exposes `TitleText`, `TitleDate`, `TitleTime` (all `RichText` nodes)
- **`Outline`** — positional container with `X`, `Y`, `Width`
- **`OutlineElement`** — leaf container; exposes `IndentLevel`, `NumberList`, `Tags`

Navigation methods on `CompositeNode`:

| Method / Property | Description |
|---|---|
| `FirstChild`, `LastChild` | Direct child access |
| `GetChildNodes(Type)` | Recursive, type-filtered search |
| `AppendChildLast(node)` | Add child at end |
| `AppendChildFirst(node)` | Add child at start |
| `InsertChild(index, node)` | Insert at position |
| `RemoveChild(node)` | Remove a child |
| `for child in node` | Iterate direct children |

```python
from aspose.note import Document, Page, Outline, OutlineElement, RichText

doc = Document("notebook.one")
for page in doc.GetChildNodes(Page):
    title_text = page.Title.TitleText.Text if page.Title and page.Title.TitleText else ""
    print(f"Page: {title_text}")
    for outline in page.GetChildNodes(Outline):
        for oe in outline.GetChildNodes(OutlineElement):
            for rt in oe.GetChildNodes(RichText):
                print(f"  {rt.Text}")
```

---

### Rich Text Content Extraction

`RichText` nodes expose:

- `Text: str` — full plain-text string
- `Runs: list[TextRun]` — list of formatted segments
- `FontSize: float | None` — paragraph-level font size
- `Tags: list[NoteTag]` — OneNote tags attached to this block
- `Append(text, style=None)` — append a text run in-memory
- `Replace(old_value, new_value)` — in-memory string substitution

Each `TextRun` carries:

| Property | Type | Description |
|---|---|---|
| `Text` | `str` | Segment text |
| `Style` | `TextStyle` | Formatting metadata |
| `Start`, `End` | `int \| None` | Character offsets |

`TextStyle` properties:

| Property | Type |
|---|---|
| `Bold`, `Italic`, `Underline`, `Strikethrough` | `bool` |
| `Superscript`, `Subscript` | `bool` |
| `FontName` | `str \| None` |
| `FontSize` | `float \| None` |
| `FontColor`, `HighlightColor` | `int \| None` (ARGB) |
| `LanguageId` | `int \| None` |
| `IsHyperlink` | `bool` |
| `HyperlinkAddress` | `str \| None` |

```python
from aspose.note import Document, RichText

doc = Document("notebook.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.IsHyperlink:
            print(f"Hyperlink: {run.Text} -> {run.Style.HyperlinkAddress}")
        if run.Style.Bold:
            print(f"Bold text: {run.Text}")
```

---

### Image Extraction

`Image` nodes expose raw bytes and metadata for every embedded image:

| Property | Type | Description |
|---|---|---|
| `FileName` | `str \| None` | Original filename |
| `Bytes` | `bytes` | Raw image data |
| `Width`, `Height` | `float \| None` | Dimensions in points |
| `AlternativeTextTitle` | `str \| None` | Alt text title — always `None` for parsed files in v26.2 |
| `AlternativeTextDescription` | `str \| None` | Alt text description |
| `HyperlinkUrl` | `str \| None` | Linked URL |
| `Tags` | `list[NoteTag]` | Attached OneNote tags |

```python
from aspose.note import Document, Image

doc = Document("notebook.one")
for i, img in enumerate(doc.GetChildNodes(Image), start=1):
    filename = img.FileName or f"image_{i}.bin"
    with open(filename, "wb") as f:
        f.write(img.Bytes)
    print(f"Saved: {filename}  ({img.Width} x {img.Height} pts)")
```

---

### Attached File Extraction

`AttachedFile` nodes expose embedded file attachments:

| Property | Type | Description |
|---|---|---|
| `FileName` | `str \| None` | Original filename |
| `Bytes` | `bytes` | Raw file data |
| `Tags` | `list[NoteTag]` | Attached OneNote tags |

```python
from aspose.note import Document, AttachedFile

doc = Document("notebook.one")
for i, af in enumerate(doc.GetChildNodes(AttachedFile), start=1):
    filename = af.FileName or f"attachment_{i}.bin"
    with open(filename, "wb") as f:
        f.write(af.Bytes)
```

---

### Table Parsing

`Table`, `TableRow`, and `TableCell` expose the full table structure:

| Class | Key Properties |
|---|---|
| `Table` | `ColumnWidths: list[float]`, `BordersVisible: bool`, `Tags: list[NoteTag]` |
| `TableRow` | Iterate cells via `GetChildNodes(TableCell)` |
| `TableCell` | Contains `RichText`, `Image`, and other content nodes |

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("notebook.one")
for table in doc.GetChildNodes(Table):
    print("Column widths:", table.ColumnWidths)
    for r, row in enumerate(table.GetChildNodes(TableRow), start=1):
        cells = row.GetChildNodes(TableCell)
        values = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in cells
        ]
        print(f"Row {r}:", values)
```

---

### OneNote Tag Inspection

`NoteTag` appears on `RichText`, `Image`, `Table`, and `OutlineElement` nodes. Properties:

| Property | Type | Description |
|---|---|---|
| `shape` | `int \| None` | Numeric tag shape identifier |
| `label` | `str \| None` | Display label string |
| `text_color` | `int \| None` | Text color as ARGB integer |
| `highlight_color` | `int \| None` | Highlight color as ARGB integer |
| `created` | `int \| None` | Raw MS timestamp integer (not datetime) |
| `completed` | `int \| None` | Raw MS timestamp integer (not datetime) |

Factory method: `NoteTag.CreateYellowStar()` creates a standard yellow-star tag node.

```python
from aspose.note import Document, RichText

doc = Document("notebook.one")
for rt in doc.GetChildNodes(RichText):
    for tag in rt.Tags:
        print(f"Tag: {tag.label} (shape={tag.shape}, completed={tag.completed})")
```

---

### Numbered List Support

`OutlineElement.NumberList` exposes:

| Property | Type | Description |
|---|---|---|
| `Format` | `str \| None` | List number format string |
| `Restart` | `int \| None` | Start number (for restarted lists) |
| `IsNumbered` | `bool` | True for ordered lists |

```python
from aspose.note import Document, OutlineElement

doc = Document("notebook.one")
for oe in doc.GetChildNodes(OutlineElement):
    nl = oe.NumberList
    if nl:
        print(f"indent={oe.IndentLevel} numbered={nl.IsNumbered} format={nl.Format!r}")
```

---

### DocumentVisitor Traversal

`DocumentVisitor` provides a visitor pattern for structured full-document traversal. Override any `VisitXxxStart` / `VisitXxxEnd` method to intercept specific node types:

- `VisitDocumentStart(doc)` / `VisitDocumentEnd(doc)`
- `VisitPageStart(page)` / `VisitPageEnd(page)`
- `VisitTitleStart(title)` / `VisitTitleEnd(title)`
- `VisitOutlineStart(outline)` / `VisitOutlineEnd(outline)`
- `VisitOutlineElementStart(oe)` / `VisitOutlineElementEnd(oe)`
- `VisitRichTextStart(rt)` / `VisitRichTextEnd(rt)`
- `VisitImageStart(img)` / `VisitImageEnd(img)`

```python
from aspose.note import Document, DocumentVisitor, Page, RichText, Image

class MySummaryVisitor(DocumentVisitor):
    def __init__(self):
        self.pages, self.texts, self.images = 0, 0, 0

    def VisitPageStart(self, page: Page) -> None:
        self.pages += 1

    def VisitRichTextStart(self, rt: RichText) -> None:
        self.texts += 1

    def VisitImageStart(self, img: Image) -> None:
        self.images += 1

doc = Document("notebook.one")
v = MySummaryVisitor()
doc.Accept(v)
print(f"Pages={v.pages}  RichText={v.texts}  Images={v.images}")
```

---

### PDF Export

Save a loaded document to PDF using `Document.Save()`. Supported via the optional ReportLab backend.

```python
from aspose.note import Document, SaveFormat

doc = Document("notebook.one")
doc.Save("output.pdf", SaveFormat.Pdf)
```

#### PdfSaveOptions

| Option | Type | Description |
|---|---|---|
| `PageIndex` | `int` | Field exists; **not forwarded to PDF exporter in v26.2** — has no effect |
| `PageCount` | `int \| None` | Field exists; **not forwarded to PDF exporter in v26.2** — has no effect |
| `TagIconDir` | `str \| None` | Directory containing custom tag icon images |
| `TagIconSize` | `float \| None` | Tag icon size in points |
| `TagIconGap` | `float \| None` | Padding around tag icons in points |

```python
import io
from aspose.note import Document, PdfSaveOptions, SaveFormat

doc = Document("notebook.one")

##Save to file
doc.Save("output.pdf", SaveFormat.Pdf)

##Save to in-memory stream
buf = io.BytesIO()
doc.Save(buf, PdfSaveOptions(SaveFormat.Pdf))
pdf_bytes = buf.getvalue()
```

---

## Format and Enum Reference

### SaveFormat

| Value | Status |
|---|---|
| `SaveFormat.Pdf` | Implemented (requires ReportLab) |
| `SaveFormat.One` | Declared only; raises `UnsupportedSaveFormatException` |
| `SaveFormat.Html` | Declared only; raises `UnsupportedSaveFormatException` |
| `SaveFormat.Jpeg`, `Png`, `Gif`, `Bmp`, `Tiff` | Declared only; raises `UnsupportedSaveFormatException` |

### FileFormat

`Document.FileFormat` always returns `FileFormat.OneNote2010` in v26.2 (hardcoded constant, not detected from file content). The enum declares three values:

| Value | Description |
|---|---|
| `FileFormat.OneNote2010` | Always returned by `Document.FileFormat` |
| `FileFormat.OneNoteOnline` | Declared in enum; not returned by parser |
| `FileFormat.OneNote2007` | Declared in enum; not returned by parser |

### NodeType

`NodeType.Document`, `NodeType.Page`, `NodeType.Outline`, `NodeType.OutlineElement`, `NodeType.RichText`, `NodeType.Image`, `NodeType.Table`, `NodeType.AttachedFile`

### HorizontalAlignment

`HorizontalAlignment.Left`, `HorizontalAlignment.Center`, `HorizontalAlignment.Right`

---

## Current Limitations

| Limitation | Detail |
|---|---|
| Read-only | Writing back to `.one` format is not implemented |
| No encryption | Encrypted documents raise `IncorrectPasswordException` |
| PDF only for export | Other `SaveFormat` values raise `UnsupportedSaveFormatException` |
| ReportLab required for PDF | Install `pip install "aspose-note[pdf]"` separately |
| `GetPageHistory` returns single-element list | Full page history traversal is a stub; returns `[page]` |
| `DetectLayoutChanges()` | Compatibility stub; no operation |

---

## Tips and Best Practices

- **Check for None**: `Page.Title`, `Title.TitleText`, `OutlineElement.NumberList`, and most metadata fields can be `None`. Always guard with `if x is not None` or `if x` before accessing properties.
- **Use `GetChildNodes(Type)`** for recursive search rather than manually iterating the tree. It searches the entire subtree.
- **Iterate direct children** with `for child in node` when you only need immediate children.
- **Handle encoding on Windows**: On Windows, `sys.stdout` may use a legacy code page. Add `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at startup when printing Unicode text.
- **Install `[pdf]` extra**: Do not import `SaveFormat.Pdf` functionality without first installing `pip install "aspose-note[pdf]"`. Without ReportLab, saving to PDF will raise an import error at runtime.
