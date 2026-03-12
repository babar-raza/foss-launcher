---
page_role: howto_article
title: "Extract Text from OneNote Files Using Python"
seoTitle: "How to Extract Text from .one Files in Python — Aspose.Note FOSS"
description: "Step-by-step guide to extracting plain text, formatted runs, and hyperlinks from Microsoft OneNote .one files using the free Aspose.Note FOSS Python library."
date: "2026-03-10"
draft: false
author: "Aspose"
summary: "Learn how to use Aspose.Note FOSS for Python to extract plain text, formatting metadata, and hyperlinks from OneNote .one section files — no Microsoft Office required."
tags: ["onenote", "python", "text-extraction", "open-source", "foss"]
categories: ["Aspose.Note"]
---

## Extract Text from OneNote Files Using Python

If you need to read text from Microsoft OneNote `.one` files in a Python script — without installing Microsoft Office or running Windows — **Aspose.Note FOSS for Python** is the solution. It is a 100% free, open-source library that parses the OneNote binary format directly and exposes a clean Python API.

### Install

```bash
pip install aspose-note
```

No API key. No license file. No Microsoft Office.

---

## The Simplest Approach: GetChildNodes(RichText)

OneNote text is stored in `RichText` nodes distributed across pages, outlines, and outline elements. `GetChildNodes(RichText)` performs a recursive search of the entire document tree and returns every text node as a flat list:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    if rt.Text:
        print(rt.Text)
```

This is the fastest way to get all text content out of a `.one` file.

---

## Save Text to a File

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
lines = [rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text]

with open("extracted.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Saved {len(lines)} text blocks to extracted.txt")
```

---

## Extract Text Per Page

When you need to know which page each text block came from:

```python
from aspose.note import Document, Page, RichText

doc = Document("MyNotes.one")
for page in doc.GetChildNodes(Page):
    title = (
        page.Title.TitleText.Text
        if page.Title and page.Title.TitleText
        else "(untitled)"
    )
    page_texts = [rt.Text for rt in page.GetChildNodes(RichText) if rt.Text]
    print(f"\n=== {title} ===")
    for text in page_texts:
        print(text)
```

---

## Extract Hyperlinks

Hyperlinks are stored on individual `TextRun` objects within `RichText` nodes. Check `run.Style.IsHyperlink`:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.IsHyperlink and run.Style.HyperlinkAddress:
            print(f"{run.Text!r}  ->  {run.Style.HyperlinkAddress}")
```

---

## Detect Formatting: Bold, Italic, Underline

Each `TextRun` carries per-character formatting through its `TextStyle`:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        s = run.Style
        if any([s.Bold, s.Italic, s.Underline]):
            flags = ", ".join(f for f, v in [
                ("bold", s.Bold), ("italic", s.Italic), ("underline", s.Underline)
            ] if v)
            print(f"[{flags}] {run.Text.strip()!r}")
```

---

## Read from a Stream

Works with cloud storage, HTTP response bodies, or in-memory buffers:

```python
import io, urllib.request
from aspose.note import Document, RichText

##Example: load from bytes already in memory
one_bytes = open("MyNotes.one", "rb").read()
doc = Document(io.BytesIO(one_bytes))
texts = [rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text]
print(f"Extracted {len(texts)} text block(s)")
```

---

## Windows Encoding Fix

On Windows terminals, `sys.stdout` may use a legacy encoding that crashes on Unicode characters. Add this at the start of your script:

```python
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

---

## What the Library Supports

| Feature | Supported |
|---|---|
| Read `.one` files (path or stream) | Yes |
| Extract `RichText.Text` (plain text) | Yes |
| Inspect `TextRun.Style` (bold, italic, hyperlink, font) | Yes |
| Extract text from table cells | Yes |
| Read page titles | Yes |
| Write back to `.one` | No |
| Encrypted documents | No |

---

## Next Steps

- [Full text extraction guide](https://docs.aspose.org/note/python/developer-guide/text-extraction/)
- [How-to: Extract Text (KB)](https://kb.aspose.org/note/python/how-to-extract-text-from-onenote-python/)
- [How-to: Export to PDF](https://kb.aspose.org/note/python/how-to-export-onenote-to-pdf-python/)
- [API Reference](https://reference.aspose.org/note/python/)
