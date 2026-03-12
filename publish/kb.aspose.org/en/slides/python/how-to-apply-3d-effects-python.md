---
page_role: howto_article
title: "How to Apply 3D Effects and Shadows to Shapes in Python"
description: "Apply 3D bevels, camera presets, light rigs, outer shadows, glow, and blur to PowerPoint shapes using Aspose.Slides FOSS for Python."
canonical: https://kb.aspose.org/slides/python/how-to-apply-3d-effects-python/
url: /kb.aspose.org/slides/python/how-to-apply-3d-effects-python/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "How to Apply 3D Effects and Shadows to Shapes in Python — Aspose.Slides FOSS"
keywords:
  - python pptx 3d effects
  - aspose slides shadow glow python
  - python powerpoint bevel camera
  - aspose slides foss 3d format python
  - python pptx outer shadow blur
type: howto_article
draft: false
weight: 90
---

Aspose.Slides FOSS provides two independent effect systems on every shape:

- **`shape.effect_format`** — 2D visual effects: outer shadow, glow, blur, soft edge
- **`shape.three_d_format`** — 3D appearance: bevel, camera perspective, light rig, material, depth

Both systems can be combined on the same shape.

---

## Prerequisites

```bash
pip install aspose-slides-foss
```

---

## Add an Outer Drop Shadow

```python
from aspose.slides_foss import ShapeType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(
        ShapeType.RECTANGLE, 100, 100, 300, 120
    )
    shape.add_text_frame("Shadowed Shape")

    ef = shape.effect_format
    ef.enable_outer_shadow_effect()
    ef.outer_shadow_effect.blur_radius = 10       # softness in points
    ef.outer_shadow_effect.direction = 315        # 315° = upper-left
    ef.outer_shadow_effect.distance = 8           # offset in points
    ef.outer_shadow_effect.shadow_color.color = Color.from_argb(128, 0, 0, 0)

    prs.save("shadow.pptx", SaveFormat.PPTX)
```

**Common `direction` values**: `0`=right, `45`=lower-right, `90`=down, `180`=left, `270`=up, `315`=upper-left.

---

## Add a Glow Effect

```python
from aspose.slides_foss import ShapeType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(
        ShapeType.ELLIPSE, 150, 100, 250, 250
    )

    ef = shape.effect_format
    ef.enable_glow_effect()
    ef.glow_effect.radius = 20
    ef.glow_effect.color.color = Color.gold

    prs.save("glow.pptx", SaveFormat.PPTX)
```

---

## Apply a Gaussian Blur

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(
        ShapeType.RECTANGLE, 100, 100, 350, 180
    )
    shape.effect_format.set_blur_effect(radius=10, grow=True)

    prs.save("blur.pptx", SaveFormat.PPTX)
```

`grow=True` expands the blur region beyond the shape boundary; `grow=False` clips the blur inside the shape.

---

## Apply a 3D Bevel

```python
from aspose.slides_foss import ShapeType, BevelPresetType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(
        ShapeType.RECTANGLE, 150, 150, 280, 120
    )
    shape.add_text_frame("3D Button")

    tdf = shape.three_d_format
    tdf.bevel_top.bevel_type = BevelPresetType.CIRCLE
    tdf.bevel_top.width = 12
    tdf.bevel_top.height = 6

    prs.save("bevel.pptx", SaveFormat.PPTX)
```

**`BevelPresetType` values**: `CIRCLE`, `RELAXED_INSET`, `COOL_SLANT`, `DIVOT`, `RIBLET`, `HARD_EDGE`, `SLOPE`, `CONVEX`

---

## 3D Bevel with Camera and Light Rig

```python
from aspose.slides_foss import (
    ShapeType, BevelPresetType, CameraPresetType,
    LightRigPresetType, LightingDirection, MaterialPresetType,
)
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(
        ShapeType.RECTANGLE, 150, 150, 280, 120
    )
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

---

## Combine Shadow and 3D Bevel

Both effect systems can be active simultaneously on the same shape:

```python
from aspose.slides_foss import (
    ShapeType, FillType, BevelPresetType,
    CameraPresetType, MaterialPresetType,
)
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(
        ShapeType.ROUNDED_RECTANGLE, 150, 150, 320, 130
    )
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

## Check and Remove Effects

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(
        ShapeType.RECTANGLE, 100, 100, 200, 100
    )
    ef = shape.effect_format

    ef.enable_outer_shadow_effect()
    ef.enable_glow_effect()
    print(f"Has effects: {not ef.is_no_effects}")  # True

    ef.disable_outer_shadow_effect()
    ef.disable_glow_effect()
    print(f"Has effects: {not ef.is_no_effects}")  # False
```

---

## See Also

- [Working with 3D Effects — Developer Guide](/docs.aspose.org/slides/python/developer-guide/working-with-3d-effects/)
- [EffectFormat and ThreeDFormat reference](/reference.aspose.org/slides/python/effects/)
- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
