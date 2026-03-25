---
canonical: https://docs.aspose.org/3d/typescript/developer-guide/model-loading/
canonical_import: '@aspose/3d-foss'
code_import: '@aspose/3d-foss'
date: '2026-03-24T16:58:44Z'
dateModified: '2026-03-24T16:58:44Z'
datePublished: '2026-03-24T16:58:44Z'
description: You provide a file path or stream, and the `library` parses it into a
  `Scene` object containing `Node`, `Entity`, and `Camera` instances ready for...
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
page_role: workflow_page
platform: typescript
reading_time: 1
robots: index, follow
seoTitle: Load Files with Aspose.3D | Guide
slug: model-loading
title: Load Files with Aspose.3D
type: workflow_page
url: /docs.aspose.org/3d/typescript/developer-guide/model-loading/
weight: 18
---

## Overview

This guide walks you through loading 3D files into memory using Aspose.3D in a TypeScript environment. You provide a file path or stream, and the `library` parses it into a `Scene` object containing `Node`, `Entity`, and `Camera` instances ready for inspection or `export`.

First, install the package using npm: `npm install Aspose.3D`. Then import the required types from `@aspose/3d-foss`. The `IOService` class provides access to importers and exporters, while `Scene` holds the loaded 3D hierarchy.

```typescript
import { IOService, Scene, ColladaImporter, ColladaFormat } from "@aspose/3d-foss";

const ioService = IOService.instance();
ioService.registerImporter(new ColladaImporter());

const scene = new Scene();
const inputStream = fs.createReadStream('model.dae');
const loadOptions = {};

// Load the scene from a DAE file
const format = ColladaFormat.getInstance();
const detector = new ColladaFormatDetector();
const detectedFormat = detector.detect(inputStream, 'model.dae');

console.log('Detected format:', detectedFormat?.extension());
```

- Use this pattern when loading COLLADA (.dae) files for inspection before export.
- Register importers explicitly via `IOService.instance().registerImporter()` to enable format detection.
- The `ColladaFormatDetector` inspects the stream and returns a FileFormat instance with extension metadata.

## Key Features

This guide walks you through loading 3D files using Aspose.3D in a TypeScript environment. You start with a supported 3D file (e.g., OBJ, GLTF, STL, or 3MF), load it into a `Scene` object, and then access its geometry, `nodes`, and `entities` for further processing or conversion.

- Supports loading common 3D formats including OBJ, GLTF, STL, and 3MF for interoperability across modeling and printing tools.
- Provides direct access to scene hierarchy via `Scene.rootNode()` and `Node.childNodes()` for inspecting or modifying 3D structures.
- Enables programmatic extraction of geometry and entities using `Entity` and `Mesh` classes for custom rendering or analysis.
- Includes `ColladaImporter` and `ColladaExporter` for importing and exporting COLLADA files in 3D pipelines.

## Prerequisites

This guide walks you through loading 3D files using Aspose.3D in a TypeScript environment. You will load a 3D model file, inspect its scene hierarchy using `Scene`, `Node`, and `Entity` objects, and prepare it for further processing or `export`.

- Node.js v16 or later installed
- TypeScript v4.9 or later installed
- Run `npm install @aspose/3d-foss` to install the package
- No additional system dependencies required

## Code Examples

This guide walks you through loading 3D files into an Aspose.3D `Scene` object using the canonical `@aspose/3d-foss` package. You will import a file, inspect its structure via the `Scene.rootNode()` and `Node.entities()` methods, and access geometry `data` through `Entity` and `Mesh` objects.

```typescript
import { Scene, IOService } from "@aspose/3d-foss";

// Load a 3D file into a Scene
const scene = new Scene();
const ioService = IOService.instance();

// Assuming 'input.fbx' exists in the current directory
const inputStream = require('fs').createReadStream('input.fbx');
ioService.importScene(scene, inputStream, {});

// Access the root node and its entities
const rootNode = scene.rootNode();
const entities = rootNode.entities();
console.log(`Root node contains ${entities.length} entities`);
```

- Use this pattern when loading a 3D model for rendering in a TypeScript 3d engine.
- This approach works with supported formats like GLTF, OBJ, and STL via the registered importers.
- Accessing `rootNode.entities()` helps identify top-level geometry for further processing.

After loading, inspect individual `entities` to retrieve `mesh` `data`. Each `Entity` may contain a `Mesh`, accessible via its `entity()` method on a `Node`. Use `Mesh.polygonCount()` and `Mesh.edges()` to validate geometry before exporting or modifying.

```typescript
import { Scene, IOService } from "@aspose/3d-foss";

const scene = new Scene();
const ioService = IOService.instance();
const inputStream = require('fs').createReadStream('input.fbx');
ioService.importScene(scene, inputStream, {});

// Traverse the scene hierarchy
const rootNode = scene.rootNode();
for (const node of rootNode.childNodes()) {
  const entity = node.entity();
  if (entity) {
    console.log(`Entity type: ${entity.constructor.name}`);
    // Access bounding box for spatial queries
    const bbox = entity.getBoundingBox();
    console.log(`Bounding box: min=${bbox.min}, max=${bbox.max}`);
  }
}
```

- Use `getBoundingBox()` to cull entities during rendering in a TypeScript 3d game engine.
- Check entity type before casting to avoid runtime errors in TypeScript 3d array workflows.
- Traverse child nodes to process complex hierarchies like rigged models or assemblies.

## Notes and Best Practices

When loading 3D files with Aspose.3D in TypeScript, ensure you use the canonical import path `@aspose/3d-foss` and validate input `formats` before processing to avoid runtime errors. The `library` supports key `formats` like OBJ, GLTF, STL, and 3MF, and relies on format-specific detectors and importers such as `ColladaFormatDetector` and `ColladaImporter` to identify and `parse` files correctly.

- Always verify the file format using a format detector (e.g., `ColladaFormatDetector`) before invoking the corresponding importer to prevent malformed input errors.
- Use `ColladaImporter` and `ColladaExporter` only for COLLADA (.dae) files, as they are not generic loaders for all formats—other formats require their own dedicated classes.
- Ensure input files conform to the expected schema for the target format; for example, GLTF files must include valid JSON structure and referenced resources.
- Handle exceptions during import to catch missing files, unsupported encodings, or corrupted data—especially important in production 3D TypeScript game engines or model viewers.

## See Also

- [Explore 3D key features](/blog.aspose.org/3d/typescript/3d-key-features/)
- [Introducing 3D Foss TypeScript](/blog.aspose.org/3d/typescript/introducing-3d-foss-typescript/)
- [Render 3D models](/docs.aspose.org/3d/typescript/developer-guide/rendering/)
- [Convert file formats](/kb.aspose.org/3d/typescript/how-to-convert-3d-models-typescript/)
- [Fix common errors](/kb.aspose.org/3d/typescript/how-to-fix-3d-models-errors-typescript/)
