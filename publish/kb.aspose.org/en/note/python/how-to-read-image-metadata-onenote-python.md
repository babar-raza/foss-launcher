---
page_role: howto_article
title: "How to Read Image Metadata from OneNote in Python"
description: "Read image dimensions, filename, alt text, and hyperlink URL from OneNote .one files using Aspose.Note FOSS for Python. Step-by-step guide with code examples."
canonical: https://kb.aspose.org/note/python/how-to-read-image-metadata-onenote-python/
url: /kb.aspose.org/note/python/how-to-read-image-metadata-onenote-python/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Note FOSS
family: note
platform: python
canonical_import: aspose_note
robots: index, follow
seoTitle: "How to Read Image Metadata from OneNote in Python — Aspose.Note FOSS"
keywords:
  - onenote image metadata python
  - read image dimensions onenote python
  - aspose note image python
  - python onenote image alt text
  - extract image info onenote python
type: howto_article
draft: false
weight: 70
---

Every `Image` node in a OneNote document carries metadata alongside the raw pixel bytes: the original filename, display dimensions (width and height in points), alternative text for accessibility, and optionally a hyperlink URL if the image was linked. Aspose.Note FOSS for Python exposes all these fields through the `Image` class.

---

## Prerequisites

```bash
pip install aspose-note
```

---

## Image Properties

| Property | Type | Description |
|---|---|---|
| `img.Bytes` | `bytes` | Raw image data. Write to disk with `open(name, "wb").write(img.Bytes)`. |
| `img.FileName` | `str \| None` | Original filename stored in the `.one` file. `None` if not stored. |
| `img.Width` | `float \| None` | Display width in points. `None` if not stored. |
| `img.Height` | `float \| None` | Display height in points. `None` if not stored. |
| `img.AlternativeTextDescription` | `str \| None` | Accessibility alt text body. `None` if not set. |
| `img.AlternativeTextTitle` | `str \| None` | Accessibility alt text title. Always `None` in v26.2 (parser does not populate it). |
| `img.HyperlinkUrl` | `str \| None` | URL if the image is a clickable hyperlink. `None` if not linked. |
| `img.Tags` | `list[NoteTag]` | OneNote tags attached to this image (star, checkbox, etc.). |

---

## Step 1 — Load the Document and Find Images

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
images = doc.GetChildNodes(Image)
print(f"Found {len(images)} image(s)")
```

---

## Step 2 — Read Metadata for Each Image

Guard all nullable fields with `is not None` before use:

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")

for i, img in enumerate(doc.GetChildNodes(Image), start=1):
    print(f"\nImage {i}:")
    print(f"  Filename:    {img.FileName or '(no filename)'}")
    print(f"  Size:        {img.Bytes and len(img.Bytes):,} bytes")

    if img.Width is not None and img.Height is not None:
        print(f"  Dimensions:  {img.Width:.1f} × {img.Height:.1f} pts")

    if img.AlternativeTextDescription:
        print(f"  Alt text:    {img.AlternativeTextDescription}")

    if img.HyperlinkUrl:
        print(f"  Hyperlink:   {img.HyperlinkUrl}")

    if img.Tags:
        for tag in img.Tags:
            print(f"  Tag:         {tag.label or tag.shape}")
```

---

## Complete Example — Save Images with Metadata Report

```python
from pathlib import Path
from aspose.note import Document, Image

def report_and_save_images(one_path: str, out_dir: str = "images") -> None:
    doc = Document(one_path)
    images = doc.GetChildNodes(Image)
    if not images:
        print("No images found.")
        return

    out = Path(out_dir)
    out.mkdir(exist_ok=True)

    for i, img in enumerate(images, start=1):
        # Determine save name
        name = img.FileName or f"image_{i}.bin"
        dest = out / name

        # Save bytes
        dest.write_bytes(img.Bytes)

        # Report metadata
        dims = (
            f"{img.Width:.0f}×{img.Height:.0f}pts"
            if img.Width is not None and img.Height is not None
            else "unknown size"
        )
        alt = img.AlternativeTextDescription or ""
        link = img.HyperlinkUrl or ""

        print(f"  [{i}] {name}  {dims}"
              + (f"  alt='{alt}'" if alt else "")
              + (f"  url={link}" if link else ""))

    print(f"\nSaved {len(images)} image(s) to '{out_dir}/'")

report_and_save_images("MyNotes.one")
```

---

## Filter Images by Property

### Images with hyperlinks

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
linked = [img for img in doc.GetChildNodes(Image) if img.HyperlinkUrl]
for img in linked:
    print(f"{img.FileName or 'image'} → {img.HyperlinkUrl}")
```

### Images with alt text

```python
from aspose.note import Document, Image

doc = Document("MyNotes.one")
with_alt = [img for img in doc.GetChildNodes(Image) if img.AlternativeTextDescription]
for img in with_alt:
    print(f"{img.FileName}: {img.AlternativeTextDescription}")
```

---

## Notes

- `img.Bytes` is always present (returns `b""` for unreadable images, never `None`). Check `len(img.Bytes) > 0` before saving.
- `img.AlternativeTextTitle` always returns `None` in version 26.2 — the parser does not populate the title field. Use `img.AlternativeTextDescription` instead.
- Dimensions are in **points** (1 point = 1/72 inch), matching PowerPoint and PDF conventions.

---

## See Also

- [How to Save Attachments from OneNote in Python](/kb.aspose.org/note/python/how-to-save-attachments-onenote-python/)
- [How to Extract Text from OneNote in Python](/kb.aspose.org/note/python/how-to-extract-text-from-onenote-python/)
- [Image API Reference](/reference.aspose.org/note/python/image/)
- [Getting Started](/docs.aspose.org/note/python/getting-started/)
