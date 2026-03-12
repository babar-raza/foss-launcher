---
page_role: howto_article
title: "Practical Guide: Converting Between 3D Formats in Python"
seoTitle: "Converting Between 3D Formats in Python — OBJ, STL, glTF, 3MF"
description: "Step-by-step guide to converting OBJ, STL, glTF, and 3MF files in Python using Aspose.3D FOSS. Includes batch conversion patterns and format-specific save options."
date: "2026-02-10"
draft: false
author: "Aspose Team"
summary: "Format conversion is a routine task in 3D pipelines. This guide walks through converting between OBJ, STL, glTF/GLB, and 3MF using Aspose.3D FOSS for Python, with a code example for each conversion path and a reusable batch pattern."
tags: ["python", "3d", "gltf", "stl", "obj", "format conversion"]
categories: ["Developer Guides", "3D"]
---

## Introduction

3D content rarely stays in a single format for its entire lifetime. A model may originate as an OBJ file exported from a modelling application, travel through a 3D printing pipeline as STL, appear in a web application as glTF, and end up in an additive manufacturing tool as 3MF. Each format serves a different audience and a different downstream tool, and conversion between them is something most 3D pipelines need to handle reliably.

Python is a natural fit for this work: shell scripts are too fragile, and full DCC (digital content creation) tool integrations are too heavy for batch processing. What you need is a library that can load any of these formats, give you a consistent scene graph, and write back out to any target format without requiring a GUI or a graphics driver.

Aspose.3D FOSS for Python (`aspose-3d-foss`, MIT license) covers that gap. This guide shows the most common conversion paths with complete, runnable code examples.

---

## Which Formats Does Aspose.3D FOSS Support?

| Format | Extension(s) | Load | Save | Common Use Case |
|---|---|:---:|:---:|---|
| Wavefront OBJ | `.obj` | Yes | Yes | Interchange from modelling tools; `.mtl` material files supported |
| STL | `.stl` | Yes | Yes | 3D printing, CAD export; binary and ASCII variants |
| glTF 2.0 / GLB | `.gltf`, `.glb` | Yes | Yes | Web viewers, game engines; GLB is the self-contained binary variant |
| COLLADA | `.dae` | Yes | — | Import from animation tools; write support planned |
| 3MF | `.3mf` | Yes | Yes | Additive manufacturing, richer print metadata than STL |

Format detection is automatic from the file extension. Format-specific option classes (`ObjLoadOptions`, `StlSaveOptions`, `GltfSaveOptions`) are available when you need fine-grained control.

> **Note on FBX:** The library includes a partial FBX tokenizer for import. FBX is not recommended for production conversion workflows in this release; use OBJ or glTF as intermediate formats instead.

---

## OBJ to STL — Preparing a Model for 3D Printing

OBJ is the most common output format from modelling and sculpting tools. STL is the lingua franca of 3D printing slicers. Converting between them is a single call.

```python
from aspose.threed import Scene
from aspose.threed.formats.stl import StlSaveOptions

scene = Scene.from_file("model.obj")

opts = StlSaveOptions()
scene.save("model.stl", opts)
```

STL only encodes triangle faces. If your OBJ file contains quad or n-gon faces, the exporter triangulates them automatically before writing. If you want to control the triangulation explicitly before saving, call `mesh.triangulate()` on each mesh in the scene:

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh
from aspose.threed.formats.stl import StlSaveOptions

scene = Scene.from_file("model.obj")

def triangulate_all(node):
    updated = []
    for entity in node.entities:
        if isinstance(entity, Mesh):
            updated.append(entity.triangulate())
        else:
            updated.append(entity)
    node.entities[:] = updated
    for child in node.child_nodes:
        triangulate_all(child)

triangulate_all(scene.root_node)
scene.save("model_triangulated.stl", StlSaveOptions())
```

---

## OBJ to glTF — Exporting for Web and Game Engines

glTF 2.0 is the preferred interchange format for real-time renderers, WebGL viewers, and game engines such as Babylon.js, Three.js, and Unity. GLB (the binary variant) packages geometry, textures, and materials into a single self-contained file, which is easier to serve over HTTP.

```python
from aspose.threed import Scene
from aspose.threed.formats.gltf import GltfSaveOptions

scene = Scene.from_file("model.obj")

##Save as JSON-based glTF (external buffer)
opts_gltf = GltfSaveOptions()
scene.save("model.gltf", opts_gltf)

##Save as self-contained GLB binary — preferred for web delivery
scene.save("model.glb", GltfSaveOptions())
```

The format is inferred from the file extension: `.gltf` produces the JSON+binary-buffer pair; `.glb` produces the single-file binary. OBJ material data (`LambertMaterial`, `PhongMaterial`) is carried through to the glTF PBR material representation where an equivalent exists.

---

## STL to glTF — From Scanner or CAD Output to Web

STL files from 3D scanners and CAD systems are common inputs that need to be made web-viewable. STL carries only triangle geometry and no material data, so the conversion is straightforward.

```python
from aspose.threed import Scene
from aspose.threed.formats.gltf import GltfSaveOptions

scene = Scene.from_file("scan.stl")
scene.save("scan.glb", GltfSaveOptions())
```

If the STL was produced by a CAD tool with an unusual coordinate system (Z-up vs Y-up), you can inspect and correct the root node transform before saving:

```python
from aspose.threed import Scene
from aspose.threed.formats.gltf import GltfSaveOptions

scene = Scene.from_file("cad_export.stl")

##Rotate 90 degrees around X to convert Z-up to Y-up
root = scene.root_node
root.transform.euler_angles.x = -90.0

scene.save("cad_export_yup.glb", GltfSaveOptions())
```

---

## glTF to 3MF — Preparing for Additive Manufacturing

3MF is a modern 3D printing format backed by the 3MF Consortium. It supports richer metadata than STL — colour, material assignments, build instructions — and is accepted by slicer software such as PrusaSlicer and Bambu Studio. If you are delivering models from a web viewer into a printing workflow, converting GLB to 3MF is a useful step.

```python
from aspose.threed import Scene
from aspose.threed.formats import SaveOptions, FileFormat

scene = Scene.from_file("model.glb")
scene.save("model.3mf")
```

The 3MF format is detected automatically from the `.3mf` extension. For explicit control, pass a `SaveOptions` instance configured for 3MF.

---

## Batch Conversion Pattern

In practice, conversion tasks operate on directories of files rather than individual files. The following pattern handles a folder of OBJ files and converts each one to GLB, with per-file error handling so a single bad file does not abort the entire run.

```python
import os
from aspose.threed import Scene
from aspose.threed.formats.gltf import GltfSaveOptions

input_dir = "./obj_files"
output_dir = "./glb_files"

os.makedirs(output_dir, exist_ok=True)

opts = GltfSaveOptions()
results = {"ok": [], "failed": []}

for filename in os.listdir(input_dir):
    if not filename.lower().endswith(".obj"):
        continue
    src = os.path.join(input_dir, filename)
    stem = os.path.splitext(filename)[0]
    dst = os.path.join(output_dir, stem + ".glb")
    try:
        scene = Scene.from_file(src)
        scene.save(dst, opts)
        results["ok"].append(filename)
        print(f"OK  {filename} -> {stem}.glb")
    except Exception as exc:
        results["failed"].append((filename, str(exc)))
        print(f"ERR {filename}: {exc}")

print(f"\n{len(results['ok'])} converted, {len(results['failed'])} failed.")
if results["failed"]:
    for name, reason in results["failed"]:
        print(f"  {name}: {reason}")
```

This pattern extends naturally to other source/target format pairs: change the extension filter and the `SaveOptions` class for any combination in the support table above.

---

## Conclusion

Aspose.3D FOSS for Python makes format conversion straightforward: load with `Scene.from_file`, optionally inspect or modify the scene graph, then save with the appropriate `SaveOptions`. The library handles triangulation, coordinate normalization, and format-specific quirks internally.

For a full list of classes and methods, see the [API Reference](/reference.aspose.net/3d/python/). To go deeper on the scene graph model — nodes, meshes, transforms — see:

- [Class Scene](/reference.aspose.net/3d/python/scene/) — loading, saving, and scene-level metadata
- [Class Node](/reference.aspose.net/3d/python/node/) — hierarchy, transforms, entity attachment
- [Class Mesh](/reference.aspose.net/3d/python/mesh/) — vertex data, polygons, vertex elements
- [How to Load 3D Models in Python](/kb.aspose.net/3d/python/how-to-load-3d-models-in-python/)
- [PyPI: aspose-3d-foss](https://pypi.org/project/aspose-3d-foss/)
