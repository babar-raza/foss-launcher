---
canonical: https://reference.aspose.org/slides/java/column/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: 'Aspose.Slides FOSS for Java: Blur: Represents a Blur effect that is
  applied to the entire shape, including its fill'
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
seoTitle: Aspose.Slides FOSS Column
slug: column
title: Column
type: reference_object_page
url: /reference.aspose.org/slides/java/column/
weight: 22
---

## Overview

Aspose.Slides FOSS for Java -- Class or function purpose in 1-3 sentences.

Aspose.Slides FOSS for Java Blur: Represents a Blur effect that is applied to the entire shape, including its fill. CellFormat: Represents format of a table cell.

```java
import org.aspose.slides.foss.*;
import org.aspose.slides.foss.export.SaveFormat;

try (Presentation prs = new Presentation()) {
    ITable table = prs.getSlides().get(0).getShapes()
            .addTable(50, 50, new double[]{120, 120, 120}, new double[]{40, 40});
    table.getRows().get(0).get(0).getTextFrame().setText("Name");
    table.getRows().get(0).get(1).getTextFrame().setText("Value");
    prs.save("table.pptx", SaveFormat.PPTX);
}
```

```java
import org.aspose.slides.foss.*;
import org.aspose.slides.foss.drawing.Color;
import org.aspose.slides.foss.export.SaveFormat;

try (Presentation prs = new Presentation()) {
    IAutoShape shape = prs.getSlides().get(0).getShapes()
            .addAutoShape(ShapeType.RECTANGLE, 50, 50, 300, 150);
    shape.getFillFormat().setFillType(FillType.SOLID);
    shape.getFillFormat().getSolidFillColor().setColor(Color.fromArgb(255, 30, 120, 200));
    prs.save("fill.pptx", SaveFormat.PPTX);
}
```

```java
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.concurrent.atomic.AtomicBoolean;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.data.Offset.offset;

Element tcPr = createTcPrElement();
        var fmt = new CellFormat(tcPr, null);

        ILineFormat border = fmt.getBorderTop();
        border.setWidth(3.0);
```

```java
import org.aspose.slides.foss.IPresentationComponent;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.data.Offset.offset;

var blur = new Blur(blurElement, null);
        IImageTransformOperation result = blur.asIImageTransformOperation();
```

```java
import org.aspose.slides.foss.IPresentationComponent;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.data.Offset.offset;

var blur = new Blur(blurElement, null);
        IPresentationComponent result = blur.asIPresentationComponent();
```

```java
import org.aspose.slides.foss.drawing.Color;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import static org.assertj.core.api.Assertions.assertThat;

var pres = new Presentation();
        ISlide slide = blankSlide(pres);
        ITable table = slide.getShapes().addTable(50, 50,
                new double[]{200}, new double[]{60});
        ICell cell = table.getRows().get(0).get(0);
        cell.getCellFormat().getFillFormat().setFillType(FillType.SOLID);
        cell.getCellFormat().getFillFormat().getSolidFillColor().setColor(Color.LIGHT_BLUE);
        cell.getTextFrame().setText("Blue");

        try (Presentation pres2 = roundTrip(pres)) {
            ITable t2 = findTable(pres2.getSlides().get(0));
            ICellFormat cf2 = t2.getRows().get(0).get(0).getCellFormat();
        }
```

## Constructor

The `Column` class represents `a` column in `a` table and provides access to column-specific properties and methods. It is instantiated using `a` constructor that binds it to an underlying XML element and table context.

| Parameter | Type | Description |
|-----------|------|-------------|
| gridColElement | `Element` | The underlying gridCol XML element. |
| saveCallback | `Runnable` | Callback invoked when changes are saved. |
| cells | `Cell[]` | Array of `Cell` objects belonging to this column. |

```java
import com.aspose.slides.*;

var column = new Column(null, () -> {}, new Cell[0]);
```

## Properties

The `Column` class represents `a` column in `a` table and provides access to its width and associated cells. It is initialized with an underlying XML element and table context, and supports saving changes via save().

| Name | Type | Description |
|------|------|-------------|
| `Element` | `Element` | Returns the underlying XML element backing this column. |
| `Runnable` | `Runnable` | Callback invoked when changes are saved. |
| `IBaseSlide` | `IBaseSlide` | Returns the parent slide containing the table. |
| `ITable` | `ITable` | Returns the parent table containing this column. |
| Width | double | Gets the width of the column in points. |

```java
import com.aspose.slides.*;

try (Presentation prs = new Presentation()) {
    ITable table = prs.getSlides().get(0).getShapes()
            .addTable(50, 50, new double[]{100, 100, 100}, new double[]{50, 50});
    IColumn column = table.getColumns().get(0);
    double width = column.getWidth();
}

```

## Methods

The `Column` class represents `a` column in `a` table and provides methods to access its width and underlying XML structure. It is used to manage column-level properties in table layouts.

```java
import com.aspose.slides.*;

try (Presentation prs = new Presentation()) {
    ITable table = prs.getSlides().get(0).getShapes()
            .addTable(50, 50, new double[]{100, 100, 100}, new double[]{50, 50});
    double width = table.getColumns().get(1).getWidth();
}
```

| Method | Return Type | Description |
|--------|-------------|-------------|
| `Column(gridColElement: Element, saveCallback: Runnable, cells)` | Constructor | Creates `a` new `Column` backed by the given gridColElement. |
| `initInternal(gridColElement: Element, colIndex, tblElement: Element, saveCallback: Runnable, parentSlide: IBaseSlide, table: ITable)` | void | Initializes this column from the given gridColElement and table context. |
| `findChildren(parent: Element, localName: String)` | List<`Element`> | [static] Finds child elements with the specified local name. |
| save() | void | Saves changes to the underlying XML. |
| getWidth() | double | Returns the width of the column in points. |

## Example

The `Column` class represents `a` column in `a` table and provides access to its width and associated cells. The save() method persists changes to the underlying XML structure.

```java
import com.aspose.slides.*;

var pres = new Presentation();
var slide = pres.getSlides().get(0);
var table = slide.getShapes().addTable(50, 50, new double[]{150, 150}, new double[]{50, 50, 50});
table.getColumns().get(0).setWidth(200);
table.getRows().get(0).get(0).getTextFrame().setText("Cell A1");
 pres.save("table.pptx", SaveFormat.PPTX);
```

## See Also

The `Column` class represents `a` column in `a` table and provides access to its width and associated cells. Related classes include `ColumnCollection`, which manages `a` collection of columns, and `CellCollection`, which manages cells within `a` row or table.

```java
import com.aspose.slides.*;

try (Presentation pres = new Presentation()) {
    ITable table = pres.getSlides().get(0).getShapes()
            .addTable(50, 50, new double[]{120, 120}, new double[]{40, 40});
    IColumn column = table.getColumns().get(0);
    column.save();
}
```

- [The Presentation class provides access to slides via the getSlides() method](/reference.aspose.org/slides/java/presentation/)
- [Open existing presentations](/blog.aspose.org/slides/java/slides-foss-java/)
- [Key features for slides](/blog.aspose.org/slides/java/slides-features/)
- [Create presentations from scratch](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
- [Work with slides programmatically](/docs.aspose.org/slides/java/developer-guide/slide-manipulation/)
