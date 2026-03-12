---
page_role: howto_article
title: "How to Create Presentations in Python"
description: "Learn how to create a PowerPoint presentation from scratch in Python using Aspose.Slides FOSS — add slides, shapes, and text, then save to PPTX format."
date: 2026-03-11
weight: 10
draft: false
type: "topic"
keywords: ["create pptx python", "python create powerpoint", "aspose slides foss create", "python presentation from scratch", "add slide python", "add shape python"]
step1: "Install aspose-slides-foss from PyPI"
step2: "Import aspose.slides_foss and SaveFormat"
step3: "Create a Presentation using the context manager"
step4: "Access the first slide via prs.slides[0]"
step5: "Add an AutoShape and attach a TextFrame"
step6: "Save to PPTX with prs.save()"
---

Aspose.Slides FOSS for Python lets you create PowerPoint presentations entirely in Python with no dependency on Microsoft Office. This guide shows how to create a new presentation, add slides and shapes, format text, and save the result.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install the Package

Install Aspose.Slides FOSS from PyPI. Python 3.10 or later is required.

```bash
pip install aspose-slides-foss
```

Verify the installation:

```python
import aspose.slides_foss as slides
print("Aspose.Slides FOSS ready")
```

The `lxml` dependency is installed automatically. No other system packages are required.

---

### Step 2: Import the Required Modules

Import the package and the `SaveFormat` enum needed for saving.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat
from aspose.slides_foss import ShapeType
```

All shape-type constants live in `aspose.slides_foss.ShapeType`. All formatting types (`FillType`, `NullableBool`) are also in `aspose.slides_foss`.

---

### Step 3: Create a Presentation

Use `slides.Presentation()` as a context manager. A new presentation starts with one blank slide.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    print(f"Slides in new presentation: {len(prs.slides)}")
    # work with prs inside this block
    prs.save("output.pptx", SaveFormat.PPTX)
```

**Important:** Always open and use `Presentation` inside a `with` block. Do not store a reference outside the `with` statement — resources will not be released correctly.

---

### Step 4: Access a Slide

The first slide is at index 0. A blank presentation has exactly one slide.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]  # zero-based index
    print(f"Slide at index 0: {slide}")
    prs.save("output.pptx", SaveFormat.PPTX)
```

---

### Step 5: Add a Shape

Use `slide.shapes.add_auto_shape()` to add an AutoShape. The parameters are `(shape_type, x, y, width, height)` all in points (1 point = 1/72 inch; standard slide is 720 × 540 pt).

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    # Rectangle at (50, 50) with 400 wide and 120 tall
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 400, 120)

    # Attach a text frame
    shape.add_text_frame("Hello from Aspose.Slides FOSS!")

    prs.save("with-shape.pptx", SaveFormat.PPTX)
```

---

### Step 6: Save the Presentation

Call `prs.save(path, SaveFormat.PPTX)` before the `with` block exits. PPTX is the only supported output format.

```python
prs.save("result.pptx", SaveFormat.PPTX)
```

The file is written atomically — if an error occurs before this call, no output file is created.

{{% /steps %}}

---

## Complete Working Example

The following script creates a two-slide presentation with a title shape on the first slide and a table on the second.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, NullableBool, FillType
from aspose.slides_foss.drawing import Color
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    # --- Slide 1: title shape ---
    slide1 = prs.slides[0]
    title = slide1.shapes.add_auto_shape(ShapeType.RECTANGLE, 40, 40, 640, 80)
    tf = title.add_text_frame("Q1 Results — Executive Summary")
    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_height = 32
    fmt.font_bold = NullableBool.TRUE
    fmt.fill_format.fill_type = FillType.SOLID
    fmt.fill_format.solid_fill_color.color = Color.from_argb(255, 0, 70, 127)

    # --- Slide 2: table ---
    prs.slides.add_empty_slide(prs.layout_slides[0])
    slide2 = prs.slides[1]
    table = slide2.shapes.add_table(40, 40, [200.0, 120.0, 120.0], [40.0, 40.0, 40.0])
    headers = ["Region", "Revenue", "Growth"]
    data = [
        ["North", "$1.2M", "+8%"],
        ["South", "$0.9M", "+4%"],
    ]
    for col, header in enumerate(headers):
        table.rows[0][col].text_frame.text = header
    for row_idx, row_data in enumerate(data):
        for col, cell_text in enumerate(row_data):
            table.rows[row_idx + 1][col].text_frame.text = cell_text

    prs.save("q1-results.pptx", SaveFormat.PPTX)

print("Saved q1-results.pptx")
```

---

## Common Issues and Fixes

**`ResourceWarning: unclosed Presentation`**

You are instantiating `Presentation` without a `with` block. Always use:

```python
with slides.Presentation() as prs:
    ...
```

**`AttributeError: __enter__`**

If you see this error, check that you imported `aspose.slides_foss` (not `aspose.slides`). The package name on PyPI is `aspose-slides-foss` and the runtime import is `aspose.slides_foss`.

**`TypeError: SaveFormat.PPTX is not callable`**

`SaveFormat.PPTX` is an enum member, not a function. Use it as `prs.save("file.pptx", SaveFormat.PPTX)`.

---

## Frequently Asked Questions

**What is the default slide size?**

A new `Presentation()` creates slides at the standard 10 × 7.5 inch (720 × 540 point) size. Changing the slide size is not yet supported in this edition.

**Can I add more than one slide?**

Yes. Call `prs.slides.add_empty_slide(prs.layout_slides[0])` to append a blank slide and access it by index:

```python
prs.slides.add_empty_slide(prs.layout_slides[0])
slide2 = prs.slides[1]
```

**Can I open an existing file and add slides?**

Yes:

```python
with slides.Presentation("existing.pptx") as prs:
    prs.slides.add_empty_slide(prs.layout_slides[0])
    prs.save("existing.pptx", SaveFormat.PPTX)
```

**What formats can I save to?**

Only `SaveFormat.PPTX` is supported. Export to PDF, HTML, SVG, or images is not available in this edition.

---

## See Also

- [How to Add Shapes in Python](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [How to Format Text in Python](/kb.aspose.org/slides/python/how-to-format-text-python/)
- [Features Overview](/docs.aspose.org/slides/python/developer-guide/features/)
- [API Reference](/reference.aspose.org/slides/python/)
