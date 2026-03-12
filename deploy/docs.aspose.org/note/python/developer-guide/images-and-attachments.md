---
page_role: howto_article
description: >-
  Extract embedded images and attached files from Microsoft OneNote .one files
  in Python using Aspose.Note FOSS. Covers Image, AttachedFile, bytes, metadata, and disk saving.
title: Images and Attached Files — Aspose.Note FOSS for Python
type: docs
weight: 30
---

Aspose.Note FOSS for Python gives direct access to both embedded images and attached files stored inside OneNote `.one` section files. Content is exposed through the `Image` and `AttachedFile` node types.

---

## Extracting Images

Every image in a OneNote document is represented by an `Image` node. Use `GetChildNodes(Image)` to retrieve all images from the document recursively:

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
for i, img in enumerate(doc.GetChildNodes(Image), start=1):
    filename = img.FileName or f"image_{i}.bin"
    with open(filename, "wb") as f:
        f.write(img.Bytes)
    print(f"Saved: {filename}  ({img.Width} x {img.Height} pts)")
```

### Image Properties

| Property | Type | Description |
|---|---|---|
| `FileName` | `str \| None` | Original filename stored in the OneNote file (may be `None`) |
| `Bytes` | `bytes` | Raw image data (format matches the original, e.g. PNG, JPEG) |
| `Width` | `float \| None` | Rendered width in points |
| `Height` | `float \| None` | Rendered height in points |
| `AlternativeTextTitle` | `str \| None` | Alt text title for accessibility |
| `AlternativeTextDescription` | `str \| None` | Alt text description |
| `HyperlinkUrl` | `str \| None` | URL if the image is a clickable hyperlink |
| `Tags` | `list[NoteTag]` | OneNote tags attached to this image |

### Save Images with Safe Filenames

When `FileName` is `None` or contains characters unsafe for the filesystem, sanitize before saving:

```python
import re
from aspose.note import Document, Image

def safe_name(name: str | None, fallback: str) -> str:
    if not name:
        return fallback
    return re.sub(r'[<>:"/\\|?*]', "_", name)

doc = Document("MyNotes.one")
for i, img in enumerate(doc.GetChildNodes(Image), start=1):
    name = safe_name(img.FileName, f"image_{i}.bin")
    with open(name, "wb") as f:
        f.write(img.Bytes)
```

### Extract Images Per Page

```python
from aspose.note import Document, Page, Image

doc = Document("MyNotes.one")
for page_num, page in enumerate(doc.GetChildNodes(Page), start=1):
    images = page.GetChildNodes(Image)
    print(f"Page {page_num}: {len(images)} image(s)")
    for i, img in enumerate(images, start=1):
        filename = f"page{page_num}_img{i}.bin"
        with open(filename, "wb") as f:
            f.write(img.Bytes)
```

### Inspect Image Alt Text and Hyperlinks

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
for img in doc.GetChildNodes(Image):
    if img.AlternativeTextTitle:
        print("Alt title:", img.AlternativeTextTitle)
    if img.AlternativeTextDescription:
        print("Alt desc:", img.AlternativeTextDescription)
    if img.HyperlinkUrl:
        print("Linked to:", img.HyperlinkUrl)
```

### Detect Image File Format from Bytes

Python's `imghdr` module (Python ≤ 3.12) or the `struct` module can detect image format from the first bytes:

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
    elif b[:2] in (b'BM',):
        fmt = "bmp"
    else:
        fmt = "bin"
    name = (img.FileName or f"image.{fmt}").rsplit(".", 1)[0] + f".{fmt}"
    with open(name, "wb") as f:
        f.write(b)
```

---

## Extracting Attached Files

Embedded file attachments are stored as `AttachedFile` nodes:

```python
from aspose.note import Document, AttachedFile

doc = Document("NotesWithAttachments.one")
for i, af in enumerate(doc.GetChildNodes(AttachedFile), start=1):
    filename = af.FileName or f"attachment_{i}.bin"
    with open(filename, "wb") as f:
        f.write(af.Bytes)
    print(f"Saved attachment: {filename}  ({len(af.Bytes):,} bytes)")
```

### AttachedFile Properties

| Property | Type | Description |
|---|---|---|
| `FileName` | `str \| None` | Original filename stored in the OneNote file |
| `Bytes` | `bytes` | Raw file content |
| `Tags` | `list[NoteTag]` | OneNote tags attached to this node |

---

## Inspect Tags on Images and Attachments

Both `Image` and `AttachedFile` nodes support OneNote tags:

```python
from aspose.note import Document, Image, AttachedFile

doc = Document("MyNotes.one")

for img in doc.GetChildNodes(Image):
    for tag in img.Tags:
        print(f"Image tag: {tag.label}  completed={tag.completed}")

for af in doc.GetChildNodes(AttachedFile):
    for tag in af.Tags:
        print(f"Attachment tag: {tag.label}  completed={tag.completed}")
```

---

## Summary: Image vs AttachedFile

| Feature | `Image` | `AttachedFile` |
|---|---|---|
| `FileName` | Yes (original image name) | Yes (original file name) |
| `Bytes` | Raw image bytes | Raw file bytes |
| `Width` / `Height` | Yes (rendered dimensions) | No |
| `AlternativeTextTitle/Description` | Yes | No |
| `HyperlinkUrl` | Yes | No |
| `Tags` | Yes | Yes |
| `Replace(node)` method | Yes | No |

---

## Tips

- Always guard against `None` filenames — `img.FileName` is `None` when the file had no name in the source document.
- `img.Bytes` is never `None` and is always the raw binary content; it can be zero bytes for placeholder images.
- Use `Page.GetChildNodes(Image)` instead of `Document.GetChildNodes(Image)` to scope extraction to a single page.
- The `Image.Replace(image)` method replaces the content of one image node with another in-memory; saving back to `.one` is not supported.

---

## See Also

- [API Reference — Image](https://reference.aspose.org/note/python/image/)
- [How-to: Traverse the DOM (KB)](https://kb.aspose.org/note/python/how-to-traverse-onenote-dom-python/)
- [Developer Guide — Tables](tables/)
