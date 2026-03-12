---
page_role: howto_article
title: Developer Guide
description: >-
  A comprehensive guide to using Aspose.Note FOSS for Python to read, traverse, and export
  Microsoft OneNote .one files. Covers the document DOM, content extraction, PDF export, and
  advanced traversal patterns.
type: docs
weight: 99
---

Aspose.Note FOSS for Python is a free, open-source library for reading Microsoft OneNote `.one` section files without any dependency on Microsoft Office. It provides a clean public API under the `aspose.note` package, modeled after the Aspose.Note for .NET interface. The library is suitable for document automation, content indexing, data extraction pipelines, and archival workflows.

This developer guide covers the full public API surface available in version 26.2, with runnable code examples for every major feature.

## Document Loading

Load a `.one` file from a file path or a binary stream. The `Document` class is the entry point for all operations.

### Load from a file path

```python
from aspose.note import Document

doc = Document("MyNotes.one")
print(doc.DisplayName)   # Display name of the section
print(doc.Count())       # Number of pages
```

### Load from a binary stream

Useful when reading from cloud storage, HTTP responses, or in-memory buffers:

```python
from pathlib import Path
from aspose.note import Document

with Path("MyNotes.one").open("rb") as f:
    doc = Document(f)

print(doc.DisplayName)
print(doc.Count())
```

### Load options

Use `LoadOptions` to set optional parameters at load time:

```python
from aspose.note import Document, LoadOptions

opts = LoadOptions()
opts.LoadHistory = True   # Include page history in the DOM
doc = Document("MyNotes.one", opts)
```

> **Note**: `DocumentPassword` exists on `LoadOptions` for API compatibility, but encrypted documents are not supported. Attempting to load an encrypted file raises `IncorrectPasswordException`.

---

## Document Structure (DOM)

The OneNote document model is a tree:

```
Document
  └── Page (0..n)
        ├── Title
        │     ├── TitleText (RichText)
        │     ├── TitleDate (RichText)
        │     └── TitleTime (RichText)
        └── Outline (0..n)
              └── OutlineElement (0..n)
                    ├── RichText
                    ├── Image
                    ├── Table
                    │     └── TableRow
                    │           └── TableCell
                    │                 └── RichText / Image
                    └── AttachedFile
```

Every node exposes `ParentNode` and a `Document` property that walks up to the root. Composite nodes support child iteration, `FirstChild`, `LastChild`, `AppendChildLast`, `InsertChild`, `RemoveChild`, and `GetChildNodes(Type)`.

---

## Iterating Pages

Pages are the direct children of `Document`. Iterate them directly or use `GetChildNodes`:

```python
from aspose.note import Document, Page

doc = Document("MyNotes.one")

for page in doc:
    title = page.Title.TitleText.Text if page.Title and page.Title.TitleText else "(untitled)"
    author = page.Author or "(unknown)"
    print(f"  {title}  [by {author}]")
```

Page metadata:

| Property | Type | Description |
|---|---|---|
| `Title` | `Title \| None` | Page title block |
| `Author` | `str \| None` | Author string |
| `CreationTime` | `datetime \| None` | Page creation time |
| `LastModifiedTime` | `datetime \| None` | Last modification time |
| `Level` | `int \| None` | Sub-page indent level |

---

## Text Extraction

### Extract all plain text

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
all_text = [rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text]
print("\n".join(all_text))
```

### Inspect formatting runs

Each `RichText` contains a list of `TextRun` segments. Each run carries its own `TextStyle`:

```python
from aspose.note import Document, RichText

doc = Document("FormattedNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        style = run.Style
        flags = []
        if style.Bold: flags.append("bold")
        if style.Italic: flags.append("italic")
        if style.IsHyperlink: flags.append(f"link={style.HyperlinkAddress}")
        print(f"{run.Text!r:40s} [{', '.join(flags)}]")
```

### Extract hyperlinks

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.IsHyperlink and run.Style.HyperlinkAddress:
            print(run.Text, "->", run.Style.HyperlinkAddress)
```

---

## Image Extraction

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
for i, img in enumerate(doc.GetChildNodes(Image), start=1):
    name = img.FileName or f"image_{i}.bin"
    with open(name, "wb") as f:
        f.write(img.Bytes)
    print(f"Saved {name}  ({img.Width}x{img.Height})")
```

Image properties: `FileName`, `Bytes`, `Width`, `Height`, `AlternativeTextTitle`, `AlternativeTextDescription`, `HyperlinkUrl`, `Tags`.

---

## Table Parsing

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    print("Column widths:", table.ColumnWidths)
    for r, row in enumerate(table.GetChildNodes(TableRow), start=1):
        cells = row.GetChildNodes(TableCell)
        row_text = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            for cell in cells
        ]
        print(f"Row {r}:", row_text)
```

---

## Attached Files

```python
from aspose.note import Document, AttachedFile

doc = Document("NotesWithAttachments.one")
for i, af in enumerate(doc.GetChildNodes(AttachedFile), start=1):
    name = af.FileName or f"attachment_{i}.bin"
    with open(name, "wb") as f:
        f.write(af.Bytes)
    print(f"Saved: {name}")
```

---

## Tags and Numbered Lists

### Inspect NoteTag items

```python
from aspose.note import Document, RichText, Image, Table

doc = Document("TaggedNotes.one")
for rt in doc.GetChildNodes(RichText):
    for tag in rt.Tags:
        print(f"RichText tag: {tag.label} shape={tag.shape}")
for img in doc.GetChildNodes(Image):
    for tag in img.Tags:
        print(f"Image tag: {tag.label}")
```

### Inspect numbered lists

```python
from aspose.note import Document, OutlineElement

doc = Document("NumberedNotes.one")
for oe in doc.GetChildNodes(OutlineElement):
    nl = oe.NumberList
    if nl:
        print(f"indent={oe.IndentLevel} numbered={nl.IsNumbered} format={nl.Format!r}")
```

---

## DocumentVisitor Pattern

Use `DocumentVisitor` to implement a visitor that walks the entire document tree:

```python
from aspose.note import Document, DocumentVisitor, Page, RichText, Image

class ContentCounter(DocumentVisitor):
    def __init__(self):
        self.pages = 0
        self.texts = 0
        self.images = 0

    def VisitPageStart(self, page: Page) -> None:
        self.pages += 1

    def VisitRichTextStart(self, rt: RichText) -> None:
        self.texts += 1

    def VisitImageStart(self, img: Image) -> None:
        self.images += 1

doc = Document("MyNotes.one")
counter = ContentCounter()
doc.Accept(counter)
print(f"Pages: {counter.pages}, Texts: {counter.texts}, Images: {counter.images}")
```

---

## PDF Export

PDF export requires the optional ReportLab dependency. Install it with:

```bash
pip install "aspose-note[pdf]"
```

### Basic PDF export

```python
from aspose.note import Document, SaveFormat

doc = Document("MyNotes.one")
doc.Save("output.pdf", SaveFormat.Pdf)
```

### PDF export with tag icon options

```python
import io
from aspose.note import Document, PdfSaveOptions, SaveFormat

doc = Document("MyNotes.one")

##With tag icon customization
opts = PdfSaveOptions(SaveFormat.Pdf)
opts.TagIconDir = "./tag-icons"   # Custom directory for tag icons
opts.TagIconSize = 10             # Icon size in points
opts.TagIconGap = 2               # Gap around icons in points
doc.Save("output.pdf", opts)

##Save to in-memory stream
buf = io.BytesIO()
doc.Save(buf, PdfSaveOptions(SaveFormat.Pdf))
pdf_bytes = buf.getvalue()
```

> **Note**: `PdfSaveOptions.PageIndex` and `PageCount` fields exist but are not forwarded to the PDF exporter in v26.2 — the entire document is always exported.

---

## Current Limitations

| Area | Status |
|---|---|
| Reading `.one` files | Fully supported |
| PDF export (via ReportLab) | Supported |
| Writing back to `.one` | Not implemented |
| Encrypted documents | Not supported (raises `IncorrectPasswordException`) |
| HTML / image / ONE save formats | Declared for API compatibility; raise `UnsupportedSaveFormatException` |

---

## Available Guides

- [Features Overview](features/) — full feature list with evidence
- [Getting Started](/docs.aspose.org/note/python/getting-started/) — prerequisites, installation, and first steps
- [Installation](/docs.aspose.org/note/python/getting-started/installation/) — pip install and optional dependencies

---

## See Also

- [Knowledge Base — All How-to Articles](https://kb.aspose.org/note/python/)
- [API Reference](https://reference.aspose.org/note/python/)
- [Blog — Aspose.Note for Python](https://blog.aspose.org/note/python/)
