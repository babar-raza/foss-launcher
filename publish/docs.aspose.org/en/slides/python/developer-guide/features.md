---
page_role: howto_article
title: Features and Capabilities
description: >-
  Complete list of Aspose.Slides FOSS for Python features — slides, shapes, text formatting,
  fill types, visual effects, 3D formatting, speaker notes, comments, images, and document properties.
weight: 21
type: docs
---

## Features and Capabilities

Aspose.Slides FOSS for Python provides a broad set of capabilities for working with PowerPoint `.pptx` files programmatically. This page lists all supported feature areas with representative code examples.

---

### Presentation I/O

Open an existing `.pptx` file or create a new one, then save back to PPTX format.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

# Open an existing presentation
with slides.Presentation("input.pptx") as prs:
    print(f"Slide count: {len(prs.slides)}")
    prs.save("output.pptx", SaveFormat.PPTX)

# Create a new presentation (starts with one blank slide)
with slides.Presentation() as prs:
    prs.save("new.pptx", SaveFormat.PPTX)
```

**Note:** PPTX is the only supported save format. Export to PDF, HTML, SVG, or images is not available.

Unknown XML parts in the source file are preserved verbatim on save — opening and re-saving a `.pptx` will never strip content the library does not yet understand.

---

### Slides Management

Add, remove, clone, and reorder slides.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    # Access the first slide
    slide = prs.slides[0]

    # Add an additional blank slide at the end
    prs.slides.add_empty_slide(prs.layout_slides[0])

    print(f"Total slides: {len(prs.slides)}")
    prs.save("multi-slide.pptx", SaveFormat.PPTX)
```

---

### Shapes

Add AutoShapes, PictureFrames, Tables, and Connectors to a slide.

#### AutoShapes

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    # Add a rectangle at (x=50, y=50) with width=300, height=100
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 100)
    shape.add_text_frame("Aspose.Slides FOSS")
    prs.save("shapes.pptx", SaveFormat.PPTX)
```

#### Tables

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    # Column widths and row heights in points
    col_widths = [120.0, 120.0, 120.0]
    row_heights = [40.0, 40.0, 40.0]
    table = slide.shapes.add_table(50, 50, col_widths, row_heights)
    table.rows[0][0].text_frame.text = "Product"
    table.rows[0][1].text_frame.text = "Quantity"
    table.rows[0][2].text_frame.text = "Price"
    prs.save("table.pptx", SaveFormat.PPTX)
```

#### Connectors

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    box1 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 100, 150, 60)
    box2 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 350, 100, 150, 60)
    conn = slide.shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)
    conn.start_shape_connected_to = box1
    conn.start_shape_connection_site_index = 3  # right side
    conn.end_shape_connected_to = box2
    conn.end_shape_connection_site_index = 1    # left side
    prs.save("connector.pptx", SaveFormat.PPTX)
```

---

### Text Formatting

Format text at paragraph and character level using `PortionFormat`.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, NullableBool, FillType
from aspose.slides_foss.drawing import Color
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 500, 150)
    tf = shape.add_text_frame("Bold blue heading")

    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_height = 28
    fmt.font_bold = NullableBool.TRUE
    fmt.fill_format.fill_type = FillType.SOLID
    fmt.fill_format.solid_fill_color.color = Color.from_argb(255, 0, 70, 127)

    prs.save("text.pptx", SaveFormat.PPTX)
```

`NullableBool.TRUE` sets the property explicitly; `NullableBool.NOT_DEFINED` inherits from the slide master.

---

### Fill Types

Apply solid, gradient, pattern, or picture fills to shapes.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, FillType
from aspose.slides_foss.drawing import Color
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 150)

    # Solid fill
    shape.fill_format.fill_type = FillType.SOLID
    shape.fill_format.solid_fill_color.color = Color.from_argb(255, 30, 120, 200)

    prs.save("fill.pptx", SaveFormat.PPTX)
```

---

### Visual Effects

Apply outer shadow, glow, soft edge, blur, reflection, and inner shadow to shapes.

The effect properties are accessible through `shape.effect_format`. Set `outer_shadow_effect`, `glow_effect`, `soft_edge_effect`, `blur_effect`, `reflection_effect`, or `inner_shadow_effect` to configure each independently.

---

### 3D Formatting

Apply 3D bevel, camera, light rig, material, and extrusion depth via `shape.three_d_format`. This controls the visual depth and lighting model for shape rendering in PPTX viewers that support 3D effects.

---

### Speaker Notes

Attach notes to any slide using `notes_slide_manager`.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    notes = prs.slides[0].notes_slide_manager.add_notes_slide()
    notes.notes_text_frame.text = "Key talking point: emphasize the ROI benefit."
    prs.save("notes.pptx", SaveFormat.PPTX)
```

---

### Comments

Add threaded comments with author information and slide position.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.drawing import PointF
from aspose.slides_foss.export import SaveFormat
from datetime import datetime

with slides.Presentation() as prs:
    author = prs.comment_authors.add_author("Jane Smith", "JS")
    slide = prs.slides[0]
    author.comments.add_comment(
        "Please verify this data before the presentation.",
        slide,
        PointF(2.0, 2.0),
        datetime.now()
    )
    prs.save("comments.pptx", SaveFormat.PPTX)
```

---

### Embedded Images

Embed an image from a file path into the presentation and add it to a slide as a `PictureFrame`.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    with open("logo.png", "rb") as f:
        image_data = f.read()
    image = prs.images.add_image(image_data)
    slide = prs.slides[0]
    slide.shapes.add_picture_frame(
        slides.ShapeType.RECTANGLE, 50, 50, 200, 150, image
    )
    prs.save("with-image.pptx", SaveFormat.PPTX)
```

---

### Document Properties

Read and write core, app, and custom document properties.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    props = prs.document_properties

    # Core properties
    props.title = "Q1 Results"
    props.author = "Finance Team"
    props.subject = "Quarterly Review"
    props.keywords = "Q1, finance, results"

    # Custom property
    props.set_custom_property_value("ReviewedBy", "Legal Team")

    prs.save("deck.pptx", SaveFormat.PPTX)
```

---

### Known Limitations

The following areas raise `NotImplementedError` and are not available in this edition:

| Area | Status |
|------|--------|
| Charts | Not implemented |
| SmartArt | Not implemented |
| Animations and transitions | Not implemented |
| PDF / HTML / SVG / image export | Not implemented (PPTX only) |
| VBA macros | Not implemented |
| Digital signatures | Not implemented |
| Hyperlinks and action settings | Not implemented |
| OLE objects | Not implemented |
| Mathematical text | Not implemented |

---

## See Also

- [Getting Started](/docs.aspose.org/slides/python/getting-started/) — Installation and first script
- [API Reference](/reference.aspose.org/slides/python/) — Class and method reference
- [How-To Guides](/kb.aspose.org/slides/python/) — Task-oriented articles
