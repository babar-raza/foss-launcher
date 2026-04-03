---
canonical: https://reference.aspose.org/slides/_index/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: Developers can manipulate `.pptx` files by creating, loading, and saving
  presentations while preserving formatting fidelity across round-trip operations.
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
page_role: toc
platform: cpp
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Slides FOSS Reference _Index
slug: _index
title: Reference _Index
type: toc
url: /reference.aspose.org/slides/_index/
weight: 5
---

## Capabilities

Aspose.Slides FOSS for C++ provides core `presentation` processing capabilities through the `Aspose::Slides::Foss` namespace. Developers can manipulate `.pptx` files by creating, loading, and saving presentations while preserving formatting fidelity across round-trip operations.

The API supports `slide`-level operations including adding, removing, cloning, reordering, and iterating `slides`. `Shape` manipulation covers auto `shapes`, `picture` frames, tables, and connectors. Text formatting is handled via `TextFrame`, `Paragraph`, and `Portion` objects with support for character, paragraph, and `text` `frame` formatting including `bullet` styles via `BulletFormat`.

Fill formatting is available through `FillFormat`, `GradientFormat`, `GradientStop`, and `GradientStopCollection` for solid, gradient, pattern, and `picture` fills. Effect formatting (shadow, glow, blur) is exposed via `EffectFormat`. `Slide` `comments` are managed using `Comment` and `IComment` interfaces, and document properties such as `title`, `subject`, and `company` are accessible via `DocumentProperties` and `IDocumentProperties`.

## Quick Install

This section covers installation and setup for Aspose.Slides FOSS for C++. The library provides core `presentation` processing capabilities through the `Aspose::Slides::Foss` namespace, including `slide` manipulation, shape handling, `text` formatting, and fill effects.

```bash
pip install aspose-slides-foss-cpp
```

After installation, verify the `package` is available by importing the canonical namespace `Aspose::Slides::Foss` in `a` C++ source file. No additional configuration or environment setup is required.

## Getting Started

This section covers the minimal setup and first steps for using Aspose.Slides FOSS for C++. It introduces the canonical namespace `Aspose::Slides::Foss` and demonstrates how to instantiate core objects like `DocumentProperties` and `Comment` using the documented API surface.

```cpp
using namespace Aspose::Slides::Foss;

int main() {
 auto docProps = DocumentProperties();
 docProps.set_title("Sample Presentation");
 docProps.set_subject("FOSS C++ Usage");
 return 0;
}
```

## Developer Guide

This section covers core object model classes for working with `presentation` content in Aspose.Slides FOSS for C++. It includes foundational interfaces and concrete types for `slide` `comments`, document properties, and shape formatting.

- Comment and IComment — create, read, and modify slide comments with author, text, and timestamp support
- DocumentProperties and IDocumentProperties — access and update presentation metadata such as title, subject, company, and application version
- FillFormat, EffectFormat, and BulletFormat — configure shape fills, visual effects, and paragraph bullet formatting
- GradientFormat, GradientStop, and GradientStopCollection — define and manipulate gradient fill properties
