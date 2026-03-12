---
page_role: howto_article
title: "Working with Connectors — Aspose.Slides FOSS for Python"
description: "Add connectors between shapes in PowerPoint presentations using Aspose.Slides FOSS for Python. Connect shapes with bent, straight, and curved connectors using connection site indexes."
canonical: https://docs.aspose.org/slides/python/developer-guide/working-with-connectors/
url: /docs.aspose.org/slides/python/developer-guide/working-with-connectors/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "Working with Connectors in PowerPoint — Aspose.Slides FOSS for Python"
keywords:
  - aspose slides connector python
  - python pptx connect shapes
  - python powerpoint bent connector
  - aspose slides add connector python
  - python pptx shape connection
type: howto_article
draft: false
weight: 40
---

Connectors are shapes that visually link two other shapes with a line. Aspose.Slides FOSS for Python supports bent, straight, and curved connectors. The connection points on a shape are identified by integer **connection site indexes**.

---

## Connection Site Indexes

Each shape exposes four standard connection sites:

| Index | Side |
|:---:|---|
| `0` | Top |
| `1` | Left |
| `2` | Bottom |
| `3` | Right |

---

## Adding a Bent Connector Between Two Shapes

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    # Create two shapes to connect
    box1 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 150, 150, 60)
    box1.add_text_frame("Start")

    box2 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 400, 150, 150, 60)
    box2.add_text_frame("End")

    # Add a bent connector (position/size are ignored once connected)
    conn = slide.shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)

    # Connect right side of box1 → left side of box2
    conn.start_shape_connected_to = box1
    conn.start_shape_connection_site_index = 3   # right
    conn.end_shape_connected_to = box2
    conn.end_shape_connection_site_index = 1     # left

    prs.save("connector.pptx", SaveFormat.PPTX)
```

---

## Connector Shape Types

| ShapeType | Description |
|---|---|
| `ShapeType.BENT_CONNECTOR3` | Two 90° bends (most common for flowchart-style diagrams) |
| `ShapeType.BENT_CONNECTOR2` | One 90° bend |
| `ShapeType.BENT_CONNECTOR4` | Three 90° bends |
| `ShapeType.STRAIGHT_CONNECTOR1` | Direct straight line |
| `ShapeType.CURVE_CONNECTOR2` | Single smooth curve |
| `ShapeType.CURVE_CONNECTOR3` | Double-bend curve |

---

## Top-to-Bottom Connection

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    top = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 250, 80, 200, 60)
    top.add_text_frame("Decision")

    bottom = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 250, 300, 200, 60)
    bottom.add_text_frame("Action")

    conn = slide.shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)
    conn.start_shape_connected_to = top
    conn.start_shape_connection_site_index = 2    # bottom of top box
    conn.end_shape_connected_to = bottom
    conn.end_shape_connection_site_index = 0      # top of bottom box

    prs.save("vertical-connector.pptx", SaveFormat.PPTX)
```

---

## Flowchart with Multiple Connectors

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat


def add_box(slide, text, x, y, w=160, h=50):
    s = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, x, y, w, h)
    s.add_text_frame(text)
    return s


def connect(slide, s1, site1, s2, site2):
    conn = slide.shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)
    conn.start_shape_connected_to = s1
    conn.start_shape_connection_site_index = site1
    conn.end_shape_connected_to = s2
    conn.end_shape_connection_site_index = site2
    return conn


with slides.Presentation() as prs:
    slide = prs.slides[0]

    start = add_box(slide, "Start", 260, 60)
    process = add_box(slide, "Process Data", 260, 180)
    end = add_box(slide, "End", 260, 300)

    connect(slide, start, 2, process, 0)    # start → process (bottom to top)
    connect(slide, process, 2, end, 0)      # process → end (bottom to top)

    prs.save("flowchart.pptx", SaveFormat.PPTX)
```

---

## Formatting a Connector

Connectors support the same `line_format` properties as other shapes:

```python
from aspose.slides_foss import ShapeType, LineDashStyle
from aspose.slides_foss.drawing import Color
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    box1 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 150, 150, 60)
    box2 = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 400, 150, 150, 60)

    conn = slide.shapes.add_connector(ShapeType.BENT_CONNECTOR3, 0, 0, 10, 10)
    conn.start_shape_connected_to = box1
    conn.start_shape_connection_site_index = 3
    conn.end_shape_connected_to = box2
    conn.end_shape_connection_site_index = 1

    # Style the connector line
    conn.line_format.width = 2.5
    conn.line_format.dash_style = LineDashStyle.DASH
    conn.line_format.fill_format.solid_fill_color.color = Color.dark_blue

    prs.save("styled-connector.pptx", SaveFormat.PPTX)
```

---

## See Also

- [How to Connect Shapes with Connectors in Python](/kb.aspose.org/slides/python/how-to-connect-shapes-python/)
- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [Slide class reference](/reference.aspose.org/slides/python/slide/)
- [Developer Guide — Features](/docs.aspose.org/slides/python/developer-guide/features/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
