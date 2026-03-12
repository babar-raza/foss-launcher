---
page_role: howto_article
linkTitle: "Page"
title: "Page — Aspose.Note FOSS for Python API Reference"
description: "API reference for the Page class in aspose-note v26.2. Represents a OneNote page within a Document, including title, author, timestamps, and level."
categories:
  - Class
layout: "reference"
---

## Class: Page

**Package**: `aspose.note`
**Import**: `from aspose.note import Page`
**Inherits**: `CompositeNode`

`Page` represents a single OneNote page within a `Document`. Pages are the direct children of `Document`. Each page can contain `Outline` nodes (which in turn contain `OutlineElement` and content nodes).

---

## Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `Title` | `Title \| None` | Read | The page title block; `None` if the page has no title |
| `Author` | `str \| None` | Read | Author string stored in the file metadata |
| `CreationTime` | `datetime \| None` | Read | Page creation timestamp |
| `LastModifiedTime` | `datetime \| None` | Read | Last modification timestamp |
| `Level` | `int \| None` | Read | Sub-page indent level; `0` is top-level, `1` is first indent, etc. |

### Inherited from CompositeNode

| Property / Method | Description |
|---|---|
| `FirstChild` | First direct child node |
| `LastChild` | Last direct child node |
| `GetChildNodes(Type)` | Recursive type-filtered search |
| `for child in page` | Iterate direct children (Outlines) |

### Inherited from Node

| Property | Description |
|---|---|
| `ParentNode` | The parent `Document` |
| `Document` | The root `Document` |

---

## Methods

### Clone(deep=False)

```python
page.Clone(deep: bool = False) -> Page
```

Returns a copy of the page. `deep=False` creates a shallow clone with no children.

---

### Accept(visitor)

```python
page.Accept(visitor: DocumentVisitor) -> None
```

Dispatches `VisitPageStart(page)` on the visitor, then recursively visits child nodes, then `VisitPageEnd(page)`.

---

## Usage Examples

### Iterate all pages

```python
from aspose.note import Document, Page

doc = Document("MyNotes.one")
for page in doc.GetChildNodes(Page):
    title = (
        page.Title.TitleText.Text
        if page.Title and page.Title.TitleText
        else "(untitled)"
    )
    print(f"  {title}  author={page.Author}  level={page.Level}")
```

### Check for sub-pages

Sub-pages have `Level > 0`:

```python
from aspose.note import Document, Page

doc = Document("MyNotes.one")
for page in doc.GetChildNodes(Page):
    if page.Level and page.Level > 0:
        title = page.Title.TitleText.Text if page.Title and page.Title.TitleText else ""
        print(f"Sub-page (level={page.Level}): {title!r}")
```

### Access the full title block

The `Title` node contains three optional `RichText` children:

```python
from aspose.note import Document, Page

doc = Document("MyNotes.one")
for page in doc.GetChildNodes(Page):
    if page.Title:
        if page.Title.TitleText:
            print("Text:", page.Title.TitleText.Text)
        if page.Title.TitleDate:
            print("Date:", page.Title.TitleDate.Text)
        if page.Title.TitleTime:
            print("Time:", page.Title.TitleTime.Text)
```

### Extract all content from a single page

```python
from aspose.note import Document, Page, RichText, Image, Table, AttachedFile

doc = Document("MyNotes.one")
page = doc.GetChildNodes(Page)[0]  # first page

print(f"RichText: {len(page.GetChildNodes(RichText))}")
print(f"Images:   {len(page.GetChildNodes(Image))}")
print(f"Tables:   {len(page.GetChildNodes(Table))}")
print(f"Files:    {len(page.GetChildNodes(AttachedFile))}")
```

### Timestamps

```python
from aspose.note import Document, Page

doc = Document("MyNotes.one")
for page in doc.GetChildNodes(Page):
    print(f"Created:  {page.CreationTime}")
    print(f"Modified: {page.LastModifiedTime}")
```

---

## None-Safety

`Title`, `Author`, `CreationTime`, `LastModifiedTime`, and `Level` can all be `None`. Always guard:

```python
title_text = (
    page.Title.TitleText.Text
    if page.Title and page.Title.TitleText
    else ""
)
```

---

## See Also

- [Document](document/) — parent of Page
- [Title](/reference.aspose.org/note/python/#title) — title node
- [Outline](/reference.aspose.org/note/python/#outline) — outline container
- [RichText](richtext/) — text content
- [Text Extraction Developer Guide](https://docs.aspose.org/note/python/developer-guide/text-extraction/)
- [How-to: Extract Text per Page (KB)](https://kb.aspose.org/note/python/how-to-extract-text-onenote-python/)
