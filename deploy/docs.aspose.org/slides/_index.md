---
canonical: https://docs.aspose.org/slides/_index/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: All operations rely on the canonical `using Aspose.Slides;` namespace.
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
seoTitle: Aspose.Slides Docs _Index
slug: _index
title: Docs _Index
type: toc
url: /docs.aspose.org/slides/_index/
weight: 2
---

## Capabilities

This section covers the core capabilities of Aspose.Slides for .NET, focusing on presentation file handling, slide management, and shape/text formatting using the documented API surface. All operations rely on the canonical `using Aspose.Slides;` namespace.

- Load, create, and save `.pptx` presentations with full fidelity using Presentation and related package-level operations
- Manage slides: add, remove, clone, reorder, and iterate via `AddEmptySlide`, `AddClone`, and slide reference methods
- Work with shapes: auto shapes, picture frames, tables, and connectors using `AddAutoShape`, `AddPictureFrame`, `AddTable`, and `AddConnector`
- Format text at portion, paragraph, and text frame levels using `BasePortionFormat`, `BulletFormat`, and `FillFormat`
- Apply fill types (solid, gradient, pattern, picture) and effects via `FillFormat`, GradientStopCollection, and `EffectFormat`

## Quick Install

This section covers installation and setup for Aspose.Slides on .NET. Aspose.Slides provides classes such as `BasePortionFormat`, `BulletFormat`, `Camera`, `ColorFormat`, `Comment`, `CommentCollection`, `DocumentProperties`, `EffectFormat`, `FillFormat`, GradientStop, GradientStopCollection, IComment, IDocumentProperties, IImage, and Image for working with presentations programmatically.

```bash
dotnet add package Aspose.Slides
```

After installation, verify the package is correctly referenced by adding `using Aspose.Slides;` at the top of your C# file and compiling a minimal project. No additional configuration or post-install steps are required.

## Getting Started

This section covers the .NET API for presentation creation, reading, and manipulation using Aspose.Slides. It includes core classes such as `BasePortionFormat`, `BulletFormat`, `Camera`, `ColorFormat`, `Comment`, `CommentCollection`, `DocumentProperties`, `EffectFormat`, `FillFormat`, GradientStop, GradientStopCollection, IComment, IDocumentProperties, IImage, and Image.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
presentation.Save("output.pptx", SaveFormat.Pptx);
```

## Developer Guide

This section covers the .NET API for presentation processing using Aspose.Slides, focusing on core classes for slide, shape, text, and formatting operations. Developers work directly with Slide, ShapeCollection, TextFrame, Portion, and `FillFormat` to build, modify, and export presentations.

Key operations include loading and saving presentations, adding slides and shapes, applying fills and effects, and managing text formatting through `BulletFormat`, `BasePortionFormat`, and `EffectFormat`. The API supports programmatic control over camera presets, gradient stops, and comment authoring via `Camera`, GradientStopCollection, and `CommentCollection`.

- Create and manipulate slides, shapes, and text frames
- Apply solid, gradient, and picture fills using `FillFormat`
- Configure bullets and text formatting with `BulletFormat` and `BasePortionFormat`
- Add and manage comments via `Comment` and `CommentCollection`
- Control 3D camera settings and effects using `Camera` and `EffectFormat`

## See Also

This section covers the Aspose.Slides .NET API surface for presentation authoring, including slide, shape, text, and formatting operations.

- Working with slides — add, remove, clone, and reorder slides in a presentation
- Managing shapes — insert and configure auto shapes, picture frames, tables, and connectors
- Text formatting — apply character, paragraph, and text frame formatting using `BasePortionFormat`, `BulletFormat`, and `FillFormat`
- Slide effects and 3D — configure camera presets, bevels, and gradient fills via `Camera`, `EffectFormat`, and GradientStopCollection
- Comments and metadata — add comments via `Comment` and `CommentCollection`, and manage document properties via `DocumentProperties`
