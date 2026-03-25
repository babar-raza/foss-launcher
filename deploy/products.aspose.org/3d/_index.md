---
canonical: https://products.aspose.org/3d/_index/
canonical_import: Aspose.ThreeD
date: '2026-03-21T18:15:13Z'
dateModified: '2026-03-21T18:15:13Z'
datePublished: '2026-03-21T18:15:13Z'
description: It provides classes like `Scene`, `Node`, `Entity`, and `Group` to model
  3D content, along with format-specific classes such as `FbxFormat`, `GltfFormat`,...
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
lastmod: '2026-03-21T18:15:13Z'
page_role: landing
platform: dotnet
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.3D | Guide
slug: _index
title: Aspose.3D
type: landing
url: /products.aspose.org/3d/_index/
weight: 1
---

## Overview

Aspose.3D is a dotnet 3d library for working with 3D scenes, nodes, and entities. It provides classes like `Scene`, `Node`, `Entity`, and `Group` to model 3D content, along with format-specific classes such as `FbxFormat`, `GltfFormat`, `ObjFormat`, `StlFormat`, `ColladaFormat`, `PlyFormat`, and `TmfFormat` for import and export operations.

Developers use `Aspose.[identifier omitted]` to load, manipulate, and save 3D files across common formats including FBX, GLTF, OBJ, STL, and DAE. The library supports coordinate system configuration, bounding box calculations, and scene graph traversal via methods like `GetBoundingBox()`, `ChildNodes()`, and `ParentNode()`.

## Key Features

Aspose.3D is a dotnet 3d library for working with 3D scenes, nodes, and entities. It provides core classes like `Scene`, `Node`, `Entity`, and format-specific handlers such as `FbxFormat`, `GltfFormat`, and `StlFormat` to load, manipulate, and export 3D content.

- Supports multiple 3D formats including FBX, GLTF, STL, OBJ, and PLY through dedicated format classes like `FbxFormat` and `GltfFormat`.
- Enables scene composition with `Scene`, `Node`, and `Entity` classes to build hierarchical 3D structures.
- Provides bounding box calculations via `GetBoundingBox()` on `Entity` and `Group` for spatial analysis and culling.
- Allows rendering configuration with `ImageRenderOptions` to control background color, shadows, and asset directories.
- Supports coordinate system and axis definitions using `CoordinateSystem` and `Axis` enums for left- or right-handed conventions.
- Includes exception types `ImportException` and `ExportException` for robust error handling during file I/O operations.

## Quick Start

Aspose.3D provides a lightweight .NET 3D engine for loading, saving, and manipulating 3D scenes. Use the `Scene` class to manage 3D content and `Node`, `Entity`, and format classes like `FbxFormat`, `GltfFormat`, and `StlFormat` to handle file I/O operations.

```csharp
using Aspose.[identifier omitted];

var scene = new Scene();
var node = new Node("MyNode");
node.Entity = new Entity("MyEntity");
scene.RootNode.ChildNodes.Add(node);
scene.Save("output.fbx", FbxFormat.FbxFormat());
```

## See Also

Aspose.3D provides a dotnet 3d engine for working with 3D scenes, nodes, and entities. The library supports core formats like `FbxFormat`, `GltfFormat`, `ObjFormat`, `StlFormat`, and `ColladaFormat`, with classes such as `Scene`, `Node`, `Entity`, and `Group` forming the foundational API surface.

- [Explore key 3D features](/blog.aspose.org/3d/dotnet/3d-key-features/)
- [Discover open-source .NET support](/blog.aspose.org/3d/dotnet/introducing-3d-foss-dotnet/)
- [Load 3D files step-by-step](/docs.aspose.org/3d/dotnet/developer-guide/model-loading/)
- [Convert 3D formats easily](/kb.aspose.org/3d/dotnet/how-to-convert-3d-models-dotnet/)
- [Fix common 3D errors](/kb.aspose.org/3d/dotnet/how-to-fix-3d-models-errors-dotnet/)
