---
canonical: https://blog.aspose.org/slides/java/slides-foss-java/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: Aspose.Slides FOSS for Java gives you direct, code-first control over
  `.pptx` files without requiring Microsoft PowerPoint or external dependencies.
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
page_role: blog_announcement
platform: java
reading_time: 1
robots: index, follow
seoTitle: The Presentation class allows opening existing presentations | Guide
slug: slides-foss-java
title: The Presentation class allows opening existing presentations
type: blog_announcement
url: /blog.aspose.org/slides/java/slides-foss-java/
weight: 16
---

## Introduction

You need to process PowerPoint files in your Java application — maybe to generate reports, automate slide decks, or convert presentations to PDF. Aspose.Slides FOSS for Java gives you direct, code-first control over `.pptx` files without requiring Microsoft PowerPoint or external dependencies.

```java
import com.aspose.slides.*;
import com.aspose.slides.export.SaveFormat;

// Open an existing presentation
try (Presentation prs = new Presentation("input.pptx")) {
    prs.save("output.pptx", SaveFormat.PPTX);
}

// Create a new presentation from scratch
try (Presentation prs = new Presentation()) {
    var slide = prs.getSlides().get(0);
    prs.save("new.pptx", SaveFormat.PPTX);
}
```

The `Presentation` class handles both workflows: loading an existing `.pptx` file by path or stream, and initializing `a` blank presentation ready for content. Every operation preserves layout, formatting, and embedded objects through full round-trip fidelity. This makes it ideal for batch processing, templating, or dynamic slide generation in CI/CD pipelines.

## Key Highlights

- The `Presentation` constructor accepts a file path to open existing `.pptx` presentations for reading or editing.
- Calling `new Presentation()` without arguments creates a blank presentation with one default slide.
- All changes are persisted by calling save() with a target filename and `SaveFormat` enum value.
- The library supports full round-trip fidelity: opening, modifying, and re-saving preserves layout and metadata.
- You can iterate slides, add shapes, insert tables, and apply text formatting using only the `com.aspose.slides` package.

## Getting Started

You need to process PowerPoint files in your Java application — maybe to update slides, extract content, or generate reports. Aspose.Slides FOSS for Java lets you open existing presentations or create new ones with just `a` few lines of code. The `Presentation` class handles both workflows seamlessly.

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

The constructor `new Presentation("input.pptx")` loads `a` `.pptx` file from disk, preserving all slides, shapes, and formatting. The `new Presentation()` constructor initializes an empty presentation with one default slide. Both approaches support the `try-with-resources` pattern for safe resource cleanup. After loading or creating, you can manipulate slides and shapes before saving the result.

## See Also

The `Presentation` class is the entry point for working with PowerPoint files in Aspose.Slides FOSS for Java. You can open an existing `.pptx` file or create `a` new presentation from scratch — both workflows are fully supported with identical APIs.

- [Learn about the Presentation class](/products.aspose.org/slides/_index/)
- [Discover key features and capabilities](/blog.aspose.org/slides/java/slides-features/)
- [Create presentations from scratch](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
- [Work with slides programmatically](/docs.aspose.org/slides/java/developer-guide/slide-manipulation/)
- [Convert file formats easily](/kb.aspose.org/slides/java/convert-png-pptx-java/)
