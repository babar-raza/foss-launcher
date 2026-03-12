---
page_role: howto_article
title: Installation
description: >-
  Install Aspose.3D FOSS for Python via pip, verify the installation,
  set up a virtual environment, and run your first scene-loading script.
weight: 11
type: docs
---

## Installation of Aspose.3D FOSS for Python

Aspose.3D FOSS for Python is distributed as a pure-Python package on PyPI. It has **zero external dependencies** — no native extensions to compile, no system libraries to install, and no Microsoft Office or other third-party runtime required.

---

### Prerequisites

| Requirement | Detail |
|-------------|--------|
| Python version | 3.7, 3.8, 3.9, 3.10, 3.11, or 3.12 |
| Package manager | pip (bundled with CPython) |
| Operating system | Windows, macOS, Linux (any platform that runs CPython) |
| Compiler / build tools | None required |
| System packages | None required |

---

### 1. Install via pip (Recommended)

The simplest way to install Aspose.3D FOSS is directly from PyPI:

```bash
pip install aspose-3d-foss
```

pip will download and install the package and record it in your environment. No post-install configuration is needed.

To install a pinned version for reproducible builds:

```bash
pip install aspose-3d-foss==26.1.0
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
pip install aspose-3d-foss
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

After installing, verify that the library imports correctly:

```python
from aspose.threed import Scene

scene = Scene()
print("Aspose.3D FOSS installed successfully")
print(f"Root node name: {scene.root_node.name}")
```

Expected output:

```
Aspose.3D FOSS installed successfully
Root node name: RootNode
```

You can also check the installed version with pip:

```bash
pip show aspose-3d-foss
```

This will print the version, author, and license (MIT).

---

### Quick Start: Load a Scene and Inspect It

The following script loads a 3D file, prints information about every mesh node, and re-exports the scene to GLB format:

```python
from aspose.threed import Scene
from aspose.threed.formats.obj import ObjLoadOptions

##Load an OBJ file with material support
options = ObjLoadOptions()
options.enable_materials = True
options.flip_coordinate_system = False

scene = Scene()
scene.open("model.obj", options)

##Print the scene hierarchy
print(f"Top-level nodes: {len(scene.root_node.child_nodes)}")

for node in scene.root_node.child_nodes:
    if node.entity is None:
        continue
    mesh = node.entity
    print(f"  Node: {node.name}")
    print(f"    Vertices: {len(mesh.control_points)}")
    print(f"    Polygons: {len(mesh.polygons)}")
    if node.material:
        print(f"    Material: {type(node.material).__name__}")

##Re-export to GLB (binary glTF)
scene.save("output.glb")
print("Saved output.glb")
```

If you do not yet have an OBJ file, the library can also create a scene from scratch:

```python
from aspose.threed import Scene

##Create an empty scene and save it as glTF
scene = Scene()
scene.save("empty.gltf")
print("Created empty.gltf")
```

---

### Platform Notes

**Windows, macOS, Linux:** The library is identical on all platforms. There are no platform-specific code paths or binary extensions.

**Docker / serverless:** Because there are no system-package dependencies, the library works inside slim Docker images (such as `python:3.12-slim`) without installing any additional apt or yum packages.

**CI/CD:** Add `pip install aspose-3d-foss` to your CI pipeline's dependency step. No additional setup is required.

**Conda:** If your project uses Conda, install the library from PyPI inside a Conda environment:

```bash
conda create -n my-env python=3.12
conda activate my-env
pip install aspose-3d-foss
```

---

### Additional Resources

- [Product Page](https://products.aspose.net/3d/python/) — Overview, feature summary, and testimonials
- [Developer Guide](/docs.aspose.org/3d/python/developer-guide/) — Complete API reference with code examples
- [Features and Functionalities](/docs.aspose.org/3d/python/developer-guide/features/) — Format support, scene graph, materials, math utilities, and more
