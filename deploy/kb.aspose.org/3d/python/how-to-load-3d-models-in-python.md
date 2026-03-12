---
page_role: howto_article
title: "How to Load 3D Models in Python"
description: "Learn how to open OBJ, STL, glTF, COLLADA, and 3MF files in Python using Aspose.3D FOSS, traverse the scene graph, and read mesh geometry including vertices, polygons, and UV data."
date: 2026-01-15
weight: 10
draft: false
type: "topic"
keywords: ["load 3d model python", "open obj python", "read stl python", "aspose 3d load", "scene from file python", "mesh vertices python"]
step1: "Install aspose-3d-foss from PyPI"
step2: "Import the Scene class from aspose.threed"
step3: "Load a file using Scene.from_file() or scene.open()"
step4: "Traverse scene nodes to find mesh objects"
step5: "Read vertex positions and polygon indices"
step6: "Apply format-specific load options (ObjLoadOptions)"
---

Aspose.3D FOSS for Python provides a straightforward API for opening 3D files without any native dependencies. After loading a file into a `Scene` object, you can walk the node hierarchy and read raw geometry data for every mesh in the scene.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install the Package

Install Aspose.3D FOSS from PyPI. No additional system libraries are required.

```bash
pip install aspose-3d-foss
```

Verify the installation:

```python
import aspose.threed
print(aspose.threed.__version__)  # e.g. 26.1.0
```

Supported Python versions: 3.7, 3.8, 3.9, 3.10, 3.11, 3.12.

---

### Step 2: Import the Scene Class

The `Scene` class is the top-level container for all 3D data. Import it along with any load-option classes you need.

```python
from aspose.threed import Scene
from aspose.threed.formats import ObjLoadOptions
```

All public classes live under `aspose.threed` or its sub-packages (`aspose.threed.entities`, `aspose.threed.formats`, `aspose.threed.utilities`).

---

### Step 3: Load a File

Use the static `Scene.from_file()` method to open any supported format. The library detects the format automatically from the file extension.

```python
##Automatic format detection
scene = Scene.from_file("model.obj")
```

Alternatively, create a `Scene` instance and call `open()` — useful when you want to pass load options or handle errors explicitly:

```python
scene = Scene()
scene.open("model.obj")
```

Both methods support OBJ, STL (binary and ASCII), glTF 2.0 / GLB, COLLADA (DAE), and 3MF files.

---

### Step 4: Traverse Scene Nodes

A loaded scene is a tree of `Node` objects rooted at `scene.root_node`. Iterate recursively to find all nodes:

```python
from aspose.threed import Scene, Node

scene = Scene.from_file("model.obj")

def walk(node: Node, depth: int = 0) -> None:
    indent = "  " * depth
    print(f"{indent}Node: {node.name!r}")
    for child in node.child_nodes:
        walk(child, depth + 1)

walk(scene.root_node)
```

Each `Node` can carry zero or more `Entity` objects (meshes, cameras, lights). Check `node.entities` to see what is attached.

---

### Step 5: Access Vertex and Polygon Data

Cast a node's entity to `Mesh` and read its control points (vertex positions) and polygons (face index lists):

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh

scene = Scene.from_file("model.obj")

for node in scene.root_node.child_nodes:
    for entity in node.entities:
        if isinstance(entity, Mesh):
            mesh: Mesh = entity
            print(f"Mesh '{node.name}': "
                  f"{len(mesh.control_points)} vertices, "
                  f"{len(mesh.polygons)} polygons")

            # First vertex position
            if mesh.control_points:
                v = mesh.control_points[0]
                print(f"  First vertex: ({v.x:.4f}, {v.y:.4f}, {v.z:.4f})")

            # First polygon face (list of control-point indices)
            if mesh.polygons:
                print(f"  First polygon: {mesh.polygons[0]}")
```

`mesh.control_points` is a list of `Vector4` objects; `x`, `y`, `z` carry the position and `w` is the homogeneous coordinate (normally 1.0).

`mesh.polygons` is a list of lists of integers, where each inner list is the ordered set of control-point indices for one face.

---

### Step 6: Apply Format-Specific Load Options

For fine-grained control over how an OBJ file is interpreted, pass an `ObjLoadOptions` instance to `scene.open()`:

```python
from aspose.threed import Scene
from aspose.threed.formats import ObjLoadOptions

options = ObjLoadOptions()
options.flip_coordinate_system = True   # Convert right-hand Y-up to Z-up
options.scale = 0.01                    # Convert centimetres to metres
options.enable_materials = True         # Load .mtl material file
options.normalize_normal = True         # Normalize all normals to unit length

scene = Scene()
scene.open("model.obj", options)
```

For STL files, the equivalent class is `StlLoadOptions`. For glTF, use `GltfLoadOptions`. See the [API reference](/reference.aspose.net/3d/python/) for a full list.

{{% /steps %}}

---

## Common Issues and Fixes

**FileNotFoundError when calling `Scene.from_file()`**

The path must be absolute or correct relative to the working directory at runtime. Use `pathlib.Path` to build reliable paths:

```python
from pathlib import Path
from aspose.threed import Scene

path = Path(__file__).parent / "assets" / "model.obj"
scene = Scene.from_file(str(path))
```

**`mesh.polygons` is empty after loading an STL file**

STL files store triangles as raw facets, not an indexed mesh. After loading, polygons are synthesised from those facets. If `polygons` appears empty, check `len(mesh.control_points)` — if the count is a multiple of 3 the geometry is stored in unindexed form and each consecutive triple of vertices forms one triangle.

**Coordinate system mismatch (model appears rotated or mirrored)**

Different tools use different conventions (Y-up vs Z-up, left-hand vs right-hand). Set `ObjLoadOptions.flip_coordinate_system = True` or apply a rotation to the root node's `Transform` after loading.

**`AttributeError: 'NoneType' object has no attribute 'polygons'`**

A node's entity list may contain non-mesh entities (cameras, lights). Always guard with `isinstance(entity, Mesh)` before casting.

---

## Frequently Asked Questions (FAQ)

**Which 3D formats can I load?**

OBJ (Wavefront), STL (binary and ASCII), glTF 2.0 / GLB, COLLADA (DAE), and 3MF. FBX file tokenization is partially supported but full parsing is not yet complete.

**Does loading an OBJ file also load the `.mtl` material?**

Yes, when `ObjLoadOptions.enable_materials = True` (the default). The library looks for the `.mtl` file in the same directory as the `.obj` file. If the `.mtl` is missing, geometry is still loaded and a warning is emitted.

**Can I load a file from a byte stream instead of a path?**

`Scene.open()` accepts a file path string. Loading from an in-memory stream is not exposed in the current API; write the bytes to a temporary file first.

**How do I get surface normals?**

After loading, check `mesh.get_element(VertexElementType.NORMAL)`. This returns a `VertexElementNormal` whose `data` list contains one normal vector per reference, mapped according to `mapping_mode` and `reference_mode`.

```python
from aspose.threed.entities import Mesh, VertexElementType

normals = mesh.get_element(VertexElementType.NORMAL)
if normals:
    print(normals.data[0])  # First normal vector
```

**Is the library thread-safe for loading multiple files concurrently?**

Each `Scene` object is independent. Loading separate files into separate `Scene` instances from separate threads is safe as long as you do not share a single `Scene` across threads without external locking.
