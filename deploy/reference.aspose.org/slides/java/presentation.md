---
canonical: https://reference.aspose.org/slides/java/presentation/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: It enables creation, loading, and saving of `.pptx` files with full round-trip
  fidelity.
display_name: Aspose.Slides FOSS for Java
family: slides
keywords:
- slides javascript
- slides java
- slides javascript library
- slideshow javascript
- javascript slides pdf
- java slides pdf
- slideshow javascript library
- java slides ppt
lastmod: '2026-03-24T17:06:48Z'
page_role: reference_object_page
platform: java
reading_time: 1
robots: index, follow
seoTitle: The Presentation class provides access to slides via the
slug: presentation
title: The Presentation class provides access to slides via the getSlides() method
type: reference_object_page
url: /reference.aspose.org/slides/java/presentation/
weight: 21
---

## Overview

The `Presentation` class provides access to slides via the getSlides() method and serves as the entry point for working with slide decks in Aspose.Slides FOSS for Java. It enables creation, loading, and saving of `.pptx` files with full round-trip fidelity.

```java
import com.aspose.slides.*;

try (var pres = new Presentation()) {
    var slides = pres.getSlides();
    var slide = slides.addEmptySlide(slides.getLayoutSlides().get(0));
    pres.save("output.pptx", SaveFormat.PPTX);
}
```

| Class | Description | Source Claim |
|-------|-------------|--------------|
| `BaseSlide` | Represents common data for all slide types | CLM-slides-bc91e3 |
| `CellCollection` | Represents `a` collection of cells | CLM-slides-3f635e |

## Constructor

The `Presentation` class provides access to slides via the getSlides() method. It supports creating new presentations and loading existing `.pptx` files with full round-trip fidelity.

| Constructor | Parameters | Description |
|-------------|------------|-------------|
| `Presentation()` | — | Creates `a` new empty `Presentation` instance. |
| `Presentation(String fileName)` | fileName: `String` — Path to an existing `.pptx` file | Loads `a` `Presentation` from the specified file. |
| `Presentation(InputStream stream)` | stream: InputStream — Input stream containing `a` `.pptx` file | Loads `a` `Presentation` from the provided stream. |
| `Presentation(String fileName, LoadOptions loadOptions)` | fileName: `String`, loadOptions: LoadOptions | Loads `a` `Presentation` from `a` file using specified load options. |
| `Presentation(InputStream stream, LoadOptions loadOptions)` | stream: InputStream, loadOptions: LoadOptions | Loads `a` `Presentation` from `a` stream using specified load options. |

```java
import com.aspose.slides.*;

try (Presentation pres = new Presentation()) {
    IAutoShape shape = pres.getSlides().get(0).getShapes()
            .addAutoShape(ShapeType.RECTANGLE, 50, 50, 300, 150);
    shape.getFillFormat().setFillType(FillType.SOLID);
    pres.save("output.pptx", SaveFormat.PPTX);
}
```

## Properties

The `Presentation` class exposes slide collections and document metadata through its properties. This section lists key properties defined on `Presentation` and related objects, with full API surface coverage per claims.

| Name | Type | Description |
|------|------|-------------|
| getSlides() | `ISlideCollection` | Returns the collection of slides in the presentation. |
| getDocumentProperties() | `IDocumentProperties` | Returns the document properties (built-in and custom). |
| `getComments()` | `ICommentCollection` | Returns the collection of comments attached to slides. |
| getAuthors() | `ICommentAuthorCollection` | Returns the collection of comment authors. |
| getSlideSize() | ISlideSize | Returns the slide size and margins configuration. |
| getTheme() | ITheme | Returns the master theme applied to the presentation. |
| getSlideShowSettings() | ISlideShowSettings | Returns the slide show configuration. |
| getSlideMaster() | `IMasterSlide` | Returns the first slide master (if present). |
| getNotesMaster() | INotesMaster | Returns the notes master (if present). |
| getHandoutMaster() | IHandoutNotesMaster | Returns the handout master (if present). |

The `BulletFormat` class exposes paragraph bullet formatting properties. Its properties define bullet appearance and behavior.

| Name | Type | Description |
|------|------|-------------|
| getType() | `BulletType` | Returns or sets the bullet type (e.`g`., NONE, SYMBOL, NUMBERED, PICTURE). |
| `getChar()` | char | Returns or sets the character used for symbol bullets. |
| getNumberStyle() | NumberStyle | Returns or sets the number style for numbered bullets. |
| getStartNumber() | `int` | Returns or sets the starting number for numbered bullets. |
| getPicture() | `IPictureFrame` | Returns or sets the picture used for picture bullets. |
| getBulletColor() | `IColorFormat` | Returns the color format of the bullet. |
| getBulletFontSize() | `float` | Returns or sets the font size of the bullet. |

The `Color` class is an immutable value type representing an ARGB color. It is used throughout the API for fill, line, and text color definitions.

```java
import com.aspose.slides.*;

var color = new Color(0, 128, 255);
int a = color.getA();
int r = color.getR();
int g = color.getG();
int b = color.getB();
```

## Methods

Aspose.Slides FOSS for Java -- Method table: signature, return type, description.

| Item | Description |
| --- | --- |
| BulletType: Represents the type of the extended bullets |  |
| ColorFormat.createChildElement() is part of the public API for Aspose.Slides FOSS for Java. |  |

```java
import org.aspose.slides.foss.Presentation;
import org.aspose.slides.foss.export.SaveFormat;

// Open an existing presentation
try (Presentation prs = new Presentation("input.pptx")) {
    System.out.println("Slides: " + prs.getSlides().size());
    prs.save("output.pptx", SaveFormat.PPTX);
}

// Create a new presentation
try (Presentation prs = new Presentation()) {
    var slide = prs.getSlides().get(0);
    prs.save("new.pptx", SaveFormat.PPTX);
}
```

```java
import org.aspose.slides.foss.Presentation;
import org.aspose.slides.foss.ShapeType;
import org.aspose.slides.foss.IAutoShape;
import org.aspose.slides.foss.ISlide;
import org.aspose.slides.foss.export.SaveFormat;

try (Presentation prs = new Presentation()) {
    ISlide slide = prs.getSlides().get(0);
    IAutoShape shape = slide.getShapes().addAutoShape(ShapeType.RECTANGLE, 50, 50, 300, 100);
    shape.addTextFrame("Hello, world!");
    prs.save("shapes.pptx", SaveFormat.PPTX);
}
```

```java
import org.aspose.slides.foss.*;
import org.aspose.slides.foss.drawing.Color;
import org.aspose.slides.foss.export.SaveFormat;

try (Presentation prs = new Presentation()) {
    IAutoShape shape = prs.getSlides().get(0).getShapes()
            .addAutoShape(ShapeType.RECTANGLE, 50, 50, 400, 150);
    shape.addTextFrame("Formatted text");
    IPortionFormat fmt = shape.getTextFrame().getParagraphs().get(0)
            .getPortions().get(0).getPortionFormat();
    fmt.setFontHeight(24);
    fmt.setFontBold(NullableBool.TRUE);
    fmt.getFillFormat().setFillType(FillType.SOLID);
    fmt.getFillFormat().getSolidFillColor().setColor(Color.fromArgb(255, 0, 70, 127));
    prs.save("text.pptx", SaveFormat.PPTX);
}
```

## Example

The `Presentation` class provides access to slides via the getSlides() method, enabling iteration and manipulation of slide content. This example demonstrates creating `a` presentation, adding `a` rectangle shape with formatted text, and saving it as `a` PPTX file using the canonical import path.

```java
import com.aspose.slides.*;
import com.aspose.slides.drawing.Color;
import com.aspose.slides.export.SaveFormat;

try (Presentation prs = new Presentation()) {
    IAutoShape shape = prs.getSlides().get(0).getShapes()
            .addAutoShape(ShapeType.RECTANGLE, 50, 50, 400, 150);
    shape.addTextFrame("Formatted text");
    IPortionFormat fmt = shape.getTextFrame().getParagraphs().get(0)
            .getPortions().get(0).getPortionFormat();
    fmt.setFontHeight(24);
    fmt.setFontBold(NullableBool.TRUE);
    fmt.getFillFormat().setFillType(FillType.SOLID);
    fmt.getFillFormat().getSolidFillColor().setColor(Color.fromArgb(255, 0, 70, 127));
    prs.save("text.pptx", SaveFormat.PPTX);
}
```

## See Also

The `Presentation` class provides access to slides via the getSlides() method. Related core classes include `BaseSlide`, `Cell`, `BulletFormat`, and `ColorFormat`.

```java
import com.aspose.slides.*;

try (Presentation prs = new Presentation()) {
    ISlide slide = prs.getSlides().get(0);
    System.out.println("Slides: " + prs.getSlides().size());
}

```

- [Access slide columns](/reference.aspose.org/slides/java/column/)
- [Open existing presentations](/blog.aspose.org/slides/java/slides-foss-java/)
- [Key features overview](/blog.aspose.org/slides/java/slides-features/)
- [Create new presentations](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
- [Work with slides](/docs.aspose.org/slides/java/developer-guide/slide-manipulation/)
