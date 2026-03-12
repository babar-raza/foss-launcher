---
page_role: howto_article
title: "How to Export 3D Scenes to glTF/GLB in TypeScript"
description: "Step-by-step guide to exporting 3D scenes to glTF 2.0 JSON or binary GLB format using @aspose/3d FOSS in TypeScript and Node.js."
date: 2026-01-20
weight: 20
draft: false
type: "topic"
keywords: ["export gltf typescript", "obj to glb nodejs", "aspose 3d save gltf", "gltf save options", "binary glb typescript"]
step1: "Install @aspose/3d"
step2: "Import Scene, GltfSaveOptions, and GltfFormat"
step3: "Build or load a scene"
step4: "Configure GltfSaveOptions"
step5: "Save using scene.save()"
step6: "Verify the output file"
---

Aspose.3D FOSS supports glTF 2.0 as both an import and export format. The same `Scene` object can be populated from an OBJ, FBX, STL, or other source file and then written to `.gltf` (JSON + external binary) or `.glb` (single binary container) by setting one flag on `GltfSaveOptions`.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install @aspose/3d

```bash
npm install @aspose/3d
```

Confirm Node.js 16 or later is active:

```bash
node --version   # must be >= 16.0.0
```

### Step 2: Import Scene, GltfSaveOptions, and GltfFormat

```typescript
import { Scene } from '@aspose/3d';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';
```

`GltfFormat` is the format descriptor passed to `scene.save()`. `GltfSaveOptions` carries all export configuration.

If you are also loading a source file (e.g., OBJ), import the matching load options:

```typescript
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
```

### Step 3: Build or load a scene

**Option A — Load from an existing file (OBJ → GLB conversion):**

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());
```

**Option B — Build a minimal scene programmatically:**

```typescript
import { Scene, Node, Mesh } from '@aspose/3d';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
const childNode = new Node('cube');
scene.rootNode.addChildNode(childNode);
// Attach geometry to childNode as needed
```

### Step 4: Configure GltfSaveOptions

`GltfSaveOptions` controls the output format and encoding details.

```typescript
const saveOpts = new GltfSaveOptions();

// Set to true for a single binary .glb file
// Set to false (default) for JSON .gltf + separate .bin
saveOpts.binaryMode = true;
```

Additional options you may set:

| Property | Type | Default | Effect |
|---|---|---|---|
| `binaryMode` | `boolean` | `false` | `true` → GLB, `false` → glTF JSON |
| `embedImages` | `boolean` | `false` | Embed textures inside the GLB/glTF |
| `flipTexCoordV` | `boolean` | `false` | Flip UV vertical axis for engine compatibility |

### Step 5: Save using scene.save()

Pass the output path, the `GltfFormat` descriptor, and the configured options:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

const saveOpts = new GltfSaveOptions();
saveOpts.binaryMode = true;   // produce .glb

scene.save('output.glb', GltfFormat.getInstance(), saveOpts);
console.log('Converted to GLB successfully');
```

To produce a JSON `.gltf` file instead:

```typescript
saveOpts.binaryMode = false;
scene.save('output.gltf', GltfFormat.getInstance(), saveOpts);
console.log('Exported to glTF JSON successfully');
```

### Step 6: Verify the output file

Check that the output file exists and has a non-zero size:

```typescript
import * as fs from 'fs';

const outputPath = 'output.glb';
const stats = fs.statSync(outputPath);
console.log(`Output file size: ${stats.size} bytes`);

if (stats.size === 0) {
    throw new Error('Export produced an empty file — check scene content');
}
```

For a round-trip verification, reload the GLB and inspect the node count:

```typescript
import { Scene } from '@aspose/3d';
import { GltfLoadOptions } from '@aspose/3d/formats/gltf';

const verify = new Scene();
verify.open('output.glb', new GltfLoadOptions());

let nodeCount = 0;
function countNodes(node: any): void {
    nodeCount++;
    for (const child of node.childNodes) countNodes(child);
}
countNodes(verify.rootNode);

console.log(`Round-trip verification: ${nodeCount} node(s) in output`);
```

{{% /steps %}}

## Common Issues and Fixes

**OBJ cannot be exported directly — must load first**
OBJ is an import-only format in `@aspose/3d`. You cannot call `scene.save('output.obj', ...)`. Load the OBJ with `scene.open()`, then export to glTF, GLB, STL, 3MF, FBX, or COLLADA.

**Output .glb is smaller than expected / meshes are missing**
If the loaded scene has nodes without entities (e.g., empty groups from an OBJ), the GLB will not contain those nodes' geometry. Confirm your input file has actual polygon data using `mesh.controlPoints.length > 0` before saving.

**Cannot find module '@aspose/3d/formats/gltf'**
Ensure you are on Node.js 16+ and that `@aspose/3d` is installed in the same `node_modules` as your entry point. Run `npm ls @aspose/3d` to confirm the version is 24.12.0 or later.

**GltfFormat.getInstance() returns undefined**
This indicates a version mismatch between the main `@aspose/3d` package and a cached older version. Delete `node_modules` and `package-lock.json`, then run `npm install` again.

**Textures are missing in the output GLB**
Set `saveOpts.embedImages = true` to inline textures. Without this, texture paths in the output glTF/GLB point to files relative to the output directory — make sure those image files are present alongside the output.

**Type error: Argument of type 'GltfSaveOptions' is not assignable**
Ensure both `Scene` and `GltfSaveOptions` are imported from the same installed package instance. Mixed installs (global + local) can cause interface mismatches.

## Frequently Asked Questions (FAQ)

**What is the difference between glTF and GLB?**
glTF 2.0 JSON (`.gltf`) stores the scene graph as a human-readable JSON file with separate `.bin` buffers and image files. GLB (`.glb`) packages everything into a single binary container. Set `binaryMode = true` for GLB, `false` for JSON glTF.

**Can I export a scene that was built entirely in code (no source file)?**
Yes. Create a `Scene`, add `Node` objects, attach `Mesh` or other entities, then call `scene.save()`. The scene does not need to originate from a loaded file.

**Is glTF export lossless?**
For geometry and transforms, yes. Materials are mapped to glTF PBR material properties where possible. Proprietary FBX material extensions may not round-trip perfectly.

**Can I export to STL or 3MF instead?**
Yes. The pattern is identical — import the corresponding format's `*SaveOptions` and `*Format.getInstance()`:

```typescript
import { StlSaveOptions, StlFormat } from '@aspose/3d/formats/stl';
const opts = new StlSaveOptions();
scene.save('output.stl', StlFormat.getInstance(), opts);
```

**Does scene.save() run asynchronously?**
No. `scene.save()` is synchronous. Wrap it in a worker thread if you need to avoid blocking the event loop during large exports.

**What Node.js versions are supported?**
Node.js 16, 18, 20, and 22+. Node.js 14 and earlier are not supported.

## See Also

- [How to Load 3D Models in TypeScript](../how-to-load-3d-models-in-typescript/)
- [API Reference: GltfSaveOptions](/3d/typescript/gltfsaveoptions/)
- [API Reference: GltfFormat](/3d/typescript/gltfformat/)
- [API Reference: Scene](/3d/typescript/scene/)
- [npm: @aspose/3d](https://www.npmjs.com/package/@aspose/3d)
