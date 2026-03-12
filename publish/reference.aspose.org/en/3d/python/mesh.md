---
canonical: https://reference.aspose.org/3d/python/mesh/
canonical_import: aspose.threed
date: '2026-03-11T00:09:28Z'
dateModified: '2026-03-11T00:09:28Z'
datePublished: '2026-03-11T00:09:28Z'
description: Mesh is the primary polygon geometry entity in Aspose.3D for Python.
  It stores vertex positions as control points, defines polygon faces by vertex index
  lists, and supports vertex element data layers such as normals and UV coordinates.
display_name: Aspose.3D
family: 3d
keywords:
- aspose threed Mesh class
- python 3d mesh control_points
- python mesh polygon geometry
- aspose mesh create_polygon
- aspose threed mesh reference
lastmod: '2026-03-11T00:09:28Z'
page_role: reference_object_page
platform: python
reading_time: 2
robots: index, follow
seoTitle: Aspose.3D Mesh Class Reference — Python
slug: mesh
title: Mesh
type: reference_object_page
url: /reference.aspose.org/3d/python/mesh/
weight: 23
---

Package: `aspose.threed.entities` (aspose-3d-foss 26.1.0)

`Mesh` stores polygon geometry as a list of control points (vertex positions) and a list of polygon faces. Each polygon face is a list of zero-based indices into the control points array. Faces may be triangles, quads, or higher-arity polygons. Additional per-vertex data — normals, UV coordinates, vertex colours — is attached as `VertexElement` layers.

```python
class Mesh(Geometry):
```

#### Inheritance

`A3DObject` → `SceneObject` → `Entity` → `Geometry` → `Mesh`

---

## Examples

**Build a single triangle mesh from scratch:**

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector4

# Create the mesh and add three vertex positions
# control_points is a property (list) — append to it directly
mesh = Mesh()
mesh.control_points.append(Vector4(0.0, 0.0, 0.0, 1.0))   # vertex 0
mesh.control_points.append(Vector4(1.0, 0.0, 0.0, 1.0))   # vertex 1
mesh.control_points.append(Vector4(0.5, 1.0, 0.0, 1.0))   # vertex 2

# Define one triangle face using vertex indices
mesh.create_polygon(0, 1, 2)

# Attach to a scene and save
scene = Scene()
scene.root_node.create_child_node("triangle", mesh)
scene.save("triangle.stl")
```

**Build a quad mesh and triangulate it before export:**

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector4

mesh = Mesh()
# Four corners of a unit square in the XZ plane
for x, z in [(0, 0), (1, 0), (1, 1), (0, 1)]:
    mesh.control_points.append(Vector4(float(x), 0.0, float(z), 1.0))

# One quad face
mesh.create_polygon(0, 1, 2, 3)
print(f"Polygons before triangulate: {mesh.polygon_count}")  # 1

triangulated = mesh.triangulate()
print(f"Polygons after triangulate: {triangulated.polygon_count}")  # 2

scene = Scene()
scene.root_node.create_child_node("quad", triangulated)
scene.save("quad.glb")
```

---

## Properties

`control_points`, `polygon_count`, `polygons`, `edges`, and `vertex_elements` are all **properties** — access them without parentheses.

| Property | Type | Access | Description |
|---|---|---|---|
| `control_points` | `list[Vector4]` | read | Vertex position array. Each entry is a `Vector4(x, y, z, w)` where `w` is `1.0` for position data. Append to this list to add vertices. |
| `polygon_count` | `int` | read | Number of polygon faces defined on this mesh. |
| `polygons` | `list[list[int]]` | read | All face definitions as a list of index lists. Each inner list holds the vertex indices (into `control_points`) for one face. |
| `edges` | `list[int]` | read | Raw edge index data. Primarily for internal use and advanced topology queries. |
| `vertex_elements` | `list[VertexElement]` | read | All vertex element layers currently attached to this mesh (normals, UVs, colours, etc.). |
| `visible` | `bool` | read/write | When `False`, the mesh is hidden in viewers that respect visibility. |
| `cast_shadows` | `bool` | read/write | Whether this mesh casts shadows in renderers that support shadow maps. |
| `receive_shadows` | `bool` | read/write | Whether this mesh receives shadows from other shadow-casting geometry. |

---

## Methods

### `create_polygon(*indices)`

Define a new polygon face by providing the vertex indices in order. The indices reference positions in `control_points`. Accepts three or more indices for triangles, quads, and n-gons.

| Parameter | Type | Description |
|---|---|---|
| `*indices` | `int` | Vertex index arguments in winding order (typically counter-clockwise when viewed from outside). |

**Returns:** `None`

```python
mesh = Mesh()
# ... populate control_points ...
mesh.create_polygon(0, 1, 2)       # triangle
mesh.create_polygon(0, 1, 2, 3)    # quad
print(mesh.polygon_count)          # 2
```

---

### `triangulate()`

Return a new `Mesh` where every polygon has been split into triangles using fan triangulation. The original mesh is not modified. Useful before exporting to formats that require triangle-only geometry (such as STL or some glTF pipelines).

**Returns:** `Mesh` — a new mesh containing only triangles.

```python
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector4

mesh = Mesh()
for v in [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]:
    mesh.control_points.append(Vector4(*v, 1.0))
mesh.create_polygon(0, 1, 2, 3)   # one quad

tri_mesh = mesh.triangulate()
print(tri_mesh.polygon_count)      # 2
```

---

### `to_mesh()`

Return this `Mesh` as a `Mesh` instance. For `Mesh` objects this is an identity operation (returns `self`). Defined on the `Geometry` base class to provide a uniform conversion interface when working with generic `Geometry` references.

**Returns:** `Mesh`

```python
from aspose.threed.entities import Geometry

def ensure_mesh(geom: Geometry):
    return geom.to_mesh()
```

---

### `create_element(element_type, mapping_mode, reference_mode)`

Add a new `VertexElement` layer of the specified type to the mesh. Use this to attach normals, tangents, binormals, vertex colours, and smoothing groups.

| Parameter | Type | Description |
|---|---|---|
| `element_type` | `VertexElementType` | The kind of data this layer holds (e.g., `VertexElementType.NORMAL`). |
| `mapping_mode` | `MappingMode` | How the data maps to geometry: `BY_CONTROL_POINT`, `BY_POLYGON_VERTEX`, `BY_POLYGON`, etc. |
| `reference_mode` | `ReferenceMode` | How indices are used: `DIRECT` or `INDEX_TO_DIRECT`. |

**Returns:** `VertexElement`

```python
from aspose.threed.entities import Mesh, VertexElementType, MappingMode, ReferenceMode
from aspose.threed.utilities import Vector4

mesh = Mesh()
mesh.control_points.append(Vector4(0, 0, 0, 1))
mesh.control_points.append(Vector4(1, 0, 0, 1))
mesh.control_points.append(Vector4(0.5, 1, 0, 1))
mesh.create_polygon(0, 1, 2)

normal_element = mesh.create_element(
    VertexElementType.NORMAL,
    MappingMode.BY_CONTROL_POINT,
    ReferenceMode.DIRECT,
)
```

---

### `create_element_uv(uv_mapping, mapping_mode, reference_mode)`

Add a UV coordinate layer to the mesh. This is the preferred method for attaching texture coordinate data.

| Parameter | Type | Description |
|---|---|---|
| `uv_mapping` | `TextureMapping` | The UV channel purpose: `DIFFUSE`, `SPECULAR`, `NORMAL`, `AMBIENT`, etc. |
| `mapping_mode` | `MappingMode` | How UVs map to geometry elements. |
| `reference_mode` | `ReferenceMode` | Indexing mode: `DIRECT` or `INDEX_TO_DIRECT`. |

**Returns:** `VertexElementUV`

```python
from aspose.threed.entities import Mesh, TextureMapping, MappingMode, ReferenceMode

mesh = Mesh()
# ... define control_points and polygons ...
uv_element = mesh.create_element_uv(
    TextureMapping.DIFFUSE,
    MappingMode.BY_POLYGON_VERTEX,
    ReferenceMode.INDEX_TO_DIRECT,
)
```

---

## See Also

- [Entity class reference](/reference.aspose.org/3d/python/entity/)
- [Node class reference](/reference.aspose.org/3d/python/node/)
- [Scene class reference](/reference.aspose.org/3d/python/scene/)
- [How to build mesh programmatically](/kb.aspose.org/3d/python/build-mesh-python/)
