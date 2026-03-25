---
canonical: https://kb.aspose.org/slides/java/convert-png-pptx-java/
canonical_import: com.aspose.slides
code_import: com.aspose.slides
date: '2026-03-24T17:06:48Z'
dateModified: '2026-03-24T17:06:48Z'
datePublished: '2026-03-24T17:06:48Z'
description: The `Presentation` class loads source files, and its save() method writes
  output in the target format.
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
page_role: howto_article
platform: java
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.Slides FOSS for Java | Guide
slug: convert-png-pptx-java
title: How to Convert File Formats with Aspose.Slides FOSS for Java
type: howto_article
url: /kb.aspose.org/slides/java/convert-png-pptx-java/
weight: 13
---

## Problem

You will convert presentation files between supported formats—such as PPTX to PDF or PPTX to image formats—using Aspose.Slides FOSS for Java. The `Presentation` class loads source files, and its save() method writes output in the target format.

## Prerequisites

You will convert presentation files between supported formats using Aspose.Slides FOSS for Java. Ensure your environment meets the following requirements before proceeding.

- Java Development Kit (JDK) version 8 or higher
- Aspose.Slides FOSS for Java library installed via Maven or JAR
- Input presentation file in `.pptx` format

## Conversion Steps

You will load `a` presentation file and save it to another format using Aspose.Slides FOSS for Java. The conversion process uses the `Presentation` class to open source files and the save() method to write output in supported formats such as PPTX, PDF, and image formats.

- Java Development Kit (JDK) 8 or later
- Aspose.Slides FOSS for Java library JAR in your classpath

### Step 1: Load Source `Presentation`

Create `a` `Presentation` object by passing the path to your source file. This loads the entire presentation into memory for processing.

```java
import com.aspose.slides.*;

Presentation pres = new Presentation("input.pptx");
```

This returns `a` `Presentation` instance ready for format conversion.

### Step 2: Save to Target Format

Call save() on the `Presentation` object with the output file path and desired format. Supported output formats include PPTX, PDF, and image formats like PNG or JPEG.

```java
pres.save("output.pdf", SaveFormat.Pdf);
```

This writes the converted file to disk in the specified format.

### Step 3: Release Resources

Call `dispose()` on the `Presentation` object to free native resources and ensure clean shutdown.

```java
pres.dispose();
```

This step prevents memory leaks in long-running applications.

### Code Breakdown

The `Presentation` constructor loads the source file. The save() method handles format conversion internally using built-in exporters. The `dispose()` method ensures proper cleanup of internal resources.

### Error Handling

Wrap conversion logic in `a` try-catch block to handle Exception types such as IllegalArgumentException for invalid paths or IOException for write failures.

```java
try {
    Presentation pres = new Presentation("input.pptx");
    pres.save("output.pdf", SaveFormat.Pdf);
    pres.dispose();
} catch (Exception e) {
    System.err.println("Conversion failed: " + e.getMessage());
}
```

### Next Steps

Learn how to convert slides to images or batch-process multiple presentations in the related guides.

## Code Example

You will load `a` PowerPoint presentation file and save it in `a` different format using Aspose.Slides FOSS for Java. The example demonstrates converting `a` .pptx file to another supported format by leveraging the `Presentation` class and its save() method.

- Java Development Kit (JDK) 8 or later installed
- Aspose.Slides FOSS for Java library added to your project classpath

### Load and Save `a` `Presentation`

Step 1: Load the source presentation file. Use the `Presentation` class constructor to open the .pptx file.

```java
import com.aspose.slides.*;

Presentation pres = new Presentation("input.pptx");
```

This returns `a` `Presentation` object containing all slides, shapes, and formatting from the source file.

### Convert to Target Format

Step 2: Save the presentation in the desired output format. Call save() with the output file path and format.

```java
pres.save("output.pdf", SaveFormat.Pdf);
```

This writes the converted file to disk in the specified format. Supported output formats include PDF, XPS, and image formats such as PNG and JPEG.

### Error Handling

Wrap file I/O operations in `a` try-catch block to handle IOException and Exception explicitly. The `Presentation` constructor and save() method may throw these exceptions on invalid paths or unsupported formats.

```java
try {
    Presentation pres = new Presentation("input.pptx");
    pres.save("output.pdf", SaveFormat.Pdf);
} catch (IOException e) {
    System.err.println("File I/O error: " + e.getMessage());
} catch (Exception e) {
    System.err.println("Conversion error: " + e.getMessage());
}
```

This ensures robust handling of malformed input files or missing dependencies during conversion.

## Supported Formats

Aspose.Slides FOSS for Java supports conversion between major presentation file formats. You can load and save presentations in formats including PPTX, PPT, PPSX, PPS, POTX, POT, PPTM, PPSM, POTM, ODP, OTP, and PDF.

| Format | Extension | Notes |
|--------|-----------|-------|
| PowerPoint Open XML | .pptx | Default format for PowerPoint 2007 and later |
| PowerPoint Macro-Enabled | .pptm | Supports macros |
| PowerPoint 97-2003 | .ppt | Legacy binary format |
| PowerPoint Show | .pps | Runs as `a` slideshow |
| PowerPoint XML | .xml | XML-based format |
| PowerPoint Template | .potx | Template format |
| PowerPoint Macro-Enabled Template | .potm | Template with macros |
| OpenDocument `Presentation` | .odp | Open standard format |
| OpenDocument Template | .otp | Template for ODP |
| PDF | .pdf | Portable `Document` Format |
| SVG | .svg | Scalable Vector Graphics |
| XPS | .xps | XML Paper Specification |
| HTML | .html | Web page format |
| MHTML | .mht | Web archive format |
| TIFF | .tiff | Tagged `Image` File Format |
| JPEG | .jpg | JPEG image |
| PNG | .png | Portable Network Graphics |
| BMP | .bmp | Bitmap image |
| EMF | .emf | Enhanced Metafile |
| WMF | .wmf | Windows Metafile |
| EPUB | .epub | Electronic publication |
| FODP | .fodp | Flat OpenDocument `Presentation`

## See Also

Aspose.Slides FOSS for Java -- Related conversion guides and format documentation.

For details on see also, see the Aspose.Slides FOSS for Java documentation.

- [Frequently asked questions and answers](/kb.aspose.org/slides/java/faq/)
- [Announcement about Presentation class support](/blog.aspose.org/slides/java/slides-foss-java/)
- [Key features overview for presentations](/blog.aspose.org/slides/java/slides-features/)
- [Step-by-step guide to create presentations](/docs.aspose.org/slides/java/developer-guide/presentation-creation/)
- [Detailed workflow for working with slides](/docs.aspose.org/slides/java/developer-guide/slide-manipulation/)
