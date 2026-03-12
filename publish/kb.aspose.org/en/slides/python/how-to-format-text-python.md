---
page_role: howto_article
title: "How to Format Text in Python"
description: "Learn how to format text in PowerPoint presentations using Python and Aspose.Slides FOSS — bold, italic, font size, color, and paragraph alignment."
date: 2026-03-11
weight: 30
draft: false
type: "topic"
keywords: ["python format text pptx", "python bold text powerpoint", "aspose slides format text", "python font color pptx", "python text alignment slide", "PortionFormat python"]
step1: "Install aspose-slides-foss from PyPI"
step2: "Add a shape to a slide"
step3: "Get the TextFrame from the shape"
step4: "Access Paragraph and Portion objects"
step5: "Apply PortionFormat properties (bold, italic, font size, color)"
step6: "Save the presentation"
---

Aspose.Slides FOSS for Python provides fine-grained text formatting through the `PortionFormat` class. A `Portion` is the smallest independent unit of text — it maps to a single formatting run within a paragraph. This guide shows how to apply bold, italic, font size, and color formatting to text in a presentation.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install the Package

```bash
pip install aspose-slides-foss
```

---

### Step 2: Add a Shape with a Text Frame

Before formatting text, a shape must contain a `TextFrame`. Use `shape.add_text_frame()` to create one.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 500, 150)
    tf = shape.add_text_frame("Default text — will be formatted")
    prs.save("output.pptx", SaveFormat.PPTX)
```

---

### Step 3: Access the TextFrame

`shape.add_text_frame()` returns the `TextFrame` object. You can also retrieve it later via `shape.text_frame`.

```python
tf = shape.text_frame          # if the frame already exists
tf = shape.add_text_frame("") # creates a new frame
```

A `TextFrame` contains a list of `Paragraph` objects (`tf.paragraphs`). Each `Paragraph` contains `Portion` objects (`paragraph.portions`).

---

### Step 4: Apply Bold and Italic Formatting

Use `portion_format.font_bold` and `portion_format.font_italic`. These properties accept `NullableBool.TRUE`, `NullableBool.FALSE`, or `NullableBool.NOT_DEFINED` (inherit from master).

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, NullableBool
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 500, 150)
    tf = shape.add_text_frame("Bold and italic text")

    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_bold = NullableBool.TRUE
    fmt.font_italic = NullableBool.TRUE

    prs.save("bold-italic.pptx", SaveFormat.PPTX)
```

---

### Step 5: Set Font Size and Color

Set `portion_format.font_height` for size (in points) and use `fill_format` for color.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, NullableBool, FillType
from aspose.slides_foss.drawing import Color
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 500, 150)
    tf = shape.add_text_frame("Large corporate-blue heading")

    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_height = 32                          # 32pt font
    fmt.font_bold = NullableBool.TRUE
    fmt.fill_format.fill_type = FillType.SOLID
    fmt.fill_format.solid_fill_color.color = Color.from_argb(255, 0, 70, 127)

    prs.save("colored-text.pptx", SaveFormat.PPTX)
```

`Color.from_argb(alpha, red, green, blue)` accepts values 0–255 for each channel.

---

### Step 6: Multiple Portions in One Paragraph

A single paragraph can contain multiple portions with different formatting. Add a new `Portion` to a paragraph's `portions` collection:

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, NullableBool, FillType
from aspose.slides_foss.drawing import Color
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 600, 100)
    tf = shape.add_text_frame("")  # start with empty frame

    paragraph = tf.paragraphs[0]

    # First portion: normal text
    portion1 = paragraph.portions[0]
    portion1.text = "Normal text followed by "
    portion1.portion_format.font_height = 20

    # Second portion: bold red text
    portion2 = slides.Portion()
    portion2.text = "bold red text"
    portion2.portion_format.font_height = 20
    portion2.portion_format.font_bold = NullableBool.TRUE
    portion2.portion_format.fill_format.fill_type = FillType.SOLID
    portion2.portion_format.fill_format.solid_fill_color.color = Color.from_argb(255, 200, 0, 0)
    paragraph.portions.add(portion2)

    prs.save("mixed-format.pptx", SaveFormat.PPTX)
```

{{% /steps %}}

---

## Common Issues and Fixes

**Text appears black even after setting color**

Ensure `fill_format.fill_type = FillType.SOLID` is set before assigning the color. Without setting the fill type, the color change may have no effect.

**`NullableBool.TRUE` vs `True`**

`portion_format.font_bold` expects `NullableBool.TRUE`, not the Python `True`. Assigning Python `True` may raise a `TypeError` or silently do nothing depending on the binding.

**Font does not appear in the saved file**

The `font_latin` property sets the Latin font family. If not set, the presentation theme font is used. Custom fonts must be embedded or available on the viewing machine.

---

## Frequently Asked Questions

**How do I change the font family?**

Set `portion_format.latin_font`:

```python
fmt.latin_font = slides.FontData("Arial")
```

`FontData` accepts the font family name as a string.

**How do I set paragraph alignment?**

Use `paragraph_format.alignment`:

```python
from aspose.slides_foss import TextAlignment

tf.paragraphs[0].paragraph_format.alignment = TextAlignment.CENTER
```

Supported values: `LEFT`, `CENTER`, `RIGHT`, `JUSTIFY`.

**How do I set line spacing?**

Use `paragraph_format.space_before` (points before paragraph) or `paragraph_format.space_after` (points after paragraph):

```python
tf.paragraphs[0].paragraph_format.space_before = 12   # 12pt before
tf.paragraphs[0].paragraph_format.space_after = 6     # 6pt after
```

---

## See Also

- [How to Add Shapes in Python](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [How to Create Presentations in Python](/kb.aspose.org/slides/python/how-to-create-presentations-python/)
- [Features Overview](/docs.aspose.org/slides/python/developer-guide/features/)
- [API Reference](/reference.aspose.org/slides/python/)
