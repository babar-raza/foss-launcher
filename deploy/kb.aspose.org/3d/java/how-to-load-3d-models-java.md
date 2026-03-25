---
canonical: https://kb.aspose.org/3d/java/how-to-load-3d-models-java/
canonical_import: com.aspose.threed
code_import: com.aspose.threed
date: '2026-03-24T16:56:25Z'
dateModified: '2026-03-24T16:56:25Z'
datePublished: '2026-03-24T16:56:25Z'
description: The library supports importing files via format-specific importers registered
  at runtime, with format detection handled by `IOService`.
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
page_role: howto_article
platform: java
reading_time: 1
robots: index, follow
seoTitle: How to Load Files with Aspose.3D | Guide
slug: how-to-load-3d-models-java
title: How to Load Files with Aspose.3D
type: howto_article
url: /kb.aspose.org/3d/java/how-to-load-3d-models-java/
weight: 11
---

## Problem

You will `load` a 3D file into Aspose.3D using the `IImporter` interface and `LoadOptions` to prepare a `Scene` for further processing. The library supports importing files via format-specific importers registered at runtime, with format detection handled by `IOService`.

- Java Development Kit (JDK) 8 or later
- Aspose.3D for Java library (com.aspose.threed package)

## Prerequisites

You will `load` 3D files using Aspose.3D by setting up your Java environment and importing the required package. This section covers the minimal setup needed before loading any supported format.

- Java Development Kit (JDK) version 8 or higher
- Aspose.3D Java library added to your project classpath
- Import statement: `import com.aspose.threed.*;`

## Loading the File

You will `load` 3D files using Aspose.3D by specifying a file path or stream and applying optional `load` settings via `LoadOptions`, `FbxLoadOptions`, or `GltfLoadOptions`. The `Scene` class and `IImporter` interface handle file ingestion, while `IOService` helps `detect` formats.

- Java Development Kit (JDK) 8 or later
- Aspose.3D for Java library (com.aspose.threed package)

### Load a file from a file path

Use `Scene` with a file path string to `load` a 3D model. The library auto-detects the format using the file extension unless you explicitly `set` it via `LoadOptions`.

```java
import com.aspose.threed.*;

Scene scene = new Scene("model.fbx");
```

This creates a `Scene` instance populated with entities from the file. Supported formats include FBX, GLTF, and others listed in `FileFormat`.

### Load from a stream with explicit format

When reading from a stream, use `IOService.detectFormat()` to infer the format, then pass it to `LoadOptions` before loading.

```java
import com.aspose.threed.*;

FileFormat format = IOService.getFormatByFileName("model.gltf");
LoadOptions options = new LoadOptions();
options.setFileFormat(format);
Scene scene = new Scene();
scene.open(stream, options);
```

This ensures correct parsing when the stream lacks a file extension or when loading from non-file sources like network responses.

### Apply format-specific `load` options

For FBX or GLTF files, use `FbxLoadOptions` or `GltfLoadOptions` to control coordinate system flipping and other format-specific behaviors.

```java
import com.aspose.threed.*;

FbxLoadOptions options = new FbxLoadOptions();
options.setFlipCoordinateSystem(true);
Scene scene = new Scene("model.fbx", options);
```

This configures the loader to convert between right-handed and left-handed coordinate systems, which is essential for compatibility with certain rendering engines.

### Error handling

Wrap loading operations in a try-catch block to handle `ImportException` and IOException. These exceptions indicate unsupported formats, corrupted files, or I/O failures.

```java
import com.aspose.threed.*;

try {
  Scene scene = new Scene("model.fbx");
} catch (ImportException e) {
  System.err.println("Failed to import file: " + e.getMessage());
} catch (IOException e) {
  System.err.println("I/O error: " + e.getMessage());
}
```

This ensures robust handling of malformed or unrecognized files during runtime.

### Next steps

After loading, explore the scene graph using `Entity`, `Node`, and `Geometry` classes. You can also `export` the scene to other formats using `IExporter` implementations.

## Code Example

You will `load` a 3D file using Aspose.3D, inspect its contents, and print a summary of its entities. This example uses the `Scene` class to `open` a file, the `Entity` class to access geometric objects, and the `FileFormat` class to `detect` and verify the format.

- Java Development Kit (JDK) 8 or later
- Aspose.3D for Java library added to your project's classpath

### Load and Inspect a 3D File

Step 1: Detect the file format using `IOService.getFormatByFileName()` to ensure compatibility before loading.

```java
import com.aspose.threed.*;

String filePath = "model.fbx";
FileFormat format = IOService.getFormatByFileName(filePath);
System.out.println("Detected format: " + format);

if (!format.getCanImport()) {
    throw new [identifier omitted]("Format does not support import.");
}
```

This prints the detected format and checks `getCanImport()` to confirm the file can be loaded.

### Load the File and Inspect Entities

Step 2: Load the file into a `Scene` object using the appropriate importer.

```java
Scene scene = new Scene();
scene.open(filePath);

int entityCount = 0;
for (Entity entity : scene.getRootNode().getChildNodes()) {
    entityCount++;
    System.out.println("Entity " + entityCount + ": " + entity.getClass().getSimpleName());
}

System.out.println("Total entities: " + entityCount);
```

This opens the file, iterates over child nodes, and prints the type and count of `Entity` instances found.

### Error Handling

Wrap file operations in try-catch blocks to handle `ImportException` and IOException. The `IOService.detectFormat()` method may throw IOException, while `Scene.open()` may throw `ImportException`.

```java
try {
    Scene scene = new Scene();
    scene.open(filePath);
} catch (ImportException e) {
    System.err.println("Import failed: " + e.getMessage());
} catch (IOException e) {
    System.err.println("IO error: " + e.getMessage());
}
```

This ensures robust handling of malformed or unsupported files during loading.

## Supported Formats

Aspose.3D supports loading multiple 3D file formats through the `FileFormat` and `IOService` classes. You can `detect` a file's format using `IOService.detectFormat()` or infer it from the file extension using `IOService.getFormatByFileName()`. The `FileFormat` class exposes format metadata via `getCanImport()` and `getCanExport()` methods.

| Format | Extension | Notes |
|--------|-----------|-------|
| FBX | .fbx | Import only; ASCII format not supported |
| GLTF | .gltf, .glb | Import and `export` |
| PLY | .ply | Import only |
| Draco | .drc | Import only |
| 3MF | .3mf | Import only |
| PDF | .pdf | Import only |

## See Also

You will explore related documentation for Aspose.3D to deepen your understanding of file handling workflows. The API supports loading, saving, and converting 3D formats using classes like `FbxImporter`, `FbxExporter`, `GltfExporter`, and `FileFormat`. These tools enable integration into Java-based 3d java game engine or 3d java skins projects.

- [Frequently asked questions](/kb.aspose.org/3d/java/faq/)
- [Key capabilities overview](/blog.aspose.org/3d/java/3d-key-features/)
- [Translation transform support](/blog.aspose.org/3d/java/introducing-3d-foss-java/)
- [Load files step-by-step](/docs.aspose.org/3d/java/developer-guide/model-loading/)
- [Render 3D models guide](/docs.aspose.org/3d/java/developer-guide/rendering/)
