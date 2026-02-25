---
title: "How to Save a File"
---

## Goal

This guide explains how to save 3D scenes to disk using Aspose.3D for Python. You will learn how to export scenes in different formats using the Scene.save() method. [claim: c9]

## When You'd Use This

Use this approach when you need to export processed 3D models to a file, for example after applying transformations or merging multiple scenes.

## Prerequisites

- Aspose.3D for Python installed (`pip install aspose-3d`).
- Python 3.8 or later.
- A loaded Scene object with 3D content.

## Steps

1. Import the Aspose.3D library.
2. Load or create a Scene with 3D content. [claim: c4]
3. Call `Scene.save()` with the output path and desired format. [claim: c9]
4. Verify the output file was written successfully.

## Aspose.3D for Python Code Example

```python
import aspose.threed as a3d

# Load an existing scene
scene = a3d.Scene()
scene.open("input_model.fbx")

# Save to OBJ format
scene.save("output_model.obj", a3d.FileFormat.WAVEFRONT_OBJ)

# Save to STL format for 3D printing
scene.save("output_model.stl", a3d.FileFormat.STL_BINARY)

print("Files saved successfully.")
```

## Common Mistakes

- Specifying an output directory that does not exist.
- Forgetting to specify the file format parameter.
- Attempting to save an empty scene with no geometry.

## See Also

- [How to Open a File](../how-to-open-a-file/)
- [Getting Started](../getting-started/)
