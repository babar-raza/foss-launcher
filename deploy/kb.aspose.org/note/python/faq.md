---
canonical: https://kb.aspose.org/note/python/frequently-asked-questions/
canonical_import: aspose.note
code_import: aspose.note
date: '2026-03-24T16:57:01Z'
dateModified: '2026-03-24T16:57:01Z'
datePublished: '2026-03-24T16:57:01Z'
description: Other formats such as HTML, images (PNG/JPEG), or the native .one format
  are declared for API compatibility but not implemented. Attempting to save to these...
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
page_role: faq
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Note FAQ | Guide
slug: frequently-asked-questions
title: Aspose.Note FAQ
type: faq
url: /kb.aspose.org/note/python/frequently-asked-questions/
weight: 8
---

## Frequently Asked Questions

### Can Aspose.Note save notes to formats other than PDF?

No, Aspose.Note only supports saving to PDF. Other formats such as HTML, images (PNG/JPEG), or the native .one format are declared for API compatibility but not implemented. Attempting to save to these formats will not produce valid output. Use `SaveFormat.Pdf` exclusively when calling `Document.Save()`.

### Can Aspose.Note write new .one files?

No, Aspose.Note does not support writing back to the native .one file format. The library is designed for reading existing .one files and building an in-memory document object model (DOM). While you can modify the DOM and save the result as PDF, persisting changes to a .one file is not implemented. This limitation applies to all write operations targeting the .one format.

### How do I convert a OneNote file to PDF using Python?

Load the .one file into a `Document` object and call `Save()` with `SaveFormat.Pdf`. This is the only supported export path. The following example reads a file and writes a PDF output.

```python
from aspose.note import Document, SaveFormat

doc = Document("input.one")
doc.Save("output.pdf", SaveFormat.Pdf)
```

### What happens if I try to load an encrypted .one file?

Loading an encrypted .one file raises `IncorrectPasswordException`. Aspose.Note does not support password-protected or encrypted documents at all. The DocumentPassword property is not implemented, and no API exists to supply a password. You must decrypt the file externally before loading it.

### Can I use Aspose.Note to process OneNote Online files?

Yes, Aspose.Note can read files saved in OneNote Online formats, as indicated by the `FileFormat.OneNoteOnline` enum value. However, the same limitations apply: only PDF export is supported, and the library cannot write back to .one or OneNote Online formats. Ensure the input file is accessible and not encrypted.

## See Also

Aspose.Note for Python is designed primarily for reading and processing OneNote (.one) files. The library builds an in-memory DOM from .one files but does not support saving changes back to the .one format. For output, only PDF saving is fully implemented; other formats like HTML, images, or .one are declared for compatibility but not implemented. This limitation is important when planning workflows that require round-trip editing of OneNote documents.

- [Troubleshooting common issues](/kb.aspose.org/note/python/error-troubleshooting/)
- [Convert file formats step-by-step](/kb.aspose.org/note/python/how-to-convert-pdf-to-tiff-python/)
- [Fix common errors effectively](/kb.aspose.org/note/python/fix-notebooks-errors/)
- [Load files correctly and quickly](/kb.aspose.org/note/python/load-notebooks/)
- [Optimize performance tips](/kb.aspose.org/note/python/optimize-notebooks/)
