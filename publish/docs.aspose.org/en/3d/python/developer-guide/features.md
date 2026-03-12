---
page_role: howto_article
title: Features and Functionalities
description: >-
  Comprehensive guide to Aspose.3D FOSS for Python features — format support,
  scene graph, mesh API, materials, math utilities, animation, load/save
  options, and complete Python code examples.
type: docs
weight: 10
---

Aspose.3D FOSS for Python provides a complete scene-graph API for reading, constructing, and writing 3D content in multiple industry-standard formats. This page documents every major feature area with working Python code examples that use the actual library API.

## Installation and Setup

Install the library from PyPI with a single command:

```bash
pip install aspose-3d-foss
```

No additional system packages, native extensions, or compiler toolchains are required. The library is pure Python and supports Python 3.7 through 3.12 on Windows, macOS, and Linux.

To verify the installation:

```python
from aspose.threed import Scene

scene = Scene()
print("Aspose.3D FOSS installed successfully")
print(f"Root node name: {scene.root_node.name}")
```

## Features and Functionalities

### Format Support

Aspose.3D FOSS for Python reads and writes the following formats:

| Format | Extension | Read | Write | Notes |
|--------|-----------|:----:|:-----:|-------|
| Wavefront OBJ | `.obj` | Yes | Yes | .mtl material loading supported |
| STL (binary) | `.stl` | Yes | Yes | Roundtrip verified (39 tests) |
| STL (ASCII) | `.stl` | Yes | Yes | Roundtrip verified |
| glTF 2.0 | `.gltf` | Yes | Yes | Full scene graph preserved |
| GLB (binary glTF) | `.glb` | Yes | Yes | Single-file binary container |
| COLLADA | `.dae` | Yes | Yes | Scene hierarchy and materials |
| 3MF | `.3mf` | Yes | Yes | Additive manufacturing format |
| FBX | `.fbx` | Partial | No | Tokenizer working; parser has known bugs |

#### Loading OBJ with Options

`ObjLoadOptions` controls how OBJ files are parsed:

```python
from aspose.threed import Scene
from aspose.threed.formats.obj import ObjLoadOptions

options = ObjLoadOptions()
options.enable_materials = True        # Load accompanying .mtl file
options.flip_coordinate_system = False # Preserve original handedness
options.normalize_normal = True        # Normalize vertex normals to unit length
options.scale = 1.0                    # Apply a uniform scale factor at load time

scene = Scene()
scene.open("model.obj", options)

print(f"Loaded {len(scene.root_node.child_nodes)} top-level nodes")
```

#### Saving to STL

`StlSaveOptions` controls binary vs. ASCII output and other STL-specific settings:

```python
from aspose.threed import Scene
from aspose.threed.formats.stl import StlSaveOptions

scene = Scene.from_file("model.obj")
options = StlSaveOptions()
scene.save("output.stl", options)
```

### Scene Graph

All 3D content is organized as a tree of `Node` objects. The root of the tree is `scene.root_node`. Every node can contain child nodes and carry an `Entity` (mesh, camera, or light) plus a `Transform`.

#### Traversing the Scene Hierarchy

```python
from aspose.threed import Scene

scene = Scene.from_file("model.glb")

def traverse(node, depth=0):
    indent = "  " * depth
    entity_type = type(node.entity).__name__ if node.entity else "none"
    print(f"{indent}{node.name} [{entity_type}]")
    for child in node.child_nodes:
        traverse(child, depth + 1)

traverse(scene.root_node)
```

#### Building a Scene Programmatically

```python
from aspose.threed import Scene, Node, Entity
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector3

scene = Scene()
root = scene.root_node

##Create a child node and position it
child = root.create_child_node("my_object")
child.transform.translation = Vector3(1.0, 0.0, 0.0)
child.transform.scale = Vector3(2.0, 2.0, 2.0)

scene.save("constructed.glb")
```

#### Inspecting GlobalTransform

`GlobalTransform` gives the world-space transform of a node after accumulating all ancestor transforms:

```python
from aspose.threed import Scene

scene = Scene.from_file("model.dae")

for node in scene.root_node.child_nodes:
    gt = node.global_transform
    print(f"Node: {node.name}")
    print(f"  World translation: {gt.translation}")
    print(f"  World scale: {gt.scale}")
```

### Mesh API

The `Mesh` entity gives access to geometry data including control points (vertices), polygons, and vertex elements for normals, UVs, and colors.

#### Reading Mesh Geometry

```python
from aspose.threed import Scene
from aspose.threed.formats.obj import ObjLoadOptions

options = ObjLoadOptions()
options.enable_materials = True
options.flip_coordinate_system = False

scene = Scene()
scene.open("model.obj", options)

for node in scene.root_node.child_nodes:
    if node.entity is None:
        continue
    mesh = node.entity
    print(f"Mesh: {node.name}")
    print(f"  Vertices: {len(mesh.control_points)}")
    print(f"  Polygons: {len(mesh.polygons)}")
```

#### Accessing Vertex Elements

Vertex elements carry per-vertex or per-polygon data. The most common elements are normals, UV coordinates, vertex colors, and smoothing groups:

```python
from aspose.threed import Scene
from aspose.threed.entities import VertexElementNormal, VertexElementUV

scene = Scene.from_file("model.obj")

for node in scene.root_node.child_nodes:
    if node.entity is None:
        continue
    mesh = node.entity

    # Iterate vertex elements to find normals and UVs
    for element in mesh.vertex_elements:
        if isinstance(element, VertexElementNormal):
            print(f"  Normals count: {len(element.data)}")
        elif isinstance(element, VertexElementUV):
            print(f"  UV count: {len(element.data)}")
```

### Material System

Aspose.3D FOSS supports two material types: `LambertMaterial` (diffuse shading) and `PhongMaterial` (specular shading). Both are loaded automatically from .mtl files when using `ObjLoadOptions` with `enable_materials = True`.

#### Reading Materials from OBJ

```python
from aspose.threed import Scene
from aspose.threed.shading import LambertMaterial, PhongMaterial
from aspose.threed.formats.obj import ObjLoadOptions

options = ObjLoadOptions()
options.enable_materials = True

scene = Scene()
scene.open("model.obj", options)

for node in scene.root_node.child_nodes:
    mat = node.material
    if mat is None:
        continue
    print(f"Node: {node.name}")
    if isinstance(mat, PhongMaterial):
        print(f"  Type: Phong")
        print(f"  Diffuse: {mat.diffuse_color}")
        print(f"  Specular: {mat.specular_color}")
    elif isinstance(mat, LambertMaterial):
        print(f"  Type: Lambert")
        print(f"  Diffuse: {mat.diffuse_color}")
```

#### Assigning a Material Programmatically

```python
from aspose.threed import Scene, Node
from aspose.threed.shading import PhongMaterial
from aspose.threed.utilities import Vector3

scene = Scene.from_file("model.glb")

material = PhongMaterial()
material.diffuse_color = Vector3(0.8, 0.2, 0.2)   # Red diffuse
material.specular_color = Vector3(1.0, 1.0, 1.0)  # White specular

##Apply to the first mesh node
for node in scene.root_node.child_nodes:
    if node.entity is not None:
        node.material = material
        break

scene.save("recolored.glb")
```

### Math Utilities

The `aspose.threed.utilities` module provides all geometric math types needed for scene construction and inspection.

| Class | Purpose |
|-------|---------|
| `Vector2` | 2D floating-point vector (UV coordinates) |
| `Vector3` | 3D double-precision vector (positions, normals) |
| `Vector4` | 4D double-precision vector (homogeneous coordinates) |
| `FVector3` | 3D single-precision vector (compact storage) |
| `Quaternion` | Rotation representation without gimbal lock |
| `Matrix4` | 4×4 transformation matrix |
| `BoundingBox` | Axis-aligned bounding box with min/max corners |

#### Working with Transforms

```python
from aspose.threed.utilities import Vector3, Quaternion, Matrix4
import math

##Build a rotation quaternion from axis-angle
axis = Vector3(0.0, 1.0, 0.0)          # Y-axis
angle_rad = math.radians(45.0)
q = Quaternion.from_angle_axis(angle_rad, axis)

print(f"Quaternion: x={q.x:.4f} y={q.y:.4f} z={q.z:.4f} w={q.w:.4f}")

##Convert to rotation matrix
mat = q.to_matrix()
print(f"Rotation matrix row 0: {mat[0, 0]:.4f} {mat[0, 1]:.4f} {mat[0, 2]:.4f}")
```

#### Computing a Bounding Box

```python
from aspose.threed import Scene
from aspose.threed.utilities import BoundingBox

scene = Scene.from_file("model.stl")

##BoundingBox can be obtained from the scene or computed manually
for node in scene.root_node.child_nodes:
    if node.entity is None:
        continue
    mesh = node.entity
    bb = mesh.get_bounding_box()
    size = bb.maximum - bb.minimum
    print(f"Mesh: {node.name}")
    print(f"  Min: {bb.minimum}")
    print(f"  Max: {bb.maximum}")
    print(f"  Size: {size}")
```

### Animation

Aspose.3D FOSS provides an animation model based on `AnimationClip`, `AnimationNode`, `KeyFrame`, and `KeyframeSequence`. Animation data stored in loaded files (glTF, COLLADA) is accessible through these objects.

#### Reading Animation Clips

```python
from aspose.threed import Scene

scene = Scene.from_file("animated.glb")

for clip in scene.animation_clips:
    print(f"Clip: {clip.name}  Duration: {clip.description}")
    for anim_node in clip.animations:
        print(f"  Animated node: {anim_node.name}")
        for channel in anim_node.channels:
            print(f"    Channel: {channel.target_property}  Keys: {len(channel.keyframe_sequence.keyframes)}")
```

### Load and Save Options

Every supported format has a corresponding options class that controls parsing and serialization behavior.

| Class | Format | Key Properties |
|-------|--------|---------------|
| `ObjLoadOptions` | OBJ | `enable_materials`, `flip_coordinate_system`, `normalize_normal`, `scale` |
| `StlSaveOptions` | STL | Binary vs. ASCII output mode |
| (glTF uses defaults) | glTF / GLB | Scene graph and materials preserved automatically |

---

## Usage Examples

### Example 1: OBJ to STL Format Conversion

Convert an OBJ file (with materials) to binary STL, printing mesh statistics along the way:

```python
from aspose.threed import Scene
from aspose.threed.formats.obj import ObjLoadOptions
from aspose.threed.formats.stl import StlSaveOptions

##Load OBJ with material support
load_opts = ObjLoadOptions()
load_opts.enable_materials = True
load_opts.flip_coordinate_system = False
load_opts.normalize_normal = True

scene = Scene()
scene.open("input.obj", load_opts)

##Report what was loaded
total_vertices = 0
total_polygons = 0
for node in scene.root_node.child_nodes:
    if node.entity is not None:
        mesh = node.entity
        total_vertices += len(mesh.control_points)
        total_polygons += len(mesh.polygons)
        print(f"  {node.name}: {len(mesh.control_points)} vertices, {len(mesh.polygons)} polygons")

print(f"Total: {total_vertices} vertices, {total_polygons} polygons")

##Save as STL
save_opts = StlSaveOptions()
scene.save("output.stl", save_opts)
print("Saved output.stl")
```

### Example 2: Batch glTF to GLB Packing

Re-save a directory of separate glTF + texture files as self-contained GLB binaries:

```python
import os
from aspose.threed import Scene

input_dir = "gltf_files"
output_dir = "glb_files"
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if not filename.endswith(".gltf"):
        continue
    src = os.path.join(input_dir, filename)
    dst = os.path.join(output_dir, filename.replace(".gltf", ".glb"))
    scene = Scene.from_file(src)
    scene.save(dst)
    print(f"Packed {filename} -> {os.path.basename(dst)}")
```

### Example 3: Scene Graph Inspection and Export Report

Walk a COLLADA file's scene graph, collect per-mesh statistics, and print a structured report:

```python
from aspose.threed import Scene

scene = Scene.from_file("assembly.dae")

report = []

def collect(node, path=""):
    full_path = f"{path}/{node.name}" if node.name else path
    if node.entity is not None:
        mesh = node.entity
        gt = node.global_transform
        report.append({
            "path": full_path,
            "vertices": len(mesh.control_points),
            "polygons": len(mesh.polygons),
            "world_x": gt.translation.x,
            "world_y": gt.translation.y,
            "world_z": gt.translation.z,
        })
    for child in node.child_nodes:
        collect(child, full_path)

collect(scene.root_node)

print(f"{'Path':<40} {'Verts':>6} {'Polys':>6} {'X':>8} {'Y':>8} {'Z':>8}")
print("-" * 78)
for entry in report:
    print(
        f"{entry['path']:<40} "
        f"{entry['vertices']:>6} "
        f"{entry['polygons']:>6} "
        f"{entry['world_x']:>8.3f} "
        f"{entry['world_y']:>8.3f} "
        f"{entry['world_z']:>8.3f}"
    )
```

---

## Tips and Best Practices

### Format Selection

- **glTF 2.0 / GLB** is the recommended interchange format for scenes that include materials, animations, and complex hierarchies. Prefer GLB (binary) over glTF (text + external files) for portability.
- **STL** is the right choice when the downstream consumer is a slicer, CAD tool, or any tool that only needs geometry — STL carries no material or animation data.
- **OBJ** is widely supported and a good choice when material data must be exchanged with older tools. Always keep the .mtl file alongside the .obj file.

### Coordinate Systems

- Different applications use different handedness conventions. Set `ObjLoadOptions.flip_coordinate_system = True` when importing OBJ files from tools that use a right-handed coordinate system if your pipeline expects left-handed coordinates, and vice versa.
- Verify the axis convention of the source asset before applying any flip — flipping twice produces incorrect geometry.

### Normalization

- Always set `ObjLoadOptions.normalize_normal = True` when the downstream pipeline expects unit normals (for example, when passing normals to a shader or doing dot-product lighting calculations). Unnormalized normals from poorly-formed OBJ files cause lighting artifacts.

### Performance

- Load files once and transform the in-memory scene graph rather than reloading from disk for each output format. A single `Scene.from_file()` call followed by multiple `scene.save()` calls is more efficient than repeated loads.
- When processing large batches, construct a single `ObjLoadOptions` or `StlSaveOptions` instance and reuse it across all files instead of constructing a new options object per file.

### Error Handling

- Wrap `scene.open()` and `scene.save()` calls in `try/except` blocks when processing untrusted or user-supplied files. Report the filename in exception messages to simplify debugging in batch pipelines.

---

## Common Issues

| Issue | Cause | Resolution |
|-------|-------|------------|
| Mesh appears mirrored after loading | Coordinate system handedness mismatch | Toggle `ObjLoadOptions.flip_coordinate_system` |
| Normals are zero-length | Source file has unnormalized normals | Set `ObjLoadOptions.normalize_normal = True` |
| Materials not loaded from OBJ | `enable_materials` is `False` (default) | Set `ObjLoadOptions.enable_materials = True` |
| Scene loads but all nodes are empty | File uses FBX format | FBX parser is in progress; use OBJ, STL, or glTF instead |
| Model is extremely small or large | Source file uses non-metric units | Apply `ObjLoadOptions.scale` to convert to your target unit |
| `AttributeError` on `mesh.polygons` | Node entity is not a Mesh | Guard with `if node.entity is not None` before accessing entity properties |
| GLB file is rejected by viewer | Saved with `.gltf` extension | Use `.glb` extension when calling `scene.save()` to trigger binary container |

---

## Frequently Asked Questions

**What Python versions are supported?**
Python 3.7, 3.8, 3.9, 3.10, 3.11, and 3.12 are all supported. The library is pure Python with no native extension, so it works on any platform where CPython runs.

**Does the library have any external dependencies?**
No. Aspose.3D FOSS for Python has zero external dependencies beyond the Python standard library. It installs as a single `pip install aspose-3d-foss` command with no follow-on steps.

**Is FBX supported?**
The FBX tokenizer is implemented and can parse the binary FBX token stream, but the scene-graph builder on top of the tokenizer has known bugs and is not production-ready. Use OBJ, STL, glTF, COLLADA, or 3MF for reliable production use.

**Can I use Aspose.3D FOSS in a commercial product?**
Yes. The library is released under the MIT license, which permits use in proprietary and commercial software without royalty payments, provided the license notice is included.

**How do I report a bug or request a format?**
Open an issue in the repository. Include a minimal reproducer file and the Python version, operating system, and library version from `pip show aspose-3d-foss`.

---

## API Reference Summary

### Core Classes

- **`Scene`** — Top-level container for a 3D scene. Entry point for `open()`, `from_file()`, and `save()`.
- **`Node`** — Tree node in the scene graph. Carries `entity`, `transform`, `global_transform`, `material`, `child_nodes`, and `name`.
- **`Entity`** — Base class for objects attached to nodes (Mesh, Camera, Light).
- **`Transform`** — Local-space position, rotation (Quaternion), and scale for a node.
- **`GlobalTransform`** — Read-only world-space transform computed by accumulating all ancestor transforms.

### Geometry

- **`Mesh`** — Polygon mesh with `control_points` (vertex list) and `polygons`.
- **`VertexElementNormal`** — Per-vertex or per-polygon normal vectors.
- **`VertexElementUV`** — Per-vertex UV texture coordinates.
- **`VertexElementVertexColor`** — Per-vertex color data.
- **`VertexElementSmoothingGroup`** — Polygon smoothing group assignments.

### Materials

- **`LambertMaterial`** — Diffuse shading model with `diffuse_color` and `emissive_color`.
- **`PhongMaterial`** — Specular shading model adding `specular_color` and `shininess`.

### Math Utilities (`aspose.threed.utilities`)

- **`Vector2`** — 2D vector.
- **`Vector3`** — 3D double-precision vector.
- **`Vector4`** — 4D double-precision vector.
- **`FVector3`** — 3D single-precision vector.
- **`Quaternion`** — Rotation quaternion with `from_angle_axis()` and `to_matrix()`.
- **`Matrix4`** — 4×4 transformation matrix.
- **`BoundingBox`** — Axis-aligned bounding box with `minimum` and `maximum` corners.

### Animation

- **`AnimationClip`** — Named container for a set of animation channels and their keyframes.
- **`AnimationNode`** — Per-node animation data within a clip.
- **`KeyFrame`** — Single keyframe with time and value.
- **`KeyframeSequence`** — Ordered sequence of keyframes for a single animated property.

### Load / Save Options

- **`ObjLoadOptions`** — OBJ-specific load settings: `enable_materials`, `flip_coordinate_system`, `normalize_normal`, `scale`.
- **`StlSaveOptions`** — STL-specific save settings (binary vs. ASCII mode).

### Cameras and Lights

- **`Camera`** — Camera entity with projection settings, attachable to a `Node`.
- **`Light`** — Light source entity, attachable to a `Node`.
