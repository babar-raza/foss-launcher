---
page_role: howto_article
title: Format Support
description: >-
  Complete guide to 3D format support in Aspose.3D FOSS for Python — OBJ, STL,
  glTF/GLB, COLLADA, 3MF, and FBX (partial), with load/save options and
  auto-detection details.
weight: 30
type: docs
---

Aspose.3D FOSS for Python can read and write seven 3D formats using a single in-memory scene representation. The library translates each format into a common `Scene` object on load and serialises that object back to the target format on save. This means a scene loaded from OBJ can be saved directly to glTF without any intermediate conversion steps.

---

## Supported Formats

| Format | Extension | Read | Write | Options class | Notes |
|--------|-----------|:----:|:-----:|---------------|-------|
| Wavefront OBJ | `.obj` | Yes | Yes | `ObjLoadOptions` | `.mtl` material loading supported |
| STL (binary) | `.stl` | Yes | Yes | `StlSaveOptions` | Binary and ASCII read; save defaults to binary |
| STL (ASCII) | `.stl` | Yes | Yes | `StlSaveOptions` | Round-trip verified |
| glTF 2.0 | `.gltf` | Yes | Yes | `GltfSaveOptions` | Full scene graph, materials, and animations preserved |
| GLB (binary glTF) | `.glb` | Yes | Yes | `GltfSaveOptions` | Single-file binary container |
| COLLADA | `.dae` | Yes | Yes | — | Scene hierarchy and materials |
| 3MF | `.3mf` | Yes | Yes | `ThreeMfSaveOptions` | Additive manufacturing format |
| FBX | `.fbx` | Partial | No | — | Tokenizer working; full parser is in progress — **not production-ready** |

---

## OBJ Format

Wavefront OBJ is the most widely supported interchange format for static meshes. Aspose.3D FOSS loads geometry (vertices, normals, UV coordinates, and polygonal faces) and optionally the companion `.mtl` material file.

### ObjLoadOptions

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_materials` | `bool` | `True` | Parse the `.mtl` file referenced by the OBJ header |
| `flip_coordinate_system` | `bool` | `False` | Convert from Y-up right-handed to Z-up right-handed |
| `normalize_normal` | `bool` | `False` | Normalise all imported surface normals to unit length |
| `scale` | `float` | `1.0` | Uniform scale factor applied to all vertex positions |
| `file_name` | `str` | `""` | Override the `.mtl` search name |

### Loading an OBJ file

```python
from aspose.threed import Scene
from aspose.threed.formats import ObjLoadOptions

options = ObjLoadOptions()
options.enable_materials = True
options.flip_coordinate_system = False
options.scale = 1.0

scene = Scene()
scene.open("model.obj", options)

print(f"Top-level nodes: {len(scene.root_node.child_nodes)}")
```

### Saving to OBJ

```python
scene.save("output.obj")
```

OBJ export writes vertex positions and polygon faces. If the scene contains `LambertMaterial` or `PhongMaterial` objects, the library writes a companion `.mtl` file automatically.

---

## STL Format

STL (STereoLithography) stores triangle meshes as an unindexed list of facets. Both binary and ASCII variants are supported for reading; the library defaults to binary on save.

### StlSaveOptions

`StlSaveOptions` has no mandatory fields. Instantiate it to pass to `scene.save()`:

```python
from aspose.threed.formats import StlSaveOptions

opts = StlSaveOptions()
scene.save("output.stl", opts)
```

### Round-trip example

```python
from aspose.threed import Scene

##Load
scene = Scene.from_file("model.stl")

##Inspect
for node in scene.root_node.child_nodes:
    if node.entity:
        print(f"{node.name}: {len(node.entity.control_points)} vertices")

##Save
scene.save("roundtrip.stl")
```

STL stores only triangle geometry — no normals beyond the facet normal, no UV coordinates, no materials, and no hierarchy. If your scene contains quads or higher-order polygons, they are triangulated automatically on save.

---

## glTF / GLB Format

glTF 2.0 is the recommended format for modern 3D exchange. It preserves the full scene graph (node hierarchy, named nodes, transforms), materials (`LambertMaterial`, `PhongMaterial` → PBR conversion), and animation clips. GLB is the single-file binary container variant.

### GltfSaveOptions

```python
from aspose.threed.formats import GltfSaveOptions

opts = GltfSaveOptions()
scene.save("output.gltf", opts)   # JSON + external .bin
scene.save("output.glb",  opts)   # Self-contained binary
```

### Material support

Aspose.3D FOSS materials are mapped to glTF `pbrMetallicRoughness` on export:

```python
from aspose.threed import Scene
from aspose.threed.shading import PhongMaterial
from aspose.threed.utilities import Vector3

scene = Scene()
node = scene.root_node.create_child_node("object")

mat = PhongMaterial()
mat.diffuse_color  = Vector3(0.8, 0.2, 0.2)   # red
mat.specular_color = Vector3(1.0, 1.0, 1.0)
mat.shininess = 50.0
node.material = mat

scene.save("colored.gltf")
```

### Verifying glTF output

```python
import json

with open("output.gltf") as f:
    data = json.load(f)

print(f"Asset version : {data['asset']['version']}")
print(f"Nodes         : {len(data.get('nodes', []))}")
print(f"Meshes        : {len(data.get('meshes', []))}")
```

---

## COLLADA Format

COLLADA (`.dae`) is an XML-based format that supports scene hierarchies, materials, multiple UV channels, and skeletal animation. Aspose.3D FOSS reads and writes the full node tree and material definitions.

```python
from aspose.threed import Scene

##Load a COLLADA file
scene = Scene.from_file("model.dae")

##Inspect top-level nodes
for node in scene.root_node.child_nodes:
    print(f"  {node.name}")

##Save back to COLLADA
scene.save("output.dae")
```

COLLADA is a good choice when you need to round-trip hierarchies with named nodes and materials without any data loss.

---

## 3MF Format

3MF (3D Manufacturing Format) targets additive manufacturing (3D printing) workflows. It stores triangle geometry, colour, and print-specific metadata in a ZIP-based container.

```python
from aspose.threed import Scene
from aspose.threed.formats import ThreeMfSaveOptions

scene = Scene.from_file("part.stl")   # Load from STL
opts  = ThreeMfSaveOptions()
scene.save("part.3mf", opts)          # Write as 3MF
```

3MF is the recommended export format when targeting slicer software (Cura, PrusaSlicer, Bambu Studio, etc.).

---

## FBX Format

> **Status: in progress — not production-ready.**

FBX (`.fbx`) support in Aspose.3D FOSS is currently at the tokenizer stage. The binary FBX tokenizer can parse the file structure, but the full node, mesh, and material parser has known bugs and is not complete. FBX read results should be treated as experimental.

**Do not use FBX in production pipelines with this release.** If your source data is in FBX, convert it to glTF or OBJ first using Blender or FBX Review before loading with Aspose.3D FOSS.

FBX write is not supported.

---

## Format Auto-Detection

`Scene.from_file()` and `scene.open()` detect the format automatically using the file extension and, where available, magic bytes in the file header:

```python
from aspose.threed import Scene

##The library detects each format without being told explicitly
scene_obj  = Scene.from_file("model.obj")
scene_glb  = Scene.from_file("model.glb")
scene_stl  = Scene.from_file("model.stl")
scene_dae  = Scene.from_file("model.dae")
scene_3mf  = Scene.from_file("model.3mf")
```

If the extension is absent or ambiguous, the library falls back to header inspection (magic bytes). Unsupported or unrecognised files raise an `IOError` with a descriptive message.

---

## Tips and Best Practices

- **Use glTF or GLB for modern pipelines.** glTF preserves the full scene graph, materials, and animation data. It is the most complete format for interchange with game engines and web viewers.
- **Use OBJ for maximum compatibility.** OBJ is supported by virtually every 3D tool. It is limited to static meshes but is extremely portable.
- **Use 3MF for printing.** 3MF carries colour, orientation hints, and print settings that STL cannot express.
- **Avoid FBX until it is production-ready.** Check the release notes for the version in which full FBX parsing is complete.
- **Match save extension to format.** Do not pass a `.gltf` extension when you want binary GLB — use `.glb` explicitly. The extension determines which serialiser is used.
- **Check polygon compatibility.** STL and 3MF require triangles. Quads and N-gons are triangulated automatically on save, but vertex count will increase. If you need to control triangulation, call `mesh.triangulate()` before saving.
