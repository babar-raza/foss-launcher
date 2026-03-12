---
page_role: howto_article
title: "How to Load 3D Models in TypeScript"
description: "Step-by-step guide to loading OBJ, glTF, FBX, and other 3D formats in Node.js using the @aspose/3d FOSS package for TypeScript."
date: 2026-01-20
weight: 10
draft: false
type: "topic"
keywords: ["load 3d model typescript", "aspose 3d open obj", "scene open nodejs", "obj load options", "aspose 3d foss typescript"]
step1: "Install @aspose/3d via npm"
step2: "Import Scene and format-specific loader options"
step3: "Open a 3D file using scene.open()"
step4: "Iterate over scene nodes"
step5: "Access mesh vertex data via controlPoints"
step6: "Configure ObjLoadOptions for material loading"
---

The `@aspose/3d` package gives TypeScript and Node.js applications a straightforward API for opening 3D scene files. `Scene` is the root object: call `scene.open()` with a file path and optional format-specific load options, then traverse `scene.rootNode` to access geometry, materials, and transforms.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install @aspose/3d via npm

Add the package to your project. No native binaries or platform-specific build tools are required — only Node.js 16 or later.

```bash
npm install @aspose/3d
```

For TypeScript projects, type definitions are bundled with the package:

```bash
##tsconfig.json — minimum required settings
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true
  }
}
```

### Step 2: Import Scene and format-specific options

Each format exposes its own loader class and options object under a sub-path. Import only what you need:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
```

For other formats the pattern is identical:

```typescript
import { GltfLoadOptions } from '@aspose/3d/formats/gltf';
import { FbxLoadOptions } from '@aspose/3d/formats/fbx';
import { StlLoadOptions } from '@aspose/3d/formats/stl';
```

### Step 3: Open a 3D file using scene.open()

Create a `Scene` instance, then call `scene.open()` with the file path and an optional load-options object. The call is synchronous.

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
const options = new ObjLoadOptions();
options.enableMaterials = true;

scene.open('model.obj', options);
console.log('Scene loaded successfully');
```

To load from a `Buffer` already in memory (useful in serverless or streaming contexts):

```typescript
import * as fs from 'fs';
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const buffer = fs.readFileSync('model.obj');
const scene = new Scene();
scene.openFromBuffer(buffer, new ObjLoadOptions());
```

### Step 4: Iterate over scene nodes

The scene graph is a tree rooted at `scene.rootNode`. Each `Node` can contain child nodes and an optional `entity` (mesh, camera, light, etc.).

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

function visitNode(node: any, depth: number = 0): void {
    const indent = '  '.repeat(depth);
    console.log(`${indent}Node: ${node.name}`);
    if (node.entity) {
        console.log(`${indent}  Entity type: ${node.entity.constructor.name}`);
    }
    for (const child of node.childNodes) {
        visitNode(child, depth + 1);
    }
}

visitNode(scene.rootNode);
```

### Step 5: Access mesh vertex data via controlPoints

When a node's entity is a `Mesh`, you can read the raw control points (vertices) from the `controlPoints` array. Each entry is a `Vector4` with `x`, `y`, `z`, and `w` components.

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

for (const node of scene.rootNode.childNodes) {
    if (!node.entity) continue;
    const entity = node.entity;
    // Check if the entity is a Mesh by duck-typing controlPoints
    if ('controlPoints' in entity) {
        const mesh = entity as any;
        console.log(`Mesh "${node.name}": ${mesh.controlPoints.length} vertices`);
        // Print first three vertices
        for (let i = 0; i < Math.min(3, mesh.controlPoints.length); i++) {
            const v = mesh.controlPoints[i];
            console.log(`  v[${i}]: x=${v.x.toFixed(4)}, y=${v.y.toFixed(4)}, z=${v.z.toFixed(4)}`);
        }
    }
}
```

### Step 6: Configure ObjLoadOptions for material loading

`ObjLoadOptions` exposes properties to control how accompanying `.mtl` material files and textures are resolved.

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const options = new ObjLoadOptions();
options.enableMaterials = true;   // parse .mtl file if present

const scene = new Scene();
scene.open('model.obj', options);

// Inspect materials attached to nodes
for (const node of scene.rootNode.childNodes) {
    if (node.entity && node.entity.material) {
        console.log(`Material on "${node.name}": ${node.entity.material.constructor.name}`);
    }
}
```

{{% /steps %}}

## Common Issues and Fixes

**Error: Cannot find module '@aspose/3d/formats/obj'**
The format sub-paths require Node.js 12.7+ package exports. Make sure you are on Node.js 16 or later. If using TypeScript, set `"moduleResolution": "node16"` or `"bundler"` in `tsconfig.json`.

**scene.rootNode.childNodes is empty after open()**
Some OBJ files use non-standard line endings or lack a trailing newline. Verify the file is a valid OBJ by opening it in a text editor. Also confirm you passed `ObjLoadOptions` and not a generic `LoadOptions` — the format-specific options are required for correct dispatch.

**controlPoints array has zero length**
The mesh may have been loaded but contains no geometry (e.g., an empty group in the OBJ). Use `mesh.polygonCount` to check before iterating vertices.

**Memory usage is high for large files**
Load-from-buffer with `scene.openFromBuffer()` does not reduce peak memory — the entire file must be parsed. For large files (> 100 MB), ensure your Node.js process has sufficient heap: `node --max-old-space-size=4096 yourScript.js`.

**Type errors: 'entity' is of type 'unknown'**
The `entity` property is typed broadly. Cast to `any` or to a specific class (`Mesh`, `Camera`, etc.) depending on what you expect in your scene.

## Frequently Asked Questions (FAQ)

**Which formats can be loaded with scene.open()?**
OBJ, glTF 2.0 (.gltf + .bin), GLB, STL, 3MF, FBX, and COLLADA (.dae) are all supported for import. Pass the corresponding `*LoadOptions` class for each format.

**Can I load a file without specifying options?**
Yes. `scene.open('model.glb')` works without options for formats that do not require special configuration. Passing options is recommended for OBJ because material resolution depends on `enableMaterials`.

**Does loading run asynchronously?**
No. `scene.open()` and `scene.openFromBuffer()` are synchronous. Wrap them in a worker thread or `setImmediate` if you need to keep an event loop responsive.

**Is OBJ export supported?**
No. OBJ format is import-only in `@aspose/3d`. To export, save to glTF/GLB, STL, 3MF, FBX, or COLLADA using `scene.save()`.

**Where is the .mtl file expected when loading OBJ?**
By default, the parser looks for the `.mtl` file referenced inside the OBJ (`mtllib` directive) relative to the OBJ file's directory. Make sure both files are in the same folder.

## See Also

- [How to Export 3D Scenes to glTF/GLB in TypeScript](/kb.aspose.org/3d/typescript/how-to-export-gltf-in-typescript/)
- [API Reference: Scene](/3d/typescript/scene/)
- [API Reference: ObjLoadOptions](/3d/typescript/objloadoptions/)
- [npm: @aspose/3d](https://www.npmjs.com/package/@aspose/3d)
