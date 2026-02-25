---
title: "How to Open a File"
---

## Goal

This guide explains how to open and load 3D model files using Aspose.3D for Python. You will learn how to use the Scene class to load files with automatic format detection. [claim: c8]

## When You'd Use This

Use this approach when you need to load 3D models from disk in your Python application, for example when building a model viewer or processing pipeline.

## Prerequisites

- Aspose.3D for Python installed (`pip install aspose-3d`).
- Python 3.8 or later.
- A 3D model file in a supported format (FBX, OBJ, or STL).

## Steps

1. Import the Aspose.3D library into your Python script.
2. Create a new Scene instance — this is the root container for all 3D objects. [claim: c4]
3. Call `Scene.open()` with the path to your 3D file. The library auto-detects the format. [claim: c8]
4. Access the loaded geometry through `scene.root_node`.

## Aspose.3D for Python Code Example

```python
import aspose.threed as a3d

# Create a new scene and load a 3D file
scene = a3d.Scene()
scene.open("input_model.fbx")

# Access the root node and iterate child nodes
root = scene.root_node
for node in root.child_nodes:
    print(f"Node: {node.name}")
    if node.entity and isinstance(node.entity, a3d.entities.Mesh):
        mesh = node.entity
        print(f"  Vertices: {len(mesh.control_points)}")
```

## Common Mistakes

- Forgetting to install the library before importing it.
- Passing a file path that does not exist or lacks read permissions.
- Trying to open an unsupported file format without checking first.

## See Also

- [Getting Started](../getting-started/)
- [FAQ](../faq/)
