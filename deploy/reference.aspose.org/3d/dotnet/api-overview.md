---
canonical: https://reference.aspose.org/3d/dotnet/api-overview/
canonical_import: Aspose.ThreeD
date: '2026-03-22T15:30:08Z'
dateModified: '2026-03-22T15:30:08Z'
datePublished: '2026-03-22T15:30:08Z'
description: It supports format detection, import, and export via public APIs such
  as `IOService.RegisterDetector()`, `FormatDetector.Detect()`, and...
display_name: Aspose.3D
family: 3d
keywords:
- dotnet 3d
- dotnet 3d engine
- dotnet 3d library
- is .net 3.5 safe
- shapr 3d cost
- difference between dotnet and dotnet framework
- 3d symptoms
- python 3d logo
lastmod: '2026-03-22T15:30:08Z'
page_role: api_reference
platform: dotnet
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D API Reference | Guide
slug: api-overview
title: Aspose.3D API Reference
type: api_reference
url: /reference.aspose.org/3d/dotnet/api-overview/
weight: 6
---

## Overview

Aspose.3D provides a .NET 3D engine for loading, saving, and manipulating 3D scenes. It supports format detection, import, and export via public APIs such as `IOService.RegisterDetector()`, `FormatDetector.Detect()`, and `ColladaReader.Import()`.

| Method | Description |
|--------|-------------|
| `IOService.RegisterDetector(detector, format)` | Registers a format detector; the format parameter specifies the format this detector handles |
| `FormatDetector.Detect()` | Returns true if the format matches, false otherwise |
| `ColladaReader.Import()` | Public API method for importing Collada files |

```csharp
using System;
using System.IO;
using Aspose.[identifier omitted];
using Aspose.[identifier omitted].Formats;

var scene = new Scene();
scene.Open(File.OpenRead("input.fbx"));
```

## Public API

The Aspose.3D API provides a focused set of core classes for 3D scene manipulation, format I/O, and entity management in .NET applications. Developers interact primarily with `Scene`, `Node`, `Entity`, and format-specific classes like `FbxFormat`, `GltfFormat`, and `StlFormat`. The `IOService` class serves as the central registry for importers, exporters, and format detectors, enabling extensibility and custom format support.

| Class | Description |
|-------|-------------|
| `ColladaFormat` | Handles COLLADA (.dae) file format operations including detection, loading, and saving. |
| `Entity` | Base class for all 3D entities; provides bounding box and parent node access. |
| `ExportException` | Exception type thrown during export operations. |
| `FbxFormat` | Handles Autodesk FBX file format operations including detection, loading, and saving. |
| `FileFormat` | Static factory class providing access to common format instances like `ObjFormat`, `StlFormat`, `GltfFormat`, `FbxFormat`, and `TmfFormat`. |
| `GltfFormat` | Handles glTF file format operations including detection, loading, and saving. |
| `Group` | Container for grouping multiple entities; supports bounding box computation. |
| `ImageRenderOptions` | Configuration for rendering 3D scenes to images, including background color and shadow settings. |
| `ImportException` | Exception type thrown during import operations. |
| `IOService` | Central service for registering importers, exporters, and format detectors; provides singleton access via `Instance()`. |
| `Node` | `Scene` graph node that can hold geometry, transforms, and child nodes. |
| `ObjFormat` | Handles Wavefront OBJ file format operations. |
| `PlyFormat` | Handles Polygon File `Format` (PLY) operations. |
| `Scene` | Top-level container for 3D scenes, managing root nodes and global settings. |
| `StlFormat` | Handles STL (stereolithography) file format operations. |

`Format` detection and registration are handled through the `IOService` singleton. To register a custom importer, call `IOService.Instance().RegisterImporter(importer)`, where importer must implement the `Importer` interface and support format detection via `SupportsFormat()`. Similarly, exporters and detectors are registered using `RegisterExporter()` and `RegisterDetector()`, with the latter requiring the specific format it handles. These mechanisms enable runtime extensibility for new 3D formats without modifying the core library.

## Common Patterns

Aspose.3D provides a streamlined workflow for loading, detecting, and exporting 3D scenes using its core API surface. Developers can register custom importers, exporters, and format detectors via the `IOService` singleton to extend format support. The `IOService.RegisterExporter()` method accepts an exporter instance to register for saving scenes, while `IOService.RegisterImporter()` and `IOService.RegisterDetector()` handle loading and format detection respectively.

```csharp
using System;
using System.IO;
using Aspose.[identifier omitted];

var testFile = "../../../../../../../TestData/input/cube.obj";

if (!File.Exists(testFile))
{
    throw new [identifier omitted]($"Test file not found: {testFile}");
}

using var stream = File.OpenRead(testFile);
var scene = new Scene();
scene.Open(stream);

var node = scene.RootNode.ChildNodes[0];
var mesh = node.Entities[0] as Mesh;
```

`Format` detection is supported via the `FormatDetector.Detect()` method, which returns true if the input stream matches a known format. Exporters can be queried for format compatibility using `Exporter.SupportsFormat()`. These methods enable robust, dynamic handling of 3D file formats in production environments.

The `Mesh.CreatePolygon()` method is part of the public API and supports direct mesh construction for custom geometry. This allows developers to programmatically define polygonal faces without relying on external file imports.

## See Also

Developers evaluating Aspose.3D for .NET 3D processing can verify format support at runtime using `Exporter.SupportsFormat()` and `Importer.SupportsFormat()`, both returning `True if supported, false otherwise`. The `SaveOptions.ExportTextures()` property is part of the public API for texture export configuration.

- [Io Service reference](/reference.aspose.org/3d/dotnet/io-service/)
- [Get started with Aspose.3D](/docs.aspose.org/3d/dotnet/developer-guide/getting-started/)
- [Installation guide](/docs.aspose.org/3d/dotnet/developer-guide/installation/)
- [Frequently asked questions](/kb.aspose.org/3d/dotnet/faq/)
- [Troubleshooting tips](/kb.aspose.org/3d/dotnet/troubleshooting/)
