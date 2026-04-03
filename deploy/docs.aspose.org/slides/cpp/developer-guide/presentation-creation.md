---
canonical: https://docs.aspose.org/slides/cpp/developer-guide/presentation-creation/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: You start with `a` blank `presentation`, add `slides` and `shapes`, apply
  formatting, and `save` the result as `a`.pptx file.
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
seoTitle: Create Presentations with Aspose.Slides FOSS for C++ | Guide
slug: presentation-creation
title: Create Presentations with Aspose.Slides FOSS for C++
type: workflow_page
url: /docs.aspose.org/slides/cpp/developer-guide/presentation-creation/
weight: 18
---

## Overview

This guide walks you through creating and manipulating presentations using Aspose.Slides FOSS for C++. You start with `a` blank `presentation`, add `slides` and `shapes`, apply formatting, and `save` the result as `a`.pptx file.

Using the canonical namespace `Aspose::Slides::Foss`, you work directly with core objects like `AutoShape`, `FillFormat`, `BulletFormat`, and `DocumentProperties`. Each object exposes methods defined in the API surface to configure visual and structural properties. The workflow follows `a` linear pattern: instantiate, configure, and persist.

```cpp
using namespace Aspose::Slides::Foss;

// Create a new presentation
auto pres = System::MakeObject<Presentation>();

// Access the first slide
auto slide = pres->get_Slides()->idx_get(0);

// Add a rectangle auto shape
auto shape = slide->get_Shapes()->AddAutoShape(ShapeType::Rectangle, 100.0f, 100.0f, 300.0f, 200.0f);

// Set solid fill color
auto fillFormat = shape->get_FillFormat();
fillFormat->set_FillType(FillType::Solid);
fillFormat->get_SolidFillColor()->set_Color(System::Drawing::Color::get_LightBlue());

// Save the presentation
pres->Save(u"output.pptx", SaveFormat::Pptx);
```

- Use AddAutoShape() to insert geometric shapes for visual emphasis.
- Apply `FillFormat` to define background color or gradient for shapes.
- Save the final presentation in .pptx format using Save() with `SaveFormat::Pptx`.

## Working with Data

This guide walks you through reading, writing, and modifying `presentation` metadata and `slide` content using Aspose.Slides FOSS for C++. You load `a` `presentation`, access its document properties and `comments`, then update `text` formatting and fill styles on `shapes`.

```cpp
using namespace Aspose::Slides::Foss;

// Load an existing presentation
auto pres = System::MakeObject<Presentation>(u"input.pptx");

// Access document properties
auto docProps = pres->get_DocumentProperties();

// Modify title and subject
docProps->set_title(u"Updated Presentation Title");
docProps->set_subject(u"FOSS C++ Workflow Example");

// Save the updated presentation
pres->Save(u"output.pptx", Aspose::Slides::Export::SaveFormat::Pptx);
```

- Use `DocumentProperties` to read or update metadata like title and subject before saving.
- Modify `Comment` text or creation time to reflect updated review notes.
- Apply `FillFormat` and `EffectFormat` changes to shapes for visual consistency.

To modify `text` formatting on `a` shape, access its `TextFrame`, then adjust paragraph and portion properties. The `BulletFormat` class lets you configure `bullet` `type`, character, and `style` for list items.

```cpp
using namespace Aspose::Slides::Foss;

auto pres = System::MakeObject<Presentation>(u"input.pptx");
auto slide = pres->get_Slides()->idx_get(0);
auto shape = System::DynamicCast<AutoShape>(slide->get_Shapes()->idx_get(0));
auto textFrame = shape->get_TextFrame();
auto paragraph = textFrame->get_Paragraphs()->idx_get(0);
auto portion = paragraph->get_Portions()->idx_get(0);

// Update bullet formatting
auto bulletFormat = paragraph->get_BulletFormat();
bulletFormat->set_type(BulletType::Symbol);
bulletFormat->set_character(0x2022); // bullet character

// Set portion text and formatting
portion->set_Text(u"New bullet point text");

pres->Save(u"output.pptx", Aspose::Slides::Export::SaveFormat::Pptx);
```

- Configure bullet symbols using `BulletFormat::set_character()` with Unicode values.
- Apply consistent bullet styles across paragraphs to improve slide readability.
- Update portion text directly without recreating the text frame structure.

Fill formatting on `shapes` supports solid, gradient, and `picture` fills. Use `FillFormat` to manage fill `type` and `GradientFormat` for multi-stop gradients with configurable `shapes` and positions.

```cpp
using namespace Aspose::Slides::Foss;

auto pres = System::MakeObject<Presentation>(u"input.pptx");
auto slide = pres->get_Slides()->idx_get(0);
auto shape = System::DynamicCast<AutoShape>(slide->get_Shapes()->idx_get(1));
auto fillFormat = shape->get_FillFormat();

// Apply gradient fill
fillFormat->set_FillType(FillType::Gradient);
auto gradientFormat = fillFormat->get_GradientFormat();
gradientFormat->set_GradientShape(GradientShape::Linear);

// Add gradient stops
auto stops = gradientFormat->get_GradientStops();
auto stop1 = System::MakeObject<GradientStop>();
auto stop2 = System::MakeObject<GradientStop>();
stop1->set_Position(0.0f);
stop2->set_Position(1.0f);
// Note: Color setting requires SimpleColorFormat (not shown in API surface)

pres->Save(u"output.pptx", Aspose::Slides::Export::SaveFormat::Pptx);
```

- Use `GradientFormat::set_GradientShape()` to switch between linear and radial gradients.
- Adjust `GradientStop` positions to control color transition points across the shape.
- Apply `FillFormat` changes to `AutoShape` objects to maintain visual hierarchy.

## Code Examples

This guide walks you through creating `a` new `presentation`, adding `a` `slide` with `a` `text` shape, and applying `bullet` formatting using Aspose.Slides FOSS for C++. You start with an empty `presentation`, `insert` `a` `title` `slide`, populate `a` `text` shape with `paragraphs`, and configure `bullet` styles using the `BulletFormat` class.

```cpp
using namespace Aspose::Slides::Foss;

// Create a new presentation
auto presentation = System::MakeObject<Presentation>();

// Add a title slide
auto slide = presentation->get_Slides()->AddEmptySlide(presentation->get_Slides()->get_Item(0));

// Access the first shape (AutoShape) on the slide
auto shape = System::DynamicCast<Aspose::Slides::Foss::AutoShape>(slide->get_Shapes()->idx_get(0));

// Set the shape text
shape->get_TextFrame()->set_Text("Key Features of Aspose.Slides FOSS for C++");

// Save the presentation
presentation->Save(u"output.pptx", Aspose::Slides::Export::SaveFormat::Pptx);
```

- Use this approach when generating conference slide decks from structured data.
- Apply when preparing technical documentation for internal training sessions.
- Leverage for rapid prototyping of presentation content before final styling.

Next, add multiple `paragraphs` to the shape and apply `bullet` formatting to each. Access the `BulletFormat` object through each `Paragraph` to set the `bullet` `type` and character. This ensures consistent visual hierarchy across `slide` content.

```cpp
using namespace Aspose::Slides::Foss;

auto presentation = System::MakeObject<Presentation>();
auto slide = presentation->get_Slides()->AddEmptySlide(presentation->get_Slides()->get_Item(0));
auto shape = System::DynamicCast<Aspose::Slides::Foss::AutoShape>(slide->get_Shapes()->idx_get(0));
auto textFrame = shape->get_TextFrame();

// Clear existing paragraphs
textFrame->get_Paragraphs()->Clear();

// Add paragraphs
auto para1 = System::MakeObject<Paragraph>();
para1->get_PortionFormat()->set_Text(u"Open-source and free to use");
textFrame->get_Paragraphs()->Add(para1);

auto para2 = System::MakeObject<Paragraph>();
para2->get_PortionFormat()->set_Text(u"Full PPTX round-trip support");
textFrame->get_Paragraphs()->Add(para2);

// Apply bullet formatting
for (int i = 0; i < textFrame->get_Paragraphs()->get_Count(); ++i) {
 auto bulletFormat = textFrame->get_Paragraphs()->idx_get(i)->get_BulletFormat();
 bulletFormat->set_type(BulletType::Circle);
 bulletFormat->set_character(u'•');
}

presentation->Save(u"bulleted.pptx", Aspose::Slides::Export::SaveFormat::Pptx);
```

- Use bullet formatting when listing features, requirements, or steps in a workflow.
- Apply consistent bullet styles to improve readability in technical presentations.
- Modify bullet characters to match brand guidelines or accessibility standards.

## Notes and Best Practices

When working with Aspose.Slides FOSS for C++, memory management and object lifecycle control are critical for stable, long-running applications. The library follows RAII principles, so always ensure `Presentation` objects are destroyed or reset after use to release file handles and internal resources. Avoid holding multiple `Presentation` instances open simultaneously unless necessary, and prefer reusing `AutoShape` and `FillFormat` objects within `a` single `presentation` context to reduce allocation overhead.

- Use `std::shared_ptr<Presentation>` to manage presentation lifetimes and avoid dangling pointers when passing objects across functions.
- Call `save()` only once per `Presentation` instance to prevent unintended side effects from repeated serialization.
- Avoid modifying slide content inside tight loops without periodic cleanup; batch changes and commit them in a single pass.
- Validate input files with FileFormatUtil before loading to catch unsupported or corrupted formats early.

## See Also

- [Introducing the open-source C++ library](/slides/cpp/slides-introduction/)
- [Key capabilities and features overview](/slides/cpp/slides-key-features/)
- [Step-by-step presentation workflow guide](/slides/cpp/developer-guide/slide-manipulation/)
- [Convert documents between major formats](/slides/cpp/convert-pptx-to-fodp/)
- [Resolve frequent issues and errors](/slides/cpp/fix-presentations-errors/)
