---
page_role: howto_article
layout: "family"
type: "_default"

head_title: "Aspose.Note FOSS for Python | Free OneNote File Reader API"
head_description: "Read, traverse, and export Microsoft OneNote .one files in Python. 100% free, open-source, MIT-licensed. Supports text extraction, image export, table parsing, and PDF generation."

title: "Aspose.Note FOSS for Python"
description: "A free, open-source Python library for reading Microsoft OneNote (.one) files. Extract text, images, tables, and attachments. Export to PDF. No Microsoft Office required."
button:
  enable: true

overview:
  enable: true
  content: |
    Aspose.Note FOSS for Python is a 100% free, MIT-licensed library that lets you read Microsoft OneNote (.one) files entirely from Python—no Microsoft Office, no COM automation, no proprietary runtime required. It exposes a clean, Aspose.Note-shaped public API (`aspose.note.*`) modeled on the familiar Aspose.Note for .NET interface, backed by a built-in MS-ONE/OneStore binary parser written in pure Python.

    Install from PyPI with `pip install aspose-note` (or `pip install "aspose-note[pdf]"` to enable PDF export). Requires Python 3.10 or later.

    The library is suitable for document automation scripts, content indexing pipelines, archival tools, and any server-side workflow that needs to consume OneNote content without a Microsoft Office dependency.

features:
  enable: true
  title: "What You Can Do"
  items:
    - title: "Read .one Files"
      content: "Load any Microsoft OneNote section file (.one) from a file path or a binary stream using the Document class. Supports OneNote 2010, OneNote Online, and OneNote 2007 format variants."
    - title: "Traverse the Document DOM"
      content: "Navigate the full OneNote document object model: Document → Page → Outline → OutlineElement → RichText / Image / Table / AttachedFile. Use GetChildNodes(Type) for recursive type-based search or DocumentVisitor for full-document traversal."
    - title: "Extract Rich Text"
      content: "Read raw text via RichText.Text or inspect individual TextRun segments for bold, italic, underline, font, color, hyperlink, and language metadata. Use RichText.Replace() to substitute text in-memory."
    - title: "Export Images and Attachments"
      content: "Iterate Image nodes to retrieve raw bytes, filename, dimensions, and alt text. Iterate AttachedFile nodes to save embedded file attachments to disk."
    - title: "Parse Tables"
      content: "Traverse Table → TableRow → TableCell hierarchies. Read column widths, border visibility, and cell content composed of RichText nodes."
    - title: "Inspect Tags and Lists"
      content: "Read NoteTag metadata (shape, label, color, completion state) on RichText, Image, and Table nodes. Inspect NumberList on OutlineElement for indentation level and list format."
    - title: "Export to PDF"
      content: "Save any loaded Document to PDF using Document.Save(path, SaveFormat.Pdf). Customize output with PdfSaveOptions: page range, tag icon directory, tag icon size, and gap. Requires the optional ReportLab dependency (pip install \"aspose-note[pdf]\")."
    - title: "Stream-Based Loading"
      content: "Open .one files directly from a binary stream (e.g. io.BytesIO or an HTTP response body) without writing to disk first. Useful for cloud storage and web service integrations."

code_samples:
  enable: true
  title: "Quick Start Examples"
  items:
    - title: "Load and iterate pages"
      content: |
        ```python
        from aspose.note import Document

        doc = Document("notebook.one")
        print(doc.DisplayName)   # Section display name
        print(doc.Count())       # Number of pages

        for page in doc:
            title = page.Title.TitleText.Text if page.Title and page.Title.TitleText else "(untitled)"
            print(title)
        ```
    - title: "Extract all text"
      content: |
        ```python
        from aspose.note import Document, RichText

        doc = Document("notebook.one")
        texts = [rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text]
        print("\n".join(texts))
        ```
    - title: "Export to PDF"
      content: |
        ```python
        from aspose.note import Document, SaveFormat

        doc = Document("notebook.one")
        doc.Save("output.pdf", SaveFormat.Pdf)
        ```

support:
  enable: true

back_to_top:
  enable: true
---

---

## Explore the Documentation

- [Getting Started](https://docs.aspose.org/note/python/getting-started/) — install and run your first script
- [Developer Guide](https://docs.aspose.org/note/python/developer-guide/) — feature-by-feature guides
- [API Reference](https://reference.aspose.org/note/python/) — complete class and method reference
- [Knowledge Base](https://kb.aspose.org/note/python/) — how-to articles and recipes
- [Blog](https://blog.aspose.org/note/python/) — release announcements and tutorials
