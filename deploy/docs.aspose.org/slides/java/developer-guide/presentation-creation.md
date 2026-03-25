---
canonical: https://docs.aspose.org/slides/java/developer-guide/presentation-creation/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: You start with `a` blank or existing `.pptx` file, `add` slides and content
  such as shapes, tables, and formatted text, then save the result as `a` new...
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
seoTitle: Create Presentations with Aspose.Slides FOSS for Java | Guide
slug: presentation-creation
title: Create Presentations with Aspose.Slides FOSS for Java
type: workflow_page
url: /docs.aspose.org/slides/java/developer-guide/presentation-creation/
weight: 18
---

## Overview

This guide walks you through creating and manipulating presentation files using Aspose.Slides FOSS for Java. You start with `a` blank or existing `.pptx` file, `add` slides and content such as shapes, tables, and formatted text, then save the result as `a` new `.pptx` file.

```java
import com.aspose.slides.*;

// Create a new presentation
Presentation presentation = new Presentation();

// Add a blank slide
ISlide slide = presentation.getSlides().addEmptySlide(presentation.getSlides().get_Item(0));

// Save the presentation to disk
presentation.save("output.pptx", SaveFormat.Pptx);
```

- Use this approach when generating reports from templates with dynamic slide content.
- Use this approach when building slide decks programmatically from data sources.
- Use this approach when creating presentations for archival or distribution without user interaction.

## Working with Data

This section shows how to read, write, and modify data elements in Aspose.Slides FOSS for Java presentations. You work with tables, cells, columns, and comments using core classes like `Cell`, `Column`, `Comment`, and `CommentCollection`. All operations preserve the original presentation structure and formatting.

```java
import com.aspose.slides.*;

// Load an existing presentation
Presentation presentation = new Presentation("input.pptx");
ISlide slide = presentation.getSlides().get(0);
ITable table = (ITable) slide.getShapes().get(0);

// Read data from the first cell
Cell cell = table.getRows().get(0).get(0);
String cellText = cell.getText();
System.out.println("Cell text: " + cellText);
```

- Use this approach when extracting data from embedded tables for reporting.
- Read cell content before modifying to verify current values.
- Access columns via `table.getRows().get(rowIndex).get(colIndex)` for precise targeting.

To write or update data, assign new text to `a` cell and call save() to persist changes. The `Cell` class supports direct text assignment through its setText() method. Always ensure the target cell exists before writing to avoid runtime errors.

```java
import com.aspose.slides.*;

Presentation presentation = new Presentation("input.pptx");
ISlide slide = presentation.getSlides().get(0);
ITable table = (ITable) slide.getShapes().get(0);

// Write new data to the second cell in the first row
table.getRows().get(0).get(1).setText("Updated Value");

// Save the modified presentation
presentation.save("output.pptx", SaveFormat.Pptx);
```

- Use this pattern when updating report figures or labels programmatically.
- Ensure the target cell index is within bounds to prevent IndexOutOfBoundsException.
- Call save() after all modifications to commit changes to disk.

Modify column widths using the `Column` class and its getWidth() method. The `ColumnCollection` provides access to all columns via index-based retrieval. Adjusting column width affects the entire column layout in the table.

```java
import com.aspose.slides.*;

Presentation presentation = new Presentation("input.pptx");
ISlide slide = presentation.getSlides().get(0);
ITable table = (ITable) slide.getShapes().get(0);

// Access the first column and set its width
table.getColumns().get(0).setWidth(150.0);

// Save the updated presentation
presentation.save("output.pptx", SaveFormat.Pptx);
```

- Adjust column widths to fit dynamic content like long labels or numbers.
- Use getWidth() to read current width before making adjustments.
- Column width changes apply to all cells in that column across rows.

Add or edit comments using the `Comment` and `CommentCollection` classes. Comments attach to specific slides and authors, supporting metadata like creation time and position. Use `CommentCollection` to manage all comments for `a` given author.

```java
import com.aspose.slides.*;

Presentation presentation = new Presentation("input.pptx");
ISlide slide = presentation.getSlides().get(0);
ICommentAuthor author = presentation.getCommentAuthors().get(0);

// Add a new comment to the slide
Comment comment = new Comment("Review note", author, slide, new java.awt.Point(100, 100), java.time.LocalDateTime.now());
slide.getComments().add(comment);

// Save the presentation with the new comment
presentation.save("output.pptx", SaveFormat.Pptx);
```

- Attach feedback or review notes directly to slides for team collaboration.
- Include timestamps and precise coordinates for comment placement.
- Retrieve existing comments via `slide.getComments()` for auditing or editing.

## Code Examples

This guide walks you through creating a new presentation, adding a slide with a title and bullet list, and saving it as a .pptx file using Aspose.Slides FOSS for Java. The workflow uses only the canonical import path and classes from the verified API surface.

```java
import com.aspose.slides.*;

public class CreatePresentation {
    public static void main(String[] args) {
        // Create a new presentation
        Presentation presentation = new Presentation();

        // Access the first slide
        ISlide slide = presentation.getSlides().get_Item(0);

        // Add a title placeholder and set text
        IAutoShape titleShape = slide.getShapes().addAutoShape(ShapeType.Rectangle, 100, 100, 500, 100);
        titleShape.getTextFrame().setText("Welcome to Aspose.Slides FOSS for Java");

        // Add a bullet list
        IAutoShape bulletShape = slide.getShapes().addAutoShape(ShapeType.Rectangle, 100, 250, 500, 200);
        IParagraph paragraph = bulletShape.getTextFrame().getParagraphs().addParagraph();
        paragraph.getParagraphFormat().getBullet().setType(BulletType.Symbol);
        paragraph.getTextFrame().setText("Create presentations programmatically\nAdd shapes and text\nSave to .pptx format");

        // Save the presentation
        presentation.save("output.pptx", SaveFormat.Pptx);
    }
}
```

- Use this approach when generating reports or training decks from structured data.
- Use this approach when building presentation templates with dynamic content.
- Use this approach when automating slide creation for documentation pipelines.

The example demonstrates core operations: instantiating a `Presentation`, adding shapes via `IAutoShape`, and configuring bullet formatting through `IParagraph` and `BulletFormat`. All operations use only methods and types from the verified API surface.

Ensure your project includes the Aspose.Slides FOSS for Java JAR in the classpath. The library supports full round-trip fidelity for .pptx files and integrates with standard Java I/O streams.

For more advanced workflows, you can extend this pattern by adding tables, images, or 3D camera settings using the `Cell`, `Column`, and `Camera` classes from the API surface.

## Notes and Best Practices

When using Aspose.Slides FOSS for Java, manage memory carefully during large presentation processing and always `close` streams after use. Avoid holding unnecessary references to slide or shape objects to prevent memory bloat, especially in long-running services.

- Use `Presentation` within try-with-resources blocks to ensure automatic disposal of internal resources.
- Call `dispose()` explicitly on `Presentation` instances when not using try-with-resources.
- Avoid cloning slides repeatedly in loops—clone once and reuse where possible.
- Prefer `Slide.clone()` over `SlideCollection.addClone()` for better performance in batch operations.

## See Also

- [Open existing presentations](/blog.aspose.org/slides/java/slides-foss-java/)
- [Key features overview](/blog.aspose.org/slides/java/slides-features/)
- [Work with slides](/docs.aspose.org/slides/java/developer-guide/slide-manipulation/)
- [Convert file formats](/kb.aspose.org/slides/java/convert-png-pptx-java/)
- [Fix common errors](/kb.aspose.org/slides/java/fix-presentations-errors-java/)
