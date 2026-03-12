---
page_role: howto_article
title: "How to Traverse the OneNote Document DOM in Python"
description: "Learn how to walk the full Aspose.Note document object model in Python using GetChildNodes, iteration, and the DocumentVisitor pattern."
date: 2026-03-10
lastmod: 2026-03-10
weight: 50
slug: "how-to-traverse-onenote-dom-python"
draft: false
type: "topic"
keywords:
  - "onenote dom python"
  - "traverse onenote document python"
  - "aspose note document visitor python"
  - "onenote tree traversal python"
  - "GetChildNodes python onenote"
step1: "Install aspose-note from PyPI"
step2: "Load the .one file with Document"
step3: "Use GetChildNodes(Type) for recursive type-filtered search"
step4: "Iterate direct children with for child in node"
step5: "Implement DocumentVisitor for full-tree traversal"
step6: "Navigate using ParentNode and Document properties"
---

Aspose.Note FOSS for Python represents a OneNote section file as a tree of typed Python objects. Understanding how to traverse this tree efficiently is the foundation for all content extraction tasks. This guide covers all three traversal approaches: `GetChildNodes`, direct iteration, and `DocumentVisitor`.

---

## The Document Object Model

The OneNote DOM is a strict tree:

```
Document
  ├── Page
  │     ├── Title
  │     │     ├── TitleText (RichText)
  │     │     ├── TitleDate (RichText)
  │     │     └── TitleTime (RichText)
  │     └── Outline
  │           └── OutlineElement
  │                 ├── RichText
  │                 ├── Image
  │                 ├── AttachedFile
  │                 └── Table
  │                       └── TableRow
  │                             └── TableCell
  │                                   └── RichText / Image
  └── Page  (next page ...)
```

Every node inherits from `Node`. Nodes that have children inherit from `CompositeNode`.

---

## Method 1: GetChildNodes (Recursive, Type-Filtered)

`CompositeNode.GetChildNodes(Type)` performs a recursive depth-first search of the entire subtree and returns a flat list of all nodes matching the given type. This is the most convenient approach for content extraction:

```python
from aspose.note import Document, RichText, Image, Table, AttachedFile

doc = Document("MyNotes.one")

##All RichText nodes anywhere in the document
texts = doc.GetChildNodes(RichText)
print(f"RichText nodes: {len(texts)}")

##All images
images = doc.GetChildNodes(Image)
print(f"Image nodes: {len(images)}")

##All tables
tables = doc.GetChildNodes(Table)
print(f"Table nodes: {len(tables)}")

##All attachments
attachments = doc.GetChildNodes(AttachedFile)
print(f"AttachedFile nodes: {len(attachments)}")
```

Scope the search to a single page by calling `GetChildNodes` on `Page` instead of `Document`:

```python
from aspose.note import Document, Page, RichText

doc = Document("MyNotes.one")
for page in doc.GetChildNodes(Page):
    page_texts = page.GetChildNodes(RichText)
    print(f"  Page has {len(page_texts)} text nodes")
```

---

## Method 2: Direct Child Iteration

`for child in node` iterates the **immediate** children of a `CompositeNode`. Use this when you need one specific level of the hierarchy:

```python
from aspose.note import Document

doc = Document("MyNotes.one")

##Direct children of Document are Pages
for page in doc:
    title = (
        page.Title.TitleText.Text
        if page.Title and page.Title.TitleText
        else "(untitled)"
    )
    print(f"Page: {title}")
    # Direct children of Page are Outlines (and optionally Title)
    for child in page:
        print(f"  {type(child).__name__}")
```

---

## Method 3: DocumentVisitor

`DocumentVisitor` provides a visitor pattern for structured traversal. Override only the `VisitXxxStart/End` methods you need. The visitor is dispatched by calling `doc.Accept(visitor)`:

```python
from aspose.note import (
    Document, DocumentVisitor, Page, Title,
    Outline, OutlineElement, RichText, Image,
)

class StructurePrinter(DocumentVisitor):
    def __init__(self):
        self._depth = 0

    def _indent(self):
        return "  " * self._depth

    def VisitPageStart(self, page: Page) -> None:
        t = page.Title.TitleText.Text if page.Title and page.Title.TitleText else "(untitled)"
        print(f"{self._indent()}Page: {t!r}")
        self._depth += 1

    def VisitPageEnd(self, page: Page) -> None:
        self._depth -= 1

    def VisitOutlineStart(self, outline) -> None:
        self._depth += 1

    def VisitOutlineEnd(self, outline) -> None:
        self._depth -= 1

    def VisitRichTextStart(self, rt: RichText) -> None:
        if rt.Text.strip():
            print(f"{self._indent()}Text: {rt.Text.strip()!r}")

    def VisitImageStart(self, img: Image) -> None:
        print(f"{self._indent()}Image: {img.FileName!r} ({img.Width}x{img.Height}pts)")

doc = Document("MyNotes.one")
doc.Accept(StructurePrinter())
```

### Available Visitor Methods

| Method pair | Node type |
|---|---|
| `VisitDocumentStart/End` | `Document` |
| `VisitPageStart/End` | `Page` |
| `VisitTitleStart/End` | `Title` |
| `VisitOutlineStart/End` | `Outline` |
| `VisitOutlineElementStart/End` | `OutlineElement` |
| `VisitRichTextStart/End` | `RichText` |
| `VisitImageStart/End` | `Image` |

---

## Navigating Up the Tree

Every node exposes `ParentNode` and a `Document` property to navigate upward:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    parent = rt.ParentNode   # OutlineElement, TableCell, Title, etc.
    root = rt.Document       # always the Document root
    print(f"  '{rt.Text.strip()!r}' parent={type(parent).__name__}")
    break
```

---

## Child Management Methods

`CompositeNode` also exposes in-memory child management (useful for programmatic document construction, though write-back to `.one` is not supported):

| Method | Description |
|---|---|
| `node.FirstChild` | First direct child or `None` |
| `node.LastChild` | Last direct child or `None` |
| `node.AppendChildLast(child)` | Add child at end |
| `node.AppendChildFirst(child)` | Add child at start |
| `node.InsertChild(index, child)` | Insert at position |
| `node.RemoveChild(child)` | Remove a child |

---

## Count Nodes With a Visitor

```python
from aspose.note import Document, DocumentVisitor, Page, RichText, Image

class Counter(DocumentVisitor):
    def __init__(self):
        self.pages = self.texts = self.images = 0

    def VisitPageStart(self, page: Page) -> None:
        self.pages += 1

    def VisitRichTextStart(self, rt: RichText) -> None:
        self.texts += 1

    def VisitImageStart(self, img: Image) -> None:
        self.images += 1

doc = Document("MyNotes.one")
c = Counter()
doc.Accept(c)
print(f"Pages={c.pages}  RichText={c.texts}  Images={c.images}")
```

---

## Choosing the Right Traversal Method

| Scenario | Best approach |
|---|---|
| Find all nodes of one type (e.g. all RichText) | `GetChildNodes(RichText)` |
| Iterate direct children only | `for child in node` |
| Walk the tree with context (depth, parent state) | `DocumentVisitor` |
| Navigate from content up to the parent or root | `node.ParentNode` / `node.Document` |

---

**Related Resources:**

- [Developer Guide](https://docs.aspose.org/note/python/developer-guide/)
- [Features Overview](https://docs.aspose.org/note/python/developer-guide/features/)
- [API Reference](https://reference.aspose.org/note/python/)
- [Blog: Introducing Aspose.Note FOSS for Python](https://blog.aspose.org/note/python/introducing-aspose-note-foss-for-python/)
