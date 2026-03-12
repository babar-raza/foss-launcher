---
canonical: https://products.aspose.org/slides/_index/
canonical_import: aspose_slides_foss
date: '2026-03-11T16:00:00Z'
dateModified: '2026-03-11T16:00:00Z'
datePublished: '2026-03-11T16:00:00Z'
description: Aspose.Slides FOSS is an open-source library for creating, reading, and editing PowerPoint presentations. Available for Python — MIT licensed, no Office dependency.
display_name: Aspose.Slides FOSS
family: slides
keywords:
- python powerpoint
- python pptx
- python presentation
- aspose slides python
- open source powerpoint python
- create pptx python
lastmod: '2026-03-11T16:00:00Z'
page_role: landing
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Slides FOSS | Guide
slug: _index
title: Aspose.Slides FOSS
type: landing
url: /products.aspose.org/slides/_index/
weight: 1
---

## Overview

Aspose.Slides FOSS is a Python library for creating, reading, and modifying PowerPoint `.pptx` files without requiring Microsoft Office. It provides a lightweight, MIT-licensed alternative for programmatic presentation manipulation in production environments.

Key capabilities include managing slides — add, remove, clone, and reorder them — inserting shapes such as AutoShapes, PictureFrames, Tables, and Connectors, formatting text at paragraph and character level, applying fill types (solid, gradient, pattern, picture), and working with visual effects including shadow, glow, blur, and reflection. Per-slide speaker notes, threaded comments, embedded images, and document properties are all fully supported.

## Key Features

- **Presentation I/O** — Open and save `.pptx` files with full round-trip fidelity; unknown XML parts are preserved verbatim.
- **Slides** — Add, remove, clone, and iterate slides using `prs.slides`.
- **Shapes** — Insert AutoShapes, PictureFrames, Tables, and Connectors via `slide.shapes.add_auto_shape()`.
- **Text** — Format text with `PortionFormat`: font size, bold, italic, underline, and color at character granularity.
- **Fill** — Apply `FillType.SOLID`, `GRADIENT`, `PATTERN`, or `PICTURE` fills to shapes.
- **Effects** — Outer shadow, glow, soft edge, blur, reflection, and inner shadow.
- **Notes** — Attach speaker notes to any slide via `notes_slide_manager`.
- **Comments** — Add threaded comments with author metadata and timestamps.
- **Images** — Embed images from file paths, byte streams, or `io.BytesIO` objects.
- **Document Properties** — Read and write core, app, and custom properties.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat
from aspose.slides_foss import ShapeType

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 100)
    shape.add_text_frame("Hello, Aspose.Slides FOSS!")
    prs.save("output.pptx", SaveFormat.PPTX)
```

## Quick Start

Install Aspose.Slides FOSS from PyPI. Python 3.10 or later is required; `lxml` is installed automatically as a dependency.

```bash
pip install aspose-slides-foss
```

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

# Open an existing presentation
with slides.Presentation("input.pptx") as prs:
    print(f"Slides: {len(prs.slides)}")
    prs.save("output.pptx", SaveFormat.PPTX)
```

## See Also

- [Installation guide](/docs.aspose.org/slides/python/getting-started/installation/)
- [Developer guide](/docs.aspose.org/slides/python/developer-guide/)
- [API reference](/reference.aspose.org/slides/python/)
- [How-to guides](/kb.aspose.org/slides/python/)
