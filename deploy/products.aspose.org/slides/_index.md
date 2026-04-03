---
canonical: https://products.aspose.org/slides/_index/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: It supports reading, writing, and modifying.pptx files with full fidelity,
  including `slide` management, shape rendering, and `text` formatting.
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
page_role: landing
platform: cpp
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Slides FOSS for C++ | Guide
slug: _index
title: Aspose.Slides FOSS for C++
type: landing
url: /products.aspose.org/slides/_index/
weight: 1
---

## Overview

Aspose.Slides FOSS for C++ enables developers to process PowerPoint presentations programmatically without requiring Microsoft PowerPoint. It supports reading, writing, and modifying.pptx files with full fidelity, including `slide` management, shape rendering, and `text` formatting.

The library exposes core `presentation` constructs through the `IPresentation` interface and supporting classes such as `Slide`, `Shape`, and `TextFrame`. Formatting capabilities include `FillFormat`, `GradientFormat`, `BulletFormat`, and `EffectFormat`, while metadata is handled via `DocumentProperties` and `IDocumentProperties`. Comments are supported through the `Comment` and `IComment` interfaces.

- Read and write .pptx files with round-trip fidelity
- Manage slides: add, remove, clone, and reorder
- Format shapes with solid, gradient, and picture fills
- Apply paragraph and character formatting including bullets
- Add and manipulate slide comments with timestamps
- Access and modify presentation metadata (title, subject, app version)

## Key Features

Aspose.Slides FOSS for C++ enables developers to process PowerPoint presentations programmatically without requiring Microsoft PowerPoint. It exposes core `presentation` constructs through the `IPresentation` interface and supporting classes such as `Slide`, `Shape`, `TextFrame`, and `FillFormat`, all under the `Aspose::Slides::Foss` namespace.

- Read and write `.pptx` files with full round-trip fidelity using the `IPresentation` interface
- Manipulate slides—add, remove, clone, and reorder—via the `SlideCollection` interface
- Format text with character, paragraph, and bullet styling through `TextFrame`, `Paragraph`, and `BulletFormat`
- Apply fill styles—including solid, gradient, and picture fills—using `FillFormat`, `GradientFormat`, and `GradientStopCollection`
- Attach comments to slides with timestamps and author context via the `Comment` class
- Access and modify document properties such as title, subject, and company using `DocumentProperties`

## Quick Start

Aspose.Slides FOSS for C++ enables programmatic creation, modification, and conversion of PowerPoint presentations without requiring Microsoft PowerPoint. It exposes core `presentation` constructs through the `IPresentation` interface and supporting classes such as `AutoShape`, `AdjustValue`, and `BasePortionFormat`.

```cpp
using namespace Aspose::Slides::Foss;

// Create a new presentation and add a title slide
auto pres = MakeObject<Presentation>();
auto slide = pres->get_Slides()->idx_get(0);
slide->get_Shapes()->AddAutoShape(ShapeType::Rectangle, 50.0f, 50.0f, 400.0f, 100.0f);
pres->Save(u"output.pptx", SaveFormat::Pptx);
```

## See Also

- [Introducing Slides Foss Cpp](/slides/cpp/slides-introduction/)
- [Explore key features](/slides/cpp/slides-key-features/)
- [Create presentations from scratch](/slides/cpp/developer-guide/presentation-creation/)
- [Work with slides efficiently](/slides/cpp/developer-guide/slide-manipulation/)
- [Convert file formats easily](/slides/cpp/convert-pptx-to-fodp/)
