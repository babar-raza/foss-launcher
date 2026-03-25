---
canonical: https://kb.aspose.org/3d/typescript/faq/
canonical_import: '@aspose/3d-foss'
code_import: '@aspose/3d-foss'
date: '2026-03-24T16:58:44Z'
dateModified: '2026-03-24T16:58:44Z'
datePublished: '2026-03-24T16:58:44Z'
description: It supports import/`export` of `formats` like GLTF, OBJ, STL, and 3MF,
  and provides a structured API surface for scene graph manipulation, animation...
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
page_role: faq
platform: typescript
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D FAQ | Guide
slug: faq
title: Aspose.3D FAQ
type: faq
url: /kb.aspose.org/3d/typescript/faq/
weight: 8
---

## Frequently Asked Questions

Aspose.3D is a TypeScript 3D `library` for working with 3D scenes, `nodes`, `entities`, and `animations`. It supports import/`export` of `formats` like GLTF, OBJ, STL, and 3MF, and provides a structured API surface for scene graph manipulation, animation authoring, and format handling.

### What is the correct import path for Aspose.3D in TypeScript?

Use `import { ... } from "Aspose.3D"` as the only valid import path for Aspose.3D in TypeScript. Any other import path, including aliases or alternative package names, is invalid and will not resolve correctly. This ensures compatibility with the published npm package and aligns with the canonical module structure.

### How do I create a basic 3D scene with a node and `entity`?

Construct a `Scene`, then create a `Node` with an `Entity` (e.g., `Mesh`) and attach it to the scene's root node. Use `scene.rootNode().childNodes().push(node)` to `add` the node to the scene hierarchy. The `Entity` subclass determines the geometric or visual `content`, while `Node` provides the scene graph transform and ownership context.

```typescript
import { Scene, Node, Mesh } from "@aspose/3d-foss";

const scene = new Scene();
const mesh = new Mesh("MyMesh", null, null, null);
const node = new Node("MyNode", mesh);
scene.rootNode().childNodes().push(node);
```

### Can I `export` a scene to GLTF format using Aspose.3D?

Yes, Aspose.3D supports exporting scenes to GLTF via the `ColladaExporter` and `ColladaFormat` classes, which also handle GLTF as a target format. Use `IOService.instance().registerExporter(new ColladaExporter())` to register the exporter, then call `exporter.export(scene, stream, options)` with a writable stream and appropriate save options.

### How do I access animation clips and keyframe sequences?

Create an `AnimationClip`, then use `createAnimationNode()` to generate an `AnimationNode`. From there, call `getKeyframeSequence()` or `createKeyframeSequence()` on the `AnimationNode` to manage keyframe `data`. Each `KeyframeSequence` holds time-value pairs for animating properties like transforms or `materials`.

### What classes handle file system abstraction in Aspose.3D?

The `FileSystem` class provides static factory methods like `createLocalFileSystem()`, `createZipFileSystem()`, and `createDummyFileSystem()` to abstract file I/O. Use readFile() and writeFile() on a `FileSystem` `instance` to perform I/O operations with `IOConfig` options, enabling custom storage backends.

## See Also

Aspose.3D provides core 3D scene manipulation capabilities in TypeScript, with support for `formats` like GLTF, STL, and 3MF. The `library` exposes foundational classes such as `Scene`, `Node`, `Entity`, and `AnimationClip` for building 3D applications, including 3D typescript game engines and 3D visualization tools.

- [Convert file formats step-by-step](/kb.aspose.org/3d/typescript/how-to-convert-3d-models-typescript/)
- [Fix common errors and resolve issues](/kb.aspose.org/3d/typescript/how-to-fix-3d-models-errors-typescript/)
- [Load 3D files efficiently and correctly](/kb.aspose.org/3d/typescript/how-to-load-3d-models-typescript/)
- [Optimize performance for large models](/kb.aspose.org/3d/typescript/how-to-optimize-3d-models-typescript/)
- [Save files in supported formats](/kb.aspose.org/3d/typescript/how-to-save-3d-models-typescript/)
