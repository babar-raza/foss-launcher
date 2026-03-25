---
canonical: https://kb.aspose.org/note/python/load-notebooks/
canonical_import: aspose.note
code_import: aspose.note
date: '2026-03-24T16:57:01Z'
dateModified: '2026-03-24T16:57:01Z'
datePublished: '2026-03-24T16:57:01Z'
description: Aspose.Note supports reading `.one` files and exposes the file format
  via the read-only `FileFormat` property.
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
seoTitle: How to Load Files with Aspose.Note | Guide
slug: load-notebooks
title: How to Load Files with Aspose.Note
type: howto_article
url: /kb.aspose.org/note/python/load-notebooks/
weight: 11
---

## Problem

You will load a Microsoft OneNote (.one) file into memory using the `Document` class. Aspose.Note supports reading `.one` files and exposes the file format via the read-only `FileFormat` property.

## Prerequisites

- Install Python 3.8 or later.
- Run `pip install aspose.note` to install the library.
- Ensure your environment has read access to `.one` files.

## Loading the File

Aspose.Note -- Show how to load the file with code — cover file paths, streams, and load options.

For details on loading the file, see the Aspose.Note documentation.

## Code Example

You will load a OneNote file using Aspose.Note, inspect its structure, and print a summary of its pages and content types. This example uses only the canonical `aspose.note` import and documented API methods.

- Python 3.7+ installed
- Aspose.Note for Python via pip (`pip install aspose-note`)

### Load and Inspect a OneNote File

Step 1: Import the library and load a `.one` file into a `Document` object. Use the `Document` constructor with the file path.

```python
import aspose.note

doc = aspose.note.Document("sample.one")
```

This returns a `Document` instance with the file's content loaded into memory.

Step 2: Inspect the document's file format and page count using the `FileFormat` property and `Count()` method.

```python
print(f"File format: {doc.FileFormat}")
print(f"Page count: {doc.Count()}")
```

The output shows the detected format (e.g., OneNote2010) and number of pages.

Step 3: Iterate through pages and print basic node counts to verify structure.

```python
for i, page in enumerate(doc):
    outline_count = 0
    for node in page:
        if node.NodeType == aspose.note.NodeType.Outline:
            outline_count += 1
    print(f"Page {i+1}: {outline_count} outline(s)")
```

This confirms the presence of outline nodes per page, matching expected OneNote document structure.

### Error Handling

Wrap file loading in a try-except block to catch `FileCorruptedException` or `IncorrectDocumentStructureException`. These exceptions indicate malformed or unsupported files.

```python
try:
    doc = aspose.note.Document("sample.one")
except (aspose.note.FileCorruptedException, aspose.note.IncorrectDocumentStructureException) as e:
    print(f"File error: {e}")
```

This ensures robust handling of invalid input without crashing the application.

### Next Steps

After loading, you can traverse pages, extract text, or convert to PDF using `Save()`. See the API reference for `Document.Save()` and `DocumentVisitor` for advanced processing.

## Supported Formats

Aspose.Note supports loading Microsoft OneNote files for programmatic access and conversion. You will load `.one` files and inspect their format using the `Document` class and `FileFormat` enum.

| Format | Extension | Notes |
|--------|-----------|-------|
| Microsoft OneNote | `.one` | Primary format; supports reading and DOM construction |
| PDF | `.pdf` | Output-only; saving to PDF is supported via `SaveFormat.Pdf` |
| OneNote 2007 | — | Detected as `FileFormat.OneNote2007` |
| OneNote 2010 | — | Detected as `FileFormat.OneNote2010` |
| OneNote Online | — | Detected as `FileFormat.OneNoteOnline` |

The `FileFormat` enum identifies the source format after loading. Use `document.FileFormat` to inspect the detected version of the loaded `.one` file.

```python
import aspose.note

document = aspose.note.Document("sample.one")
print(document.FileFormat)
```

## See Also

Aspose.Note -- Related: saving, converting, and format-specific guides.

For details on see also, see the Aspose.Note documentation.

- [Frequently asked questions](/kb.aspose.org/note/python/frequently-asked-questions/)
- [Export notebooks to PDF](/blog.aspose.org/note/python/export-pdf-notebooks/)
- [Introducing Note Foss Python](/blog.aspose.org/note/python/note-foss/)
- [Convert file formats](/docs.aspose.org/note/python/developer-guide/document-conversion/)
- [Manage notebooks](/docs.aspose.org/note/python/developer-guide/notebook-manipulation/)
