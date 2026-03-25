---
canonical: https://reference.aspose.org/slides/python/shape/
canonical_import: aspose.slides
code_import: aspose.slides
date: '2026-03-24T16:56:57Z'
dateModified: '2026-03-24T16:56:57Z'
datePublished: '2026-03-24T16:56:57Z'
description: It is used to read or modify geometric properties of shapes such as rounded
  corners or arrowhead sizes.
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
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: 'Adjustvalue: Represents a geometry shape''s adjustment value | Guide'
slug: shape
title: 'Adjustvalue: Represents a geometry shape''s adjustment value'
type: reference_object_page
url: /reference.aspose.org/slides/python/shape/
weight: 20
---

## Overview

The `AdjustValue` class represents `a` geometry shape's adjustment value and provides access to its `name`, raw numeric value, and angle value. It is used to read or modify geometric properties of shapes such as rounded corners or arrowhead sizes.

| Name | Type | Description |
|------|------|-------------|
| `name` | str (read-only) | The `name` of the adjustment value. |
| raw_value | int | The raw numeric adjustment value. |
| `angle_value` | float | The angle value in degrees. |

```python
from aspose.slides import Presentation, ShapeType

with Presentation() as pres:
    shape = pres.slides[0].shapes.add_auto_shape(ShapeType.ROUNDED_RECTANGLE, 50, 50, 200, 100)
    adj_values = shape.as_i_geometry_shape.adjust_values
    if len(adj_values) > 0:
        adj = adj_values[0]
        name = adj.name
        raw = adj.raw_value
        angle = adj.angle_value
```

## Constructor

The `AdjustValue` class represents `a` geometry shape's adjustment value. It is used to access or modify numeric or angular `adjustments` applied to shapes like callouts or arrows. This class is read-only for the `name` property and read-write for raw_value and `angle_value`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| raw_value | int | 0 | The raw numeric adjustment value. |
| `angle_value` | float | 0.0 | The angle-based adjustment value in degrees. |
| `name` | str | "" | The `name` of the adjustment (read-only). |

```python
import aspose.slides as slides

with slides.Presentation() as prs:
    shape = prs.slides[0].shapes.add_auto_shape(slides.ShapeType.CALLOUT_2, 100, 100, 200, 100)
    adj = shape.adjust_values[0]
    adj.raw_value = 50
    adj.angle_value = 45.0
```

## Properties

The `AdjustValue` class represents `a` geometry shape's adjustment value in Aspose.Slides. It provides access to named, raw, and angular adjustment data used by geometry shapes such as auto shapes.

| Name | Type | Description |
|------|------|-------------|
| `name` | str (read-only) | The `name` of the adjustment value. |
| raw_value | int | The raw integer value of the adjustment. |
| `angle_value` | float | The angle value (in degrees) of the adjustment. |

```python
import aspose.slides as slides

with slides.Presentation() as pres:
    slide = pres.slides[0]
    shape = slide.shapes.add_auto_shape(slides.ShapeType.ROUNDED_RECTANGLE, 100, 100, 200, 100)
    adj_values = shape.geometry_shape.adjust_values
    if len(adj_values) > 0:
        adj = adj_values[0]
        name = adj.name
        raw = adj.raw_value
        angle = adj.angle_value
```

## Methods

The `AdjustValue` class represents `a` geometry shape's adjustment value and exposes properties to access its `name`, raw integer value, and angle value. It does not define any methods.

| Method | Return Type | Description |
|--------|-------------|-------------|
| (none) | (none) | (none) |

```python
import aspose.slides as slides

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(slides.ShapeType.ROUNDED_RECTANGLE, 100, 100, 200, 100)
    adj_vals = shape.as_i_geometry_shape.adjust_values
    if len(adj_vals) > 0:
        adj = adj_vals[0]
        name = adj.name
        raw = adj.raw_value
        angle = adj.angle_value
```

## Example

```python
import aspose.slides
from aspose.slides import Presentation, ShapeType

# Create a presentation and add a rounded rectangle
pres = Presentation()
slide = pres.slides[0]
shape = slide.shapes.add_auto_shape(ShapeType.ROUNDED_RECTANGLE, 100, 100, 200, 100)

# Access the geometry shape and its adjustment values
geom_shape = shape.as_i_geometry_shape
adjust_values = geom_shape.adjust_values

# Modify the first adjustment value (e.g., corner rounding)
if len(adjust_values) > 0:
    adj = adjust_values[0]
    adj.raw_value = 20

pres.save("output.pptx")
```

## See Also

The `AdjustValue` class represents `a` geometry shape's adjustment value and exposes properties for `name`, raw value, and angle value. Related classes include `AutoShape` for shape creation and `AdjustValueCollection` for managing multiple adjustment values.

```python
import aspose.slides as slides

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(slides.ShapeType.ROUNDED_RECTANGLE, 100, 100, 200, 100)
    adj_values = shape.as_i_geometry_shape.adjust_values
    for adj in adj_values:
        name = adj.name
        raw = adj.raw_value
        angle = adj.angle_value
```

- [Adjustvalue definition and usage](/reference.aspose.org/slides/python/api-overview/)
- [3D shape formatting capabilities](/blog.aspose.org/slides/python/introducing-slides-foss-python/)
- [Key features for presentations](/blog.aspose.org/slides/python/slides-key-features/)
- [Create presentations programmatically](/docs.aspose.org/slides/python/developer-guide/presentation-creation/)
- [Work with slides effectively](/docs.aspose.org/slides/python/developer-guide/slide-manipulation/)
