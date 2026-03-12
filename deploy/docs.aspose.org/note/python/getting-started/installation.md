---
page_role: howto_article
title: Installation
description: >-
  Install Aspose.Note FOSS for Python from PyPI using pip. Covers the core install,
  the optional PDF export dependency, editable installs for contributors, and virtual
  environment best practices.
weight: 11
type: docs
---

## Installation of Aspose.Note FOSS for Python

Aspose.Note FOSS for Python is distributed via [PyPI](https://pypi.org/project/aspose-note/) under the package name `aspose-note`. Installation requires Python 3.10 or later.

---

### 1. Standard Install (Recommended)

Install the core library with pip:

```bash
pip install aspose-note
```

This installs the `aspose.note` package with no optional dependencies. It supports all reading and traversal features. PDF export is **not** included.

---

### 2. Install with PDF Export Support

To enable `Document.Save(..., SaveFormat.Pdf)`, install with the `[pdf]` extra. This adds the [ReportLab](https://www.reportlab.com/) dependency (`reportlab>=3.6`):

```bash
pip install "aspose-note[pdf]"
```

If you have already installed the core package, upgrade it and add the extra in one command:

```bash
pip install --upgrade "aspose-note[pdf]"
```

> **Note**: Attempting to call `Document.Save` with `SaveFormat.Pdf` without ReportLab installed will raise an `ImportError` at runtime. Install the `[pdf]` extra before using PDF functionality.

---

### 3. Virtual Environment (Best Practice)

Use a virtual environment to isolate the library from your system Python:

```bash
##Create a virtual environment
python -m venv .venv

##Activate it
##Windows:
.venv\Scripts\activate
##Linux / macOS:
source .venv/bin/activate

##Install (with PDF support)
pip install "aspose-note[pdf]"
```

---

### 4. Editable Install (For Contributors)

Clone the repository and install in editable mode to develop or run tests against the source:

```bash
git clone https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python.git
cd Aspose.Note-FOSS-for-Python

##Editable install with PDF support
pip install -e ".[pdf]"

##Run the test suite
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Verification

After installation, verify that the package is importable:

```python
from aspose.note import Document, SaveFormat, FileFormat
print("Aspose.Note FOSS for Python installed successfully.")
```

Check the installed version:

```bash
pip show aspose-note
```

Expected output (version may differ):

```
Name: aspose-note
Version: 26.2
Summary: Aspose.Note-compatible Python API for reading OneNote (.one) files
...
```

---

## Dependencies

| Dependency | Required? | Purpose |
|---|---|---|
| Python 3.10+ | Always | Minimum language version |
| `reportlab>=3.6` | Optional (via `[pdf]` extra) | PDF export via `Document.Save(..., SaveFormat.Pdf)` |

The core library has **zero mandatory third-party dependencies**. All MS-ONE/OneStore binary parsing is implemented in pure Python within the `aspose.note._internal` subpackage.

---

## Package Details

| Attribute | Value |
|---|---|
| Package name | `aspose-note` |
| PyPI URL | https://pypi.org/project/aspose-note/ |
| Import path | `from aspose.note import ...` |
| Version (current) | 26.2 |
| Python support | 3.10, 3.11, 3.12 |
| Operating systems | Windows, Linux, macOS (OS-independent) |
| License | MIT (Aspose-Split) |
| Source repository | https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python |

---

## Additional Resources

- [Aspose.Note FOSS for Python — PyPI](https://pypi.org/project/aspose-note/)
- [Source Repository](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python)
- [Report Issues](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/issues)
- [Developer Guide](../developer-guide/)
- [API Reference](https://reference.aspose.org/note/python/)
