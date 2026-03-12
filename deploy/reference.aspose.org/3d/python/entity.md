---
canonical: https://reference.aspose.org/3d/python/entity/
canonical_import: aspose_3d_foss
date: '2026-03-10T22:36:17Z'
dateModified: '2026-03-10T22:36:17Z'
datePublished: '2026-03-10T22:36:17Z'
description: It provides access to its parent node hierarchy and exposes the `excluded`
  state used for visibility and exclusion flags. The class integrates with the...
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
lastmod: '2026-03-10T22:36:17Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D Entity
slug: entity
title: Entity
type: reference_object_page
url: /reference.aspose.org/3d/python/entity/
weight: 22
---

## Overview

The `Entity` class represents a base object in the 3D `scene` graph that can be assigned to a `Node` and supports visibility control via exclusion flags. It provides access to its parent node hierarchy and exposes the `excluded` state used for visibility and exclusion flags. The class integrates with the `transform` system through its parent `Node`, enabling hierarchical transformations defined by `Transform`.

| Name | Type | Description |
|------|------|-------------|
| `parent_nodes` | List[`Node`] (read-only) | List of parent nodes in the `scene` graph |
| `parent_node` | Optional[`Node`] (read-only) | Direct parent node, or `None` if root |
| `excluded` | bool (read-only) | Exclusion flag controlling visibility |
| `parent_node(value)` | Method | Sets the parent node |
| `parent_nodes()` | Method | Returns list of parent nodes |
| `parent_node()` | Method | Returns the parent node |
| `excluded()` | Method | Returns the exclusion state |
| `excluded(value)` | Method | Sets the exclusion state |
| `properties` | `PropertyCollection` (read-only) | Collection of custom `properties` |
| `name` | str (read-only) | Object `name` |
| `find_property(property_name)` | Method | Finds a `property` by `name` |
| `get_property(property)` | Method | Gets a `property` `value` |
| `name(value)` | Method | Sets the object `name` |
| `properties()` | Method | Returns the `property` collection |

## Constructor

The `Entity` class in Aspose.3D represents a base object for 3D `scene` elements and supports local transformation (`translation`, `rotation`, `scaling`) via its parent `Node` hierarchy. It provides access to `scene` graph relationships and visibility state through its `properties` and methods.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Optional `name` for the `entity` |
| parent | `Node` | Optional parent node to attach the `entity` to |
| `excluded` | bool | Initial exclusion state (default: `False`) |

## Properties

The `Entity` class serves as the base class for attachable objects in Aspose.3D and provides core functionality for geometric transformations within a 3D `scene` graph. It defines `properties` that control object hierarchy and visibility state.

| Name | Type | Description |
|------|------|-------------|
| `parent_nodes` | List['`Node`'] (read-only) | Returns the list of parent nodes to which this `entity` is attached. |
| `parent_node` | Optional['`Node`'] (read-only) | Returns the immediate parent node of this `entity`, or `None` if unattached. |
| `excluded` | bool (read-only) | Indicates whether this `entity` is `excluded` from rendering or transformation calculations. |

## Methods

The `Entity` class in Aspose.3D supports instancing through multiple parent nodes and provides control over exclusion state. It also integrates with transformation hierarchies including pre/post `rotation` and pivot points via its parent node relationships.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `parent_nodes()` | List[`Node`] | Returns the list of parent nodes this `entity` is attached to, supporting instancing. |
| `parent_node()` | Optional[`Node`] | Returns the primary parent node of this `entity`. |
| `parent_node(value: Optional['Node'])` | None | Sets the primary parent node of this `entity`. |
| `excluded()` | bool | Returns whether this `entity` is `excluded` from rendering or transformation evaluation. |
| `excluded(value: bool)` | None | Sets whether this `entity` is `excluded` from rendering or transformation evaluation. |

## Example

The `Entity` class in Aspose.3D provides core `scene` graph functionality for 3D python visualization and 3d python game development. It supports parent-child relationships via `parent_node()` and `parent_nodes()`, and allows exclusion from rendering via the `excluded` `property`. This example demonstrates how to construct an `Entity`, assign it a parent node, and compute its bounding box and full `transform` composition using the available API surface.

```python
import aspose.threed

# Create a new entity
entity = aspose.threed.Entity()

# Assign a parent node (Node must be created separately)
node = aspose.threed.Node()
entity.parent_node(node)

# Access parent nodes list
parents = entity.parent_nodes()

# Check exclusion state
is_excluded = entity.excluded()

# Set exclusion
entity.excluded(True)
```

## See Also

The `Entity` class serves as a base for `scene` objects in Aspose.3D and supports method chaining for setter methods like `parent_node()` and `excluded()`. It integrates with the rendering pipeline via the `entity` renderer key (stub), though direct renderer access is not yet implemented for most subclasses.

- [Transform handling (local and global)](/reference.aspose.org/3d/python/node/)
- [Bounding boxes and transformations](/blog.aspose.org/3d/python/3d-key-features/)
- [Bounding boxes and transformations](/blog.aspose.org/3d/python/3d-foss-python/)
- [Import for 3D printing workflows](/docs.aspose.org/3d/python/developer-guide/model-loading/)
- [How to Convert 3d Models Python](/kb.aspose.org/3d/python/convert-3d-models-python/)
