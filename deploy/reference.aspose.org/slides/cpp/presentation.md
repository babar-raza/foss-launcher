---
canonical: https://reference.aspose.org/slides/cpp/presentation-overview/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: It serves as the top-level container for `slides`, master `slides`, and
  `presentation`-wide properties.
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
page_role: reference_object_page
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FOSS Presentation
slug: presentation-overview
title: Presentation
type: reference_object_page
url: /reference.aspose.org/slides/cpp/presentation-overview/
weight: 21
---

## Overview

The `Presentation` class represents `a` PowerPoint `presentation` and provides methods to load, create, and `save` `.pptx` files. It serves as the top-level container for `slides`, master `slides`, and `presentation`-wide properties.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `save(std::string)` | void | Saves the `presentation` to `a` file in `PPTX` format. |
| get_Slides() | `SlideCollection` & | Returns the collection of `slides` in the `presentation`. |
| get_Masters() | `MasterSlideCollection` & | Returns the collection of master `slides`. |
| get_Comments() | `CommentCollection` & | Returns the collection of `comments`. |
| get_DocumentProperties() | `DocumentProperties` & | Returns the document properties (`title`, `subject`, etc.). |

Slides are accessed via get_Slides(), which returns `a` `SlideCollection`. Each `slide` inherits from `BaseSlide`, which implements `IBaseSlide` and provides common `data` for all `slide` types (). Tables are represented by the `Table` class, and individual cells within tables are represented by the `Cell` class ().

## Constructor

The `Presentation` class in Aspose.Slides FOSS for C++ represents `a` PowerPoint `presentation` and provides methods to load, create, and `save` presentations. It supports full round-trip fidelity for `.pptx` files and exposes `slide` collections via get_Slides().

| Constructor | Parameters | Description |
|-------------|------------|-------------|
| `Presentation()` | none | Initializes `a` new `Presentation` object with `a` default blank `presentation`. |
| `Presentation(System::String)` | fileName (System::String) | Initializes `a` new `Presentation` object by loading an existing `.pptx` file. |
| `Presentation(System::IO::Stream)` | stream (System::IO::Stream) | Initializes `a` new `Presentation` object by loading from `a` stream. |

```cpp
using namespace Aspose::Slides::Foss;

// Create a new presentation
auto presentation = System::MakeObject<Presentation>();

// Save to file
presentation->Save(u"output.pptx", SaveFormat::Pptx);
```

## Properties

The `Presentation` class exposes properties that provide access to core `presentation` metadata and structure. These properties are read-write where applicable and enable programmatic inspection and modification of `presentation`-level attributes.

| Name | Type | Description |
|------|------|-------------|
| `slides()` | `SlideCollection&` | Returns the collection of `slides` in the `presentation`. |
| `document_properties()` | `DocumentProperties&` | Returns the document properties object for reading and writing metadata such as `title` and `subject`. |
| `app_version()` | `const std::string&` | Returns the version of the application that created the `presentation`. |
| `name_of_application()` | `const std::string&` | Returns the `name` of the application that created the `presentation`. |
| `company()` | `const std::string&` | Returns the `company` `name` associated with the `presentation`. |
| `set_company(value: std::string)` | void | Sets the `company` `name` associated with the `presentation`. |
| `set_name_of_application(value: std::string)` | void | Sets the `name` of the application that created the `presentation`. |
| `title()` | `const std::string&` | Returns the `title` of the `presentation`. |
| `set_title(value: std::string)` | void | Sets the `title` of the `presentation`. |
| `subject()` | `const std::string&` | Returns the `subject` of the `presentation`. |
| `set_subject(value: std::string)` | void | Sets the `subject` of the `presentation`. |

```cpp
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/export/save_format.h>

using namespace Aspose::Slides::Foss;

int main() {
 Presentation pres("input.pptx");
 pres.document_properties().set_title("New Title");
 pres.document_properties().set_company("Example Corp");
 pres.save("output.pptx", SaveFormat::PPTX);
}
```

## Methods

| Item | Description |
| --- | --- |
| BulletFormat: Represents paragraph bullet formatting properties | |
| Color: Represents an ARGB color, equivalent to System | |

```cpp
#include <chrono>
#include <filesystem>
#include <string>
#include <Aspose/Slides/Foss/auto_shape.h>
#include <Aspose/Slides/Foss/drawing/color.h>
#include <Aspose/Slides/Foss/effect_format.h>
#include <Aspose/Slides/Foss/export/save_format.h>
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/rectangle_alignment.h>
#include <Aspose/Slides/Foss/shape_type.h>
#include <Aspose/Slides/Foss/slide.h>
#include <Aspose/Slides/Foss/slide_collection.h>

Presentation pres;
 auto& slide = clear_slide(pres);
 auto& shape = slide.shapes().add_auto_shape(ShapeType::RECTANGLE, 100, 100, 200, 100);
 auto& ef = shape.effect_format();
 ef.enable_outer_shadow_effect();
 auto* shadow = ef.outer_shadow_effect();
 shadow->set_blur_radius(10);
 shadow->set_direction(315);
 shadow->set_distance(8);
 shadow->shadow_color().set_color(Color::from_argb(128, 0, 0, 0));
 auto pres2 = save_and_reopen(pres);
 auto& ef2 = pres2.slides()[0].shapes()[0].effect_format();
 auto* s2 = ef2.outer_shadow_effect();
```

```cpp
#include <chrono>
#include <filesystem>
#include <string>
#include <vector>
#include <Aspose/Slides/Foss/cell.h>
#include <Aspose/Slides/Foss/cell_format.h>
#include <Aspose/Slides/Foss/column.h>
#include <Aspose/Slides/Foss/column_collection.h>
#include <Aspose/Slides/Foss/drawing/color.h>
#include <Aspose/Slides/Foss/export/save_format.h>
#include <Aspose/Slides/Foss/fill_format.h>
#include <Aspose/Slides/Foss/fill_type.h>
#include <Aspose/Slides/Foss/line_format.h>
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/row.h>
#include <Aspose/Slides/Foss/row_collection.h>
#include <Aspose/Slides/Foss/shape.h>
#include <Aspose/Slides/Foss/shape_collection.h>
#include <Aspose/Slides/Foss/slide.h>
#include <Aspose/Slides/Foss/slide_collection.h>
#include <Aspose/Slides/Foss/table.h>

Presentation pres;
 auto& slide = blank_slide(pres);
 std::vector<double> col_widths = {150};
 std::vector<double> row_heights = {50};
 auto& table = slide.shapes().add_table(50, 50, col_widths, row_heights);
 auto& cell = table.rows()[0][0];
 cell.text_frame()->set_text("Bordered");
 auto& fmt = cell.cell_format();
 fmt.border_top().fill_format().set_fill_type(FillType::SOLID);
 fmt.border_top().fill_format().solid_fill_color().set_color(Drawing::Color::red);
 fmt.border_top().set_width(3);
 fmt.border_bottom().fill_format().set_fill_type(FillType::SOLID);
 fmt.border_bottom().fill_format().solid_fill_color().set_color(Drawing::Color::red);
 fmt.border_bottom().set_width(3);
 fmt.border_left().fill_format().set_fill_type(FillType::SOLID);
 fmt.border_left().fill_format().solid_fill_color().set_color(Drawing::Color::red);
 fmt.border_left().set_width(3);
 fmt.border_right().fill_format().set_fill_type(FillType::SOLID);
 fmt.border_right().fill_format().solid_fill_color().set_color(Drawing::Color::red);
 fmt.border_right().set_width(3);
 auto pres2 = save_and_reopen(pres);
 auto* t2 = find_table(pres2.slides()[0]);
 auto& fmt2 = t2->rows()[0][0].cell_format();
```

```cpp
#include <chrono>
#include <filesystem>
#include <string>
#include <vector>
#include <Aspose/Slides/Foss/cell.h>
#include <Aspose/Slides/Foss/cell_format.h>
#include <Aspose/Slides/Foss/column.h>
#include <Aspose/Slides/Foss/column_collection.h>
#include <Aspose/Slides/Foss/drawing/color.h>
#include <Aspose/Slides/Foss/export/save_format.h>
#include <Aspose/Slides/Foss/fill_format.h>
#include <Aspose/Slides/Foss/fill_type.h>
#include <Aspose/Slides/Foss/line_format.h>
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/row.h>
#include <Aspose/Slides/Foss/row_collection.h>
#include <Aspose/Slides/Foss/shape.h>
#include <Aspose/Slides/Foss/shape_collection.h>
#include <Aspose/Slides/Foss/slide.h>
#include <Aspose/Slides/Foss/slide_collection.h>
#include <Aspose/Slides/Foss/table.h>

Presentation pres;
 auto& slide = blank_slide(pres);
 std::vector<double> col_widths = {200};
 std::vector<double> row_heights = {60};
 auto& table = slide.shapes().add_table(50, 50, col_widths, row_heights);
 auto& cell = table.rows()[0][0];
 cell.cell_format().fill_format().set_fill_type(FillType::SOLID);
 cell.cell_format().fill_format().solid_fill_color().set_color(Drawing::Color::light_blue);
 cell.text_frame()->set_text("Blue");
 auto pres2 = save_and_reopen(pres);
 auto* t2 = find_table(pres2.slides()[0]);
 auto& cf2 = t2->rows()[0][0].cell_format();
```

```cpp
#include <chrono>
#include <filesystem>
#include <string>
#include <Aspose/Slides/Foss/auto_shape.h>
#include <Aspose/Slides/Foss/drawing/color.h>
#include <Aspose/Slides/Foss/export/save_format.h>
#include <Aspose/Slides/Foss/fill_format.h>
#include <Aspose/Slides/Foss/fill_type.h>
#include <Aspose/Slides/Foss/font_data.h>
#include <Aspose/Slides/Foss/nullable_bool.h>
#include <Aspose/Slides/Foss/paragraph.h>
#include <Aspose/Slides/Foss/paragraph_collection.h>
#include <Aspose/Slides/Foss/paragraph_format.h>
#include <Aspose/Slides/Foss/portion.h>
#include <Aspose/Slides/Foss/portion_collection.h>
#include <Aspose/Slides/Foss/portion_format.h>
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/shape.h>
#include <Aspose/Slides/Foss/shape_collection.h>
#include <Aspose/Slides/Foss/shape_type.h>
#include <Aspose/Slides/Foss/slide.h>
#include <Aspose/Slides/Foss/slide_collection.h>
#include <Aspose/Slides/Foss/text_alignment.h>
#include <Aspose/Slides/Foss/text_frame.h>
#include <Aspose/Slides/Foss/text_strikethrough_type.h>
#include <Aspose/Slides/Foss/text_underline_type.h>

Presentation pres;
 pres.slides()[0].shapes().clear();
 auto& shape = pres.slides()[0].shapes().add_auto_shape(
 ShapeType::RECTANGLE, 50, 50, 400, 200);
 shape.text_frame()->set_text("Centered");
 shape.text_frame()->paragraphs()[0].paragraph_format().set_alignment(
 TextAlignment::CENTER);
 auto pres2 = save_and_reopen(pres);
 auto& reloaded = dynamic_cast<AutoShape&>(pres2.slides()[0].shapes()[0]);
 auto& pf = reloaded.text_frame()->paragraphs()[0].paragraph_format();
```

```cpp
#include <chrono>
#include <filesystem>
#include <string>
#include <Aspose/Slides/Foss/auto_shape.h>
#include <Aspose/Slides/Foss/drawing/color.h>
#include <Aspose/Slides/Foss/export/save_format.h>
#include <Aspose/Slides/Foss/fill_format.h>
#include <Aspose/Slides/Foss/fill_type.h>
#include <Aspose/Slides/Foss/font_data.h>
#include <Aspose/Slides/Foss/nullable_bool.h>
#include <Aspose/Slides/Foss/paragraph.h>
#include <Aspose/Slides/Foss/paragraph_collection.h>
#include <Aspose/Slides/Foss/paragraph_format.h>
#include <Aspose/Slides/Foss/portion.h>
#include <Aspose/Slides/Foss/portion_collection.h>
#include <Aspose/Slides/Foss/portion_format.h>
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/shape.h>
#include <Aspose/Slides/Foss/shape_collection.h>
#include <Aspose/Slides/Foss/shape_type.h>
#include <Aspose/Slides/Foss/slide.h>
#include <Aspose/Slides/Foss/slide_collection.h>
#include <Aspose/Slides/Foss/text_alignment.h>
#include <Aspose/Slides/Foss/text_frame.h>
#include <Aspose/Slides/Foss/text_strikethrough_type.h>
#include <Aspose/Slides/Foss/text_underline_type.h>

Presentation pres;
 auto [shape, fmt] = shaped(pres);
 fmt->fill_format().set_fill_type(FillType::SOLID);
 fmt->fill_format().solid_fill_color().set_color(Color::red);
 auto pres2 = save_and_reopen(pres);
 auto& fmt2 = reloaded_portion_format(pres2);
 auto c = fmt2.fill_format().solid_fill_color().color();
```

```cpp
#include <chrono>
#include <filesystem>
#include <string>
#include <Aspose/Slides/Foss/auto_shape.h>
#include <Aspose/Slides/Foss/export/save_format.h>
#include <Aspose/Slides/Foss/paragraph.h>
#include <Aspose/Slides/Foss/paragraph_collection.h>
#include <Aspose/Slides/Foss/portion.h>
#include <Aspose/Slides/Foss/portion_collection.h>
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/shape.h>
#include <Aspose/Slides/Foss/shape_collection.h>
#include <Aspose/Slides/Foss/shape_type.h>
#include <Aspose/Slides/Foss/slide.h>
#include <Aspose/Slides/Foss/slide_collection.h>
#include <Aspose/Slides/Foss/text_frame.h>

Presentation pres;
 auto& shape = pres.slides()[0].shapes().add_auto_shape(
 ShapeType::RECTANGLE, 50, 50, 400, 100);
 shape.text_frame()->set_text("Hello ");
 Portion new_portion("World!");
 shape.text_frame()->paragraphs()[0].portions().add(std::move(new_portion));
```

## Example

The `Presentation` class enables loading, creating, and saving PowerPoint presentations. It provides access to `slides`, metadata, and formatting structures including `bullet` formatting via `BulletFormat` and `color` definitions via `ColorFormat`.

```cpp
using namespace Aspose::Slides::Foss;

auto pres = System::MakeObject<Presentation>();
pres->get_SlideComments()->AddComment(System::MakeObject<Comment>(u"Review note", pres->get_Slides()->idx_get(0), nullptr, Drawing::PointF(100.0f, 100.0f), std::chrono::system_clock::now()));
pres->Save(u"output.pptx", SaveFormat::Pptx);
```

## See Also

- [Reference for comment objects](/slides/cpp/manage-comments/)
- [Introduction to Slides FOSS C++](/slides/cpp/slides-introduction/)
- [Key features of Slides FOSS](/slides/cpp/slides-key-features/)
- [Create presentations step by step](/slides/cpp/developer-guide/presentation-creation/)
- [Work with slides programmatically](/slides/cpp/developer-guide/slide-manipulation/)
