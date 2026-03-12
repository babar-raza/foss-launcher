---
page_role: reference_object_page
title: "LambertMaterial and PhongMaterial — Aspose.3D FOSS for Python API Reference"
description: "API reference for LambertMaterial and PhongMaterial in aspose-3d-foss. Set ambient, diffuse, emissive, specular colors and shininess for 3D mesh shading."
canonical: https://reference.aspose.org/3d/python/material/
url: /reference.aspose.org/3d/python/material/
date: '2026-03-12'
dateModified: '2026-03-12'
datePublished: '2026-03-12'
display_name: Aspose.3D FOSS
family: 3d
platform: python
canonical_import: aspose.threed
robots: index, follow
seoTitle: "LambertMaterial and PhongMaterial — Aspose.3D FOSS for Python API Reference"
keywords:
  - aspose threed material python
  - python 3d lambert phong material
  - aspose 3d foss material class
  - python 3d diffuse specular shininess
  - aspose threed shading material
type: reference_object_page
draft: false
weight: 60
---

**Package**: `aspose.threed.shading` (aspose-3d-foss)

Aspose.3D FOSS provides two material classes in the classic shading hierarchy:

- **`LambertMaterial`** — diffuse matte shading (no specularity)
- **`PhongMaterial`** — extends Lambert with specular highlights and shininess

Both are assigned to a `Node` via `node.material`. Colors are set using `Vector3(r, g, b)` where components are in `[0.0, 1.0]`.

---

## LambertMaterial

```python
class LambertMaterial(Material):
```

#### Inheritance

`A3DObject` → `Material` → `LambertMaterial`

### Constructor

```python
LambertMaterial(name: str = None)
```

### Properties

| Property | Type | Description |
|---|---|---|
| `ambient_color` | `Vector3 \| None` | Ambient light contribution. Default `None` (unset). |
| `diffuse_color` | `Vector3 \| None` | Base color under diffuse illumination. Default `None`. |
| `emissive_color` | `Vector3 \| None` | Self-emitted light color. Default `None`. |
| `transparent_color` | `Vector3 \| None` | Transmission/transparency tint color. Default `None`. |
| `transparency` | `float` | Opacity level: `0.0` = fully opaque, `1.0` = fully transparent. Clamped to `[0.0, 1.0]`. |

### Class Constants

| Constant | Value | Description |
|---|---|---|
| `MAP_DIFFUSE` | `"Diffuse"` | Key for a diffuse texture map. |
| `MAP_AMBIENT` | `"Ambient"` | Key for an ambient texture map. |
| `MAP_EMISSIVE` | `"Emissive"` | Key for an emissive texture map. |
| `MAP_SPECULAR` | `"Specular"` | Key for a specular texture map. |
| `MAP_NORMAL` | `"Normal"` | Key for a normal map. |

---

## PhongMaterial

```python
class PhongMaterial(LambertMaterial):
```

#### Inheritance

`A3DObject` → `Material` → `LambertMaterial` → `PhongMaterial`

Inherits all `LambertMaterial` properties and adds:

### Additional Properties

| Property | Type | Description |
|---|---|---|
| `specular_color` | `Vector3 \| None` | Color of specular (shiny) highlights. Default `None`. |
| `specular_factor` | `float` | Scale of the specular contribution. Default `0.0`. |
| `shininess` | `float` | Phong shininess exponent. Higher = tighter/smaller highlights. Default `0.0`. |
| `reflection_color` | `Vector3 \| None` | Environment reflection tint. Default `None`. |
| `reflection_factor` | `float` | Blend amount for reflection. Default `0.0`. |

---

## Usage Examples

### Lambert Matte Material

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh
from aspose.threed.shading import LambertMaterial
from aspose.threed.utilities import Vector3, Vector4

scene = Scene()

# Build a simple triangle mesh
mesh = Mesh()
mesh.control_points.append(Vector4(0, 0, 0, 1))
mesh.control_points.append(Vector4(1, 0, 0, 1))
mesh.control_points.append(Vector4(0.5, 1, 0, 1))
mesh.create_polygon(0, 1, 2)

# Create a matte red material
mat = LambertMaterial("red-matte")
mat.diffuse_color = Vector3(0.8, 0.1, 0.1)    # R, G, B in [0, 1]
mat.ambient_color = Vector3(0.1, 0.05, 0.05)

node = scene.root_node.create_child_node("triangle", mesh)
node.material = mat

scene.save("lambert.obj")
```

### Phong Shiny Material

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh
from aspose.threed.shading import PhongMaterial
from aspose.threed.utilities import Vector3, Vector4

scene = Scene()

mesh = Mesh()
mesh.control_points.append(Vector4(0, 0, 0, 1))
mesh.control_points.append(Vector4(1, 0, 0, 1))
mesh.control_points.append(Vector4(0.5, 1, 0, 1))
mesh.create_polygon(0, 1, 2)

mat = PhongMaterial("shiny-blue")
mat.diffuse_color = Vector3(0.1, 0.2, 0.8)   # blue
mat.specular_color = Vector3(1.0, 1.0, 1.0)  # white highlights
mat.specular_factor = 0.5
mat.shininess = 64.0                           # tight specular lobe
mat.ambient_color = Vector3(0.05, 0.05, 0.1)

node = scene.root_node.create_child_node("mesh", mesh)
node.material = mat

scene.save("phong.obj")
```

### Semi-Transparent Material

```python
from aspose.threed.shading import LambertMaterial
from aspose.threed.utilities import Vector3

mat = LambertMaterial("glass")
mat.diffuse_color = Vector3(0.7, 0.9, 1.0)   # faint blue tint
mat.transparency = 0.7                         # 70% transparent
```

### Read Material from Imported Scene

```python
from aspose.threed import Scene
from aspose.threed.shading import LambertMaterial, PhongMaterial

scene = Scene()
scene.open("model.obj")

def inspect_node(node):
    if node.material:
        m = node.material
        kind = "Phong" if isinstance(m, PhongMaterial) else "Lambert"
        print(f"Node '{node.name}' — {kind}: diffuse={m.diffuse_color}")
        if isinstance(m, PhongMaterial):
            print(f"  shininess={m.shininess}")
    for child in node.child_nodes:
        inspect_node(child)

inspect_node(scene.root_node)
```

---

## See Also

- [Mesh class reference](/reference.aspose.org/3d/python/mesh/)
- [Node class reference](/reference.aspose.org/3d/python/node/)
- [Scene class reference](/reference.aspose.org/3d/python/scene/)
- [Aspose.3D Python API Reference](/reference.aspose.org/3d/python/)
