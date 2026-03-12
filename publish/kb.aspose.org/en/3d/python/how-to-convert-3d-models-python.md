---
canonical: https://kb.aspose.org/3d/python/convert-3d-models-python/
canonical_import: aspose.threed
date: '2026-03-11T00:09:28Z'
dateModified: '2026-03-11T00:09:28Z'
datePublished: '2026-03-11T00:09:28Z'
description: Learn how to convert 3D models between formats such as OBJ, glTF, STL,
  and 3MF in Python using Aspose.3D's Scene.from_file() and scene.save() API.
display_name: Aspose.3D
family: 3d
keywords:
- aspose 3d python convert
- python convert obj to gltf
- python convert 3d model
- aspose threed file format
- python scene save
- python 3d format conversion
lastmod: '2026-03-11T00:09:28Z'
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Convert 3D Models with Aspose.3D for Python
slug: convert-3d-models-python
title: How to Convert 3D Models with Aspose.3D for Python
type: howto_article
url: /kb.aspose.org/3d/python/convert-3d-models-python/
weight: 13
---

## Problem

Developers working with 3D assets in Python often need to convert models between formats — for example from OBJ to glTF binary, or from STL to 3MF. Aspose.3D handles this with two calls: `Scene.from_file()` to load the source file and `scene.save()` to write the output in the desired format.

## Prerequisites

- Python 3.7 or later
- Install via pip: `pip install aspose-3d-foss`

```python
from aspose.threed import Scene, FileFormat
```

## Conversion Steps

### Step 1: Load the Source File

Use `Scene.from_file()` to load any supported input format. The method detects the format from the file extension automatically.

```python
from aspose.threed import Scene

scene = Scene.from_file("model.obj")
```

To pass load options (for example to control coordinate system flipping when loading OBJ), provide an options object as the second argument:

```python
from aspose.threed import Scene
from aspose.threed.formats import ObjLoadOptions

options = ObjLoadOptions()
options.flip_coordinate_system = False

scene = Scene.from_file("model.obj", options)
```

### Step 2: Save to the Target Format

Call `scene.save()` with the output file path. The format is inferred from the file extension, or you can pass a `FileFormat` constant explicitly for unambiguous control.

```python
from aspose.threed import FileFormat

# Save as binary glTF (.glb) — compact and widely supported
scene.save("output.glb", FileFormat.GLTF2_BINARY)

# Save as STL
scene.save("output.stl")

# Save as 3MF
scene.save("output.3mf")
```

### Step 3: Use Save Options for Fine-Grained Control

For glTF output you can use `GltfSaveOptions` to control binary mode and other settings:

```python
from aspose.threed.formats import GltfSaveOptions

opts = GltfSaveOptions()
opts.binary_mode = True
scene.save("output.glb", opts)
```

## Code Example

Complete example: load an OBJ file and convert it to binary glTF.

```python
from aspose.threed import Scene, FileFormat

# Step 1: load the source model
scene = Scene.from_file("model.obj")

# Step 2: save to binary glTF
scene.save("model.glb", FileFormat.GLTF2_BINARY)

print("Conversion complete: model.obj -> model.glb")
```

## Supported Formats

Aspose.3D supports conversion between multiple 3D formats.

| Format | Extension | Notes |
|--------|-----------|-------|
| Wavefront OBJ | .obj | Load and save supported |
| glTF 2.0 binary | .glb | Compact binary format; use `FileFormat.GLTF2_BINARY` |
| glTF 2.0 JSON | .gltf | Use `FileFormat.GLTF2` |
| Microsoft 3MF | .3mf | Load and save supported |
| STL | .stl | Load and save supported |
| FBX | .fbx | Load supported for basic geometry (limited); see FBX note below |

**Note on FBX:** Aspose.3D FOSS has limited FBX support. Loading basic geometry from FBX files works in most cases, but writing to FBX is not fully supported. Use glTF or OBJ as the preferred output format.

## See Also

- [How to Load 3D Files](/kb.aspose.org/3d/python/load-3d-models-python/)
- [Bounding boxes and transformations](/blog.aspose.org/3d/python/3d-key-features/)
- [Import for 3D printing workflows](/docs.aspose.org/3d/python/developer-guide/model-loading/)
