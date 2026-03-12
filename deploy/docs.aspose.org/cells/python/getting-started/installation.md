---
page_role: howto_article
title: Installation
description: >-
  Learn how to install Aspose.Cells FOSS for Python using pip, set up a virtual
  environment, verify the installation, and install optional plugins.
weight: 11
type: docs
---

## Installation of Aspose.Cells FOSS for Python

Aspose.Cells FOSS for Python is distributed as a standard Python package on PyPI under the name **`aspose-cells-foss`**. The recommended installation method is `pip`, which handles all dependencies automatically.

---

### 1. pip (Recommended)

pip is the standard way to install Aspose.Cells FOSS for Python. No additional tools or build steps are required.

**Install the latest version:**

```bash
pip install aspose-cells-foss
```

**Install a specific version:**

```bash
pip install aspose-cells-foss==26.3.0
```

**Upgrade an existing installation:**

```bash
pip install --upgrade aspose-cells-foss
```

---

### 2. Virtual Environment (Recommended for Projects)

Using a virtual environment isolates your project dependencies from the system Python installation.

**Create and activate a virtual environment:**

```bash
##Create
python -m venv .venv

##Activate on Linux/macOS
source .venv/bin/activate

##Activate on Windows
.venv\Scripts\activate

##Install
pip install aspose-cells-foss
```

---

### 3. Verify the Installation

After installing, run the following snippet to confirm the library loads correctly:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
workbook.worksheets[0].cells["A1"].value = "Installation verified!"
workbook.save("verify.xlsx")
print("Aspose.Cells FOSS for Python is installed correctly.")
```

If the file `verify.xlsx` is created without errors, the installation is complete. The import uses `aspose_cells` (underscore, not dot).

---

### 4. System Requirements

| Requirement | Details |
|---|---|
| Python version | 3.7 or later (3.9–3.13 recommended) |
| Operating system | Windows x86/x64, Linux (Ubuntu, CentOS, etc.), macOS x64/ARM64 |
| Microsoft Office | Not required |
| pip dependencies | `pycryptodome>=3.15.0`, `olefile>=0.46` (auto-installed) |

---

### 5. Package Name vs. Import Name

| Context | Name |
|---|---|
| PyPI / pip install | `aspose-cells-foss` |
| Python import | `from aspose_cells import ...` |

The pip package name uses a hyphen (`aspose-cells-foss`) while the Python import uses an underscore (`aspose_cells`). This follows the standard Python packaging convention.

---

### 6. Plugin Installation

#### markitdown-aspose-cells-plugin

Extends Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) library with support for XLSX, XLS, and ODS formats:

```bash
pip install markitdown-aspose-cells-plugin
```

Usage:

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert("spreadsheet.xlsx")
print(result.text_content)  # Spreadsheet data as Markdown tables
```

---

## Additional Resources

- [Aspose.Cells FOSS for Python — PyPI](https://pypi.org/project/aspose-cells-foss/)
- [GitHub Repository](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python)
- [Aspose.Cells FOSS for Python — Developer Guide](https://docs.aspose.org/cells/python/developer-guide/)
- [Aspose.Cells FOSS for Python — API Reference](https://reference.aspose.org/cells/python/)
- [Knowledge Base](https://kb.aspose.org/cells/python/) — Task-oriented how-to guides
- [Product Overview](https://products.aspose.org/cells/python/) — Features and capabilities summary
- [Blog: Introducing Aspose.Cells FOSS](https://blog.aspose.org/cells/python/introducing-cells-foss-python/) — Library overview and quick start
- [Free Support Forum](https://forum.aspose.com/c/cells)
