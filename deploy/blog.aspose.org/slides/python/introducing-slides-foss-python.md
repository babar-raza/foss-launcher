---
canonical: https://blog.aspose.org/slides/python/introducing-slides-foss-python/
canonical_import: aspose.slides
code_import: aspose.slides
date: '2026-03-24T16:56:57Z'
dateModified: '2026-03-24T16:56:57Z'
datePublished: '2026-03-24T16:56:57Z'
description: Aspose.Slides removes that friction, letting you generate, modify, and
  export PowerPoint files directly in your scripts — no GUI required.
display_name: Aspose.Slides
family: slides
keywords:
- slides python
- python slides for beginners
- python slides ppt
- python slides pdf
- slide python pptx
- python slides for kids
- python slides library
- python slides github
lastmod: '2026-03-24T16:56:57Z'
page_role: blog_announcement
platform: python
reading_time: 1
robots: index, follow
seoTitle: The library supports 3D shape formatting including bevel,
slug: introducing-slides-foss-python
title: The library supports 3D shape formatting including bevel, camera, light rig,
  ...
type: blog_announcement
url: /blog.aspose.org/slides/python/introducing-slides-foss-python/
weight: 16
---

## Introduction

Creating professional presentations programmatically in Python often means wrestling with complex APIs or relying on heavy desktop suites. Aspose.Slides removes that friction, letting you generate, modify, and export PowerPoint files directly in your scripts — no GUI required.

You can now apply rich 3D formatting to shapes — including bevels, cameras, light rigs, materials, and extrusion `depth` — and those settings persist reliably across save/reload cycles. For example, setting `a` circular bevel on `a` rectangle shape and saving the file preserves all 3D properties when reopened.

Line formatting is equally precise: control width, dash style, arrows, joins, and `alignment` — all with stable behavior after round-tripping. Threaded `comments` with authors, timestamps, and positions are also fully supported, enabling collaborative review workflows in automated slide generation.

```python
from aspose.slides import Presentation, ShapeType, BevelPresetType, CameraPresetType

pres = Presentation()
slide = pres.slides[0]
shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 200, 100)
shape.three_d_format.bevel_top.bevel_type = BevelPresetType.CIRCLE
shape.three_d_format.bevel_top.width = 10
shape.three_d_format.bevel_top.height = 5
shape.three_d_format.camera.camera_type = CameraPresetType.PERSPECTIVE_ABOVE
pres.save("output.pptx")
```

## Key Highlights

You're building presentations programmatically and need precise control over visuals — not just text, but 3D shapes, custom fills, and polished formatting. Aspose.Slides for Python gives you that control without requiring PowerPoint installed.

- Add, remove, clone, reorder, and iterate slides using the `ISlideCollection` interface — ideal for dynamic slide generation from data sources.
- Apply solid, gradient, pattern, or picture fills to shapes and text via `FillFormat`, supporting rich visual styling and branding consistency.
- Configure 3D shape effects like bevels, cameras, light rigs, and extrusion depth using `BevelPresetType` and related 3D properties.
- Format lines with custom width, dash style, arrows, and alignment through `ILineFormat` for clean connectors and borders.
- Apply text effects including outer shadow, glow, soft edge, blur, reflection, and inner shadow using `EffectFormat`.
- Control text formatting at character, paragraph, and text frame levels — including bullets, font height, bold, and color — using `BasePortionFormat` and `BulletFormat`.
- Embed images from file, bytes, or stream via `IImage`, then add them to presentations using `Presentation.images.add_image()`.
- Set core, app, and custom document properties to manage metadata like author, title, and custom fields for enterprise workflows.

```python
from aspose.slides import ShapeType, FillType
from aspose.slides import Color
import aspose.slides as slides
from aspose.slides import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 150)
    shape.fill_format.fill_type = FillType.SOLID
    shape.fill_format.solid_fill_color.color = Color.from_argb(255, 30, 120, 200)
    prs.save("fill.pptx", SaveFormat.PPTX)
```

## Getting Started

You want to `add` polished 3D effects to shapes in your PowerPoint presentations — like beveled edges, dynamic lighting, and realistic shadows — all from Python. Aspose.Slides makes this possible without opening PowerPoint, and it preserves those effects when you save and reload the file.

```python
from aspose.slides import Presentation, ShapeType
from aspose.slides import Color

# Create a new presentation and add a rectangle shape
pres = Presentation()
slide = pres.slides[0]
shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 150, 100, 300, 150)

# Apply outer shadow effect with blur and color
ef = shape.effect_format
ef.enable_outer_shadow_effect()
shadow = ef.outer_shadow_effect
shadow.blur_radius = 8
shadow.direction = 225
shadow.distance = 6
shadow.shadow_color.color = Color.from_argb(100, 0, 0, 0)

# Save the presentation with effects intact
pres.save("output.pptx", None)
pres.dispose()
```

Document properties like title, `author`, and custom fields also survive round-trips. This matters when you generate reports or presentations programmatically and need metadata to persist across generations.

```python
from aspose.slides import Presentation

pres = Presentation()
props = pres.document_properties
props.title = "Q3 Sales Review"
props.author = "Jane Smith"
props.keywords = "sales, q3, 2024"
pres.document_properties.set_custom_property_value("Region", "EMEA")

pres.save("report.pptx", None)
pres.dispose()
```

## See Also

- [Explore 3D shape formatting](/products.aspose.org/slides/_index/)
- [Discover advanced 3D capabilities](/blog.aspose.org/slides/python/slides-key-features/)
- [Create presentations with 3D effects](/docs.aspose.org/slides/python/developer-guide/presentation-creation/)
- [Work with 3D slide elements](/docs.aspose.org/slides/python/developer-guide/slide-manipulation/)
- [Convert presentations with 3D support](/kb.aspose.org/slides/python/how-to-convert-png-to-pptx-python/)
