---
page_role: howto_article
# Static
layout: "family"
type: "_default"

# Head
head_title: "Aspose.Slides FOSS for Python | Open-Source PowerPoint Library"
head_description: "Aspose.Slides FOSS for Python is a free, open-source library for creating, reading, and editing PowerPoint (.pptx) presentations. MIT licensed, pure Python, requires Python 3.10+."

# Header
title: "Aspose.Slides FOSS for Python"
description: "Create, read, and edit PowerPoint presentations from Python — free and open-source, no Office dependency required."
button:
  enable: true

# Overview
overview:
  enable: true
  content: |
    Aspose.Slides FOSS for Python is a MIT-licensed pure-Python library for working with PowerPoint `.pptx` files. Install it with a single pip command and immediately start creating, reading, and editing presentations without installing Microsoft Office or any proprietary runtime.

    The library exposes a Presentation API built around `Presentation`, `Slide`, `Shape`, `TextFrame`, `Paragraph`, and `Portion` — the conceptual model used by PowerPoint itself. You can add and remove slides, insert AutoShapes, Tables, and Connectors, format text at character level with bold, italic, font size and color, apply solid or gradient fills, add visual effects (shadow, glow, blur, reflection), and work with per-slide speaker notes and threaded comments.

    The context manager pattern ensures reliable resource cleanup: always open a `Presentation` with `with slides.Presentation(...) as prs:`. The only supported save format is PPTX — export to PDF, HTML, SVG, or images is not available in this edition. Unknown XML parts encountered during load are preserved verbatim on save, so round-tripping never destroys content the library does not yet understand.

    Because `aspose-slides-foss` has zero runtime dependencies beyond `lxml` (installed automatically) and supports Python 3.10 and later, it runs identically on Windows, macOS, and Linux CI runners, Docker containers, and serverless functions.

# Testimonials section
testimonialswrapper:
  enable: false

# Support
support:
  enable: true

# Back to top
back_to_top:
  enable: true
---
