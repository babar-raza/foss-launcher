---
page_role: howto_article
title: "How to Save Attached Files from OneNote in Python"
description: "Extract and save embedded file attachments from OneNote .one files using Aspose.Note FOSS for Python. Step-by-step guide with code examples."
canonical: https://kb.aspose.org/note/python/how-to-save-attachments-onenote-python/
url: /kb.aspose.org/note/python/how-to-save-attachments-onenote-python/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Note FOSS
family: note
platform: python
canonical_import: aspose_note
robots: index, follow
seoTitle: "How to Save Attached Files from OneNote in Python — Aspose.Note FOSS"
keywords:
  - onenote extract attachments python
  - save attached files onenote python
  - aspose note attached file python
  - python onenote attachedfile bytes
  - extract embedded files onenote python
type: howto_article
draft: false
weight: 60
---

OneNote `.one` files can contain embedded file attachments — any file type that was inserted into a page using **Insert → File Attachment** in OneNote. Aspose.Note FOSS for Python exposes these through the `AttachedFile` class, which provides the original file name and the raw bytes of the embedded file.

---

## Prerequisites

```bash
pip install aspose-note
```

---

## Step 1 — Load the Document

```python
from aspose.note import Document

doc = Document("MyNotes.one")
```

---

## Step 2 — Find All Attached Files

Use `GetChildNodes(AttachedFile)` to recursively collect every attachment in the document, regardless of which page or outline it appears on:

```python
from aspose.note import Document, AttachedFile

doc = Document("MyNotes.one")
attachments = doc.GetChildNodes(AttachedFile)
print(f"Found {len(attachments)} attachment(s)")
```

---

## Step 3 — Save Each Attachment to Disk

Access `af.Bytes` for the raw file content and `af.FileName` for the original name. Always guard against a `None` filename — the library returns `None` when the filename metadata was not stored in the file:

```python
from aspose.note import Document, AttachedFile

doc = Document("MyNotes.one")

for i, af in enumerate(doc.GetChildNodes(AttachedFile), start=1):
    name = af.FileName or f"attachment_{i}.bin"
    with open(name, "wb") as f:
        f.write(af.Bytes)
    print(f"Saved: {name} ({len(af.Bytes):,} bytes)")
```

---

## Complete Example

This script extracts all attachments from a `.one` file and saves them to a dedicated output directory:

```python
from pathlib import Path
from aspose.note import Document, AttachedFile

def save_all_attachments(one_path: str, out_dir: str = "attachments") -> None:
    doc = Document(one_path)
    out = Path(out_dir)
    out.mkdir(exist_ok=True)

    attachments = doc.GetChildNodes(AttachedFile)
    if not attachments:
        print("No attachments found.")
        return

    for i, af in enumerate(attachments, start=1):
        name = af.FileName or f"attachment_{i}.bin"
        dest = out / name
        dest.write_bytes(af.Bytes)
        print(f"  [{i}] {name}  ({len(af.Bytes):,} bytes)")

    print(f"\nSaved {len(attachments)} file(s) to '{out_dir}/'")

save_all_attachments("MyNotes.one")
```

---

## Notes

- `af.Bytes` returns `b""` (empty bytes) when the attachment data could not be parsed from the binary file. Check `len(af.Bytes) > 0` before saving if you want to skip empty attachments.
- `af.Tags` is a list of `NoteTag` objects if the attachment has any OneNote tags applied to it.
- Aspose.Note FOSS for Python reads `.one` files but does not write back to `.one`. You cannot create or modify attachments.

---

## See Also

- [How to Read Image Metadata from OneNote in Python](/kb.aspose.org/note/python/how-to-read-image-metadata-onenote-python/)
- [How to Extract Text from OneNote in Python](/kb.aspose.org/note/python/how-to-extract-text-from-onenote-python/)
- [How to Traverse the OneNote DOM in Python](/kb.aspose.org/note/python/how-to-traverse-dom-onenote-python/)
- [AttachedFile API Reference](/reference.aspose.org/note/python/#attachedfile)
- [Getting Started](/docs.aspose.org/note/python/getting-started/)
