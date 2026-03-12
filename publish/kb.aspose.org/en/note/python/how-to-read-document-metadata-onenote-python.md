---
page_role: howto_article
title: "How to Read Document and Page Metadata from OneNote in Python"
description: "Read section name, page author, creation time, modification time, and page level from OneNote .one files using Aspose.Note FOSS for Python."
canonical: https://kb.aspose.org/note/python/how-to-read-document-metadata-onenote-python/
url: /kb.aspose.org/note/python/how-to-read-document-metadata-onenote-python/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Note FOSS
family: note
platform: python
canonical_import: aspose_note
robots: index, follow
seoTitle: "How to Read OneNote Metadata in Python — Section Name, Author, Timestamps"
keywords:
  - onenote document metadata python
  - read onenote page author python
  - aspose note page creation time python
  - python onenote display name
  - read onenote timestamps python
type: howto_article
draft: false
weight: 80
---

OneNote `.one` files store metadata at two levels: the **document** (section) level holds the section name; the **page** level holds the author, creation timestamp, last-modified timestamp, and page hierarchy level. Aspose.Note FOSS for Python exposes all of these through the `Document` and `Page` classes.

---

## Prerequisites

```bash
pip install aspose-note
```

---

## Document-Level Metadata

The `Document` object exposes one metadata field:

| Property | Type | Description |
|---|---|---|
| `doc.DisplayName` | `str \| None` | The OneNote section display name stored in the file's metadata. `None` if not present. |

```python
from aspose.note import Document

doc = Document("MyNotes.one")
print(f"Section name: {doc.DisplayName or '(none)'}")
```

> **`doc.CreationTime`** is declared as a property but always returns `None` in version 26.2 — the field is parsed but not yet surfaced at the `Document` level.

---

## Page-Level Metadata

Each `Page` object carries:

| Property | Type | Description |
|---|---|---|
| `page.Author` | `str \| None` | The display name of the user who created or owns the page. |
| `page.CreationTime` | `datetime \| None` | When the page was created. Returns a Python `datetime` object in UTC. |
| `page.LastModifiedTime` | `datetime \| None` | When the page was last modified. |
| `page.Level` | `int \| None` | Sub-page indent level. `0` = top-level page, `1` = first-level sub-page, `2` = second-level, etc. |

---

## Step 1 — Read Section Name

```python
from aspose.note import Document

doc = Document("ProjectNotes.one")
name = doc.DisplayName
print(f"Section: {name or '(not stored)'}")
```

---

## Step 2 — Read Metadata for Every Page

```python
from aspose.note import Document, Page

doc = Document("ProjectNotes.one")

for i, page in enumerate(doc, start=1):
    title = ""
    if page.Title and page.Title.TitleText:
        title = page.Title.TitleText.Text.strip()

    level = page.Level or 0
    indent = "  " * level

    author = page.Author or "(unknown)"
    created = page.CreationTime.strftime("%Y-%m-%d") if page.CreationTime else "(none)"
    modified = page.LastModifiedTime.strftime("%Y-%m-%d %H:%M") if page.LastModifiedTime else "(none)"

    print(f"{indent}[{i}] {title or '(untitled)'}")
    print(f"{indent}    Author:   {author}")
    print(f"{indent}    Created:  {created}")
    print(f"{indent}    Modified: {modified}")
    print(f"{indent}    Level:    {level}")
```

---

## Complete Example — Metadata Report

```python
from aspose.note import Document

def print_metadata_report(one_path: str) -> None:
    doc = Document(one_path)

    print(f"Section:    {doc.DisplayName or '(not stored)'}")
    print(f"Page count: {doc.Count()}")
    print()

    for i, page in enumerate(doc, start=1):
        title = ""
        if page.Title and page.Title.TitleText:
            title = page.Title.TitleText.Text.strip()

        level = page.Level or 0
        prefix = "  " * level + f"[{i}]"

        parts = [prefix, f'"{title or "(untitled)"}"']
        if page.Author:
            parts.append(f"by {page.Author}")
        if page.CreationTime:
            parts.append(f"created {page.CreationTime.strftime('%Y-%m-%d')}")
        if page.LastModifiedTime:
            parts.append(f"modified {page.LastModifiedTime.strftime('%Y-%m-%d')}")

        print("  ".join(parts))

print_metadata_report("ProjectNotes.one")
```

---

## Detecting Sub-Pages

In OneNote, sub-pages are visually indented under their parent page. The `page.Level` property reflects this nesting:

```python
from aspose.note import Document

doc = Document("MyNotes.one")

for page in doc:
    level = page.Level or 0
    title = ""
    if page.Title and page.Title.TitleText:
        title = page.Title.TitleText.Text.strip()

    indent = "  " * level
    marker = "├─" if level > 0 else "•"
    print(f"{indent}{marker} {title or '(untitled)'}")
```

Level values:
- `0` — top-level page
- `1` — first-level sub-page (one indent)
- `2` — second-level sub-page (two indents)

---

## Notes

- All timestamps (`CreationTime`, `LastModifiedTime`) are `datetime` objects in UTC when present.
- `page.Level` returns `None` for pages where the level was not stored in the binary format. Treat `None` as `0` using `page.Level or 0`.
- `doc.DisplayName` reads the section name from the OneNote file's metadata block — it is the section tab name visible in the OneNote sidebar, not a filename.

---

## See Also

- [How to Traverse the OneNote DOM in Python](/kb.aspose.org/note/python/how-to-traverse-dom-onenote-python/)
- [How to Extract Text from OneNote in Python](/kb.aspose.org/note/python/how-to-extract-text-from-onenote-python/)
- [Document API Reference](/reference.aspose.org/note/python/document/)
- [Page API Reference](/reference.aspose.org/note/python/page/)
- [Getting Started](/docs.aspose.org/note/python/getting-started/)
