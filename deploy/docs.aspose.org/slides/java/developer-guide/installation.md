---
canonical: https://docs.aspose.org/slides/java/developer-guide/installation/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: 'Aspose.Slides FOSS for Java: Code example demonstrates usage of AdjustValue'
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
seoTitle: Aspose.Slides FOSS Installation
slug: installation
summary: ''
title: Installation
type: workflow_page
url: /docs.aspose.org/slides/java/developer-guide/installation/
weight: 3
---

## Overview

Aspose.Slides FOSS for Java -- Introductory overview: explain what the library does, its primary use cases, and what readers will accomplish. Mention the product name in the first sentence..

Aspose.Slides FOSS for Java Code example demonstrates usage of AdjustValue.

```java
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.concurrent.atomic.AtomicBoolean;
import static org.assertj.core.api.Assertions.assertThat;

Element gd = createGdElement("adj1", "val 50000");
        var adj = new AdjustValue(gd, null);
```

```java
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.concurrent.atomic.AtomicBoolean;
import static org.assertj.core.api.Assertions.assertThat;

Element gd = doc.createElementNS(NS_A, "a:gd");
        doc.appendChild(gd);
        var adj = new AdjustValue(gd, null);
```

## Key Features

Aspose.Slides FOSS for Java enables developers to generate, modify, and convert PowerPoint presentations programmatically using pure Java. This section outlines the core capabilities you’ll use daily when building presentation automation workflows.

- Apply solid, gradient, pattern, and picture fills to shapes using `FillFormat` to enhance visual appeal and branding consistency.
- Adjust shape geometry dynamically with `AdjustValue` to fine-tune effects like corner rounding or arrowhead size without manual editing.
- Add realistic lighting and depth effects using `PresetShadow` to create professional slide elements with minimal code.
- Combine multiple visual layers using `FillOverlay` to blend fills for advanced styling while preserving source integrity.
- Create and manipulate tables with precise cell, row, and column control for structured data presentation.
- Format text at the portion, paragraph, and text frame levels using `BasePortionFormat` and `BulletFormat` for consistent typography.

## Prerequisites

Aspose.Slides FOSS for Java -- Required setup and dependencies.

```java
import org.aspose.slides.foss.FillBlendMode;
import org.aspose.slides.foss.FillType;
import org.aspose.slides.foss.IPresentationComponent;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;

var fo = new FillOverlay(fillOverlayElement, null);
        IImageTransformOperation result = fo.asIImageTransformOperation();
```

```java
import org.aspose.slides.foss.FillBlendMode;
import org.aspose.slides.foss.FillType;
import org.aspose.slides.foss.IPresentationComponent;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;

var fo = new FillOverlay(fillOverlayElement, null);
        IPresentationComponent result = fo.asIPresentationComponent();
```

## Code Examples

This guide walks you through installing Aspose.Slides FOSS for Java and applying visual effects to shapes in a presentation. You will install the library using Maven, create a new presentation, add a rectangle shape, and apply three image transform operations: `AdjustValue`, `FillOverlay`, and `PresetShadow`. Each operation modifies how the shape appears when rendered.

```java
import com.aspose.slides.*;
import com.aspose.slides.foss.drawing.Color;
import com.aspose.slides.foss.export.SaveFormat;
import com.aspose.slides.foss.effects.PresetShadowType;
import org.w3c.dom.Element;
import javax.xml.parsers.DocumentBuilderFactory;

try (Presentation prs = new Presentation()) {
    IAutoShape shape = prs.getSlides().get(0).getShapes()
            .addAutoShape(ShapeType.RECTANGLE, 50, 50, 300, 150);

    // Apply solid fill
    shape.getFillFormat().setFillType(FillType.SOLID);
    shape.getFillFormat().getSolidFillColor().setColor(Color.fromArgb(255, 100, 150, 200));

    // Add shadow effect
    var shadow = new PresetShadow(shape.getEffectFormat().getEffectLayers().add(), null);
    shadow.setPreset(PresetShadowType.BOTTOM_RIGHT_DROP_SHADOW);

    // Add fill overlay
    var fo = new FillOverlay(shape.getEffectFormat().getEffectLayers().add(), null);
    fo.setBlend(FillBlendMode.MULTIPLY);

    // Add adjust value (e.g., for shape geometry modification)
    var adj = new AdjustValue(shape.getEffectFormat().getEffectLayers().add(), null);
    adj.setValue(50000);

    prs.save("effects.pptx", SaveFormat.PPTX);
}
```

- Use `AdjustValue` when you need to programmatically adjust shape geometry parameters such as corner rounding or arrowhead size.
- Apply `FillOverlay` to blend multiple fills using modes like MULTIPLY or OVERLAY for advanced visual effects.
- Set `PresetShadow` to add standardized drop shadows that match PowerPoint's built-in shadow styles.

The Maven command installs the FOSS artifact directly into your local repository. After installation, the example above creates a new presentation, adds a rectangle, and applies three image transform operations using the `EffectFormat` API. Each operation is added to the effect layer collection and configured with specific parameters.

{{< callout >}}
Ensure your project uses the canonical import path `com.aspose.slides.*`. Avoid .NET-style `using` directives or incorrect package names.
{{< /callout >}}

## Best Practices

This section outlines best practices for using Aspose.Slides FOSS for Java in production workflows. Always install the library using the official Maven artifact to ensure compatibility and access to verified APIs.

- Use `import com.aspose.slides.*;` — never use alternative package paths or .NET-style directives.
- Apply `FillFormat` and `FillOverlay` only after confirming shape type supports fill effects (e.g., `AutoShape`, `PictureFrame`).
- Validate `AdjustValue` parameters before applying to avoid runtime exceptions; values must be within the expected 0–100,000 range.
- Use `PresetShadow` with `PresetShadowType` constants only; custom shadow definitions are not supported in this FOSS version.

When applying visual effects like shadows or overlays, always test output fidelity across platforms. The `PresetShadow` class supports only predefined shadow types, and `FillOverlay` blending requires compatible fill types on both base and overlay layers.

For text formatting, chain `FillFormat` and `PortionFormat` calls only after confirming the `TextFrame` and `Paragraph` objects exist. Use `AdjustValue` to control shape-specific parameters like aspect ratio or corner rounding, but validate input values before assignment.

## Troubleshooting

Aspose.Slides FOSS for Java -- Common issues and solutions.

For details on troubleshooting, see the Aspose.Slides FOSS for Java documentation.

## FAQ

Aspose.Slides FOSS for Java -- Section content.

## API Reference Summary

Aspose.Slides FOSS for Java -- Section content.

For details on api reference summary, see the Aspose.Slides FOSS for Java documentation.

## See Also

To deepen your understanding of Aspose.Slides FOSS for Java, explore how core formatting and effect classes like `AdjustValue`, `FillFormat`, `FillOverlay`, and `PresetShadow` integrate into real workflows. Each class is designed for precise XML-backed manipulation of slide content, as demonstrated in the test examples.

- [Learn the basics and first steps](/docs.aspose.org/slides/java/developer-guide/started/)
- [Browse the complete API reference](/reference.aspose.org/slides/java/api/)
- [See how to open existing presentations](/blog.aspose.org/slides/java/slides-foss-java/)
- [Discover key features and capabilities](/blog.aspose.org/slides/java/slides-features/)
- [Step-by-step guide to create presentations](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
