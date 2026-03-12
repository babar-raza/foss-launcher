---
page_role: howto_article
title: "Introducing Aspose.3D FOSS for Python"
seoTitle: "Aspose.3D FOSS for Python — Open-Source 3D File Processing Library"
description: "Aspose.3D FOSS for Python is a zero-dependency, MIT-licensed library for loading and converting OBJ, STL, glTF, COLLADA, and 3MF files in pure Python."
date: "2026-01-15"
draft: false
author: "Aspose Team"
summary: "We are releasing Aspose.3D FOSS for Python — a pure-Python, MIT-licensed library for reading and writing common 3D file formats with no external dependencies."
tags: ["3d", "python", "open source", "foss", "obj", "stl", "gltf", "collada", "3mf", "aspose"]
categories: ["Aspose.3D", "Release Announcements", "Python"]
---

## Introduction

We are releasing **Aspose.3D FOSS for Python** — a pure-Python library for reading, writing, and converting common 3D file formats. The library is published on PyPI as [`aspose-3d-foss`](https://pypi.org/project/aspose-3d-foss/), carries an MIT license, and has zero external dependencies.

If you have ever needed to inspect or convert 3D files programmatically — extract mesh vertex counts, pipe OBJ geometry into a processing script, or batch-convert STL files to glTF for a web viewer — this library is built for that use case. It does not require a graphics driver, a native extension module, or any cloud connection.

---

## What's Included

### Core Scene Graph

Every file is loaded into a `Scene` object that mirrors the original file's node hierarchy. Nodes carry `Transform` (translation, rotation, scale) and one or more attached entities such as `Mesh`, `Camera`, or `Light`. The scene graph is the same regardless of source format, so code written to walk and process geometry works across all supported formats without modification.

### Geometry Access

`Mesh` objects expose:

- `control_points` — list of vertex positions as `Vector4` (x, y, z, w)
- `polygons` — list of face index lists (arbitrary polygon arity, not just triangles)
- `get_element(VertexElementType)` — retrieves named vertex data layers for normals, UVs, vertex colours, and smoothing groups

### Materials

`LambertMaterial` and `PhongMaterial` carry the material properties read from OBJ `.mtl` files (ambient, diffuse, specular, emissive, transparency, shininess). Materials survive the load–save round trip for formats that support them.

### Math Utilities

`Vector2`, `Vector3`, `Vector4`, `FVector3`, `Quaternion`, `Matrix4`, and `BoundingBox` are included as lightweight value types for geometry calculations.

### Animation

The `AnimationClip`, `AnimationNode`, `KeyframeSequence`, and `KeyFrame` classes provide access to keyframe animation data from formats that carry it, such as glTF and COLLADA.

---

## Quick Start

```bash
pip install aspose-3d-foss
```

Load a 3D file and print the vertex count of every mesh:

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh

scene = Scene.from_file("model.obj")

def visit(node):
    for entity in node.entities:
        if isinstance(entity, Mesh):
            print(f"{node.name}: {len(entity.control_points)} vertices, "
                  f"{len(entity.polygons)} polygons")
    for child in node.child_nodes:
        visit(child)

visit(scene.root_node)
```

Convert the same file to glTF:

```python
from aspose.threed import Scene
from aspose.threed.formats import GltfSaveOptions

scene = Scene.from_file("model.obj")
scene.save("model.gltf", GltfSaveOptions())
```

That is the complete program. No configuration files, no API keys, no network calls.

---

## Supported Formats

| Format | Extension(s) | Load | Save | Notes |
|---|---|:---:|:---:|---|
| Wavefront OBJ | `.obj` | Yes | Yes | `.mtl` material loading supported |
| STL | `.stl` | Yes | Yes | Binary and ASCII; coordinate-system flip option |
| glTF 2.0 | `.gltf`, `.glb` | Yes | Yes | GLB (self-contained binary) supported |
| COLLADA | `.dae` | Yes | — | Write support planned |
| 3MF | `.3mf` | Yes | Yes | Suitable for 3D printing workflows |
| FBX | `.fbx` | Partial | — | Tokenizer only; full parser in progress |

Format detection is automatic from the file extension. Format-specific load and save options (`ObjLoadOptions`, `StlSaveOptions`, `GltfSaveOptions`, `ThreeMfSaveOptions`) are available for fine-grained control.

---

## Open Source and Free

The library is MIT licensed. You can use it in commercial applications, modify it, and redistribute it without restriction. The source is available on GitHub under the Aspose organisation.

There are no usage tiers, no token limits, and no telemetry. The library performs all processing locally.

**Dependencies**: none. The package installs as a pure-Python wheel with no C extensions and no third-party runtime requirements.

---

## Getting Started

- **Install**: `pip install aspose-3d-foss`
- **How-to: Loading files** — [How to Load 3D Models in Python](/kb.aspose.net/3d/python/how-to-load-3d-models-in-python/)
- **How-to: Converting files** — [How to Convert 3D Models in Python](/kb.aspose.net/3d/python/how-to-convert-3d-models-in-python/)
- **API Reference** — [Aspose.3D FOSS for Python API Reference](/reference.aspose.net/3d/python/)
- **PyPI** — [aspose-3d-foss on PyPI](https://pypi.org/project/aspose-3d-foss/)

---

## Conclusion

Aspose.3D FOSS for Python 26.1.0 covers the most common 3D file formats used in tooling, pipelines, and web applications — OBJ, STL, glTF, COLLADA, and 3MF — with a consistent Python API and no installation friction. If you encounter a bug, an unsupported edge case, or a format you need added, please open an issue on GitHub. We actively maintain the library and welcome contributions.
