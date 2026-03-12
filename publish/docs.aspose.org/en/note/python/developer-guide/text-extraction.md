---
page_role: howto_article
description: >-
  Extract plain text, formatted runs, and hyperlinks from Microsoft OneNote .one files
  in Python using Aspose.Note FOSS. Covers RichText, TextRun, TextStyle, and page-by-page extraction.
title: Text Extraction — Aspose.Note FOSS for Python
type: docs
weight: 10
---

Aspose.Note FOSS for Python exposes the full text content of every OneNote page through the `RichText` node. Each `RichText` holds both a plain-text `.Text` string and a `.Runs` list of individually styled `TextRun` segments. This page documents every available text extraction pattern.

---

## Extract All Plain Text

The fastest way to get all text from a document is `GetChildNodes(RichText)`, which performs a recursive depth-first traversal across the entire DOM:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    if rt.Text:
        print(rt.Text)
```

Collect into a list and join:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
all_text = "\n".join(
    rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text
)
```

---

## Extract Text Per Page

Organize extracted text by page title:

```python
from aspose.note import Document, Page, RichText

doc = Document("MyNotes.one")
for page in doc.GetChildNodes(Page):
    title = (
        page.Title.TitleText.Text
        if page.Title and page.Title.TitleText
        else "(untitled)"
    )
    print(f"\n=== {title} ===")
    for rt in page.GetChildNodes(RichText):
        if rt.Text:
            print(rt.Text)
```

---

## Inspect Formatting Runs

`RichText.Runs` is a list of `TextRun` objects. Each run covers a contiguous range of characters with a uniform `TextStyle`:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        style = run.Style
        parts = []
        if style.Bold:          parts.append("bold")
        if style.Italic:        parts.append("italic")
        if style.Underline:     parts.append("underline")
        if style.Strikethrough: parts.append("strikethrough")
        if style.Superscript:   parts.append("superscript")
        if style.Subscript:     parts.append("subscript")
        if style.FontName:      parts.append(f"font={style.FontName!r}")
        if style.FontSize:      parts.append(f"size={style.FontSize}pt")
        label = ", ".join(parts) if parts else "plain"
        print(f"[{label}] {run.Text!r}")
```

### TextStyle Property Reference

| Property | Type | Description |
|---|---|---|
| `Bold` | `bool` | Bold text |
| `Italic` | `bool` | Italic text |
| `Underline` | `bool` | Underlined text |
| `Strikethrough` | `bool` | Strikethrough text |
| `Superscript` | `bool` | Superscript |
| `Subscript` | `bool` | Subscript |
| `FontName` | `str \| None` | Font family name |
| `FontSize` | `float \| None` | Font size in points |
| `FontColor` | `int \| None` | Font color as ARGB integer |
| `HighlightColor` | `int \| None` | Background highlight color as ARGB integer |
| `LanguageId` | `int \| None` | Language identifier (LCID) |
| `IsHyperlink` | `bool` | Whether this run is a hyperlink |
| `HyperlinkAddress` | `str \| None` | URL when `IsHyperlink` is True |

---

## Extract Hyperlinks

Hyperlinks are stored at the `TextRun` level. Check `Style.IsHyperlink`:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.IsHyperlink and run.Style.HyperlinkAddress:
            print(f"  {run.Text!r:40s} -> {run.Style.HyperlinkAddress}")
```

---

## Extract Bold and Highlighted Text

Filter runs by formatting properties to isolate specific content:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
print("=== Bold segments ===")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.Bold and run.Text.strip():
            print(f"  {run.Text.strip()!r}")

print("\n=== Highlighted segments ===")
for rt in doc.GetChildNodes(RichText):
    for run in rt.Runs:
        if run.Style.HighlightColor is not None and run.Text.strip():
            color = f"#{run.Style.HighlightColor & 0xFFFFFF:06X}"
            print(f"  [{color}] {run.Text.strip()!r}")
```

---

## Extract Text from Title Blocks

Page titles are `RichText` nodes inside the `Title` object — they are not returned by a top-level `GetChildNodes(RichText)` on the page unless you include the `Title` subtree. Access them directly:

```python
from aspose.note import Document, Page

doc = Document("MyNotes.one")
for page in doc.GetChildNodes(Page):
    if page.Title:
        if page.Title.TitleText:
            print("Title text:", page.Title.TitleText.Text)
        if page.Title.TitleDate:
            print("Title date:", page.Title.TitleDate.Text)
        if page.Title.TitleTime:
            print("Title time:", page.Title.TitleTime.Text)
```

---

## Extract Text from Tables

Table cells contain `RichText` children. Use nested `GetChildNodes` calls:

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("MyNotes.one")
for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        row_values = []
        for cell in row.GetChildNodes(TableCell):
            cell_text = " ".join(
                rt.Text for rt in cell.GetChildNodes(RichText)
            ).strip()
            row_values.append(cell_text)
        print(row_values)
```

---

## In-Memory Text Operations

### Replace text

`RichText.Replace(old_value, new_value)` substitutes text in-memory across all runs:

```python
from aspose.note import Document, RichText

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    rt.Replace("TODO", "DONE")
##Changes are in-memory only; saving back to .one is not supported
```

### Append a text run

```python
from aspose.note import Document, RichText, TextStyle

doc = Document("MyNotes.one")
for rt in doc.GetChildNodes(RichText):
    rt.Append(" [reviewed]")  # appends with default style
    break  # just the first node in this example
```

---

## Save Extracted Text to File

```python
import sys
from aspose.note import Document, RichText

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

doc = Document("MyNotes.one")
lines = [rt.Text for rt in doc.GetChildNodes(RichText) if rt.Text]

with open("extracted.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Extracted {len(lines)} text blocks.")
```

---

## Tips

- `GetChildNodes(RichText)` on a `Document` searches the **entire** tree including all pages, outlines, and outline elements. Call it on a specific `Page` to limit scope.
- Always check `rt.Text` (or `if rt.Text:`) before printing — empty `RichText` nodes exist in some documents.
- On Windows, reconfigure `sys.stdout` to UTF-8 to avoid `UnicodeEncodeError` when printing characters outside the system code page.
- `TextRun.Start` and `TextRun.End` indicate character offsets within the parent `RichText.Text` string and can be used to map formatted runs to the full text string.

---

## See Also

- [How-to: Extract Text from OneNote (KB)](https://kb.aspose.org/note/python/how-to-extract-text-onenote-python/)
- [Blog: Extract Text from OneNote](https://blog.aspose.org/note/python/extract-text-onenote-python/)
- [API Reference — RichText](https://reference.aspose.org/note/python/richtext/)
- [API Reference — Page](https://reference.aspose.org/note/python/page/)
