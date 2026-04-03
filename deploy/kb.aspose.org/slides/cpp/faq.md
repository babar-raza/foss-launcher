---
canonical: https://kb.aspose.org/slides/cpp/frequently-asked-questions/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: It enables `slide` manipulation, shape rendering, `text` formatting,
  and fill styles. However, certain advanced features remain unsupported as documented
  in...
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
page_role: faq
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FOSS for C++ FAQ | Guide
slug: frequently-asked-questions
title: Aspose.Slides FOSS for C++ FAQ
type: faq
url: /kb.aspose.org/slides/cpp/frequently-asked-questions/
weight: 8
---

## Frequently Asked Questions

Aspose.Slides FOSS for C++ supports core `presentation` operations including opening, creating, and saving `.pptx` files with full round-trip fidelity. It enables `slide` manipulation, shape rendering, `text` formatting, and fill styles. However, certain advanced features remain unsupported as documented in the product's limitations.

### What areas are not yet available in Aspose.Slides FOSS for C++?

The following areas are not yet available in Aspose.Slides FOSS for C++: animation effects, 3D scene rendering beyond basic `camera` setup, `comments` beyond basic `text` and timestamp support, and advanced shape `adjustments`. These limitations are explicitly listed in the product's README.md and reflect the current scope of the FOSS distribution. Developers should avoid relying on these features for production workflows until future releases extend support.

### How do I add `a` `bullet` to `a` paragraph?

Use the `BulletFormat` class to configure `bullet` properties on `a` paragraph. First, access the paragraph through `a` `text` `frame`, then call get_BulletFormat() to obtain the `bullet` formatting object. Set the `bullet` `type` and character as needed using `set_type()` and `set_character()`.

```cpp
using namespace Aspose::Slides::Foss;

// Assuming 'paragraph' is a valid Paragraph pointer
auto bulletFormat = paragraph->get_BulletFormat();
bulletFormat->set_type(BulletType::Circle);
bulletFormat->set_character(u'•');
```

### Can I use 3D `camera` settings in Aspose.Slides FOSS for C++?

Yes, basic 3D `camera` settings are supported via the `Camera` class. You can initialize internal `camera` state and `save` `camera` properties, but advanced 3D scene rendering features such as lighting control or complex projections are not available. Use `ensure_camera()` to create or retrieve the `camera` element with default `preset` "orthographicFront".

### How do I set document properties like `title` and `subject`?

Access the `presentation`'s document properties through the `DocumentProperties` interface. Call `set_title()` and `set_subject()` to assign values, then `save` the `presentation` to persist changes. These properties are stored in the `presentation`'s core properties part and survive round-trip `save` operations.

```cpp
using namespace Aspose::Slides::Foss;

auto pres = System::MakeObject<Presentation>();
auto docProps = pres->get_DocumentProperties();
docProps->set_title(u"Meeting C++ 2025 Slides");
docProps->set_subject(u"C++ Conference Presentation");
pres->Save(u"output.pptx", SaveFormat::Pptx);
```

## See Also

- [Troubleshooting common issues](/slides/cpp/troubleshooting-guide/)
- [Convert file formats step-by-step](/slides/cpp/convert-pptx-to-fodp/)
- [Fix common errors effectively](/slides/cpp/fix-presentations-errors/)
- [Load files correctly and efficiently](/slides/cpp/load-presentations/)
- [Optimize performance tips](/slides/cpp/optimize-presentations/)
