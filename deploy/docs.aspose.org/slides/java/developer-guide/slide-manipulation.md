---
canonical: https://docs.aspose.org/slides/java/developer-guide/slide-manipulation/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: The workflow starts with `a` `.pptx` file as input and ends with `a`
  modified `.pptx` file as output, using only the `com.aspose.slides` package.
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
page_role: workflow_page
platform: java
reading_time: 1
robots: index, follow
seoTitle: Work with Slides with Aspose.Slides FOSS for Java | Guide
slug: slide-manipulation
title: Work with Slides with Aspose.Slides FOSS for Java
type: workflow_page
url: /docs.aspose.org/slides/java/developer-guide/slide-manipulation/
weight: 19
---

## Overview

This guide walks you through working with slides in Aspose.Slides FOSS for Java — loading `a` presentation, accessing its slides, and saving changes. The workflow starts with `a` `.pptx` file as input and ends with `a` modified `.pptx` file as output, using only the `com.aspose.slides` package.

```java
import com.aspose.slides.*;

// Load an existing presentation
Presentation presentation = new Presentation("input.pptx");

// Access the first slide
ISlide slide = presentation.getSlides().get_Item(0);

// Save the modified presentation
presentation.save("output.pptx", SaveFormat.Pptx);
```

- Use this approach when updating slide content in batch processing pipelines.
- Apply this pattern when cloning slides for templated presentations.
- Adopt this workflow when reordering slides based on dynamic business rules.

The `Presentation` class loads `.pptx` files and exposes slide collections via getSlides(). Each `ISlide` instance supports operations like shape iteration, text modification, and formatting using classes such as `AutoShape`, `BasePortionFormat`, and `BulletFormat`. All changes persist only after calling save() with `a` target format.

Ensure your environment includes the Aspose.Slides FOSS for Java JAR in the classpath. No additional dependencies are required for basic slide operations.

## Working with Data

This section shows how to read, write, and modify data elements in Aspose.Slides FOSS for Java presentations. You load `a` presentation, access table cells or shapes containing data, update their content, and save the modified file.

```java
import com.aspose.slides.*;

public class WorkingWithData {
    public static void main(String[] args) {
        // Load a presentation with a table
        Presentation presentation = new Presentation("input.pptx");
        ISlide slide = presentation.getSlides().get(0);
        ITable table = (ITable) slide.getShapes().get(0);

        // Read a cell value
        String cellValue = table.getRows().get(0).getCells().get(0).getTextFrame().getText();
        System.out.println("Original cell value: " + cellValue);

        // Modify the cell value
        table.getRows().get(0).getCells().get(0).getTextFrame().setText("Updated Value");

        // Save the modified presentation
        presentation.save("output.pptx", SaveFormat.Pptx);
    }
}
```

- Use this approach when updating dynamic data in reports embedded in slides.
- Apply this pattern when correcting outdated figures in presentation templates.
- Leverage this method when programmatically populating slides from external data sources.

To read data from shapes other than tables, access the `TextFrame` of an `AutoShape`. The getText() method returns the full text content of the shape. For bullet formatting, use the `BulletFormat` class to inspect or modify bullet properties.

```java
import com.aspose.slides.*;

public class ReadShapeData {
    public static void main(String[] args) {
        Presentation presentation = new Presentation("input.pptx");
        ISlide slide = presentation.getSlides().get(0);

        // Access first AutoShape
        AutoShape shape = (AutoShape) slide.getShapes().get(1);
        String shapeText = shape.getTextFrame().getText();
        System.out.println("Shape text: " + shapeText);

        // Access paragraph bullet format
        BulletFormat bulletFormat = shape.getTextFrame().getParagraphs().get(0).getBulletFormat();
        System.out.println("Bullet type: " + bulletFormat.getType());

        presentation.dispose();
    }
}
```

- Use this approach when extracting slide content for indexing or analysis.
- Apply this pattern when auditing bullet styles across presentation slides.
- Leverage this method when migrating legacy text formatting to new standards.

To write new data, create `a` table or shape, populate its text content, and `add` it to the slide. Use `Cell` and `Column` objects to define table structure programmatically.

```java
import com.aspose.slides.*;

public class WriteNewData {
    public static void main(String[] args) {
        Presentation presentation = new Presentation();
        ISlide slide = presentation.getSlides().get(0);

        // Create a 3x3 table
        double[] widths = {100, 100, 100};
        double[] heights = {30, 30, 30};
        ITable table = slide.getShapes().addTable(50, 50, widths, heights);

        // Populate cells
        for (int row = 0; row < 3; row++) {
            for (int col = 0; col < 3; col++) {
                table.getRows().get(row).getCells().get(col).getTextFrame().setText("R" + row + "C" + col);
            }
        }

        presentation.save("output.pptx", SaveFormat.Pptx);
    }
}
```

- Use this approach when generating dynamic tables from database query results.
- Apply this pattern when building slide decks from structured JSON or CSV data.
- Leverage this method when creating standardized report templates with pre-filled data.

For modifying existing data, access the `Cell` or `TextFrame` object and call setText() to replace content. Always call save() to persist changes to disk.

## Code Examples

This guide walks you through creating a new presentation, adding a slide, inserting a table with formatted cells, and saving the result as a PPTX file using Aspose.Slides FOSS for Java. You will use core classes like `Presentation`, `SlideCollection`, `Table`, `Cell`, and `Column` to build a structured slide layout programmatically.

```java
import com.aspose.slides.*;

// Create a new presentation
Presentation presentation = new Presentation();

// Add a blank slide
ISlide slide = presentation.getSlides().addEmptySlide(presentation.getSlides().get_Item(0));

// Create a 3x3 table with 100pt column widths
Table table = new Table(100, 100, 100, 50, 50, 50);
slide.getShapes().addTable(table);

// Populate the first row
Cell cell00 = table.getRows().get_Item(0).get_Item(0);
cell00.getTextFrame().setText("Header 1");

Cell cell01 = table.getRows().get_Item(0).get_Item(1);
cell01.getTextFrame().setText("Header 2");

Cell cell02 = table.getRows().get_Item(0).get_Item(2);
cell02.getTextFrame().setText("Header 3");

// Save the presentation
presentation.save("output.pptx", SaveFormat.Pptx);
```

- Use this approach when generating report templates with consistent column headers.
- Use this approach when building slide decks from tabular data sources like CSV or databases.
- Use this approach when preparing presentations for archival where exact layout fidelity matters.

Next, you can add a second slide with a bullet list using `Paragraph` and `Portion` objects. This demonstrates how to apply bullet formatting and text styling using the `BulletFormat` and `BasePortionFormat` classes from the API surface.

```java
import com.aspose.slides.*;

// Load the existing presentation
Presentation presentation = new Presentation("output.pptx");

// Add a new slide with title layout
ISlide slide2 = presentation.getSlides().addEmptySlide(presentation.getSlides().get_Item(0));

// Create a text frame and paragraph
AutoShape shape = (AutoShape) slide2.getShapes().addAutoShape(ShapeType.Rectangle, 50, 100, 500, 200);
Paragraph paragraph = new Paragraph();
shape.getTextFrame().getParagraphs().add(paragraph);

// Add a portion with bullet formatting
Portion portion = new Portion("First bullet point");
paragraph.getPortions().add(portion);

// Apply bullet type and formatting
BulletFormat bulletFormat = paragraph.getParagraphFormat().getBullet();
bulletFormat.setType(BulletType.Symbol);

// Save updated presentation
presentation.save("output_with_bullets.pptx", SaveFormat.Pptx);
```

- Use this approach when creating slide outlines for meeting agendas or project milestones.
- Use this approach when converting markdown-style bullet lists into presentation slides.
- Use this approach when applying consistent bullet styles across multiple slides in a deck.

Finally, you can add a comment to a slide using `Comment` and `CommentAuthor` classes. This shows how to attach metadata to specific slide positions for collaborative review workflows.

```java
import com.aspose.slides.*;

// Load the presentation
Presentation presentation = new Presentation("output_with_bullets.pptx");

// Get the first slide
ISlide slide = presentation.getSlides().get_Item(0);

// Create a comment author if not present
ICommentAuthor author = presentation.getCommentAuthors().addAuthor("Reviewer", "R.A.");

// Add a comment at a specific point
PointF position = new PointF(100, 100);
Comment comment = new Comment("Please verify table alignment.", author, slide, position, LocalDateTime.now());
slide.getComments().add(comment);

// Save with comments embedded
presentation.save("output_with_comments.pptx", SaveFormat.Pptx);
```

- Use this approach when embedding reviewer feedback directly into slide decks for internal review.
- Use this approach when archiving presentation review history alongside the final deliverable.
- Use this approach when syncing comments with external tracking systems via programmatic comment extraction.

## Notes and Best Practices

When working with Aspose.Slides FOSS for Java, managing memory efficiently and avoiding common pitfalls ensures stable slide processing in production. This section outlines key notes and best practices for developers handling slides, shapes, and text.

- Always call `dispose()` on `Presentation` objects after use to release native resources and prevent memory leaks.
- Avoid holding multiple `Presentation` instances open simultaneously—close or dispose them as soon as operations complete.
- Use `Slide.getClone()` instead of manual slide copying to preserve formatting and layout fidelity during duplication.
- Prefer iterating slides via `Presentation.getSlides().iterator()` over index-based access for better performance on large presentations.

## See Also

- [Open existing presentations](/blog.aspose.org/slides/java/slides-foss-java/)
- [Key features overview](/blog.aspose.org/slides/java/slides-features/)
- [Create new presentations](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
- [Convert file formats](/kb.aspose.org/slides/java/convert-png-pptx-java/)
- [Fix common errors](/kb.aspose.org/slides/java/fix-presentations-errors-java/)
