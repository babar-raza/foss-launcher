---
canonical: https://docs.aspose.org/slides/cpp/getting-started/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: This library enables programmatic `slide` manipulation, `text` formatting,
  and shape handling without requiring Microsoft PowerPoint.
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
page_role: getting_started
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: Getting Started with Aspose.Slides FOSS for C++ | Guide
slug: getting-started
title: Getting Started with Aspose.Slides FOSS for C++
type: getting_started
url: /docs.aspose.org/slides/cpp/getting-started/
weight: 4
---

## Overview

Getting started with Aspose.Slides FOSS for C++ means building applications that create, modify, and `save` PowerPoint-compatible presentations using open-source C++ code. This library enables programmatic `slide` manipulation, `text` formatting, and shape handling without requiring Microsoft PowerPoint.

You can work with `slide` content including `paragraphs` and `bullet` formatting through the `BulletFormat` class, which exposes methods like `BulletType()`, `set_type()`, and `set_character()` to control list styling. `Slide` `comments` are represented by the `Comment` class, supporting `text` content and creation timestamps via `text()`, `set_text()`, `created_time()`, and `set_created_time()`.

The library supports core `presentation` operations such as adding `shapes`, applying fills (solid, gradient, pattern), and managing document properties like `title` and `subject`. It reads and writes `PPTX` files with full fidelity and also supports writing to `FODP` format.

## Prerequisites

To use Aspose.Slides FOSS for C++, ensure you have C++17 or later installed, along with CMake 3.16 or newer for dependency management. Install the library using CMake’s find_package mechanism as shown in the installation `reference`.

```cmake
find_package(aspose_slides_foss REQUIRED)
```

Include the main header and use the canonical namespace `Aspose::Slides::Foss`. The `Presentation` class enables creating and manipulating `slides`, while `DocumentProperties` allows setting metadata such as the `author` via `set_author()`. The `Camera` class supports 3D scene rendering, and its `has_parent()` method returns true if initialized with `a` parent `XML` element.

## Installation

Install Aspose.Slides FOSS for C++ using CMake’s find_package directive to integrate the library into your build system. This ensures correct linking and header inclusion without manual path configuration.

```cmake
find_package(aspose_slides_foss REQUIRED)
```

After installation, include the main header and use the canonical namespace `Aspose::Slides::Foss`. The `Camera` class represents `camera` properties for 3D scene rendering, and `DocumentProperties.set_subject()` sets the `subject` of the `presentation`.

```cpp
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/document_properties.h>

using namespace Aspose::Slides::Foss;

Presentation pres;
pres.document_properties().set_subject("Q1 Financial Summary");
```

## Quick Start

To create and modify `a` `presentation` using Aspose.Slides FOSS for C++, include the main header and use the canonical namespace `Aspose::Slides::Foss`. The `Presentation` class provides the entry point for working with `slides`, `shapes`, and document properties.

```cpp
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/export/save_format.h>

using namespace Aspose::Slides::Foss;

Presentation pres;
pres.document_properties().set_title("Quick Start Demo");
pres.document_properties().set_subject("FOSS C++ Presentation");
pres.save("quick_start.pptx", SaveFormat::PPTX);
```

You can also add `comments` to `slides` using the `Comment` class. Construct `a` comment with `text`, associated `slide`, `author`, `position`, and creation time, then attach it to `a` `slide`'s comment collection.

```cpp
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/comment.h>
#include <Aspose/Slides/Foss/comment_author.h>
#include <Aspose/Slides/Foss/export/save_format.h>

using namespace Aspose::Slides::Foss;

Presentation pres;
auto& slide = pres.slides()[0];
auto author = pres.comment_authors().add_author(u"Author Name", u"AN");
auto comment = new Comment(u"This is a sample comment.", &slide, author, Drawing::PointF(100, 100), std::chrono::system_clock::now());
slide.comments().add(comment);
pres.save("with_comment.pptx", SaveFormat::PPTX);
```

## Next Steps

To continue working with Aspose.Slides FOSS for C++, explore how to manipulate `slide` `comments` with precise timestamps using `Comment.set_created_time()` and adjust shape geometry using `AdjustValue`.

- Learn how to format paragraph bullets using `BulletFormat` in the [Text Formatting Guide](/slides/cpp/developer-guide/text-formatting).
- Review all available shape types and their properties in the [Shapes API Reference](/slides/cpp/api-reference).
- Understand how to manage presentation metadata like author and subject via `DocumentProperties` in the [Document Properties Tutorial](/slides/cpp/developer-guide/document-properties).

## See Also

- [Aspose.Slides FOSS for C++ API Reference](/slides/cpp/api-overview/)
- [How to Convert File Formats with Aspose.Slides FOSS for C++](/slides/cpp/convert-pptx-to-fodp/)
- [How to Fix Common Errors with Aspose.Slides FOSS for C++](/slides/cpp/fix-presentations-errors/)
- [How to Load Files with Aspose.Slides FOSS for C++](/slides/cpp/load-presentations/)
- [How to Optimize Performance with Aspose.Slides FOSS for C++](/slides/cpp/optimize-presentations/)
