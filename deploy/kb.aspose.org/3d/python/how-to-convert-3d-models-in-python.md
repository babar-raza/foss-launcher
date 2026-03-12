---
page_role: howto_article
title: "How to Convert 3D Models in Python"
description: "Convert 3D files between formats in Python using Aspose.3D FOSS. Covers OBJ to STL, OBJ to glTF 2.0, and STL to 3MF with format-specific save options."
date: 2026-01-15
weight: 20
draft: false
type: "topic"
keywords: ["convert 3d model python", "obj to stl python", "obj to gltf python", "3d format conversion python", "aspose 3d convert", "stl to 3mf python"]
step1: "Install aspose-3d-foss from PyPI"
step2: "Load the source model with Scene.from_file() or scene.open()"
step3: "Inspect the loaded scene to verify geometry before converting"
step4: "Save to the target format using scene.save() with save options"
step5: "Verify the output file"
---

Format conversion with Aspose.3D FOSS for Python is a two-step process: load into a `Scene` object, then save to the desired output format. Because all geometry is held in a common in-memory representation, no format-specific intermediate steps are needed. The sections below show the most common conversions with working code.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install the Package

```bash
pip install aspose-3d-foss
```

No system libraries, compilers, or additional runtime dependencies are required.

```python
import aspose.threed
print(aspose.threed.__version__)  # e.g. 26.1.0
```

---

### Step 2: Load the Source Model

Use `Scene.from_file()` for the simplest case — the format is detected automatically from the file extension:

```python
from aspose.threed import Scene

scene = Scene.from_file("model.obj")
```

For OBJ files where you need control over coordinate system or material loading, use `scene.open()` with `ObjLoadOptions`:

```python
from aspose.threed import Scene
from aspose.threed.formats import ObjLoadOptions

options = ObjLoadOptions()
options.flip_coordinate_system = True  # Convert to Z-up if needed
options.enable_materials = True        # Load the accompanying .mtl file
options.normalize_normal = True

scene = Scene()
scene.open("model.obj", options)
```

Both approaches produce an identical `Scene` object for the subsequent save step.

---

### Step 3: Inspect the Loaded Scene

Before committing to a conversion, it is worth checking that the geometry loaded correctly. A missing file, an unsupported FBX feature, or a path issue with a `.mtl` file can all produce an empty scene.

```python
from aspose.threed import Scene
from aspose.threed.entities import Mesh

scene = Scene.from_file("model.obj")

mesh_count = 0
total_vertices = 0

def count_meshes(node) -> None:
    global mesh_count, total_vertices
    for entity in node.entities:
        if isinstance(entity, Mesh):
            mesh_count += 1
            total_vertices += len(entity.control_points)
    for child in node.child_nodes:
        count_meshes(child)

count_meshes(scene.root_node)
print(f"Loaded {mesh_count} mesh(es), {total_vertices} total vertices")

if mesh_count == 0:
    raise ValueError("Scene contains no geometry — check the source file path and format")
```

---

### Step 4: Save to the Target Format

Call `scene.save()` with the output path. Pass a format-specific save-options object for control over binary vs ASCII output, coordinate axes, and compression.

**OBJ to STL (binary)**

```python
from aspose.threed import Scene
from aspose.threed.formats import StlSaveOptions

scene = Scene.from_file("model.obj")

save_opts = StlSaveOptions()
##StlSaveOptions defaults to binary output, which is more compact.

scene.save("model.stl", save_opts)
print("Saved model.stl")
```

**OBJ to glTF 2.0**

```python
from aspose.threed import Scene
from aspose.threed.formats import GltfSaveOptions

scene = Scene.from_file("model.obj")

save_opts = GltfSaveOptions()

scene.save("model.gltf", save_opts)
print("Saved model.gltf")
```

To save as a self-contained GLB binary instead of a `.gltf` + external buffers, change the output extension to `.glb`:

```python
scene.save("model.glb", save_opts)
```

**OBJ to 3MF**

```python
from aspose.threed import Scene
from aspose.threed.formats import ThreeMfSaveOptions

scene = Scene.from_file("model.obj")

save_opts = ThreeMfSaveOptions()

scene.save("model.3mf", save_opts)
print("Saved model.3mf")
```

**STL to glTF 2.0**

The same pattern applies regardless of source format:

```python
from aspose.threed import Scene
from aspose.threed.formats import GltfSaveOptions

scene = Scene.from_file("input.stl")
scene.save("output.gltf", GltfSaveOptions())
print("Saved output.gltf")
```

---

### Step 5: Verify the Output

After saving, confirm the output file exists and has a non-zero size. For a more thorough check, reload it and compare mesh counts:

```python
import os
from aspose.threed import Scene
from aspose.threed.entities import Mesh

output_path = "model.stl"

##Basic file-system check
size = os.path.getsize(output_path)
print(f"Output file size: {size} bytes")
if size == 0:
    raise RuntimeError("Output file is empty — save may have failed silently")

##Round-trip verification: reload and count geometry
def _iter_nodes(node):
    yield node
    for child in node.child_nodes:
        yield from _iter_nodes(child)

reloaded = Scene.from_file(output_path)
mesh_count = sum(
    1
    for node in _iter_nodes(reloaded.root_node)
    for entity in node.entities
    if isinstance(entity, Mesh)
)
print(f"Round-trip check: {mesh_count} mesh(es) in output")
```

{{% /steps %}}

---

## Common Issues and Fixes

**Output file is created but contains no geometry**

The source file may have loaded with zero meshes. Add the inspection step from Step 3 before saving. Also confirm that the file extension matches the actual format — Aspose.3D uses the extension to select the parser.

**glTF output is missing textures**

Aspose.3D FOSS carries geometry and material properties through conversion. If the source OBJ references external image files in the `.mtl`, those image files are not automatically copied alongside the `.gltf`. Copy texture images to the output directory manually after saving.

**STL output looks inside-out (face normals flipped)**

STL does not carry winding-order metadata. If the output normals are inverted, set `StlSaveOptions` options if available, or flip the coordinate system during load: `ObjLoadOptions.flip_coordinate_system = True`.

**`ValueError: unsupported format` when saving**

Check the output file extension is one of `.obj`, `.stl`, `.gltf`, `.glb`, `.dae`, `.3mf`. Extensions are case-sensitive on Linux.

**Very large files cause slow conversion**

Aspose.3D FOSS processes geometry in memory. For files with millions of polygons, ensure sufficient RAM. There is currently no streaming-write API.

---

## Frequently Asked Questions (FAQ)

**Can I convert a file without writing it to disk first?**

The current API requires a file path for both `open()` and `save()`. Use `tempfile.NamedTemporaryFile` if you need to keep intermediate data out of permanent storage.

**Is FBX supported as a source format for conversion?**

FBX tokenization is partially implemented, but the parser is not complete. FBX input may produce incomplete scenes. Use OBJ, STL, glTF, COLLADA, or 3MF as reliable source formats.

**Will materials survive an OBJ-to-glTF conversion?**

Basic Phong/Lambert material properties (diffuse colour) are carried through the `Scene` model and written into the glTF material block. Procedural or custom shader parameters not expressible in the glTF material model are dropped.

**Can I convert multiple files in a loop?**

Yes. Each `Scene.from_file()` call creates an independent object, so a loop over a list of paths is straightforward:

```python
from pathlib import Path
from aspose.threed import Scene
from aspose.threed.formats import StlSaveOptions

source_dir = Path("input")
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

opts = StlSaveOptions()
for obj_file in source_dir.glob("*.obj"):
    scene = Scene.from_file(str(obj_file))
    out_path = output_dir / obj_file.with_suffix(".stl").name
    scene.save(str(out_path), opts)
    print(f"Converted {obj_file.name} -> {out_path.name}")
```

**Does the conversion preserve the scene hierarchy (parent/child nodes)?**

Yes. The node tree is preserved as far as the target format allows. Formats like STL store only flat geometry with no node structure; the hierarchy is flattened on save. Formats like glTF and COLLADA retain the full hierarchy.
