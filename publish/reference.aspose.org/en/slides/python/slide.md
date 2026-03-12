---
page_role: reference_object_page
title: "Slide — Aspose.Slides FOSS for Python API Reference"
description: "API reference for the Slide class in aspose-slides-foss. Shapes collection, notes slide, comments, hiding slides, and layout management."
canonical: https://reference.aspose.org/slides/python/slide/
url: /reference.aspose.org/slides/python/slide/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "Slide Class — Aspose.Slides FOSS for Python API Reference"
keywords:
  - aspose slides slide python
  - python pptx slide class
  - python slide shapes
  - python speaker notes
  - aspose slides foss python api
type: reference_object_page
draft: false
weight: 20
---

The `Slide` class represents a single slide in a `Presentation`. It is not instantiated directly — slides are created by `SlideCollection.add_empty_slide()` or accessed via `prs.slides[index]`.

**Package**: `aspose.slides_foss`

**Access**:

```python
import aspose.slides_foss as slides

with slides.Presentation() as prs:
    slide = prs.slides[0]   # first slide (zero-based index)
```

---

## Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `shapes` | `ShapeCollection` | Read | All shapes on this slide: AutoShapes, Tables, PictureFrames, Connectors. |
| `notes_slide_manager` | `NotesSlideManager` | Read | Manages the speaker notes slide for this slide. Call `.add_notes_slide()` to create notes. |
| `slide_number` | `int` | Read | One-based slide position number. |
| `hidden` | `bool` | Read/Write | When `True`, the slide is excluded from the slideshow. |
| `layout_slide` | `LayoutSlide` | Read | The layout slide applied to this slide. |
| `master_slide` | `MasterSlide` | Read | The master slide for this slide's layout. |

---

## ShapeCollection Methods

Add shapes to `slide.shapes` using these methods:

| Method | Signature | Description |
|---|---|---|
| `add_auto_shape` | `(type, x, y, width, height) -> AutoShape` | Add an AutoShape (rectangle, ellipse, triangle, etc.) at the given position and size (all in points). |
| `add_table` | `(x, y, col_widths, row_heights) -> Table` | Add a table. `col_widths` is a list of floats (points per column); `row_heights` is a list of floats (points per row). |
| `add_picture_frame` | `(type, x, y, width, height, image) -> PictureFrame` | Add an image. `image` is an `Image` object from `prs.images.add_image(bytes_or_path)`. |
| `add_connector` | `(type, x, y, width, height) -> Connector` | Add a connector shape. Connect to shapes via `.start_shape_connected_to` and `.end_shape_connected_to`. |
| `remove` | `(shape) -> None` | Remove a specific shape by reference. |
| `remove_at` | `(index) -> None` | Remove the shape at zero-based `index`. |
| `clear` | `() -> None` | Remove all shapes from the slide. |
| `__getitem__` | `[index: int] -> Shape` | Return the shape at zero-based `index`. |
| `__len__` | `() -> int` | Total number of shapes on the slide. |
| `__iter__` | — | Iterate over all shapes. |

---

## NotesSlideManager

| Method | Description |
|---|---|
| `add_notes_slide()` | Create and attach a speaker notes slide. Returns the `NotesSlide` object. |
| `notes_slide` | `NotesSlide \| None` — returns the existing notes slide if already created; `None` otherwise. |

The `NotesSlide` object exposes `notes_text_frame`, a `TextFrame` for the notes body text.

---

## Usage Examples

### Add Shapes to a Slide

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    rect = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 100)
    rect.add_text_frame("Main Content")

    ellipse = slide.shapes.add_auto_shape(ShapeType.ELLIPSE, 400, 50, 150, 100)
    ellipse.add_text_frame("Highlight")

    prs.save("shapes.pptx", SaveFormat.PPTX)
```

### Iterate Slides and Inspect Shapes

```python
import aspose.slides_foss as slides

with slides.Presentation("deck.pptx") as prs:
    for slide in prs.slides:
        print(f"Slide {slide.slide_number}: {len(slide.shapes)} shapes")
        for shape in slide.shapes:
            print(f"  {shape.name} at ({shape.x:.0f}, {shape.y:.0f})")
```

### Add Speaker Notes

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    notes = slide.notes_slide_manager.add_notes_slide()
    notes.notes_text_frame.text = "Remember to emphasize the ROI figures here."
    prs.save("with-notes.pptx", SaveFormat.PPTX)
```

### Add a Table

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    table = slide.shapes.add_table(50, 50, [150.0, 150.0, 150.0], [40.0, 40.0, 40.0])

    headers = ["Product", "Units", "Revenue"]
    for col, header in enumerate(headers):
        table.rows[0][col].text_frame.text = header

    table.rows[1][0].text_frame.text = "Widget A"
    table.rows[1][1].text_frame.text = "1,200"
    table.rows[1][2].text_frame.text = "$60,000"

    prs.save("table-slide.pptx", SaveFormat.PPTX)
```

### Hide a Slide

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation("deck.pptx") as prs:
    prs.slides[2].hidden = True  # exclude slide 3 from slideshow
    prs.save("deck-modified.pptx", SaveFormat.PPTX)
```

### Connect Two Shapes

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
    conn.start_shape_connection_site_index = 3   # right side of box1
    conn.end_shape_connected_to = box2
    conn.end_shape_connection_site_index = 1     # left side of box2

    prs.save("connected.pptx", SaveFormat.PPTX)
```

Connection site indexes: `0` = top, `1` = left, `2` = bottom, `3` = right.

---

## See Also

- [Presentation class reference](/reference.aspose.org/slides/python/presentation/)
- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [TextFrame class reference](/reference.aspose.org/slides/python/textframe/)
- [Slides Python API Reference home](/reference.aspose.org/slides/python/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [How to Work with Tables](/kb.aspose.org/slides/python/how-to-work-with-tables-python/)
- [Developer Guide](/docs.aspose.org/slides/python/developer-guide/)
