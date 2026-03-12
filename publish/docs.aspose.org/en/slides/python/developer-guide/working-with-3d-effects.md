---
page_role: howto_article
title: "Working with 3D Effects and Visual Effects — Aspose.Slides FOSS for Python"
description: "Apply 3D bevels, camera presets, light rigs, and visual effects (shadow, glow, blur) to shapes in PowerPoint using Aspose.Slides FOSS for Python."
canonical: https://docs.aspose.org/slides/python/developer-guide/working-with-3d-effects/
url: /docs.aspose.org/slides/python/developer-guide/working-with-3d-effects/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "3D Effects and Visual Effects in PowerPoint — Aspose.Slides FOSS for Python"
keywords:
  - aspose slides 3d effects python
  - python pptx bevel shadow glow
  - python powerpoint 3d format
  - aspose slides effect format python
  - python pptx outer shadow blur
type: howto_article
draft: false
weight: 50
---

Aspose.Slides FOSS for Python provides two separate effect systems accessible on every shape:

- **`EffectFormat`** (`shape.effect_format`) — 2D visual effects: shadow, glow, soft edge, blur, reflection
- **`ThreeDFormat`** (`shape.three_d_format`) — 3D appearance: bevel, camera projection, light rig, material, extrusion depth

Both persist through save/reload cycles.

---

## Visual Effects (EffectFormat)

### Outer Drop Shadow

```python
from aspose.slides_foss import ShapeType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 300, 120)
    shape.add_text_frame("Shadowed Text")

    ef = shape.effect_format
    ef.enable_outer_shadow_effect()
    ef.outer_shadow_effect.blur_radius = 10      # softness in points
    ef.outer_shadow_effect.direction = 315       # angle: 315° = upper-left cast
    ef.outer_shadow_effect.distance = 8          # offset in points
    ef.outer_shadow_effect.shadow_color.color = Color.from_argb(128, 0, 0, 0)  # semi-transparent black

    prs.save("shadow.pptx", SaveFormat.PPTX)
```

Common `direction` values: `0` = right, `45` = lower-right, `90` = down, `270` = up, `315` = upper-left.

### Glow Effect

```python
from aspose.slides_foss import ShapeType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.ELLIPSE, 150, 100, 200, 200)

    ef = shape.effect_format
    ef.enable_glow_effect()
    ef.glow_effect.radius = 15
    ef.glow_effect.color.color = Color.gold

    prs.save("glow.pptx", SaveFormat.PPTX)
```

### Soft Edge (Feathered Border)

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 350, 180)

    ef = shape.effect_format
    ef.enable_soft_edge_effect()
    ef.soft_edge_effect.radius = 12   # feather radius in points

    prs.save("soft-edge.pptx", SaveFormat.PPTX)
```

### Blur

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 350, 180)

    shape.effect_format.set_blur_effect(radius=8, grow=True)

    prs.save("blur.pptx", SaveFormat.PPTX)
```

### Checking and Removing Effects

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 200, 100)
    ef = shape.effect_format

    ef.enable_outer_shadow_effect()
    ef.enable_glow_effect()
    print(f"Has effects: {not ef.is_no_effects}")  # True

    ef.disable_outer_shadow_effect()
    ef.disable_glow_effect()
    print(f"Has effects: {not ef.is_no_effects}")  # False
```

---

## 3D Formatting (ThreeDFormat)

### Bevel Effect

```python
from aspose.slides_foss import ShapeType, BevelPresetType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 150, 150, 250, 120)
    shape.add_text_frame("3D Button")

    tdf = shape.three_d_format
    tdf.bevel_top.bevel_type = BevelPresetType.CIRCLE
    tdf.bevel_top.width = 12
    tdf.bevel_top.height = 6

    prs.save("bevel.pptx", SaveFormat.PPTX)
```

**BevelPresetType values**: `CIRCLE`, `RELAXED_INSET`, `COOL_SLANT`, `DIVOT`, `RIBLET`, `HARD_EDGE`, `SLOPE`, `CONVEX`

### Camera Preset

```python
from aspose.slides_foss import ShapeType, BevelPresetType, CameraPresetType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 150, 150, 250, 120)
    tdf = shape.three_d_format
    tdf.bevel_top.bevel_type = BevelPresetType.CIRCLE
    tdf.bevel_top.width = 10
    tdf.camera.camera_type = CameraPresetType.PERSPECTIVE_ABOVE
    prs.save("camera.pptx", SaveFormat.PPTX)
```

### Light Rig and Material

```python
from aspose.slides_foss import (
    ShapeType, BevelPresetType, CameraPresetType,
    LightRigPresetType, LightingDirection, MaterialPresetType,
)
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 150, 150, 250, 120)
    shape.add_text_frame("Metal Button")

    tdf = shape.three_d_format
    tdf.bevel_top.bevel_type = BevelPresetType.CIRCLE
    tdf.bevel_top.width = 10
    tdf.bevel_top.height = 5
    tdf.camera.camera_type = CameraPresetType.PERSPECTIVE_ABOVE
    tdf.light_rig.light_type = LightRigPresetType.BALANCED
    tdf.light_rig.direction = LightingDirection.TOP
    tdf.material = MaterialPresetType.METAL
    tdf.depth = 20

    prs.save("3d-metal.pptx", SaveFormat.PPTX)
```

**MaterialPresetType values**: `STANDARD`, `WARM`, `COOL`, `PLASTIC`, `METAL`, `MATTE`, `WIREFRAME`

---

## Combining 2D and 3D Effects

You can apply both `effect_format` and `three_d_format` to the same shape:

```python
from aspose.slides_foss import (
    ShapeType, FillType, BevelPresetType, CameraPresetType, MaterialPresetType,
)
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.ROUNDED_RECTANGLE, 150, 150, 300, 120)
    shape.add_text_frame("Premium Card")

    # Solid fill
    shape.fill_format.fill_type = FillType.SOLID
    shape.fill_format.solid_fill_color.color = Color.from_argb(255, 30, 80, 180)

    # 3D bevel
    tdf = shape.three_d_format
    tdf.bevel_top.bevel_type = BevelPresetType.CIRCLE
    tdf.bevel_top.width = 8
    tdf.camera.camera_type = CameraPresetType.PERSPECTIVE_ABOVE
    tdf.material = MaterialPresetType.PLASTIC

    # Drop shadow
    ef = shape.effect_format
    ef.enable_outer_shadow_effect()
    ef.outer_shadow_effect.blur_radius = 12
    ef.outer_shadow_effect.direction = 270
    ef.outer_shadow_effect.distance = 6
    ef.outer_shadow_effect.shadow_color.color = Color.from_argb(80, 0, 0, 0)

    prs.save("premium-card.pptx", SaveFormat.PPTX)
```

---

## See Also

- [How to Apply 3D Effects in Python](/kb.aspose.org/slides/python/how-to-apply-3d-effects-python/)
- [EffectFormat and ThreeDFormat reference](/reference.aspose.org/slides/python/effects/)
- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [Developer Guide — Features](/docs.aspose.org/slides/python/developer-guide/features/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
