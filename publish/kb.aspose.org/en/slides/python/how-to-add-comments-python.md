---
page_role: howto_article
title: "How to Add Comments and Speaker Notes to PowerPoint in Python"
description: "Add threaded review comments and speaker notes to PowerPoint presentations using Aspose.Slides FOSS for Python. Manage comment authors and read notes from existing files."
canonical: https://kb.aspose.org/slides/python/how-to-add-comments-python/
url: /kb.aspose.org/slides/python/how-to-add-comments-python/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "How to Add Comments and Speaker Notes to PowerPoint in Python — Aspose.Slides FOSS"
keywords:
  - python pptx add comment
  - aspose slides comment author python
  - python powerpoint speaker notes
  - aspose slides foss notes slide python
  - python pptx comment threaded
type: howto_article
draft: false
weight: 100
---

Aspose.Slides FOSS for Python supports two annotation mechanisms:

- **Threaded comments** — attached to a slide at a specific position, visible in PowerPoint's Review pane
- **Speaker notes** — per-slide text visible in Presenter View and the Notes pane

---

## Prerequisites

```bash
pip install aspose-slides-foss
```

---

## Add a Comment

Comments belong to an **author** object. Create an author first, then add comments through `author.comments`:

```python
from aspose.slides_foss.drawing import PointF
from datetime import datetime
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    # Create a comment author with name and initials
    author = prs.comment_authors.add_author("Jane Smith", "JS")

    slide = prs.slides[0]

    # Add a comment at (2.0, 2.0) inches from the slide top-left corner
    author.comments.add_comment(
        "Please review the figures on this slide",
        slide,
        PointF(2.0, 2.0),
        datetime.now(),
    )

    prs.save("commented.pptx", SaveFormat.PPTX)
```

The `PointF` coordinates are in **inches** from the top-left of the slide. Multiple calls to `add_comment()` create a threaded comment chain under the same author.

---

## Multiple Authors and Comments

```python
from aspose.slides_foss.drawing import PointF
from datetime import datetime
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    author1 = prs.comment_authors.add_author("Alice Brown", "AB")
    author2 = prs.comment_authors.add_author("Bob Davis", "BD")

    slide = prs.slides[0]

    author1.comments.add_comment(
        "Initial draft — needs revision",
        slide, PointF(1.0, 1.0), datetime.now()
    )
    author2.comments.add_comment(
        "Approved after changes",
        slide, PointF(3.0, 1.0), datetime.now()
    )

    prs.save("multi-author.pptx", SaveFormat.PPTX)
```

---

## Read Comments from an Existing File

```python
import aspose.slides_foss as slides

with slides.Presentation("commented.pptx") as prs:
    for author in prs.comment_authors:
        print(f"Author: {author.name} ({author.initials})")
        for comment in author.comments:
            print(f"  Slide {comment.slide_number}: {comment.text}")
```

---

## Add Speaker Notes to a Slide

Speaker notes are added through `slide.notes_slide_manager`:

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    slide.shapes.add_auto_shape(
        ShapeType.RECTANGLE, 50, 50, 600, 300
    ).add_text_frame("Main slide content")

    # Create the notes slide and write text
    notes = slide.notes_slide_manager.add_notes_slide()
    notes.notes_text_frame.text = (
        "Mention the Q3 revenue increase. Emphasize the 24% YoY growth."
    )

    prs.save("with-notes.pptx", SaveFormat.PPTX)
```

---

## Add Notes to Multiple Slides

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

note_texts = [
    "Opening — introduce the agenda and set expectations.",
    "Key metrics — emphasize Q4 results and growth trajectory.",
    "Closing — summarize and call to action.",
]

with slides.Presentation() as prs:
    layout = prs.slides[0].layout_slide
    prs.slides.add_empty_slide(layout)
    prs.slides.add_empty_slide(layout)

    for i, slide in enumerate(prs.slides):
        slide.shapes.add_auto_shape(
            ShapeType.RECTANGLE, 50, 50, 600, 300
        ).add_text_frame(f"Slide {i + 1}")

        n = slide.notes_slide_manager.add_notes_slide()
        n.notes_text_frame.text = note_texts[i]

    prs.save("all-notes.pptx", SaveFormat.PPTX)
```

---

## Check Whether Notes Already Exist

`notes_slide_manager.notes_slide` returns `None` if no notes slide has been created:

```python
import aspose.slides_foss as slides

with slides.Presentation("existing.pptx") as prs:
    for i, slide in enumerate(prs.slides):
        existing = slide.notes_slide_manager.notes_slide
        if existing:
            print(f"Slide {i + 1}: {existing.notes_text_frame.text[:60]}")
        else:
            print(f"Slide {i + 1}: no notes")
```

---

## See Also

- [Working with Comments — Developer Guide](/docs.aspose.org/slides/python/developer-guide/working-with-comments/)
- [Presentation class reference](/reference.aspose.org/slides/python/presentation/)
- [Slide class reference](/reference.aspose.org/slides/python/slide/)
- [How to Add Shapes](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
