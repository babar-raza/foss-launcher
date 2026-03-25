---
canonical: https://kb.aspose.org/slides/python/troubleshooting/
canonical_import: aspose.slides
code_import: aspose.slides
date: '2026-03-24T16:56:57Z'
dateModified: '2026-03-24T16:56:57Z'
datePublished: '2026-03-24T16:56:57Z'
description: Aspose.Slides only supports `.pptx` and legacy `.ppt` formats; other
  formats like `.odp` or `.key` will trigger this error.
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
page_role: troubleshooting
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides Troubleshooting
slug: troubleshooting
title: Troubleshooting
type: troubleshooting
url: /kb.aspose.org/slides/python/troubleshooting/
weight: 9
---

## Common Issues

If `Presentation()` raises FileFormatException, the input file is either corrupted or in an unsupported format. Aspose.Slides only supports `.pptx` and legacy `.ppt` formats; other formats like `.odp` or `.key` will trigger this error.

```python
import aspose.slides

try:
    pres = aspose.slides.Presentation("input.pptx")
except Exception as e:
    print(f"Error: {e}")
```

If `pres.save("output.pptx")` raises NotImplementedError, the export path uses an unimplemented feature. Specifically, updating content types during format conversion is not yet supported and will raise this error when attempting certain export operations.

If `pres.slides` returns an empty collection despite expecting slides, verify the source file `contains` slides and was loaded without error. The slides property on `Presentation` is read-only and reflects the actual slide `count` in the loaded document.

If text formatting fails silently, ensure you access `AutoShape.text_frame` before modifying content. The text_frame property is read-only and returns `ITextFrame`; calling `add_text_frame()` is required to initialize it.

```python
import aspose.slides

pres = aspose.slides.Presentation()
slide = pres.slides[0]
shape = slide.shapes.add_auto_shape(aspose.slides.ShapeType.RECTANGLE, 50, 50, 300, 100)
text_frame = shape.add_text_frame("Hello World")
```

## Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| `FileFormatException: Unknown file format` | File is not `a` valid `.pptx` or `.ppt` | Check the file extension; convert external formats to `.pptx` using PowerPoint before loading |
| NullPointerException on `presentation.slides` | `Presentation` object was not initialized correctly | Instantiate with `Presentation(path)` before accessing slides |
| NotImplementedError | Attempting to use an unimplemented feature (e.`g`., updating content types during export) | Avoid format conversion workflows that modify content types; use save() with explicit `SaveFormat` where supported |
| `IOException: Access to the path is denied` | File is locked by another process or write permissions are missing | Close other applications using the file; run the script with appropriate permissions |
| `TypeError: 'NoneType' object is not subscriptable` on `slide.shapes[0]` | `Slide` has no shapes or index is out of range | Call `shapes.count` first to verify shape `count` before indexing |

## Getting Help

If `Presentation` fails to load or save `a` file, verify the file path and format support. Check that the input file is `a` valid `.pptx` or supported legacy format, and ensure you use `import aspose.slides` to avoid import errors.

- Report bugs or request features on the [Aspose.Slides GitHub issues page](https://github.com/aspose-slides/aspose-slides-python)
- Browse the [Aspose.Slides Python documentation]( for API references and usage examples
- Search or ask questions on Stack Overflow using tags python, `slides-python`, or `python-slides-pptx`

## See Also

- [API reference documentation](/reference.aspose.org/slides/python/api-overview/)
- [3D shape formatting details](/blog.aspose.org/slides/python/introducing-slides-foss-python/)
- [Key features overview](/blog.aspose.org/slides/python/slides-key-features/)
- [Getting started guide](/docs.aspose.org/slides/python/developer-guide/getting-started/)
- [Create presentations step-by-step](/docs.aspose.org/slides/python/developer-guide/presentation-creation/)
