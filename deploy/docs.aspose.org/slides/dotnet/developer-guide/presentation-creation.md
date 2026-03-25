---
canonical: https://docs.aspose.org/slides/dotnet/developer-guide/presentation-creation/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: You start with an empty presentation, add a slide, insert a shape with
  formatted text, and save the result as a .pptx file.
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
seoTitle: Create Presentations with Aspose.Slides | Guide
slug: presentation-creation
title: Create Presentations with Aspose.Slides
type: workflow_page
url: /docs.aspose.org/slides/dotnet/developer-guide/presentation-creation/
weight: 18
---

## Overview

This guide walks you through creating and saving a new presentation using Aspose.Slides. You start with an empty presentation, add a slide, insert a shape with formatted text, and save the result as a .pptx file.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
var slide = presentation.Slides[0];
var autoShape = slide.Shapes.AddAutoShape(ShapeType.Rectangle, 100, 100, 300, 100);
autoShape.TextFrame.Text = "Hello, Aspose.Slides!";
presentation.Save("output.pptx", SaveFormat.Pptx);
```

- Use this approach when generating dynamic reports as slide decks.
- Use this approach when building presentation templates from data.
- Use this approach when automating slide creation for training materials.

## Working with Data

This section shows how to read, write, and modify data elements in Aspose.Slides presentations. You work directly with slide content such as text portions, bullet formatting, and image properties using core API classes like `BasePortionFormat`, `BulletFormat`, and Image.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
var slide = presentation.Slides[0];
var shape = slide.Shapes.AddAutoShape(AutoShapeType.Rectangle, 50, 50, 300, 100);
var textFrame = shape.AddTextFrame("Sample Text");
var portion = textFrame.Paragraphs[0].Portions[0];
var format = portion.PortionFormat;
format.FontHeight = 18;
presentation.Save("output.pptx", SaveFormat.Pptx);
```

- Use `Portion.PortionFormat` to set font size, color, and other character-level properties.
- Access `TextFrame.Paragraphs` to modify paragraph-level formatting like indentation or alignment.
- Apply `BulletFormat` to enable and configure bullet types (e.g., `BulletType.Symbol`, `BulletType.Numbered`).

To read existing data, load a presentation and inspect its slide content. The Image class exposes dimensions and raw data for embedded picture frames, while `BasePortionFormat` provides access to formatting attributes via RprElement() and `GetNullableBoolAttr()`.

```csharp
using Aspose.Slides;

var presentation = new Presentation("input.pptx");
var slide = presentation.Slides[0];
foreach (var shape in slide.Shapes)
{
    if (shape is PictureFrame picFrame)
    {
        var image = picFrame.PictureFormat.Picture.Image;
        var width = image.Width;
        var height = image.Height;
    }
}
presentation.Dispose();
```

- Use `PictureFrame.PictureFormat.Picture.Image` to retrieve the IImage instance for dimension checks.
- Call `Image.Save(filename)` to export the image to disk using its original format.
- Check `Image.Width` and `Image.Height` to validate sizing before resizing or embedding.

Modify bullet formatting by accessing `Paragraph.ParagraphFormat.BulletFormat`. Use `BulletFormat.Type()` to determine the current bullet type and `BulletFormat.InsertPprChild()` to adjust XML structure when needed.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
var slide = presentation.Slides[0];
var shape = slide.Shapes.AddAutoShape(AutoShapeType.Rectangle, 50, 50, 300, 150);
var textFrame = shape.AddTextFrame("First item\nSecond item");
var para = textFrame.Paragraphs[0];
para.ParagraphFormat.BulletFormat.Type = BulletType.Symbol;
para.ParagraphFormat.BulletFormat.Char = '•';
presentation.Save("bulleted.pptx", SaveFormat.Pptx);
```

- Set `BulletFormat.Type` to `BulletType.Symbol` or `BulletType.Numbered` to change bullet style.
- Assign a character to `BulletFormat.Char` for custom symbol bullets.
- Use `BulletFormat.BuildTagIndex()` to rebuild internal tag indices after bulk formatting changes.

## Code Examples

This guide walks you through creating a new presentation, adding a slide with a title, and saving it as a .pptx file using Aspose.Slides. You start by instantiating the Presentation class, then add a slide using AddEmptySlide(), and finally write the result to disk using Save().

```csharp
using Aspose.Slides;

var presentation = new Presentation();
presentation.Slides.AddEmptySlide(presentation.Slides[0]);
presentation.Save("output.pptx", Aspose.Slides.Export.SaveFormat.Pptx);
```

- Use this approach when generating on-demand slide decks from templates.
- Use this approach when building presentation reports from programmatic data.
- Use this approach when initializing a new presentation before adding content.

Next, add a title placeholder to the first slide and populate it with text. Access the slide's PlaceholderCollection, locate the title placeholder by type, and set its text using the TextFrame property. This ensures the slide follows standard PowerPoint layout conventions.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
var slide = presentation.Slides.AddEmptySlide(presentation.Slides[0]);
var titlePlaceholder = slide.Placeholders.FirstOrDefault(p => p.Type == Aspose.Slides.PlaceholderType.Title);
if (titlePlaceholder != null)
{
    titlePlaceholder.TextFrame.Text = "Annual Sales Report";
}
presentation.Save("title-presentation.pptx", Aspose.Slides.Export.SaveFormat.Pptx);
```

- Use this approach when generating branded presentations with consistent title formatting.
- Use this approach when populating slide titles from external data sources.
- Use this approach when validating placeholder presence before content injection.

Finally, add a picture frame to the slide and embed an image. Load the image using the Image class, then insert it into the slide via AddPictureFrame(). This demonstrates how to include visual assets in a presentation programmatically.

```csharp
using Aspose.Slides;

var presentation = new Presentation();
var slide = presentation.Slides.AddEmptySlide(presentation.Slides[0]);
var imageData = System.IO.File.ReadAllBytes("chart.png");
var image = new Image(imageData, "image/png");
var pictureFrame = slide.Shapes.AddPictureFrame(Aspose.Slides.ShapeType.Rectangle, 50, 150, 300, 200, image);
presentation.Save("with-image.pptx", Aspose.Slides.Export.SaveFormat.Pptx);
```

- Use this approach when embedding charts or diagrams generated outside PowerPoint.
- Use this approach when building dynamic slide decks with variable imagery.
- Use this approach when preparing presentations for export to PDF or video.

## Notes and Best Practices

When working with Aspose.Slides in .NET, always use the canonical import `using Aspose.Slides;` and avoid Python-style imports. Performance and memory stability depend on proper resource handling and avoiding unnecessary object duplication.

- Use using blocks or explicitly call `Dispose()` on Presentation instances to release unmanaged resources and prevent memory leaks.
- Avoid cloning slides or shapes unless necessary—`AddClone()` and `AddClone()` operations increase memory pressure and processing time.
- Minimize repeated access to slide collections; cache slide references in local variables to reduce internal lookups.
- For batch operations, process presentations in smaller batches rather than loading large files entirely into memory.

## See Also

- [Create new presentations from scratch](/blog.aspose.org/slides/dotnet/introducing-slides-foss-dotnet/)
- [Explore core slide capabilities](/blog.aspose.org/slides/dotnet/slides-key-features/)
- [Master slide manipulation techniques](/docs.aspose.org/slides/dotnet/developer-guide/slide-manipulation/)
- [Convert presentations between formats](/kb.aspose.org/slides/dotnet/how-to-convert-png-to-pptx-dotnet/)
- [Resolve frequent Aspose.Slides issues](/kb.aspose.org/slides/dotnet/how-to-fix-presentations-errors-dotnet/)
