---
canonical: https://blog.aspose.org/3d/typescript/3d-key-features/
canonical_import: "@aspose/3d"
date: '2026-03-11T16:00:00Z'
dateModified: '2026-03-11T16:00:00Z'
datePublished: '2026-03-11T16:00:00Z'
description: Aspose.3D FOSS for TypeScript provides scene graph management, multi-format I/O, mesh operations, keyframe animation, and PBR material support for Node.js and browser environments.
display_name: Aspose.3D
family: 3d
keywords:
- typescript 3d library
- aspose 3d typescript features
- nodejs 3d scene
- typescript gltf fbx
- 3d model nodejs
- "@aspose/3d npm"
lastmod: '2026-03-11T16:00:00Z'
page_role: blog_announcement
platform: typescript
reading_time: 3
robots: index, follow
seoTitle: Aspose.3D FOSS for TypeScript — Key Features Overview
slug: 3d-key-features
title: Aspose.3D FOSS for TypeScript — Key Features
type: blog_announcement
url: /blog.aspose.org/3d/typescript/3d-key-features/
weight: 20
---

## Introduction

Aspose.3D FOSS for TypeScript (`@aspose/3d`) is an open-source, MIT-licensed 3D file format library for Node.js and modern browser environments. Developers building 3D model viewers, format converters, geometry processing tools, or server-side 3D pipelines can install it with a single `npm install @aspose/3d` command and immediately start loading, constructing, and exporting 3D content.

The library supports the major interchange formats — OBJ, glTF 2.0 / GLB, FBX, STL, 3MF, and COLLADA — all as both import and export targets. The scene graph API mirrors the model familiar from 3D authoring tools: a `Scene` holds a `rootNode`, each `Node` can carry child nodes and entity objects (`Mesh`, `Camera`, `Light`), and the transform hierarchy is fully accessible for reading and writing.

## Key Features

- **Multi-format I/O** — Import and export OBJ (with `.mtl` materials), glTF 2.0 / GLB, FBX, STL (binary and ASCII), 3MF, and COLLADA from both file paths and in-memory `Buffer` objects
- **Scene graph API** — `Scene`, `Node`, `Mesh`, `Camera`, `Light` hierarchy with full parent/child management; traverse nodes recursively via `node.childNodes`
- **PBR material system** — Lambert, Phong, and PBR (metallic/roughness) materials accessible via `node.entity.material`
- **Mesh operations** — Access raw vertex data via `mesh.controlPoints` (array of `Vector4`), polygon indices via `mesh.polygonCount`, and vertex element channels via `mesh.getElement()`
- **Math utilities** — `Vector2`, `Vector3`, `Vector4`, `Matrix4`, `Quaternion`, and bounding box types for spatial calculations
- **Animation system** — Keyframe animation with `AnimationClip`, `AnimationChannel`, and interpolation curves (linear, Bezier, TCB spline)
- **Format-specific options** — Per-format `LoadOptions` / `SaveOptions` classes control coordinate flipping, scale, material loading, and more

## Getting Started

Install from npm. Node.js 16 or later is required; TypeScript 5.0+ is recommended.

```bash
npm install @aspose/3d
```

Load an OBJ file and inspect the scene:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
const options = new ObjLoadOptions();
options.enableMaterials = true;
scene.open('model.obj', options);

for (const node of scene.rootNode.childNodes) {
    if (node.entity && 'controlPoints' in node.entity) {
        const mesh = node.entity as any;
        console.log(`Mesh "${node.name}": ${mesh.controlPoints.length} vertices`);
    }
}
```

## Export to glTF

Save any loaded or constructed scene to glTF 2.0 binary (GLB):

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('input.obj', new ObjLoadOptions());
scene.save('output.glb');
console.log('Exported to output.glb');
```

The library auto-detects the output format from the file extension. Pass a `GltfSaveOptions` instance for control over PBR material embedding, textures, and binary vs. JSON encoding.

## Scene Construction

Build a scene programmatically and export it:

```typescript
import { Scene, Node } from '@aspose/3d';
import { Mesh } from '@aspose/3d/entities';

const scene = new Scene();
const mesh = new Mesh();
// ... populate mesh.controlPoints and polygons ...
const node = new Node('myMesh');
node.entity = mesh;
scene.rootNode.addChildNode(node);
scene.save('programmatic.glb');
```

## See Also

- [How to Load 3D Models in TypeScript](/kb.aspose.org/3d/typescript/how-to-load-3d-models-in-typescript/)
- [How to Export glTF in TypeScript](/kb.aspose.org/3d/typescript/how-to-export-gltf-in-typescript/)
- [Format Support](/docs.aspose.org/3d/typescript/developer-guide/format-support/)
- [API Reference](/reference.aspose.org/3d/typescript/)
