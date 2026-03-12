---
page_role: howto_article
title: "How to Extract Text from OneNote Files in Python"
description: "Learn how to extract plain text, formatted runs, and hyperlinks from Microsoft OneNote .one files using Aspose.Note FOSS for Python."
date: 2026-03-10
lastmod: 2026-03-10
weight: 10
slug: "how-to-extract-text-onenote-python"
draft: false
type: "topic"
keywords:
  - "extract text from onenote python"
  - "read onenote file python"
  - "onenote text extraction python"
  - "parse one file python"
  - "aspose note python text"
  - "onenote python library"
  - "read onenote without office python"
step1: "Install aspose-note from PyPI"
step2: "Load the .one file with the Document class"
step3: "Call GetChildNodes(RichText) to collect all text nodes"
step4: "Iterate RichText.Runs to inspect formatted segments"
step5: "Filter runs by formatting properties (bold, hyperlink, etc.)"
step6: "Write extracted text to a file or process it in your application"
---

Microsoft OneNote `.one` files are binary documents that cannot be read as plain text or parsed with generic XML tools. Aspose.Note FOSS for Python provides a pure-Python parser that loads `.one` files into a full document object model (DOM), making it straightforward to extract text, formatting metadata, and hyperlinks programmatically.

### Benefits of Using Aspose.Note FOSS for Python

1. **No Microsoft Office required** — read `.one` files on any platform, including Linux CI/CD servers
2. **Full text and formatting access** — plain text, bold/italic/underline runs, font properties, and hyperlink URLs
3. **Free and open-source** — MIT license, no usage fees or API keys

---

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install Aspose.Note FOSS for Python

Install the library from PyPI. The core package has no mandatory dependencies:

```bash
pip install aspose-note
```

Verify the installation:

```python
from aspose.note import Document
print("Installation OK")
```

---

### Step 2: Load the .one File

Create a `Document` instance by passing the file path:

```python
from aspose.note import Document

doc = Document("MyNotes.one")
print(f"Section: {doc.DisplayName}")
print(f"Pages:   {doc.Count()}")
```

To load from a binary stream (e.g. from cloud storage or an HTTP response):

```python
from aspose.note import Document

with open("MyNotes.one", "rb") as f:
    doc = Document(f)
```

---

### Step 3: Extract All Plain Text

Use `GetChildNodes(RichText)` to collect every `RichText` node in the document tree. This performs a recursive depth-first search across all pages, outlines, and outline elements:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
texts = [rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text]

for text in texts:
    print(text)
```

To save all text to a file:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
texts = [rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text]

with open("extracted_text.txt", "w", encoding="utf-8") as out:
    out.write("\n".join(texts))

print(f"Wrote {len(texts)} text blocks to extracted_text.txt")
```

---

### Step 4: Inspect Formatted Runs

Each `RichText` node contains a `Runs` list of `TextRun` segments. Each run carries an independent `TextStyle` with per-character formatting:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")

for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        style = run.Style
        attrs = []
        if style.Bold:        attrs.append("bold")
        if style.Italic:      attrs.append("italic")
        if style.Underline:   attrs.append("underline")
        if style.Strikethrough: attrs.append("strikethrough")
        if style.FontName:    attrs.append(f"font={style.FontName}")
        if style.FontSize:    attrs.append(f"size={style.FontSize}pt")
        label = ", ".join(attrs) if attrs else "plain"
        print(f"[{label}] {run.Text!r}")
```

---

### Step 5: Extract Hyperlinks

Hyperlinks are stored on individual `TextRun` nodes. Check `Style.IsHyperlink` and read `Style.HyperlinkAddress`:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")

for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.IsHyperlink and run.Style.HyperlinkAddress:
            print(f"Link text: {run.Text!r}")
            print(f"URL:       {run.Style.HyperlinkAddress}")
```

---

### Step 6: Extract Text Per Page

To extract text organized by page title:

```python
from aspose.note import Document, Page, RichText

doc = Document("MyNotes.one")

for page in doc.GetChildNodes(Page):
    title = (
        page.Title.TitleText.Text
        if page.Title and page.Title.TitleText
        else "(untitled)"
    )
    print(f"\n=== {title} ===")
    for rt in page.GetChildNodes(RichText):
        if rt.Text:
            print(rt.Text)
```

{{% /steps %}}

---

## Common Issues and Fixes

### 1. ImportError: No module named 'aspose'

**Cause**: The package is not installed in the active Python environment.

**Fix**:
```bash
pip install aspose-note
##Confirm active environment:
pip show aspose-note
```

### 2. FileNotFoundError when loading .one file

**Cause**: The file path is incorrect or the file does not exist.

**Fix**: Use an absolute path or verify the file exists before loading:

```python
from pathlib import Path
from aspose.note import Document

path = Path("MyNotes.one")
if not path.exists():
    raise FileNotFoundError(f"File not found: {path.resolve()}")
doc = Document(str(path))
```

### 3. UnicodeEncodeError on Windows when printing

**Cause**: Windows terminals may use a legacy encoding that cannot render Unicode characters.

**Fix**: Reconfigure stdout at the start of your script:

```python
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

### 4. Empty text results

**Cause**: The `.one` file may be empty, contain only images or tables (no RichText nodes), or be a notebook file (`.onetoc2`) rather than a section file (`.one`).

**Fix**: Check the page count and inspect node types:

```python
from aspose.note import Document

doc = Document("MyNotes.one")
print(f"Pages: {doc.Count()}")
for page in doc:
    print(f"  Children: {sum(1 for _ in page)}")
```

### 5. IncorrectPasswordException

**Cause**: The `.one` file is encrypted. Encrypted documents are not supported.

**Fix**: Aspose.Note FOSS for Python does not support encrypted `.one` files. The full-featured commercial Aspose.Note product supports decryption.

---

## Frequently Asked Questions

### Can I extract text from all pages at once?

Yes. `doc.GetChildNodes(RichText)` searches the entire document tree recursively, including all pages, outlines, and outline elements.

### Does the library support .onetoc2 notebook files?

No. The library handles `.one` section files only. Notebook table-of-contents files (`.onetoc2`) are a different format and are not supported.

### Can I extract text from tables?

Yes. `TableCell` nodes contain `RichText` children that can be read the same way:

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        for cell in row.GetChildNodes(TableCell):
            cell_text = " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
            print(cell_text, end="\t")
        print()
```

### What Python versions are supported?

Python 3.10, 3.11, and 3.12.

### Is the library thread-safe?

Each `Document` instance should be used from a single thread. For parallel extraction, create a separate `Document` per thread.

---

**Related Resources:**

- [Features Overview](https://docs.aspose.org/note/python/developer-guide/features/)
- [Developer Guide](https://docs.aspose.org/note/python/developer-guide/)
- [How to Export to PDF](how-to-export-onenote-to-pdf-python/)
- [API Reference](https://reference.aspose.org/note/python/)
