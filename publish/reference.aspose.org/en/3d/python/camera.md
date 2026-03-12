---
page_role: reference_object_page
title: "Camera — Aspose.3D FOSS for Python API Reference"
description: "API reference for the Camera class in aspose-3d-foss. Set projection type, near/far clipping planes, field of view, and aspect ratio for 3D scene cameras."
canonical: https://reference.aspose.org/3d/python/camera/
url: /reference.aspose.org/3d/python/camera/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.3D FOSS
family: 3d
platform: python
canonical_import: aspose.threed
robots: index, follow
seoTitle: "Camera — Aspose.3D FOSS for Python API Reference"
keywords:
  - aspose threed camera python
  - python 3d camera projection
  - aspose 3d foss camera class
  - python 3d perspective orthographic camera
  - aspose threed entities camera
type: reference_object_page
draft: false
weight: 40
---

**Package**: `aspose.threed.entities` (aspose-3d-foss)

`Camera` is an `Entity` that defines a viewpoint in a 3D scene. It controls how the scene is projected onto a 2D image plane. A camera is attached to a `Node` to position and orient it in the scene.

```python
class Camera(Entity):
```

#### Inheritance

`A3DObject` → `SceneObject` → `Entity` → `Camera`

---

## Implementation Notes

In this edition of aspose-3d-foss, the `Camera` class is a **declaration stub**. Only `projection_type` and `name` are functionally stored and retrievable. All other properties (`near_plane`, `far_plane`, `field_of_view`, `aspect_ratio`, etc.) have setters that are no-ops — the assigned values are not retained. Read-back of these properties returns the class default value regardless of what was assigned.

When importing camera data from a 3D file (glTF, FBX), the `projection_type` is parsed correctly. Other camera attributes are available if the format stores them as scene-graph metadata.

---

## Constructor

```python
Camera(name: str = None, projection_type: str = "PERSPECTIVE")
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str \| None` | `None` | Optional name for the camera node. |
| `projection_type` | `str` | `"PERSPECTIVE"` | Initial projection type. Use `ProjectionType.PERSPECTIVE` or `ProjectionType.ORTHOGRAPHIC`. |

---

## Properties

| Property | Type | Description |
|---|---|---|
| `projection_type` | `str` | Projection mode: `"PERSPECTIVE"` or `"ORTHOGRAPHIC"`. Set with `ProjectionType` constants. |
| `near_plane` | `float` | Distance to the near clipping plane. Geometry closer than this is not rendered. Default `0.1`. |
| `far_plane` | `float` | Distance to the far clipping plane. Geometry farther than this is not rendered. Default `1000.0`. |
| `field_of_view` | `float` | Vertical field of view in degrees (perspective cameras only). |
| `field_of_view_x` | `float` | Horizontal field of view in degrees. |
| `field_of_view_y` | `float` | Vertical field of view in degrees (same as `field_of_view`). |
| `aspect_ratio` | `float` | Width-to-height ratio of the output image. Default `1.0`. |
| `ortho_height` | `float` | Height of the orthographic view volume in world units (orthographic cameras only). Default `100.0`. |
| `name` | `str` | Name of the camera object. |

---

## Usage Examples

> **Note**: In this edition, only `projection_type` is functionally stored. Property assignments for `near_plane`, `far_plane`, `field_of_view`, and `aspect_ratio` are accepted without error but do not persist.

### Perspective Camera

```python
from aspose.threed import Scene
from aspose.threed.entities import Camera
from aspose.threed.entities import ProjectionType

scene = Scene()

# projection_type is stored and saved
cam = Camera("MainCamera", ProjectionType.PERSPECTIVE)

node = scene.root_node.create_child_node("camera", cam)

# Position the camera using node transform (this does persist)
node.transform.set_translation(0.0, 5.0, 20.0)

scene.save("scene-with-camera.glb")
```

### Orthographic Camera

```python
from aspose.threed import Scene
from aspose.threed.entities import Camera, ProjectionType

scene = Scene()

# Only projection_type is retained; other property assignments are no-ops
cam = Camera("OrthoCamera", ProjectionType.ORTHOGRAPHIC)

scene.root_node.create_child_node("ortho_cam", cam)
scene.save("ortho-scene.glb")
```

### Read Camera After Import

```python
from aspose.threed import Scene
from aspose.threed.entities import Camera

scene = Scene()
scene.open("model.glb")

for node in scene.root_node.child_nodes:
    if isinstance(node.entity, Camera):
        cam = node.entity
        # projection_type is reliably populated; other numeric properties
        # return default values (0.0 / 1.0) regardless of file content
        print(f"Camera '{cam.name}': {cam.projection_type}")
```

---

## See Also

- [Light class reference](/reference.aspose.org/3d/python/light/)
- [Node class reference](/reference.aspose.org/3d/python/node/)
- [Transform class reference](/reference.aspose.org/3d/python/transform/)
- [Scene class reference](/reference.aspose.org/3d/python/scene/)
- [Aspose.3D Python API Reference](/reference.aspose.org/3d/python/)
