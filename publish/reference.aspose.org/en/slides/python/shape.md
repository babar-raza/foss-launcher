---
page_role: reference_object_page
title: "Shape — Aspose.Slides FOSS for Python API Reference"
description: "API reference for the Shape base class in aspose-slides-foss. Position, size, rotation, fill, line, effect, and 3D format properties."
canonical: https://reference.aspose.org/slides/python/shape/
url: /reference.aspose.org/slides/python/shape/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "Shape Class — Aspose.Slides FOSS for Python API Reference"
keywords:
  - aspose slides shape python
  - python pptx shape class
  - python slide shape position size
  - aspose slides fill format python
  - aspose slides effect format python
type: reference_object_page
draft: false
weight: 30
---

`Shape` is the base class for all objects that can be placed on a slide: `AutoShape`, `PictureFrame`, `Table`, and `Connector`. All shape types share the properties documented here.

**Package**: `aspose.slides_foss`

Shapes are never instantiated directly — they are created via `slide.shapes.add_auto_shape()`, `add_table()`, `add_picture_frame()`, or `add_connector()`.

---

## Geometry Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `x` | `float` | Read/Write | Horizontal position in points from the slide left edge. |
| `y` | `float` | Read/Write | Vertical position in points from the slide top edge. |
| `width` | `float` | Read/Write | Shape width in points. |
| `height` | `float` | Read/Write | Shape height in points. |
| `rotation` | `float` | Read/Write | Clockwise rotation angle in degrees. |

All five geometry properties persist through save/reload cycles.

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 50, 300, 150)
    shape.rotation = 30   # rotate 30° clockwise

    print(f"Position: ({shape.x}, {shape.y})")
    print(f"Size: {shape.width} × {shape.height}")
    print(f"Rotation: {shape.rotation}°")
```

---

## Identity Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `name` | `str` | Read/Write | Shape name. Defaults to an auto-generated name like `"Rectangle 1"`. |
| `shape_type` | `ShapeType` | Read | The shape type enumeration value (e.g., `ShapeType.RECTANGLE`, `ShapeType.ELLIPSE`). |
| `shape_id` | `int` | Read | Unique integer ID within the presentation. |

---

## Formatting Properties

| Property | Type | Description |
|---|---|---|
| `fill_format` | `FillFormat` | Shape fill: solid color, gradient, pattern, picture, or no fill. |
| `line_format` | `LineFormat` | Stroke: width, dash style, color, arrowheads, join and cap styles. |
| `effect_format` | `EffectFormat` | Visual effects: outer shadow, inner shadow, glow, blur, soft edge, reflection. |
| `three_d_format` | `ThreeDFormat` | 3D properties: bevel, camera, light rig, material, extrusion depth. |

---

## Text

| Property / Method | Description |
|---|---|
| `text_frame` | `TextFrame \| None` — returns the text frame if the shape contains one; `None` for shapes without text (e.g., bare connectors). |
| `add_text_frame(text)` | Create and attach a `TextFrame` containing `text`. Returns the new `TextFrame`. |

---

## Usage Examples

### Shape Geometry and Name

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.ROUNDED_RECTANGLE, 50, 50, 250, 80)
    shape.name = "CalloutBox"
    shape.rotation = 0
    shape.add_text_frame("Key insight")
    prs.save("named-shape.pptx", SaveFormat.PPTX)
```

### Solid Fill

```python
from aspose.slides_foss import ShapeType, FillType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 150)
    shape.fill_format.fill_type = FillType.SOLID
    shape.fill_format.solid_fill_color.color = Color.from_argb(255, 30, 120, 200)
    prs.save("solid-fill.pptx", SaveFormat.PPTX)
```

### Gradient Fill

```python
from aspose.slides_foss import ShapeType, FillType, GradientShape
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 150)
    shape.fill_format.fill_type = FillType.GRADIENT
    gf = shape.fill_format.gradient_format
    gf.gradient_shape = GradientShape.LINEAR
    gf.linear_gradient_angle = 45
    gf.gradient_stops.add(0.0, Color.blue)
    gf.gradient_stops.add(1.0, Color.light_yellow)
    prs.save("gradient.pptx", SaveFormat.PPTX)
```

### Pattern Fill

```python
from aspose.slides_foss import ShapeType, FillType, PatternStyle
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 150)
    shape.fill_format.fill_type = FillType.PATTERN
    pf = shape.fill_format.pattern_format
    pf.pattern_style = PatternStyle.PERCENT50
    pf.fore_color.color = Color.dark_blue
    pf.back_color.color = Color.light_yellow
    prs.save("pattern.pptx", SaveFormat.PPTX)
```

### Outer Shadow Effect

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
    ef.outer_shadow_effect.direction = 315
    ef.outer_shadow_effect.distance = 8
    ef.outer_shadow_effect.shadow_color.color = Color.from_argb(128, 0, 0, 0)
    prs.save("shadow.pptx", SaveFormat.PPTX)
```

### 3D Bevel

```python
from aspose.slides_foss import ShapeType, BevelPresetType, CameraPresetType, LightRigPresetType, MaterialPresetType
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
    tdf.material = MaterialPresetType.METAL
    tdf.depth = 20
    prs.save("threed.pptx", SaveFormat.PPTX)
```

---

## See Also

- [Presentation class reference](/reference.aspose.org/slides/python/presentation/)
- [Slide class reference](/reference.aspose.org/slides/python/slide/)
- [TextFrame class reference](/reference.aspose.org/slides/python/textframe/)
- [FillFormat class reference](/reference.aspose.org/slides/python/fill-format/)
- [EffectFormat + ThreeDFormat reference](/reference.aspose.org/slides/python/effects/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [Developer Guide — Features](/docs.aspose.org/slides/python/developer-guide/features/)
