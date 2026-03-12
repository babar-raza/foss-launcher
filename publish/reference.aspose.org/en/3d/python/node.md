---
canonical: https://reference.aspose.org/3d/python/node/
canonical_import: aspose.threed
date: '2026-03-11T12:10:17Z'
dateModified: '2026-03-11T12:10:17Z'
datePublished: '2026-03-11T12:10:17Z'
description: The Node class represents a named element in the Aspose.3D scene graph.
  It holds an Entity, maintains parent-child relationships, and carries a local transform.
display_name: Aspose.3D
family: 3d
keywords:
- aspose threed Node class
- python 3d scene node
- aspose threed child_nodes
- python node entity scene graph
- aspose 3d node reference
lastmod: '2026-03-11T12:10:17Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D Node Class Reference — Python
slug: node
title: Node
type: reference_object_page
url: /reference.aspose.org/3d/python/node/
weight: 21
---

## Overview

The `Node` class represents a named element in the Aspose.3D scene graph. Each node can hold one `Entity` (such as a `Mesh`, `Camera`, or `Light`), maintains parent-child relationships with other nodes, and carries a local transform. Nodes are the primary way to organize 3D objects in a scene hierarchy.

```python
from aspose.threed import Scene, Node

scene = Scene()

# Access the root node — root_node is a property on Scene
root = scene.root_node

# Create a child node
child = root.create_child_node("my_node")

# child_nodes is a property — access without parentheses
for node in root.child_nodes:
    print(node.name)
```

## Constructor

The `Node` constructor initializes a node with an optional name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Optional name for the node |

## Properties

All node attributes below are **properties** — access them without parentheses.

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | Human-readable identifier for the node |
| `entity` | `Entity` or `None` | The entity attached to this node (e.g., `Mesh`, `Camera`, `Light`) |
| `child_nodes` | `list[Node]` | List of child nodes. Use `child_nodes` — not `children` |
| `parent_node` | `Optional[Node]` | Immediate parent node in the scene hierarchy |
| `parent_nodes` | `list[Node]` | All parent nodes (supports instancing) |
| `excluded` | `bool` | When `True`, this node is excluded from rendering |
| `transform` | `Transform` | Local transform (translation, rotation, scale) |
| `global_transform` | `GlobalTransform` | World-space transformation matrix |
| `properties` | `PropertyCollection` | Custom properties attached to this node |

## Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `create_child_node(name)` | `Node` | Creates and attaches a new child node with the given name |
| `create_child_node(name, entity)` | `Node` | Creates a child node and assigns an entity to it |
| `add_child_node(node)` | `None` | Adds an existing node as a child of this node |
| `get_child(name)` | `Optional[Node]` | Finds a direct child node by name |
| `find_node(name)` | `Optional[Node]` | Recursively finds a descendant node by name |
| `get_property(name)` | `Any` | Gets a property value by name |
| `find_property(name)` | `Optional[Property]` | Finds a property by name |

## Example

Create a scene, attach a mesh to a node, and traverse the scene graph:

```python
from aspose.threed import Scene, Node
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector4

scene = Scene()
mesh = Mesh()
mesh.control_points.append(Vector4(0, 0, 0, 1))
mesh.control_points.append(Vector4(1, 0, 0, 1))
mesh.control_points.append(Vector4(0.5, 1, 0, 1))
mesh.create_polygon(0, 1, 2)

# Attach mesh to a child node
node = scene.root_node.create_child_node("triangle", mesh)

# Traverse child_nodes (property, not a method)
for child in scene.root_node.child_nodes:
    entity = child.entity
    if entity is not None:
        print(f"Node '{child.name}': {type(entity).__name__}")
        # excluded is a property
        print(f"  Excluded: {entity.excluded}")
```

## See Also

- [Scene class reference](/reference.aspose.org/3d/python/scene/)
- [Entity class reference](/reference.aspose.org/3d/python/entity/)
- [Mesh class reference](/reference.aspose.org/3d/python/mesh/)
- [Load files with Aspose.3D](/docs.aspose.org/3d/python/developer-guide/model-loading/)
- [Convert file formats with Aspose.3D](/kb.aspose.org/3d/python/convert-fbx-gltf-python/)
