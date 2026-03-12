---
page_role: howto_article
linkTitle: "Document"
title: "Document — Aspose.Note FOSS for Python API Reference"
description: "API reference for the Document class in aspose-note v26.2. The root entry point for loading and working with Microsoft OneNote .one section files."
categories:
  - Class
layout: "reference"
---

## Class: Document

**Package**: `aspose.note`
**Import**: `from aspose.note import Document`
**Inherits**: `CompositeNode`

`Document` is the root node of the OneNote document object model. It represents a single OneNote section file (`.one`). All pages are direct children of `Document`.

---

## Constructor

```python
Document(source=None, load_options=None)
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `source` | `str \| Path \| BinaryIO \| None` | No | File path string, `pathlib.Path`, binary stream (file handle, `io.BytesIO`, etc.), or `None` for an empty document |
| `load_options` | `LoadOptions \| None` | No | Optional load-time configuration |

### Examples

```python
from aspose.note import Document

##Load from a file path
doc = Document("MyNotes.one")

##Load from a binary stream
with open("MyNotes.one", "rb") as f:
    doc = Document(f)

##Empty document (no source file)
doc = Document()
```

### Exceptions raised by constructor

| Exception | Condition |
|---|---|
| `FileCorruptedException` | The file cannot be parsed |
| `IncorrectDocumentStructureException` | The file structure is unsupported |
| `IncorrectPasswordException` | The file is encrypted (encryption not supported) |
| `UnsupportedFileFormatException` | The file format is not recognized |

---

## Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `DisplayName` | `str \| None` | Read | The display name of the section as stored in the file metadata |
| `CreationTime` | `datetime \| None` | Read | Section creation timestamp |
| `FileFormat` | `FileFormat` | Read | **Always returns `FileFormat.OneNote2010`** — hardcoded constant in v26.2, not detected from the file |

### Inherited from CompositeNode

| Property | Type | Description |
|---|---|---|
| `FirstChild` | `Node \| None` | First direct child (first page) |
| `LastChild` | `Node \| None` | Last direct child (last page) |

### Inherited from Node

| Property | Type | Description |
|---|---|---|
| `ParentNode` | `Node \| None` | Always `None` for Document (it is the root) |
| `Document` | `Document \| None` | Returns `self` (Document is its own root; never `None` for a live Document instance) |

---

## Methods

### Count()

```python
doc.Count() -> int
```

Returns the number of direct child `Page` nodes (i.e., the number of pages in the section).

```python
from aspose.note import Document

doc = Document("MyNotes.one")
print(f"Pages: {doc.Count()}")
```

---

### Save(target, format_or_options)

```python
doc.Save(target: str | Path | BinaryIO, format_or_options: SaveFormat | SaveOptions | None = None) -> None
```

Saves the document to a file path, `pathlib.Path`, or a binary stream. Only `SaveFormat.Pdf` is currently implemented.

| Parameter | Type | Description |
|---|---|---|
| `target` | `str \| Path \| BinaryIO` | Output file path or writable binary stream |
| `format_or_options` | `SaveFormat \| SaveOptions \| None` | Target format or options object |

**Exceptions**:
- `UnsupportedSaveFormatException` — raised for any `SaveFormat` other than `Pdf`

> **Note on `PdfSaveOptions.PageIndex` / `PageCount`**: These fields exist on the dataclass but are **not forwarded to the PDF exporter in v26.2** and have no effect. The full document is always exported.

```python
import io
from aspose.note import Document, SaveFormat, PdfSaveOptions

doc = Document("MyNotes.one")

##Save to file path (string)
doc.Save("output.pdf", SaveFormat.Pdf)

##Save to a pathlib.Path
from pathlib import Path
doc.Save(Path("output.pdf"), SaveFormat.Pdf)

##Save to an in-memory stream
buf = io.BytesIO()
doc.Save(buf, PdfSaveOptions(SaveFormat.Pdf))
pdf_bytes = buf.getvalue()
```

---

### Accept(visitor)

```python
doc.Accept(visitor: DocumentVisitor) -> None
```

Dispatches the visitor to traverse the entire document tree. Calls `visitor.VisitDocumentStart(self)`, then recursively visits all child nodes.

```python
from aspose.note import Document, DocumentVisitor

class MyVisitor(DocumentVisitor):
    def VisitDocumentStart(self, doc):
        print(f"Document: {doc.DisplayName}")

doc = Document("MyNotes.one")
doc.Accept(MyVisitor())
```

---

### GetPageHistory(page)

```python
doc.GetPageHistory(page: Page) -> list[Page]
```

Returns the version history of a page. In v26.2, this is a compatibility stub that returns `[page]`.

---

### DetectLayoutChanges()

```python
doc.DetectLayoutChanges() -> None
```

Compatibility stub. No operation.

---

### Iteration

```python
for page in doc:
    ...
```

Iterates the direct child `Page` nodes in document order.

---

## Complete Example

```python
from aspose.note import Document, Page, RichText, SaveFormat

doc = Document("MyNotes.one")

print(f"Section: {doc.DisplayName}")
print(f"Format:  {doc.FileFormat}")
print(f"Created: {doc.CreationTime}")
print(f"Pages:   {doc.Count()}")

for page in doc:
    title = page.Title.TitleText.Text if page.Title and page.Title.TitleText else "(untitled)"
    texts = page.GetChildNodes(RichText)
    print(f"  [{title}]  {len(texts)} text node(s)")

doc.Save("output.pdf", SaveFormat.Pdf)
print("Saved output.pdf")
```

---

## See Also

- [Page](page/) — direct child of Document
- [LoadOptions](/reference.aspose.org/note/python/#loadoptions) — constructor options
- [PdfSaveOptions](/reference.aspose.org/note/python/#pdfsaveoptions) — PDF export configuration
- [DocumentVisitor](/reference.aspose.org/note/python/#documentvisitor) — visitor-pattern traversal
- [PDF Export Developer Guide](https://docs.aspose.org/note/python/developer-guide/pdf-export/)
- [How-to: Export OneNote to PDF (KB)](https://kb.aspose.org/note/python/how-to-export-onenote-pdf-python/)
