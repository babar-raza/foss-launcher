---
canonical: https://docs.aspose.org/slides/python/developer-guide/slide-manipulation/
canonical_import: aspose.slides
code_import: aspose.slides
date: '2026-03-24T16:56:57Z'
dateModified: '2026-03-24T16:56:57Z'
datePublished: '2026-03-24T16:56:57Z'
description: You start with `a` `.pptx` file or `a` blank presentation, manipulate
  slides and shapes, then export the result to another format.
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
page_role: workflow_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Work with Slides with Aspose.Slides | Guide
slug: slide-manipulation
title: Work with Slides with Aspose.Slides
type: workflow_page
url: /docs.aspose.org/slides/python/developer-guide/slide-manipulation/
weight: 19
---

## Overview

This guide walks you through creating, loading, and saving PowerPoint presentations using Aspose.Slides for Python. You start with `a` `.pptx` file or `a` blank presentation, manipulate slides and shapes, then export the result to another format.

First, install Aspose.Slides via pip and import it as `aspose.slides`. Then instantiate `a` `Presentation` object to load an existing file or create `a` new one. Use the slides collection to `add`, remove, or reorder slides. Finally, call save() with `a` filename and optional format to persist changes.

```python
import aspose.slides

# Load an existing presentation
presentation = aspose.slides.Presentation("input.pptx")

# Add a new slide using the first layout slide
slide = presentation.slides.add_empty_slide(presentation.layout_slides[0])

# Save the updated presentation
presentation.save("output.pptx", aspose.slides.SaveFormat.PPTX)
```

- Use this approach when updating slide decks with new content programmatically.
- Use this approach when generating presentation templates for reports or proposals.
- Use this approach when converting legacy `.ppt` files to modern `.pptx` format.

## Working with Data

This guide walks you through reading, writing, and modifying data elements in PowerPoint presentations using Aspose.Slides. You load `a` `.pptx` file, access slide content such as shapes and text frames, update data like cell values in tables or shape text, and save the modified presentation.

```python
import aspose.slides

# Load an existing presentation
presentation = aspose.slides.Presentation("input.pptx")

# Access the first slide
slide = presentation.slides[0]

# Access shapes on the slide
shapes = slide.shapes

# Save the presentation with changes
presentation.save("output.pptx", aspose.slides.SaveFormat.PPTX)
```

- Use this approach when updating slide content programmatically before distribution.
- Apply this pattern when generating dynamic reports from templates.
- Leverage this workflow to batch-process presentations with consistent data updates.

To read data, access `AutoShape` objects and extract text from their text_frame. To write data, set the `text_frame.text` property directly. For tables, use `Cell` and `Column` collections to read or update cell values. Each operation preserves formatting and layout fidelity.

```python
import aspose.slides

# Load presentation
presentation = aspose.slides.Presentation("input.pptx")
slide = presentation.slides[0]

# Read text from first AutoShape
if isinstance(slide.shapes[0], aspose.slides.AutoShape):
    shape = slide.shapes[0]
    text = shape.text_frame.text
    print("Shape text:", text)

# Write new text to the same shape
shape.text_frame.text = "Updated content"

# Save updated presentation
presentation.save("output.pptx", aspose.slides.SaveFormat.PPTX)
```

- Use this approach when extracting slide notes or content for indexing.
- Apply this pattern when correcting typos or updating branding text across slides.
- Leverage this workflow to audit or validate text content in presentations.

To modify tabular data, access the `CellCollection` through `a` table shape. Update individual `Cell` values using the `text_frame.text` property. This enables dynamic report generation or data refresh from external sources.

```python
import aspose.slides

# Load presentation
presentation = aspose.slides.Presentation("input.pptx")
slide = presentation.slides[0]

# Access first table shape (assumed to be at index 1)
table_shape = slide.shapes[1]
table = table_shape.table

# Read value from first cell
cell = table.rows[0].cells[0]
original_value = cell.text_frame.text
print("Original cell value:", original_value)

# Update cell value
cell.text_frame.text = "New value"

# Save updated presentation
presentation.save("output.pptx", aspose.slides.SaveFormat.PPTX)
```

- Use this approach when refreshing data in embedded tables from CSV or database sources.
- Apply this pattern when generating invoices or statements with variable line items.
- Leverage this workflow to standardize formatting across multiple table cells.

Always call `dispose()` after processing to release resources, especially in loops or long-running scripts. Use `SaveFormat.PPTX` to preserve full fidelity when saving back to the native format.

For best results, validate shape types before casting to avoid runtime errors. When working with tables, ensure row and column indices are within bounds before accessing cells.

Q: Can I modify text in `a` table cell without affecting formatting? A: Yes — setting `cell.text_frame.text` replaces only the content, preserving existing paragraph and portion formatting.

Q: Does Aspose.Slides support reading and writing data in `.ppt` files? A: Yes — the `Presentation` class handles both `.pptx` and legacy `.ppt` formats with the same API surface.

## Code Examples

This guide walks you through creating and manipulating slides in `a` PowerPoint presentation using Aspose.Slides. You start with `a` blank presentation, `add` `a` slide with `a` title and shape, then save it as `a` .pptx file.

```python
import aspose.slides

# Create a new presentation
presentation = aspose.slides.Presentation()

# Add a blank slide
slide = presentation.slides.add_empty_slide(presentation.layout_slides.get_by_type(aspose.slides.SlideLayoutType.BLANK))

# Add a rectangle AutoShape
shape = slide.shapes.add_auto_shape(aspose.slides.ShapeType.RECTANGLE, 100, 100, 300, 150)
shape.text_frame.add_text_frame("Welcome to Aspose.Slides")

# Save the presentation
presentation.save("output.pptx", aspose.slides.SaveFormat.PPTX)
```

- Use `add_empty_slide()` to insert a new slide with a specified layout type.
- Add `AutoShape` objects to a slide’s shapes collection to include geometric elements.
- Call save() with `SaveFormat.PPTX` to persist the presentation in modern PowerPoint format.

Next, load an existing presentation, modify its first slide, and export it to PDF. This demonstrates round-trip fidelity and format conversion.

```python
import aspose.slides

# Load an existing presentation
presentation = aspose.slides.Presentation("input.pptx")

# Access the first slide
slide = presentation.slides[0]

# Add a text box with formatted content
shape = slide.shapes.add_auto_shape(aspose.slides.ShapeType.TEXT_BOX, 50, 250, 400, 50)
text_frame = shape.text_frame
text_frame.text = "Updated at runtime"

# Save as PDF
presentation.save("output.pdf", aspose.slides.SaveFormat.PDF)
```

- Use `Presentation(filename)` to open a .pptx file for editing.
- Access slides via zero-based indexing on the slides collection.
- Export to PDF using save() with `SaveFormat.PDF` for archival or sharing.

Finally, `clone` `a` slide from one presentation to another and preserve formatting during the transfer.

```python
import aspose.slides

# Load source and target presentations
source_pres = aspose.slides.Presentation("source.pptx")
target_pres = aspose.slides.Presentation("target.pptx")

# Clone the second slide from source to target
target_pres.slides.insert_clone(0, source_pres.slides[1])

# Save the updated target presentation
target_pres.save("merged.pptx", aspose.slides.SaveFormat.PPTX)
```

- Use `insert_clone()` to copy a slide while preserving layout, content, and formatting.
- This approach works reliably for building slide decks from templates or components.
- Both source and target presentations remain independent after cloning.

## Notes and Best Practices

When working with slides in Python using Aspose.Slides, managing memory efficiently and avoiding common pitfalls ensures stable, scalable automation. This section covers critical `notes` for developers building production-grade slide processing workflows.

- Always call save() explicitly to flush buffers and write output files—do not rely on garbage collection.
- Reuse `Presentation` instances when processing multiple slides in batch to reduce memory overhead.
- Avoid holding references to disposed slides or shapes; release them promptly after use.
- For large presentations, prefer streaming save formats where supported and avoid loading full documents into memory unnecessarily.

## See Also

- [3D shape formatting support](/blog.aspose.org/slides/python/introducing-slides-foss-python/)
- [Key features overview](/blog.aspose.org/slides/python/slides-key-features/)
- [Create presentations from scratch](/docs.aspose.org/slides/python/developer-guide/presentation-creation/)
- [Convert file formats easily](/kb.aspose.org/slides/python/how-to-convert-png-to-pptx-python/)
- [Fix common errors quickly](/kb.aspose.org/slides/python/how-to-fix-presentations-errors-python/)
