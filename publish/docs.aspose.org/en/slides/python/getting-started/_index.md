---
page_role: toc
title: Getting Started
description: >-
  Get started with Aspose.Slides FOSS for Python — installation, license details,
  and your first presentation creation script.
weight: 10
type: docs
---

This section covers everything you need to set up Aspose.Slides FOSS for Python and write your first presentation.

## In This Section

| Page | Description |
|------|-------------|
| [Installation](/docs.aspose.org/slides/python/getting-started/installation/) | Install `aspose-slides-foss` via pip, set up a virtual environment, verify the installation, and run a quick start script. |
| [License](/docs.aspose.org/slides/python/getting-started/license/) | MIT License details — free for any use, no API key, no registration required. |

## Quick Install

```bash
pip install aspose-slides-foss
```

Requires Python 3.10 or later. The `lxml` dependency is installed automatically.

## Minimal Working Example

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat
from aspose.slides_foss import ShapeType

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 400, 120)
    shape.add_text_frame("Hello, Aspose.Slides FOSS!")
    prs.save("output.pptx", SaveFormat.PPTX)
```

Always use `Presentation` inside a `with` block to ensure proper cleanup.

## Next Steps

After installing, see the [Developer Guide](/docs.aspose.org/slides/python/developer-guide/) for feature guides covering shapes, text formatting, tables, fill, effects, speaker notes, comments, and document properties.
