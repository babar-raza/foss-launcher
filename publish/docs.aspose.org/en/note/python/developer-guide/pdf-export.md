---
page_role: howto_article
description: >-
  Export Microsoft OneNote .one files to PDF in Python using Aspose.Note FOSS.
  Covers basic export, page range selection, tag icon rendering, and batch processing.
title: PDF Export — Aspose.Note FOSS for Python
type: docs
weight: 20
---

Aspose.Note FOSS for Python supports exporting loaded `.one` documents to PDF via `Document.Save()`. PDF rendering is provided by the optional [ReportLab](https://www.reportlab.com/) library. This is the only save format currently implemented; other `SaveFormat` values raise `UnsupportedSaveFormatException`.

---

## Prerequisites

Install the library with the `[pdf]` extra to pull in ReportLab:

```bash
pip install "aspose-note[pdf]"
```

Verify:

```bash
python -c "from aspose.note import Document, SaveFormat; print('PDF export ready')"
```

---

## Basic Export

Export all pages of a document to a single PDF file:

```python
from aspose.note import Document, SaveFormat

doc = Document("MyNotes.one")
doc.Save("output.pdf", SaveFormat.Pdf)
```

Pages appear in the PDF in the same order as they appear in the DOM.

---

## Using PdfSaveOptions

`PdfSaveOptions` provides fine-grained control over the export. Pass it instead of the bare `SaveFormat` enum:

```python
from aspose.note import Document, PdfSaveOptions, SaveFormat

opts = PdfSaveOptions(SaveFormat=SaveFormat.Pdf)

doc = Document("MyNotes.one")
doc.Save("output.pdf", opts)
```

### Tag Icon Rendering via PdfSaveOptions

`PdfSaveOptions` accepts tag icon display settings. Pass it instead of the bare `SaveFormat` enum when you need to customise tag icon rendering:

```python
from aspose.note import Document, PdfSaveOptions, SaveFormat

doc = Document("TaggedNotes.one")

opts = PdfSaveOptions(SaveFormat.Pdf)
opts.TagIconDir = "./my-icons"
opts.TagIconSize = 12.0
opts.TagIconGap = 2.0

doc.Save("tagged.pdf", opts)
```

> **Note on `PageIndex` / `PageCount`**: These fields exist on `PdfSaveOptions` but are **not forwarded to the PDF exporter in v26.2** and have no effect. The entire document is always exported.

---

## PdfSaveOptions Reference

| Property | Type | Default | Description |
|---|---|---|---|
| `PageIndex` | `int` | `0` | Field exists but **not forwarded to PDF exporter in v26.2** — has no effect |
| `PageCount` | `int \| None` | `None` | Field exists but **not forwarded to PDF exporter in v26.2** — has no effect |
| `TagIconDir` | `str \| None` | `None` | Path to directory containing custom NoteTag icon image files |
| `TagIconSize` | `float \| None` | `None` | Rendered size of tag icons in points |
| `TagIconGap` | `float \| None` | `None` | Padding around tag icons in points |

---

## Batch Export

Convert every `.one` file in a directory to PDF:

```python
from pathlib import Path
from aspose.note import Document, SaveFormat

input_dir = Path("./notes")
output_dir = Path("./pdfs")
output_dir.mkdir(parents=True, exist_ok=True)

for one_file in sorted(input_dir.glob("*.one")):
    try:
        doc = Document(str(one_file))
        out = output_dir / one_file.with_suffix(".pdf").name
        doc.Save(str(out), SaveFormat.Pdf)
        print(f"OK  {one_file.name} -> {out.name}  ({doc.Count()} pages)")
    except Exception as exc:
        print(f"ERR {one_file.name}: {exc}")
```

---

## Load from Stream, Save to File

Combine stream-based loading with file-based PDF output:

```python
from pathlib import Path
from aspose.note import Document, SaveFormat

one_bytes = Path("MyNotes.one").read_bytes()

import io
doc = Document(io.BytesIO(one_bytes))
doc.Save("output.pdf", SaveFormat.Pdf)
```

---

## Get PDF Bytes In-Memory

`Document.Save()` accepts a binary stream directly — no temporary file needed:

```python
import io
from aspose.note import Document, PdfSaveOptions, SaveFormat

doc = Document("MyNotes.one")

buf = io.BytesIO()
doc.Save(buf, PdfSaveOptions(SaveFormat.Pdf))
pdf_bytes = buf.getvalue()
print(f"PDF size: {len(pdf_bytes)} bytes")
```

---

## Supported and Unsupported SaveFormat Values

| SaveFormat | Status |
|---|---|
| `SaveFormat.Pdf` | Implemented |
| `SaveFormat.One` | Raises `UnsupportedSaveFormatException` |
| `SaveFormat.Html` | Raises `UnsupportedSaveFormatException` |
| `SaveFormat.Jpeg` | Raises `UnsupportedSaveFormatException` |
| `SaveFormat.Png` | Raises `UnsupportedSaveFormatException` |
| `SaveFormat.Gif` | Raises `UnsupportedSaveFormatException` |
| `SaveFormat.Bmp` | Raises `UnsupportedSaveFormatException` |
| `SaveFormat.Tiff` | Raises `UnsupportedSaveFormatException` |

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `ImportError: No module named 'reportlab'` | `[pdf]` extra not installed | `pip install "aspose-note[pdf]"` |
| `UnsupportedSaveFormatException` | Non-PDF SaveFormat used | Use `SaveFormat.Pdf` only |
| `IncorrectPasswordException` | Encrypted .one file | Use an unencrypted file |
| `FileNotFoundError` | Input .one path wrong | Verify path with `Path.exists()` |
| Permission error on output | Output directory not writable | Check output directory permissions |
