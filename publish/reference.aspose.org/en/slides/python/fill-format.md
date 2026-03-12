---
page_role: reference_object_page
title: "FillFormat — Aspose.Slides FOSS for Python API Reference"
description: "API reference for FillFormat in aspose-slides-foss. Solid, gradient, pattern, picture, and no-fill types with full code examples."
canonical: https://reference.aspose.org/slides/python/fill-format/
url: /reference.aspose.org/slides/python/fill-format/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "FillFormat Class — Aspose.Slides FOSS for Python API Reference"
keywords:
  - aspose slides fill format python
  - python pptx solid fill
  - python pptx gradient fill
  - python pptx pattern fill
  - aspose slides color python
type: reference_object_page
draft: false
weight: 50
---

`FillFormat` controls how a shape's interior (or a text portion's color) is filled. It is accessed via `shape.fill_format` or `portion.portion_format.fill_format`.

**Package**: `aspose.slides_foss`

The fill type is selected by setting `fill_format.fill_type` to one of the `FillType` enumeration values. Only the sub-object matching the active `fill_type` is used; other sub-objects are ignored.

---

## FillType Enumeration

| Value | Description |
|---|---|
| `FillType.SOLID` | Uniform color fill. Configure via `solid_fill_color`. |
| `FillType.GRADIENT` | Smooth color transition. Configure via `gradient_format`. |
| `FillType.PATTERN` | Repeating geometric pattern. Configure via `pattern_format`. |
| `FillType.PICTURE` | Image fill. Configure via `picture_fill_format`. |
| `FillType.NO_FILL` | Transparent — no fill is applied. |

---

## FillFormat Properties

| Property | Type | Description |
|---|---|---|
| `fill_type` | `FillType` | Active fill type. Set this before configuring sub-objects. |
| `solid_fill_color` | `ColorFormat` | Color used when `fill_type == FillType.SOLID`. |
| `gradient_format` | `GradientFormat` | Gradient settings when `fill_type == FillType.GRADIENT`. |
| `pattern_format` | `PatternFormat` | Pattern settings when `fill_type == FillType.PATTERN`. |
| `picture_fill_format` | `PictureFillFormat` | Image settings when `fill_type == FillType.PICTURE`. |

---

## ColorFormat

A `ColorFormat` wraps an ARGB color value.

| Property | Type | Description |
|---|---|---|
| `color` | `Color` | The ARGB color. Assign a `Color` instance. |

**Color construction**:

```python
from aspose.slides_foss.drawing import Color

# From ARGB components (alpha, red, green, blue — each 0–255)
c = Color.from_argb(255, 30, 120, 200)   # opaque blue

# Named preset colors
Color.red        # ARGB(255, 255, 0, 0)
Color.blue       # ARGB(255, 0, 0, 255)
Color.dark_blue
Color.light_yellow
Color.gold
Color.white
Color.black
```

---

## GradientFormat

| Property | Type | Description |
|---|---|---|
| `gradient_shape` | `GradientShape` | Shape of the gradient: `LINEAR`, `RECTANGLE`, `RADIAL`, `PATH`. |
| `linear_gradient_angle` | `float` | Angle in degrees for linear gradients (0 = left-to-right, 90 = top-to-bottom). |
| `gradient_stops` | `GradientStopCollection` | Ordered list of color stops. Each stop has a position (0.0–1.0) and a color. |

**GradientStopCollection Methods**:

| Method | Description |
|---|---|
| `add(position, color)` | Append a stop at `position` (float 0.0–1.0) with the given `Color`. |

---

## PatternFormat

| Property | Type | Description |
|---|---|---|
| `pattern_style` | `PatternStyle` | The geometric tile pattern (50+ styles, e.g., `PERCENT50`, `DARK_DOWNWARD_DIAGONAL`). |
| `fore_color` | `ColorFormat` | Foreground color (the pattern lines/dots). |
| `back_color` | `ColorFormat` | Background color (the space between pattern lines). |

---

## PictureFillFormat

| Property | Type | Description |
|---|---|---|
| `picture_fill_mode` | `PictureFillMode` | How the image fills the shape: `STRETCH` (scales to fill), `TILE`, `TILE_FLIP`. |
| `picture` | `PictureFillFormatPicture` | Holds the embedded image. Set `picture.image` to an `Image` from `prs.images.add_image(bytes)`. |

---

## Usage Examples

### Solid Fill

```python
from aspose.slides_foss import ShapeType, FillType
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 150)
    shape.fill_format.fill_type = FillType.SOLID
    shape.fill_format.solid_fill_color.color = Color.from_argb(255, 0, 128, 255)
    prs.save("solid.pptx", SaveFormat.PPTX)
```

### Linear Gradient (Blue → Red, 45°)

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
    gf.gradient_stops.add(1.0, Color.red)
    prs.save("gradient.pptx", SaveFormat.PPTX)
```

### Pattern Fill (50% Dark Blue on Light Yellow)

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

### Picture Fill (Stretched Image)

```python
from aspose.slides_foss import ShapeType, FillType, PictureFillMode
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    # Load image bytes from a file
    with open("background.png", "rb") as f:
        img_bytes = f.read()
    img = prs.images.add_image(img_bytes)

    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 0, 0, 720, 540)
    shape.fill_format.fill_type = FillType.PICTURE
    shape.fill_format.picture_fill_format.picture_fill_mode = PictureFillMode.STRETCH
    shape.fill_format.picture_fill_format.picture.image = img
    prs.save("picture-fill.pptx", SaveFormat.PPTX)
```

### No Fill (Transparent Shape)

```python
from aspose.slides_foss import ShapeType, FillType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 150)
    shape.fill_format.fill_type = FillType.NO_FILL
    shape.add_text_frame("Transparent background")
    prs.save("no-fill.pptx", SaveFormat.PPTX)
```

---

## See Also

- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [EffectFormat + ThreeDFormat reference](/reference.aspose.org/slides/python/effects/)
- [Slides Python API Reference home](/reference.aspose.org/slides/python/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [How to Format Text](/kb.aspose.org/slides/python/how-to-format-text-python/)
- [Developer Guide — Features](/docs.aspose.org/slides/python/developer-guide/features/)
