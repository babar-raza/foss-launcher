---
canonical: https://reference.aspose.org/3d/python/entity/
canonical_import: aspose.threed
date: '2026-03-10T22:36:17Z'
dateModified: '2026-03-10T22:36:17Z'
datePublished: '2026-03-10T22:36:17Z'
description: The Entity class is the base class for all attachable 3D objects in
  Aspose.3D for Python. It provides access to parent node relationships and visibility
  control via the excluded property.
display_name: Aspose.3D
family: 3d
keywords:
- aspose threed Entity class
- python 3d entity parent_node
- aspose entity excluded property
- aspose threed scene entity
- python 3d entity reference
lastmod: '2026-03-10T22:36:17Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D Entity Class Reference — Python
slug: entity
title: Entity
type: reference_object_page
url: /reference.aspose.org/3d/python/entity/
weight: 22
---

## Overview

The `Entity` class is the abstract base class for objects that can be attached to a `Node` in the Aspose.3D scene graph. Concrete subclasses include `Mesh`, `Camera`, `Light`, and `Geometry`. `Entity` provides access to the parent node hierarchy and exposes the `excluded` property for visibility control.

All attributes listed below are **properties** — access them without parentheses.

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh

scene = Scene.from_file("model.obj")

for node in scene.root_node.child_nodes:
    entity = node.entity
    if entity is not None:
        # excluded is a property, not a method call
        if not entity.excluded:
            # parent_node is a property, not a method call
            parent = entity.parent_node
            print(f"Active entity '{entity.name}', parent: {parent.name if parent else 'None'}")
```

## Inheritance

`A3DObject` → `SceneObject` → `Entity`

Subclasses: `Geometry` → `Mesh`, `Camera`, `Light`, and others.

## Constructor

`Entity` is an abstract base class and is not instantiated directly. Use a concrete subclass such as `Mesh`.

## Properties

| Name | Type | Description |
|------|------|-------------|
| `parent_nodes` | `list[Node]` (read-only) | All parent nodes to which this entity is attached. Supports instancing (same entity referenced from multiple nodes). |
| `parent_node` | `Optional[Node]` (read-only) | The primary parent node, or `None` if the entity is not attached. |
| `excluded` | `bool` (read/write) | When `True`, this entity is excluded from rendering. Access and set as a property: `entity.excluded = True`. |
| `name` | `str` (read/write) | Human-readable name for this entity. |
| `properties` | `PropertyCollection` (read-only) | Collection of custom properties. |

## Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_property(name)` | `Any` | Gets a property value by name. |
| `find_property(name)` | `Optional[Property]` | Finds a property by name. |

**Important:** `parent_node`, `parent_nodes`, and `excluded` are **properties**, not methods. Do not call them with parentheses. The correct patterns are:

```python
# CORRECT
is_excluded = entity.excluded
parent = entity.parent_node
parents = entity.parent_nodes

# WRONG — do not do this
is_excluded = entity.excluded()   # TypeError
parent = entity.parent_node()     # TypeError
```

To set `parent_node`, assign to the property:

```python
entity.parent_node = some_node    # CORRECT
```

## Example

Inspect entity state after loading a scene:

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh

scene = Scene.from_file("model.stl")

for node in scene.root_node.child_nodes:
    entity = node.entity
    if entity is None:
        continue

    # Properties accessed without parentheses
    print(f"Entity: {entity.name or '(unnamed)'}")
    print(f"  Type: {type(entity).__name__}")
    print(f"  Excluded: {entity.excluded}")
    print(f"  Parent node: {entity.parent_node.name if entity.parent_node else 'None'}")

    if isinstance(entity, Mesh):
        print(f"  Vertices: {len(entity.control_points)}")
        print(f"  Polygons: {entity.polygon_count}")
```

## See Also

- [Node class reference](/reference.aspose.org/3d/python/node/)
- [Mesh class reference](/reference.aspose.org/3d/python/mesh/)
- [Import for 3D printing workflows](/docs.aspose.org/3d/python/developer-guide/model-loading/)
- [How to Convert 3D Models with Python](/kb.aspose.org/3d/python/convert-3d-models-python/)
