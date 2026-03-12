---
canonical: https://reference.aspose.org/3d/python/node/
canonical_import: aspose.threed
date: '2026-03-12T15:45:33Z'
dateModified: '2026-03-12T15:45:33Z'
datePublished: '2026-03-12T15:45:33Z'
description: It serves as the foundational building block for constructing 3D scenes
  in python 3d visualization and python 3d game engine workflows.
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
seoTitle: Aspose.3D Node
slug: node
title: Node
type: reference_object_page
url: /reference.aspose.org/3d/python/node/
weight: 21
---

## Overview

The `Node` class in Aspose.3D represents a transformable object in a 3D `scene` hierarchy, supporting parent-child relationships, `entity` attachment, and global transformation computation. It serves as the foundational building block for constructing 3D scenes in python 3d visualization and python 3d game engine workflows.

## Constructor

The `Node` class in Aspose.3D represents a `transform` node in a 3D `scene` hierarchy. It supports parent-child relationships, `entity` association, and `scene` graph traversal for python 3d visualization and game development workflows.

```python
import aspose.threed

node = aspose.threed.Node()
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Optional `name` for the node |
| parent | `Node` | Optional parent node to attach to |
| `entity` | `Entity` | Optional `entity` to associate with the node |

## Properties

The `Node` class in Aspose.3D represents a transformable object in a 3D `scene` hierarchy. It inherits from `Entity` and provides access to `scene` graph relationships, local and global transforms, and child nodes.

| Name | Type | Description |
|------|------|-------------|
| `name` | str (read-only) | The `name` of the node. |
| `parent_node` | `Node` (read-only) | The parent node in the `scene` graph. |
| `parent_nodes` | List[`Node`] (read-only) | List of parent nodes (typically one unless instanced). |
| `child_nodes` | List[`Node`] (read-only) | List of child nodes attached to this node. |
| local_transform | `GlobalTransform` (read-only) | Local transformation including `translation`, `rotation`, and `scale`. |
| `global_transform` | `GlobalTransform` (read-only) | World-space transformation matrix and derived values. |
| `excluded` | bool (read-only) | Indicates whether the node is `excluded` from rendering. |
| `properties` | `PropertyCollection` (read-only) | Custom metadata `properties` attached to the node. |
| `entity` | `Entity` (read-only) | The geometric or logical `entity` bound to this node. |
| `scene` | `Scene` (read-only) | The `scene` that contains this node. |

## Methods

The `Node` class in Aspose.3D represents a `transform` node in a 3D `scene` hierarchy. It supports `scene` graph operations including parent-child relationships, bounding volume computation, and `entity` attachment. Methods exposed by `Node` align with the `Entity` base class and extend functionality for `scene` traversal and rendering control.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `parent_node(value: Optional['Node'])` | None | Sets the parent node of this node. |
| `excluded(value: bool)` | None | Sets whether this node is `excluded` from rendering. |
| `get_bounding_box()` | [identifier omitted] | Computes the axis-aligned bounding box of the node and its children. |
| `get_entity_renderer_key()` | str | Returns a unique key used by the renderer to identify this `entity`. |
| `name(value: str)` | None | Sets the `name` of the node. |
| `find_property(property_name: str)` | `Property` | Finds a `property` by `name`. |
| `get_property(property: str)` | Any | Gets the `value` of a `property` by `name`. |
| `set_property(property: str, value)` | None | Sets a `property` `value` by `name`. |
| `remove_property(property)` | None | Removes a `property` by `name` or reference. |
| `parent_nodes` | List['`Node`'] (read-only) | Returns the list of parent nodes. |
| `parent_node` | Optional['`Node`'] (read-only) | Returns the parent node. |
| `excluded` | bool (read-only) | Returns whether the node is `excluded` from rendering. |
| `name` | str (read-only) | Returns the `name` of the node. |
| `properties` | `PropertyCollection` (read-only) | Returns the collection of custom `properties`. |
| `child_nodes` | List['`Node`'] (read-only) | Returns the list of child nodes. |
| `transform` | `GlobalTransform` (read-only) | Returns the global transformation matrix. |
| local_transform | `GlobalTransform` (read-only) | Returns the local transformation matrix. |
| `visible` | bool (read-only) | Returns whether the node is `visible`. |
| `visible(value: bool)` | None | Sets whether the node is `visible`. |
| `cast_shadows(value: bool)` | None | Sets whether the node casts shadows. |
| `receive_shadows(value: bool)` | None | Sets whether the node receives shadows. |
| `cast_shadows` | bool (read-only) | Returns whether the node casts shadows. |
| `receive_shadows` | bool (read-only) | Returns whether the node receives shadows. |
| geometry | `Geometry` (read-only) | Returns the attached geometry, if any. |
| `geometry(value: Geometry)` | None | Attaches a geometry to this node. |
| `material` | Material (read-only) | Returns the attached `material`, if any. |
| `material(value: Material)` | None | Attaches a `material` to this node. |
| light | `Light` (read-only) | Returns the attached light, if any. |
| `light(value: Light)` | None | Attaches a light to this node. |
| camera | `Camera` (read-only) | Returns the attached camera, if any. |
| `camera(value: Camera)` | None | Attaches a camera to this node. |
| `find_node(name: str)` | Optional['`Node`'] | Finds a descendant node by `name`. |
| get_child_nodes() | List['`Node`'] (read-only) | Returns the list of child nodes. |
| `remove_child_node(node: 'Node')` | None | Removes a child node from this node. |
| `add_child_node(node: 'Node')` | None | Adds a child node to this node. |
| clone() | '`Node`' | Creates a shallow copy of the node. |
| `clone(recursive: bool)` | '`Node`' | Creates a copy of the node, optionally cloning children. |

## Example

The `Node` class in Aspose.3D represents a transformable object in a 3D `scene` hierarchy. It supports parent-child relationships, `entity` attachment, and global transformation computation via `GlobalTransform`. This example demonstrates creating a node, attaching a `Mesh` `entity`, and accessing its global `transform` for python 3d visualization workflows.

```python
import aspose.threed as a3d

# Create a new scene and node
scene = a3d.Scene()
node = a3d.Node()
scene.root_node.child_nodes.add(node)

# Attach a mesh entity to the node
mesh = a3d.Mesh()
node.entity = mesh

# Access the node's global transform
evaluate_global_transform = node.evaluate_global_transform

# Extract translation and rotation from the transform
translation = evaluate_global_transform.translation
rotation = evaluate_global_transform.rotation
```

## See Also

The `Node` class in Aspose.3D represents a transformable object in a 3D `scene` hierarchy. It supports parent-child relationships, `entity` association, and global transformation computation via `GlobalTransform`. Related classes include `Scene`, `Entity`, `Camera`, and `AnimationNode` for `scene` management and animation binding.

```python
import aspose.threed

scene = aspose.threed.Scene()
node = scene.root_node
entity = aspose.threed.Mesh()
node.entity = entity
```

- [Explore 3D key features](/blog.aspose.org/3d/python/3d-key-features/)
- [Introducing 3D FOSS Python](/blog.aspose.org/3d/python/3d-foss-python/)
- [Load files with Aspose.3D](/docs.aspose.org/3d/python/developer-guide/model-loading/)
- [Convert file formats guide](/kb.aspose.org/3d/python/convert-collada-fbx-python/)
- [Fix common errors](/kb.aspose.org/3d/python/fix-3d-models-errors-python/)
