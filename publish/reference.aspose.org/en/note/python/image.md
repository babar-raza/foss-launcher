---
page_role: howto_article
linkTitle: "Image"
title: "Image — Aspose.Note FOSS for Python API Reference"
description: "API reference for the Image class in aspose-note v26.2. Represents an embedded image in a OneNote document with raw bytes, filename, dimensions, and tags."
categories:
  - Class
layout: "reference"
---

## Class: Image

**Package**: `aspose.note`
**Import**: `from aspose.note import Image`
**Inherits**: `CompositeNode`

`Image` represents an embedded image stored inside a OneNote `.one` file. It exposes the raw image bytes, the original filename, rendered dimensions, alt text, a hyperlink URL (if any), and any OneNote tags attached to the image.

---

## Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `FileName` | `str \| None` | Read | Original filename as stored in the OneNote file; `None` if not present |
| `Bytes` | `bytes` | Read | Raw image data (PNG, JPEG, or other binary format depending on source) |
| `Width` | `float \| None` | Read | Rendered width in points |
| `Height` | `float \| None` | Read | Rendered height in points |
| `AlternativeTextTitle` | `str \| None` | Read | Accessibility alt text title — **always `None` for files parsed in v26.2**; the parser does not populate this field |
| `AlternativeTextDescription` | `str \| None` | Read | Accessibility alt text description |
| `HyperlinkUrl` | `str \| None` | Read | URL if the image is a clickable link |
| `Tags` | `list[NoteTag]` | Read | OneNote tags attached to this image |

### Inherited from CompositeNode / Node

| Property | Description |
|---|---|
| `ParentNode` | Containing node (OutlineElement, TableCell) |
| `Document` | Root Document |

---

## Methods

### Replace(image)

```python
img.Replace(image: Image) -> None
```

Replaces the content of this `Image` node with the content of another `Image` node, in-memory. Saving back to `.one` is not supported.

---

### Accept(visitor)

```python
img.Accept(visitor: DocumentVisitor) -> None
```

Dispatches `VisitImageStart(img)` and `VisitImageEnd(img)` on the visitor.

---

## Usage Examples

### Save all images to disk

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
for i, img in enumerate(doc.GetChildNodes(Image), start=1):
    filename = img.FileName or f"image_{i}.bin"
    with open(filename, "wb") as f:
        f.write(img.Bytes)
    print(f"Saved: {filename}  ({img.Width} x {img.Height} pts)")
```

### Detect image format from bytes

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
for img in doc.GetChildNodes(Image):
    b = img.Bytes
    if b[:4] == b'\x89PNG':
        fmt = "png"
    elif b[:2] == b'\xff\xd8':
        fmt = "jpeg"
    elif b[:4] == b'GIF8':
        fmt = "gif"
    else:
        fmt = "bin"
    print(f"  {img.FileName!r} detected as {fmt}")
```

### Find all linked images

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
for img in doc.GetChildNodes(Image):
    if img.HyperlinkUrl:
        print(f"  Linked image: {img.FileName!r} -> {img.HyperlinkUrl}")
```

### Read alt text

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
for img in doc.GetChildNodes(Image):
    if img.AlternativeTextTitle or img.AlternativeTextDescription:
        print(f"  Alt title: {img.AlternativeTextTitle!r}")
        print(f"  Alt desc:  {img.AlternativeTextDescription!r}")
```

### Inspect tags on images

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
for img in doc.GetChildNodes(Image):
    for tag in img.Tags:
        print(f"  Image tag: label={tag.label!r}  completed={tag.completed}")
```

### Images per page

```python
from aspose.note import Document, Page, Image

doc = Document("MyNotes.one")
for page_num, page in enumerate(doc.GetChildNodes(Page), start=1):
    images = page.GetChildNodes(Image)
    print(f"Page {page_num}: {len(images)} image(s)")
```

---

## None-Safety

- `FileName` is `None` when no filename was stored — always provide a fallback when writing to disk.
- `Bytes` is always a `bytes` object and is never `None`.
- `Width` and `Height` are `None` for images with no dimension metadata.
- `AlternativeTextTitle`, `AlternativeTextDescription`, and `HyperlinkUrl` are `None` when not set.

---

## See Also

- [AttachedFile](/reference.aspose.org/note/python/#attachedfile) — embedded file attachments
- [NoteTag](/reference.aspose.org/note/python/#notetag) — tags on images
- [Page](page/) — ancestor of Image
- [Images and Attached Files Developer Guide](https://docs.aspose.org/note/python/developer-guide/images-and-attachments/)
- [How-to: Traverse the DOM (KB)](https://kb.aspose.org/note/python/how-to-traverse-onenote-dom-python/)
