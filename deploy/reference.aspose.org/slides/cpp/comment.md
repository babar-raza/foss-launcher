---
canonical: https://reference.aspose.org/slides/cpp/add-comment/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-03-29T16:35:25Z'
dateModified: '2026-03-29T16:55:07Z'
datePublished: '2026-03-29T16:35:25Z'
description: It is used to programmatically add, read, or modify `slide` annotations
  in presentations processed by Aspose.Slides FOSS for C++.
display_name: Aspose.Slides FOSS for C++
family: slides
keywords:
- cppcon slides
- cpp slides
- cppnow slides
- cppcon slides 2025
- aspose slides cpp
- meeting cpp slides
lastmod: '2026-03-29T16:55:07Z'
page_role: reference_object_page
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: 'Aspose.Slides FOSS Comment: Represents a comment on a slide'
slug: add-comment
title: 'Comment: Represents a comment on a slide'
type: reference_object_page
url: /reference.aspose.org/slides/cpp/add-comment/
weight: 20
---

## Overview

The `Comment` class represents `a` comment attached to `a` `slide`, storing `text` content, creation timestamp, and authorship metadata. It is used to programmatically add, read, or modify `slide` annotations in presentations processed by Aspose.Slides FOSS for C++.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `Comment(text: std::string, slide: Slide *, author: CommentAuthor *, position: Drawing::PointF, created_time: std::chrono::system_clock::time_point)` | Constructor | Constructs `a` comment with the given properties. |
| `text() -> [[nodiscard]] const std::string &` | `const std::string &` | Returns the comment `text`. |
| `set_text(value: std::string) -> void` | void | Sets the comment `text`. |
| `created_time() -> [[nodiscard]] std::chrono::system_clock::time_point` | `std::chrono::system_clock::time_point` | Returns the comment creation time. |
| `set_created_time(value: std::chrono::system_clock::time_point) -> void` | void | Sets the comment creation time. |

The `AutoShape` class represents an `AutoShape` on `a` `slide`, supporting geometry, fill, and effect formatting. The `Camera` class defines `camera` properties for 3D scene rendering, including `preset` types and internal XML state management.

```cpp
using namespace Aspose::Slides::Foss;

// Example: Construct a Comment with sample data
std::chrono::system_clock::time_point now = std::chrono::system_clock::now();
Comment comment(u"Review this section", nullptr, nullptr, Drawing::PointF(100.0f, 100.0f), now);
std::string text = comment.text();
```

## Constructor

The `Comment` class represents `a` comment attached to `a` `slide`. It stores `text` content, creation timestamp, `author`, and `position`. The constructor initializes `a` new comment with specified properties.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | const std::string & | The comment `text` content |
| `slide` | `Slide` * | The `slide` to which the comment is attached |
| `author` | `CommentAuthor` * | The `author` of the comment |
| `position` | Drawing::`PointF` | The `position` of the comment marker on the `slide` |
| `created_time` | std::chrono::system_clock::time_point | The timestamp when the comment was created |

The constructor signature for `Comment` is shown below. All parameters are required; no default values are provided.

```cpp
using namespace Aspose::Slides::Foss;

// Example constructor usage (not executable without full context)
// Comment* comment = new Comment("Sample text", slide, author, position, created_time);
```

## Properties

The `Comment` class provides read-write access to comment metadata through its properties. Each property corresponds to `a` core attribute of `a` `slide` comment: `text` content, creation timestamp, and `author` association.

| Name | Type | Description |
|------|------|-------------|
| `text` | `const std::string &` | Returns or sets the comment `text` content. |
| `created_time` | `std::chrono::system_clock::time_point` | Returns or sets the timestamp when the comment was created. |
| `author` | `CommentAuthor *` | Returns the `author` associated with the comment. |
| `position` | `Drawing::PointF` | Returns the `position` of the comment marker on the `slide`. |
| shape | `AutoShape *` | Returns the auto shape used to render the comment marker. |

```cpp
using namespace Aspose::Slides::Foss;

int main() {
 Presentation pres("input.pptx");
 auto& slide = pres.slides()[0];
 auto& comments = slide.comments_manager()->comments();
 if (comments.get_Count() > 0) {
 auto comment = comments[0];
 auto text = comment->text();
 auto time = comment->created_time();
 }
 return 0;
}
```

## Methods

The `Comment` class provides methods to access and modify comment metadata, including `text` content and creation timestamp. All methods operate on the comment instance and reflect changes to the underlying `slide` document.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `Comment(text: std::string, slide: Slide *, author: CommentAuthor *, position: Drawing::PointF, created_time: std::chrono::system_clock::time_point)` | Constructor | Constructs `a` comment with the given properties. |
| `text() -> [[nodiscard]] const std::string &` | `const std::string &` | Returns the comment `text` content. |
| `set_text(value: std::string) -> void` | void | Sets the comment `text` content. |
| `created_time() -> [[nodiscard]] std::chrono::system_clock::time_point` | `std::chrono::system_clock::time_point` | Returns the comment creation timestamp. |
| `set_created_time(value: std::chrono::system_clock::time_point) -> void` | void | Sets the comment creation timestamp. |

## Example

The following example demonstrates creating `a` comment on `a` `slide` and setting its `text` content using the `Comment` class. It uses the canonical import `Aspose::Slides::Foss` and constructs `a` `Comment` with sample `data`, then attaches it to `a` `slide`.

```cpp
using namespace Aspose::Slides::Foss;

int main() {
 Presentation pres;
 auto& slide = pres.slides()[0];
 auto author = new CommentAuthor();
 auto comment = new Comment(
 "This is a sample comment.",
 &slide,
 author,
 Drawing::PointF(100.0f, 100.0f),
 std::chrono::system_clock::now()
 );
 comment->set_text("Updated comment text.");
 return 0;
}
```

## See Also

- [Presentation object overview](/slides/cpp/create-presentation/)
- [Introduction to Slides FOSS C++](/slides/cpp/slides-foss/)
- [Key features of Slides FOSS](/slides/cpp/slides-features/)
- [Create presentations programmatically](/slides/cpp/developer-guide/presentation-creation/)
- [Work with slides in C++](/slides/cpp/developer-guide/slide-manipulation/)
