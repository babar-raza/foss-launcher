---
canonical: https://kb.aspose.org/slides/_index/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: Developers can manipulate `slide` content, formatting, and document properties
  using `a` focused set of classes aligned with the PowerPoint file model.
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
seoTitle: Aspose.Slides FOSS Kb _Index
slug: _index
title: Kb _Index
type: toc
url: /kb.aspose.org/slides/_index/
weight: 7
---

## Capabilities

Aspose.Slides FOSS for C++ provides core `presentation` processing capabilities through the `Aspose::Slides::Foss` namespace. Developers can manipulate `slide` content, formatting, and document properties using `a` focused set of classes aligned with the PowerPoint file model.

The library supports reading, creating, and saving `.pptx` presentations with full fidelity. Core operations include `slide` management—adding, removing, cloning, and reordering `slides`—as well as iterating over `slides` in `a` `presentation`. Shapes such as auto `shapes`, `picture` frames, tables, and connectors can be added and configured on `slides`.

Text formatting is supported at the portion, paragraph, and `text` `frame` levels, including `bullet` formatting via `BulletFormat`. Fill formatting for `shapes` includes solid, gradient, pattern, and `picture` fills, with gradient-specific control through `GradientFormat` and `GradientStopCollection`. Document metadata such as `title`, `subject`, and application `name` is accessible and modifiable via `DocumentProperties` and `IDocumentProperties`.

`Slide` `comments` are supported through the `Comment` class and `IComment` interface, allowing `text` and creation time to be set and retrieved. `Shape` effects like shadows and glows are handled via `EffectFormat`, while `camera` properties for 3D rendering are exposed through the `Camera` class.

## Quick Install

This section covers installation and setup for Aspose.Slides FOSS for C++. The library provides core `presentation` processing functionality through classes in the `Aspose::Slides::Foss` namespace.

```bash
pip install aspose-slides-foss-cpp
```

After installation, verify the `package` is accessible by compiling `a` minimal C++ program that includes the header and uses the `using namespace Aspose.Slides FOSS for C++;` directive. No additional configuration steps are required.

## Getting Started

This section covers the minimal setup and first steps for using Aspose.Slides FOSS for C++. It introduces the canonical namespace and demonstrates the simplest way to create and `save` `a` `presentation` file using the documented API surface.

```cpp
using namespace Aspose::Slides::Foss;

int main() {
 auto pres = System::MakeObject<Presentation>();
 pres->Save(u"output.pptx", SaveFormat::Pptx);
 return 0;
}
```

## Developer Guide

This section covers core operations for working with presentations using Aspose.Slides FOSS for C++. It includes handling `presentation` metadata, `slide` content, and formatting properties through the documented API surface.

Use `DocumentProperties` and `IDocumentProperties` to read and write `presentation` metadata such as `title`, `subject`, and application `name`. Access `slide`-level `comments` via `Comment` and `IComment` to manage annotations with timestamps and `author` context.

Format `shapes` using `FillFormat`, `EffectFormat`, and `BulletFormat` to control background, visual effects, and paragraph styling. For gradient fills, configure `GradientFormat` and `GradientStopCollection` with individual `GradientStop` entries to define `color` transitions.

- Presentation I/O — open, create, and save `.pptx` files
- Slide management — add, remove, clone, and iterate slides
- Shape support — AutoShapes, PictureFrames, Tables, Connectors
- Text formatting — TextFrame, Paragraph, Portion with bullet and style control
