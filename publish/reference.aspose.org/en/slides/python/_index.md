---
canonical: https://reference.aspose.org/slides/python/
canonical_import: aspose_slides_foss
date: '2026-03-11T16:00:00Z'
dateModified: '2026-03-11T16:00:00Z'
datePublished: '2026-03-11T16:00:00Z'
description: Aspose.Slides FOSS for Python API Reference — Presentation, Slide, Shape, TextFrame, FillFormat, EffectFormat, and supporting classes.
display_name: Aspose.Slides
family: slides
keywords:
- aspose slides python api
- aspose.slides_foss reference
- python pptx presentation class
- python slide shapes api
lastmod: '2026-03-11T16:00:00Z'
page_role: reference_home
platform: python
reading_time: 2
robots: index, follow
seoTitle: Aspose.Slides FOSS for Python — API Reference
slug: _index
title: Aspose.Slides FOSS for Python API Reference
type: reference_home
url: /reference.aspose.org/slides/python/
weight: 1
---

## Overview

The Aspose.Slides FOSS for Python API is organized into the `aspose.slides_foss` package and its sub-packages. All public classes live under `aspose.slides_foss` or one of its sub-modules.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat
from aspose.slides_foss import ShapeType, FillType, NullableBool
from aspose.slides_foss.drawing import Color, PointF
```

---

## Core Classes

| Class | Description |
|-------|-------------|
| `Presentation` | Root container. Open or create a `.pptx` file. Must be used as a context manager. |
| `ISlideCollection` | Collection of slides accessible via `prs.slides`. |
| `Slide` | A single slide; access shapes, notes, and comments via `slide.shapes`, `slide.notes_slide_manager`. |
| `ShapeCollection` | Collection of shapes on a slide. Add shapes with `add_auto_shape()`, `add_table()`, `add_connector()`, `add_picture_frame()`. |
| `AutoShape` | Rectangular, elliptical, or other standard shape. |
| `PictureFrame` | Shape containing an embedded raster image. |
| `Table` | Tabular shape with `rows` and `columns` collections. |
| `Connector` | Line connector linking two shapes. |
| `TextFrame` | Text container attached to a shape. Contains `paragraphs`. |
| `Paragraph` | Single paragraph in a `TextFrame`. Contains `portions` and `paragraph_format`. |
| `Portion` | Run of text within a paragraph. Contains `text` and `portion_format`. |
| `PortionFormat` | Character-level formatting: `font_height`, `font_bold`, `font_italic`, `fill_format`. |
| `FillFormat` | Fill settings for a shape or text: `fill_type`, `solid_fill_color`, `gradient_fill_format`. |
| `EffectFormat` | Visual effects: `outer_shadow_effect`, `glow_effect`, `blur_effect`, `reflection_effect`, `inner_shadow_effect`, `soft_edge_effect`. |
| `ThreeDFormat` | 3D formatting: `bevel_top`, `bevel_bottom`, `camera`, `light_rig`, `material`, `extrusion_depth`. |
| `NotesSlideManger` | Manages speaker notes for a slide via `add_notes_slide()`. |
| `NotesSlide` | Speaker notes page; `notes_text_frame` gives access to note text. |
| `CommentAuthorCollection` | Collection of comment authors; add with `prs.comment_authors.add_author()`. |
| `CommentAuthor` | A named comment author with initials. |
| `Comment` | A threaded comment on a slide with position, timestamp, and text. |
| `DocumentProperties` | Core, app, and custom presentation properties. |
| `ImageCollection` | Embedded images; add with `prs.images.add_image()`. |

---

## Enumerations

| Enum | Import Path | Key Members |
|------|-------------|-------------|
| `ShapeType` | `aspose.slides_foss` | `RECTANGLE`, `ELLIPSE`, `TRIANGLE`, `BENT_CONNECTOR3`, `STRAIGHT_CONNECTOR1`, and many more |
| `FillType` | `aspose.slides_foss` | `NOT_DEFINED`, `NO_FILL`, `SOLID`, `GRADIENT`, `PATTERN`, `PICTURE` |
| `NullableBool` | `aspose.slides_foss` | `NOT_DEFINED`, `FALSE`, `TRUE` |
| `SaveFormat` | `aspose.slides_foss.export` | `PPTX` (only supported save format) |

---

## Sub-Packages

| Package | Description |
|---------|-------------|
| `aspose.slides_foss.export` | `SaveFormat` enum and related export types |
| `aspose.slides_foss.drawing` | `Color`, `PointF`, and drawing primitives |

---

## Quick Reference

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, FillType, NullableBool
from aspose.slides_foss.drawing import Color
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    # Add shape with text
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 400, 120)
    tf = shape.add_text_frame("Slide content")

    # Format the text
    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_height = 24
    fmt.font_bold = NullableBool.TRUE
    fmt.fill_format.fill_type = FillType.SOLID
    fmt.fill_format.solid_fill_color.color = Color.from_argb(255, 0, 70, 127)

    # Fill the shape
    shape.fill_format.fill_type = FillType.SOLID
    shape.fill_format.solid_fill_color.color = Color.from_argb(255, 230, 240, 255)

    prs.save("demo.pptx", SaveFormat.PPTX)
```

---

## See Also

- [Developer Guide](/docs.aspose.org/slides/python/developer-guide/) — Feature guides with code examples
- [How-To Guides](/kb.aspose.org/slides/python/) — Task-oriented articles
- [Getting Started](/docs.aspose.org/slides/python/getting-started/installation/) — Installation and first script
