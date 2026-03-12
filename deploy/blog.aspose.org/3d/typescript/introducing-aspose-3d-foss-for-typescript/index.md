---
page_role: howto_article
title: "Introducing Aspose.3D FOSS for TypeScript"
seoTitle: "Aspose.3D FOSS for TypeScript — Open-Source 3D File Processing in Node.js"
description: "Aspose.3D FOSS for TypeScript is now available on npm. Load, convert, and export OBJ, glTF, GLB, STL, 3MF, FBX, and COLLADA files in Node.js with full TypeScript type definitions."
date: "2026-01-20"
draft: false
author: "Aspose Team"
summary: "The @aspose/3d npm package brings MIT-licensed 3D scene processing to TypeScript and Node.js — with support for six major formats, full type definitions, and a single dependency."
tags: ["aspose 3d", "typescript", "nodejs", "gltf", "3d formats", "open source", "foss"]
categories: ["Product Announcements", "3D"]
---

## Introduction

We are pleased to announce the availability of **Aspose.3D FOSS for TypeScript** as the `@aspose/3d` npm package. This MIT-licensed library brings production-quality 3D scene processing to TypeScript and Node.js applications without requiring native binaries, platform-specific toolchains, or commercial licenses.

The library is designed around a straightforward `Scene` API: load a 3D file with `scene.open()`, inspect or transform the scene graph, and write the result with `scene.save()`. Full TypeScript type definitions are bundled — no separate `@types/` package is required.

## Key Features

**Multi-format I/O.** The package reads and writes six major 3D formats in a single install. OBJ is supported for import; glTF 2.0, GLB, STL, 3MF, FBX, and COLLADA support both import and export.

**First-class TypeScript support.** All public classes, enumerations, and option types are fully typed. IDEs with TypeScript language service support (VS Code, WebStorm, etc.) provide accurate autocompletion and inline documentation for every API call.

**Node.js 16–22+ compatibility.** The package is tested against Node.js 16, 18, 20, and 22 LTS releases. No native addons are compiled during install, so it works on all platforms Node.js supports.

**One runtime dependency.** The only dependency is `xmldom`, used exclusively for COLLADA XML parsing. All other format parsers are pure JavaScript implementations.

**MIT license.** Use `@aspose/3d` in commercial, open-source, or internal projects without restriction.

## Quick Start

Install the package:

```bash
npm install @aspose/3d
```

Load an OBJ file and convert it to a binary GLB:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

const saveOpts = new GltfSaveOptions();
saveOpts.binaryMode = true;   // produce a single .glb file
scene.save('output.glb', GltfFormat.getInstance(), saveOpts);

console.log('Converted to GLB successfully');
```

Iterate over scene nodes to inspect geometry:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

for (const node of scene.rootNode.childNodes) {
    console.log(`Node: ${node.name}`);
    if (node.entity) {
        console.log(`  Entity type: ${node.entity.constructor.name}`);
    }
}
```

## Supported Formats

| Format | Extension | Import | Export | Notes |
|---|---|:---:|:---:|---|
| Wavefront OBJ | `.obj` | Yes | No | Reads `.mtl` materials when `enableMaterials: true` |
| glTF 2.0 | `.gltf` | Yes | Yes | JSON with external `.bin` buffer |
| Binary GLB | `.glb` | Yes | Yes | Set `binaryMode: true` in `GltfSaveOptions` |
| STL | `.stl` | Yes | Yes | ASCII and binary STL |
| 3MF | `.3mf` | Yes | Yes | Open Packaging Convention archive |
| FBX | `.fbx` | Yes | Yes | Binary and ASCII FBX |
| COLLADA | `.dae` | Yes | Yes | Requires bundled `xmldom` dependency |

## TypeScript Advantages

Working with `@aspose/3d` in TypeScript catches category errors at compile time rather than at runtime. When you call `scene.save()`, the compiler verifies that the options object matches the expected `SaveOptions` subtype for the chosen format. Format-specific load and save options expose only the properties relevant to that format — there is no untyped options bag to guess at.

For example, `GltfSaveOptions.binaryMode` is a typed `boolean`, so the compiler rejects `saveOpts.binaryMode = 'yes'` before any code runs. Animation properties on `AnimationClip`, material channels on `PbrMaterial`, and vertex element types on `VertexElement` are all similarly typed and discoverable through IntelliSense without consulting external documentation.

## Open Source

The package is published under the **MIT License**. Source code is available on GitHub. Contributions, bug reports, and format support requests are welcome through the repository's issue tracker.

The library has one runtime dependency: `xmldom` version 0.9+, used only when reading or writing COLLADA files. All other parsers and writers are self-contained pure-JavaScript implementations with no binary components.

## Getting Started

- **npm**: `npm install @aspose/3d`
- **Knowledge Base**: [How to Load 3D Models in TypeScript](/kb/3d/typescript/how-to-load-3d-models-in-typescript/)
- **Knowledge Base**: [How to Export 3D Scenes to glTF/GLB in TypeScript](/kb/3d/typescript/how-to-export-gltf-in-typescript/)
- **API Reference**: [Aspose.3D FOSS for TypeScript — Full Class Reference](/3d/typescript/)
- **GitHub**: [aspose-3d/aspose-3d-node](https://github.com/aspose-3d/aspose-3d-node)

## Conclusion

`@aspose/3d` version 24.12.0 provides a stable, typed, dependency-light foundation for 3D file processing in TypeScript and Node.js. Whether the use case is format conversion, scene inspection, geometry extraction, or pipeline integration, the library covers the most common 3D interchange formats under a permissive open-source license.

Install it today and let us know what you build.
