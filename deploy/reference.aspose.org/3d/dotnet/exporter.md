---
canonical: https://reference.aspose.org/3d/dotnet/exporter/
canonical_import: Aspose.ThreeD
date: '2026-03-23T13:18:57Z'
dateModified: '2026-03-23T13:18:57Z'
datePublished: '2026-03-23T13:18:57Z'
description: It works in conjunction with format-specific classes like `FbxFormat`,
  `ObjFormat`, and `StlFormat` to serialize scene data.
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
lastmod: '2026-03-23T13:18:57Z'
page_role: reference_object_page
platform: dotnet
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D Exporter
slug: exporter
title: Exporter
type: reference_object_page
url: /reference.aspose.org/3d/dotnet/exporter/
weight: 21
---

## Overview

The `Exporter` class in Aspose.3D enables programmatic export of 3D scenes to supported file formats. It works in conjunction with format-specific classes like `FbxFormat`, `ObjFormat`, and `StlFormat` to serialize scene data.

## Constructor

The `Exporter` class in Aspose.3D provides constructors to initialize instances for exporting 3D scenes to various formats. Constructor overloads support default initialization and configuration via format-specific options.

| Constructor | Parameters | Description |
|-------------|------------|-------------|
| `Exporter()` | None | Initializes a new instance of the `Exporter` class with default settings. |
| `Exporter(FileFormat)` | format: `FileFormat` | Initializes a new instance of the `Exporter` class for the specified output format. |
| `Exporter(FileFormat, SaveOptions)` | format: `FileFormat`, options: `SaveOptions` | Initializes a new instance of the `Exporter` class for the specified format and custom save options. |

## Properties

The `Exporter` class in Aspose.3D provides programmatic control over 3D export operations. It exposes properties that define export behavior, such as target format, coordinate system, and unit scaling. These properties are used in conjunction with the `Scene` and `FileFormat` classes to configure export pipelines for formats like `FbxFormat`, `GltfFormat`, `StlFormat`, and `ObjFormat`.

| `Name` | Type | Description |
|------|------|-------------|
| `Format` | `FileFormat` | Specifies the target file format for export. |
| `CoordinateSystem` | `CoordinateSystem` | Defines the coordinate system used during export (LeftHanded or RightHanded). |
| UnitScale | double | Sets the scaling factor applied to geometry units during export. |
| `AxisSystem` | `AxisSystem` | Configures the primary axis orientation for the exported scene. |
| `AssetDirectories` | `string[]` | Specifies directories where external assets (e.g., textures) are located. |
| `EnableShadows` | `bool` | Enables or disables shadow rendering in the exported scene. |
| `BackgroundColor` | `Color` | Sets the background color used when rendering the scene. |
| `Name` | string | Assigns a display name to the exported asset. |
| Visible | `bool` | Controls whether the exported entity is visible by default. |
| `AssetInfo` | `AssetInfo` | Provides metadata about the exported asset, such as author and creation date. |

## Methods

Aspose.3D -- Method table: signature, return type, description.

For details on methods, see the Aspose.3D documentation.

## Example

This example demonstrates exporting a 3D scene to a supported format using Aspose.3D. It constructs a minimal scene with a node and entity, then saves it using a registered exporter from the `FileFormat` class.

```csharp
import Aspose.[identifier omitted]

scene = Aspose.[identifier omitted].Scene()
node = Aspose.[identifier omitted].Node()
entity = Aspose.[identifier omitted].Entity("MyEntity")
node.Entity = entity
scene.RootNode.ChildNodes.Add(node)
scene.Save("output.fbx", Aspose.[identifier omitted].FbxFormat())
```

## See Also

The `Exporter` class in Aspose.3D enables programmatic export of 3D scenes to supported formats. Related classes include `Scene`, `Node`, and format-specific exporters like `FbxFormat`, `ObjFormat`, and `StlFormat`.

- [Explore 3D key features](/blog.aspose.org/3d/dotnet/3d-key-features/)
- [Introducing 3D FOSS .NET](/blog.aspose.org/3d/dotnet/introducing-3d-foss-dotnet/)
- [Load files with Aspose.3D](/docs.aspose.org/3d/dotnet/developer-guide/model-loading/)
- [Convert file formats](/kb.aspose.org/3d/dotnet/how-to-convert-3d-models-dotnet/)
- [Fix common errors](/kb.aspose.org/3d/dotnet/how-to-fix-3d-models-errors-dotnet/)
