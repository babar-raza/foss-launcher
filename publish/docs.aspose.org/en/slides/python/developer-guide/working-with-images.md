---
page_role: howto_article
title: "Working with Images in Presentations — Aspose.Slides FOSS for Python"
description: "Embed images in PowerPoint slides using Aspose.Slides FOSS for Python. Add picture frames from file path or bytes, resize and position images, and use images as shape fills."
canonical: https://docs.aspose.org/slides/python/developer-guide/working-with-images/
url: /docs.aspose.org/slides/python/developer-guide/working-with-images/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "Working with Images in PowerPoint Presentations — Aspose.Slides FOSS for Python"
keywords:
  - aspose slides add image python
  - python pptx picture frame
  - embed image powerpoint python
  - aspose slides picture fill python
  - python pptx add photo slide
type: howto_article
draft: false
weight: 30
---

Aspose.Slides FOSS for Python lets you embed images in a presentation's shared image collection and display them on slides using `PictureFrame` shapes. Images can also be used as shape background fills via `FillType.PICTURE`.

---

## Adding an Image from File

Load image bytes from disk and add them to the presentation's image collection with `prs.images.add_image()`. Then place the image on a slide as a `PictureFrame`:

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    # Add the image to the shared collection
    with open("logo.png", "rb") as f:
        img = prs.images.add_image(f.read())

    # Place it on the slide as a PictureFrame
    slide = prs.slides[0]
    slide.shapes.add_picture_frame(ShapeType.RECTANGLE, 50, 50, 300, 200, img)

    prs.save("with-image.pptx", SaveFormat.PPTX)
```

The four positional arguments to `add_picture_frame()` are: `x, y, width, height` in points.

---

## Adding an Image from Bytes

If you already have image bytes (e.g., downloaded from a URL or read from a database), pass them directly to `add_image()`:

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

# Simulate having bytes in memory
with open("photo.jpg", "rb") as f:
    image_bytes = f.read()

with slides.Presentation() as prs:
    img = prs.images.add_image(image_bytes)
    prs.slides[0].shapes.add_picture_frame(ShapeType.RECTANGLE, 100, 80, 400, 250, img)
    prs.save("from-bytes.pptx", SaveFormat.PPTX)
```

---

## Positioning and Sizing a PictureFrame

The `PictureFrame` returned by `add_picture_frame()` inherits all `Shape` geometry properties and can be repositioned after creation:

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    with open("photo.jpg", "rb") as f:
        img = prs.images.add_image(f.read())

    pf = prs.slides[0].shapes.add_picture_frame(ShapeType.RECTANGLE, 0, 0, 100, 100, img)

    # Reposition and resize after creation
    pf.x = 50
    pf.y = 100
    pf.width = 350
    pf.height = 250

    prs.save("positioned.pptx", SaveFormat.PPTX)
```

---

## Using an Image as a Shape Fill

Any shape (not just PictureFrame) can use an image as its background fill. Set `fill_type = FillType.PICTURE` and assign the image to `picture_fill_format.picture.image`:

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType, FillType, PictureFillMode
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    with open("background.png", "rb") as f:
        img = prs.images.add_image(f.read())

    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.ROUNDED_RECTANGLE, 50, 50, 400, 250)
    shape.fill_format.fill_type = FillType.PICTURE
    shape.fill_format.picture_fill_format.picture_fill_mode = PictureFillMode.STRETCH
    shape.fill_format.picture_fill_format.picture.image = img

    prs.save("picture-fill.pptx", SaveFormat.PPTX)
```

`PictureFillMode.STRETCH` scales the image to fill the entire shape. Use `TILE` or `TILE_FLIP` for repeating patterns.

---

## Adding Multiple Images Across Slides

Images added to `prs.images` are shared across all slides — the same `Image` object can be used on multiple slides without duplicating the data:

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    with open("logo.png", "rb") as f:
        logo = prs.images.add_image(f.read())

    # Add the same image to both slides
    prs.slides[0].shapes.add_picture_frame(ShapeType.RECTANGLE, 600, 10, 100, 40, logo)

    prs.save("shared-image.pptx", SaveFormat.PPTX)
```

---

## See Also

- [How to Add Images to Slides in Python](/kb.aspose.org/slides/python/how-to-add-images-python/)
- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [FillFormat class reference](/reference.aspose.org/slides/python/fill-format/)
- [Developer Guide — Features](/docs.aspose.org/slides/python/developer-guide/features/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
