---
canonical: https://kb.aspose.org/slides/cpp/save-presentations/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: The `IPresentation` interface provides methods to open `.pptx` files
  and persist them as other formats such as `PDF`, `XPS`, or `images`.
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
seoTitle: How to Save Files with Aspose.Slides FOSS for C++ | Guide
slug: save-presentations
title: How to Save Files with Aspose.Slides FOSS for C++
type: howto_article
url: /kb.aspose.org/slides/cpp/save-presentations/
weight: 12
---

## Problem

You will load `a` `presentation` file and `save` it in `a` different format using Aspose.Slides FOSS for C++. The `IPresentation` interface provides methods to open `.pptx` files and persist them as other formats such as `PDF`, `XPS`, or `images`.

## Prerequisites

- Install a C++17-compatible compiler (e.g., GCC 9+, Clang 9+, or MSVC 2019+).
- Download and extract the Aspose.Slides FOSS for C++ library archive from the official release page.
- Include the `include/` directory in your compiler’s header search path and link against the compiled library binary.

## Saving the File

You will load `a` `presentation` file and `save` it in `a` different format using the `IPresentation` interface and the `SaveFormat` enum.

- A valid presentation file (e.g., `.pptx`) exists on disk
- Aspose.Slides FOSS for C++ is installed and the canonical import `using namespace Aspose::Slides::Foss;` is used

### Step 1: Load the `presentation`

Use the `IPresentation` class to open the source file. This loads the entire `presentation` into memory for modification or export.

```cpp
using namespace Aspose::Slides::Foss;

auto pres = System::MakeObject<IPresentation>(u"input.pptx");
```

This returns an `IPresentation` object representing the loaded file.

### Step 2: Save in `a` different format

Call Save() on the `IPresentation` object with `a` file path and `a` `SaveFormat` enum value to export the `presentation`.

```cpp
pres->Save(u"output.pdf", SaveFormat::PDF);
```

This writes the `presentation` to disk as `a` `PDF` file. Supported output formats include `PPT`, `PDF`, `XPS`, `PPTX`, `PPSX`, `TIFF`, `ODP`, `PPTM`, `PPSM`, and `POTX`.

### Error Handling

Wrap file operations in `a` try block and catch `System::Exception^` to handle invalid paths, unsupported formats, or I/O failures.

```cpp
try {
 auto pres = System::MakeObject<IPresentation>(u"input.pptx");
 pres->Save(u"output.pdf", SaveFormat::PDF);
} catch (System::Exception^ ex) {
 // Handle error: log or display ex->get_Message()
}
```

This ensures robust handling of runtime issues during `save` operations.

### Next Steps

Learn how to [convert slides to images](/slides/cpp/developer-guide/converting-to-images/) or [work with slide layouts](/slides/cpp/developer-guide/working-with-slides/).

## Code Example

You will load an existing `presentation` file, modify its document properties, and `save` it in `a` different format using the `IPresentation` interface and `DocumentProperties` class from Aspose.Slides FOSS for C++.

Start by including the canonical import and constructing an `IPresentation` object from an existing `.pptx` file. Then access the document properties via the get_DocumentProperties() method and update fields such as `title()` and `subject()`.

```cpp
using namespace Aspose::Slides::Foss;

auto pres = System::MakeObject<Presentation>(u"input.pptx");
pres->get_DocumentProperties()->set_title(u"Updated Presentation Title");
pres->get_DocumentProperties()->set_subject(u"FOSS Demo");
pres->Save(u"output.pptx", SaveFormat::Pptx);
```

This code loads `input.pptx`, updates the `presentation` `title` and `subject`, and saves the modified file as `output.pptx`. The Save() method preserves all content and formatting while applying the updated metadata.

{{< callout >}}
Ensure the input file `input.pptx` exists in the working directory before running this example. The output file `output.pptx` will be created in the same directory.
{{< /callout >}}

## Output Options

Aspose.Slides FOSS for C++ supports saving presentations in multiple output formats. You specify the target format using the `SaveFormat` enumeration when calling the Save method on an `IPresentation` object. Available formats include `PPTX`, `PPT`, `PDF`, `XPS`, and `image` formats such as PNG, JPEG, and `TIFF`.

- PPTX and PPT for PowerPoint-compatible presentations
- PDF for portable document output
- XPS for fixed-page documents
- PNG, JPEG, TIFF for slide-level image export

Format-specific options are limited in this FOSS version. For `image` exports, resolution and `size` are determined by the `slide` dimensions and the target `image` format’s inherent properties. Use the Save method overload that accepts `a` `SaveFormat` enum value to control output `type`.

## See Also

- [Frequently asked questions](/slides/cpp/frequently-asked-questions/)
- [Get up and running quickly](/slides/cpp/getting-started/)
- [Overview of the open-source library](/slides/cpp/slides-introduction/)
- [Key capabilities and features](/slides/cpp/slides-key-features/)
- [Step-by-step presentation creation](/slides/cpp/developer-guide/presentation-creation/)
