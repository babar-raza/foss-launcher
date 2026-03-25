---
canonical: https://kb.aspose.org/slides/python/faq/
canonical_import: aspose.slides
code_import: aspose.slides
date: '2026-03-24T16:56:57Z'
dateModified: '2026-03-24T16:56:57Z'
datePublished: '2026-03-24T16:56:57Z'
description: This permissive open-source license allows you to use, modify, and distribute
  the library in both personal and commercial projects without restriction,...
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
page_role: faq
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FAQ | Guide
slug: faq
title: Aspose.Slides FAQ
type: faq
url: /kb.aspose.org/slides/python/faq/
weight: 8
---

## Frequently Asked Questions

Aspose.Slides for Python is distributed under the MIT License. This permissive open-source license allows you to use, modify, and distribute the library in both personal and commercial projects without restriction, provided the original copyright notice and license text are included.

Yes, you can create and manipulate PowerPoint (.pptx) files using Aspose.Slides for Python. The library supports full round-trip fidelity for .pptx files, enabling you to open existing presentations, modify slides and shapes, and save the updated file.

```python
import aspose.slides

presentation = aspose.slides.Presentation()
presentation.save("output.pptx")
```

To `add` text to `a` slide, create `a` new slide, `add` an `AutoShape`, and set its text content using the text_frame property. The `AutoShape` class provides the `add_text_frame()` method to initialize `a` text container, and you can then populate it with paragraphs and portions.

Aspose.Slides supports exporting presentations to PDF, `images`, and other formats via the save() method on the `Presentation` class. Pass `a` file path and `a` format enum (e.`g`., `SaveFormat.PDF`) to control the output type.

The `Presentation` class is the main entry point for working with PowerPoint files. It provides access to slides, `masters`, layout slides, and document properties. Call save() to persist changes and `dispose()` to release resources when finished.

## See Also

- [Convert file formats](/kb.aspose.org/slides/python/how-to-convert-png-to-pptx-python/)
- [Fix common errors](/kb.aspose.org/slides/python/how-to-fix-presentations-errors-python/)
- [Load files](/kb.aspose.org/slides/python/how-to-load-presentations-python/)
- [Optimize performance](/kb.aspose.org/slides/python/how-to-optimize-presentations-python/)
- [Save files](/kb.aspose.org/slides/python/how-to-save-presentations-python/)
