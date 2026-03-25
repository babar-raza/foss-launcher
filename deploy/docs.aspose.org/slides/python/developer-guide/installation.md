---
canonical: https://docs.aspose.org/slides/python/developer-guide/installation/
canonical_import: aspose.slides
code_import: aspose.slides
date: '2026-03-24T16:56:57Z'
dateModified: '2026-03-24T16:56:57Z'
datePublished: '2026-03-24T16:56:57Z'
description: This guide walks you through installing Aspose.Slides and verifying your
  setup to begin building slides, adding shapes, and exporting to formats like PDF
  or...
display_name: Aspose.Slides
family: slides
keywords:
- slides python
- python slides for beginners
- python slides ppt
- python slides pdf
- slide python pptx
- python slides for kids
- python slides library
- python slides github
lastmod: '2026-03-24T16:56:57Z'
page_role: workflow_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Slides Installation
slug: installation
summary: ''
title: Installation
type: workflow_page
url: /docs.aspose.org/slides/python/developer-guide/installation/
weight: 3
---

## Overview

Aspose.Slides for Python enables developers to create, edit, and convert PowerPoint presentations programmatically. This guide walks you through installing Aspose.Slides and verifying your setup to begin building slides, adding shapes, and exporting to formats like PDF or PPTX.

Install Aspose.Slides using pip with the command `pip install aspose-slides-foss>=26.3.2`. The library requires Python 3.10 or later and automatically installs lxml as `a` dependency. After installation, import the package using `import aspose.slides` to access all presentation processing capabilities.

```python
import aspose.slides as slides
from aspose.slides import SaveFormat

# Create a new presentation
with slides.Presentation() as prs:
    # Access the first slide
    slide = prs.slides[0]
    # Add a rectangle shape
    shape = slide.shapes.add_auto_shape(slides.ShapeType.RECTANGLE, 50, 50, 300, 100)
    # Add text to the shape
    shape.add_text_frame("Hello, world!")
    # Save as PPTX
    prs.save("output.pptx", SaveFormat.PPTX)
```

- Use this approach when generating dynamic slide decks from data sources.
- Use this approach when creating templates for reports or presentations.
- Use this approach when building slide-based content for archival or distribution.

## Key Features

This guide walks you through installing and verifying Aspose.Slides for Python to begin building, modifying, and converting PowerPoint presentations programmatically. Aspose.Slides enables you to create, edit, and export slides in Python without requiring Microsoft PowerPoint, supporting formats like PPTX and PDF.

```shell
pip install aspose-slides-foss>=26.3.2
```

After installation, ensure your environment meets the minimum requirement: Python 3.10 or later. The library automatically installs lxml as `a` dependency during setup. Verify the installation by importing the package and creating `a` new presentation object.

```python
import aspose.slides as slides
from aspose.slides import SaveFormat

# Create a new presentation
with slides.Presentation() as prs:
    # Access the first slide
    slide = prs.slides[0]
    # Add a rectangle shape
    shape = slide.shapes.add_auto_shape(slides.ShapeType.RECTANGLE, 50, 50, 300, 100)
    # Add text to the shape
    shape.add_text_frame("Welcome to Aspose.Slides")
    # Save as PPTX
    prs.save("output.pptx", SaveFormat.PPTX)
```

- Use this approach when generating dynamic slide decks from data sources like CSV or JSON.
- Leverage the `Presentation` constructor to build presentations from scratch without external templates.
- Call save() with `SaveFormat.PPTX` to ensure full fidelity for PowerPoint 2007+ clients.

## Prerequisites

This guide walks you through installing Aspose.Slides for Python to begin creating, editing, and converting PowerPoint presentations programmatically. You will set up the library, verify your environment, and prepare to build slides workflows in Python.

- Install Aspose.Slides via: `pip install aspose-slides-foss>=26.3.2`
- Ensure Python 3.10 or later is installed
- The library automatically installs lxml as a dependency

```python
import aspose.slides

# Verify installation by importing the library
print(f"Aspose.Slides version: {aspose.slides.__version__}")
```

## Code Examples

Aspose.Slides -- Runnable code examples.

The following example demonstrates how to get started with Aspose.Slides.

```python
import aspose.slides

# Initialize — see the aspose.slides API reference for available classes
```

## Best Practices

This section covers essential best practices for installing and using Aspose.Slides in Python projects. Ensure your environment meets the minimum requirements before proceeding.

- Install Aspose.Slides using `pip install aspose-slides-foss>=26.3.2` to get the latest stable version.
- Verify your Python version is 3.10 or higher, as the library does not support earlier versions.
- Confirm lxml is installed automatically — it is a required transitive dependency.
- Avoid mixing Aspose.Slides with unrelated Aspose libraries (e.g., `aspose.cells`) to prevent import conflicts.

After installation, always use the canonical import `import aspose.slides` — never alias it or substitute another path. This ensures compatibility with the documented API surface and avoids runtime errors from incorrect module resolution.

{{< callout >}}
If you encounter `ModuleNotFoundError` after installation, check that your `pip` targets the correct Python 3.10+ interpreter and that no virtual environment isolation is blocking the package.
{{< /callout >}}

## Troubleshooting

This section helps you resolve common issues when installing and using Aspose.Slides for Python. The library installs via pip and requires Python 3.10+ with lxml as `a` dependency; most problems arise from version mismatches, incorrect imports, or missing system libraries.

Ensure you install the correct package using the exact command: `pip install aspose-slides-foss>=26.3.2`. Using `aspose-slides` (without `-foss`) or an older version may cause runtime errors or missing features. Also verify your Python version with `python --version` before installing.

If you see `ModuleNotFoundError: No module named 'aspose.slides'`, confirm that the installation completed successfully and that you are using the correct Python environment (e.`g`., virtual environment or system interpreter). Run `pip show aspose-slides-foss` to verify the package is installed and its version.

```python
import aspose.slides
print(f"Aspose.Slides version: {aspose.slides.__version__}")
```

- Use this check after installation to confirm the correct package is loaded.
- Run this in the same environment where your application executes to avoid path conflicts.
- Verify the version is ≥26.3.2 to ensure compatibility with documented features.

If your script fails with `ImportError: cannot import name 'Presentation' from 'aspose.slides'`, double-check that you did not alias the import incorrectly (e.`g`., `import aspose.slides as slides` is acceptable, but `import aspose.slides` is invalid and will break the workflow). Always use `import aspose.slides` as the canonical import.

On Linux systems, missing system libraries like libgdiplus can cause failures when rendering shapes or `images`. Install them using your package `manager` (e.`g`., `sudo apt-get install libgdiplus` on Debian/Ubuntu) to resolve such issues.

If lxml fails to install during `pip install aspose-slides-foss`, ensure `python3-dev` and `libxml2-dev` are present. Aspose.Slides depends on lxml for XML processing, and missing build dependencies prevent successful installation.

```python
import aspose.slides
from aspose.slides import Presentation, SaveFormat

with Presentation() as prs:
    slide = prs.slides[0]
    slide.shapes.add_auto_shape(1, 50, 50, 200, 50)
    prs.save("test.pptx", SaveFormat.PPTX)
```

- This snippet validates that both the core library and its XML dependency (lxml) are correctly installed.
- Use it to test shape creation and file output after installation.
- If this fails, re-run `pip install --force-reinstall aspose-slides-foss>=26.3.2` and retry.

## FAQ

### How do I install Aspose.Slides for Python?

Install Aspose.Slides using pip with the command `pip install aspose-slides-foss>=26.3.2`. The library requires Python 3.10 or later and automatically installs lxml as `a` dependency during setup.

### Can I use Aspose.Slides with older Python versions?

No. Aspose.Slides for Python requires Python 3.10 or newer. Attempting to install or run on earlier versions will result in compatibility errors.

### What happens if I install the wrong package?

Using an incorrect package such as `aspose.cells` or any non-`aspose.slides` variant will not provide PowerPoint functionality and may cause import errors. Always use `import aspose.slides` and install `aspose-slides-foss>=26.3.2`.

## API Reference Summary

Aspose.Slides -- Section content.

For details on api reference summary, see the Aspose.Slides documentation.

## See Also

- [Get started with Aspose.Slides](/docs.aspose.org/slides/python/developer-guide/getting-started/)
- [View full API documentation](/reference.aspose.org/slides/python/api-overview/)
- [Explore 3D shape formatting support](/blog.aspose.org/slides/python/introducing-slides-foss-python/)
- [Discover key features of the library](/blog.aspose.org/slides/python/slides-key-features/)
- [Create presentations step by step](/docs.aspose.org/slides/python/developer-guide/presentation-creation/)
