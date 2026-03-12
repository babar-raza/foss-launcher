---
page_role: howto_article
title: "Introducing Aspose.Note FOSS for Python — Free OneNote File Reading API"
seoTitle: "Aspose.Note FOSS for Python — Free, Open-Source OneNote Reader"
description: "Aspose.Note FOSS for Python is now available on PyPI. Read Microsoft OneNote .one files, extract text and images, parse tables, and export to PDF — entirely free, MIT-licensed, no Microsoft Office required."
date: "2026-03-10"
draft: false
author: "Aspose"
summary: "Aspose.Note FOSS for Python brings a familiar, Aspose.Note-shaped API for reading OneNote .one files to the Python ecosystem. Install from PyPI, extract text and images, traverse the document DOM, and export to PDF — no Microsoft Office, no proprietary runtime."
tags: ["onenote", "python", "open-source", "foss", "pdf-export", "text-extraction"]
categories: ["Aspose.Note"]
---

## Aspose.Note FOSS for Python Is Now Available

We are pleased to announce the availability of **Aspose.Note FOSS for Python** on PyPI. This free, open-source library lets Python developers read Microsoft OneNote `.one` section files, traverse their full document object model, extract content, and export to PDF — without requiring Microsoft Office or any proprietary runtime.

Install it now:

```bash
pip install aspose-note
```

For PDF export:

```bash
pip install "aspose-note[pdf]"
```

---

## What Is Aspose.Note FOSS for Python?

Aspose.Note FOSS for Python is a 100% free, MIT-licensed Python library that provides an **Aspose.Note-shaped public API** (`aspose.note.*`) for reading Microsoft OneNote `.one` files. It is backed by a built-in pure-Python MS-ONE/OneStore binary parser — no COM interop, no platform-native DLL, no Microsoft Office installation required.

The API surface is modeled after [Aspose.Note for .NET](https://products.aspose.com/note/net/), making the transition familiar for teams already using Aspose products on other platforms.

---

## Key Capabilities

### Read Any .one File

Load OneNote 2010, OneNote Online, and OneNote 2007 section files from a file path or any binary stream:

```python
from aspose.note import Document

doc = Document("MyNotes.one")
print(doc.DisplayName)   # Section name
print(doc.Count())       # Number of pages
```

### Traverse the Full Document DOM

The library exposes a complete document object model: `Document → Page → Outline → OutlineElement → RichText / Image / Table / AttachedFile`. Use `GetChildNodes(Type)` for recursive, type-filtered searches:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
all_text = [rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text]
```

### Extract Text with Rich Formatting

Every `RichText` node contains a list of `TextRun` segments. Each run carries per-character `TextStyle` metadata: bold, italic, underline, font name, font color, hyperlink address, and more:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.IsHyperlink:
            print(f"  Link: {run.Text} -> {run.Style.HyperlinkAddress}")
        elif run.Style.Bold:
            print(f"  Bold: {run.Text}")
```

### Save Images and Attachments

Retrieve embedded images as raw bytes with filename and dimensions. Save attached files to disk:

```python
from aspose.note import Document, Image, AttachedFile

doc = Document("MyNotes.one")
for img in doc.GetChildNodes(Image):
    with open(img.FileName or "image.bin", "wb") as f:
        f.write(img.Bytes)

for af in doc.GetChildNodes(AttachedFile):
    with open(af.FileName or "attachment.bin", "wb") as f:
        f.write(af.Bytes)
```

### Parse Tables

Walk `Table → TableRow → TableCell` hierarchies and read cell content:

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        cells = [
            " ".join(rt.Text for rt in cell.GetChildNodes(RichText))
            for cell in row.GetChildNodes(TableCell)
        ]
        print(cells)
```

### Export to PDF

Save any loaded document to PDF using the optional ReportLab backend. Configure page range and tag icon rendering with `PdfSaveOptions`:

```python
from aspose.note import Document, SaveFormat

doc = Document("MyNotes.one")
doc.Save("output.pdf", SaveFormat.Pdf)
```

---

## Supported Content Types

| Content | Supported |
|---|---|
| Pages and page titles | Yes |
| Plain text (`RichText.Text`) | Yes |
| Formatted runs (bold, italic, underline, font, color) | Yes |
| Hyperlinks in text runs | Yes |
| Embedded images (bytes, filename, dimensions) | Yes |
| Attached files (bytes, filename) | Yes |
| Tables (rows, cells, column widths) | Yes |
| OneNote tags (NoteTag: shape, label, color) | Yes |
| Numbered and bulleted lists (NumberList) | Yes |
| Page metadata (author, creation time, level) | Yes |
| PDF export | Yes (ReportLab required) |
| Write back to `.one` | Not supported |
| Encrypted documents | Not supported |

---

## Familiar API for .NET Developers

Teams already using Aspose.Note for .NET will find the Python API immediately recognizable. Core classes such as `Document`, `Page`, `RichText`, `Image`, `DocumentVisitor`, and `SaveFormat` match the .NET equivalents in name and behavior.

For scenarios requiring full write support, conversion to additional formats, or encrypted document handling, the commercial [Aspose.Note for .NET](https://products.aspose.com/note/net/) and [Aspose.Note for Java](https://products.aspose.com/note/java/) products are available.

---

## Installation Summary

| Command | Purpose |
|---|---|
| `pip install aspose-note` | Core library (reading, traversal, DOM access) |
| `pip install "aspose-note[pdf]"` | Core + PDF export (adds ReportLab) |
| `pip install -e ".[pdf]"` | Editable install from source (contributors) |

**Requirements**: Python 3.10, 3.11, or 3.12. No Microsoft Office required.

---

## Get Started

- **PyPI**: https://pypi.org/project/aspose-note/
- **Source code**: https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python
- **Report issues**: https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/issues
- [Getting Started Guide](https://docs.aspose.org/note/python/getting-started/)
- [Developer Guide](https://docs.aspose.org/note/python/developer-guide/)
- [API Reference](https://reference.aspose.org/note/python/)
- [KB Articles](https://kb.aspose.org/note/python/)
