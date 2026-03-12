---
page_role: faq
title: "Aspose.3D FOSS for TypeScript — FAQ"
description: "Frequently asked questions about @aspose/3d — installation, format support, async loading, Node.js compatibility, and common TypeScript errors."
date: 2026-03-11
weight: 80
draft: false
type: "topic"
keywords: ["aspose 3d typescript faq", "nodejs 3d library questions", "@aspose/3d faq", "typescript 3d formats", "aspose 3d errors"]
---

## Frequently Asked Questions

### How do I install @aspose/3d?

Install from npm. Node.js 16 or later is required:

```bash
npm install @aspose/3d
```

Verify the installation:

```typescript
import { Scene } from '@aspose/3d';
const scene = new Scene();
console.log('@aspose/3d ready');
```

TypeScript type definitions are bundled with the package. No separate `@types/` package is needed.

---

### Which file formats are supported?

| Format | Import | Export |
|--------|--------|--------|
| OBJ (Wavefront) | Yes | Yes |
| glTF 2.0 / GLB | Yes | Yes |
| FBX (Autodesk) | Yes | Yes |
| STL (Stereo Lithography) | Yes | Yes |
| 3MF (3D Manufacturing) | Yes | Yes |
| COLLADA (.dae) | Yes | Yes |

---

### How do I load a 3D file?

Create a `Scene` and call `scene.open()`:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());
```

For formats that don't need special options, omit the second argument:

```typescript
const scene = new Scene();
scene.open('model.glb');
```

---

### Is scene.open() asynchronous?

No. `scene.open()` and `scene.openFromBuffer()` are synchronous calls. If you need non-blocking I/O, run them inside a Node.js worker thread or wrap with `setImmediate`.

---

### How do I save to glTF/GLB?

Call `scene.save()` with a file path. The format is detected automatically from the extension:

```typescript
scene.save('output.glb');   // binary glTF
scene.save('output.gltf');  // JSON glTF
scene.save('output.obj');   // OBJ
scene.save('output.stl');   // STL
```

---

### How do I load from a Buffer (in-memory)?

Use `scene.openFromBuffer()`:

```typescript
import * as fs from 'fs';
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const buffer = fs.readFileSync('model.obj');
const scene = new Scene();
scene.openFromBuffer(buffer, new ObjLoadOptions());
```

---

### Error: Cannot find module '@aspose/3d/formats/obj'

This requires Node.js 12.7+ package exports resolution. Ensure you are on Node.js 16+. For TypeScript, set `"moduleResolution": "node16"` or `"bundler"` in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "moduleResolution": "node16",
    "target": "ES2020"
  }
}
```

---

### What is the type of node.entity?

`node.entity` is typed broadly. To access mesh-specific properties, check for their presence with `'controlPoints' in node.entity` or use the `Mesh` class from `@aspose/3d/entities`:

```typescript
import { Mesh } from '@aspose/3d/entities';

if (node.entity instanceof Mesh) {
    const mesh = node.entity;
    console.log(mesh.controlPoints.length);
}
```

---

### Does the library run in the browser?

The library is designed for Node.js. Browser support depends on bundler configuration and file system APIs being replaced with in-memory alternatives.

---

### Is the library thread-safe?

Each `Scene` object is independent. Using separate `Scene` instances from separate Node.js worker threads is safe as long as you do not share a single scene across threads without external synchronization.

---

### What Node.js versions are supported?

Node.js 16, 18, 20, and 22 are officially supported. TypeScript 5.0+ is recommended.

---

### Does @aspose/3d support animations?

Yes. The animation system includes `AnimationClip`, `AnimationChannel`, and keyframe curve types accessible from `@aspose/3d/animation`.

---

## See Also

- [How to Load 3D Models in TypeScript](/kb.aspose.org/3d/typescript/how-to-load-3d-models-in-typescript/)
- [How to Export glTF in TypeScript](/kb.aspose.org/3d/typescript/how-to-export-gltf-in-typescript/)
- [How to Build a Mesh Programmatically](/kb.aspose.org/3d/typescript/how-to-build-mesh-programmatically-in-typescript/)
- [Installation Guide](/docs.aspose.org/3d/typescript/getting-started/installation/)
- [API Reference](/reference.aspose.org/3d/typescript/)
