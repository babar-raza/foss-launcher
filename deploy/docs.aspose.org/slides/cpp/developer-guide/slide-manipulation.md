---
canonical: https://docs.aspose.org/slides/cpp/developer-guide/slide-manipulation/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: The workflow uses only the `Aspose::Slides::Foss` namespace and leverages
  core classes like `Presentation`, `Slide`, and `SlideCollection` to manipulate...
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
seoTitle: Work with Slides with Aspose.Slides FOSS for C++ | Guide
slug: slide-manipulation
title: Work with Slides with Aspose.Slides FOSS for C++
type: workflow_page
url: /docs.aspose.org/slides/cpp/developer-guide/slide-manipulation/
weight: 19
---

## Overview

This guide walks you through working with `slides` in Aspose.Slides FOSS for C++, covering how to load existing presentations, add new `slides`, and `save` the modified document. The workflow uses only the `Aspose::Slides::Foss` namespace and leverages core classes like `Presentation`, `Slide`, and `SlideCollection` to manipulate `slide` content programmatically.

```cpp
using namespace Aspose::Slides::Foss;

// Load an existing presentation
auto presentation = System::MakeObject<Presentation>(u"input.pptx");

// Access the slide collection
auto slides = presentation->get_Slides();

// Add a new blank slide at the end
auto newSlide = slides->AddEmptySlide(slides->get_Count());

// Save the updated presentation
presentation->Save(u"output.pptx", SaveFormat::Pptx);
```

- Use this approach when updating conference slide decks for events like cppcon slides 2025 or meeting cpp slides.
- Apply it to automate slide generation for reports or training materials where slide count varies dynamically.
- Leverage it when preparing presentation templates that require consistent slide insertion logic.

## Working with Data

This section covers core `data` manipulation operations for `presentation` elements in Aspose.Slides FOSS for C++. You will learn how to read, write, and modify `text` formatting, `bullet` styles, and document properties using the `BulletFormat`, `DocumentProperties`, and `Comment` classes.

All operations use the canonical namespace `Aspose::Slides::Foss`. Begin by including the necessary headers and initializing your `presentation` object. The following examples demonstrate how to work with paragraph bullets, document metadata, and `slide` `comments` using only the documented API surface.

### Reading and Modifying Bullet Formatting

Use `BulletFormat` to inspect or update `bullet` characteristics such as `type`, character, and `position`. Access the `BulletFormat` object through `a` paragraph’s formatting interface, then call `BulletType()` to read the current `bullet` `style` or `set_type()` to change it.

```cpp
using namespace Aspose::Slides::Foss;

// Assume 'paragraph' is a valid Paragraph* obtained from a slide
auto bulletFormat = paragraph->get_BulletFormat();

// Read current bullet type
auto type = bulletFormat->BulletType();

// Change bullet type to filled circle
bulletFormat->set_type(BulletType::FilledCircle);

// Set custom bullet character
bulletFormat->set_character(u'•');
```

- Use `BulletType()` to verify bullet style before applying conditional formatting logic.
- Call `set_type()` with a valid `BulletType` enum to standardize bullet appearance across slides.
- Set a custom character with `set_character()` when the built-in bullet types do not meet design requirements.

### Updating Document Properties

Access `presentation`-level metadata via `DocumentProperties`. You can read or modify core properties like `title()` and `subject()`, and extended properties such as `company()` and `name_of_application()`.

```cpp
using namespace Aspose::Slides::Foss;

// Assume 'presentation' is a valid Presentation* instance
auto docProps = presentation->get_DocumentProperties();

// Read current title
auto title = docProps->title();

// Update title and subject
 docProps->set_title(u"Q3 Financial Review");
docProps->set_subject(u"Revenue and expense breakdown");

// Set company metadata
docProps->set_company(u"Contoso Ltd.");
```

- Update `title()` and `subject()` to ensure consistent metadata for archival or searchability.
- Set `company()` to embed organizational context for internal distribution.
- Use `set_name_of_application()` to record the tool used for generation or modification.

### Adding and Editing `Slide` Comments

Attach `comments` to `slides` using the `Comment` class. Construct `a` comment with `author`, `position`, and timestamp, then add it to `a` `slide`’s comment collection. Modify existing `comments` by updating their `text()` or `created_time()`.

```cpp
using namespace Aspose::Slides::Foss;

// Assume 'slide' is a valid Slide* and 'author' is a CommentAuthor*
auto comment = System::MakeObject<Comment>(
 u"Please verify data alignment.",
 slide.GetPtr(),
 author,
 Drawing::PointF(100.0f, 200.0f),
 std::chrono::system_clock::now()
);

// Add comment to slide
slide->get_Comments()->Add(comment);

// Update comment text
comment->set_text(u"Please verify data alignment and formatting.");
```

- Use `Comment` constructor to embed time-stamped feedback directly on slides.
- Call `set_text()` to revise editorial notes without creating duplicate comments.
- Read `created_time()` to sort or filter comments chronologically.

These operations reflect the minimal but complete set of `data` manipulation capabilities available in Aspose.Slides FOSS for C++. For advanced formatting or 3D effects, refer to the `FillFormat`, `GradientFormat`, and `EffectFormat` classes in the API surface.

## Code Examples

This guide walks you through creating and manipulating `slides` in Aspose.Slides FOSS for C++. You start with `a` blank `presentation`, add `a` `slide`, `insert` `a` shape with formatted `text`, and `save` the result as `a`.pptx file.

```cpp
using namespace Aspose::Slides::Foss;

// Create a new presentation
Presentation presentation;

// Add a blank slide
Slide slide = presentation.get_Slides()->AddEmptySlide(presentation.get_Slides()->get_Count());

// Add a rectangle auto shape
AutoShape shape = slide->get_Shapes()->AddAutoShape(ShapeType::Rectangle, 50.0f, 50.0f, 300.0f, 100.0f);

// Set solid fill color
shape->get_FillFormat()->set_FillType(FillType::Solid);
shape->get_FillFormat()->get_SolidFillColor()->set_Color(Color::Get_LightBlue());

// Add text and format the first portion
shape->get_TextFrame()->get_Paragraphs()->Add()->get_Portions()->Add()->set_Text(u"Hello, Aspose.Slides FOSS!");

// Save the presentation
presentation->Save(u"output.pptx", SaveFormat::Pptx);
```

- Use this approach when generating presentation templates for internal reports.
- Apply solid fills to highlight key data points in dashboards.
- Add text to shapes to create labeled diagrams without external dependencies.

Next, add `a` comment to the `slide` and set document properties. Comments attach metadata to specific `slide` positions, while document properties provide `presentation`-level context.

```cpp
using namespace Aspose::Slides::Foss;

// Load an existing presentation
Presentation presentation(u"output.pptx");

// Get the first slide
Slide slide = presentation.get_Slides()->idx_get(0);

// Create a comment author
CommentAuthor author = presentation->get_CommentAuthors()->AddAuthor(u"Author Name", u"AN");

// Add a comment at position (200, 150)
Comment comment = slide->get_Comments()->AddComment(u"Review this section before finalizing.", slide, author, Drawing::PointF(200.0f, 150.0f), std::chrono::system_clock::now());

// Set document title
presentation->get_DocumentProperties()->set_title(u"FOSS Presentation Demo");

// Save with updated metadata
presentation->Save(u"output_with_comments.pptx", SaveFormat::Pptx);
```

- Attach comments to guide reviewers during collaborative editing workflows.
- Set document title and subject to improve file discoverability in enterprise repositories.
- Use `CommentAuthor` objects to maintain consistent attribution across multiple slides.

## Notes and Best Practices

When working with Aspose.Slides FOSS for C++, ensure you use the canonical namespace `Aspose::Slides::Foss` in all code. Memory management is handled automatically via smart pointers, so avoid manual new/delete calls. Always `dispose` of `Presentation` objects explicitly using delete when they are no longer needed, especially in long-running processes or batch operations.

- Use `std::shared_ptr<Presentation>` to manage presentation lifetimes safely and avoid memory leaks.
- Avoid holding multiple `Presentation` instances open simultaneously unless necessary — close unused ones promptly.
- Prefer in-memory operations (e.g., cloning slides via CloneSlide()) over repeated file I/O for performance.
- Validate input files before processing using `FileFormatUtil.DetectFileFormat()` to prevent runtime exceptions.

## See Also

- [Introducing the open-source library](/slides/cpp/slides-introduction/)
- [Key capabilities and features overview](/slides/cpp/slides-key-features/)
- [Step-by-step presentation creation guide](/slides/cpp/developer-guide/presentation-creation/)
- [Supported file format conversions](/slides/cpp/convert-pptx-to-fodp/)
- [Resolving frequent runtime issues](/slides/cpp/fix-presentations-errors/)
