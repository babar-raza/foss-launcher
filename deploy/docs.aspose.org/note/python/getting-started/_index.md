---
page_role: howto_article
title: Getting Started
description: >-
  Get up and running with Aspose.Note FOSS for Python. Learn what the library does,
  what you need to install it, and how to read your first OneNote .one file in minutes.
type: docs
weight: 10
---

Aspose.Note FOSS for Python is a free, open-source library for reading Microsoft OneNote `.one` section files. It provides a public API modeled after Aspose.Note for .NET, backed by a pure-Python MS-ONE/OneStore binary parser. No Microsoft Office installation is required.

## What You Can Do

- **Read `.one` files** — open any OneNote 2010, OneNote Online, or OneNote 2007 section file
- **Traverse the document DOM** — navigate pages, outlines, outline elements, and all content types
- **Extract text** — read plain text or inspect individual formatting runs (bold, italic, hyperlinks, font color)
- **Extract images** — retrieve embedded images as raw bytes with filename and dimensions
- **Extract attached files** — save embedded file attachments to disk
- **Parse tables** — walk table rows and cells, read column widths and cell content
- **Inspect tags and lists** — read OneNote tags (NoteTag) and numbered list metadata
- **Export to PDF** — save any loaded document to PDF using the optional ReportLab backend

## Prerequisites

| Requirement | Details |
|---|---|
| Python | 3.10 or later |
| Operating system | Any (Windows, Linux, macOS) — OS-independent |
| Microsoft Office | **Not required** |
| PDF export | Requires `reportlab>=3.6` — install via the `[pdf]` extra |

## Installation

Install the core library from PyPI:

```bash
pip install aspose-note
```

If you plan to export documents to PDF, install with the `[pdf]` extra:

```bash
pip install "aspose-note[pdf]"
```

For detailed installation options (editable installs, virtual environments), see the [Installation guide](installation/).

## Your First Script

The following script loads a OneNote section file, prints the section display name and page count, then lists every page title:

```python
from aspose.note import Document

doc = Document("MyNotes.one")
print(f"Section: {doc.DisplayName}")
print(f"Pages:   {doc.Count()}")

for page in doc:
    title = (
        page.Title.TitleText.Text
        if page.Title and page.Title.TitleText
        else "(untitled)"
    )
    print(f"  - {title}")
```

**Important**: The public import path is `from aspose.note import ...`. Do not use `import aspose_note` or `from onenote import ...`—those are not the correct package names.

## Extract All Text

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    if rt.Text:
        print(rt.Text)
```

## Export to PDF

```python
from aspose.note import Document, SaveFormat

doc = Document("MyNotes.one")
doc.Save("output.pdf", SaveFormat.Pdf)
```

Requires `pip install "aspose-note[pdf]"`.

## Next Steps

- [Installation](installation/) — all install methods, virtual environments, PDF dependency
- [Developer Guide](../developer-guide/) — full API reference with examples for text, images, tables, tags, and PDF
- [Features Overview](../developer-guide/features/) — complete feature list with code samples
- [KB Articles](https://kb.aspose.org/note/python/) — practical how-to guides
- [API Reference](https://reference.aspose.org/note/python/) — full class and method reference
