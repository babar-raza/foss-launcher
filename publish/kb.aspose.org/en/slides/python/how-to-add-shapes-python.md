---
page_role: howto_article
title: "How to Add Shapes in Python"
description: "Learn how to add AutoShapes, Tables, Connectors, and PictureFrames to PowerPoint slides in Python using Aspose.Slides FOSS."
date: 2026-03-11
weight: 20
draft: false
type: "topic"
keywords: ["python add shape pptx", "python add rectangle powerpoint", "aspose slides add shape", "python add table slide", "python add connector pptx", "add picture frame python"]
step1: "Install aspose-slides-foss from PyPI"
step2: "Create or open a Presentation"
step3: "Access a slide from prs.slides"
step4: "Add an AutoShape with add_auto_shape()"
step5: "Add a Table with add_table()"
step6: "Add a Connector between two shapes"
---

Aspose.Slides FOSS for Python supports adding AutoShapes, Tables, Connectors, and PictureFrames to presentation slides. All shape types are added through the `slide.shapes` collection.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install the Package

```bash
pip install aspose-slides-foss
```

Verify the installation:

```python
import aspose.slides_foss as slides
print("Ready")
```

---

### Step 2: Create a Presentation

Always use `Presentation` as a context manager.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    # ... add shapes ...
    prs.save("output.pptx", SaveFormat.PPTX)
```

---

### Step 3: Add an AutoShape

`slide.shapes.add_auto_shape(shape_type, x, y, width, height)` places a shape at the given position and size (all in points). Use `ShapeType` constants to select the shape.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    # Rectangle
    rect = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 100)
    rect.add_text_frame("Rectangle shape")

    # Ellipse
    ellipse = slide.shapes.add_auto_shape(ShapeType.ELLIPSE, 400, 50, 200, 100)
    ellipse.add_text_frame("Ellipse shape")

    prs.save("autoshapes.pptx", SaveFormat.PPTX)
```

---

### Step 4: Add a Table

`slide.shapes.add_table(x, y, col_widths, row_heights)` creates a table at the specified position. Column widths and row heights are lists of point values.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    col_widths = [150.0, 150.0, 150.0]
    row_heights = [40.0, 40.0, 40.0]
    table = slide.shapes.add_table(50, 200, col_widths, row_heights)

    # Set header row text
    headers = ["Product", "Units", "Revenue"]
    for col, text in enumerate(headers):
        table.rows[0][col].text_frame.text = text

    # Set data rows
    rows = [
        ["Widget A", "120", "$2,400"],
        ["Widget B", "85", "$1,700"],
    ]
    for row_idx, row_data in enumerate(rows):
        for col, text in enumerate(row_data):
            table.rows[row_idx + 1][col].text_frame.text = text

    prs.save("table.pptx", SaveFormat.PPTX)
```

---

### Step 5: Add a Connector

Connectors link two shapes visually. Create the shapes first, then add a connector and set its start and end connection points.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    box1 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 100, 150, 60)
    box1.add_text_frame("Start")

    box2 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 350, 100, 150, 60)
    box2.add_text_frame("End")

    conn = slide.shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)
    conn.start_shape_connected_to = box1
    conn.start_shape_connection_site_index = 3  # right side of box1
    conn.end_shape_connected_to = box2
    conn.end_shape_connection_site_index = 1    # left side of box2

    prs.save("connector.pptx", SaveFormat.PPTX)
```

Connection site indices are numbered 0–3 for a rectangle: top=0, left=1, bottom=2, right=3.

---

### Step 6: Add a Picture Frame

Embed an image and add it to the slide as a `PictureFrame`. Read the image bytes first, add them to the presentation's image collection, then create the frame.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    with open("logo.png", "rb") as f:
        image_data = f.read()

    image = prs.images.add_image(image_data)

    slide = prs.slides[0]
    slide.shapes.add_picture_frame(
        ShapeType.RECTANGLE,  # bounding shape type
        50, 50,               # x, y in points
        200, 150,             # width, height in points
        image
    )

    prs.save("with-image.pptx", SaveFormat.PPTX)
```

{{% /steps %}}

---

## Common Issues and Fixes

**Shape appears outside the visible slide area**

Slides are 720 × 540 points by default. Values of `x` or `y` beyond those bounds place the shape off-slide. Keep `x < 720` and `y < 540`, and ensure `x + width <= 720` and `y + height <= 540`.

**`AttributeError: 'NoneType' object has no attribute 'text_frame'`**

`add_auto_shape()` returns the shape object directly. If you see `None`, check that you are not discarding the return value.

**Table cell text is empty after assignment**

The correct property is `.text_frame.text` (not `.text` directly on the cell). Access cells as `table.rows[row_index][col_index].text_frame.text = "value"`.

---

## Frequently Asked Questions

**How many shapes can I add to a slide?**

There is no library-imposed limit. Practical limits depend on file size and the rendering capability of your target PPTX viewer.

**Can I change a shape's position after adding it?**

Yes. The shape object returned by `add_auto_shape()` has `x`, `y`, `width`, and `height` properties that you can set:

```python
shape.x = 100
shape.y = 200
shape.width = 400
shape.height = 80
```

**Can I set the shape outline (border) color?**

Yes, via `shape.line_format`:

```python
from aspose.slides_foss.drawing import Color
shape.line_format.fill_format.solid_fill_color.color = Color.from_argb(255, 200, 0, 0)
```

**Are charts supported?**

No. Charts, SmartArt, and OLE objects are not implemented in this edition and raise `NotImplementedError`.

---

## See Also

- [How to Create Presentations in Python](/kb.aspose.org/slides/python/how-to-create-presentations-python/)
- [How to Format Text in Python](/kb.aspose.org/slides/python/how-to-format-text-python/)
- [Features Overview](/docs.aspose.org/slides/python/developer-guide/features/)
- [API Reference](/reference.aspose.org/slides/python/)
