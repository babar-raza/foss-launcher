---
page_role: howto_article
title: Getting Started
description: >
  Get up and running with Aspose.3D FOSS for Python — prerequisites,
  installation, and your first scene in under five minutes.
type: docs
sidebar:
  open: true
---

##Getting Started with Aspose.3D FOSS for Python

Welcome to **Aspose.3D FOSS for Python** — a free, MIT-licensed library for loading, constructing, and exporting 3D scenes from Python. This guide will take you from a fresh environment to a working scene in a few minutes.

---

## Prerequisites

Before installing, make sure your environment meets these requirements:

### Python Version

- Python **3.7, 3.8, 3.9, 3.10, 3.11, or 3.12**
- CPython is the reference interpreter; all six versions are tested on each release

### Package Manager

- **pip** (bundled with all modern Python installations)
- No other build tools, compilers, or system packages are required

### Operating System

- Windows, macOS, and Linux are all supported
- The library is pure Python — no platform-specific native extension to compile

---

## Installation

Install from PyPI using pip:

```bash
pip install aspose-3d-foss
```

See the [Installation Guide](installation.md) for virtual-environment setup, verification steps, and a quick-start code example.

---

## What You Can Do with Aspose.3D FOSS for Python

Once installed, you can immediately:

- **Load** OBJ (with .mtl material support), STL, glTF 2.0, GLB, COLLADA, and 3MF files
- **Inspect** scene hierarchies — traverse nodes, read meshes, access vertex normals and UVs
- **Transform** scenes — apply positions, rotations (via `Quaternion`), and scales using `Transform`
- **Apply materials** — work with `LambertMaterial` and `PhongMaterial` on scene nodes
- **Export** to any supported format with per-format save options
- **Compute geometry** — query bounding boxes, accumulate world-space transforms with `GlobalTransform`
- **Read animation** — access `AnimationClip` and `KeyframeSequence` data from loaded glTF and COLLADA files

---

## Quick Start

The following code loads a scene file, prints the root node's children, and resaves the scene in GLB format:

```python
from aspose.threed import Scene

scene = Scene.from_file("input.obj")

print(f"Root node children: {len(scene.root_node.child_nodes)}")
for node in scene.root_node.child_nodes:
    entity_type = type(node.entity).__name__ if node.entity else "no entity"
    print(f"  {node.name} [{entity_type}]")

scene.save("output.glb")
print("Saved output.glb")
```

---

## Next Steps

- **[Installation Guide](installation.md)** — Virtual environment setup, pip install, and verification
- **[Developer Guide](/docs.aspose.org/3d/python/developer-guide/)** — Complete API reference, format support details, and code examples
- **[Features and Functionalities](/docs.aspose.org/3d/python/developer-guide/features/)** — Deep-dive into every feature area with working Python examples
