---
page_role: howto_article
title: "Scene Rendering and Export"
description: "How to export 3D scenes from @aspose/3d for TypeScript — GLB, glTF, STL, FBX, COLLADA, and 3MF output, in-memory buffer export, format options, and integration with downstream renderers."
type: docs
weight: 30
---

`@aspose/3d` is a processing and conversion library — it does not perform GPU rendering or produce image files. "Rendering" in the context of this library means **exporting a scene to a format that a downstream renderer, game engine, or viewer can consume**.

This page covers all export paths: file-based saving, in-memory buffer output, format-specific options, and how to prepare scenes for common downstream targets (Three.js, Babylon.js, model viewers, and game engines).

## Basic Export

Call `scene.save()` with a file path. The library infers the output format from the file extension:

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('input.fbx');

scene.save('output.glb');    // GLB (binary glTF)
scene.save('output.stl');    // STL
scene.save('output.dae');    // COLLADA
scene.save('output.3mf');    // 3MF
```

## Exporting to GLB (Recommended for Web and Games)

GLB (binary glTF 2.0) is a single self-contained file that embeds all mesh data, materials, and textures. It is the recommended output format for web viewers (Three.js, Babylon.js, model-viewer) and game engines (Godot, Unity via importer):

```typescript
import { Scene } from '@aspose/3d';
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('source.obj');

const opts = new GltfSaveOptions();
opts.binaryMode = true;    // produce .glb instead of .gltf + .bin
opts.embedAssets = true;   // embed all referenced assets into the binary

scene.save('output.glb', opts);
console.log('GLB export complete');
```

Set `embedAssets = true` whenever you need a truly self-contained file. When false, external texture references in the source file are preserved as relative paths in the `.gltf` output — which can break in environments that do not have access to those paths.

## Exporting to glTF (JSON Format for Inspection)

The JSON variant (`.gltf` + `.bin`) is useful during development because the JSON is human-readable:

```typescript
import { Scene } from '@aspose/3d';
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('input.fbx');

const opts = new GltfSaveOptions();
opts.binaryMode = false;  // JSON + .bin sidecar

scene.save('output.gltf', opts);
```

## Exporting to STL (3D Printing Workflows)

STL is geometry-only (no materials, no animation). It is the standard exchange format for 3D printing slicers:

```typescript
import { Scene } from '@aspose/3d';
import { StlSaveOptions } from '@aspose/3d/formats/stl';

const scene = new Scene();
scene.open('model.obj');

const opts = new StlSaveOptions();
opts.binaryMode = true;   // binary STL is more compact than ASCII

scene.save('output.stl', opts);
```

Set `binaryMode = false` to produce ASCII STL, which is text-readable but larger.

## Exporting to FBX (DCC Tool Workflows)

FBX output preserves scene hierarchy, mesh data, materials, and animation clips. Use it when the output will be imported into Blender, Maya, or Unreal Engine:

```typescript
import { Scene } from '@aspose/3d';
import { FbxSaveOptions } from '@aspose/3d/formats/fbx';

const scene = new Scene();
scene.open('input.dae');

const opts = new FbxSaveOptions();
scene.save('output.fbx', opts);
```

## In-Memory Export with `saveToBuffer()`

For serverless functions, HTTP responses, and streaming pipelines, export directly to a `Buffer` without writing to disk:

```typescript
import { Scene } from '@aspose/3d';
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

async function convertToGlbBuffer(inputPath: string): Promise<Buffer> {
    const scene = new Scene();
    scene.open(inputPath);

    const opts = new GltfSaveOptions();
    opts.binaryMode = true;
    opts.embedAssets = true;

    return scene.saveToBuffer('output.glb', opts);
}

// Express.js / HTTP response example
// const glbBuffer = await convertToGlbBuffer('model.obj');
// res.setHeader('Content-Type', 'model/gltf-binary');
// res.send(glbBuffer);
```

`saveToBuffer()` takes the output file name as the first argument (the extension is used for format inference) and the same options objects as `save()`.

## Combining `openFromBuffer()` and `saveToBuffer()`

A fully in-memory conversion pipeline — no disk I/O at any stage:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

function objBufferToGlbBuffer(objData: Buffer): Buffer {
    const scene = new Scene();

    const loadOpts = new ObjLoadOptions();
    loadOpts.enableMaterials = true;
    scene.openFromBuffer(objData, loadOpts);

    const saveOpts = new GltfSaveOptions();
    saveOpts.binaryMode = true;
    saveOpts.embedAssets = true;

    return scene.saveToBuffer('output.glb', saveOpts);
}
```

## Preparing Scenes for Specific Renderers

### Three.js / Babylon.js (Web)

These renderers natively load GLB files. Export with `binaryMode = true` and `embedAssets = true`. If textures are referenced from the source OBJ, ensure the `.mtl` and image files are co-located when loading, so they are picked up and embedded.

### model-viewer (Web Component)

Accepts `.glb` directly. Same export settings as Three.js.

### Godot Engine

Import GLB via Godot's importer (Project → Import). Use `binaryMode = true`. Godot supports PBR materials from glTF 2.0 natively.

### Blender

For the best import fidelity use FBX (`output.fbx`) or glTF (`output.gltf` + `output.bin`). Blender's glTF 2.0 importer handles PBR materials; the FBX importer handles animation.

### 3D Printing (Slicers: Cura, PrusaSlicer, Bambu Studio)

Export to STL or 3MF. Use 3MF when you need color or material metadata preserved. Use STL for maximum compatibility.

## Export Format Comparison

| Format | Extension | Materials | Animation | Single File | Best For |
|--------|-----------|:---------:|:---------:|:-----------:|----------|
| GLB | `.glb` | PBR (glTF 2.0) | Yes | Yes | Web, games, general delivery |
| glTF | `.gltf` | PBR (glTF 2.0) | Yes | No (+ .bin) | Development, inspection |
| STL | `.stl` | No | No | Yes | 3D printing, geometry-only |
| FBX | `.fbx` | Phong/PBR | Yes | Yes | DCC tools (Maya, Blender, Unreal) |
| COLLADA | `.dae` | Yes | Yes | Yes | Cross-DCC exchange |
| 3MF | `.3mf` | Color/material | No | Yes | Modern 3D printing |

## Common Export Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Output GLB opens as JSON in viewer | `binaryMode` left as `false` | Set `opts.binaryMode = true` |
| Textures missing in output GLB | `embedAssets` not set | Set `opts.embedAssets = true` |
| STL file has no color in slicer | STL format does not support color | Use 3MF for color data |
| `saveToBuffer` returns empty buffer | Extension argument missing or wrong | Pass the full filename with extension, e.g. `'output.glb'` |
| FBX opens without animation in Blender | Source file (OBJ/STL) has no animation | Animation only carries through if present in the source |
| Output file is very large | Source OBJ has many duplicate vertices | GLB binary output already deduplicates; check source asset quality |

## See Also

- [Model Loading](model-loading/) — loading 3D files from disk and buffers
- [Scene Graph](scene-graph/) — building and modifying the scene before export
- [Format Support](format-support/) — complete read/write matrix
- [API Overview](/reference.aspose.org/3d/typescript/api-overview/) — all classes and enumerations
