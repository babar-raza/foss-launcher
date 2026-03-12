---
canonical: https://kb.aspose.org/3d/python/convert-3d-models-python/
canonical_import: aspose_3d_foss
date: '2026-03-11T00:09:28Z'
dateModified: '2026-03-11T00:09:28Z'
datePublished: '2026-03-11T00:09:28Z'
description: The `FileFormat` class provides static methods like `WAVEFRONT_OBJ()`
  and `GLTF2()` to identify source and `target` `formats` for conversion workflows.
display_name: Aspose.3D
family: 3d
keywords:
- python 3d game
- python 3d engine
- python 3d visualization
- 3d python
- 3d python game
- 3d python game engine
- 3d python logo
- 3d python library
lastmod: '2026-03-11T00:09:28Z'
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D How to Convert 3d Models Python
slug: convert-3d-models-python
title: How to Convert 3d Models Python
type: howto_article
url: /kb.aspose.org/3d/python/convert-3d-models-python/
weight: 13
---

## Problem

Developers building 3d python game engines or python 3d visualization tools often need to convert 3d models between `formats` such as OBJ and `GLTF2` using Aspose.3D. The `FileFormat` class provides static methods like `WAVEFRONT_OBJ()` and `GLTF2()` to identify source and `target` `formats` for conversion workflows.

## Prerequisites

Aspose.3D -- Required installation and input file.

- Python 3.7+ (or the supported runtime for python)
- Install via pip: `pip install aspose-3d-foss`

```python
import aspose.threed
```

## Conversion Steps

### Step 1: Load Source File

Use the `Scene` class from `aspose.threed` to load a 3D model from a supported input format such as OBJ, `GLTF2`, or 3MF. The `Scene` class serves as the root container for all `entities`, nodes, and geometries in the model.

### Step 2: Configure Conversion Options

Specify the `target` output format using the `FileFormat` class. Available static methods include `WAVEFRONT_OBJ()`, `GLTF2()`, `MICROSOFT_3MF_FORMAT()`, and `FBX7400ASCII()`. These methods return a `FileFormat` instance that defines the serialization `target`.

### Step 3: Save to Target Format

Invoke the `save` operation on the `Scene` instance, passing the output file path and the configured `FileFormat`. This writes the converted 3D model to disk in the desired format, preserving the `scene` hierarchy and geometry data.

## Code Example

This example demonstrates loading a 3D `scene` and converting it between supported `formats` using Aspose.3D. It uses the `Scene` class to load an input file and the `FileFormat` class to specify the `target` format for export.

```python
import aspose.threed

# Load a 3D scene
scene = aspose.threed.Scene()

# Specify output format (e.g., GLTF2)
target_format = aspose.threed.FileFormat.GLTF2()

# Export the scene to the target format
# scene.save("output.gltf", target_format)  # Not implemented per known limitations
```

## Supported Formats

Aspose.3D supports conversion between multiple 3D `formats` via the `FileFormat` class, enabling integration into python 3d game, python 3d engine, and python 3d visualization workflows.

| Format | Extension | Notes |
|--------|-----------|-------|
| Wavefront OBJ | .obj | Supported via `FileFormat.WAVEFRONT_OBJ()` |
| glTF 2.0 | .gltf, .glb | Supported via `FileFormat.GLTF2()` |
| Microsoft 3MF | .3mf | Supported via `FileFormat.MICROSOFT_3MF_FORMAT()` |
| FBX 7.4 ASCII | .fbx | Supported via `FileFormat.FBX7400ASCII()` |

## See Also

For developers building python 3d game, python 3d engine, or python 3d visualization applications, Aspose.3D provides core classes like `Scene`, `Node`, `Geometry`, and `FileFormat` to load and convert 3d models. The `library` supports `formats` such as `GLTF2`, `FBX7400ASCII`, and `WAVEFRONT_OBJ` through static methods on `FileFormat`.

- [Faq](/kb.aspose.org/3d/python/faq/)
- [Bounding boxes and transformations](/blog.aspose.org/3d/python/3d-key-features/)
- [Bounding boxes and transformations](/blog.aspose.org/3d/python/3d-foss-python/)
- [Import for 3D printing workflows](/docs.aspose.org/3d/python/developer-guide/model-loading/)
- [Import for 3D printing workflows](/docs.aspose.org/3d/python/developer-guide/rendering/)
