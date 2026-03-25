---
canonical: https://reference.aspose.org/slides/_index/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: Developers can create, load, and save PowerPoint files with fidelity,
  manage slide content, and apply formatting via classes like `BasePortionFormat`,...
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
page_role: toc
platform: dotnet
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Slides Reference _Index
slug: _index
title: Reference _Index
type: toc
url: /reference.aspose.org/slides/_index/
weight: 5
---

## Capabilities

This section covers the core capabilities of Aspose.Slides for .NET, focusing on presentation file handling, slide manipulation, and shape/text formatting using the documented API surface. Developers can create, load, and save PowerPoint files with fidelity, manage slide content, and apply formatting via classes like `BasePortionFormat`, `BulletFormat`, `FillFormat`, and `ColorFormat`.

- Load and save `.pptx` presentations with full round-trip support
- Add, remove, clone, and reorder slides in a presentation
- Create and format shapes including auto shapes, picture frames, tables, and connectors
- Apply text formatting at portion, paragraph, and text frame levels using `BasePortionFormat` and `BulletFormat`
- Configure fill and color properties via `FillFormat`, `ColorFormat`, and GradientStopCollection
- Manage comments and document properties using `CommentCollection`, `Comment`, and `DocumentProperties`

## Quick Install

This section covers installation and setup for Aspose.Slides on .NET. Install the package via NuGet, then reference the library using the canonical import `using Aspose.Slides;`.

```bash
dotnet add package Aspose.Slides
```

After installation, verify the setup by creating a new presentation, adding a slide, and saving it as a .pptx file. This confirms the core presentation I/O functionality is working correctly.

## Getting Started

This section covers the .NET API for presentation creation, reading, and manipulation using Aspose.Slides. It includes core classes such as `BasePortionFormat`, `BulletFormat`, `Camera`, `ColorFormat`, `Comment`, `CommentCollection`, `DocumentProperties`, `EffectFormat`, `FillFormat`, GradientStop, GradientStopCollection, IComment, IDocumentProperties, IImage, and Image.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
presentation.Save("output.pptx", SaveFormat.Pptx);
```

## Developer Guide

This section covers the .NET API surface for Aspose.Slides, focusing on core classes used to manipulate presentation elements. Developers work directly with low-level XML-backed objects such as `BasePortionFormat`, `BulletFormat`, `ColorFormat`, `FillFormat`, and `EffectFormat` to read and write formatting attributes.

Key operations include accessing slide content via `Comment`, `CommentCollection`, and `DocumentProperties`, and managing visual properties through GradientStop, GradientStopCollection, and camera settings via `Camera`. All formatting changes are persisted using the Save() method on the respective element.

- Formatting: `BasePortionFormat`, `BulletFormat`, `ColorFormat`, `FillFormat`, `EffectFormat`
- Slide content: `Comment`, `CommentCollection`, `DocumentProperties`
- 3D and visual effects: `Camera`, GradientStop, GradientStopCollection

## See Also

- Presentation I/O — open, create, and save `.pptx` files with full round-trip fidelity
- Slides — add, remove, clone, reorder, and iterate slides
- Shapes — auto shapes, picture frames, tables, connectors
- Text — text frames, paragraphs, portions with character, paragraph, and text frame formatting (including bullets)
- Fill — solid, gradient, pattern, and picture fills
