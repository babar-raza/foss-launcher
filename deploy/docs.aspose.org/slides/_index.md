---
canonical: https://docs.aspose.org/slides/_index/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: Developers can manipulate `.pptx` files by adding, removing, cloning,
  and reordering `slides`, as well as working with `shapes`, `text`, and formatting.
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
seoTitle: Aspose.Slides FOSS Docs _Index
slug: _index
title: Docs _Index
type: toc
url: /docs.aspose.org/slides/_index/
weight: 2
---

## Capabilities

Aspose.Slides FOSS for C++ provides core `presentation` processing capabilities through the `Aspose::Slides::Foss` namespace. Developers can manipulate `.pptx` files by adding, removing, cloning, and reordering `slides`, as well as working with `shapes`, `text`, and formatting.

The library supports shape formatting via `FillFormat`, `GradientFormat`, `EffectFormat`, and `BulletFormat`, enabling control over solid, gradient, and `picture` fills, as well as shadow and glow effects. Text formatting includes paragraph and portion-level properties, with `bullet` configuration through `BulletFormat`.

- Slide management — add, remove, clone, reorder, and iterate slides
- Shape handling — AutoShapes, PictureFrames, Tables, Connectors
- Text formatting — `TextFrame`, `Paragraph`, `Portion`, and `BulletFormat`
- Fill and effects — `FillFormat`, `GradientFormat`, `EffectFormat`
- Document properties — `DocumentProperties`, `IDocumentProperties`
- Comments — `Comment`, `IComment` with author, position, and timestamp support

## Quick Install

This section covers installation of Aspose.Slides FOSS for C++, `a` library for creating, reading, and manipulating PowerPoint-compatible presentations using the Aspose.Slides FOSS for C++ namespace.

```bash
pip install aspose-slides-foss
```

After installation, verify the setup by importing the namespace and instantiating `a` `Presentation` object. Confirm that the constructor completes without error and that basic operations like adding `a` `slide` succeed.

## Getting Started

This section covers the minimal setup and first steps for using Aspose.Slides FOSS for C++. It introduces the core namespace and demonstrates how to instantiate `a` `Presentation` object to `begin` working with `slide` decks.

```cpp
using namespace Aspose::Slides::Foss;

int main() {
 auto presentation = System::MakeObject<Presentation>();
 return 0;
}
```

## Developer Guide

This section covers core operations for working with presentations using Aspose.Slides FOSS for C++. It includes handling `presentation` metadata, `slide` content, and shape formatting through the documented API surface.

Use `DocumentProperties` and `IDocumentProperties` to read and write `presentation` metadata such as `title`, `subject`, and application `name`. Access `slide`-level `comments` via `Comment` and `IComment` to manage annotations with timestamps and `author` context.

Format `shapes` using `FillFormat`, `GradientFormat`, `EffectFormat`, and `BulletFormat` to control visual appearance, including solid and gradient fills, shadow/glow effects, and paragraph `bullet` styling.
