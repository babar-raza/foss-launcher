---
canonical: https://kb.aspose.org/slides/cpp/convert-pptx-to-fodp/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: This operation preserves `slide` content, `shapes`, `text`, and formatting
  while enabling interoperability across platforms and tools.
display_name: Aspose.Slides FOSS for C++
family: slides
keywords:
- cppcon slides
- cpp slides
- cppnow slides
- cppcon slides 2025
- aspose slides cpp
- meeting cpp slides
lastmod: '2026-04-01T14:41:49Z'
page_role: howto_article
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.Slides FOSS for C++ | Guide
slug: convert-pptx-to-fodp
title: How to Convert File Formats with Aspose.Slides FOSS for C++
type: howto_article
url: /kb.aspose.org/slides/cpp/convert-pptx-to-fodp/
weight: 13
---

## Problem

You will convert PowerPoint presentations between supported formats—specifically loading `a` `.pptx` file and saving it as another format—using the `Presentation` class from Aspose.Slides FOSS for C++. This operation preserves `slide` content, `shapes`, `text`, and formatting while enabling interoperability across platforms and tools.

## Prerequisites

You will convert PowerPoint presentations between formats such as `PPTX`, `PDF`, and `image` formats using the `Presentation` class from Aspose.Slides FOSS for C++. This requires installing the library and providing `a` valid input `presentation` file.

- C++17 or later compiler (e.g., GCC 9+, Clang 9+, MSVC 2019+)
- Aspose.Slides FOSS for C++ library installed via package manager or built from source
- A valid PowerPoint file (e.g., `input.pptx`) to convert

## Conversion Steps

You will convert PowerPoint presentations between formats such as `PPTX`, `PDF`, and `TIFF` using the `IPresentation` interface and `SaveFormat` enum in Aspose.Slides FOSS for C++. The process involves loading `a` source file, specifying the target format, and saving the result.

- Aspose.Slides FOSS for C++ installed and accessible via CMake or direct linking
- A source presentation file in a supported format (e.g., PPTX, PPT, ODP)

### Step 1: Load Source `Presentation`

Construct an `IPresentation` object by passing the path to your source file. This loads the entire `presentation` into memory for manipulation.

```cpp
using namespace Aspose::Slides::Foss;

auto pres = System::MakeObject<IPresentation>(u"input.pptx");
```

This returns `a` fully initialized `IPresentation` instance ready for conversion.

### Step 2: Specify Target Format

Choose the output format using the `SaveFormat` enum. Supported targets include `PDF`, `XPS`, `TIFF`, and other PowerPoint variants like `PPTX` or `PPSX`.

```cpp
SaveFormat format = SaveFormat::PDF;
```

The `SaveFormat` enum ensures `type`-safe format selection without runtime errors.

### Step 3: Save Converted File

Call the Save() method on the `IPresentation` object, passing the output path and the chosen `SaveFormat` value.

```cpp
pres->Save(u"output.pdf", SaveFormat::PDF);
```

This writes the converted file to disk in the specified format with full fidelity.

### Code Breakdown

The `IPresentation` constructor handles format detection automatically based on file extension. The Save() method performs format conversion internally using the `SaveFormat` parameter. No explicit option objects are required—conversion behavior is determined by the target format.

### Error Handling

Wrap conversion logic in `a` `System::Exception` handler to catch file I/O errors or unsupported format cases. The library throws `System::Exception` for invalid paths or malformed input files.

```cpp
try {
 auto pres = System::MakeObject<IPresentation>(u"input.pptx");
 pres->Save(u"output.pdf", SaveFormat::PDF);
} catch (System::Exception& ex) {
 // Handle error
}
```

### Next Steps

After conversion, explore `slide` manipulation, shape editing, or `text` formatting using the `IPresentation` interface. See the full API `reference` for advanced operations.

## Code Example

You will load `a` PowerPoint `presentation` and convert it to `PDF` using the `IPresentation` interface and Save method. This demonstrates the core conversion workflow supported by Aspose.Slides FOSS for C++.

- Aspose.Slides FOSS for C++ installed and accessible in your build environment
- A source `.pptx` file available at a known path

```cpp
using namespace Aspose::Slides::Foss;

auto pres = MakeObject<Aspose::Slides::Foss::Presentation>(u"input.pptx");
pres->Save(u"output.pdf", Aspose::Slides::Foss::SaveFormat::Pdf);
```

This code loads `input.pptx` into an `IPresentation` object and writes the result as `output.pdf`. The `SaveFormat::Pdf` enum value specifies the target format. All supported output formats—including Pptx, Pdf, Tiff, and `image` formats like Png and Jpeg—are accessible via the `SaveFormat` enum.

Ensure your build links against the Aspose.Slides FOSS for C++ library and includes its headers. The u prefix on string literals ensures UTF-16 compatibility on Windows, while standard `std::u16string` handling applies on other platforms.

## Supported Formats

Aspose.Slides FOSS for C++ supports conversion between common `presentation` formats using the `IPresentation` interface. You can load `a` source `presentation` and `save` it in multiple output formats including `PPTX`, `PDF`, and `image` formats such as `TIFF`.

| Format | Extension | Notes |
|--------|-----------|-------|
| PowerPoint Open `XML` | `.pptx` | Full round-trip fidelity |
| `PDF` | `.pdf` | High-fidelity document export |
| `TIFF` | `.tiff` | Multi-page `image` format |

## See Also

- [Frequently asked questions](/slides/cpp/frequently-asked-questions/)
- [Get up and running quickly](/slides/cpp/getting-started/)
- [What's new in this release](/slides/cpp/slides-introduction/)
- [Core capabilities overview](/slides/cpp/slides-key-features/)
- [Step-by-step presentation creation](/slides/cpp/developer-guide/presentation-creation/)
