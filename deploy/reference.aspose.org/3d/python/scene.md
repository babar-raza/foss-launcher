---
canonical: https://reference.aspose.org/3d/python/scene/
canonical_import: aspose.threed
date: '2026-03-12T15:45:33Z'
dateModified: '2026-03-12T15:45:33Z'
datePublished: '2026-03-12T15:45:33Z'
description: It provides methods to load, manipulate, and `save` 3D content across
  supported `formats` like OBJ, GLTF, STL, and 3MF.
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
lastmod: '2026-03-12T15:45:33Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D Scene
slug: scene
title: Scene
type: reference_object_page
url: /reference.aspose.org/3d/python/scene/
weight: 22
---

## Overview

The `Scene` class in Aspose.3D represents a 3D `scene` container that holds a hierarchy of nodes, `entities`, and assets. It provides methods to load, manipulate, and `save` 3D content across supported `formats` like OBJ, GLTF, STL, and 3MF.

```python
import aspose.threed

scene = aspose.threed.Scene()
scene.open("model.fbx")
```

## Constructor

The `Scene` class in Aspose.3D provides a container for 3D scenes and supports loading, manipulation, and saving of 3D content. It is the primary entry point for working with 3D models in python 3d visualization and python 3d game workflows.

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | Default constructor initializes an empty `scene` |
| file_path | str | Path to a 3D file to load (used with `open()` after construction) |
| options | [identifier omitted] | Optional load configuration (e.g., [identifier omitted]) |
| stream | io._IOBase | Binary stream containing 3D data |
| format | `FileFormat` | Explicit file format hint when loading from stream |
| parent | `SceneObject` | Internal parent reference (not for public use) |

```python
import aspose.threed

scene = aspose.threed.Scene()
```

## Properties

The `Scene` class in Aspose.3D provides access to core 3D `scene` data through its read-only `properties`. These `properties` expose the root node, asset metadata, and animation clips associated with the loaded 3D content.

| Name | Type | Description |
|------|------|-------------|
| `root_node` | `Node` | The top-level node of the `scene` hierarchy. |
| `asset_info` | `AssetInfo` | Metadata about the 3D file, such as `title`, `author`, and `revision`. |
| `animations` | `List[AnimationClip]` | List of animation clips defined in the `scene`. |
| nodes | `List[Node]` | All nodes contained in the `scene`, including nested children. |
| objects | `List[SceneObject]` | All `scene` objects (`entities`) referenced directly or indirectly. |

```python
import aspose.threed

scene = aspose.threed.Scene()
# After loading a file, inspect root node and asset info
print(scene.root_node.name)
print(scene.asset_info.author)
```

## Methods

Aspose.3D -- Method table: signature, return type, description.

For details on methods, see the Aspose.3D documentation.

## Example

The `Scene` class in Aspose.3D serves as the root container for 3D scenes, supporting loading, manipulation, and saving of 3D content. It integrates with core classes like `Node`, `Entity`, `Geometry`, and `FileFormat` to enable python 3d visualization and python 3d game development workflows.

```python
import aspose.threed as a3d

# Create a new scene and add a root node
scene = a3d.Scene()
node = scene.root_node

# Assign a file format for export (e.g., GLTF2)
format = a3d.FileFormat.GLTF2()
print(f"Export format: {format.extension}")
```

## See Also

The `Scene` class serves as the root container for 3D content in Aspose.3D, supporting import, export, and manipulation of 3D scenes for python 3d visualization and python 3d game development workflows. Related classes include `Node`, `Entity`, `Camera`, and `AnimationClip` for building structured 3D scenes.

```python
import aspose.threed

scene = aspose.threed.Scene()
node = scene.root_node
```

- [Explore 3D key features](/blog.aspose.org/3d/python/3d-key-features/)
- [Introducing 3D FOSS Python](/blog.aspose.org/3d/python/3d-foss-python/)
- [Load files with Aspose.3D](/docs.aspose.org/3d/python/developer-guide/model-loading/)
- [Convert file formats guide](/kb.aspose.org/3d/python/convert-collada-fbx-python/)
- [Fix common errors](/kb.aspose.org/3d/python/fix-3d-models-errors-python/)
