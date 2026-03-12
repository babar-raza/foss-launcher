---
canonical: https://kb.aspose.org/3d/python/convert-fbx-gltf-python/
canonical_import: aspose_3d_foss
date: '2026-03-11T12:10:17Z'
dateModified: '2026-03-11T12:10:17Z'
datePublished: '2026-03-11T12:10:17Z'
description: Aspose.3D enables this via the `Scene` class and `FileFormat` static
  methods like `WAVEFRONT_OBJ()` and `GLTF2()` to load and `save` models programmatically.
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
lastmod: '2026-03-11T12:10:17Z'
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.3D | Guide
slug: convert-fbx-gltf-python
title: How to Convert File Formats with Aspose.3D
type: howto_article
url: /kb.aspose.org/3d/python/convert-fbx-gltf-python/
weight: 13
---

## Problem

Developers building 3d python game, 3d python visualization, or python 3d engine projects often need to convert 3D models between `formats` such as OBJ and glTF 2.0. Aspose.3D enables this via the `Scene` class and `FileFormat` static methods like `WAVEFRONT_OBJ()` and `GLTF2()` to load and `save` models programmatically.

## Prerequisites

Aspose.3D -- Required installation and input file.

- Python 3.7+ (or the supported runtime for python)
- Install via pip: `pip install aspose-3d-foss`

```python
import aspose.threed
```

## Conversion Steps

Aspose.3D enables format conversion for 3D assets in Python workflows. Use the `Scene` class to load source files, configure export settings via `create_save_options()`, and write output in `target` `formats` such as OBJ, glTF 2.0, or 3MF using `FileFormat` constants.

### Step 1: Load Source File

Initialize a `Scene` object and load the input file using its constructor. This populates the `scene` graph with `entities`, nodes, and geometry from the source format.

```python
import aspose.threed

scene = aspose.threed.Scene('input.fbx')
```

### Step 2: Configure Save Options

Create `save` options using the plugin's `create_save_options()` method. Set `properties` such as compression behavior to control how the output file is generated.

```python
options = scene.get_plugin().create_save_options()
options.enable_compression = False
```

### Step 3: Save to Target Format

Call `save()` on the `Scene` instance with the output path and selected `FileFormat` constant to export the 3D content in the desired format.

```python
scene.save('output.obj', aspose.threed.FileFormat.WAVEFRONT_OBJ())
```

## Code Example

This example demonstrates loading a 3D `scene` and saving it in a different format using Aspose.3D. It uses the `Scene` class to load an input file and the `FileFormat` class to specify the `target` format for export.

```python
# Example usage
import aspose.threed
# See API reference for complete examples
```

## Supported Formats

Aspose.3D supports conversion between multiple 3D file `formats` using the `FileFormat` class and related APIs. Developers can leverage this capability in python 3d game, python 3d engine, and python 3d visualization workflows.

| Format | Extension | Notes |
|--------|-----------|-------|
| Wavefront OBJ | .obj | Supported via `FileFormat.WAVEFRONT_OBJ()` |
| glTF 2.0 | .gltf, .glb | Supported via `FileFormat.GLTF2()` |
| Microsoft 3MF | .3mf | Supported via `FileFormat.MICROSOFT_3MF_FORMAT()` |
| FBX 7.4 ASCII | .fbx | Supported via `FileFormat.FBX7400ASCII()` |

## See Also

Aspose.3D provides classes like `Scene`, `Mesh`, `Node`, and `FileFormat` to support 3D python game development, python 3d visualization, and python 3d engine workflows. The `library` enables conversion between common 3D `formats` such as OBJ, `GLTF2`, 3MF, and FBX.

- [Aspose.3D FAQ](/kb.aspose.org/3d/python/faq/)
- [Camera and light objects](/blog.aspose.org/3d/python/3d-key-features/)
- [Camera and light objects](/blog.aspose.org/3d/python/3d-foss-python/)
- [Load Files with Aspose.3D](/docs.aspose.org/3d/python/developer-guide/model-loading/)
- [Render 3D Models with Aspose.3D](/docs.aspose.org/3d/python/developer-guide/rendering/)
