---
page_role: reference_object_page
title: "EffectFormat and ThreeDFormat — Aspose.Slides FOSS for Python API Reference"
description: "API reference for EffectFormat and ThreeDFormat in aspose-slides-foss. Outer shadow, glow, blur, soft edge, reflection, bevel, camera, light rig, and material."
canonical: https://reference.aspose.org/slides/python/effects/
url: /reference.aspose.org/slides/python/effects/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "EffectFormat and ThreeDFormat — Aspose.Slides FOSS for Python API Reference"
keywords:
  - aspose slides effect format python
  - python pptx shadow glow blur
  - aspose slides 3d format python
  - python pptx bevel camera light rig
  - aspose slides foss effects python
type: reference_object_page
draft: false
weight: 60
---

Aspose.Slides FOSS provides two separate format objects for advanced shape styling: `EffectFormat` for 2D visual effects and `ThreeDFormat` for three-dimensional appearance.

**Package**: `aspose.slides_foss`

Both are accessed from any `Shape` object:

```python
ef = shape.effect_format     # EffectFormat
tdf = shape.three_d_format   # ThreeDFormat
```

---

## EffectFormat

`EffectFormat` controls effects rendered in the same plane as the slide: drop shadows, glows, soft edges, blurs, and reflections.

### Properties

| Property | Type | Description |
|---|---|---|
| `is_no_effects` | `bool` | `True` when no effects are active. |
| `outer_shadow_effect` | `OuterShadow \| None` | Drop shadow outside the shape boundary. `None` until `enable_outer_shadow_effect()` is called. |
| `inner_shadow_effect` | `InnerShadow \| None` | Shadow cast inside the shape boundary. `None` until enabled. |
| `glow_effect` | `Glow \| None` | Colored glow around the shape edge. `None` until `enable_glow_effect()` is called. |
| `blur_effect` | `Blur \| None` | Gaussian blur of the shape. `None` until `set_blur_effect()` is called. |
| `soft_edge_effect` | `SoftEdge \| None` | Feathered edge fade. `None` until `enable_soft_edge_effect()` is called. |
| `reflection_effect` | `Reflection \| None` | Mirror reflection below the shape. `None` until enabled. |

### Enable / Disable Methods

| Method | Description |
|---|---|
| `enable_outer_shadow_effect()` | Create and attach an `OuterShadow` with default settings. |
| `disable_outer_shadow_effect()` | Remove the outer shadow. |
| `enable_glow_effect()` | Create and attach a `Glow` with default settings. |
| `disable_glow_effect()` | Remove the glow. |
| `enable_soft_edge_effect()` | Create and attach a `SoftEdge`. |
| `disable_soft_edge_effect()` | Remove the soft edge. |
| `set_blur_effect(radius, grow)` | Apply a Gaussian blur. `radius` is in points; `grow` (bool) controls whether the blur area expands the shape bounds. |

---

## OuterShadow Properties

| Property | Type | Description |
|---|---|---|
| `blur_radius` | `float` | Shadow softness in points. Larger = softer edge. |
| `direction` | `float` | Shadow angle in degrees (0 = right, 90 = down, 315 = upper-left). |
| `distance` | `float` | Offset distance in points between shape and shadow center. |
| `shadow_color` | `ColorFormat` | Shadow color with alpha. Use `Color.from_argb(alpha, r, g, b)` for semi-transparent shadows. |

---

## Glow Properties

| Property | Type | Description |
|---|---|---|
| `radius` | `float` | Glow spread radius in points. |
| `color` | `ColorFormat` | Glow color. |

---

## SoftEdge Properties

| Property | Type | Description |
|---|---|---|
| `radius` | `float` | Feather radius in points. |

---

## Blur Properties

| Property | Type | Description |
|---|---|---|
| `radius` | `float` | Blur radius in points. |

---

## ThreeDFormat

`ThreeDFormat` gives a flat shape a three-dimensional appearance by defining bevel, camera perspective, light source, material, and extrusion depth.

### Properties

| Property | Type | Description |
|---|---|---|
| `bevel_top` | `ShapeBevel` | Bevel applied to the top (front) face of the shape. |
| `bevel_bottom` | `ShapeBevel` | Bevel applied to the bottom (back) face. |
| `camera` | `Camera` | Camera position/projection for the 3D view. |
| `light_rig` | `LightRig` | Light source preset and direction. |
| `material` | `MaterialPresetType` | Surface material appearance (e.g., `METAL`, `PLASTIC`, `MATTE`). |
| `depth` | `float` | Extrusion depth in points. |
| `contour_width` | `float` | Width of the shape contour/edge highlight in points. |
| `contour_color` | `ColorFormat` | Color of the contour. |

### ShapeBevel Properties

| Property | Type | Description |
|---|---|---|
| `bevel_type` | `BevelPresetType` | Bevel shape preset (e.g., `CIRCLE`, `RELAXED_INSET`, `COOL_SLANT`, `DIVOT`, `HARD_EDGE`, `SLOPE`, `CONVEX`). |
| `width` | `float` | Horizontal bevel size in points. |
| `height` | `float` | Vertical bevel size in points. |

### Camera Properties

| Property | Type | Description |
|---|---|---|
| `camera_type` | `CameraPresetType` | Preset camera position (e.g., `PERSPECTIVE_ABOVE`, `ISOMETRIC_LEFT_UP`, `ORTHOGRAPHIC_FRONT`). |

### LightRig Properties

| Property | Type | Description |
|---|---|---|
| `light_type` | `LightRigPresetType` | Light preset (e.g., `BALANCED`, `THREE_PT`, `SOFT`, `HARSH`, `FLOOD`). |
| `direction` | `LightingDirection` | Direction the light comes from (e.g., `TOP`, `BOTTOM`, `LEFT`, `RIGHT`, `TOP_LEFT`). |

### MaterialPresetType Values

| Value | Appearance |
|---|---|
| `STANDARD` | Default matte-like surface |
| `WARM` | Warm tonal surface |
| `COOL` | Cool tonal surface |
| `PLASTIC` | Smooth plastic sheen |
| `METAL` | Metallic reflective surface |
| `MATTE` | Flat non-reflective |
| `WIREFRAME` | Wireframe outline only |

---

## Usage Examples

### Outer Drop Shadow

```python
from aspose.slides_foss import ShapeType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 250, 100)
    ef = shape.effect_format
    ef.enable_outer_shadow_effect()
    ef.outer_shadow_effect.blur_radius = 10
    ef.outer_shadow_effect.direction = 315   # upper-left shadow
    ef.outer_shadow_effect.distance = 8
    ef.outer_shadow_effect.shadow_color.color = Color.from_argb(128, 0, 0, 0)
    prs.save("shadow.pptx", SaveFormat.PPTX)
```

### Gold Glow Effect

```python
from aspose.slides_foss import ShapeType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.ELLIPSE, 100, 100, 200, 200)
    ef = shape.effect_format
    ef.enable_glow_effect()
    ef.glow_effect.radius = 15
    ef.glow_effect.color.color = Color.gold
    prs.save("glow.pptx", SaveFormat.PPTX)
```

### Soft Edge Fade

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 300, 150)
    ef = shape.effect_format
    ef.enable_soft_edge_effect()
    ef.soft_edge_effect.radius = 12
    prs.save("soft-edge.pptx", SaveFormat.PPTX)
```

### 3D Bevel with Metal Material

```python
from aspose.slides_foss import (
    ShapeType, BevelPresetType, CameraPresetType,
    LightRigPresetType, LightingDirection, MaterialPresetType,
)
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 200, 100)
    tdf = shape.three_d_format
    tdf.bevel_top.bevel_type = BevelPresetType.CIRCLE
    tdf.bevel_top.width = 10
    tdf.bevel_top.height = 5
    tdf.camera.camera_type = CameraPresetType.PERSPECTIVE_ABOVE
    tdf.light_rig.light_type = LightRigPresetType.BALANCED
    tdf.light_rig.direction = LightingDirection.TOP
    tdf.material = MaterialPresetType.METAL
    tdf.depth = 20
    prs.save("3d-bevel.pptx", SaveFormat.PPTX)
```

### Combining Effects

```python
from aspose.slides_foss import ShapeType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.ROUNDED_RECTANGLE, 100, 100, 280, 120)
    ef = shape.effect_format

    # Add both shadow and glow simultaneously
    ef.enable_outer_shadow_effect()
    ef.outer_shadow_effect.blur_radius = 8
    ef.outer_shadow_effect.direction = 270  # downward shadow
    ef.outer_shadow_effect.distance = 5
    ef.outer_shadow_effect.shadow_color.color = Color.from_argb(100, 0, 0, 0)

    ef.enable_glow_effect()
    ef.glow_effect.radius = 8
    ef.glow_effect.color.color = Color.from_argb(180, 0, 120, 255)

    print(f"Has effects: {not ef.is_no_effects}")
    prs.save("combined-effects.pptx", SaveFormat.PPTX)
```

---

## See Also

- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [FillFormat class reference](/reference.aspose.org/slides/python/fill-format/)
- [Slides Python API Reference home](/reference.aspose.org/slides/python/)
- [How to Apply 3D Effects](/kb.aspose.org/slides/python/how-to-apply-3d-effects-python/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [Developer Guide — Features](/docs.aspose.org/slides/python/developer-guide/features/)
