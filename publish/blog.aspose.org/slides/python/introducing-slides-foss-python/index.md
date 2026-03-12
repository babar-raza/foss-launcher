---
canonical: https://blog.aspose.org/slides/python/introducing-slides-foss-python/
canonical_import: aspose_slides_foss
date: '2026-03-11T16:00:00Z'
dateModified: '2026-03-11T16:00:00Z'
datePublished: '2026-03-11T16:00:00Z'
description: Aspose.Slides FOSS for Python is a free, open-source library for creating
  and editing PowerPoint presentations without Microsoft Office. MIT licensed, pure Python,
  no API key required.
display_name: Aspose.Slides
family: slides
keywords:
- python powerpoint
- python pptx library
- create pptx python
- open source powerpoint python
- aspose slides foss python
- python presentation library
lastmod: '2026-03-11T16:00:00Z'
page_role: blog_announcement
platform: python
reading_time: 3
robots: index, follow
seoTitle: Introducing Aspose.Slides FOSS for Python — Open-Source PPTX Library
slug: introducing-slides-foss-python
title: Introducing Aspose.Slides FOSS for Python
type: blog_announcement
url: /blog.aspose.org/slides/python/introducing-slides-foss-python/
weight: 10
---

## Introduction

Aspose.Slides FOSS for Python is now available on PyPI — a free, MIT-licensed library for creating, reading, and editing PowerPoint `.pptx` files entirely in Python, with no dependency on Microsoft Office or any proprietary runtime.

The library is designed for developers who need to generate or manipulate presentation files programmatically: automating slide decks from data, extracting text and metadata from uploaded PPTX files, building presentation-based reporting pipelines, or embedding presentation creation into web applications. Because `aspose-slides-foss` is pure Python with only `lxml` as a dependency, it deploys identically on Windows, macOS, Linux, and Docker containers.

## Key Features

- **Full round-trip PPTX support** — Open any `.pptx` file, modify its content, and save it back without losing unknown XML parts that the library does not yet understand.
- **Slides management** — Add, remove, and iterate slides using `prs.slides`; the presentation starts with one blank slide after `slides.Presentation()`.
- **AutoShapes, Tables, and Connectors** — Insert shapes via `slide.shapes.add_auto_shape()`, tabular data via `slide.shapes.add_table()`, and visual connectors between shapes via `slide.shapes.add_connector()`.
- **Rich text formatting** — Format text at character level with `PortionFormat`: font size, bold, italic, underline, and ARGB color via `FillType.SOLID` and `Color.from_argb()`.
- **Fill types** — Apply `FillType.SOLID`, `GRADIENT`, `PATTERN`, or `PICTURE` fills to any shape.
- **Visual effects** — Outer shadow, glow, soft edge, blur, reflection, and inner shadow via `shape.effect_format`.
- **3D formatting** — Bevel, camera, light rig, material, and extrusion depth via `shape.three_d_format`.
- **Speaker notes** — Attach notes text to each slide via `notes_slide_manager.add_notes_slide()`.
- **Threaded comments** — Add comments with author metadata and slide position.
- **Embedded images** — Embed from file path, bytes, or `io.BytesIO` stream.
- **Document properties** — Read and write core, app, and custom properties.

## Getting Started

Install from PyPI. Python 3.10 or later is required; `lxml` is installed automatically.

```bash
pip install aspose-slides-foss
```

Create your first presentation with a shape and save it:

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat
from aspose.slides_foss import ShapeType

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 400, 120)
    shape.add_text_frame("Hello from Aspose.Slides FOSS!")
    prs.save("hello.pptx", SaveFormat.PPTX)
```

Always use `Presentation` inside a `with` block — this ensures all internal resources are released when the block exits.

## Text Formatting Example

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, NullableBool, FillType
from aspose.slides_foss.drawing import Color
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 500, 150)
    tf = shape.add_text_frame("Bold heading in corporate blue")
    fmt = tf.paragraphs[0].portions[0].portion_format
    fmt.font_height = 28
    fmt.font_bold = NullableBool.TRUE
    fmt.fill_format.fill_type = FillType.SOLID
    fmt.fill_format.solid_fill_color.color = Color.from_argb(255, 0, 70, 127)
    prs.save("formatted.pptx", SaveFormat.PPTX)
```

## Current Limitations

The following areas raise `NotImplementedError` in this release:

- Charts, SmartArt, and OLE objects
- Animations and slide transitions
- Export to PDF, HTML, SVG, or image formats
- Hyperlinks, action settings, VBA macros, and digital signatures

Unknown XML parts encountered during load are preserved verbatim on save, so PPTX files produced by other tools round-trip safely.

## See Also

- [Installation Guide](/docs.aspose.org/slides/python/getting-started/installation/)
- [Features Overview](/docs.aspose.org/slides/python/developer-guide/features/)
- [How to Create Presentations](/kb.aspose.org/slides/python/how-to-create-presentations-python/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [API Reference](/reference.aspose.org/slides/python/)
