---
page_role: howto_article
title: "How to Load Presentations in Python"
description: "Learn how to open an existing PowerPoint (.pptx) file in Python using Aspose.Slides FOSS — inspect slides, shapes, and text, then save the result."
date: 2026-03-11
weight: 11
draft: false
type: "topic"
keywords: ["load pptx python", "open powerpoint python", "read pptx python", "aspose slides load", "inspect presentation python", "pptx slides count python"]
step1: "Install aspose-slides-foss from PyPI"
step2: "Import aspose.slides_foss"
step3: "Open the file with slides.Presentation('input.pptx')"
step4: "Inspect the slide count and shape collection"
step5: "Read text from shapes"
step6: "Save or close the presentation"
---

Aspose.Slides FOSS for Python lets you open any `.pptx` file, inspect its content, and either save it back to PPTX or extract data from it. This guide covers opening a file, iterating slides, reading shape text, and round-tripping the save.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install the Package

```bash
pip install aspose-slides-foss
```

---

### Step 2: Open an Existing Presentation

Pass the file path to `slides.Presentation()`. Use the context manager to ensure cleanup.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation("input.pptx") as prs:
    print(f"Slide count: {len(prs.slides)}")
    prs.save("output.pptx", SaveFormat.PPTX)
```

Unknown XML parts in the source file are preserved verbatim — the library never removes content it does not yet understand.

---

### Step 3: Inspect Slides

Iterate over all slides and print their index:

```python
import aspose.slides_foss as slides

with slides.Presentation("deck.pptx") as prs:
    for i, slide in enumerate(prs.slides):
        shape_count = len(slide.shapes)
        print(f"Slide {i}: {shape_count} shapes")
```

---

### Step 4: Read Shape Text

Iterate over shapes and read text from shapes that have a `TextFrame`:

```python
import aspose.slides_foss as slides

with slides.Presentation("deck.pptx") as prs:
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text_frame") and shape.text_frame is not None:
                text = shape.text_frame.text
                if text.strip():
                    print(f"  Shape text: {text!r}")
```

---

### Step 5: Read Document Properties

Access core document properties from `prs.document_properties`:

```python
import aspose.slides_foss as slides

with slides.Presentation("deck.pptx") as prs:
    props = prs.document_properties
    print(f"Title:   {props.title}")
    print(f"Author:  {props.author}")
    print(f"Subject: {props.subject}")
```

---

### Step 6: Round-Trip Save

After inspecting or modifying the presentation, save it back to PPTX:

```python
prs.save("output.pptx", SaveFormat.PPTX)
```

Saving to a different path creates a new file. Saving to the same path overwrites the original.

{{% /steps %}}

---

## Common Issues and Fixes

**`FileNotFoundError`**

Check that the path to the `.pptx` file is correct relative to the working directory. Use `pathlib.Path` for robust path construction:

```python
from pathlib import Path
path = Path(__file__).parent / "assets" / "deck.pptx"
with slides.Presentation(str(path)) as prs:
    ...
```

**`Exception: File format is not supported`**

The library supports `.pptx` (Office Open XML) only. Legacy `.ppt` (binary PowerPoint 97–2003) files are not supported.

**Shapes have no text_frame attribute**

Some shapes (Connectors, PictureFrames, GroupShapes) do not have a `text_frame`. Guard with `hasattr(shape, "text_frame") and shape.text_frame is not None` before accessing text.

---

## Frequently Asked Questions

**Does loading preserve all original content?**

Yes. Unknown XML parts are preserved verbatim on round-trip save. The library will not remove any XML content it does not yet understand.

**Can I load a password-protected PPTX?**

Password-protected (encrypted) presentations are not supported in this edition.

**Can I extract embedded images?**

Access the images collection: `prs.images` returns the `ImageCollection`. Each image has a `content_type` and a `bytes` property to read the raw image data.

**Is loading from an in-memory stream supported?**

Loading directly from `io.BytesIO` is not exposed in the current API. Write the bytes to a temporary file first:

```python
import tempfile, os
import aspose.slides_foss as slides

with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
    tmp.write(pptx_bytes)
    tmp_path = tmp.name

try:
    with slides.Presentation(tmp_path) as prs:
        print(f"Slides: {len(prs.slides)}")
finally:
    os.unlink(tmp_path)
```

---

## See Also

- [How to Create Presentations in Python](/kb.aspose.org/slides/python/how-to-create-presentations-python/)
- [How to Save Presentations in Python](/kb.aspose.org/slides/python/how-to-save-presentations-python/)
- [Features Overview](/docs.aspose.org/slides/python/developer-guide/features/)
- [API Reference](/reference.aspose.org/slides/python/)
