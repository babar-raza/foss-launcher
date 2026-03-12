---
page_role: howto_article
title: Installation
description: >-
  Install Aspose.Slides FOSS for Python via pip, verify the installation,
  set up a virtual environment, and run your first presentation-creation script.
weight: 11
type: docs
---

## Installation of Aspose.Slides FOSS for Python

Aspose.Slides FOSS for Python is distributed as a pure-Python package on PyPI. Its only external dependency is `lxml`, which pip installs automatically — no native extensions to compile, no system libraries to install, and no Microsoft Office or other proprietary runtime required.

---

### Prerequisites

| Requirement | Detail |
|-------------|--------|
| Python version | 3.10 or later |
| Package manager | pip (bundled with CPython) |
| Operating system | Windows, macOS, Linux (any platform that runs CPython) |
| Compiler / build tools | None required |
| Automatic dependency | `lxml` (installed by pip automatically) |

---

### 1. Install via pip (Recommended)

The simplest way to install Aspose.Slides FOSS is directly from PyPI:

```bash
pip install aspose-slides-foss
```

pip downloads and installs the package along with the `lxml` dependency. No post-install configuration is needed.

To install a pinned version for reproducible builds:

```bash
pip install aspose-slides-foss==26.3.0
```

---

### 2. Set Up a Virtual Environment (Recommended for Projects)

Using a virtual environment keeps the library isolated from other Python projects and avoids version conflicts.

**Create and activate a virtual environment:**

```bash
##Create the environment
python -m venv .venv

##Activate on Linux / macOS
source .venv/bin/activate

##Activate on Windows (Command Prompt)
.venv\Scripts\activate.bat

##Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

**Install the library inside the activated environment:**

```bash
pip install aspose-slides-foss
```

**Record dependencies for reproducibility:**

```bash
pip freeze > requirements.txt
```

To recreate the environment on another machine:

```bash
python -m venv .venv
source .venv/bin/activate   # or the Windows equivalent
pip install -r requirements.txt
```

---

### 3. Verify the Installation

After installing, verify that the library imports correctly and a `Presentation` can be created:

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    print("Aspose.Slides FOSS installed successfully")
    print(f"Slides in empty presentation: {len(prs.slides)}")
```

Expected output:

```
Aspose.Slides FOSS installed successfully
Slides in empty presentation: 1
```

You can also check the installed version with pip:

```bash
pip show aspose-slides-foss
```

This prints the version, author, and license (`MIT`).

---

### Quick Start: Create a Presentation with a Shape

The following script creates a new presentation, adds a rectangle with text, and saves it as a `.pptx` file:

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat
from aspose.slides_foss import ShapeType

with slides.Presentation() as prs:
    slide = prs.slides[0]

    ##Add a rectangle shape and set its text
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 400, 150)
    shape.add_text_frame("Hello from Aspose.Slides FOSS!")

    prs.save("hello.pptx", SaveFormat.PPTX)

print("Saved hello.pptx")
```

**Important:** Always use `Presentation` as a context manager (`with` statement). This ensures proper cleanup of internal resources when the block exits.

---

### Platform Notes

**Windows, macOS, Linux:** The library is identical on all platforms. There are no platform-specific code paths or binary extensions beyond `lxml`.

**Docker / serverless:** The library works inside slim Docker images (such as `python:3.12-slim`) with `pip install aspose-slides-foss`. No additional apt or yum packages are required unless `lxml` needs to compile from source (the PyPI wheel covers common architectures).

**CI/CD:** Add `pip install aspose-slides-foss` to your CI pipeline's dependency step. No additional setup is required.

**Conda:** If your project uses Conda, install the library from PyPI inside a Conda environment:

```bash
conda create -n slides-env python=3.12
conda activate slides-env
pip install aspose-slides-foss
```

---

### Additional Resources

- [Product Page](/products.aspose.org/slides/python/) — Overview, feature summary, and quick start
- [License](/docs.aspose.org/slides/python/getting-started/license/) — MIT License details, no API key required
- [Developer Guide](/docs.aspose.org/slides/python/developer-guide/) — Feature guides with code examples
- [API Reference](/reference.aspose.org/slides/python/) — Class and method reference
