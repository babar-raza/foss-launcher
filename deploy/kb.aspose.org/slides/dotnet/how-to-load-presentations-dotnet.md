---
canonical: https://kb.aspose.org/slides/dotnet/how-to-load-presentations-dotnet/
canonical_import: Aspose.Slides
code_import: Aspose.Slides
date: '2026-03-24T17:07:48Z'
dateModified: '2026-03-24T17:07:48Z'
datePublished: '2026-03-24T17:07:48Z'
description: This operation opens the file in memory for reading or editing without
  modifying the original.
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
seoTitle: How to Load Files with Aspose.Slides | Guide
slug: how-to-load-presentations-dotnet
title: How to Load Files with Aspose.Slides
type: howto_article
url: /kb.aspose.org/slides/dotnet/how-to-load-presentations-dotnet/
weight: 11
---

## Problem

You will load a PowerPoint (.pptx) file into Aspose.Slides using the Presentation class to access and manipulate its slides, shapes, and text. This operation opens the file in memory for reading or editing without modifying the original.

## Prerequisites

You will load a presentation file (e.g., .pptx) using Aspose.Slides and inspect its contents via the Presentation class. Ensure you have the Aspose.Slides for .NET package installed and reference the correct namespace using `using Aspose.Slides;`.

- Install the Aspose.Slides NuGet package: `dotnet add package Aspose.Slides`
- Target .NET 6.0 or later for full compatibility
- Include `using Aspose.Slides;` at the top of your C# source file

```csharp
using Aspose.Slides;

var presentation = new Presentation("input.pptx");
Console.WriteLine($"Loaded {presentation.Slides.Count} slides.");
```

## Loading the File

You will load a presentation file using Aspose.Slides by specifying a file path, stream, or load options. The Presentation class handles all loading scenarios.

- Aspose.Slides installed and referenced in your .NET project
- A valid .pptx file available at a known path or accessible via stream

### Load a presentation from a file path

Call the Presentation constructor with the file path to load a presentation directly from disk.

```csharp
using Aspose.Slides;

Presentation presentation = new Presentation("presentation.pptx");
```

This returns a Presentation object ready for manipulation. The file must exist and be a valid Office Open XML presentation (.pptx).

### Load from a stream

Use a Stream object when loading from memory, network, or non-file sources.

```csharp
using Aspose.Slides;
using System.IO;

using Stream stream = File.OpenRead("presentation.pptx");
Presentation presentation = new Presentation(stream);
```

The stream must be readable and positioned at the start of the file data. The Presentation instance reads the entire stream during construction.

### Specify load options

Pass a LoadOptions instance to control loading behavior such as password protection or format detection.

```csharp
using Aspose.Slides;

LoadOptions loadOptions = new LoadOptions();
Presentation presentation = new Presentation("presentation.pptx", loadOptions);
```

Available LoadOptions support password-protected files and format-specific hints. The constructor validates the file format and throws InvalidDataException for malformed input.

### Error handling

Handle [identifier omitted] when the path is invalid, InvalidDataException for corrupted files, and PasswordProtectedException for encrypted presentations without credentials.

Next, learn how to access slides and shapes after loading.

## Code Example

You will load a presentation file using Aspose.Slides, inspect its core metadata, and print a summary of its contents using the `DocumentProperties` and Presentation classes.

- A .NET development environment with .NET Framework 4.6.1 or later
- Aspose.Slides for .NET installed via NuGet package manager

### Load and Inspect a Presentation File

Step 1: Load the presentation file. Use the Presentation class constructor to open a `.pptx` file.

```csharp
using Aspose.Slides;

var presentation = new Presentation("sample.pptx");
```

This returns a Presentation object with all slides and metadata loaded.

Step 2: Access document properties. Use the `DocumentProperties` class to retrieve core metadata such as title and author.

```csharp
var docProps = presentation.DocumentProperties;
Console.WriteLine($"Title: {docProps.Title}");
Console.WriteLine($"Author: {docProps.Author}");
```

This prints the title and author stored in the presentation’s core properties.

Step 3: Print a slide count summary. Access the Slides collection and output its count.

```csharp
Console.WriteLine($"Total slides: {presentation.Slides.Count}");
```

This outputs the number of slides in the loaded presentation.

Step 4: Clean up resources. Call `Dispose()` on the Presentation instance to release file handles.

```csharp
presentation.Dispose();
```

This ensures the file is unlocked and memory is freed.

The complete example loads a `.pptx` file, reads its title, author, and slide count, then disposes the object safely.

## Supported Formats

You will load presentation files in various formats using Aspose.Slides. The library supports loading and saving PowerPoint files with full fidelity, and the Presentation class handles all supported input formats.

| Format | Extension | Notes |
|--------|-----------|-------|
| PowerPoint Open XML | .pptx | Standard Office Open XML presentation format |
| PowerPoint Macro-Enabled | .pptm | Presentation with macros enabled |
| PowerPoint 97-2003 | .ppt | Legacy binary format supported for reading |
| PowerPoint Template | .potx | Template file format |
| PowerPoint Template Macro-Enabled | .potm | Template with macros |
| PowerPoint Slide Show | .ppsx | Slide show format |
| PowerPoint Slide Show Macro-Enabled | .ppsm | Slide show with macros |
| PowerPoint Binary | .pps | Legacy slide show format |
| PowerPoint `Add`-In | .ppam | `Add`-in format |
| PowerPoint `Add`-In Binary | .pia | Legacy add-in format |
| PowerPoint XML | .xml | XML-based presentation format |
| PowerPoint HTML | .html | Web page format |
| PowerPoint MHTML | .mht | MHTML archive format |
| PowerPoint PDF | .pdf | PDF output (via save) |
| PowerPoint XPS | .xps | XPS document (via save) |
| PowerPoint TIFF | .tiff | TIFF image (via save) |
| PowerPoint JPEG | .jpg | JPEG image (via save) |
| PowerPoint PNG | .png | PNG image (via save) |
| PowerPoint BMP | .bmp | BMP image (via save) |
| PowerPoint GIF | .gif | GIF image (via save) |
| PowerPoint SVG | .svg | SVG image (via save) |
| PowerPoint EMF | .emf | Enhanced Metafile (via save) |
| PowerPoint WMF | .wmf | Windows Metafile (via save) |

## See Also

You will load presentation files using Aspose.Slides and prepare them for further processing such as saving, converting, or modifying slide content. The Presentation class handles file I/O operations for PPTX and legacy formats.

- [Frequently asked questions](/kb.aspose.org/slides/dotnet/faq/)
- [New presentation creation announcement](/blog.aspose.org/slides/dotnet/introducing-slides-foss-dotnet/)
- [Key features overview](/blog.aspose.org/slides/dotnet/slides-key-features/)
- [Create presentations step-by-step](/docs.aspose.org/slides/dotnet/developer-guide/presentation-creation/)
- [Work with slides effectively](/docs.aspose.org/slides/dotnet/developer-guide/slide-manipulation/)
