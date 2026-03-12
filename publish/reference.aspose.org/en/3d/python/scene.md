---
canonical: https://reference.aspose.org/3d/python/scene/
canonical_import: aspose.threed
date: '2026-03-11T00:09:28Z'
dateModified: '2026-03-11T00:09:28Z'
datePublished: '2026-03-11T00:09:28Z'
description: The Scene class is the root container for 3D content in Aspose.3D for
  Python. It provides access to the root node hierarchy and enables loading, constructing,
  and saving 3D scenes.
display_name: Aspose.3D
family: 3d
keywords:
- aspose threed Scene class
- python Scene from_file
- aspose 3d python scene reference
- python 3d scene root_node
- aspose threed scene save
lastmod: '2026-03-11T00:09:28Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D Scene Class Reference — Python
slug: scene
title: Scene
type: reference_object_page
url: /reference.aspose.org/3d/python/scene/
weight: 20
---

## Overview

The `Scene` class in Aspose.3D serves as the root container for 3D content, managing top-level objects and enabling parent/child relationship management for the scene hierarchy. It provides access to root nodes and sub-scenes, forming the entry point for loading, constructing, and saving 3D scenes.

```python
from aspose.threed import Scene

# Create an empty scene
scene = Scene()

# Access the root node — root_node is a property, not a method call
root = scene.root_node
```

## Constructor

The `Scene` class can be instantiated with no arguments to create an empty scene, or with optional parameters to configure the initial state.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Optional name of the scene |
| `file_format` | `FileFormat` | Optional file format for serialization |
| `asset_info` | `AssetInfo` | Optional asset metadata |
| `root_node` | `Node` | Optional root node to initialize the scene hierarchy |

```python
from aspose.threed import Scene

# Empty scene
scene = Scene()

# Access the root node (property, not a method)
root = scene.root_node
```

## Class Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `Scene.from_file(file_path)` | `Scene` | Loads a scene from the specified file path, detecting the format automatically. |
| `Scene.from_file(file_path, options)` | `Scene` | Loads a scene with format-specific load options. |

```python
from aspose.threed import Scene
from aspose.threed.formats import ObjLoadOptions

# Load from file (format detected from extension)
scene = Scene.from_file("model.obj")

# Load with options
opts = ObjLoadOptions()
scene = Scene.from_file("model.obj", opts)
```

## Properties

`root_node` and other scene-level attributes are **properties** — access them without parentheses.

| Name | Type | Description |
|------|------|-------------|
| `root_node` | `Node` | Root node of the scene hierarchy. Access as a property: `scene.root_node` |
| `sub_scenes` | `list[Scene]` | Sub-scenes nested within this scene |
| `asset_info` | `AssetInfo` | Asset metadata such as author, creation date, and units |
| `animations` | `list[AnimationClip]` | Animation clips defined in the scene |
| `name` | `str` | Name of the scene object |
| `properties` | `PropertyCollection` | Custom properties attached to the scene |

## Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `save(file_path)` | `None` | Saves the scene to a file; format inferred from extension |
| `save(file_path, format)` | `None` | Saves the scene to a file in the specified `FileFormat` |
| `save(file_path, options)` | `None` | Saves the scene using format-specific save options |
| `find_node(name)` | `Optional[Node]` | Finds a node by name in the scene hierarchy |
| `get_property(name)` | `Any` | Gets a property value by name |
| `find_property(name)` | `Optional[Property]` | Finds a property by name |
| `clear()` | `None` | Clears all content from the scene |

**Note:** `root_node` is a **property** on the `Scene` class, not a method. Do not write `scene.root_node()` — the correct access is `scene.root_node`.

## Example

Create a scene, add a mesh node, and save to GLB:

```python
from aspose.threed import Scene, FileFormat
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector4

# Create scene and mesh
scene = Scene()
mesh = Mesh()
mesh.control_points.append(Vector4(0, 0, 0, 1))
mesh.control_points.append(Vector4(1, 0, 0, 1))
mesh.control_points.append(Vector4(0.5, 1, 0, 1))
mesh.create_polygon(0, 1, 2)

# Add node to root — root_node is a property
node = scene.root_node.create_child_node("triangle", mesh)

# Save
scene.save("triangle.glb", FileFormat.GLTF2_BINARY)
```

## See Also

- [API reference overview](/reference.aspose.org/3d/python/api-overview/)
- [Node class reference](/reference.aspose.org/3d/python/node/)
- [3D printing workflow import](/docs.aspose.org/3d/python/developer-guide/model-loading/)
- [Convert 3D models with Python](/kb.aspose.org/3d/python/convert-3d-models-python/)
