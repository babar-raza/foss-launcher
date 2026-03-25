---
canonical: https://kb.aspose.org/slides/dotnet/how-to-convert-png-to-pptx-dotnet/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: The library supports loading and saving presentations in formats such
  as PPTX, PPT, PDF, and image formats like PNG or JPEG.
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
page_role: howto_article
platform: dotnet
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.Slides | Guide
slug: how-to-convert-png-to-pptx-dotnet
title: How to Convert File Formats with Aspose.Slides
type: howto_article
url: /kb.aspose.org/slides/dotnet/how-to-convert-png-to-pptx-dotnet/
weight: 13
---

## Problem

You will convert a presentation file from one format to another using Aspose.Slides. The library supports loading and saving presentations in formats such as PPTX, PPT, PDF, and image formats like PNG or JPEG.

## Prerequisites

You will convert presentation files between supported formats using Aspose.Slides. Ensure you have the .NET SDK installed and reference the Aspose.Slides package.

- .NET 6.0 or later
- Aspose.Slides for .NET NuGet package installed via `dotnet add package Aspose.Slides`
- Input presentation file in `.pptx` format

## Conversion Steps

You will load a presentation file, configure export settings, and save it to another format using Aspose.Slides. This section shows how to convert between common presentation formats such as PPTX, PDF, and image formats using the core API surface.

- Aspose.Slides installed and referenced in your .NET project
- A source presentation file (e.g., .pptx) available at a known path

### Step 1: Load the Source Presentation

Initialize a Presentation object by passing the file path to its constructor. This loads the entire presentation structure into memory for manipulation or export.

```csharp
using Aspose.Slides;

Presentation presentation = new Presentation("input.pptx");
```

This returns a fully populated Presentation instance ready for format conversion.

### Step 2: Save to Target Format

Call the Save method on the Presentation object with the desired output path and format. Aspose.Slides supports saving to PDF, images (PNG, JPEG), and other presentation formats.

```csharp
presentation.Save("output.pdf", SaveFormat.Pdf);
```

The file `output.pdf` is written to disk with all slides rendered at default resolution.

### Step 3: Convert to Image Format

To export individual slides as images, iterate through the Slides collection and call Save on each slide with an image format option.

```csharp
for (int i = 0; i < presentation.Slides.Count; i++)
{
    presentation.Slides[i].Save($"slide-{i}.png", SaveFormat.Png);
}
```

Each slide is saved as a separate PNG file named `slide-0.png`, `slide-1.png`, etc.

### Code Breakdown

The Presentation class handles loading and saving of presentation files. Its Save method accepts a file path and a SaveFormat enum value to determine output type. Slide-level Save calls allow granular control over image export.

### Error Handling

Wrap conversion logic in a try block and catch IOException for file access issues or [identifier omitted] if type assumptions fail during slide iteration.

```csharp
try
{
    using var presentation = new Presentation("input.pptx");
    presentation.Save("output.pdf", SaveFormat.Pdf);
}
catch (IOException ex)
{
    // Handle file I/O errors
}
catch ([identifier omitted] ex)
{
    // Handle unexpected type during slide access
}
```

This ensures robust handling of malformed files or permission issues during conversion.

### Next Steps

Learn how to customize export settings like resolution or slide range, or explore text formatting options for generated output.

## Code Example

You will load a presentation file and convert it to another format using the Presentation class and its Save method. Aspose.Slides supports round-trip fidelity for `.pptx` files and can export to formats such as PDF, XPS, and images.

- Aspose.Slides for .NET installed and referenced in your project
- A source `.pptx` file available at a known path

```csharp
using Aspose.Slides;

var presentation = new Presentation("input.pptx");
presentation.Save("output.pdf", Aspose.Slides.Export.SaveFormat.Pdf);
```

This code loads `input.pptx`, then saves it as `output.pdf`. The Save method accepts a file path and a SaveFormat enum value specifying the target format. Supported export formats include PDF, XPS, and image formats like PNG or JPEG.

The Presentation constructor reads the `.pptx` file and builds an in-memory model of slides, shapes, and text. Calling Save with `SaveFormat.Pdf` triggers conversion using the internal rendering engine.

## Supported Formats

You will convert presentations between common file formats using Aspose.Slides. The library supports round-trip operations for PowerPoint formats and exports to PDF, images, and other formats via the Presentation class.

| Format | Extension | Notes |
|--------|-----------|-------|
| PowerPoint Open XML | .pptx | Full read/write support |
| PowerPoint Macro-Enabled | .pptm | Full read/write support |
| PowerPoint 97-2003 | .ppt | Read-only |
| PDF | .pdf | `Export` via Save() |
| JPEG | .jpg | `Export` via Save() |
| PNG | .png | `Export` via Save() |
| TIFF | .tiff | `Export` via Save() |
| SVG | .svg | `Export` via Save() |
| HTML | .html | `Export` via Save() |
| XPS | .xps | `Export` via Save() |
| ODP | .odp | Read-only |
| OTP | .otp | Read-only |

## See Also

Aspose.Slides -- Related conversion guides and format documentation.

For details on see also, see the Aspose.Slides documentation.

- [Frequently asked questions](/kb.aspose.org/slides/dotnet/faq/)
- [New presentation creation announcement](/blog.aspose.org/slides/dotnet/introducing-slides-foss-dotnet/)
- [Key features overview](/blog.aspose.org/slides/dotnet/slides-key-features/)
- [Create presentations step-by-step](/docs.aspose.org/slides/dotnet/developer-guide/presentation-creation/)
- [Work with slides effectively](/docs.aspose.org/slides/dotnet/developer-guide/slide-manipulation/)
