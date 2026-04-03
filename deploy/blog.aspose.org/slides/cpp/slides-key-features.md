---
canonical: https://blog.aspose.org/slides/cpp/slides-key-features/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: Built on the `Aspose::Slides::Foss` namespace, it supports core `presentation`
  operations including `slide` manipulation, shape rendering, and format...
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
page_role: feature_blog
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FOSS Slides Key Features
slug: slides-key-features
title: Slides Key Features
type: feature_blog
url: /blog.aspose.org/slides/cpp/slides-key-features/
weight: 17
---

## Introduction

If you have ever needed to programmatically create, edit, or convert PowerPoint presentations in `a` C++ application without relying on Microsoft Office, Aspose.Slides FOSS for C++ provides `a` lightweight, cross-platform solution. Built on the `Aspose::Slides::Foss` namespace, it supports core `presentation` operations including `slide` manipulation, shape rendering, and format conversion.

- Process presentation files in PPTX, PPT, ODP, and other supported formats with full round-trip fidelity
- Add, remove, clone, and reorder slides using the `Presentation` and `ISlideCollection` interfaces
- Work with shapes, text frames, and formatting via `AutoShape`, `TextFrame`, and `Portion` classes

## Key Highlights

If you have ever needed to programmatically manage `presentation` metadata or apply precise `text` formatting in C++ without external dependencies, Aspose.Slides FOSS for C++ provides lightweight, header-based APIs for document properties and paragraph styling.

- Set presentation metadata using `DocumentProperties` to define title, subject, and application name.
- Configure paragraph bullet formatting via `BulletFormat` to specify bullet type, character, and position.
- Apply gradient fills to shapes using `GradientFormat` and `GradientStopCollection` for visual consistency.
- Attach comments to slides with `Comment`, including author, position, and creation timestamp.

```cpp
using namespace Aspose::Slides::Foss;

// Set presentation title and subject
auto docProps = MakeObject<DocumentProperties>();
docProps->set_title(L"Q4 Sales Report");
docProps->set_subject(L"Quarterly Financial Summary");
docProps->set_name_of_application(L"Aspose.Slides FOSS for C++");
```

## Getting Started

If you have ever needed to programmatically manage `presentation` metadata or apply precise `text` formatting in C++, Aspose.Slides FOSS for C++ provides lightweight, header-only access to core PowerPoint features via the `Aspose::Slides::Foss` namespace. The library exposes classes like `DocumentProperties` for metadata and `BulletFormat` for paragraph styling without requiring external dependencies or GUI interaction.

```cpp
using namespace Aspose::Slides::Foss;

// Create a new presentation and set document properties
auto pres = System::MakeObject<Presentation>();
pres->get_DocumentProperties()->set_Title(u"CppSlides 2025 Overview");
pres->get_DocumentProperties()->set_Subject(u"Technical presentation for C++ developers");

// Save the presentation
pres->Save(u"output.pptx", SaveFormat::Pptx);
```

The `DocumentProperties` class enables setting standard metadata such as `title` and `subject`, while `BulletFormat` allows fine-grained control over paragraph `bullet` types and characters. These classes integrate directly into `slide` content workflows without requiring commercial licensing or external services.

## See Also

- [Introducing the open-source C++ library](/slides/cpp/slides-introduction/)
- [Create presentations from scratch](/slides/cpp/developer-guide/presentation-creation/)
- [Work with slides programmatically](/slides/cpp/developer-guide/slide-manipulation/)
- [Convert file formats easily](/slides/cpp/convert-pptx-to-fodp/)
- [Fix common errors and errors](/slides/cpp/fix-presentations-errors/)
