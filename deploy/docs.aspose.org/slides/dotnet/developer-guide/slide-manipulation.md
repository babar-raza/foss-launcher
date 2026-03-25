---
canonical: https://docs.aspose.org/slides/dotnet/developer-guide/slide-manipulation/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: The workflow starts with a `.pptx` file as input and ends with a modified
  `.pptx` file as output, using core slide and shape management capabilities.
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
page_role: workflow_page
platform: dotnet
reading_time: 1
robots: index, follow
seoTitle: Work with Slides with Aspose.Slides | Guide
slug: slide-manipulation
title: Work with Slides with Aspose.Slides
type: workflow_page
url: /docs.aspose.org/slides/dotnet/developer-guide/slide-manipulation/
weight: 19
---

## Overview

This guide walks you through working with slides in Aspose.Slides for .NET—loading a presentation, accessing its slides, and saving changes. The workflow starts with a `.pptx` file as input and ends with a modified `.pptx` file as output, using core slide and shape management capabilities.

```csharp
using Aspose.Slides;

// Load an existing presentation
using var presentation = new Presentation("input.pptx");

// Access the first slide
var slide = presentation.Slides[0];

// Save the modified presentation
presentation.Save("output.pptx", SaveFormat.Pptx);
```

- Use this approach when updating slide content in batch processing pipelines.
- Apply when cloning slides between presentations for template reuse.
- Use this pattern when iterating slides to inspect or modify shapes and text.

## Working with Data

This guide walks you through reading, writing, and modifying data elements in Aspose.Slides presentations. You start with a `.pptx` file, extract or update structured content such as text, fills, and formatting, and save the modified presentation—enabling programmatic control over slide data for reporting, automation, or integration workflows.

Aspose.Slides exposes core data manipulation capabilities through classes like `BasePortionFormat`, `BulletFormat`, `FillFormat`, `ColorFormat`, and GradientStopCollection. These allow you to inspect and adjust formatting attributes, bullet styles, and color properties directly on slide elements.

```csharp
using Aspose.Slides;

var presentation = new Presentation("input.pptx");
var slide = presentation.Slides[0];
var shape = slide.Shapes[0] as AutoShape;
var textFrame = shape.TextFrame;
var portion = textFrame.Paragraphs[0].Portions[0];
var format = portion.PortionFormat;
format.FillFormat.FillType = FillType.Solid;
format.FillFormat.SolidFillColor.Color = System.Drawing.Color.Red;
presentation.Save("output.pptx", SaveFormat.Pptx);
```

- Use this approach when applying consistent branding colors to text across multiple slides.
- Apply dynamic fill updates to shapes based on data-driven conditions (e.g., status indicators).
- Modify portion formatting before exporting to PDF or image formats to ensure visual fidelity.

To read bullet formatting, access the `BulletFormat` object from a paragraph. The Type() method returns the bullet style (e.g., Symbol, Numbered, or `None`), and InsertPprChild() lets you add missing XML elements for bullet configuration.

```csharp
using Aspose.Slides;

var presentation = new Presentation("input.pptx");
var slide = presentation.Slides[0];
var shape = slide.Shapes[0] as AutoShape;
var textFrame = shape.TextFrame;
var paragraph = textFrame.Paragraphs[0];
var bullet = paragraph.ParagraphFormat.Bullet;
var bulletType = bullet.Type();
if (bulletType == BulletType.Symbol)
{
    bullet.InsertPprChild("buChar");
}
presentation.Save("output.pptx", SaveFormat.Pptx);
```

- Use this to detect and normalize bullet styles before generating standardized reports.
- Rebuild missing bullet XML nodes when importing presentations with malformed formatting.
- Convert numbered lists to symbolic ones for localization or accessibility compliance.

Gradient fills are managed via GradientStopCollection, which holds color stops and their positions. `Add` new stops using `Add(position, color)` and persist changes with Save() on the parent slide part.

```csharp
using Aspose.Slides;

var presentation = new Presentation("input.pptx");
var slide = presentation.Slides[0];
var shape = slide.Shapes[0] as AutoShape;
var fillFormat = shape.FillFormat;
var gradientStops = fillFormat.GradientStops;
gradientStops.Add(0.0f, System.Drawing.Color.Blue);
gradientStops.Add(1.0f, System.Drawing.Color.Yellow);
fillFormat.Save();
presentation.Save("output.pptx", SaveFormat.Pptx);
```

- Apply multi-stop gradients to highlight key sections in marketing decks.
- Dynamically generate gradient fills based on data ranges (e.g., heatmaps).
- Ensure gradient fidelity when converting to image formats for web use.

## Code Examples

This guide walks you through creating and manipulating slides in a PowerPoint presentation using Aspose.Slides for .NET. You start by loading or creating a presentation, then add a new slide, insert a shape, and save the result — all using only the documented API surface.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
var slide = presentation.Slides.AddEmptySlide(presentation.LayoutSlides[0]);
var autoShape = slide.Shapes.AddAutoShape(ShapeType.Rectangle, 100, 100, 300, 150);
autoShape.FillFormat.FillType = FillType.Solid;
autoShape.FillFormat.SolidFillColor.Color = Color.Red;
presentation.Save("output.pptx", SaveFormat.Pptx);
```

- Use `AddEmptySlide()` to insert a new slide based on a layout slide.
- Apply `AddAutoShape()` to place a rectangle with defined position and dimensions.
- Set `FillType` and SolidFillColor to configure the shape’s fill appearance.

Next, add text to the shape using the TextFrame and Portion objects. The TextFrame holds paragraphs, and each Paragraph contains one or more Portion objects with formatting. Only documented methods from the API surface are used.

```csharp
var textFrame = autoShape.TextFrame;
var paragraph = textFrame.Paragraphs.Add();
var portion = paragraph.Portions.Add();
portion.Text = "Hello, Aspose.Slides!";
portion.PortionFormat.FontHeight = 24;
portion.PortionFormat.FillFormat.FillType = FillType.Solid;
portion.PortionFormat.FillFormat.SolidFillColor.Color = Color.White;
presentation.Save("output_with_text.pptx", SaveFormat.Pptx);
```

- Use `TextFrame.Paragraphs.Add()` to create a new paragraph inside the shape.
- Call `Portions.Add()` to add a text portion and set its content via Text.
- Apply font size and fill color using PortionFormat properties.

Finally, attach a comment to the slide using the `Comments` collection. Each comment includes author, timestamp, and text — all accessible through the IComment interface.

```csharp
var commentAuthor = presentation.Comments.AddAuthor("John Doe", "JD");
var comment = presentation.Comments.AddComment(slide, new PointF(200, 200), "Review this shape.", commentAuthor, DateTime.Now);
comment.Text = "Please verify dimensions.";
presentation.Save("output_with_comment.pptx", SaveFormat.Pptx);
```

- Call `AddAuthor()` to register a comment author before adding comments.
- Use `AddComment()` to attach a comment to a specific slide at a given point.
- Modify the comment text via the Text() method on the IComment instance.

## Notes and Best Practices

When working with Aspose.Slides in .NET, managing memory efficiently and avoiding common pitfalls ensures stable performance during slide processing. Always dispose of Presentation objects after use to release unmanaged resources, especially when processing large presentations or running batch operations.

- Call `Presentation.Dispose()` or wrap Presentation in a using block to prevent memory leaks during repeated slide operations.
- Avoid holding multiple Presentation instances open simultaneously—close or dispose each after saving or modifying.
- Prefer `AddEmptySlide()` over cloning when creating new slides from scratch to reduce memory overhead.
- When iterating slides, use foreach with `Presentation.Slides` directly instead of caching slide collections in large loops.

## See Also

- [Create new presentations from scratch](/blog.aspose.org/slides/dotnet/introducing-slides-foss-dotnet/)
- [Explore core slide capabilities](/blog.aspose.org/slides/dotnet/slides-key-features/)
- [Build presentations step by step](/docs.aspose.org/slides/dotnet/developer-guide/presentation-creation/)
- [Convert between presentation formats](/kb.aspose.org/slides/dotnet/how-to-convert-png-to-pptx-dotnet/)
- [Resolve frequent issues and errors](/kb.aspose.org/slides/dotnet/how-to-fix-presentations-errors-dotnet/)
