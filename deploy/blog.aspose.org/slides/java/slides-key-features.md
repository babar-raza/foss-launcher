---
canonical: https://blog.aspose.org/slides/java/slides-features/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: Built on the `com.aspose.slides` package, it enables developers to manipulate
  presentations using core classes like `Presentation`, `Slide`, `AutoShape`,...
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
page_role: feature_blog
platform: java
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides FOSS Slides Key Features
slug: slides-features
title: Slides Key Features
type: feature_blog
url: /blog.aspose.org/slides/java/slides-features/
weight: 17
---

## Introduction

If you have ever needed to programmatically create, modify, or convert PowerPoint presentations in Java without relying on Microsoft Office, Aspose.Slides FOSS for Java delivers `a` lightweight, server-safe solution. Built on the `com.aspose.slides` package, it enables developers to manipulate presentations using core classes like `Presentation`, `Slide`, `AutoShape`, and `TextFrame`.

The library supports full round-trip fidelity for `.pptx` files, allowing you to open, edit, and save presentations while preserving layout and formatting. You can `add` or remove slides, insert shapes and tables, apply text formatting—including bullets and character styles—and manage slide properties such as headers, footers, and comments. All operations occur entirely in memory, making it ideal for headless environments.

## Key Highlights

If you have ever needed to programmatically generate or modify PowerPoint presentations in Java without relying on Microsoft Office, Aspose.Slides FOSS for Java provides `a` lightweight, dependency-free solution. The library exposes core presentation manipulation capabilities through classes like `BaseSlide`, `AutoShape`, `Cell`, and `Comment`, all accessible via the canonical `com.aspose.slides.*` package.

- Process presentations by loading, creating, and saving `.pptx` files with full round-trip fidelity using `IPresentation` and related interfaces.
- Add and format shapes—including autoshapes and tables—with support for fill types, 3D effects, and locking via `AutoShape`, `BaseShapeLock`, and `Cell` classes.
- Manage text content at the portion, paragraph, and text frame level using `BasePortionFormat` and `BulletFormat` for precise styling control.
- Attach and retrieve comments on slides with `Comment`, `CommentAuthor`, and `CommentCollection` to support collaborative review workflows.
- Convert slides to PNG, JPEG, PDF, HTML, and other supported formats using built-in save options tied to the `SaveFormat` enum.

```java
import com.aspose.slides.*;

public class CreatePresentation {
    public static void main(String[] args) {
        // Create a new presentation
        Presentation pres = new Presentation();

        // Add a blank slide
        ISlide slide = pres.getSlides().addEmptySlide(pres.getSlides().get_Item(0));

        // Add a rectangle shape
        IAutoShape shape = slide.getShapes().addAutoShape(ShapeType.Rectangle, 100, 100, 300, 200);
        shape.getFillFormat().setFillType(FillType.Solid);
        shape.getFillFormat().getSolidFillColor().setColor(Color.getRed());

        // Save as PPTX
        pres.save("output.pptx", SaveFormat.Pptx);
    }
}
```

The `Presentation` class serves as the entry point for all operations. It supports opening existing `.pptx` files and creating new ones from scratch. Once instantiated, you can manipulate slides, shapes, and text using strongly-typed objects that mirror the underlying Office Open XML structure. The `ISlide` interface exposes methods to `add` and arrange content, while `IAutoShape` and `ICell` provide access to visual and tabular elements respectively.

Text formatting is handled through `BasePortionFormat` and `BulletFormat`, which expose low-level XML-backed properties like getRprElement() and removeBulletTypeElements(). These allow fine-grained control over character and paragraph styling without requiring external dependencies or COM interop.

## Getting Started

- Process PPTX files by loading, adding slides, and saving with full round-trip fidelity
- Insert and format shapes, tables, and text using `AutoShape`, `Cell`, and `BasePortionFormat`
- Attach comments to slides with `Comment` and `CommentAuthor` objects

```java
import com.aspose.slides.*;

public class CreateSimplePresentation {
    public static void main(String[] args) {
        Presentation presentation = new Presentation();
        ISlide slide = presentation.getSlides().addEmptySlide(presentation.getSlides().get_Item(0));
        IAutoShape shape = slide.getShapes().addAutoShape(ShapeType.Rectangle, 100, 100, 400, 100);
        shape.getTextFrame().getText().setText("Hello from Aspose.Slides FOSS for Java");
        presentation.save("output.pptx", SaveFormat.Pptx);
    }
}
```

The example above creates `a` new presentation, adds an empty slide, inserts `a` rectangle `AutoShape`, sets its text content, and saves the result as `output.pptx`. The `SaveFormat.Pptx` enum ensures the output conforms to the Office Open XML standard. All operations use only classes from the verified API surface, including `Presentation`, `ISlide`, `IAutoShape`, and `SaveFormat`.

For table manipulation, the `Cell` and `Column` classes enable structured data insertion. Each `Cell` can be initialized with row/column indices and associated table context, while `Column` exposes width and cell collection access. These classes support reading and writing tabular content in slides without external dependencies.

## See Also

- [Open existing presentations](/blog.aspose.org/slides/java/slides-foss-java/)
- [Create new presentations](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
- [Work with slides](/docs.aspose.org/slides/java/developer-guide/slide-manipulation/)
- [Convert file formats](/kb.aspose.org/slides/java/convert-png-pptx-java/)
- [Fix common errors](/kb.aspose.org/slides/java/fix-presentations-errors-java/)
