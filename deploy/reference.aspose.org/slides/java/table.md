---
canonical: https://reference.aspose.org/slides/java/table/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: 'ColorFormat: Represents a color used in a presentation.'
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
seoTitle: The Table class allows adding tables via the addTable()
slug: table
title: The Table class allows adding tables via the addTable() method
type: reference_object_page
url: /reference.aspose.org/slides/java/table/
weight: 20
---

## Overview

Aspose.Slides FOSS for Java -- Class or function purpose in 1-3 sentences.

Aspose.Slides FOSS for Java BulletFormat.initInternal(): Initializes this bullet format from the given {@code } element. ColorFormat: Represents a color used in a presentation.

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
import java.util.List;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

Element avLst = createAvLstWithGds(2);
        var collection = new AdjustValueCollection();
        collection.initInternal(avLst, null);

        IAdjustValue first = collection.get(0);

        IAdjustValue second = collection.get(1);
```

```java
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.List;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

Element avLst = createAvLstWithGds(3);
        var collection = new AdjustValueCollection();
        collection.initInternal(avLst, null);

        List<IAdjustValue> list = collection.asICollection();
```

```java
import static org.assertj.core.api.Assertions.assertThat;

var color = new Color(0, 128, 255);
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

## Constructor

The `Table` class represents `a` table on `a` slide and provides the `addTable()` method to insert tables. Tables are constructed via `addTable()` on `a` `ShapeCollection` and initialized with grid dimensions and position.

| Constructor | Parameters | Description |
|-------------|------------|-------------|
| `Table()` | — | Creates an empty `Table` with no backing element. |
| `Table(x: double, y: double, width: double, height: double, columns: int, rows: int)` | x, y, width, height, columns, rows | Creates `a` new `Table` at the specified position and size with the given grid dimensions. |
| `Table(x: double, y: double, width: double, height: double, columns: int, rows: int, tableStyle: ITableStyle)` | x, y, width, height, columns, rows, tableStyle | Creates `a` new `Table` with an initial style applied. |

```java
import com.aspose.slides.*;

try (var pres = new Presentation()) {
    var slide = pres.getSlides().get(0);
    var table = slide.getShapes().addTable(100, 100, 400, 200, 3, 2);
    table.getCell(0, 0).getTextFrame().setText("Header 1");
    table.getCell(0, 1).getTextFrame().setText("Header 2");
}
```

## Properties

The `Table` class provides access to table structure through its properties. This section lists the properties exposed by the `Table` class in Aspose.Slides FOSS for Java.

| Name | Type | Description |
|------|------|-------------|
| getRows() | `ICellCollection` | Returns the collection of rows in the table. |
| `getColumns()` | `IColumnCollection` | Returns the collection of columns in the table. |
| getLeft() | double | Returns the left position of the table. |
| getTop() | double | Returns the top position of the table. |
| getWidth() | double | Returns the width of the table. |
| getHeight() | double | Returns the height of the table. |
| getHasHeaderRow() | boolean | Indicates whether the table has `a` header row. |
| getVerticalAlignment() | `TextVerticalType` | Returns the vertical alignment of text in the table cells. |
| getCellMarginTop() | double | Returns the top margin of cells in the table. |
| getCellMarginBottom() | double | Returns the bottom margin of cells in the table. |
| getCellMarginLeft() | double | Returns the left margin of cells in the table. |
| getCellMarginRight() | double | Returns the right margin of cells in the table. |
| `getCellFormat()` | `ICellFormat` | Returns the cell format object for the table. |
| getFormat() | IShapeFormat | Returns the shape format object for the table. |
| getSlide() | `ISlide` | Returns the parent slide of the table. |

```java
import com.aspose.slides.*;

try (Presentation pres = new Presentation()) {
    ITable table = pres.getSlides().get(0).getShapes().addTable(50, 50, new double[]{120, 120}, new double[]{40, 40});
    int rowCount = table.getRows().size();
    int colCount = table.getColumns().size();
    double width = table.getWidth();
    pres.save("table.pptx", SaveFormat.PPTX);
}
```

## Methods

The `Cell` class represents `a` single cell in `a` table and provides methods to initialize and access its underlying XML structure. It supports vertical text orientation and exposes the tcPr child element via getTcPr().

| Method | Return Type | Description |
|--------|-------------|-------------|
| `Cell()` | `Cell` | Creates an empty `Cell` with no backing element. |
| `initInternal(tcElement: Element, rowIndex, colIndex, saveCallback: Runnable, parentSlide: IBaseSlide, table: ITable)` | void | Initializes this cell from the given tc element and table context. |
| save() | void | Persists changes by invoking the save callback if present. |
| `findChild(parent: Element, localName: String)` | `Element` | Finds `a` child element by local name within the given parent. |
| getTcPr() | `Element` | Returns the tcPr child element of the backing tc element. |

```java
import org.w3c.dom.Element;
import com.aspose.slides.*;

Element tc = createTcElement();
Cell cell = new Cell(tc, null);
cell.setTextVerticalType(TextVerticalType.VERTICAL270);
```

The `Column` class represents `a` table column and provides access to its width and associated cells. It is initialized with grid column data and table context.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `Column(gridColElement: Element, saveCallback: Runnable, cells)` | `Column` | Creates `a` new `Column` backed by the given gridCol element. |
| `initInternal(gridColElement: Element, colIndex, tblElement: Element, saveCallback: Runnable, parentSlide: IBaseSlide, table: ITable)` | void | Initializes this column from the given gridCol element and table context. |
| `[static] findChildren(parent: Element, localName: String)` | `List<Element>` | Finds all child elements with the specified local name. |
| save() | void | Persists changes by invoking the save callback if present. |
| getWidth() | double | Returns the width of the column. |

The `AdjustValue` class represents `a` single geometry adjustment value backed by an OOXML `a:gd` element, used in shape geometry definitions.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `AdjustValue(gdElement: Element, saveCallback: Runnable)` | `AdjustValue` | Creates `a` new `AdjustValue` backed by the given `a:gd` element. |
| save() | void | Persists changes by invoking the save callback if present. |
| `findChild(parent: Element, localName: String)` | `Element` | Finds `a` child element by local name within the given parent. |

```java
import org.w3c.dom.Element;
import com.aspose.slides.*;

Element gd = doc.createElementNS(NS_A, "a:gd");
doc.appendChild(gd);
AdjustValue adj = new AdjustValue(gd, null);
```

## Example

The `Table` class enables adding tables to slides using the `addTable()` method. This example demonstrates creating `a` table, initializing its cells, and setting vertical text orientation.

```java
import com.aspose.slides.*;
import org.w3c.dom.Element;

// Create a table with 2 rows and 2 columns
ITable table = slide.getShapes().addTable(100, 100, 300, 300, new double[]{150, 150}, new double[]{50, 50});

// Initialize and configure a cell
Cell cell = (Cell)table.getRows().get(0).getCells().get(0);
cell.initInternal(null, 0, 0, null, slide, table);
cell.setTextVerticalType(TextVerticalType.VERTICAL270);

// Save the presentation
presentation.save("output.pptx", SaveFormat.PPTX);
```

## See Also

The `Table` class enables adding tables to slides using the `addTable()` method. Related classes include `Cell`, `Column`, and `ColorFormat`, which support table structure and formatting.

```java
import com.aspose.slides.*;

var pres = new Presentation();
ISlide slide = pres.getSlides().get(0);
ITable table = slide.getShapes().addTable(50, 50,
    new double[]{120, 120, 120}, new double[]{40, 40});
```

- [Aspose.Slides FOSS for Java API reference](/reference.aspose.org/slides/java/api/)
- [Presentation class overview](/blog.aspose.org/slides/java/slides-foss-java/)
- [Key features overview](/blog.aspose.org/slides/java/slides-features/)
- [Create presentations guide](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
- [Work with slides guide](/docs.aspose.org/slides/java/developer-guide/slide-manipulation/)
