---
canonical: https://products.aspose.org/slides/_index/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: It supports reading, writing, and modifying .pptx files with full fidelity,
  enabling developers to automate slide generation, formatting, and conversion in...
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
page_role: landing
platform: java
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Slides FOSS for Java | Guide
slug: _index
title: Aspose.Slides FOSS for Java
type: landing
url: /products.aspose.org/slides/_index/
weight: 1
---

## Overview

Aspose.Slides FOSS for Java -- Product introduction and key value proposition.

Aspose.Slides FOSS for Java Install Aspose.Slides FOSS for Java via: mvn dependency:get -Dartifact=org.aspose.slides.foss:aspose-slides-foss:1.0.0.

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

## Key Features

Aspose.Slides FOSS for Java processes PowerPoint presentations without requiring Microsoft PowerPoint. It supports reading, writing, and modifying .pptx files with full fidelity, enabling developers to automate slide generation, formatting, and conversion in Java applications.

- Open existing presentations with `Presentation` to load and modify .pptx files
- Create new presentations from scratch using the parameterless `Presentation` constructor
- Add and format shapes—including rectangles, connectors, and picture frames—with full layout control
- Apply text formatting at portion, paragraph, and text frame levels, including font size, bold, and color
- Configure solid, gradient, and pattern fills for shapes and text using `ColorFormat` and `FillFormat`
- Manage comments with authors, positions, and timestamps for collaborative review workflows

```java
import com.aspose.slides.*;
import com.aspose.slides.export.SaveFormat;

// Open an existing presentation
try (Presentation prs = new Presentation("input.pptx")) {
    prs.save("output.pptx", SaveFormat.PPTX);
}

// Create a new presentation
try (Presentation prs = new Presentation()) {
    var slide = prs.getSlides().get(0);
    prs.save("new.pptx", SaveFormat.PPTX);
}
```

## Quick Start

Aspose.Slides FOSS for Java processes PowerPoint files without requiring Microsoft PowerPoint. It supports reading, writing, and modifying .pptx presentations programmatically, enabling server-side slide generation, report automation, and document conversion in Java applications.

- Open existing presentations with `new Presentation("input.pptx")`
- Create new presentations from scratch with `new Presentation()`
- Add shapes, text, and formatting to slides
- Save presentations in .pptx format with full fidelity

## See Also

To begin using Aspose.Slides FOSS for Java, install it via Maven using the command `mvn dependency:get -Dartifact=org.aspose.slides.foss:aspose-slides-foss:1.0.0`. The `Presentation` class supports both opening existing presentations and creating new ones from scratch, enabling end-to-end slide manipulation without requiring Microsoft PowerPoint.

- [Open existing presentations with Presentation class](/blog.aspose.org/slides/java/slides-foss-java/)
- [Key features of Aspose.Slides FOSS for Java](/blog.aspose.org/slides/java/slides-features/)
- [Create new presentations step by step](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
- [Work with slides programmatically](/docs.aspose.org/slides/java/developer-guide/slide-manipulation/)
- [Convert file formats easily](/kb.aspose.org/slides/java/convert-png-pptx-java/)
