---
canonical: https://kb.aspose.org/slides/dotnet/faq/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: These limitations are explicitly documented in the product README and
  reflect current development priorities. Developers should avoid relying on these...
display_name: Aspose.Slides
family: slides
keywords:
- python slides
- python slides for beginners
- python slideshare
- python slideshow
- python slides ppt
- python slides pdf
- python slideshow py
- python slideshow with transitions
lastmod: '2026-03-24T17:07:48Z'
page_role: faq
platform: dotnet
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FAQ | Guide
slug: faq
title: Aspose.Slides FAQ
type: faq
url: /kb.aspose.org/slides/dotnet/faq/
weight: 8
---

## Frequently Asked Questions

### What features are currently not implemented in Aspose.Slides?

The following areas are not yet implemented: advanced 3D rendering, animation timeline editing, and certain slide master customizations. These limitations are explicitly documented in the product README and reflect current development priorities. Developers should avoid relying on these features for production workflows until future releases support them.

### Can I use Aspose.Slides in a .NET application?

Yes, Aspose.Slides is designed for .NET applications and supports full integration with C# and VB.NET projects. Use the canonical import `using Aspose.Slides;` at the top of your source file to access all presentation manipulation capabilities. The library is optimized for server-side and desktop use cases without requiring Microsoft PowerPoint.

### How do I add a new slide to a presentation?

Call `AddEmptySlide()` on the presentation's slides collection to insert a new blank slide at the end. You can then add shapes, text, or other content to the returned `BaseSlide` instance. This method ensures proper slide indexing and maintains presentation structure integrity.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
presentation.Slides.AddEmptySlide();
presentation.Save("output.pptx", SaveFormat.Pptx);
```

### Does Aspose.Slides support text formatting with bullets?

Yes, bullet formatting is fully supported through the `BulletFormat` class and related APIs. You can set bullet type, size, color, and alignment for paragraphs within text frames. Bullets are applied at the paragraph level and persist when saving to `.pptx`.

### What file formats does Aspose.Slides support?

Aspose.Slides supports reading and writing `.pptx` files with full fidelity. It does not natively support older `.ppt` formats or conversion to PDF, images, or other formats in this release. Developers targeting those outputs should consider using additional tools or waiting for future versions.

## See Also

Aspose.Slides for .NET supports core presentation operations including opening, creating, and saving .pptx files, adding and manipulating slides, and working with shapes, text, and formatting. The API surface is limited to the documented classes and methods — any functionality not explicitly listed in the API SURFACE is not implemented. According to the product's known limitations, certain advanced features remain unsupported and are not yet implemented.

- [Troubleshooting common issues](/kb.aspose.org/slides/dotnet/troubleshooting/)
- [Convert file formats guide](/kb.aspose.org/slides/dotnet/how-to-convert-png-to-pptx-dotnet/)
- [Fix common errors](/kb.aspose.org/slides/dotnet/how-to-fix-presentations-errors-dotnet/)
- [Load files step-by-step](/kb.aspose.org/slides/dotnet/how-to-load-presentations-dotnet/)
- [Optimize performance tips](/kb.aspose.org/slides/dotnet/how-to-optimize-presentations-dotnet/)
