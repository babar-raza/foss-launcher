---
page_role: toc
title: Developer Guide
description: >-
  Aspose.Slides FOSS for Python developer guide — shapes, text formatting, tables,
  connectors, fill types, visual effects, notes, comments, images, and document properties.
weight: 20
type: docs
---

This guide covers the core capabilities of Aspose.Slides FOSS for Python with runnable code examples for each feature area.

## In This Section

| Page | Description |
|------|-------------|
| [Features and Capabilities](/docs.aspose.org/slides/python/developer-guide/features/) | Full list of supported features: slides, shapes, text, fill, effects, 3D formatting, notes, comments, images, and document properties. |
| [Working with Images](/docs.aspose.org/slides/python/developer-guide/working-with-images/) | Embed images into slides as picture frames from file or bytes; control fill mode (stretch, tile). |
| [Working with Connectors](/docs.aspose.org/slides/python/developer-guide/working-with-connectors/) | Add bent, elbow, and straight connectors between shapes; set connection sites and line style. |
| [Working with 3D Effects](/docs.aspose.org/slides/python/developer-guide/working-with-3d-effects/) | Apply outer shadow, glow, blur, bevel, camera presets, light rigs, and materials to shapes. |
| [Working with Comments](/docs.aspose.org/slides/python/developer-guide/working-with-comments/) | Add threaded review comments and speaker notes; manage comment authors; read annotations. |

## API Entry Point

Every operation starts with a `Presentation` object. Always use it as a context manager:

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

# Open existing
with slides.Presentation("input.pptx") as prs:
    # work with prs
    prs.save("output.pptx", SaveFormat.PPTX)

# Create new
with slides.Presentation() as prs:
    # work with prs
    prs.save("new.pptx", SaveFormat.PPTX)
```

The context manager ensures that internal COM/XML resources are released when the block exits. Do not store a `Presentation` reference outside of the `with` block.

## Supported Output Format

The only supported save format is **PPTX** (`SaveFormat.PPTX`). Export to PDF, HTML, SVG, or image formats is not available in this edition.

## Key Classes

| Class / Enum | Import Path | Description |
|---|---|---|
| `Presentation` | `aspose.slides_foss` | Root container; use as context manager |
| `ShapeType` | `aspose.slides_foss` | Enum for shape types (RECTANGLE, ELLIPSE, …) |
| `FillType` | `aspose.slides_foss` | Enum for fill types (SOLID, GRADIENT, …) |
| `NullableBool` | `aspose.slides_foss` | Tri-state bool for formatting (TRUE, FALSE, NOT_DEFINED) |
| `SaveFormat` | `aspose.slides_foss.export` | Output format enum (only PPTX supported) |
| `Color` | `aspose.slides_foss.drawing` | ARGB color constructor |
| `PointF` | `aspose.slides_foss.drawing` | Float 2D point (used for comment positions) |

## Known Limitations

The following areas raise `NotImplementedError` in this edition:

- **Charts** — no chart creation or modification
- **SmartArt** — not supported
- **Animations and transitions** — slide transitions and object animations cannot be set
- **Export formats** — only PPTX save is supported; no PDF, HTML, SVG, or image export
- **Hyperlinks and action settings** — link objects are not modifiable
- **VBA macros and digital signatures** — not accessible

Unknown XML parts encountered during load are preserved verbatim on save — round-tripping never removes content the library does not yet understand.

## See Also

- [Getting Started](/docs.aspose.org/slides/python/getting-started/) — Installation and first script
- [API Reference](/reference.aspose.org/slides/python/) — Class and method reference
- [How-To Guides](/kb.aspose.org/slides/python/) — Task-oriented how-to articles
