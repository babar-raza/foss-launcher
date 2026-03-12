---
page_role: howto_article
title: "How to Add Images to PowerPoint Slides in Python"
description: "Embed images into PowerPoint slides as picture frames using Aspose.Slides FOSS for Python. Load images from file or bytes and control placement and fill mode."
canonical: https://kb.aspose.org/slides/python/how-to-add-images-python/
url: /kb.aspose.org/slides/python/how-to-add-images-python/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "How to Add Images to PowerPoint Slides in Python — Aspose.Slides FOSS"
keywords:
  - python pptx add image
  - aspose slides add picture python
  - python powerpoint picture frame
  - aspose slides foss image embedding python
  - python pptx add_picture_frame
type: howto_article
draft: false
weight: 70
---

Images in Aspose.Slides FOSS are embedded as **picture frames** — shapes that hold an image and can be positioned, resized, and styled like any other shape. The image data is stored once in the `prs.images` collection and referenced by the frame.

---

## Prerequisites

```bash
pip install aspose-slides-foss
```

---

## Add an Image from a File

```python
from aspose.slides_foss import ShapeType, PictureFillMode
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    # Load image into the presentation's image collection
    with open("photo.jpg", "rb") as f:
        img = prs.images.add_image(f.read())

    # Add a picture frame at (x=50, y=50, width=400, height=300) in points
    frame = slide.shapes.add_picture_frame(
        ShapeType.RECTANGLE,
        50, 50, 400, 300,
        img,
    )

    prs.save("with-image.pptx", SaveFormat.PPTX)
```

The `add_picture_frame` signature:

```
add_picture_frame(shape_type, x, y, width, height, image) → PictureFrame
```

All dimensions are in **points** (1 point = 1/72 inch). For a standard 13.33 × 7.5 inch slide the coordinate space is 960 × 540 points.

---

## Add an Image from Bytes

If you already have the image as bytes (e.g., downloaded from a URL or read from a database):

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

image_bytes = open("logo.png", "rb").read()  # or any bytes source

with slides.Presentation() as prs:
    img = prs.images.add_image(image_bytes)

    prs.slides[0].shapes.add_picture_frame(
        ShapeType.RECTANGLE,
        200, 100, 300, 200,
        img,
    )
    prs.save("logo-slide.pptx", SaveFormat.PPTX)
```

---

## Control the Fill Mode

The `picture_fill_format` on a `PictureFrame` controls how the image fills the frame bounds:

```python
from aspose.slides_foss import ShapeType, PictureFillMode
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    img = prs.images.add_image(open("texture.png", "rb").read())
    frame = prs.slides[0].shapes.add_picture_frame(
        ShapeType.RECTANGLE, 50, 50, 600, 350, img
    )

    # STRETCH: scale image to fill the frame exactly (default)
    frame.picture_format.picture_fill_mode = PictureFillMode.STRETCH

    # TILE: repeat the image in a grid pattern
    # frame.picture_format.picture_fill_mode = PictureFillMode.TILE

    prs.save("filled.pptx", SaveFormat.PPTX)
```

| `PictureFillMode` | Behaviour |
|---|---|
| `STRETCH` | Scale the image to fill the frame, ignoring aspect ratio |
| `TILE` | Repeat the image as a tiled pattern |
| `TILE_FLIP` | Tile with alternating horizontal/vertical flips |

---

## Add Multiple Images to Different Slides

```python
import os
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

image_files = ["slide1.jpg", "slide2.jpg", "slide3.jpg"]

with slides.Presentation() as prs:
    layout = prs.slides[0].layout_slide

    # Ensure enough slides exist
    while len(prs.slides) < len(image_files):
        prs.slides.add_empty_slide(layout)

    for i, path in enumerate(image_files):
        if not os.path.exists(path):
            continue
        img = prs.images.add_image(open(path, "rb").read())
        prs.slides[i].shapes.add_picture_frame(
            ShapeType.RECTANGLE, 0, 0, 960, 540, img
        )

    prs.save("multi-image.pptx", SaveFormat.PPTX)
```

---

## Count Images in an Existing Presentation

```python
import aspose.slides_foss as slides

with slides.Presentation("with-image.pptx") as prs:
    print(f"Presentation contains {len(prs.images)} image(s)")
```

The `prs.images` collection is shared across all slides — the same image bytes are stored once even if the picture frame appears on multiple slides.

---

## See Also

- [Working with Images — Developer Guide](/docs.aspose.org/slides/python/developer-guide/working-with-images/)
- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [Slide class reference](/reference.aspose.org/slides/python/slide/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
