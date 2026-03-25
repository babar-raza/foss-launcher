---
canonical: https://kb.aspose.org/note/python/how-to-convert-pdf-to-tiff-python/
canonical_import: aspose.note
code_import: aspose.note
date: '2026-03-24T16:57:01Z'
dateModified: '2026-03-24T16:57:01Z'
datePublished: '2026-03-24T16:57:01Z'
description: Aspose.Note supports reading `.one` files and exporting to PDF only;
  other formats are not implemented.
display_name: Aspose.Note
family: note
keywords:
- note python
- note python code
- note python google
- python note pdf
- python note pad
- python note taking app
- python note syntax
- python note for professional
lastmod: '2026-03-24T16:57:01Z'
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.Note | Guide
slug: how-to-convert-pdf-to-tiff-python
title: How to Convert File Formats with Aspose.Note
type: howto_article
url: /kb.aspose.org/note/python/how-to-convert-pdf-to-tiff-python/
weight: 13
---

## Problem

You will load a OneNote (.one) file using the `Document` class and convert it to PDF using the `Save` method with `SaveFormat.Pdf`. Aspose.Note supports reading `.one` files and exporting to PDF only; other formats are not implemented.

- Install the `aspose.note` package via pip
- Ensure input files are unencrypted `.one` files (encrypted files raise `IncorrectPasswordException`)

## Prerequisites

- Install Python 3.8 or later.
- Run `pip install aspose.note` to install the library.
- Ensure your input file is a valid `.one` file (OneNote 2007–2010 or OneNote Online format).

## Conversion Steps

You will convert a Microsoft OneNote (.one) file to PDF using the `Document` class and its `Save` method with `SaveFormat.Pdf`. This operation reads the source file into memory and writes the output in PDF format.

- Aspose.Note for Python is installed and accessible via `import aspose.note`
- You have a valid `.one` file path and write permissions for the output directory

### Step 1: Load the OneNote source file

Instantiate the `Document` class with the path to your `.one` file. This loads the document structure into memory for further processing.

```python
import aspose.note

doc = aspose.note.Document("input.one")
```

The `Document` object now holds the parsed content of the OneNote file.

### Step 2: `Save` the document as PDF

Call the `Save` method on the `Document` instance, specifying the output path and `SaveFormat.Pdf` to generate a PDF version.

```python
doc.save("output.pdf", aspose.note.SaveFormat.Pdf)
```

This writes the converted PDF file to disk. The `FileFormat` property of the loaded document is read-only and reflects the original format.

### Code Breakdown

The `Document` constructor parses the `.one` file and builds the internal DOM. The `Save` method supports writing to a file path or stream, and accepts `SaveFormat.Pdf` as the only implemented output format.

### Error Handling

Handle `FileCorruptedException` for malformed input files and `IncorrectPasswordException` if the file is encrypted (password-protected files are not supported). Wrap operations in try-except blocks to catch `AsposeNoteError` for general library errors.

```python
try:
    doc = aspose.note.Document("input.one")
    doc.save("output.pdf", aspose.note.SaveFormat.Pdf)
except aspose.note.FileCorruptedException as e:
    print(f"File corruption detected: {e}")
except aspose.note.IncorrectPasswordException as e:
    print(f"Password-protected files are not supported: {e}")
except aspose.note.AsposeNoteError as e:
    print(f"General error: {e}")
```

## Code Example

You will load a OneNote document and save it as a PDF using the `Document` class and its `Save` method. This example demonstrates the only supported export format in Aspose.Note for Python.

- Aspose.Note for Python installed (`pip install aspose-note`)
- A valid `.one` file available locally

### Load and `Save` a OneNote `Document` as PDF

Step 1: Import the library and load the `.one` file using the `Document` class. Call `Save` with a target path and `SaveFormat.Pdf` to export the document.

```python
import aspose.note

doc = aspose.note.Document("input.one")
doc.save("output.pdf", aspose.note.SaveFormat.Pdf)
```

This produces a PDF file named `output.pdf` in the current working directory. The `SaveFormat.Pdf` enum value is the only export format currently implemented in Aspose.Note.

### Error Handling for Common Failures

Handle `FileCorruptedException` if the input file is malformed, and `IncorrectPasswordException` if the file is encrypted (password-protected files are not supported). Wrap the operation in a try-except block to catch these explicitly.

```python
try:
    doc = aspose.note.Document("input.one")
    doc.save("output.pdf", aspose.note.SaveFormat.Pdf)
except aspose.note.FileCorruptedException as e:
    print(f"File corruption detected: {e}")
except aspose.note.IncorrectPasswordException as e:
    print(f"Encrypted files are not supported: {e}")
```

The `Document.FileFormat` property returns the detected format (OneNote2007, OneNote2010, or OneNoteOnline) and is read-only. Use `DetectLayoutChanges()` before saving if layout consistency is critical.

## Supported Formats

You will convert OneNote documents to PDF using Aspose.Note. The library supports reading `.one` files and saving them as PDF via the `Document` class and `SaveFormat.Pdf`.

| Format | Extension | Notes |
|--------|-----------|-------|
| OneNote 2010 | .one | Read-only; use `Document` to load |
| PDF | .pdf | Write-only; use `SaveFormat.Pdf` with `Document.save()` |
| OneNote Online | .one | Read-only; use `Document` to load |
| OneNote 2007 | .one | Read-only; use `Document` to load |

Only the `.one` format is supported for input, and only PDF is supported for output. Other formats like HTML, images, or round-trip `.one` saving are not implemented.

```python
import aspose.note
from aspose.note import Document, SaveFormat

doc = Document("input.one")
doc.save("output.pdf", SaveFormat.PDF)
```

## See Also

You will explore related conversion workflows and format documentation for Aspose.Note, focusing on supported operations like loading .one files and exporting to PDF. This section points to essential resources for developers building note-taking applications in Python.

- [Frequently asked questions](/kb.aspose.org/note/python/frequently-asked-questions/)
- [Export notebooks to PDF](/blog.aspose.org/note/python/export-pdf-notebooks/)
- [Introducing Note Foss Python](/blog.aspose.org/note/python/note-foss/)
- [Convert file formats step-by-step](/docs.aspose.org/note/python/developer-guide/document-conversion/)
- [Manage notebooks programmatically](/docs.aspose.org/note/python/developer-guide/notebook-manipulation/)
