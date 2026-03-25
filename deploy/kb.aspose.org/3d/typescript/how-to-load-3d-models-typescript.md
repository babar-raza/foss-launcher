---
canonical: https://kb.aspose.org/3d/typescript/how-to-load-3d-models-typescript/
canonical_import: '@aspose/3d-foss'
code_import: '@aspose/3d-foss'
date: '2026-03-24T16:58:44Z'
dateModified: '2026-03-24T16:58:44Z'
datePublished: '2026-03-24T16:58:44Z'
description: The `Scene` object provides access to the scene graph via rootNode(),
  subScenes(), and `library()` methods.
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
seoTitle: How to Load Files with Aspose.3D | Guide
slug: how-to-load-3d-models-typescript
title: How to Load Files with Aspose.3D
type: howto_article
url: /kb.aspose.org/3d/typescript/how-to-load-3d-models-typescript/
weight: 11
---

## Problem

You will load a 3D model file (e.g., OBJ, GLTF, STL, or 3MF) into an `Scene` object using Aspose.3D’s `IOService` and format-specific importers. The `Scene` object provides access to the scene graph via rootNode(), subScenes(), and `library()` methods.

- Node.js runtime with TypeScript support
- @aspose/3d-foss package installed via npm

## Prerequisites

You will load 3D files using Aspose.3D in a TypeScript environment. Ensure you have `Node`.js 16+ installed and the Aspose.3D package configured.

- Node.js version 16 or later
- TypeScript 5.0 or later
- @aspose/3d-foss package installed via npm

```typescript
import { Scene, IOService } from "@aspose/3d-foss";

const scene = new Scene();
const io = IOService.instance();
```

## Loading the File

You will load 3D models into an Aspose.3D `Scene` using file paths or streams, with support for OBJ, GLTF, STL, and 3MF `formats` via the `IOService` class.

- Node.js runtime with TypeScript support
- @aspose/3d-foss package installed via npm

### Load a 3D model from a file path

Use `IOService.instance().importScene()` with a file path to load a model. The method detects the format automatically using registered detectors.

```typescript
import { IOService } from "@aspose/3d-foss";

const scene = IOService.instance().importScene("model.fbx");
```

This returns a `Scene` object containing the loaded 3D hierarchy.

### Load a 3D model from a stream

Pass a readable stream to `importScene()` when loading from memory or network sources.

```typescript
import { IOService } from "@aspose/3d-foss";
import * as fs from "fs";

const stream = fs.createReadStream("model.gltf");
const scene = IOService.instance().importScene(stream);
```

The `Scene` object now `contains` the parsed model `data` ready for inspection or `export`.

### Specify load options for format-specific behavior

Use `ColladaLoadOptions` when importing COLLADA files to control parsing behavior.

```typescript
import { IOService, ColladaLoadOptions } from "@aspose/3d-foss";

const options = new ColladaLoadOptions();
const scene = IOService.instance().importScene("model.dae", options);
```

This ensures correct interpretation of COLLADA-specific constructs like `animations` and bind points.

### Error handling for file loading

Catch Error exceptions when loading fails due to missing files, unsupported `formats`, or corrupted `data`.

```typescript
try {
  const scene = IOService.instance().importScene("model.stl");
} catch (error) {
  console.error("Failed to load file:", error.message);
}
```

This pattern ensures robust handling of I/O issues in production 3D TypeScript applications.

### Next steps

After loading, inspect the scene hierarchy using `Scene.rootNode()`, `Node.entities()`, and `Entity.getBoundingBox()`. Export the scene to other `formats` using registered exporters like `ColladaExporter`.

## Code Example

You will load a 3D model file using Aspose.3D, inspect its scene hierarchy, and print a summary of its root node and `entities`. This example uses the canonical import path and demonstrates core classes from the API surface.

- Node.js runtime with TypeScript support
- Aspose.3D package installed via `npm install @aspose/3d-foss`

### Load and inspect a 3D scene

Step 1: Import the `library` and create a new `Scene` `instance`. The `Scene` class provides access to the root node and subscenes.

```typescript
import { Scene } from "@aspose/3d-foss";

const scene = new Scene();
```

Step 2: Access the root node using rootNode(). The root node `contains` the top-level `entities` and child `nodes` of the scene.

```typescript
const rootNode = scene.rootNode();
```

Step 3: Print the root node `name` and list its `entities`. Use `entities()` to retrieve the array of `Entity` instances attached to the node.

```typescript
console.log(`Root node: ${rootNode.name()}`);
console.log(`Entities count: ${rootNode.entities().length}`);
rootNode.entities().forEach((entity, i) => {
  console.log(`  Entity ${i}: ${entity.constructor.name}`);
});
```

This outputs the root node `name` and the `count` and type of each `entity` in the scene. For a loaded file, the `entities` would reflect the model’s geometry or objects.

### Error Handling

When loading external files, wrap operations in a try-catch block. Aspose.3D throws standard JavaScript errors for I/O failures or invalid file `formats`. Check for IOError or Error types when handling exceptions.

```typescript
try {
  // Load or process scene here
} catch (error) {
  if (error instanceof Error) {
    console.error(`Failed to load scene: ${error.message}`);
  }
}
```

Next, explore how to load specific `formats` like GLTF or STL using the `IOService` and registered importers.

## Supported Formats

Aspose.3D supports loading and saving common 3D file `formats`. You can load files using the `Scene` class and the `IOService` class to register importers and detectors. The following table lists the supported input `formats`.

| Format | Extension | Notes |
|--------|-----------|-------|
| Collada | .dae | Full import support via `ColladaImporter` and `ColladaFormatDetector` |
| STL | .stl | Import support for 3D printing workflows |
| 3MF | .3mf | Import support for modern 3D manufacturing |
| OBJ | .obj | Import support with `materials` and texture references

To load a Collada (.dae) file, instantiate `Scene`, then use `IOService.instance().registerImporter(new ColladaImporter())` before calling `Scene.open()` with the file stream.

```typescript
import { Scene, IOService, ColladaImporter } from "@aspose/3d-foss";

const scene = new Scene();
const ioService = IOService.instance();
ioService.registerImporter(new ColladaImporter());
// scene.open(stream) would follow in a real implementation
```

## See Also

You will load 3D files using Aspose.3D with TypeScript, supporting `formats` like OBJ, GLTF, STL, and 3MF. The `library` provides dedicated importers and exporters for each format via the `ColladaImporter`, `ColladaExporter`, and `ColladaFormat` classes.

- [Frequently asked questions](/kb.aspose.org/3d/typescript/faq/)
- [Key features overview](/blog.aspose.org/3d/typescript/3d-key-features/)
- [Introducing TypeScript support](/blog.aspose.org/3d/typescript/introducing-3d-foss-typescript/)
- [How to load files](/docs.aspose.org/3d/typescript/developer-guide/model-loading/)
- [How to render 3D models](/docs.aspose.org/3d/typescript/developer-guide/rendering/)
