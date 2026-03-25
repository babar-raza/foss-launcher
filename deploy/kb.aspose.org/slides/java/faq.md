---
canonical: https://kb.aspose.org/slides/java/faq/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: This is the only valid import path—do not use `import com.aspose.slides`,
  `import com.aspose.slides FOSS for Java.*` with aliases, or any other variation....
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
page_role: faq
platform: java
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FOSS for Java FAQ | Guide
slug: faq
title: Aspose.Slides FOSS for Java FAQ
type: faq
url: /kb.aspose.org/slides/java/faq/
weight: 8
---

## Frequently Asked Questions

### What is the correct import statement for Aspose.Slides FOSS for Java?

Use `import com.aspose.slides FOSS for Java.*;` to import all classes in the Aspose.Slides FOSS for Java library. This is the only valid import path—do not use `import com.aspose.slides`, `import com.aspose.slides FOSS for Java.*` with aliases, or any other variation. All classes such as `Presentation`, `AutoShape`, `Cell`, and `Comment` are accessible only through this package. Using an incorrect import path will cause compilation errors because the library is strictly scoped to `com.aspose.slides.*`.

### Which features are not implemented in Aspose.Slides FOSS for Java?

The following areas are not implemented: advanced animation timelines, 3D model rendering beyond basic camera and bevel settings, macro execution, VBA project manipulation, and certain shape lock features. These limitations are explicitly listed in the product's README and reflect the current scope of the FOSS distribution. Developers should avoid relying on these features if using this version.

### Can I create and format tables in Aspose.Slides FOSS for Java?

Yes, you can create and format tables using the `Cell`, `Column`, `CellCollection`, and `ColumnCollection` classes. Tables are added to slides via `AutoShape` or directly on slide layouts, and cell content can be set using `Cell` methods. Formatting such as borders and fills is supported through `CellFormat` and `ColumnFormat`. However, advanced table layout features like merged cells or complex grid alignment may be limited depending on the underlying XML structure.

### How do I `add` `a` comment to `a` slide?

Create `a` new comment using the `Comment` class constructor, specifying the text, author, slide, position, and creation time. Then `add` it to the slide's comment collection via the `CommentCollection` and `CommentAuthor` classes. Comments are persisted when the presentation is saved as `a` `.pptx` file. Note that comment threading and resolution states are not supported in this version.

```java
import com.aspose.slides.*;

Presentation presentation = new Presentation();
ISlide slide = presentation.getSlides().get(0);
ICommentAuthor author = presentation.getCommentAuthors().addAuthor("John Doe", "JD");
PointF position = new PointF(100f, 100f);
LocalDateTime time = LocalDateTime.now();
Comment comment = new Comment("This is a sample comment.", author, slide, position, time);
slide.getComments().add(comment);
presentation.save("output.pptx", SaveFormat.Pptx);
```

## See Also

Review these related resources to deepen your understanding of Aspose.Slides FOSS for Java and its current capabilities. The product supports core presentation operations including opening, creating, and saving .pptx files, managing slides, and working with shapes, text, and formatting. However, per the official README, certain areas remain unimplemented — specifically, the following features are not supported: advanced 3D rendering, animation timelines, and custom XML parts beyond basic OPC structure. Always verify feature availability against the latest release notes before implementation.

- [Troubleshooting common issues](/kb.aspose.org/slides/java/troubleshooting/)
- [Convert file formats step-by-step](/kb.aspose.org/slides/java/convert-png-pptx-java/)
- [Fix common errors effectively](/kb.aspose.org/slides/java/fix-presentations-errors-java/)
- [Load files correctly and efficiently](/kb.aspose.org/slides/java/load-presentations-java/)
- [Optimize performance for best results](/kb.aspose.org/slides/java/optimize-presentations-java/)
