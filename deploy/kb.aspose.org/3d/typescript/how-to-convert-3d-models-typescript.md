---
canonical: https://kb.aspose.org/3d/typescript/how-to-convert-3d-models-typescript/
canonical_import: '@aspose/3d-foss'
code_import: '@aspose/3d-foss'
date: '2026-03-24T16:58:44Z'
dateModified: '2026-03-24T16:58:44Z'
datePublished: '2026-03-24T16:58:44Z'
description: The canonical import path is `@aspose/3d-foss`, and only the listed classes
  in the API surface are available for this operation.
display_name: Aspose.3D
family: 3d
keywords:
- 3d typescript
- 3d typescript game engine
- typescript 3d library
- typescript 3d logo
- typescript 3d array
- typescript 3d engine
- typescript 3d model
- typescript 3d game
lastmod: '2026-03-24T16:58:44Z'
page_role: howto_article
platform: typescript
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.3D | Guide
slug: how-to-convert-3d-models-typescript
title: How to Convert File Formats with Aspose.3D
type: howto_article
url: /kb.aspose.org/3d/typescript/how-to-convert-3d-models-typescript/
weight: 13
---

## Problem

You will load a 3D model in `one` format (e.g., OBJ, GLTF, STL, or 3MF) and save it to another using Aspose.3D’s `Scene`, `IOService`, and format-specific exporter/importer classes. The canonical import path is `@aspose/3d-foss`, and only the listed classes in the API surface are available for this operation.

- Node.js runtime with TypeScript support
- Aspose.3D installed via `npm install @aspose/3d-foss`

## Prerequisites

You will convert 3D models between supported `formats` using Aspose.3D in a TypeScript environment. Ensure you have `Node`.js 16+ installed and the Aspose.3D package configured.

- Node.js version 16 or higher
- TypeScript compiler configured in your project
- Install @aspose/3d-foss via npm: `npm install @aspose/3d-foss`

```typescript
import { Scene, IOService, ColladaFormat } from "@aspose/3d-foss";

const scene = new Scene();
const io = IOService.instance();
io.registerImporter(new ColladaFormat().getInstance());
```

## Conversion Steps

You will load a 3D model file, configure conversion options, and save it to a different format using Aspose.3D. The process uses the `Scene`, `IOService`, and format-specific exporter classes from the Aspose.3D package.

- Install @aspose/3d-foss via npm: `npm install @aspose/3d-foss`
- Ensure your source file is accessible (local path or readable stream)

### Step 1: Load the source 3D model

Create a `Scene` `instance` and use `IOService.instance().importScene()` to load your source file. This populates the scene with geometry, `nodes`, and `entities` defined in the input format.

```typescript
import { Scene, IOService } from "@aspose/3d-foss";

const scene = new Scene();
const ioService = IOService.instance();
ioService.importScene(scene, "input.fbx");
```

### Step 2: Configure `export` options

Select the target format using the appropriate format class, such as `ColladaFormat`, and prepare save options. Aspose.3D uses format-specific exporters like `ColladaExporter` to handle output generation.

```typescript
const colladaFormat = ColladaFormat.getInstance();
const exporter = new ColladaExporter();
exporter.export(scene, "output.dae", {});
```

### Step 3: Save to target format

Call the exporter’s `export()` method with the loaded `Scene`, output file path, and empty options object. This writes the converted model to disk in the target format.

```typescript
exporter.export(scene, "output.dae", {});
```

### Code Breakdown

The `Scene` class holds the entire 3D scene graph, including `nodes` and `entities`. `IOService.instance()` provides access to registered importers and exporters. The `ColladaFormat.getInstance()` call retrieves the singleton `instance` for COLLADA format handling, and `ColladaExporter` performs the actual conversion.

### Error Handling

Wrap conversion logic in try/catch blocks to handle Error exceptions thrown during file I/O or format detection. Check `ColladaFormat.canImport()` and `ColladaFormat.canExport()` before conversion to validate format support.

### Next Steps

Explore format-specific options for GLTF, STL, or 3MF conversions. Review the `Scene.rootNode()`, `Node.entities()`, and `Entity.getBoundingBox()` methods for post-conversion inspection.

## Code Example

You will load a 3D model file and convert it to another supported format using Aspose.3D. The example demonstrates converting an STL file to GLTF using the `Scene`, `ColladaExporter`, and `ColladaFormat` classes from the Aspose.3D package.

- Node.js runtime with TypeScript support
- Aspose.3D installed via `npm install @aspose/3d-foss`

### Step 1: Load the source 3D model

```typescript
import { Scene, ColladaFormat } from "@aspose/3d-foss";

const scene = new Scene();
const format = ColladaFormat.getInstance();
// Load the source file (e.g., 'input.stl')
// Note: Actual import logic requires IOService registration per API surface
```

The `Scene` class initializes an empty 3D scene. The `ColladaFormat.getInstance()` method retrieves the singleton `instance` for COLLADA format handling. Loading a file requires registering an appropriate importer via `IOService.instance().registerImporter(...)`, as the API surface does not expose direct load methods on `Scene`.

### Step 2: Export to target format

```typescript
import { ColladaExporter } from "@aspose/3d-foss";

const exporter = new ColladaExporter();
// exporter.export(scene, outputStream, options);
```

The `ColladaExporter` class provides the `export()` method to write scene `data` to a stream. Exporting requires a valid `Scene` object and a writable stream. The API surface confirms `ColladaExporter` supports format detection via supportsFormat() and exports using `export(scene, stream, options)`, though concrete format-specific options are not listed.

### Error Handling

Handle errors using standard TypeScript try/catch blocks. Expected exceptions include Error for file I/O failures and format-specific exceptions thrown by `ColladaImporter` or `ColladaExporter` during parsing or serialization. Always validate file existence and stream readiness before calling import/`export` methods.

### Next Steps

Explore additional format conversions using `ColladaFormatDetector` for automatic format detection and `Scene.rootNode()` to inspect loaded geometry. For advanced workflows, use `AnimationClip` and `AnimationNode` to manage 3D `animations` in TypeScript 3D engine projects.

## Supported Formats

Aspose.3D supports conversion between major 3D file `formats`. You can load and save models using the `Scene` class and registered importers/exporters.

| Format | Extension | Notes |
|--------|-----------|-------|
| COLLADA | .dae | Supported via `ColladaImporter` and `ColladaExporter` |
| STL | .stl | Supported for 3D printing workflows |
| 3MF | .3mf | Supported for modern 3D printing |
| OBJ | .obj | Supported with `materials`, textures, and grouping |
| GLTF | .gltf | Supported with full PBR `material` handling |

## See Also

Aspose.3D -- Related conversion guides and format documentation.

For details on see also, see the Aspose.3D documentation.

- [Frequently asked questions](/kb.aspose.org/3d/typescript/faq/)
- [Key capabilities overview](/blog.aspose.org/3d/typescript/3d-key-features/)
- [New TypeScript support](/blog.aspose.org/3d/typescript/introducing-3d-foss-typescript/)
- [How to load files](/docs.aspose.org/3d/typescript/developer-guide/model-loading/)
- [How to render models](/docs.aspose.org/3d/typescript/developer-guide/rendering/)
