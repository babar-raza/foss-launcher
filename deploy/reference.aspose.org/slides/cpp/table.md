---
canonical: https://reference.aspose.org/slides/cpp/table-operations/
canonical_import: Aspose::Slides::Foss
code_import: Aspose::Slides::Foss
date: '2026-04-01T14:10:08Z'
dateModified: '2026-04-01T14:41:49Z'
datePublished: '2026-04-01T14:10:08Z'
description: It serves as the foundational `type` for all `color` operations in Aspose.Slides
  FOSS for C++.
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
seoTitle: 'Color: Represents an ARGB color, equivalent to System | Guide'
slug: table-operations
title: 'Color: Represents an ARGB color, equivalent to System'
type: reference_object_page
url: /reference.aspose.org/slides/cpp/table-operations/
weight: 22
---

## Overview

The `Color` class represents an ARGB `color` value and provides static factory methods to construct colors in various formats. It serves as the foundational `type` for all `color` operations in Aspose.Slides FOSS for C++.

```cpp
using namespace Aspose::Slides::Foss;

int main() {
 auto color1 = Color::from_argb(255, 0, 70, 127);
 auto color2 = Color::from_argb(128, 255, 0, 0);
 return 0;
}
```

## Constructor

The `Color` class represents an ARGB `color` value and provides constructors to instantiate colors from various component representations. It supports construction from alpha, red, green, and blue byte values, as well as from predefined `color` constants.

| Constructor | Parameters | Description |
|-------------|------------|-------------|
| `Color()` | — | Constructs `a` default `Color` instance (transparent black). |
| `Color(uint8_t a, uint8_t r, uint8_t g, uint8_t b)` | `a`: Alpha component (0–255), `r`: Red component (0–255), `g`: Green component (0–255), `b`: Blue component (0–255) | Constructs `a` `Color` from individual ARGB byte components. |
| `Color(uint32_t argb)` | argb: 32-bit ARGB value | Constructs `a` `Color` from `a` packed 32-bit ARGB integer. |
| `Color(ColorType type, float c1, float c2, float c3, float c4)` | `type`: `ColorType` enum value, c1–c4: `Color` components (interpretation depends on `type`) | Constructs `a` `Color` using `a` specified `color` mode and component values. |
| `Color(Aspose.Slides FOSS for C++::Color)` | other: Another `Color` instance | Copy constructor. |

## Properties

The `Color` class provides access to its underlying ARGB components through read-only properties. These properties expose the individual alpha, red, green, and blue channel values as 8-bit integers.

| Name | Type | Description |
|------|------|-------------|
| `a`() | [[nodiscard]] uint8_t | Returns the alpha component of the `color`. |
| `r`() | [[nodiscard]] uint8_t | Returns the red component of the `color`. |
| `g`() | [[nodiscard]] uint8_t | Returns the green component of the `color`. |
| `b`() | [[nodiscard]] uint8_t | Returns the blue component of the `color`. |
| `color_type`() | [[nodiscard]] `ColorType` | Returns the `color` mode of the `color`. |
| value() | [[nodiscard]] uint32_t | Returns the 32-bit ARGB value of the `color`. |

```cpp
using namespace Aspose::Slides::Foss;

Color red{255, 0, 0, 255};
uint8_t a = red.a();
uint8_t r = red.r();
uint8_t g = red.g();
uint8_t b = red.b();
ColorType type = red.color_type();
uint32_t val = red.value();
```

## Methods

The `Color` class provides methods to inspect and compare ARGB `color` values. Methods include equality checks, component access, and conversion helpers.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_A() const` | int32_t | Returns the alpha component (0–255). |
| `get_R() const` | int32_t | Returns the red component (0–255). |
| `get_G() const` | int32_t | Returns the green component (0–255). |
| `get_B() const` | int32_t | Returns the blue component (0–255). |
| `get_value() const` | uint32_t | Returns the 32-bit ARGB value. |
| `Equals(const Color&) const` | bool | Returns true if the `color` matches another ARGB value. |
| `Equals(const System::SharedPtr<Object>&) const` | bool | Returns true if the object is `a` `Color` with identical ARGB value. |
| `ToArgb() const` | int32_t | Returns the signed 32-bit ARGB value. |
| `ToKnownColor() const` | `ColorType` | Returns the `ColorType` enum representing the `color` mode. |
| `ToString() const` | System::String | Returns `a` string representation of the ARGB value in hex format. |

```cpp
using namespace Aspose::Slides::Foss;

Color red = Color::get_Red();
int32_t r = red.get_R();
int32_t a = red.get_A();
bool isRed = red.Equals(Color::get_Red());
System::String hex = red.ToString();
```

## Example

The `Color` class provides static factory methods to construct ARGB `color` values. The following example demonstrates creating `a` solid fill `color` using `Color::from_argb()` and applying it to `a` `text` portion.

```cpp
using namespace Aspose::Slides::Foss;

Presentation pres;
auto& shape = pres.slides()[0].shapes().add_auto_shape(ShapeType::RECTANGLE, 50, 50, 300, 100);
auto& tf = shape.add_text_frame("Sample text");
auto& portion = tf.paragraphs()[0].portions()[0];
portion.portion_format().fill_format().solid_fill_color().set_color(Color::from_argb(255, 128, 64, 192));
pres.save("color-fill.pptx", SaveFormat::PPTX);
```

## See Also

- [Introducing Slides FOSS for C++](/slides/cpp/slides-introduction/)
- [Key features of Slides FOSS](/slides/cpp/slides-key-features/)
- [Create presentations with Slides FOSS](/slides/cpp/developer-guide/presentation-creation/)
- [Work with slides using Slides FOSS](/slides/cpp/developer-guide/slide-manipulation/)
- [Convert file formats with Slides FOSS](/slides/cpp/convert-pptx-to-fodp/)
