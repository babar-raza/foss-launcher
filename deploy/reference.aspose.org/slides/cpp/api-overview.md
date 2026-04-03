---
canonical: https://reference.aspose.org/slides/cpp/api-overview/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: It enables loading, creating, and modifying.pptx files, including `slide`
  content, `shapes`, `text` formatting, and document properties. The library is...
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
page_role: api_reference
platform: cpp
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FOSS for C++ API Reference | Guide
slug: api-overview
title: Aspose.Slides FOSS for C++ API Reference
type: api_reference
url: /reference.aspose.org/slides/cpp/api-overview/
weight: 6
---

## Overview

Aspose.Slides FOSS for C++ provides `a` free C++ API for working with PowerPoint presentations. It enables loading, creating, and modifying.pptx files, including `slide` content, `shapes`, `text` formatting, and document properties. The library is designed for production use with full round-trip fidelity and supports core `presentation` features without external dependencies.

```cpp
using namespace Aspose::Slides::Foss;

Presentation pres;
pres.document_properties().set_title("Q1 Results");
pres.document_properties().set_author("Finance Team");
pres.document_properties().set_subject("Quarterly Financial Report");
pres.save("deck.pptx", SaveFormat::PPTX);
```

| Class | Description | Key Methods |
|-------|-------------|-------------|
| `BulletFormat` | Represents paragraph `bullet` formatting properties. | `BulletFormat()`, `BulletType()`, `set_type()`, `set_character()` |
| `Comment` | Represents `a` comment on `a` `slide`. | `Comment()`, `text()`, `set_text()`, `created_time()`, `set_created_time()` |
| `DocumentProperties` | Represents properties of `a` `presentation`. | `DocumentProperties()`, `title()`, `set_title()`, `subject()`, `set_subject()` |

## Public API

### Working with Comments in Aspose.Slides for C++

Aspose.Slides for C++ provides comprehensive capabilities for working with `comments` within presentations. Comments allow users to add `notes` and annotations directly to `slides`, enhancing collaboration and providing context. This section explores how to create, modify, and manage `comments` using the Aspose.Slides API.

```cpp
// Construct a comment with specified properties
Comment comment = new Comment(presentation, x, y, width, height, text);

```

The `Comment` class represents `a` comment on `a` `slide`. You can create `a` new comment using the `Comment()` constructor, providing the `presentation` object and the comment's `position` and dimensions. The `set_text()` method allows you to set the comment's content, and `set_created_time()` allows you to specify when the comment was created.

```cpp
// Set the comment text
comment.setText("This is a comment.");

// Set the comment creation time
comment.setCreatedTime(DateTime.now());
```

### Document Properties

The `DocumentProperties` class provides access to metadata associated with `a` `presentation`, such as the `author` and `subject`. You can modify these properties using the `set_author()` and `set_subject()` methods.

```cpp
// Set the author of the presentation
document.getPresentation().getDocumentProperties().setAuthor("John Doe");

// Set the subject of the presentation
document.getPresentation().getDocumentProperties().setSubject("Project Report");
```

### `Camera` Properties for 3D Scene Rendering

The `Camera` class manages properties related to 3D scene rendering within `a` `presentation`. The `has_parent()` method checks if the `camera` has been initialized with `a` parent `XML` element. This is useful for verifying the `camera`'s configuration.

### Formatting Properties

The `BulletFormat` class represents formatting properties for paragraph bullets. `AdjustValue` and `AdjustValueCollection` are used to adjust shape properties, influencing the visual appearance of elements within the `presentation`.

## Common Patterns

This section outlines common usage patterns for core classes in Aspose.Slides FOSS for C++. Developers frequently interact with `Comment`, `Camera`, and `AdjustValue` to annotate `slides`, configure 3D scene properties, and adjust shape geometry respectively.

| Method | Signature | Description |
|--------|-----------|-------------|
| `Comment()` | `Comment(text: std::string, slide: Slide *, author: CommentAuthor *, position: Drawing::PointF, created_time: std::chrono::system_clock::time_point)` | Constructs `a` comment with the given properties. |
| `text()` | `[[nodiscard]] const std::string &` | Gets the plain `text` of the comment. |
| `set_text()` | `void set_text(value: std::string)` | Sets the plain `text` of `a` `slide` comment. |
| `created_time()` | `[[nodiscard]] std::chrono::system_clock::time_point` | Gets the time of comment creation. |
| `set_created_time()` | `void set_created_time(value: std::chrono::system_clock::time_point)` | Sets the time of comment creation. |
| `slide()` | `[[nodiscard]] Slide *` | Gets the `slide` that `contains` the comment. |

| Method | Signature | Description |
|--------|-----------|-------------|
| `Camera()` | `Camera()` | Represents `camera` properties for 3D scene rendering. |
| `init_internal()` | `void init_internal(scene3d_element: pugi::xml_node, save_callback: std::function<void()>)` | Initializes the `camera` with `a` parent `XML` node and `save` callback. |
| `get_camera()` | `[[nodiscard]] pugi::xml_node` | Gets the underlying `XML` node for the `camera`. |
| `ensure_camera()` | `pugi::xml_node` | Gets or creates the element with default `preset` "orthographicFront". |
| `save()` | `void save()` | Persists `camera` changes to the `presentation`. |

| Method | Signature | Description |
|--------|-----------|-------------|
| `AdjustValue()` | `AdjustValue()` | Represents `a` value that affects the shape's form. |
| `init_internal()` | `void init_internal(parent_element: pugi::xml_node, save_callback: std::function<void()>)` | Initializes the adjust value with `a` parent `XML` node and `save` callback. |
| `save()` | `void save()` | Persists changes to the adjust value. |

## See Also

- [Getting Started with Aspose.Slides FOSS for C++](/slides/cpp/getting-started/)
- [Comment](/slides/cpp/manage-comments/)
- [Installation](/slides/cpp/developer-guide/product-installation/)
- [Aspose.Slides FOSS for C++ FAQ](/slides/cpp/frequently-asked-questions/)
- [Troubleshooting](/slides/cpp/troubleshooting-guide/)
