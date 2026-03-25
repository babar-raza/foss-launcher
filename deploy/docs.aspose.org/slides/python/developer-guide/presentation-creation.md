---
canonical: https://docs.aspose.org/slides/python/developer-guide/presentation-creation/
canonical_import: aspose.slides
code_import: aspose.slides
date: '2026-03-24T16:56:57Z'
dateModified: '2026-03-24T16:56:57Z'
datePublished: '2026-03-24T16:56:57Z'
description: You start with `a` blank presentation, `add` content like shapes and
  text, then export it to `a` standard format such as PPTX.
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
seoTitle: Create Presentations with Aspose.Slides | Guide
slug: presentation-creation
title: Create Presentations with Aspose.Slides
type: workflow_page
url: /docs.aspose.org/slides/python/developer-guide/presentation-creation/
weight: 18
---

## Overview

This guide walks you through creating and saving PowerPoint presentations using Aspose.Slides for Python. You start with `a` blank presentation, `add` content like shapes and text, then export it to `a` standard format such as PPTX.

```python
import aspose.slides

# Create a new presentation
presentation = aspose.slides.Presentation()

# Save it to a .pptx file
presentation.save("output.pptx", aspose.slides.SaveFormat.PPTX)

# Release resources
presentation.dispose()
```

- Use this approach when generating reports from templates programmatically.
- Use this approach when building slide decks for automated presentations.
- Use this approach when preparing presentations for archival or sharing in standard PPTX format.

The `Presentation` class serves as the entry point for working with slides. It exposes collections like slides, `masters`, and `layout_slides` for structured content management. After instantiation, you can `add` shapes, format text, and apply layouts before saving.

```python
import aspose.slides

# Create a new presentation
presentation = aspose.slides.Presentation()

# Access the first slide
slide = presentation.slides[0]

# Add a rectangle AutoShape
shape = slide.shapes.add_auto_shape(aspose.slides.ShapeType.RECTANGLE, 100, 100, 200, 100)

# Save the presentation
presentation.save("with_shape.pptx", aspose.slides.SaveFormat.PPTX)
presentation.dispose()
```

- Use this approach when inserting geometric shapes for diagrams or visual anchors.
- Use this approach when building slide layouts with consistent positioning.
- Use this approach when preparing presentations for further editing in PowerPoint.

## Working with Data

Aspose.Slides -- Core data manipulation operations: reading, writing, modifying cells/sheets/elements with code examples for each.

For details on working with data, see the Aspose.Slides documentation.

## Code Examples

This guide walks you through creating and saving a basic PowerPoint presentation using Aspose.Slides. You start by instantiating a `Presentation` object, add a slide, insert an `AutoShape` with text, and save the result as a `.pptx` file.

```python
import aspose.slides

# Create a new presentation
presentation = aspose.slides.Presentation()

# Add a blank slide
slide = presentation.slides.add_empty_slide(presentation.slides.get_count())

# Add an AutoShape (rectangle) to the slide
shape = slide.shapes.add_auto_shape(aspose.slides.ShapeType.RECTANGLE, 100, 100, 300, 150)

# Add text to the shape
text_frame = shape.add_text_frame("Hello, Aspose.Slides!")

# Save the presentation
presentation.save("output.pptx", aspose.slides.SaveFormat.PPTX)
```

- Use this approach when generating dynamic slide decks from data sources.
- Use `add_empty_slide()` to insert slides at specific positions using index.
- Use `add_auto_shape()` with `ShapeType.RECTANGLE` to create text containers.

Next, you can customize the shape's fill and text formatting using `FillFormat`, `IFillFormat`, and `BulletFormat`. The `AutoShape` exposes its `text_frame`, which contains paragraphs and portions for granular control.

```python
import aspose.slides

presentation = aspose.slides.Presentation()
slide = presentation.slides.add_empty_slide(presentation.slides.get_count())

# Add a rounded rectangle shape
shape = slide.shapes.add_auto_shape(aspose.slides.ShapeType.ROUNDED_RECTANGLE, 150, 120, 350, 180)

# Set solid fill color
shape.fill_format.fill_type = aspose.slides.FillType.SOLID
shape.fill_format.solid_fill_color.color = aspose.slides.Color.from_argb(255, 200, 220, 255)

# Add formatted text
text_frame = shape.add_text_frame("Formatted Text")
paragraph = text_frame.paragraphs[0]
portion = paragraph.portions[0]
portion.portion_format.fill_format.fill_type = aspose.slides.FillType.SOLID
portion.portion_format.fill_format.solid_fill_color.color = aspose.slides.Color.black

# Save the presentation
presentation.save("formatted_output.pptx", aspose.slides.SaveFormat.PPTX)
```

- Set `FillType.SOLID` and `solid_fill_color` to apply background color to shapes.
- Use `portion_format.fill_format` to style text color independently of shape fill.
- Access `text_frame.paragraphs[0]` and `portions[0]` to modify text at the smallest unit.

Finally, you can export the presentation to PDF using the same `save()` method with `SaveFormat.PDF`. This enables direct conversion from in-memory presentations to shareable formats.

```python
import aspose.slides

presentation = aspose.slides.Presentation("formatted_output.pptx")

# Export to PDF
presentation.save("output.pdf", aspose.slides.SaveFormat.PDF)

# Clean up resources
presentation.dispose()
```

- Use `SaveFormat.PDF` to convert presentations to portable documents.
- Call `dispose()` after saving to release unmanaged resources.
- Load existing `.pptx` files by passing the path to the `Presentation` constructor.

## Notes and Best Practices

When using Aspose.Slides for Python via .NET, developers should prioritize memory efficiency and correct resource handling to avoid performance degradation in production environments. The library loads entire presentations into memory, so large files or batch operations require careful management to prevent out-of-memory errors.

- Use `Presentation` objects within `with` statements to ensure automatic disposal of unmanaged resources.
- Avoid keeping multiple `Presentation` instances open simultaneously—dispose of them explicitly using `dispose()` when done.
- For batch processing, process one presentation at a time and release references before loading the next file.
- Prefer streaming operations where possible, such as saving directly to streams instead of intermediate files.

{{< callout >}}
Note: The `NotImplementedError` will be raised for unsupported features like content type updates during format conversion. Always test export paths thoroughly before deployment.
{{< /callout >}}

## See Also

- [Explore 3D shape formatting](/blog.aspose.org/slides/python/introducing-slides-foss-python/)
- [Discover key features](/blog.aspose.org/slides/python/slides-key-features/)
- [Learn slide manipulation](/docs.aspose.org/slides/python/developer-guide/slide-manipulation/)
- [Convert file formats](/kb.aspose.org/slides/python/how-to-convert-png-to-pptx-python/)
- [Fix common errors](/kb.aspose.org/slides/python/how-to-fix-presentations-errors-python/)
