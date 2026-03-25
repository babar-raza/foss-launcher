---
canonical: https://blog.aspose.org/3d/java/3d-key-features/
canonical_import: com.aspose.threed
code_import: com.aspose.threed
date: '2026-03-24T16:56:25Z'
dateModified: '2026-03-24T16:56:25Z'
datePublished: '2026-03-24T16:56:25Z'
description: It supports key operations for 3D content pipelines in Java-based applications.
display_name: Aspose.3D
family: 3d
keywords:
- 3d javascript
- 3d javascript library
- 3d java
- 3d java skins
- 3d javascript game engine
- 3d javascript game
- 3d javascript framework
- 3d java game engine
lastmod: '2026-03-24T16:56:25Z'
page_role: feature_blog
platform: java
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D 3d Key Features
slug: 3d-key-features
title: 3d Key Features
type: feature_blog
url: /blog.aspose.org/3d/java/3d-key-features/
weight: 17
---

## Introduction

If you have ever needed to `load`, convert, or `export` 3D models in Java without external dependencies, Aspose.3D provides a lightweight, API-driven approach using classes like `FileFormat`, `FbxImporter`, `FbxExporter`, `GltfExporter`, and `Geometry`. It supports key operations for 3D content pipelines in Java-based applications.

- Load 3D scenes from FBX, GLTF, or OBJ files using `FbxImporter` or `GltfData`
- Export scenes to FBX, GLTF, OBJ, or STL formats via `FbxExporter` and `GltfExporter`
- Manipulate geometry and entities using `Geometry`, `Entity`, and `A3DObject`

## Key Highlights

If you have ever needed to `load` or `export` 3D scenes in Java without external dependencies, Aspose.3D provides a lightweight, import-only API for common formats like FBX, GLTF, and OBJ. The library exposes core classes such as `FileFormat`, `LoadOptions`, `FbxLoadOptions`, and `GltfLoadOptions` to handle format detection, coordinate system flipping, and scene import.

- Import 3D scenes from FBX, GLTF, and OBJ files using `FileFormat` and `LoadOptions` to detect and configure format-specific behavior.
- Flip coordinate systems during import or export with `FbxLoadOptions`, `FbxSaveOptions`, `GltfLoadOptions`, and `GltfSaveOptions` to align with target rendering pipelines.
- Export scenes to FBX, GLTF, OBJ, and STL formats using `IExporter` implementations like `FbxExporter` and `GltfExporter`.
- Validate format support at runtime using `FileFormat.getCanImport()` and `FileFormat.getCanExport()` before attempting I/O operations.

```java
import com.aspose.threed.*;

// Detect format and load a GLTF file with coordinate system flip
FileFormat format = FileFormat.getFormatByExtension("model.gltf");
if (format.getCanImport()) {
    GltfLoadOptions opts = new GltfLoadOptions();
    opts.setFlipCoordinateSystem(true);
    Scene scene = Scene.load("model.gltf", opts);
    System.out.println("Loaded GLTF with flipped coordinate system");
}
```

The `FileFormat` class enables runtime detection of supported formats via `getFormatByExtension()` and `getCanImport()`. This avoids hard-coded assumptions and lets developers adapt to missing or unimplemented formats gracefully. For example, `FileFormat.getFormatByExtension("model.fbx")` returns a valid `FileFormat` instance only if FBX import is implemented in the current build.

Coordinate system flipping is essential when moving between left-handed (e.g., Unity) and right-handed (e.g., Blender) systems. The `setFlipCoordinateSystem(true)` method on `FbxLoadOptions` and `GltfLoadOptions` ensures geometry orientation remains consistent across platforms. This is especially critical for game engines and visualization tools that expect a specific handedness.

## Getting Started

If you have ever needed to `load` or `export` 3D scenes in Java using standardized formats like FBX, GLTF, or OBJ, Aspose.3D provides a minimal, import-driven API for handling these operations. The library exposes core classes like `FileFormat`, `LoadOptions`, `FbxLoadOptions`, and `GltfSaveOptions` to manage format detection, loading, and saving with coordinate system control.

```java
import com.aspose.threed.*;

Scene scene = new Scene();
FileFormat format = FileFormat.getFormatByExtension("model.fbx");
FbxLoadOptions loadOpts = new FbxLoadOptions();
loadOpts.setFlipCoordinateSystem(true);
// scene.getRootNode().getChildren().add(new Entity()); // minimal scene setup
// scene.save("output.fbx", new FbxSaveOptions()); // export example
```

The `FileFormat.getFormatByExtension()` method detects supported formats by file extension, returning a `FileFormat` instance that indicates import/`export` capability via `getCanImport()` and `getCanExport()`. For FBX and GLTF, `load` and `save` options include `setFlipCoordinateSystem()` to align coordinate conventions between tools.

- Detect supported formats using `FileFormat.getFormatByExtension()` and verify import/export support via `getCanImport()` and `getCanExport()`.
- Configure coordinate system alignment for FBX and GLTF using `FbxLoadOptions.setFlipCoordinateSystem()` or `GltfSaveOptions.setFlipCoordinateSystem()`.
- Construct a `Scene` and attach `Entity` or `Geometry` nodes to build a minimal 3D structure before saving.

## See Also

- [Apply translation transforms to nodes](/blog.aspose.org/3d/java/introducing-3d-foss-java/)
- [Load 3D files efficiently](/docs.aspose.org/3d/java/developer-guide/model-loading/)
- [Render 3D models in your app](/docs.aspose.org/3d/java/developer-guide/rendering/)
- [Convert between 3D formats](/kb.aspose.org/3d/java/how-to-convert-fbx-to-gltf-java/)
- [Resolve common 3D errors](/kb.aspose.org/3d/java/how-to-fix-3d-models-errors-java/)
