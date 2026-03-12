---
page_role: howto_article
title: "Loading 3D Models"
description: "How to load 3D files in TypeScript using @aspose/3d — file path loading, Buffer I/O, format-specific options, scene graph inspection, and error handling patterns."
type: docs
weight: 20
---

`@aspose/3d` provides two loading methods on the `Scene` class: `open()` for file-path loading and `openFromBuffer()` for in-memory data. Format detection is automatic from binary magic numbers or file extension, so you rarely need to specify the source format explicitly.

## Loading from a File Path

Pass the file path string to `scene.open()`. The library detects the format from the file extension and, for binary formats, from the magic bytes:

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('model.fbx');

console.log(`Root children: ${scene.rootNode.childNodes.length}`);
console.log(`Animation clips: ${scene.animationClips.length}`);
```

`open()` replaces any existing scene content. If you need to load multiple files, create separate `Scene` instances.

## Loading OBJ with Materials

OBJ files reference materials through a sidecar `.mtl` file. Material loading is off by default. Enable it with `ObjLoadOptions`:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
const options = new ObjLoadOptions();
options.enableMaterials = true;       // load the .mtl sidecar
options.flipCoordinateSystem = false; // keep original Y-up orientation
options.normalizeNormal = true;       // fix degenerate normals
options.scale = 1.0;                  // unit scale multiplier

scene.open('character.obj', options);

// Inspect materials on the first node
const first = scene.rootNode.childNodes[0];
if (first) {
    console.log(`Materials on ${first.name}: ${first.materials.length}`);
}
```

## Loading from a Buffer

Use `openFromBuffer()` when the file data is already in memory — for example, from an HTTP fetch, a database BLOB, or a zip archive extraction. This avoids writing to disk:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import * as fs from 'fs';

const buffer: Buffer = fs.readFileSync('model.obj');
const scene = new Scene();
const options = new ObjLoadOptions();
options.enableMaterials = true;

scene.openFromBuffer(buffer, options);
console.log(`Loaded ${scene.rootNode.childNodes.length} root nodes`);
```

For binary formats (GLB, STL binary, 3MF), the library reads the magic bytes from the buffer to detect the format automatically, so you can pass `undefined` as the options argument:

```typescript
import { Scene } from '@aspose/3d';
import * as fs from 'fs';

const glbBuffer: Buffer = fs.readFileSync('model.glb');
const scene = new Scene();
scene.openFromBuffer(glbBuffer); // format auto-detected from GLB magic bytes
```

## Loading from HTTP (Node.js 18+)

Fetch a remote asset and load it without touching the file system:

```typescript
import { Scene } from '@aspose/3d';

async function loadFromUrl(url: string): Promise<Scene> {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    const scene = new Scene();
    scene.openFromBuffer(buffer);
    return scene;
}

const scene = await loadFromUrl('https://example.com/model.glb');
console.log(`Loaded scene: ${scene.rootNode.childNodes.length} root nodes`);
```

## Inspecting the Loaded Scene

After loading, walk the scene graph to enumerate nodes and identify geometry:

```typescript
import { Scene, Mesh, Node } from '@aspose/3d';

const scene = new Scene();
scene.open('model.fbx');

function inspect(node: Node, depth: number = 0): void {
    const indent = '  '.repeat(depth);
    const entityType = node.entity ? node.entity.constructor.name : '(none)';
    console.log(`${indent}${node.name} [${entityType}]`);

    if (node.entity instanceof Mesh) {
        const mesh = node.entity as Mesh;
        console.log(`${indent}  vertices: ${mesh.controlPoints.length}, polygons: ${mesh.polygonCount}`);
    }

    for (const child of node.childNodes) {
        inspect(child, depth + 1);
    }
}

inspect(scene.rootNode);
```

## Reading Asset Metadata

The `assetInfo` property exposes file-level metadata:

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('model.fbx');

const info = scene.assetInfo;
if (info) {
    console.log(`Creator: ${info.creator}`);
    console.log(`Unit name: ${info.unitName}`);
    console.log(`Unit scale: ${info.unitScaleFactor}`);
}
```

Not all formats populate `assetInfo`. FBX and COLLADA have rich metadata; OBJ and STL typically do not.

## Format-Specific Load Options Reference

| Format | Options Class | Import Path | Key Options |
|--------|---------------|-------------|-------------|
| OBJ | `ObjLoadOptions` | `@aspose/3d/formats/obj` | `enableMaterials`, `flipCoordinateSystem`, `scale`, `normalizeNormal` |
| glTF / GLB | *(none required)* | — | Auto-detected; no options class needed |
| STL | `StlLoadOptions` | `@aspose/3d/formats/stl` | *(no configurable options in current version)* |
| FBX | `FbxLoadOptions` | `@aspose/3d/formats/fbx` | *(no configurable options in current version)* |
| COLLADA | `ColladaLoadOptions` | `@aspose/3d/formats/collada` | *(no configurable options in current version)* |
| 3MF | *(none required)* | — | Auto-detected |

## Common Loading Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Error: Cannot find module '@aspose/3d/formats/obj'` | `moduleResolution` not set to `node` | Add `"moduleResolution": "node"` to `tsconfig.json` |
| Empty node list after loading OBJ | `.mtl` sidecar missing or `enableMaterials` not set | Set `options.enableMaterials = true` and ensure `.mtl` is in the same directory |
| Scene loads but `rootNode.childNodes` is empty | Format uses a single root mesh, not child nodes | Access `scene.rootNode.entity` directly |
| `openFromBuffer` throws with binary STL | Buffer was sliced incorrectly — trailing bytes missing | Use the full `readFileSync()` output without slicing |
| Animation clips array is empty after FBX load | FBX file uses baked transforms, not clips | Animation is baked per frame; the clip array will be empty |

## See Also

- [Saving 3D Models](/docs.aspose.org/3d/typescript/developer-guide/rendering/) — export options and `saveToBuffer`
- [Scene Graph](scene-graph/) — traversing and modifying the node hierarchy
- [API Overview](/reference.aspose.org/3d/typescript/api-overview/) — all classes and enumerations
- [Format Support](format-support/) — complete read/write matrix
