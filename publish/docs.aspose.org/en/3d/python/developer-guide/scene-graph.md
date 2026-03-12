---
page_role: howto_article
title: Scene Graph
description: >-
  Understand and work with the Aspose.3D FOSS scene graph in Python — create
  scenes, build node hierarchies, attach mesh entities, set transforms, and
  traverse the tree recursively.
weight: 20
type: docs
---

A **scene graph** is the foundational data model of Aspose.3D FOSS for Python. Every 3D file — whether loaded from disk or constructed in memory — is represented as a tree of `Node` objects rooted at `Scene.root_node`. Each node can hold child nodes and one or more `Entity` objects (meshes, cameras, lights). Understanding the scene graph gives you direct access to the geometry, materials, and spatial transforms of every object in a scene.

## Installation and Setup

Install the library from PyPI:

```bash
pip install aspose-3d-foss
```

No native extensions, compilers, or additional system packages are required. For full installation instructions, see the [Installation Guide](/docs.aspose.org/3d/python/getting-started/installation/).

---

## Overview: Scene Graph Concepts

The scene graph in Aspose.3D FOSS follows a straightforward containment hierarchy:

```
Scene
└── root_node  (Node)
    ├── child_node_A  (Node)
    │   ├── entity: Mesh
    │   └── transform: translation, rotation, scale
    ├── child_node_B  (Node)
    │   └── child_node_C  (Node)
    │       └── entity: Mesh
    └── ...
```

| Object | Role |
|--------|------|
| `Scene` | Top-level container. Holds `root_node`, `asset_info`, `animation_clips`, and `sub_scenes`. |
| `Node` | Named tree node. Has a parent, zero or more children, zero or more entities, and a local `Transform`. |
| `Entity` | Geometry or scene object attached to a node. Common entity types: `Mesh`, `Camera`, `Light`. |
| `Transform` | Local-space position, rotation, and scale for a node. The world-space result is read from `global_transform`. |

---

## Step-by-Step: Building a Scene Graph Programmatically

### Step 1: Create a Scene

A new `Scene` always starts with an empty `root_node`:

```python
from aspose.threed import Scene

scene = Scene()
print(scene.root_node.name)   # "RootNode"
print(len(scene.root_node.child_nodes))  # 0
```

`Scene` is the entry point for everything: loading files, saving files, creating animation clips, and accessing the node tree.

---

### Step 2: Create Child Nodes

Use `create_child_node(name)` to add named nodes to the tree:

```python
from aspose.threed import Scene

scene = Scene()

parent = scene.root_node.create_child_node("parent")
child  = parent.create_child_node("child")

print(parent.name)                          # "parent"
print(child.parent_node.name)               # "parent"
print(len(scene.root_node.child_nodes))     # 1
```

Alternatively, create a standalone `Node` and attach it explicitly:

```python
from aspose.threed import Scene, Node

scene = Scene()
node = Node("standalone")
scene.root_node.add_child_node(node)
```

Both approaches produce the same result. `create_child_node` is more concise for inline construction.

---

### Step 3: Create a Mesh Entity and Attach It

A `Mesh` stores vertex data (`control_points`) and face topology (`polygons`). Create one, add geometry, then attach it to a node:

```python
from aspose.threed import Scene, Node
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector3, Vector4

scene = Scene()
parent = scene.root_node.create_child_node("parent")
child  = parent.create_child_node("child")

##Create a quad mesh (four vertices, one polygon)
mesh = Mesh("cube")
mesh.control_points.append(Vector4(0, 0, 0, 1))
mesh.control_points.append(Vector4(1, 0, 0, 1))
mesh.control_points.append(Vector4(1, 1, 0, 1))
mesh.control_points.append(Vector4(0, 1, 0, 1))
mesh.create_polygon(0, 1, 2, 3)

child.add_entity(mesh)

print(f"Mesh name:      {mesh.name}")
print(f"Vertex count:   {len(mesh.control_points)}")
print(f"Polygon count:  {mesh.polygon_count}")
```

`Vector4(x, y, z, w)` represents a homogeneous coordinate. Use `w=1` for regular point positions.

`create_polygon(*indices)` accepts vertex indices and registers one face in the polygon list. Pass three indices for a triangle, four for a quad.

---

### Step 4: Set Node Transforms

Each node has a `Transform` that controls its position, orientation, and size in local space:

```python
from aspose.threed.utilities import Vector3, Quaternion

##Translate the node 2 units along the X axis
child.transform.translation = Vector3(2.0, 0.0, 0.0)

##Scale the node to half its natural size
child.transform.scale = Vector3(0.5, 0.5, 0.5)

##Rotate 45 degrees around the Y axis using Euler angles
child.transform.euler_angles = Vector3(0.0, 45.0, 0.0)
```

Transforms are cumulative: a child node's world-space position is the composition of its own transform with all ancestor transforms. Read the evaluated world-space result from `node.global_transform` (immutable, read-only).

---

### Step 5: Traverse the Scene Graph Recursively

Walk the entire tree by recursing through `node.child_nodes`:

```python
def traverse(node, depth=0):
    indent = "  " * depth
    entity_type = type(node.entity).__name__ if node.entity else "None"
    print(f"{indent}{node.name} [{entity_type}]")
    for child in node.child_nodes:
        traverse(child, depth + 1)

traverse(scene.root_node)
```

Example output for the scene built above:

```
RootNode [None]
  parent [None]
    child [Mesh]
```

For scenes with multiple entities per node, iterate `node.entities` instead of `node.entity`:

```python
def traverse_full(node, depth=0):
    indent = "  " * depth
    entity_names = [type(e).__name__ for e in node.entities] or ["None"]
    print(f"{indent}{node.name} [{', '.join(entity_names)}]")
    for child in node.child_nodes:
        traverse_full(child, depth + 1)

traverse_full(scene.root_node)
```

---

### Step 6: Save the Scene

Pass a file path to `scene.save()`. The format is inferred from the file extension:

```python
scene.save("scene.gltf")   # JSON glTF 2.0
scene.save("scene.glb")    # Binary GLB container
scene.save("scene.obj")    # Wavefront OBJ
scene.save("scene.stl")    # STL
```

For format-specific options, pass a save-options object as the second argument:

```python
from aspose.threed.formats import GltfSaveOptions

opts = GltfSaveOptions()
scene.save("scene.gltf", opts)
```

---

## Tips and Best Practices

- **Name every node.** Giving nodes meaningful names makes debugging traversals far easier and ensures names are preserved in the exported file.
- **One mesh per node.** Keeping entities 1:1 with nodes simplifies transforms and collision queries.
- **Use `create_child_node` over manual attachment.** It sets the parent reference automatically and is less error-prone.
- **Read `global_transform` after building the hierarchy.** The world-space result is only stable once all ancestor transforms are set.
- **Do not mutate the tree during traversal.** Adding or removing child nodes while iterating `child_nodes` will produce unpredictable behaviour. Collect nodes first, then modify.
- **Control points use `Vector4`, not `Vector3`.** Always pass `w=1` for ordinary vertex positions; `w=0` represents a direction vector (not a point).

---

## Common Issues

| Issue | Resolution |
|-------|------------|
| `AttributeError: 'NoneType' object has no attribute 'polygons'` | Guard with `if node.entity is not None` before accessing entity properties. A node without entities has `entity = None`. |
| Mesh appears at the origin despite setting `translation` | `transform.translation` applies a local offset. If the parent node itself has a non-identity transform, the world position may differ. Check `global_transform`. |
| Child nodes missing after `scene.save()` / reload | Some formats (OBJ) flatten the hierarchy. Use glTF or COLLADA to preserve the full node tree. |
| `polygon_count` is 0 after `mesh.create_polygon(...)` | Verify that the vertex indices passed to `create_polygon` are within range (`0` to `len(control_points) - 1`). |
| `Node.get_child(name)` returns `None` | The name is case-sensitive. Confirm the exact name string used at creation time. |
| Traversal visits nodes in unexpected order | `child_nodes` returns children in insertion order (the order `add_child_node` / `create_child_node` was called). |
