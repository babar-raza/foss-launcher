---
page_role: reference_object_page
title: "Presentation — Aspose.Slides FOSS for Python API Reference"
description: "API reference for the Presentation class in aspose-slides-foss. Constructor, slides collection, save methods, document properties, comments, and context manager support."
canonical: https://reference.aspose.org/slides/python/presentation/
url: /reference.aspose.org/slides/python/presentation/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "Presentation Class — Aspose.Slides FOSS for Python API Reference"
keywords:
  - aspose slides presentation python
  - python pptx presentation class
  - open pptx python
  - save pptx python
  - aspose slides foss python api
type: reference_object_page
draft: false
weight: 10
---

The `Presentation` class is the root object for creating, loading, and saving PowerPoint `.pptx` files in aspose-slides-foss.

**Package**: `aspose.slides_foss`

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat
```

---

## Constructor

```python
slides.Presentation(path=None)
```

| Parameter | Type | Description |
|---|---|---|
| `path` | `str \| None` | File path to an existing `.pptx` file. Pass `None` (or omit) to create a new empty presentation with one blank slide. |

**Examples**:

```python
import aspose.slides_foss as slides

# Create a new empty presentation
prs = slides.Presentation()

# Open an existing PPTX file
prs = slides.Presentation("deck.pptx")
```

The class supports the **context manager protocol**. Use `with` to ensure the presentation is closed properly:

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation("input.pptx") as prs:
    print(f"Slide count: {len(prs.slides)}")
    prs.save("output.pptx", SaveFormat.PPTX)
```

---

## Properties

| Property | Type | Access | Description |
|---|---|---|---|
| `slides` | `SlideCollection` | Read | Ordered collection of slides. Access by zero-based index: `prs.slides[0]`. |
| `master_slides` | `MasterSlideCollection` | Read | Collection of master slides in the presentation. |
| `layout_slides` | `GlobalLayoutSlideCollection` | Read | Collection of all layout slides across all masters. |
| `comment_authors` | `CommentAuthorCollection` | Read | Collection of comment authors. Add authors via `add_author()`. |
| `document_properties` | `DocumentProperties` | Read | Core, application, and custom document metadata. |
| `images` | `ImageCollection` | Read | Collection of all images embedded in the presentation. |

---

## Methods

### save

```python
prs.save(path, format)
```

Save the presentation to a file.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Destination file path. |
| `format` | `SaveFormat` | Output format. Currently only `SaveFormat.PPTX` is supported. |

```python
from aspose.slides_foss.export import SaveFormat

prs.save("output.pptx", SaveFormat.PPTX)
```

### dispose

```python
prs.dispose()
```

Release resources. Called automatically when using the `with` statement.

---

## SlideCollection Methods

| Method | Signature | Description |
|---|---|---|
| `add_empty_slide` | `(layout: LayoutSlide) -> Slide` | Append a new empty slide using the given layout. |
| `remove_at` | `(index: int) -> None` | Remove the slide at zero-based `index`. |
| `__getitem__` | `[index: int] -> Slide` | Return the slide at zero-based `index`. |
| `__len__` | `() -> int` | Number of slides in the presentation. |
| `__iter__` | — | Iterate over all slides. |

---

## Usage Examples

### Create a Presentation with a Shape

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 100)
    shape.add_text_frame("Hello, Slides!")
    prs.save("hello.pptx", SaveFormat.PPTX)
```

### Open, Inspect, and Re-Save

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation("existing.pptx") as prs:
    print(f"Slides: {len(prs.slides)}")
    for i, slide in enumerate(prs.slides):
        print(f"  Slide {i}: {len(slide.shapes)} shapes")
    prs.save("existing-updated.pptx", SaveFormat.PPTX)
```

### Set Document Properties

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    prs.document_properties.title = "Q1 Results"
    prs.document_properties.author = "Finance Team"
    prs.document_properties.subject = "Quarterly Review"
    prs.document_properties.set_custom_property_value("Version", 3)
    prs.save("q1.pptx", SaveFormat.PPTX)
```

### Add Comments

```python
from aspose.slides_foss.drawing import PointF
from datetime import datetime
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    author = prs.comment_authors.add_author("Jane Smith", "JS")
    slide = prs.slides[0]
    author.comments.add_comment(
        "Please review this slide",
        slide,
        PointF(2.0, 2.0),
        datetime.now()
    )
    prs.save("commented.pptx", SaveFormat.PPTX)
```

---

## Limitations

The following features raise `NotImplementedError` in this version:

- Charts, SmartArt, OLE objects
- Animations and slide transitions
- Export formats other than PPTX (PDF, HTML, images)
- Hyperlinks and action settings
- VBA macros and digital signatures

Unknown XML parts in an existing PPTX file are preserved verbatim on save.

---

## See Also

- [Slides Python API Reference home](/reference.aspose.org/slides/python/)
- [Slide class reference](/reference.aspose.org/slides/python/slide/)
- [Shape class reference](/reference.aspose.org/slides/python/shape/)
- [TextFrame class reference](/reference.aspose.org/slides/python/textframe/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
- [Developer Guide](/docs.aspose.org/slides/python/developer-guide/)
- [Knowledge Base](/kb.aspose.org/slides/python/)
