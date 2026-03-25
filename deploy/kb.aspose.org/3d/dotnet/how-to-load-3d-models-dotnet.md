---
canonical: https://kb.aspose.org/3d/dotnet/how-to-load-3d-models-dotnet/
canonical_import: Aspose.ThreeD
code_import: Aspose.ThreeD
date: '2026-03-24T16:49:31Z'
dateModified: '2026-03-24T16:49:31Z'
datePublished: '2026-03-24T16:49:31Z'
description: The `Scene` class provides the entry point for file loading, and format-specific
  classes like `ObjFormat`, `StlFormat`, `FbxFormat`, and `GltfFormat`...
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
lastmod: '2026-03-24T16:49:31Z'
page_role: howto_article
platform: dotnet
reading_time: 1
robots: index, follow
seoTitle: How to Load Files with Aspose.3D | Guide
slug: how-to-load-3d-models-dotnet
title: How to Load Files with Aspose.3D
type: howto_article
url: /kb.aspose.org/3d/dotnet/how-to-load-3d-models-dotnet/
weight: 11
---

## Problem

You will load a 3D file (e.g., OBJ, STL, FBX, GLTF) into an Aspose.3D `Scene` object using the appropriate format class and `CreateLoadOptions()` method. The `Scene` class provides the entry point for file loading, and format-specific classes like `ObjFormat`, `StlFormat`, `FbxFormat`, and `GltfFormat` support detection and loading via their static instances in `FileFormat`.

- Install the Aspose.3D .NET package via NuGet.
- Add `using Aspose.ThreeD;` at the top of your C# file.

## Prerequisites

You will load 3D files using Aspose.3D by initializing the `Scene` class and specifying the input file path. Ensure you have the Aspose.3D .NET library installed and reference it with the correct using directive.

- Install Aspose.3D for .NET via NuGet Package Manager: `Install-Package Aspose.3D`
- Use .NET 6 or later for compatibility
- Include `using Aspose.ThreeD;` at the top of your C# file

## Loading the File

You will load 3D files into an Aspose.3D `Scene` object using file paths or streams, with optional format-specific load settings. The `Scene` class serves as the root container for 3D content, and supported formats include OBJ, STL, FBX, GLTF, and COLLADA.

- A .NET project targeting .NET Framework 4.6.1 or later
- Aspose.3D for .NET NuGet package installed

### Load a 3D file from a file path

Call the `Scene` constructor with the file path to load a supported 3D model. The library automatically detects the format using file extension and content inspection.

```csharp
using Aspose.[identifier omitted];

var scene = new Scene("model.fbx");
```

This creates a `Scene` instance populated with the entities, nodes, and geometry from the FBX file.

### Load from a stream with explicit format

When loading from a stream, specify the format explicitly using the corresponding format class to avoid ambiguity.

```csharp
using Aspose.[identifier omitted];
using System.IO;

using var stream = File.OpenRead("scene.stl");
var scene = new Scene(stream, StlFormat.Instance);
```

This loads the STL file content from the stream into the `Scene` object, using the `StlFormat` class to ensure correct parsing.

### Load with custom options

Use the `CreateLoadOptions()` method on the format class to obtain a load options object, then pass it to the `Scene` constructor.

```csharp
using Aspose.[identifier omitted];

var options = ColladaFormat.Instance.CreateLoadOptions();
var scene = new Scene("model.dae", ColladaFormat.Instance, options);
```

This allows configuration of format-specific loading behavior, such as coordinate system handling or unit scaling.

### Error handling

Wrap loading operations in a try-catch block to handle `ImportException` for malformed files or unsupported formats, and `ExportException` for I/O failures.

Check the file path or stream validity before loading to avoid runtime exceptions. Use `CanDetect()` on format classes to verify format support for a given stream or file name.

### Next steps

After loading, explore the `Scene`'s `RootNode`, `ChildNodes`, and `Entity` members to inspect or modify the 3D content. See how to traverse the scene graph or export to other formats.

## Code Example

You will load a 3D file using Aspose.3D, inspect its scene structure, and print a summary of its nodes and entities. This example uses the canonical .NET import and demonstrates core loading and introspection capabilities.

- A supported 3D file (e.g., .obj, .stl, .fbx, .gltf, .ply, .dae) available locally
- Aspose.3D for .NET installed via NuGet

### Load and Inspect a 3D `Scene`

Call `Scene()` to create an empty scene, then use `Scene.Open()` to load a file. The `Scene` object exposes `SubScenes()` and `Library()` for navigation.

```csharp
using Aspose.[identifier omitted];

var scene = new Scene();
scene.Open("model.fbx");

Console.WriteLine($"Scene loaded with {scene.SubScenes().Count} subscenes and {scene.Library().Count} entities.");
```

This prints the count of subscenes and library entities after loading the file. The `Scene` object now holds the full hierarchy for further inspection.

### Traverse Nodes and `Entities`

Iterate over `Scene.RootNode.ChildNodes()` to access each node. For each node, call `Entity()` to retrieve its associated entity, if any.

```csharp
foreach (var node in scene.RootNode.ChildNodes())
{
    Console.WriteLine($"Node: {node.AssetInfo().Name}");
    var entity = node.Entity();
    if (entity != null)
        Console.WriteLine($"  Entity type: {entity.GetType().Name}");
}
```

This outputs each node's name and its entity type (e.g., `Mesh`, `Group`, `Entity`). Use `GetBoundingBox()` on nodes or entities to retrieve spatial bounds.

### Error Handling

```csharp
try
{
    scene.Open("model.fbx");
}
catch (ImportException ex)
{
    Console.WriteLine($"Failed to import: {ex.Message}");
}
```

This ensures robust handling of invalid or corrupted input files during loading operations.

## Supported Formats

You will load 3D files using Aspose.3D by specifying the appropriate format class. The library supports a limited set of input formats, each represented by a dedicated format class in the `Aspose.[identifier omitted]` namespace.

| `Format` | `Extension` | Notes |
|--------|-----------|-------|
| Collada | .dae | Uses `ColladaFormat` class |
| FBX | .fbx | Uses `FbxFormat` class |
| GLTF | .gltf, .glb | Uses `GltfFormat` class |
| OBJ | .obj | Uses `ObjFormat` class |
| STL | .stl | Uses `StlFormat` class |
| TMF | .tmf | Uses `TmfFormat` class |
| PLY | .ply | Uses `PlyFormat` class |

## See Also

You will load 3D files using Aspose.3D classes such as `Scene` and format-specific readers like `ColladaReader`. This section points to related how-to guides for saving, converting, and working with supported formats.

- [Frequently asked questions](/kb.aspose.org/3d/dotnet/faq/)
- [Core capabilities overview](/blog.aspose.org/3d/dotnet/3d-key-features/)
- [Open-source .NET integration](/blog.aspose.org/3d/dotnet/introducing-3d-foss-dotnet/)
- [Step-by-step file loading guide](/docs.aspose.org/3d/dotnet/developer-guide/model-loading/)
- [Rendering 3D models tutorial](/docs.aspose.org/3d/dotnet/developer-guide/rendering/)
