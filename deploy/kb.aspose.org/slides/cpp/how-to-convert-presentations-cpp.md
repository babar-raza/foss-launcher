---
canonical: https://kb.aspose.org/slides/cpp/convert-presentations/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-03-29T16:35:25Z'
dateModified: '2026-03-29T16:55:07Z'
datePublished: '2026-03-29T16:35:25Z'
description: The library enables loading `a` source `presentation` and saving it in
  another format such as PPTX, with full fidelity for `slides`, `shapes`, and `text`...
display_name: Aspose.Slides FOSS for C++
family: slides
keywords:
- cppcon slides
- cpp slides
- cppnow slides
- cppcon slides 2025
- aspose slides cpp
- meeting cpp slides
lastmod: '2026-03-29T16:55:07Z'
page_role: howto_article
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.Slides FOSS for C++ | Guide
slug: convert-presentations
title: How to Convert File Formats with Aspose.Slides FOSS for C++
type: howto_article
url: /kb.aspose.org/slides/cpp/convert-presentations/
weight: 13
---

## Problem

You will convert `presentation` files between supported formats using Aspose.Slides FOSS for C++. The library enables loading `a` source `presentation` and saving it in another format such as PPTX, with full fidelity for `slides`, `shapes`, and `text` content.

## Prerequisites

You will convert `presentation` files between supported formats using Aspose.Slides FOSS for C++. Ensure you have the required C++ environment and input file ready before proceeding.

- C++17 or later compiler (e.g., GCC 9+, Clang 9+, MSVC 2019+)
- Aspose.Slides FOSS for C++ library installed and linked in your build system
- A source presentation file in a supported format (e.g., .pptx)

## Conversion Steps

You will convert `presentation` files between supported formats using Aspose.Slides FOSS for C++ by loading the source file, applying conversion settings, and saving to the target format using the `IPresentation` interface.

- Aspose.Slides FOSS for C++ installed and linked in your build environment
- A source presentation file in a supported format (e.g., .pptx)

### Step 1: Load Source `Presentation`

Initialize the `IPresentation` interface by constructing it with the path to your source file. This loads the entire `presentation` structure into memory for further processing.

```cpp
using namespace Aspose::Slides::Foss;

IPresentation presentation(u"input.pptx");
```

This creates `a` fully populated `IPresentation` object ready for format conversion.

### Step 2: Save to Target Format

Call the appropriate `save` method on the `IPresentation` object, specifying the output path and desired format. The library automatically handles internal serialization based on the target extension.

```cpp
presentation.Save(u"output.pptx", SaveFormat::Pptx);
```

This writes the converted `presentation` to disk in the specified format with full fidelity.

### Code Breakdown

The `IPresentation` constructor parses the source file and populates `slide`, shape, and `text` structures. The Save() method serializes the in-memory representation to the target format using internal format-specific writers. All operations occur within the `Aspose::Slides::Foss` namespace.

### Error Handling

Wrap conversion logic in `a` try-catch block to handle `System::Exception` and `std::runtime_error`. These exceptions may be thrown for invalid file paths, unsupported formats, or I/O failures during `save`.

## Code Example

You will convert `a` `presentation` file from one format to another using the `IPresentation` interface and the Save method. Aspose.Slides FOSS for C++ supports round-trip conversion of `.pptx` files to other formats such as `.pdf`, `.jpg`, `.png`, and `.svg`.

```cpp
using namespace Aspose::Slides::Foss;

// Load the source presentation
auto pres = System::MakeObject<Presentation>(u"input.pptx");

// Save as PDF
pres->Save(u"output.pdf", SaveFormat::Pdf);
```

The `Presentation` constructor loads the `.pptx` file into memory. The Save method writes the output in the specified format. Supported output formats include PDF, `image` formats (JPEG, PNG, SVG), and other `presentation` formats. Ensure the output path includes the correct file extension matching the target format.

{{< callout >}}
Note: The `SaveFormat` enum values such as `Pdf`, `Jpeg`, `Png`, and `Svg` are used to specify the target format. Only formats explicitly listed in the product documentation are supported.
{{< /callout >}}

## Supported Formats

Aspose.Slides FOSS for C++ supports conversion between common `presentation` file formats using the `IPresentation` interface. You can load `a` source `presentation` and `save` it in another format by specifying the target file extension.

| Format | Extension | Notes |
|--------|-----------|-------|
| PowerPoint Open XML | `.pptx` | Default input and output format |
| PowerPoint 97-2003 | `.ppt` | Legacy binary format |
| PDF | `.pdf` | High-fidelity document export |
| XPS | `.xps` | Fixed-page document format |
| SVG | `.svg` | Vector graphics export |
| TIFF | `.tiff` | Multi-page `image` export |
| HTML | `.html` | Web-compatible `slide` export |
| MHTML | `.mht` | Single-file web archive |
| ODP | `.odp` | `Presentation` |
| POTX | `.potx` | PowerPoint template |
| POT | `.pot` | PowerPoint 97-2003 template |
| PPSX | `.ppsx` | PowerPoint `slide` show |
| PPS | `.pps` | PowerPoint 97-2003 `slide` show |
| PPTM | `.pptm` | Macro-enabled `presentation` |
| POTM | `.potm` | Macro-enabled template |
| PPSM | `.ppsm` | Macro-enabled `slide` show |
| PPT | `.ppt` | Alias for legacy PowerPoint |
| ODP | `.odp` | format |
| SVG | `.svg` | Scalable Vector Graphics |
| XPS | `.xps` | XML Paper Specification

## See Also

- [Frequently asked questions](/slides/cpp/frequently-asked-questions/)
- [Get up and running quickly](/slides/cpp/getting-started/)
- [What's new in this release](/slides/cpp/slides-foss/)
- [Core capabilities overview](/slides/cpp/slides-features/)
- [Step-by-step presentation creation](/slides/cpp/developer-guide/presentation-creation/)
