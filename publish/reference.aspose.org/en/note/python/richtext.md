---
page_role: howto_article
linkTitle: "RichText"
title: "RichText — Aspose.Note FOSS for Python API Reference"
description: "API reference for the RichText class in aspose-note v26.2. Represents a styled text block in a OneNote document with formatting runs, hyperlinks, and tags."
categories:
  - Class
layout: "reference"
---

## Class: RichText

**Package**: `aspose.note`
**Import**: `from aspose.note import RichText`
**Inherits**: `CompositeNode`

`RichText` represents a block of styled text within an `OutlineElement`, `TableCell`, or `Title`. It exposes the full plain-text content via `.Text` and individual formatting segments via `.Runs`.

---

## Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `Text` | `str` | Read | Full plain-text string (all runs concatenated) |
| `Runs` | `list[TextRun]` | Read | Ordered list of individually formatted segments |
| `FontSize` | `float \| None` | Read | Paragraph-level font size in points |
| `Tags` | `list[NoteTag]` | Read | OneNote tags attached to this text block |

### Inherited from CompositeNode / Node

| Property | Description |
|---|---|
| `ParentNode` | Containing node (OutlineElement, TableCell, Title) |
| `Document` | Root Document |

---

## Methods

### Append(text, style=None)

```python
rt.Append(text: str, style: TextStyle | None = None) -> RichText
```

Appends a new text run with optional style. Returns `self` for chaining. Operates in-memory; changes cannot be saved back to `.one`.

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
first_rt = doc.GetChildNodes(RichText)[0]
first_rt.Append(" [reviewed]")
```

---

### Replace(old_value, new_value)

```python
rt.Replace(old_value: str, new_value: str) -> None
```

Substitutes all occurrences of `old_value` with `new_value` across all runs. Operates in-memory.

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    rt.Replace("TODO", "DONE")
```

---

### Accept(visitor)

```python
rt.Accept(visitor: DocumentVisitor) -> None
```

Dispatches `VisitRichTextStart(rt)` and `VisitRichTextEnd(rt)` on the visitor.

---

## TextRun

Each element of `RichText.Runs` is a `TextRun`:

| Property | Type | Description |
|---|---|---|
| `Text` | `str` | Segment text |
| `Style` | `TextStyle` | Formatting properties for this segment |
| `Start` | `int \| None` | Character offset of segment start within `RichText.Text` |
| `End` | `int \| None` | Character offset of segment end |

---

## TextStyle

`TextRun.Style` is a `TextStyle` with the following properties:

| Property | Type | Description |
|---|---|---|
| `Bold` | `bool` | Bold |
| `Italic` | `bool` | Italic |
| `Underline` | `bool` | Underline |
| `Strikethrough` | `bool` | Strikethrough |
| `Superscript` | `bool` | Superscript |
| `Subscript` | `bool` | Subscript |
| `FontName` | `str \| None` | Font family name |
| `FontSize` | `float \| None` | Font size in points |
| `FontColor` | `int \| None` | Font color as ARGB integer |
| `HighlightColor` | `int \| None` | Highlight background color as ARGB integer |
| `LanguageId` | `int \| None` | Language identifier (LCID) |
| `IsHyperlink` | `bool` | Whether this run is a hyperlink |
| `HyperlinkAddress` | `str \| None` | Hyperlink URL (when `IsHyperlink` is True) |

---

## Usage Examples

### Get all plain text

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    if rt.Text:
        print(rt.Text)
```

### Inspect all runs with formatting

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        s = run.Style
        attrs = [a for a, v in [
            ("bold", s.Bold), ("italic", s.Italic),
            ("underline", s.Underline), ("strike", s.Strikethrough),
        ] if v]
        label = ", ".join(attrs) or "plain"
        print(f"  [{label}] {run.Text!r}")
```

### Extract hyperlinks

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.IsHyperlink and run.Style.HyperlinkAddress:
            print(f"  {run.Text!r} -> {run.Style.HyperlinkAddress}")
```

### Find all bold text

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
bold_segments = [
    run.Text for rt in doc.GetChildNodes(RichText)
    for run in rt.Runs
    if run.Style.Bold and run.Text.strip()
]
print(bold_segments)
```

### Read tags

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for tag in rt.Tags:
        print(f"Tag: {tag.label!r}  on text: {rt.Text.strip()!r}")
```

---

## None-Safety

`Text` is always a `str` (never `None`). `Runs` is always a list (may be empty). `FontSize`, `FontColor`, `HighlightColor`, `LanguageId`, `HyperlinkAddress` can be `None`.

---

## See Also

- [Page](page/) — ancestor of RichText
- [TextRun](/reference.aspose.org/note/python/#textrun) — individual formatted segment
- [TextStyle](/reference.aspose.org/note/python/#textstyle) — formatting properties
- [NoteTag](/reference.aspose.org/note/python/#notetag) — tags on text
- [Text Extraction Developer Guide](https://docs.aspose.org/note/python/developer-guide/text-extraction/)
- [How-to: Extract Text from OneNote (KB)](https://kb.aspose.org/note/python/how-to-extract-text-onenote-python/)
- [Blog: Extract Text from OneNote in Python](https://blog.aspose.org/note/python/extract-text-onenote-python/)
