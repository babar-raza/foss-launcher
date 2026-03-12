---
page_role: howto_article
title: "Troubleshooting @aspose/3d for TypeScript"
description: "Diagnose and fix common errors with @aspose/3d — module resolution failures, empty scenes, missing materials, format errors, and TypeScript compilation issues."
date: 2026-03-11
weight: 90
draft: false
type: "topic"
keywords: ["aspose 3d typescript error", "@aspose/3d troubleshooting", "aspose 3d module not found", "@aspose/3d empty scene", "aspose 3d glb error typescript"]
---

This page covers the most common errors encountered when using `@aspose/3d` in TypeScript and Node.js projects, with root-cause explanations and verified fixes.

---

## Module Resolution Errors

### `Error: Cannot find module '@aspose/3d/formats/obj'`

**Root cause**: TypeScript's module resolution strategy does not support Node.js-style sub-path exports (`exports` in `package.json`) unless `moduleResolution` is set to `node` or `node16`.

**Fix**: Set `moduleResolution` to `"node"` in your `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "moduleResolution": "node",
    "esModuleInterop": true,
    "strict": true
  }
}
```

If you are using TypeScript 5.x with `"module": "node16"` or `"module": "nodenext"`, use `"moduleResolution": "node16"` to match.

---

### `SyntaxError: Cannot use import statement in a module`

**Root cause**: The compiled JavaScript is being run with `require()` semantics but the output contains ES module `import` syntax — this happens when `module` is set to `es2020` or `esnext` but the Node.js runtime expects CommonJS.

**Fix**: Use `"module": "commonjs"` in `tsconfig.json` and run the compiled `.js` files with `node` directly:

```json
{
  "compilerOptions": {
    "module": "commonjs",
    "outDir": "./dist"
  }
}
```

Then compile and run:

```bash
npx tsc
node dist/main.js
```

---

### `Error: Cannot find module '@aspose/3d'`

**Root cause**: The package is not installed, or `node_modules` is stale.

**Fix**:

```bash
npm install @aspose/3d
```

Verify the installation:

```bash
node -e "const { Scene } = require('@aspose/3d'); console.log('OK', new Scene().constructor.name);"
```

---

## Empty Scene After Loading

### Scene loads but `rootNode.childNodes` is empty

**Root cause (1)**: The file format places all geometry directly on `rootNode.entity` rather than as child nodes. This is common with single-mesh STL files.

**Diagnosis**:

```typescript
import { Scene, Mesh } from '@aspose/3d';

const scene = new Scene();
scene.open('model.stl');

// Check rootNode directly
if (scene.rootNode.entity) {
    console.log(`Root entity: ${scene.rootNode.entity.constructor.name}`);
}
console.log(`Child count: ${scene.rootNode.childNodes.length}`);
```

**Fix**: Traverse starting from `scene.rootNode` itself, not only its children:

```typescript
function visit(node: any): void {
    if (node.entity instanceof Mesh) {
        const m = node.entity as Mesh;
        console.log(`Mesh: ${m.controlPoints.length} vertices`);
    }
    for (const child of node.childNodes) {
        visit(child);
    }
}
visit(scene.rootNode);
```

**Root cause (2)**: The file path is wrong or the file is zero bytes. Check that the file exists and is non-empty before calling `open()`.

```typescript
import * as fs from 'fs';

const path = 'model.obj';
if (!fs.existsSync(path)) throw new Error(`File not found: ${path}`);
const stat = fs.statSync(path);
if (stat.size === 0) throw new Error(`File is empty: ${path}`);
```

---

### Materials list is empty after OBJ load

**Root cause**: Material loading is disabled by default in `ObjLoadOptions`. The library loads the geometry without reading the `.mtl` sidecar file.

**Fix**: Set `enableMaterials = true`:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
const opts = new ObjLoadOptions();
opts.enableMaterials = true;
scene.open('model.obj', opts);
```

Also ensure the `.mtl` file is in the same directory as the `.obj` file, as the library resolves it relative to the `.obj` path.

---

## Format and I/O Errors

### `openFromBuffer` throws an unrecognized format error

**Root cause**: The buffer content is not a recognizable binary format, or the buffer is corrupt (truncated, wrong encoding, or base64 instead of raw bytes).

**Diagnosis**:

```typescript
const buffer = fs.readFileSync('model.glb');
console.log('Buffer size:', buffer.length, 'bytes');
console.log('First 4 bytes (hex):', buffer.slice(0, 4).toString('hex'));
// GLB magic: 676c5446 ("glTF")
// STL binary starts with 80 bytes of header; no fixed magic
// OBJ is text — openFromBuffer may not detect format
```

**Fix**: For text-based formats (OBJ, COLLADA), pass the appropriate options class to hint the format:

```typescript
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
scene.openFromBuffer(buffer, new ObjLoadOptions());
```

---

### Output GLB opens as JSON in 3D viewers

**Root cause**: `GltfSaveOptions.binaryMode` defaults to `false`, producing `.gltf` JSON output even when the output filename is `.glb`.

**Fix**: Explicitly set `binaryMode = true`:

```typescript
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

const opts = new GltfSaveOptions();
opts.binaryMode = true;
scene.save('output.glb', opts);
```

---

### STL output has no color or material data in the slicer

**Root cause**: The STL format does not support materials or color in its standard specification. Color-capable slicers use proprietary extensions not supported by `@aspose/3d`.

**Fix**: Export to 3MF instead, which supports color and material metadata:

```typescript
scene.save('output.3mf');
```

---

## TypeScript Compilation Errors

### `Property 'controlPoints' does not exist on type 'Entity'`

**Root cause**: `Entity` is the base class; `Mesh` is the concrete type with geometry properties. You need an `instanceof` guard before accessing mesh-specific members.

**Fix**:

```typescript
import { Mesh } from '@aspose/3d';

if (node.entity instanceof Mesh) {
    const mesh = node.entity as Mesh;
    console.log(mesh.controlPoints.length);
}
```

---

### `Type 'null' is not assignable to type 'Node'`

**Root cause**: `getChildNode()` returns `Node | null`. TypeScript strict mode requires you to handle the null case.

**Fix**:

```typescript
const child = node.getChildNode('wheel');
if (!child) throw new Error('Node "wheel" not found');
// child is now Node, not null
```

---

### `Cannot find name 'GltfSaveOptions'`

**Root cause**: `GltfSaveOptions` is in the sub-path module `@aspose/3d/formats/gltf`, not the package root.

**Fix**: Import from the sub-path:

```typescript
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';
```

---

## Memory and Performance Issues

### Process runs out of memory with large FBX files

**Root cause**: Very large FBX files (>200 MB) allocate significant heap. Node.js default heap is ~1.5 GB on 64-bit systems but may not be sufficient for multi-scene files.

**Fix**: Increase the Node.js heap size:

```bash
node --max-old-space-size=8192 dist/convert.js
```

Also process files sequentially rather than in parallel when memory is constrained:

```typescript
for (const file of files) {
    const scene = new Scene();
    scene.open(file);
    scene.save(file.replace('.fbx', '.glb'));
    // scene goes out of scope; GC can reclaim
}
```

---

## See Also

- [FAQ](/kb.aspose.org/3d/typescript/faq/) — quick answers to common questions
- [Model Loading](/docs.aspose.org/3d/typescript/developer-guide/model-loading/) — loading patterns and options
- [Rendering and Export](/docs.aspose.org/3d/typescript/developer-guide/rendering/) — export options and buffer pipelines
- [API Overview](/reference.aspose.org/3d/typescript/api-overview/) — all classes and modules
