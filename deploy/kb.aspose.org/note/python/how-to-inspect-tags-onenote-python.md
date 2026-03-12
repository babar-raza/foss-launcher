---
page_role: howto_article
title: "How to Inspect OneNote Tags in Python"
description: "Learn how to read NoteTag items from Microsoft OneNote .one files in Python using Aspose.Note FOSS. Covers tags on RichText, Image, Table, and OutlineElement nodes."
date: 2026-03-10
lastmod: 2026-03-10
weight: 40
slug: "how-to-inspect-onenote-tags-python"
draft: false
type: "topic"
keywords:
  - "onenote tags python"
  - "notetag python onenote"
  - "read onenote tags python"
  - "aspose note tags python"
  - "onenote checkbox python"
  - "inspect onenote annotations python"
step1: "Install aspose-note from PyPI"
step2: "Load the .one file with Document"
step3: "Call GetChildNodes on node types that carry tags"
step4: "Iterate the Tags list on each node"
step5: "Read tag properties (label, shape, color, completion)"
step6: "Filter or export tagged content"
---

OneNote lets users annotate content with colored tags — stars, checkboxes, important flags, and custom labels. Aspose.Note FOSS for Python exposes these annotations as `NoteTag` objects on `RichText`, `Image`, `Table`, and `OutlineElement` nodes. This guide shows how to read them.

---

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install Aspose.Note FOSS for Python

```bash
pip install aspose-note
```

---

### Step 2: Load the .one File

```python
from aspose.note import Document

doc = Document("TaggedNotes.one")
print(f"Pages: {doc.Count()}")
```

---

### Step 3: Find Tags on RichText Nodes

Most tags are attached to text blocks:

```python
from aspose.note import Document, RichText

doc = Document("TaggedNotes.one")
for rt in doc.GetChildNodes(RichText):
    for tag in rt.Tags:
        print(f"[RichText] label={tag.label!r}  shape={tag.shape}  text={rt.Text.strip()!r}")
```

---

### Step 4: Find Tags on Images

```python
from aspose.note import Document, Image

doc = Document("TaggedNotes.one")
for img in doc.GetChildNodes(Image):
    for tag in img.Tags:
        print(f"[Image] label={tag.label!r}  filename={img.FileName!r}")
```

---

### Step 5: Find Tags on Tables

```python
from aspose.note import Document, Table

doc = Document("TaggedNotes.one")
for table in doc.GetChildNodes(Table):
    for tag in table.Tags:
        print(f"[Table] label={tag.label!r}  widths={table.ColumnWidths}")
```

---

### Step 6: Find Tags on OutlineElements

```python
from aspose.note import Document, OutlineElement

doc = Document("TaggedNotes.one")
for oe in doc.GetChildNodes(OutlineElement):
    for tag in oe.Tags:
        print(f"[OutlineElement] label={tag.label!r}  completed={tag.completed}")
```

---

### Step 7: Collect All Tags Across the Document

```python
from aspose.note import Document, RichText, Image, Table, OutlineElement

doc = Document("TaggedNotes.one")
all_tags = []

for rt in doc.GetChildNodes(RichText):
    for tag in rt.Tags:
        all_tags.append({"type": "RichText", "label": tag.label,
                         "completed": tag.completed, "text": rt.Text.strip()})
for img in doc.GetChildNodes(Image):
    for tag in img.Tags:
        all_tags.append({"type": "Image", "label": tag.label,
                         "completed": tag.completed, "file": img.FileName})
for table in doc.GetChildNodes(Table):
    for tag in table.Tags:
        all_tags.append({"type": "Table", "label": tag.label,
                         "completed": tag.completed})

print(f"Total tagged items: {len(all_tags)}")
for item in all_tags:
    print(item)
```

{{% /steps %}}

---

## NoteTag Property Reference

| Property | Type | Description |
|---|---|---|
| `shape` | — | Tag shape identifier (star, checkbox, arrow, etc.) |
| `label` | `str` | Human-readable label string (e.g. `"Important"`, `"To Do"`) |
| `text_color` | `int` | Text color as ARGB integer |
| `highlight_color` | `int` | Highlight color as ARGB integer |
| `created` | `datetime` | Timestamp when the tag was applied |
| `completed` | `datetime \| None` | Timestamp when the tag was completed (`None` if not completed) |

---

## Filter Completed vs Pending Tags

Tags that have been checked off (like "To Do" checkboxes) have a non-`None` `completed` field:

```python
from aspose.note import Document, RichText

doc = Document("TaggedNotes.one")
pending, done = [], []

for rt in doc.GetChildNodes(RichText):
    for tag in rt.Tags:
        item = {"label": tag.label, "text": rt.Text.strip()}
        if tag.completed is None:
            pending.append(item)
        else:
            done.append(item)

print(f"Pending: {len(pending)}  Done: {len(done)}")
for p in pending:
    print(f"  [ ] {p['label']}: {p['text']!r}")
for d in done:
    print(f"  [x] {d['label']}: {d['text']!r}")
```

---

## Create a NoteTag (In-Memory)

The factory method `NoteTag.CreateYellowStar()` creates a tag node you can attach to new content in-memory:

```python
from aspose.note import NoteTag

tag = NoteTag.CreateYellowStar()
print(f"Created tag: shape={tag.shape}  label={tag.label!r}")
```

> In-memory creation is useful for API compatibility. Since writing back to `.one` is not supported, created tags cannot be persisted to file.

---

## Common Issues

**No tags found — document returns empty Tags lists**: Not all `.one` files contain tags. Verify the source document has tags visible in Microsoft OneNote before troubleshooting the code.

**`tag.label` is an empty string**: Some tag shapes do not have a text label in the file metadata. Use `tag.shape` to identify the tag type programmatically.

---

**Related Resources:**

- [Features Overview](https://docs.aspose.org/note/python/developer-guide/features/)
- [How to Extract Text](how-to-extract-text-from-onenote-python/)
- [API Reference](https://reference.aspose.org/note/python/)
- [Blog: Introducing Aspose.Note FOSS for Python](https://blog.aspose.org/note/python/introducing-aspose-note-foss-for-python/)
