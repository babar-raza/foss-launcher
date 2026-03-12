---
page_role: reference_object_page
title: "Light — Aspose.3D FOSS for Python API Reference"
description: "API reference for the Light class in aspose-3d-foss. Configure point, directional, and spot lights with type selection for 3D scene illumination."
canonical: https://reference.aspose.org/3d/python/light/
url: /reference.aspose.org/3d/python/light/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.3D FOSS
family: 3d
platform: python
canonical_import: aspose.threed
robots: index, follow
seoTitle: "Light — Aspose.3D FOSS for Python API Reference"
keywords:
  - aspose threed light python
  - python 3d point light directional
  - aspose 3d foss light class
  - python 3d scene illumination
  - aspose threed entities light
type: reference_object_page
draft: false
weight: 50
---

**Package**: `aspose.threed.entities` (aspose-3d-foss)

`Light` is an `Entity` that adds a light source to a 3D scene. Like `Camera`, it is attached to a `Node` to control its position and direction.

```python
class Light(Camera):
```

#### Inheritance

`A3DObject` → `SceneObject` → `Entity` → `Camera` → `Light`

`Light` inherits from `Camera` and adds light-type control.

---

## Constructor

```python
Light(name: str = None, light_type: str = "POINT")
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str \| None` | `None` | Optional name for the light object. |
| `light_type` | `str` | `"POINT"` | Light type. Use `LightType` constants. |

---

## Properties

| Property | Type | Description |
|---|---|---|
| `light_type` | `str` | The kind of light source. See `LightType` values below. |
| `name` | `str` | Name of the light object. |

`Light` also inherits all `Camera` properties (`near_plane`, `far_plane`, etc.), though these are not meaningful for light objects.

---

## LightType Values

```python
from aspose.threed.entities import LightType
```

| Constant | Value | Description |
|---|---|---|
| `LightType.POINT` | `"POINT"` | Emits light equally in all directions from a single point. |
| `LightType.DIRECTIONAL` | `"DIRECTIONAL"` | Parallel rays from an infinitely distant source (like sunlight). |
| `LightType.SPOT` | `"SPOT"` | Cone-shaped beam; position and direction matter. |
| `LightType.AREA` | `"AREA"` | Light emitted from a rectangular area. |
| `LightType.VOLUME` | `"VOLUME"` | Volumetric/global illumination light. |

---

## Usage Examples

### Point Light

```python
from aspose.threed import Scene
from aspose.threed.entities import Light, LightType

scene = Scene()

light = Light("PointLight", LightType.POINT)
node = scene.root_node.create_child_node("light", light)
node.transform.set_translation(0.0, 10.0, 0.0)

scene.save("lit-scene.glb")
```

### Directional Light

```python
from aspose.threed import Scene
from aspose.threed.entities import Light, LightType

scene = Scene()

sun = Light("Sun", LightType.DIRECTIONAL)
node = scene.root_node.create_child_node("sun", sun)
# Direction is controlled by the node's rotation
node.transform.set_euler_angles(-45.0, 30.0, 0.0)  # degrees

scene.save("directional-light.glb")
```

### Add Both a Camera and a Light

```python
from aspose.threed import Scene
from aspose.threed.entities import Camera, Light, LightType, ProjectionType

scene = Scene()

# Camera
cam = Camera("Cam", ProjectionType.PERSPECTIVE)
cam.field_of_view = 60.0
cam_node = scene.root_node.create_child_node("camera", cam)
cam_node.transform.set_translation(0.0, 5.0, 15.0)

# Directional light
light = Light("DirLight", LightType.DIRECTIONAL)
light_node = scene.root_node.create_child_node("light", light)
light_node.transform.set_euler_angles(-30.0, 45.0, 0.0)

scene.save("camera-and-light.glb")
```

### Enumerate Lights in an Imported Scene

```python
from aspose.threed import Scene
from aspose.threed.entities import Light

scene = Scene()
scene.open("model.glb")

def find_lights(node, depth=0):
    if isinstance(node.entity, Light):
        print(f"{'  ' * depth}Light: {node.name} ({node.entity.light_type})")
    for child in node.child_nodes:
        find_lights(child, depth + 1)

find_lights(scene.root_node)
```

---

## See Also

- [Camera class reference](/reference.aspose.org/3d/python/camera/)
- [Node class reference](/reference.aspose.org/3d/python/node/)
- [Transform class reference](/reference.aspose.org/3d/python/transform/)
- [Scene class reference](/reference.aspose.org/3d/python/scene/)
- [Aspose.3D Python API Reference](/reference.aspose.org/3d/python/)
