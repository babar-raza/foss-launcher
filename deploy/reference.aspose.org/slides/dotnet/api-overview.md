---
canonical: https://reference.aspose.org/slides/dotnet/api-overview/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: It supports core presentation elements including slides, shapes, text,
  and formatting.
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
page_role: api_reference
platform: dotnet
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides API Reference | Guide
slug: api-overview
title: Aspose.Slides API Reference
type: api_reference
url: /reference.aspose.org/slides/dotnet/api-overview/
weight: 6
---

## Overview

The Aspose.Slides library provides classes for loading, creating, modifying, and saving PowerPoint presentations in .NET. It supports core presentation elements including slides, shapes, text, and formatting.

```csharp
using Aspose.Slides;

using var prs = new Presentation();
var slide = prs.Slides[0];
var shape = slide.Shapes.AddAutoShape(ShapeType.Rectangle, 50, 50, 300, 150);
shape.AddTextFrame("Hello, world!");
prs.Save("output.pptx", SaveFormat.Pptx);
```

| Class | `Description` | Claim IDs |
|-------|-------------|-----------|
| `EffectFormat` | Manages visual effects on shapes; InitInternal() receives the slide part for saving changes. | CLM-slides-349ffa |
| IImage | Represents an image; `Save(filename)` writes to the destination file path. | CLM-slides-b35f02 |
| IDocumentProperties | Provides access to presentation metadata; `Author()` gets or sets the dc:creator. | CLM-slides-7f3314 |
| `AuthorData` | Represents author metadata in the API. | CLM-slides-7f7351 |

## Public API

The Aspose.Slides API provides core classes for working with presentation documents in .NET. Key namespaces include Aspose.Slides.Foss for high-level operations and Aspose.Slides.Foss.Drawing for drawing primitives. The API supports loading, creating, modifying, and saving PowerPoint-compatible presentations (.pptx).

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var slide = prs.Slides[0];
var shape = slide.Shapes.AddAutoShape(ShapeType.Rectangle, 50, 50, 300, 100);
shape.AddTextFrame("Hello, world!");
prs.Save("shapes.pptx", SaveFormat.Pptx);
```

| Class | `Description` |
|-------|-------------|
| Presentation | Represents a PowerPoint presentation and provides access to slides, document properties, and comment authors. |
| `BaseSlide` | Represents a slide in a presentation, including master, layout, and regular slides. |
| `AutoShape` | Represents an auto shape such as rectangle, circle, or arrow. |
| ShapeCollection | `Contains` all shapes on a slide; initialized with the owning slide object. |
| IDocumentProperties | Provides access to document metadata including author, title, and comments. |
| `Comment` | Represents a comment attached to a slide with author, text, and timestamp. |
| `CommentAuthors` | Manages the collection of comment authors in a presentation. |
| IImage | Represents an image object with width, height, and save methods. |
| `FillFormat` | Defines fill properties for shapes, including solid, gradient, and picture fills. |
| `EffectFormat` | `Contains` effect settings such as shadow, glow, and reflection. |
| `BulletFormat` | Controls bullet type and formatting for paragraphs. |
| `BasePortionFormat` | Holds character-level formatting for text portions. |

| Method | Return Type | `Description` |
|--------|-------------|-------------|
| `IDocumentProperties.Author()` | string | Gets or sets the author (dc:creator) of the presentation. |
| `IDocumentProperties.Title()` | string | Gets or sets the title of the presentation. |
| `IDocumentProperties.Subject()` | string | Gets or sets the subject of the presentation. |
| `IDocumentProperties.Keywords()` | string | Gets or sets the keywords associated with the presentation. |
| `IDocumentProperties.Comments()` | string | Gets or sets the comments (dc:description) for the presentation. |
| `ShapeCollection.InitInternal()` | void | Initializes the collection with the owning slide object. |
| `EffectFormat.InitInternal()` | void | Initializes the format with the slide part for saving changes. |
| `IImage.Save(string)` | void | Saves the image to the specified file path. |
| `Comment.Text()` | string | Gets or sets the comment text. |
| `Comment.CreatedTime()` | DateTime | Gets the creation timestamp of the comment. |

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var author = prs.CommentAuthors.AddAuthor("Jane Smith", "JS");
var slide = prs.Slides[0];
author.Comments.AddComment("Review this slide", slide, new PointF(2.0f, 2.0f), DateTime.Now);
prs.Save("comments.pptx", SaveFormat.Pptx);
```

## Common Patterns

The IDocumentProperties interface provides access to core metadata of a presentation, including title, author, subject, keywords, and comments. These properties map to Dublin Core elements in the underlying XML structure.

| Method | Return Type | `Description` |
|--------|-------------|-------------|
| Title() | string | Gets or sets the title (dc:title) of the presentation. |
| Subject() | string | Gets or sets the subject of the presentation. |
| `Author()` | string | Gets or sets the author (dc:creator) of the presentation. |
| Keywords() | string | Gets or sets the keywords associated with the presentation. |
| `Comments()` | string | Gets or sets the comments (dc:description) for the presentation. |

```csharp
using Aspose.Slides;

using var prs = new Presentation();
var docProps = prs.DocumentProperties;
docProps.Author = "John Doe";
docProps.Comments = "Internal review version";
prs.Save("metadata.pptx", SaveFormat.Pptx);
```

The `BaseCollection` class serves as the base for strongly-typed collections in Aspose.Slides, where the element type is defined by the generic parameter or concrete subclass.

The `AdjustValue` class represents a single adjustment value used in auto shape geometry definitions.

## See Also

The `IDocumentProperties.Keywords()` method gets or sets the keywords associated with the presentation. This property is part of the IDocumentProperties interface, which provides access to core document metadata.

```csharp
using Aspose.Slides;

var pres = new Presentation();
pres.DocumentProperties.Keywords = "presentation, slides, dotnet";
Console.WriteLine(pres.DocumentProperties.Keywords);
pres.Save("metadata.pptx", SaveFormat.Pptx);
```

- [Presentation object reference](/reference.aspose.org/slides/dotnet/presentation/)
- [Frequently asked questions](/kb.aspose.org/slides/dotnet/faq/)
- [Troubleshooting common issues](/kb.aspose.org/slides/dotnet/troubleshooting/)
- [Getting started guide](/docs.aspose.org/slides/dotnet/developer-guide/getting-started/)
- [Installation instructions](/docs.aspose.org/slides/dotnet/developer-guide/installation/)
