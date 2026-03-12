<!-- GOLDEN REFERENCE | Source: slides/en/getting-started/_index.md | Original-Grade: A- -->
---
title: Getting Started
description: >
  This comprehensive guide helps you get started with Aspose.Slides for .NET —
  from installation to presentation processing basics.
type: docs
sidebar:
  open: true
---

# Getting Started with Aspose.Slides Plugins for .NET

Welcome to the **Aspose.Slides for .NET** Getting Started Guide!
This quick introduction will help you install, configure, and start using our powerful API
for working with PowerPoint presentations programmatically.

---

## System Requirements

Ensure your environment meets the minimum requirements:

### Supported Frameworks
* .NET 6.0 or later
* .NET Framework 4.0+
* Mono

### Supported Operating Systems
* Windows (x64)
* Linux (x64)
* macOS (x64, ARM64)

Full system requirements:
https://docs.aspose.net/slides/getting-started/

---

## Installation

### Install via NuGet (recommended)

1. Open your .NET project in Visual Studio or other IDE
2. Right-click the project > **Manage NuGet Packages**
3. Search for: **Aspose.Slides.NET**
4. Install the package

**Package Manager Console**

```ps
Install-Package Aspose.Slides.NET
```

**.NET CLI**

```bash
dotnet add package Aspose.Slides.NET
```

---

## What You Can Do with Aspose.Slides Plugins

Out-of-the-box presentation automation features include:

* Load and save PowerPoint files (`.pptx`, `.ppt`, `.odp`, `.potx`)
* Create new presentations programmatically
* Add and modify slides, shapes, images, charts, and media
* Convert presentations to PDF, HTML, images, and SVG
* Merge presentations or clone slides
* Extract text and media from slides
* Generate slide thumbnails and high-quality rendering
* Export presentations to video (with transitions/timings)

---

## Basic Example

Here's a simple example that loads a presentation and saves it as PDF:

```csharp
using Aspose.Slides;
using Aspose.Slides.LowCode;
using Aspose.Slides.Export;

// Load and convert presentation
using (var presentation = new Presentation("input.ppt"))
{
    presentation.Save("output.pptx", SaveFormat.Pptx);
}
```

---

## Next Steps

Continue learning with these resources:

* **Installation Guide:** Proper licensing + deployment
* **Developer Guide:** Practical programming tutorials
* **API Reference:** Full namespace/class documentation
