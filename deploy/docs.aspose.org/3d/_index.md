---
canonical: https://docs.aspose.org/3d/_index/
canonical_import: com.aspose.threed
code_import: com.aspose.threed
date: '2026-03-24T16:56:25Z'
dateModified: '2026-03-24T16:56:25Z'
datePublished: '2026-03-24T16:56:25Z'
description: It supports import/`export` via `IImporter` and `IExporter` interfaces,
  with format-specific options like `FbxLoadOptions`, `GltfSaveOptions`, and...
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
page_role: toc
platform: java
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.3D Docs _Index
slug: _index
title: Docs _Index
type: toc
url: /docs.aspose.org/3d/_index/
weight: 2
---

## Capabilities

This section covers Aspose.3D for Java, a library for loading, saving, and manipulating 3D scenes using the `com.aspose.threed` package. It supports import/`export` via `IImporter` and `IExporter` interfaces, with format-specific options like `FbxLoadOptions`, `GltfSaveOptions`, and `FileFormat` detection.

- Load and save 3D scenes in supported formats (FBX, GLTF,PLY, Draco, PDF, Microsoft 3MF)
- Configure coordinate system handling and file format options via `LoadOptions` and `SaveOptions` subclasses
- Inspect and modify scene entities using `Entity`, `Geometry`, and `Node` relationships
- Render scenes to images using `ImageRenderOptions` and custom renderers via `EntityRendererKey`

## Quick Install

This section covers installation and setup for Aspose.3D, a Java library for 3D model import, `export`, and manipulation. The library provides core classes such as `Scene`, `Node`, `Entity`, `Geometry`, and format-specific options like `FbxLoadOptions` and `GltfSaveOptions`.

```java
import com.aspose.threed.*;
```

## Getting Started

This section covers the Java API for loading, exporting, and rendering 3D scenes using Aspose.3D. The library provides core classes such as `Scene`, `Node`, `Entity`, and `Geometry`, along with format-specific loaders and exporters like `FbxImporter`, `GltfExporter`, and `IImporter`/`IExporter` interfaces.

- Load 3D files — parse formats like FBX, GLTF, OBJ using `IImporter` and `LoadOptions`
- Export scenes — write to supported formats via `IExporter` and `SaveOptions`
- Render to images — generate 2D views using `ImageRenderOptions`
- Format detection — identify file formats from streams or filenames using `IOService`

## Developer Guide

This section covers the Java API for 3D model loading, saving, and scene manipulation in Aspose.3D. It includes core classes for handling file formats, scene graphs, and rendering configuration.

Use `FileFormat` to `detect` and validate supported formats via `getFormatByExtension()` and `getCanImport()`/`getCanExport()` checks. The `IOService` class provides static methods like `detectFormat()` and `registerFormat()` for runtime format handling.

Load and `save` operations use `IImporter` and `IExporter` interfaces with format-specific options such as `FbxLoadOptions`, `GltfSaveOptions`, and `LoadOptions`. Exceptions like `ImportException` and `ExportException` handle I/O errors during conversion.

`Scene` graph entities (`Entity`, `Geometry`) support visibility, shadow casting, and parent-child relationships via `getParentNode()`, `setParentNode()`, and `getExcluded()`. Renderer keys (`EntityRendererKey`) define rendering features using `EntityRendererFeatures`.

## See Also

This section covers core Aspose.3D Java API classes for 3D model import, `export`, and scene manipulation. It includes file format handling via `FileFormat` and `IOService`, import/`export` interfaces `IImporter` and `IExporter`, and foundational scene graph entities like `Entity` and `Geometry`.

- [File Format Support](file-formats.md) — supported 3D formats, extension mapping, and format capabilities (`getCanImport()`, `getCanExport()`)
- [Import and Export](import-export.md) — load scenes from streams using `IImporter` and `IImporter`, save using `IExporter`
- [Scene Graph Entities](scene-graph.md) — working with `Entity`, `Geometry`, and node hierarchy via `getParentNode()` and `setParentNode()`
- [Format-Specific Options](format-options.md) — configure import/export behavior with `FbxLoadOptions`, `GltfSaveOptions`, and `LoadOptions`
