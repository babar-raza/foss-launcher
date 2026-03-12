---
page_role: howto_article
title: "How to Connect Shapes with Connectors in Python"
description: "Add connectors between shapes in PowerPoint using Aspose.Slides FOSS for Python. Create bent, elbow, and straight connectors with precise connection site control."
canonical: https://kb.aspose.org/slides/python/how-to-connect-shapes-python/
url: /kb.aspose.org/slides/python/how-to-connect-shapes-python/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "How to Connect Shapes with Connectors in Python — Aspose.Slides FOSS"
keywords:
  - python pptx connector shapes
  - aspose slides connector python
  - python powerpoint connect shapes
  - aspose slides foss bent connector python
  - python pptx add_connector
type: howto_article
draft: false
weight: 80
---

Connectors in Aspose.Slides FOSS are line shapes that attach to **connection sites** on other shapes. When you move a connected shape, the connector endpoint moves with it. The most common connector type is `BENT_CONNECTOR3`, which routes around obstacles with a single elbow bend.

---

## Prerequisites

```bash
pip install aspose-slides-foss
```

---

## Connection Site Indexes

Every shape has four numbered connection sites:

| Index | Position |
|---|---|
| `0` | Top center |
| `1` | Left center |
| `2` | Bottom center |
| `3` | Right center |

---

## Connect Two Shapes

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    # Add two rectangles
    box1 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 200, 200, 100)
    box2 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 450, 200, 200, 100)

    box1.add_text_frame("Start")
    box2.add_text_frame("End")

    # Add a bent connector (initial bounds are overwritten by the connection)
    conn = slide.shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)

    # Connect right side of box1 (site 3) to left side of box2 (site 1)
    conn.start_shape_connected_to = box1
    conn.start_shape_connection_site_index = 3
    conn.end_shape_connected_to = box2
    conn.end_shape_connection_site_index = 1

    prs.save("connected.pptx", SaveFormat.PPTX)
```

The placeholder bounds `(0, 0, 10, 10)` passed to `add_connector` are ignored once the connection endpoints are set — PowerPoint re-routes the connector to the attached shapes.

---

## Connector Types

```python
from aspose.slides_foss import ShapeType

# Straight line
ShapeType.STRAIGHT_CONNECTOR1

# Single elbow (L-shape)
ShapeType.BENT_CONNECTOR2

# Double elbow (Z-shape) — most common
ShapeType.BENT_CONNECTOR3

# Curved connector
ShapeType.CURVED_CONNECTOR3
```

---

## Style the Connector Line

```python
from aspose.slides_foss import ShapeType, LineDashStyle
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    box1 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 150, 180, 80)
    box2 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 500, 300, 180, 80)

    conn = slide.shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)
    conn.start_shape_connected_to = box1
    conn.start_shape_connection_site_index = 2   # bottom of box1
    conn.end_shape_connected_to = box2
    conn.end_shape_connection_site_index = 0     # top of box2

    # Style: dashed blue line, 2 pt width
    lf = conn.line_format
    lf.width = 2.0
    lf.fill_format.solid_fill_color.color = Color.blue
    lf.dash_style = LineDashStyle.DASH

    prs.save("styled-connector.pptx", SaveFormat.PPTX)
```

---

## Flowchart with Multiple Connectors

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    # Three-step flowchart
    step1 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 350, 50, 200, 70)
    step2 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 350, 220, 200, 70)
    step3 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 350, 390, 200, 70)

    step1.add_text_frame("Step 1")
    step2.add_text_frame("Step 2")
    step3.add_text_frame("Step 3")

    def connect_vertical(shapes, top_shape, bottom_shape):
        conn = shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)
        conn.start_shape_connected_to = top_shape
        conn.start_shape_connection_site_index = 2   # bottom
        conn.end_shape_connected_to = bottom_shape
        conn.end_shape_connection_site_index = 0     # top
        return conn

    connect_vertical(slide.shapes, step1, step2)
    connect_vertical(slide.shapes, step2, step3)

    prs.save("flowchart.pptx", SaveFormat.PPTX)
```

---

## Read Connector Properties

```python
from aspose.slides_foss import Connector
import aspose.slides_foss as slides

with slides.Presentation("connected.pptx") as prs:
    for shape in prs.slides[0].shapes:
        if isinstance(shape, Connector):
            start = shape.start_shape_connected_to
            end = shape.end_shape_connected_to
            print(f"Connector: {getattr(start, 'name', '?')} → {getattr(end, 'name', '?')}")
```

---

## See Also

- [Working with Connectors — Developer Guide](/docs.aspose.org/slides/python/developer-guide/working-with-connectors/)
- [Slide class reference](/reference.aspose.org/slides/python/slide/)
- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
