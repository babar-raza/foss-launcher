---
canonical: https://reference.aspose.org/3d/dotnet/io-service/
canonical_import: Aspose.ThreeD
date: '2026-03-23T13:18:57Z'
dateModified: '2026-03-23T13:18:57Z'
datePublished: '2026-03-23T13:18:57Z'
description: It supports registering custom detectors, importers, and exporters to
  extend file format support.
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
seoTitle: Aspose.3D Io Service
slug: io-service
title: Io Service
type: reference_object_page
url: /reference.aspose.org/3d/dotnet/io-service/
weight: 20
---

## Overview

The `IOService` class provides core input/output functionality for Aspose.3D, enabling format detection, import, and export operations. It supports registering custom detectors, importers, and exporters to extend file format support.

| Method | Description | Claim ID |
|--------|-------------|----------|
| `IOService.Instance()` | Returns the singleton instance of the `IOService` | - |
| `RegisterDetector(detector, format)` | Registers a format detector; the format this detector handles | CLM-3d-982d2f |
| `RegisterImporter(importer)` | Registers an importer; the importer to register | CLM-3d-94db71 |
| `RegisterExporter(exporter)` | Registers an exporter; the exporter to register | CLM-3d-e2e9ba |

```csharp
using System;
using System.IO;
using Aspose.[identifier omitted];

var testFile = "../../../../../../../TestData/input/cube.obj";
using var stream = File.OpenRead(testFile);
var scene = new Scene();
scene.Open(stream);
```

## Constructor

The `IOService` class provides core input/output functionality for Aspose.3D. It supports registering importers, exporters, and format detectors to extend file format support. The constructor initializes a new instance of the `IOService` class, which is typically accessed via the singleton `Instance()` method rather than direct instantiation.

| `Name` | Type | Description |
|------|------|-------------|
| `IOService`() | Constructor | Initializes a new instance of the `IOService` class |
| `RegisterImporter`(importer) | Method | Registers the importer to register |
| `RegisterExporter`(exporter) | Method | Registers the exporter to register |
| `RegisterDetector`(detector, format) | Method | Registers the format this detector handles |
| `Instance`() | Static Method | Returns the singleton instance of `IOService` |

## Properties

The `IOService` class provides core I/O functionality for Aspose.3D. It manages registration of importers, exporters, and format detectors. The service exposes a singleton instance via `Instance()` and supports runtime extension of supported formats.

| `Name` | Type | Description |
|------|------|-------------|
| `Instance` | `IOService` | Returns the singleton instance of the `IOService` |
| Exporters | `List<Exporter>` | Collection of registered exporters |
| Importers | `List<Importer>` | Collection of registered importers |
| Detectors | `List<FormatDetector>` | Collection of registered format detectors |

```csharp
using System;
using System.IO;
using Aspose.[identifier omitted];
using Aspose.[identifier omitted].Formats;

// Register a custom exporter and use it
var scene = new Scene();
var exporter = new FbxFormat();
IOService.Instance.RegisterExporter(exporter);

using var stream = new [identifier omitted]();
scene.Save(stream, new FbxSaveOptions());
```

## Methods

The `IOService` class provides methods to register importers, exporters, and format detectors for 3D file processing in Aspose.3D. These methods enable runtime extensibility of supported formats.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `IOService()` | `IOService` | Initializes a new instance of the `IOService` class. |
| `[static] Instance()` | `IOService` | Gets the singleton instance of the `IOService`. |
| `RegisterImporter(importer)` | void | Registers an importer with the service. The importer to register must implement the `Importer` interface. |
| `RegisterExporter(exporter)` | void | Registers an exporter with the service. The exporter to register must implement the `Exporter` interface. |
| `RegisterDetector(detector, format)` | void | Registers a format detector for a specific file format. The format this detector handles is specified by the format parameter. |

The `Exporter.SupportsFormat()` method indicates whether a given exporter can handle a particular format. It returns `True` if supported, `False` otherwise.

## Example

The `IOService` class provides methods to register custom importers, exporters, and format detectors. This enables developers to extend Aspose.3D's format support at runtime. The `RegisterDetector()` method associates a `FormatDetector` with a specific format, and the detector's `Detect()` method returns `True` if the format matches, false otherwise.

```csharp
import Aspose.[identifier omitted]

from Aspose.[identifier omitted] import IOService, ColladaFormat

detector = ColladaFormat()
service = IOService.Instance()
service.RegisterDetector(detector, ColladaFormat())
```

## See Also

The `IOService` class provides methods to register importers, exporters, and format detectors. Use `RegisterImporter()`, `RegisterExporter()`, and `RegisterDetector()` to extend format support at runtime. The `Importer.SupportsFormat()` method returns `True` if the importer supports a given format, otherwise `False`.

- [Aspose.3D API reference](/reference.aspose.org/3d/dotnet/api-overview/)
- [Key 3D features overview](/blog.aspose.org/3d/dotnet/3d-key-features/)
- [Introducing 3D FOSS .NET](/blog.aspose.org/3d/dotnet/introducing-3d-foss-dotnet/)
- [Load files with Aspose.3D](/docs.aspose.org/3d/dotnet/developer-guide/model-loading/)
- [Render 3D models with Aspose.3D](/docs.aspose.org/3d/dotnet/developer-guide/rendering/)
