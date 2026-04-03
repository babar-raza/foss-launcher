---
canonical: https://docs.aspose.org/slides/cpp/developer-guide/product-installation/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: This library supports core `presentation` operations including `slide`
  management, shape rendering, and `text` formatting — all without requiring Microsoft...
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
page_role: workflow_page
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FOSS Installation
slug: product-installation
summary: ''
title: Installation
type: workflow_page
url: /docs.aspose.org/slides/cpp/developer-guide/product-installation/
weight: 3
---

## Overview

Aspose.Slides FOSS for C++ enables developers to create, modify, and convert PowerPoint presentations directly in C++ applications. This library supports core `presentation` operations including `slide` management, shape rendering, and `text` formatting — all without requiring Microsoft PowerPoint.

The API surface provides low-level access to `presentation` components such as `BulletFormat`, `Comment`, `DocumentProperties`, `EffectFormat`, `FillFormat`, `GradientFormat`, `GradientStop`, `GradientStopCollection`, and `IImage`. Developers use these classes to programmatically control formatting, metadata, and visual effects in `.pptx` files.

```cpp
using namespace Aspose::Slides::Foss;

// Example: Create a new presentation and set document properties
auto pres = System::MakeObject<Presentation>();
pres->get_DocumentProperties()->set_Title(u"Quarterly Report");
pres->get_DocumentProperties()->set_Subject(u"Q3 Financial Summary");
pres->Save(u"report.pptx", SaveFormat::Pptx);
```

- Use `DocumentProperties` to embed metadata like title and subject for document management.
- Set `BulletFormat` properties to standardize list formatting across slides.
- Apply `FillFormat` and `GradientFormat` to customize shape backgrounds and effects.

## Key Features

Aspose.Slides FOSS for C++ enables developers to build high-fidelity `presentation` workflows directly in C++. Using the `Aspose::Slides::Foss` namespace, you can manipulate core `presentation` components such as `slides`, `shapes`, `text` formatting, and document properties without external dependencies.

- Full round-trip support for `.pptx` files ensures your presentations retain layout and formatting across save cycles.
- Direct access to `BulletFormat` lets you programmatically configure paragraph bullet types, characters, and styles for consistent list formatting.
- The `Comment` class and `IComment` interface support adding, reading, and managing slide comments with timestamps and author context.
- Document metadata is editable via `DocumentProperties` and `IDocumentProperties`, including title, subject, company, and application version.
- Shape formatting is controlled through `FillFormat`, `EffectFormat`, and `GradientFormat`, enabling solid, gradient, and effect-based visual styling.
- Camera and 3D rendering support via the `Camera` class allows configuration of perspective and projection settings for 3D shapes.

## Prerequisites

This guide walks you through setting up Aspose.Slides FOSS for C++ to process PowerPoint presentations programmatically. You will install the library, configure your C++ environment, and prepare to use core classes like `BulletFormat`, `Comment`, and `DocumentProperties`.

- C++17 or later compiler (e.g., GCC 9+, Clang 9+, MSVC 2019+)
- CMake 3.16+ for build orchestration (optional but recommended)
- Aspose.Slides FOSS for C++ library installed via package manager or from source
- Standard C++ runtime libraries (libstdc++ or libc++)

## Code Examples

This guide walks you through installing and verifying Aspose.Slides FOSS for C++ with `a` minimal runnable example. After installing the library, you create `a` new `presentation`, set document properties, and `save` it as `a`.pptx file.

```cpp
using namespace Aspose::Slides::Foss;

int main() {
 auto presentation = System::MakeObject<Presentation>();
 auto docProps = presentation->get_DocumentProperties();
 docProps->set_Title(u"Sample Presentation");
 docProps->set_Subject(u"FOSS C++ Usage");
 presentation->Save(u"output.pptx", Aspose::Slides::Export::SaveFormat::Pptx);
 return 0;
}
```

- Use this pattern when generating templated presentations for archival or reporting.
- Set `DocumentProperties` before saving to embed metadata that persists across sessions.
- The Save() method writes the file with full round-trip fidelity to .pptx format.

## Best Practices

This section outlines essential best practices for using Aspose.Slides FOSS for C++ in production workflows. Follow these guidelines to ensure correct namespace usage, maintainable code structure, and compatibility with the FOSS distribution.

- Always use `using namespace Aspose::Slides::Foss;` — never the commercial `Aspose::Slides` namespace.
- Avoid internal sub-namespaces (e.g., `Aspose::Slides::Foss::Internal`) — they are not part of the public API.
- Use only the documented classes from the API surface: `AutoShape`, `TextFrame`, `Paragraph`, `Portion`, `FillFormat`, and others listed in the product capabilities.
- Validate file I/O operations by checking return status or catching exceptions — do not assume success after `save()` or load() calls.

When working with `slides`, prefer explicit `slide` indexing over iteration where possible to avoid off-by-one errors. Use `Presentation->get_Slides()->idx_get(index)` for direct access and get_Count() to verify bounds before access. For `text` formatting, apply character-level properties (e.`g`., `PortionFormat::get_FillFormat()`) only after confirming the `Portion` object exists to prevent null dereferences.

Ensure round-trip fidelity by saving presentations in the same format (pptx) they were loaded from. Avoid mixing FOSS and commercial library headers in the same project — this can cause symbol conflicts and undefined behavior at runtime.

## Troubleshooting

This section helps you resolve common issues encountered when installing and using Aspose.Slides FOSS for C++. Each problem is paired with `a` verified cause and solution based on real-world usage patterns.

### Linker errors referencing undefined symbols for Aspose.Slides FOSS for C++ classes

This occurs when the linker cannot resolve symbols for classes like `Presentation`, `Slide`, or `DocumentProperties`. The most common cause is linking against an incorrect or incomplete static library build. Ensure the compiled aspose_slides_foss library is linked with the correct architecture (e.`g`., x64 vs x86) and that the library path is included in your linker settings. Also verify that all required object files or the static library (.`a` or.lib) are included in the final link step.

### Runtime crash or exception when constructing `Presentation`

If your program crashes immediately upon calling `Presentation::Presentation()`, check that the input file path is valid and accessible. Also ensure the file is `a` valid `.pptx` archive (`a` ZIP container with `XML` content). Corrupted or partially downloaded files often trigger internal assertions. Validate the file by opening it in `a` compatible viewer before processing.

### Missing symbols for `BulletFormat`, `Comment`, or `DocumentProperties` methods

This typically indicates that the library was compiled without full API surface support or that preprocessor macros disabled certain features. Confirm that the build configuration used to compile aspose_slides_foss includes all necessary source files. If building from source, ensure no `#ifdef` guards exclude the required classes. Rebuild the library with default settings and re-link.

### Incorrect namespace usage causing compilation errors

Using `using namespace Aspose::Slides;` instead of `using namespace Aspose.Slides FOSS for C++;` results in unresolved identifiers because the commercial namespace does not exist in the FOSS distribution. Always use the canonical import `using namespace Aspose.Slides FOSS for C++;` at the top of your source files. Double-check for typos or copy-paste errors from commercial library examples.

- Verify your build system includes the correct library path and library name (e.g., `-laspose_slides_foss`).
- Ensure the library version matches the header files used during compilation.
- Check that your compiler and linker flags are consistent (e.g., same C++ standard, same runtime library).

## FAQ

This section answers common questions about installing and using Aspose.Slides FOSS for C++. It clarifies namespace usage, import requirements, and compatibility expectations to ensure correct integration into your C++ projects.

### Why must I use `Aspose::Slides::Foss` and not `Aspose::Slides`?

The `Aspose::Slides::Foss` namespace is the only valid namespace for the open-source distribution of Aspose.Slides for C++. Using `Aspose::Slides` refers to `a` different, commercial library and will cause linker errors because the symbols do not match. Always declare `using namespace Aspose.Slides FOSS for C++;` at the top of your source files to ensure correct symbol resolution for classes like `Presentation`, `Slide`, and `DocumentProperties`.

### Can I use Python-`style` imports like `import Aspose.Slides FOSS for C++`?

No. C++ requires namespace declarations using `using namespace`, not Python-`style` import statements. Writing `import Aspose::Slides::Foss FOSS for C++` is invalid syntax in C++ and will cause compilation failure. Always use `using namespace Aspose.Slides FOSS for C++;` to access the library’s API surface.

### Does Aspose.Slides FOSS for C++ support `.ppt` files?

Aspose.Slides FOSS for C++ supports opening, creating, and saving `.pptx` files with full round-trip fidelity. Support for legacy `.ppt` formats is not available in this version. If you need to process `.ppt` files, convert them to `.pptx` first using `a` compatible tool before working with the library.

## API Reference Summary

This section summarizes the core API surface available in Aspose.Slides FOSS for C++, focusing on classes that enable `presentation` authoring and modification. The library exposes low-level access to `presentation` components such as `BulletFormat`, `Comment`, and `DocumentProperties`, all under the `Aspose::Slides::Foss` namespace. Developers work directly with these classes to manipulate `slide` content, formatting, and metadata without relying on higher-level abstractions.

```cpp
using namespace Aspose::Slides::Foss;

// Create a new presentation and set document properties
auto pres = System::MakeObject<Presentation>();
pres->get_DocumentProperties()->set_Title(u"Q3 Report");
pres->get_DocumentProperties()->set_Subject(u"Financial Summary");

// Add a comment to the first slide
auto slide = pres->get_Slides()->idx_get(0);
auto author = System::MakeObject<CommentAuthor>(u"Jane Doe", u"JD");
pres->get_CommentAuthors()->Add(author);
auto comment = System::MakeObject<Comment>(u"Review this section before finalizing.", slide, author, Drawing::PointF(1.0f, 1.0f), std::chrono::system_clock::now());
slide->get_Comments()->Add(comment);

// Save the presentation
pres->Save(u"report.pptx", SaveFormat::Pptx);
```

- Use `DocumentProperties` to set title, subject, and application metadata for presentation files.
- Attach `Comment` objects to slides using `CommentAuthor` instances for collaborative review workflows.
- Access `BulletFormat` through paragraph formatting to configure bullet type, character, and style programmatically.

## See Also

- [Get started with setup and first steps](/slides/cpp/getting-started/)
- [Browse full API reference documentation](/slides/cpp/api-overview/)
- [Read the official FOSS launch announcement](/slides/cpp/slides-introduction/)
- [Discover core features and capabilities](/slides/cpp/slides-key-features/)
- [Learn to create presentations programmatically](/slides/cpp/developer-guide/presentation-creation/)
