---
page_role: reference_object_page
title: "TextFrame, Paragraph, Portion — Aspose.Slides FOSS for Python API Reference"
description: "API reference for the TextFrame, Paragraph, Portion, and PortionFormat classes in aspose-slides-foss. Text hierarchy, character formatting, and paragraph alignment."
canonical: https://reference.aspose.org/slides/python/textframe/
url: /reference.aspose.org/slides/python/textframe/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "TextFrame, Paragraph, Portion — Aspose.Slides FOSS for Python API Reference"
keywords:
  - aspose slides textframe python
  - python pptx text formatting
  - python slide text bold italic
  - aspose slides portion format python
  - python pptx font color
type: reference_object_page
draft: false
weight: 40
---

The text system in Aspose.Slides FOSS uses a three-level hierarchy: **TextFrame → Paragraph → Portion**. A `TextFrame` is the container; it holds one or more `Paragraph` objects; each `Paragraph` holds one or more `Portion` objects, each carrying consistent character formatting.

**Package**: `aspose.slides_foss`

---

## Text Hierarchy

```
TextFrame
 └── Paragraph (paragraphs[0], paragraphs[1], …)
      └── Portion  (portions[0], portions[1], …)
           └── PortionFormat
```

---

## TextFrame

A `TextFrame` is attached to a shape. Access via `shape.text_frame` or create one with `shape.add_text_frame(text)`.

### Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `text` | `str` | Read/Write | Full plain text of all paragraphs concatenated. Setting this replaces all content with a single paragraph containing one portion. |
| `paragraphs` | `ParagraphCollection` | Read | Ordered list of `Paragraph` objects. |

### ParagraphCollection Methods

| Method | Description |
|---|---|
| `add(paragraph)` | Append a new `Paragraph` to the text frame. |
| `__getitem__[i]` | Return the `Paragraph` at zero-based index `i`. |
| `__len__` | Number of paragraphs. |

---

## Paragraph

### Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `paragraph_format` | `ParagraphFormat` | Read | Paragraph-level formatting: alignment, spacing, bullet. |
| `portions` | `PortionCollection` | Read | Ordered list of `Portion` objects in this paragraph. |

### PortionCollection Methods

| Method | Description |
|---|---|
| `add(portion)` | Append a `Portion` to this paragraph. |
| `__getitem__[i]` | Return the `Portion` at index `i`. |
| `__len__` | Number of portions. |

### ParagraphFormat Properties

| Property | Type | Description |
|---|---|---|
| `alignment` | `TextAlignment` | Text alignment: `LEFT`, `CENTER`, `RIGHT`, `JUSTIFY`, `DISTRIBUTED`. |
| `space_before` | `float` | Space before the paragraph in points. |
| `space_after` | `float` | Space after the paragraph in points. |
| `bullet` | `BulletFormat` | Bullet and numbering settings. |

---

## Portion

A `Portion` is the smallest independently-formatted text segment.

### Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `text` | `str` | Read/Write | The text content of this portion. |
| `portion_format` | `PortionFormat` | Read | Character-level formatting for this portion. |

---

## PortionFormat

Access via `portion.portion_format`.

### Character Formatting Properties

| Property | Type | Description |
|---|---|---|
| `font_bold` | `NullableBool` | Bold. Use `NullableBool.TRUE` or `NullableBool.FALSE`. |
| `font_italic` | `NullableBool` | Italic. |
| `font_underline` | `TextUnderlineType` | Underline style. Common values: `TextUnderlineType.NONE`, `TextUnderlineType.SINGLE`, `TextUnderlineType.DOUBLE`. |
| `strikethrough_type` | `TextStrikethroughType` | Strikethrough style. Common values: `TextStrikethroughType.NONE`, `TextStrikethroughType.SINGLE`. |
| `font_height` | `float` | Font size in points. |
| `latin_font` | `FontData` | Latin (Western) font. Assign `FontData("Font Name")`. |
| `fill_format` | `FillFormat` | Text colour fill. Set `fill_type = FillType.SOLID` and `solid_fill_color.color = Color.from_argb(...)`. |

### NullableBool Values

| Value | Meaning |
|---|---|
| `NullableBool.TRUE` | Explicitly enabled |
| `NullableBool.FALSE` | Explicitly disabled |
| `NullableBool.UNDEFINED` | Inherit from layout/master |

---

## Usage Examples

### Set Text and Font Size

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 400, 100)
    tf = shape.add_text_frame("Welcome to Aspose.Slides!")
    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_height = 28
    prs.save("font-size.pptx", SaveFormat.PPTX)
```

### Bold, Italic, and Underline

```python
from aspose.slides_foss import ShapeType, NullableBool, TextUnderlineType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 400, 100)
    tf = shape.add_text_frame("Formatted text")
    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_bold = NullableBool.TRUE
    fmt.font_italic = NullableBool.TRUE
    fmt.font_underline = TextUnderlineType.SINGLE
    prs.save("bold-italic.pptx", SaveFormat.PPTX)
```

### Custom Font and Color

```python
from aspose.slides_foss import ShapeType, NullableBool, FillType, FontData
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 400, 100)
    tf = shape.add_text_frame("Custom styled text")
    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_height = 24
    fmt.font_bold = NullableBool.TRUE
    fmt.latin_font = FontData("Georgia")
    fmt.fill_format.fill_type = FillType.SOLID
    fmt.fill_format.solid_fill_color.color = Color.from_argb(255, 0, 70, 127)
    prs.save("custom-font.pptx", SaveFormat.PPTX)
```

### Paragraph Alignment

```python
from aspose.slides_foss import ShapeType, TextAlignment
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 500, 150)
    tf = shape.add_text_frame("Centered heading")
    tf.paragraphs[0].paragraph_format.alignment = TextAlignment.CENTER
    prs.save("aligned.pptx", SaveFormat.PPTX)
```

### Multi-Portion Rich Text

```python
from aspose.slides_foss import ShapeType, NullableBool, FillType, Portion, Paragraph
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 500, 100)
    tf = shape.add_text_frame("")

    para = tf.paragraphs[0]
    para.portions.clear()

    # Normal portion
    p1 = Portion()
    p1.text = "Normal "
    para.portions.add(p1)

    # Bold red portion
    p2 = Portion()
    p2.text = "Important"
    p2.portion_format.font_bold = NullableBool.TRUE
    p2.portion_format.fill_format.fill_type = FillType.SOLID
    p2.portion_format.fill_format.solid_fill_color.color = Color.red
    para.portions.add(p2)

    prs.save("rich-text.pptx", SaveFormat.PPTX)
```

---

## See Also

- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [FillFormat class reference](/reference.aspose.org/slides/python/fill-format/)
- [Slides Python API Reference home](/reference.aspose.org/slides/python/)
- [How to Format Text](/kb.aspose.org/slides/python/how-to-format-text-python/)
- [Developer Guide — Features](/docs.aspose.org/slides/python/developer-guide/features/)
