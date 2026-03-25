---
canonical: https://docs.aspose.org/slides/cpp/developer-guide/presentation-creation/
canonical_import: Aspose::Slides
code_import: Aspose::Slides
date: '2026-03-24T16:29:46Z'
dateModified: '2026-03-24T16:29:46Z'
datePublished: '2026-03-24T16:29:46Z'
description: It covers loading existing `.pptx` files, creating new presentations
  from scratch, and saving the results — all using the canonical `Aspose::Slides`
  C++ API.
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
page_role: workflow_page
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: Create Presentations with Aspose.Slides FOSS for C++ | Guide
slug: presentation-creation
title: Create Presentations with Aspose.Slides FOSS for C++
type: workflow_page
url: /docs.aspose.org/slides/cpp/developer-guide/presentation-creation/
weight: 17
---

## Overview

This guide walks you through creating and manipulating PowerPoint presentations using Aspose.Slides FOSS for C++. It covers loading existing `.pptx` files, creating new presentations from scratch, and saving the results — all using the canonical `Aspose::Slides` C++ API.

```cpp
#include <Aspose::Slides>

int main() {
    // Create a new presentation
    auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>();

    // Save to disk
    pres->Save(u"output.pptx", Aspose::Slides::[identifier omitted]::Pptx);

    return 0;
}
```

- Use this approach when generating reports or slide decks programmatically.
- Use it to bootstrap templates before injecting dynamic content.
- Use it to validate presentation structure before adding complex elements.

## Working with Data

This guide walks you through reading, writing, and modifying data elements in presentations using Aspose.Slides FOSS for C++. You load a `.pptx` file, access slide content such as shapes and text frames, and update or extract data like table cells or paragraph text.

```cpp
#include <Aspose::Slides>

int main() {
    auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>(u"input.pptx");
    auto slide = pres->get_Slides()->idx_get(0);
    auto shape = System::[identifier omitted]<Aspose::Slides::IAutoShape>(slide->get_Shapes()->idx_get(0));
    auto textFrame = shape->get_TextFrame();
    return 0;
}
```

- Use this pattern when extracting slide titles or body text for indexing or reporting.
- Apply when validating content before exporting to PDF or HTML.
- Adopt when auditing presentation metadata or preparing slides for localization.

To modify text, access the `Portion` objects within a `Paragraph` and update their `Text` property. Tables require navigating `Table` objects, then rows and cells, to read or write cell values.

```cpp
#include <Aspose::Slides>

int main() {
    auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>(u"input.pptx");
    auto slide = pres->get_Slides()->idx_get(0);
    auto table = System::[identifier omitted]<Aspose::Slides::ITable>(slide->get_Shapes()->idx_get(1));
    table->get_Rows()->idx_get(0)->get_Cells()->idx_get(0)->get_CellFormat()->set_BorderTop(nullptr);
    table->get_Rows()->idx_get(0)->get_Cells()->idx_get(0)->set_Text(u"Updated Header");
    pres->Save(u"output.pptx", Aspose::Slides::[identifier omitted]::Pptx);
    return 0;
}
```

- Use this to update report headers or data labels programmatically.
- Apply when generating dynamic dashboards from template presentations.
- Adopt when correcting or localizing table content across multiple slides.

For text formatting, set font properties on `Portion` objects. You can change font name, size, bold, italic, and color directly on the portion level.

```cpp
#include <Aspose::Slides>

int main() {
    auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>(u"input.pptx");
    auto slide = pres->get_Slides()->idx_get(0);
    auto shape = System::[identifier omitted]<Aspose::Slides::IAutoShape>(slide->get_Shapes()->idx_get(0));
    auto textFrame = shape->get_TextFrame();
    auto portion = textFrame->get_Paragraphs()->idx_get(0)->get_Portions()->idx_get(0);
    portion->get_PortionFormat()->set_FontHeight(18);
    portion->get_PortionFormat()->get_FillFormat()->set_FillType(Aspose::Slides::[identifier omitted]::Solid);
    portion->get_PortionFormat()->get_FillFormat()->get_SolidFillColor()->set_Color(System::Drawing::Color::get_Red());
    pres->Save(u"formatted.pptx", Aspose::Slides::[identifier omitted]::Pptx);
    return 0;
}
```

- Use this to highlight key metrics in executive summaries.
- Apply when enforcing brand colors across presentation text.
- Adopt when preparing slides for accessibility compliance (e.g., contrast checks).

## Code Examples

This guide walks you through creating a new presentation, adding a slide, inserting a title shape, and saving the result as a `.pptx` file using Aspose.Slides FOSS for C++. The workflow starts with an empty presentation object and ends with a valid PowerPoint file ready for sharing or further editing.

```cpp
#include <Aspose::Slides>

int main() {
    // Create a new presentation
    auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>();

    // Access the first slide
    auto slide = pres->get_Slides()->idx_get(0);

    // Add a title text box
    auto titleShape = slide->get_Shapes()->[identifier omitted](Aspose::Slides::[identifier omitted]::Rectangle, 50.0f, 50.0f, 500.0f, 100.0f);
    titleShape->get_TextFrame()->set_Text("Welcome to Aspose::Slides FOSS for C++");

    // Save the presentation
    pres->Save(u"output.pptx", Aspose::Slides::[identifier omitted]::Pptx);

    return 0;
}
```

- Use this pattern when generating slide decks for internal meetings or conferences like cppcon slides 2025 or meeting cpp slides.
- Replace the title text with dynamic content such as event names, speaker names, or session titles.
- Adjust the rectangle coordinates and dimensions to match your branding guidelines for title slides.

Next, extend the workflow by adding a content slide with a bullet list. This demonstrates how to create a new slide, apply a layout, and populate it with structured text using the `[identifier omitted]` and `Paragraph` objects available in the API surface.

```cpp
#include <Aspose::Slides>

int main() {
    auto pres = System::[identifier omitted]<Aspose::Slides::Presentation>();

    // Add a new slide with title and content layout
    auto slide = pres->get_Slides()->[identifier omitted](pres->get_SlideSize()->get_Width(), pres->get_SlideSize()->get_Height());

    // Insert title
    auto titleShape = slide->get_Shapes()->[identifier omitted](Aspose::Slides::[identifier omitted]::Rectangle, 50.0f, 40.0f, 600.0f, 60.0f);
    titleShape->get_TextFrame()->set_Text("Key Features of Aspose::Slides FOSS");

    // Insert content text frame
    auto contentShape = slide->get_Shapes()->[identifier omitted](Aspose::Slides::[identifier omitted]::Rectangle, 50.0f, 120.0f, 600.0f, 200.0f);
    auto textFrame = contentShape->get_TextFrame();
    textFrame->set_Text("Bullet list example:\n- Slide creation\n- Shape insertion\n- Text formatting");

    // Save the updated presentation
    pres->Save(u"content_presentation.pptx", Aspose::Slides::[identifier omitted]::Pptx);

    return 0;
}
```

- Use this approach when preparing technical documentation slides for events like cppnow slides or python slides for beginners.
- Modify the bullet text programmatically to reflect session outcomes or feature highlights.
- Resize and reposition shapes to fit different slide layouts or aspect ratios.

## Notes and Best Practices

When using Aspose.Slides FOSS for C++, ensure you include only the canonical header `#include <Aspose.Slides FOSS for C++>` and avoid any alternative import paths. Memory management is handled internally, but you should minimize unnecessary object duplication and reuse `Presentation` instances where possible to reduce heap allocations and improve performance.

- Reuse `Presentation` objects across multiple slide operations instead of instantiating new ones for each task.
- Call `dispose()` explicitly on `Presentation` objects when finished to release unmanaged resources promptly.
- Avoid deep nesting of slide cloning or shape manipulation in tight loops without periodic cleanup.
- Prefer batch operations like `clone_slide()` over repeated add-and-fill cycles for better throughput.

## See Also

- [Explore visual effects support](/blog.aspose.org/slides/cpp/introducing-slides-foss-cpp/)
- [Discover key slide features](/blog.aspose.org/slides/cpp/slides-key-features/)
- [Learn slide manipulation basics](/docs.aspose.org/slides/cpp/developer-guide/slide-manipulation/)
- [Convert files easily](/kb.aspose.org/slides/cpp/how-to-convert-presentations-cpp/)
- [Fix common errors](/kb.aspose.org/slides/cpp/how-to-fix-presentations-errors-cpp/)
