---
title: "How to Convert Formats"
---

## Goal

This guide explains how to convert 3D models between supported formats using Aspose.3D for Python. The library supports converting FBX to OBJ and OBJ to STL among other format pairs. [claim: c6]

## When You'd Use This

Use this approach when you need to convert 3D model files between different formats, such as converting FBX models to OBJ for web display or exporting OBJ meshes to STL for 3D printing.

## Prerequisites

- Aspose.3D for Python installed (`pip install aspose-3d`).
- Python 3.8 or later.
- A source 3D model file in FBX, OBJ, or STL format.

## Steps

1. Import the Aspose.3D library.
2. Create a Scene and load the source file. [claim: c8]
3. Choose the target format (FBX, OBJ, or STL). [claim: c1] [claim: c2] [claim: c3]
4. Call `scene.save()` with the target format to perform the conversion. [claim: c9]
5. Verify the output file.

## Aspose.3D for Python Code Example

```python
import aspose.threed as a3d

# Convert FBX to OBJ
scene = a3d.Scene()
scene.open("model.fbx")
scene.save("model.obj", a3d.FileFormat.WAVEFRONT_OBJ)

# Convert OBJ to STL for 3D printing
scene2 = a3d.Scene()
scene2.open("model.obj")
scene2.save("model.stl", a3d.FileFormat.STL_BINARY)

print("Conversion complete.")
```

## Common Mistakes

- Attempting to convert to a format that is not supported by the library.
- Losing material data when converting from FBX to STL (STL does not support materials).
- Not checking the file format compatibility before conversion.

## See Also

- [How to Open a File](../how-to-open-a-file/)
- [How to Save a File](../how-to-save-a-file/)
