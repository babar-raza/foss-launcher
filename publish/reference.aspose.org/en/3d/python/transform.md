---
page_role: reference_object_page
title: "Transform — Aspose.3D FOSS for Python API Reference"
description: "API reference for the Transform class in aspose-3d-foss. Control node position, rotation, and scale using translation, Euler angles, Quaternion, and pre/post rotation."
canonical: https://reference.aspose.org/3d/python/transform/
url: /reference.aspose.org/3d/python/transform/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.3D FOSS
family: 3d
platform: python
canonical_import: aspose.threed
robots: index, follow
seoTitle: "Transform — Aspose.3D FOSS for Python API Reference"
keywords:
  - aspose threed transform python
  - python 3d node translation rotation scale
  - aspose 3d foss transform class
  - python 3d euler angles quaternion
  - aspose threed node transform
type: reference_object_page
draft: false
weight: 70
---

**Package**: `aspose.threed` (aspose-3d-foss)

`Transform` controls the position, orientation, and scale of a `Node` in the 3D scene. Every node has exactly one `Transform`, accessed via `node.transform`.

```python
class Transform(A3DObject):
```

---

## Accessing a Node's Transform

```python
from aspose.threed import Scene

scene = Scene()
node = scene.root_node.create_child_node("box")
t = node.transform     # Transform object
```

---

## Properties

| Property | Type | Description |
|---|---|---|
| `translation` | `Vector3` | Position offset from the parent node's origin. Default `Vector3(0, 0, 0)`. |
| `scaling` | `Vector3` | Non-uniform scale factor per axis. Default `Vector3(1, 1, 1)`. |
| `rotation` | `Quaternion` | Rotation as a unit quaternion. Setting this also updates `euler_angles`. |
| `euler_angles` | `Vector3` | Rotation in degrees as (X, Y, Z) Euler angles. Setting this also updates `rotation`. |
| `pre_rotation` | `Vector3` | Euler angles applied before the main rotation (used in FBX rigs). |
| `post_rotation` | `Vector3` | Euler angles applied after the main rotation. |
| `geometric_translation` | `Vector3` | Local-only translation: affects geometry but not child nodes. |
| `geometric_scaling` | `Vector3` | Local-only scale: affects geometry but not child nodes. |
| `geometric_rotation` | `Vector3` | Local-only rotation: affects geometry but not child nodes. |
| `transform_matrix` | `Matrix4` | The full combined 4×4 transformation matrix. Cached; recomputed when any component changes. Setting it decomposes back to translation/scaling/rotation. |

---

## Fluent Setter Methods

All setters return `self`, enabling chaining:

| Method | Parameters | Description |
|---|---|---|
| `set_translation(tx, ty, tz)` | `float, float, float` | Set position. |
| `set_scale(sx, sy, sz)` | `float, float, float` | Set scale. |
| `set_euler_angles(rx, ry, rz)` | `float, float, float` | Set rotation in degrees. |
| `set_rotation(rw, rx, ry, rz)` | `float, float, float, float` | Set rotation as a quaternion (w, x, y, z). |
| `set_pre_rotation(rx, ry, rz)` | `float, float, float` | Set pre-rotation in degrees. |
| `set_post_rotation(rx, ry, rz)` | `float, float, float` | Set post-rotation in degrees. |
| `set_geometric_translation(x, y, z)` | `float, float, float` | Set geometric translation. |
| `set_geometric_scaling(sx, sy, sz)` | `float, float, float` | Set geometric scale. |
| `set_geometric_rotation(rx, ry, rz)` | `float, float, float` | Set geometric rotation in degrees. |

---

## Usage Examples

### Position a Node

```python
from aspose.threed import Scene

scene = Scene()
node = scene.root_node.create_child_node("box")

# Using fluent setters
node.transform.set_translation(5.0, 0.0, -3.0)

# Or via property assignment
from aspose.threed.utilities import Vector3
node.transform.translation = Vector3(5.0, 0.0, -3.0)
```

### Rotate with Euler Angles

```python
from aspose.threed import Scene

scene = Scene()
node = scene.root_node.create_child_node("rotated")

# Rotate 45° around Y axis
node.transform.set_euler_angles(0.0, 45.0, 0.0)

# Chain multiple operations
node.transform.set_translation(2.0, 0.0, 0.0).set_scale(2.0, 2.0, 2.0)
```

### Rotate with a Quaternion

```python
from aspose.threed import Scene
from aspose.threed.utilities import Quaternion, Vector3
import math

scene = Scene()
node = scene.root_node.create_child_node("q-rotated")

# 90° rotation around the Y axis
half_angle = math.radians(45)   # half the total rotation
q = Quaternion(math.cos(half_angle), 0.0, math.sin(half_angle), 0.0)
node.transform.rotation = q

print(f"Euler: {node.transform.euler_angles}")   # synced automatically
```

### Scale and Position Together

```python
from aspose.threed import Scene

scene = Scene()
node = scene.root_node.create_child_node("big-offset")

(node.transform
    .set_translation(10.0, 0.0, 0.0)
    .set_scale(3.0, 3.0, 3.0)
    .set_euler_angles(0.0, 90.0, 0.0))
```

### Geometric Offset (Pivot Offset)

Geometric transforms shift the geometry relative to the node's pivot without affecting child nodes — useful for centering a mesh within its node:

```python
from aspose.threed import Scene

scene = Scene()
node = scene.root_node.create_child_node("centered-mesh")

# Shift the mesh half a unit down so its base sits at y=0
node.transform.set_geometric_translation(0.0, -0.5, 0.0)
```

### Read the Combined Transform Matrix

```python
from aspose.threed import Scene

scene = Scene()
node = scene.root_node.create_child_node("m")
node.transform.set_translation(1.0, 2.0, 3.0).set_euler_angles(0.0, 45.0, 0.0)

m = node.transform.transform_matrix
print(type(m))  # <class 'aspose.threed.utilities.Matrix4'>
```

---

## See Also

- [Node class reference](/reference.aspose.org/3d/python/node/)
- [Scene class reference](/reference.aspose.org/3d/python/scene/)
- [Camera class reference](/reference.aspose.org/3d/python/camera/)
- [Light class reference](/reference.aspose.org/3d/python/light/)
- [Aspose.3D Python API Reference](/reference.aspose.org/3d/python/)
