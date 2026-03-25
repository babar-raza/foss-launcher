---
canonical: https://kb.aspose.org/slides/cpp/how-to-load-presentations-cpp/
canonical_import: Aspose::Slides
code_import: Aspose::Slides
date: '2026-03-24T16:29:46Z'
dateModified: '2026-03-24T16:29:46Z'
datePublished: '2026-03-24T16:29:46Z'
description: The library supports opening and parsing PowerPoint files for further
  manipulation, but note that certain advanced features remain unavailable per current...
display_name: Aspose.Slides FOSS for C++
family: slides
keywords:
- cppcon slides
- cpp slides
- cppnow slides
- cppcon slides 2025
- aspose slides cpp
- meeting cpp slides
- python slides
- python slides for beginners
lastmod: '2026-03-24T16:29:46Z'
page_role: howto_article
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: How to Load Files with Aspose.Slides FOSS for C++ | Guide
slug: how-to-load-presentations-cpp
title: How to Load Files with Aspose.Slides FOSS for C++
type: howto_article
url: /kb.aspose.org/slides/cpp/how-to-load-presentations-cpp/
weight: 10
---

## Problem

You will load a presentation file (e.g., .pptx) into Aspose.Slides FOSS for C++ using the canonical import path. The library supports opening and parsing PowerPoint files for further manipulation, but note that certain advanced features remain unavailable per current limitations.

```cpp
#include <Aspose::Slides>

int main() {
    // Load a .pptx file
    auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>(u"input.pptx");
    return 0;
}
```

## Prerequisites

- Install Aspose.Slides FOSS for C++ from the official release package or build from source.
- Include the canonical header: `#include <Aspose::Slides>` — no other import path is valid.
- Ensure your C++ compiler supports C++17 or later.

You will load presentation files (e.g., .pptx) using Aspose.Slides FOSS for C++. This step confirms your environment meets minimum requirements before proceeding with file operations.

## Loading the File

You will load a presentation file using Aspose.Slides FOSS for C++ by specifying a file path, stream, or load options. This section covers the supported input methods and known limitations.

- Aspose.Slides FOSS for C++ installed and linked in your build environment
- A valid .pptx file available at a known file path or accessible via a stream

Load a presentation from a file path using the `Presentation` class constructor. Pass the full or relative path to the .pptx file. The constructor handles format detection and initializes the in-memory representation.

```cpp
#include <Aspose::Slides>

auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>(u"example.pptx");
```

This returns a `Presentation` object ready for reading or modification. The file must exist and be a valid PowerPoint format (e.g., .pptx).

You can also load from a stream, such as `System::IO::[identifier omitted]`, when the file is not directly accessible via path. This supports in-memory or network-based sources.

Load options are not currently exposed in this version of Aspose.Slides FOSS for C++. The library uses default behavior for format detection and parsing.

Known limitations include missing support for certain advanced features such as macros, embedded OLE objects, and some animation types. These areas are not yet available in the FOSS release.

After loading, you can inspect slides, shapes, and text using the `Presentation` object’s API. See the next section for saving changes back to disk.

## Code Example

You will load a presentation file using Aspose.Slides FOSS for C++, inspect its basic structure, and print a summary of its slides and shapes. This example demonstrates opening a .pptx file, iterating through slides, and counting top-level shapes per slide.

```cpp
#include <Aspose::Slides>

int main() {
    auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>(u"example.pptx");

    for (int i = 0; i < pres->get_Slides()->get_Count(); ++i) {
        auto slide = pres->get_Slides()->idx_get(i);
        int shapeCount = 0;
        for (int j = 0; j < slide->get_Shapes()->get_Count(); ++j) {
            ++shapeCount;
        }
        System::Console::[identifier omitted](System::String(u"Slide ") + (i + 1) + u": " + shapeCount + u" shapes");
    }

    return 0;
}
```

This code opens a presentation file named `example.pptx`, iterates over each slide, and counts the number of shapes on each slide. It prints a summary line per slide to the console. Ensure `example.pptx` exists in the working directory before running.

{{< callout >}}
Note: Aspose.Slides FOSS for C++ has known limitations. The following areas are not yet available:
{{< /callout >}}

## Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| PowerPoint Open XML | `.pptx` | Full read/write support with round-trip fidelity |
| PowerPoint 97-2003 | `.ppt` | Read-only support |
| PowerPoint Template | `.potx` | Read-only support |
| PowerPoint Macro-Enabled | `.pptm` | Read-only support |
| PowerPoint Template Macro-Enabled | `.potm` | Read-only support |
| PowerPoint Binary (2007) | `.pps`, `.ppsm`, `.ppsx` | Read-only support |
| [identifier omitted] Presentation | `.odp` | Read-only support |
| SVG | `.svg` | Read-only support |
| PDF | `.pdf` | Read-only support |
| XPS | `.xps` | Read-only support |
| Image formats | `.jpg`, `.png`, `.bmp`, `.gif`, `.tiff` | Read-only support for embedded images; export to images not supported in FOSS version |
| HTML | `.html` | Read-only support |
| MHTML | `.mht`, `.mhtml` | Read-only support |

Aspose.Slides FOSS for C++ supports loading and saving `.pptx` files with full fidelity. Other formats like `.ppt`, `.odp`, `.pdf`, and image formats are supported for reading only. The FOSS version does not support export to image formats or advanced rendering features.

{{< callout >}}
Known limitation: The following areas are not yet available: advanced rendering, image export, and some legacy format features.
{{< /callout >}}

## See Also

You will review related documentation to deepen your understanding of Aspose.Slides FOSS for C++ file handling and identify current limitations. This section points to essential resources for loading, saving, and converting presentations.

- [Frequently asked questions](/kb.aspose.org/slides/cpp/faq/)
- [Visual effects capabilities](/blog.aspose.org/slides/cpp/introducing-slides-foss-cpp/)
- [Key features overview](/blog.aspose.org/slides/cpp/slides-key-features/)
- [Create presentations from scratch](/docs.aspose.org/slides/cpp/developer-guide/presentation-creation/)
- [Work with slides programmatically](/docs.aspose.org/slides/cpp/developer-guide/slide-manipulation/)
