---
page_role: howto_article
title: "How to Save Presentations in Python"
description: "Learn how to save PowerPoint presentations to PPTX in Python using Aspose.Slides FOSS — correct context manager usage and common save patterns."
date: 2026-03-11
weight: 12
draft: false
type: "topic"
keywords: ["save pptx python", "python save powerpoint", "aspose slides save", "SaveFormat PPTX python", "python write pptx file"]
step1: "Install aspose-slides-foss from PyPI"
step2: "Create or open a Presentation with the context manager"
step3: "Make your changes to the presentation"
step4: "Call prs.save(path, SaveFormat.PPTX) before exiting the context"
step5: "Verify the output file exists"
---

Aspose.Slides FOSS for Python saves presentations exclusively to `.pptx` format using `prs.save(path, SaveFormat.PPTX)`. This guide covers the correct save pattern, saving to a different path, and common save-related errors.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install the Package

```bash
pip install aspose-slides-foss
```

---

### Step 2: Open or Create a Presentation

Always use the context manager. The save call must happen inside the `with` block.

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

# Create new
with slides.Presentation() as prs:
    prs.save("new.pptx", SaveFormat.PPTX)

# Open existing
with slides.Presentation("input.pptx") as prs:
    prs.save("output.pptx", SaveFormat.PPTX)
```

---

### Step 3: Save at the End of the `with` Block

Place the `save()` call as the last statement inside the `with` block, after all modifications are complete.

```python
import aspose.slides_foss as slides
from aspose.slides_foss import ShapeType
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 100)
    shape.add_text_frame("Hello, World!")
    prs.save("output.pptx", SaveFormat.PPTX)
```

---

### Step 4: Save to a Different Path

Pass a different output path to create a new file without modifying the original:

```python
with slides.Presentation("template.pptx") as prs:
    # modify ...
    prs.save("customized.pptx", SaveFormat.PPTX)
```

The `template.pptx` file is not modified; `customized.pptx` is created (or overwritten if it already exists).

---

### Step 5: Verify the Output

After the `with` block exits, the file is complete and closed. Check it exists:

```python
import os
from pathlib import Path

output = Path("output.pptx")
print(f"Saved: {output.exists()}, size: {output.stat().st_size} bytes")
```

{{% /steps %}}

---

## Supported Save Format

| Format | Enum Value | Supported |
|--------|------------|-----------|
| PPTX (Office Open XML) | `SaveFormat.PPTX` | Yes |
| PDF | N/A | No |
| HTML | N/A | No |
| SVG | N/A | No |
| PNG / JPEG | N/A | No |
| ODP (OpenDocument) | N/A | No |

Only PPTX is supported. Attempting to save in any other format will raise `NotImplementedError` or an unsupported format error.

---

## Common Issues and Fixes

**`PermissionError: [Errno 13] Permission denied`**

The output file is open in another application (e.g., PowerPoint has the file open). Close the file in other applications before saving.

**File is created but appears empty or corrupted**

Ensure `prs.save()` is called inside the `with` block, not after it. After the `with` block exits, the `Presentation` object is disposed and subsequent calls will fail silently or raise an error.

**`NotImplementedError` when saving**

This occurs when attempting a save format other than PPTX, or when using an unsupported feature (such as charts or animations) during save.

---

## Frequently Asked Questions

**Can I save to the same file I opened?**

Yes. Saving to the same path overwrites the original file:

```python
with slides.Presentation("deck.pptx") as prs:
    # modify ...
    prs.save("deck.pptx", SaveFormat.PPTX)  # overwrites original
```

**Can I save to a bytes buffer instead of a file?**

Saving directly to `io.BytesIO` is not supported in the current API. Save to a temporary file and read the bytes:

```python
import tempfile, os

with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
    tmp_path = tmp.name

with slides.Presentation() as prs:
    prs.save(tmp_path, SaveFormat.PPTX)

with open(tmp_path, "rb") as f:
    pptx_bytes = f.read()

os.unlink(tmp_path)
```

**Does saving preserve content I haven't modified?**

Yes. Unknown XML parts from the original file are preserved verbatim. The library only serializes the parts of the document model it understands, and passes through any XML it does not recognize.

---

## See Also

- [How to Create Presentations in Python](/kb.aspose.org/slides/python/how-to-create-presentations-python/)
- [How to Load Presentations in Python](/kb.aspose.org/slides/python/how-to-load-presentations-python/)
- [Features Overview](/docs.aspose.org/slides/python/developer-guide/features/)
- [API Reference](/reference.aspose.org/slides/python/)
