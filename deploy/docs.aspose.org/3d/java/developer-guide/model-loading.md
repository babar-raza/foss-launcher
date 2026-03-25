---
canonical: https://docs.aspose.org/3d/java/developer-guide/model-loading/
canonical_import: com.aspose.threed
code_import: com.aspose.threed
date: '2026-03-24T16:56:25Z'
dateModified: '2026-03-24T16:56:25Z'
datePublished: '2026-03-24T16:56:25Z'
description: Given a 3D file path or input stream, the library detects its format
  and loads it into a `Scene` object for further processing or conversion.
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
page_role: workflow_page
platform: java
reading_time: 1
robots: index, follow
seoTitle: Load Files with Aspose.3D | Guide
slug: model-loading
title: Load Files with Aspose.3D
type: workflow_page
url: /docs.aspose.org/3d/java/developer-guide/model-loading/
weight: 18
---

## Overview

This guide walks you through loading 3D files using Aspose.3D. Given a 3D file path or input stream, the library detects its format and loads it into a `Scene` object for further processing or conversion.

First, import the Aspose.3D package using `import com.aspose.threed.*;`. Then use `IOService.detectFormat()` to identify the file format from a stream or filename. Next, instantiate the appropriate `LoadOptions` subclass (e.g., `FbxLoadOptions`, `GltfLoadOptions`) and pass it to the `IImporter.load()` method to `parse` the file into a `Scene`.

```java
import com.aspose.threed.*;

// Detect format and load a 3D file
InputStream stream = new FileInputStream("model.fbx");
FileFormat format = IOService.detectFormat(stream, "model.fbx");
LoadOptions options = new FbxLoadOptions();
options.setFileFormat(format);
IImporter importer = new FbxImporter();
Scene scene = importer.load(stream, options);
```

- Use `IOService.getFormatByFileName()` when you know the file extension and want to skip stream-based detection.
- Pass `GltfLoadOptions` or `FbxLoadOptions` to control coordinate system flipping or pretty-printing for GLTF/FBX files.
- Wrap `importer.load()` in a try-catch block to handle `ImportException` for malformed or unsupported files.

## Key Features

This guide walks you through loading 3D files using Aspose.3D, where you provide an input stream or file path and receive a `Scene` object ready for rendering, conversion, or further manipulation. The library supports importing common formats like FBX, GLTF, andPLY through dedicated `load` options classes and the `IOService` utility.

- Supports importing multiple 3D formats including FBX, GLTF, and PLY through format-specific load options like `FbxLoadOptions` and `GltfLoadOptions`.
- Enables coordinate system flipping via `setFlipCoordinateSystem()` to align coordinate conventions between source and target environments.
- Provides automatic format detection using `IOService.detectFormat()` to simplify handling unknown or variable input types.
- Includes `FileFormat` introspection methods like `getCanImport()` and `getCanExport()` to validate format support before processing.
- Offers structured exception handling with `ImportException` and `ExportException` for robust error management during file operations.

## Prerequisites

This guide walks you through loading 3D files using Aspose.3D. You provide a file stream and optional `load` options, and the library returns a `Scene` object ready for rendering or further processing.

- Java Development Kit (JDK) 8 or later
- Aspose.3D for Java library (via Maven or JAR)
- Supported 3D file formats: FBX, GLTF, PLY, PDF, and Microsoft 3MF (based on `FileFormat` support)

Ensure your project includes the Aspose.3D dependency. For Maven, `add` the repository and dependency to `pom.xml`. Use `import com.aspose.threed.*;` at the top of your Java files — no other import paths are valid.

## Code Examples

This guide walks you through loading 3D files using Aspose.3D. You start by detecting the file format, then `load` the file into a `Scene` object using the appropriate `load` options, and finally inspect or process the loaded content.

```java
import com.aspose.threed.*;

// Detect format and load a 3D file
String filePath = "model.fbx";
FileFormat detectedFormat = IOService.getFormatByFileName(filePath);
LoadOptions loadOptions = new LoadOptions();
loadOptions.setFileFormat(detectedFormat);
Scene scene = new Scene();
scene.open(filePath, loadOptions);
```

- Use `IOService.getFormatByFileName()` to infer the format from the file extension before loading.
- Set the detected format on `LoadOptions` to ensure correct parsing behavior.
- Call `Scene.open()` with the file path and configured `LoadOptions` to load the content.

For binary or coordinate-sensitive formats like FBX or glTF, configure `load` options to handle coordinate system differences. This ensures the loaded geometry aligns with your target rendering pipeline.

```java
import com.aspose.threed.*;

// Load FBX with coordinate system flip enabled
FbxLoadOptions fbxOptions = new FbxLoadOptions();
fbxOptions.setFlipCoordinateSystem(true);
Scene scene = new Scene();
scene.open("input.fbx", fbxOptions);

// Access root nodes and entities
for (Node node : scene.getRootNodes()) {
    Entity entity = node.getEntity();
    if (entity != null) {
        System.out.println("Entity type: " + entity.getClass().getSimpleName());
    }
}
```

- Enable `setFlipCoordinateSystem(true)` for FBX files when importing into a left-handed coordinate system.
- Iterate over getRootNodes() to inspect the scene hierarchy.
- Use `getEntity()` on each node to retrieve geometry or other entity types for further processing.

When loading from a stream instead of a file, use `IOService.detectFormat()` to determine the format dynamically, then pass the stream and options to `Scene.open()`.

```java
import com.aspose.threed.*;
import java.io.FileInputStream;

// Load from InputStream with format detection
FileInputStream stream = new FileInputStream("model.gltf");
FileFormat format = IOService.detectFormat(stream, "model.gltf");
GltfLoadOptions gltfOptions = new GltfLoadOptions();
gltfOptions.setPrettyPrint(false);
Scene scene = new Scene();
scene.open(stream, gltfOptions);
stream.close();
```

- Use `IOService.detectFormat(stream, fileName)` when reading from non-file sources like HTTP responses or archives.
- Configure `GltfLoadOptions` to control pretty-printing and coordinate system behavior.
- Close the stream after loading to avoid resource leaks.

## Notes and Best Practices

When loading 3D files with Aspose.3D, always validate the input format before processing to avoid runtime exceptions. Use `FileFormat.identify()` to `detect` supported formats and confirm compatibility with your target use case, especially since USD and ASCII FBX remain unsupported.

- Use `FileFormatType` enums to programmatically verify format support before calling `Scene.open()`.
- Handle `ExportException` when saving to catch issues like unsupported export features (e.g., MTL export or vertex deduplication).
- Prefer explicit class imports (e.g., `import com.aspose.threed.Scene;`) over wildcard imports for better maintainability in production code.
- For large files, consider using `Cancellation` tokens to allow graceful interruption during import or export operations.

## See Also

- [Explore 3D key features](/blog.aspose.org/3d/java/3d-key-features/)
- [Learn about translation transforms](/blog.aspose.org/3d/java/introducing-3d-foss-java/)
- [Render 3D models](/docs.aspose.org/3d/java/developer-guide/rendering/)
- [Convert file formats](/kb.aspose.org/3d/java/how-to-convert-fbx-to-gltf-java/)
- [Fix common errors](/kb.aspose.org/3d/java/how-to-fix-3d-models-errors-java/)
