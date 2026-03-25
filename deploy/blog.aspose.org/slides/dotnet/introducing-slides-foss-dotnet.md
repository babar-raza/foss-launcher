---
canonical: https://blog.aspose.org/slides/dotnet/introducing-slides-foss-dotnet/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: Aspose.Slides lets you create and manipulate presentations directly in
  .NET code—no GUI, no dependencies, just reliable file I/O.
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
page_role: blog_announcement
platform: dotnet
reading_time: 1
robots: index, follow
seoTitle: The library allows creating new presentations using the
slug: introducing-slides-foss-dotnet
title: The library allows creating new presentations using the Presentation class
type: blog_announcement
url: /blog.aspose.org/slides/dotnet/introducing-slides-foss-dotnet/
weight: 16
---

## Introduction

Generating a PowerPoint presentation programmatically shouldn’t require launching Microsoft Office or wrestling with COM interop. Aspose.Slides lets you create and manipulate presentations directly in .NET code—no GUI, no dependencies, just reliable file I/O.

```csharp
using Aspose.Slides;

using var newPrs = new Presentation();
var slide = newPrs.Slides[0];
newPrs.Save("new.pptx", SaveFormat.Pptx);
```

You can also open existing `.pptx` files, inspect their contents, and save changes—preserving all formatting, comments, and document properties. This round-trip capability makes Aspose.Slides ideal for templating, batch report generation, or updating slide decks without manual intervention.

```csharp
using Aspose.Slides;

using var prs = new Presentation("input.pptx");
Console.WriteLine($"Slides: {prs.Slides.Count}");
prs.Save("output.pptx", SaveFormat.Pptx);
```

Custom document properties persist across saves and reloads—store version numbers, project IDs, or metadata as strings or integers. `Comments` attach to specific slides and authors, enabling collaborative review workflows directly in code.

## Key Highlights

You don’t need a full office suite to generate or modify PowerPoint files — Aspose.Slides lets you build presentations programmatically in just a few lines of C#. Whether you’re generating reports, automating slide decks, or enriching existing presentations with comments and metadata, the Presentation class handles both new and existing files with consistent, predictable behavior.

```csharp
using Aspose.Slides;

// Create a new presentation from scratch
using var newPrs = new Presentation();
var slide = newPrs.Slides[0];
newPrs.Save("new.pptx", SaveFormat.Pptx);

// Open and modify an existing presentation
using var prs = new Presentation("input.pptx");
Console.WriteLine($"Slides: {prs.Slides.Count}");
prs.Save("output.pptx", SaveFormat.Pptx);
```

- Create new presentations using the Presentation class and immediately access the first slide via `Slides[0]`.
- Open existing `.pptx` files for reading or modification — changes persist correctly on save, including slide count and content.
- Set document properties like Title, `Author`, and custom string or integer properties that survive round-trips.
- Add comments with author metadata, including position, text, and timestamp, directly to slides.
- Iterate and manipulate slides, shapes, and text using a fluent, object-oriented API designed for automation.

```csharp
using Aspose.Slides;

using var prs = new Presentation();
prs.DocumentProperties.Title = "Q1 Results";
prs.DocumentProperties.Author = "Finance Team";
prs.DocumentProperties.SetCustomPropertyValue("Version", 3);
prs.Save("deck.pptx", SaveFormat.Pptx);
```

## Getting Started

You need to generate a new PowerPoint presentation from scratch — maybe for automated reporting, slide generation, or template-based decks. Aspose.Slides makes this possible without requiring Microsoft PowerPoint or any external dependencies.

The Presentation class handles both creating new decks and opening existing ones. When you instantiate it with a file path, it loads the `.pptx` file into memory, preserving all slides, shapes, and metadata. You can then inspect or modify it before saving.

## See Also

To get started with Aspose.Slides, explore the official documentation for hands-on guidance on building and modifying presentations programmatically. The changelog provides a clear record of new features, bug fixes, and breaking changes across releases.

- [Create new presentations](/products.aspose.org/slides/_index/)
- [Explore key features](/blog.aspose.org/slides/dotnet/slides-key-features/)
- [Create Presentations with Aspose.Slides](/docs.aspose.org/slides/dotnet/developer-guide/presentation-creation/)
- [Work with slides programmatically](/docs.aspose.org/slides/dotnet/developer-guide/slide-manipulation/)
- [Convert file formats easily](/kb.aspose.org/slides/dotnet/how-to-convert-png-to-pptx-dotnet/)
