---
page_role: howto_article
title: "Working with Comments and Speaker Notes — Aspose.Slides FOSS for Python"
description: "Add threaded comments and speaker notes to PowerPoint presentations using Aspose.Slides FOSS for Python. Manage comment authors, attach comments to slides, and write notes."
canonical: https://docs.aspose.org/slides/python/developer-guide/working-with-comments/
url: /docs.aspose.org/slides/python/developer-guide/working-with-comments/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.Slides FOSS
family: slides
platform: python
canonical_import: aspose_slides_foss
robots: index, follow
seoTitle: "Working with Comments and Speaker Notes in PowerPoint — Aspose.Slides FOSS for Python"
keywords:
  - aspose slides comments python
  - python pptx add comment
  - python powerpoint speaker notes
  - aspose slides notes slide python
  - python pptx comment author
type: howto_article
draft: false
weight: 60
---

Aspose.Slides FOSS for Python supports two types of annotations: **threaded slide comments** (visible in review mode) and **speaker notes** (visible in Presenter View and the Notes pane).

---

## Threaded Comments

Comments are attached to a slide and associated with an author. The `prs.comment_authors` collection manages all authors; each author has a `comments` collection for adding and reading comments.

### Add a Comment

```python
from aspose.slides_foss.drawing import PointF
from datetime import datetime
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    # Create a comment author with initials
    author = prs.comment_authors.add_author("Jane Smith", "JS")

    slide = prs.slides[0]

    # Add a comment at position (2.0, 2.0) inches from the slide top-left
    author.comments.add_comment(
        "Please review the figures on this slide",
        slide,
        PointF(2.0, 2.0),
        datetime.now()
    )

    prs.save("commented.pptx", SaveFormat.PPTX)
```

The `PointF` position is in inches from the top-left corner of the slide. Multiple comments can be added to the same slide by calling `add_comment()` again.

### Multiple Authors and Comments

```python
from aspose.slides_foss.drawing import PointF
from datetime import datetime
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    author1 = prs.comment_authors.add_author("Alice Brown", "AB")
    author2 = prs.comment_authors.add_author("Bob Davis", "BD")

    slide = prs.slides[0]

    author1.comments.add_comment("Initial draft", slide, PointF(1.0, 1.0), datetime.now())
    author2.comments.add_comment("Approved", slide, PointF(3.0, 1.0), datetime.now())

    prs.save("multi-author.pptx", SaveFormat.PPTX)
```

### Read Comments from an Existing File

```python
import aspose.slides_foss as slides

with slides.Presentation("commented.pptx") as prs:
    for author in prs.comment_authors:
        print(f"Author: {author.name} ({author.initials})")
        for comment in author.comments:
            print(f"  [{comment.slide_number}] {comment.text}")
```

---

## Speaker Notes

Speaker notes are stored on a per-slide basis via a `NotesSlide` object. Access it through `slide.notes_slide_manager`.

### Add Speaker Notes to a Slide

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    slide.shapes.add_auto_shape(__import__('aspose.slides_foss', fromlist=['ShapeType']).ShapeType.RECTANGLE, 50, 50, 400, 200)

    # Create the notes slide and set text
    notes = slide.notes_slide_manager.add_notes_slide()
    notes.notes_text_frame.text = "Mention the Q3 revenue increase on this slide. Emphasize the 24% growth."

    prs.save("with-notes.pptx", SaveFormat.PPTX)
```

### Simpler Notes Example

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 100, 100, 500, 250).add_text_frame("Main Content")

    notes = slide.notes_slide_manager.add_notes_slide()
    notes.notes_text_frame.text = "These are the speaker notes for this slide."

    prs.save("notes.pptx", SaveFormat.PPTX)
```

### Check Whether a Notes Slide Already Exists

`notes_slide_manager.notes_slide` returns `None` if no notes slide has been created yet:

```python
import aspose.slides_foss as slides

with slides.Presentation("existing.pptx") as prs:
    for i, slide in enumerate(prs.slides):
        existing_notes = slide.notes_slide_manager.notes_slide
        if existing_notes:
            text = existing_notes.notes_text_frame.text
            print(f"Slide {i + 1} notes: {text[:60]}...")
        else:
            print(f"Slide {i + 1}: no notes")
```

### Add Notes to Multiple Slides

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

note_texts = [
    "Opening remarks — introduce the agenda.",
    "Key metrics — emphasize Q4 results.",
    "Closing — call to action.",
]

with slides.Presentation() as prs:
    # Add slides 2 and 3
    layout = prs.slides[0].layout_slide
    prs.slides.add_empty_slide(layout)
    prs.slides.add_empty_slide(layout)

    for i, slide in enumerate(prs.slides):
        slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 600, 300).add_text_frame(f"Slide {i + 1}")
        n = slide.notes_slide_manager.add_notes_slide()
        n.notes_text_frame.text = note_texts[i]

    prs.save("all-notes.pptx", SaveFormat.PPTX)
```

---

## See Also

- [How to Add Comments to Slides in Python](/kb.aspose.org/slides/python/how-to-add-comments-python/)
- [Presentation class reference](/reference.aspose.org/slides/python/presentation/)
- [Slide class reference](/reference.aspose.org/slides/python/slide/)
- [Developer Guide — Features](/docs.aspose.org/slides/python/developer-guide/features/)
- [Getting Started](/docs.aspose.org/slides/python/getting-started/)
