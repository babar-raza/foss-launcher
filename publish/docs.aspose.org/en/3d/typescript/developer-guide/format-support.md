---
page_role: howto_article
title: "3D Format Support"
description: "Complete reference for 3D file format support in Aspose.3D FOSS for TypeScript — OBJ, glTF, GLB, STL, 3MF, FBX, COLLADA, with read/write capability, format classes, and TypeScript code examples."
type: docs
weight: 30
---

Aspose.3D FOSS for TypeScript reads and writes seven major 3D file formats. Format detection is automatic when loading: the library inspects binary magic numbers so you do not need to specify the source format. Format-specific option classes are imported from sub-paths of the `@aspose/3d` package.

## Supported Formats

| Format | Extension | Read | Write | Format Class | Notes |
|---|---|:---:|:---:|---|---|
| Wavefront OBJ | `.obj` | Yes | No | `ObjFormat` | Import only; `canExport: false` |
| glTF 2.0 | `.gltf` | Yes | Yes | `GltfFormat` | JSON text + `.bin` sidecar |
| GLB | `.glb` | Yes | Yes | `GltfFormat` | Binary glTF; set `binaryMode = true` |
| STL | `.stl` | Yes | Yes | `StlFormat` | Binary and ASCII modes |
| 3MF | `.3mf` | Yes | Yes | `ThreeMfFormat` | 3D Manufacturing Format |
| FBX | `.fbx` | Yes | Yes | `FbxFormat` | Scene, mesh, animation, materials |
| COLLADA | `.dae` | Yes | Yes | `ColladaFormat` | Requires `xmldom` (auto-installed) |

## OBJ (Wavefront)

OBJ is import-only in `@aspose/3d`. The format does not support export (`canExport: false`). Use `ObjLoadOptions` to control material loading and coordinate system behavior.

Key options for `ObjLoadOptions`:

| Option | Type | Default | Effect |
|---|---|---|---|
| `enableMaterials` | `boolean` | `false` | Parse the `.mtl` file referenced by `mtllib` |
| `flipCoordinateSystem` | `boolean` | `false` | Flip the Y/Z axes to match right-handed systems |
| `scale` | `number` | `1.0` | Uniform scale applied to all vertices on load |
| `normalizeNormal` | `boolean` | `false` | Normalize vertex normals to unit length |

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
const opts = new ObjLoadOptions();
opts.enableMaterials = true;
opts.normalizeNormal = true;

scene.open('model.obj', opts);
console.log(`Loaded ${scene.rootNode.childNodes.length} top-level node(s)`);
```

To convert an OBJ to any writable format, load it and call `scene.save()` with the target format class.

## glTF and GLB

glTF 2.0 is the recommended interchange format for web and game engine use. The library uses the same `GltfFormat` class for both `.gltf` (JSON + sidecar) and `.glb` (binary, self-contained) output. Toggle between them with `GltfSaveOptions.binaryMode`.

**Load glTF or GLB:**

```typescript
import { Scene } from '@aspose/3d';
import { GltfLoadOptions } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('model.gltf', new GltfLoadOptions());
// or
scene.open('model.glb');  // format detected from magic bytes
```

**Export as JSON glTF (`.gltf` + `.bin`):**

```typescript
import { Scene } from '@aspose/3d';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('input.fbx');

const opts = new GltfSaveOptions();
opts.binaryMode = false;  // produces output.gltf + output.bin
scene.save('output.gltf', GltfFormat.getInstance(), opts);
```

**Export as binary GLB (`.glb`):**

```typescript
import { Scene } from '@aspose/3d';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('input.obj');

const opts = new GltfSaveOptions();
opts.binaryMode = true;  // single self-contained file
scene.save('output.glb', GltfFormat.getInstance(), opts);
```

Use `binaryMode = true` for production asset delivery. A single `.glb` loads faster in browsers and engines than the split text + binary pair.

## STL

STL is a triangulated mesh format used in CAD and 3D printing. Both binary and ASCII STL are supported for input and output. `StlSaveOptions.binaryFormat` controls whether the output is binary (compact) or ASCII (human-readable).

```typescript
import { Scene } from '@aspose/3d';
import { StlLoadOptions, StlSaveOptions } from '@aspose/3d/formats/stl';

const scene = new Scene();
scene.open('model.stl', new StlLoadOptions());

// Export as binary STL (default, compact)
const binaryOpts = new StlSaveOptions();
binaryOpts.binaryFormat = true;
scene.save('output_binary.stl', binaryOpts);

// Export as ASCII STL (human-readable)
const asciiOpts = new StlSaveOptions();
asciiOpts.binaryFormat = false;
scene.save('output_ascii.stl', asciiOpts);
```

STL stores only triangulated geometry and vertex normals. Material and UV data are not preserved in STL.

## 3MF (3D Manufacturing Format)

3MF is an XML-based format designed for additive manufacturing. It supports color and material metadata alongside geometry. Use it when exchanging files with 3D printing slicers or manufacturing workflows.

```typescript
import { Scene } from '@aspose/3d';
import { ThreeMfSaveOptions } from '@aspose/3d/formats/3mf';

const scene = new Scene();
scene.open('model.3mf');

// Re-export as 3MF
scene.save('output.3mf', new ThreeMfSaveOptions());
```

3MF files are ZIP archives internally. The library handles archive creation and extraction automatically.

## FBX

FBX supports scene hierarchy, mesh and geometry data, PBR and Phong materials, animation clips, and skeletal rigs. Reading and writing are both supported.

```typescript
import { Scene } from '@aspose/3d';
import { FbxSaveOptions } from '@aspose/3d/formats/fbx';

const scene = new Scene();
scene.open('animated.fbx');

// Inspect animation clips
for (const clip of scene.animationClips) {
    console.log(`Clip: "${clip.name}", nodes: ${clip.nodes.length}`);
}

// Re-export
const saveOpts = new FbxSaveOptions();
scene.save('output.fbx', saveOpts);
```

Complex FBX files with embedded media (textures baked into the binary) may produce partial results on export. Test with your specific asset corpus when precision is required.

## COLLADA (DAE)

COLLADA is an XML-based interchange format supported by a wide range of DCC tools (Blender, Maya, Cinema 4D). The library uses the `xmldom` dependency for XML parsing; it is installed automatically with `npm install @aspose/3d`.

```typescript
import { Scene } from '@aspose/3d';
import { ColladaSaveOptions } from '@aspose/3d/formats/collada';

const scene = new Scene();
scene.open('model.dae');

// Re-export as COLLADA
const saveOpts = new ColladaSaveOptions();
scene.save('output.dae', saveOpts);
```

COLLADA files may contain unit-scaling metadata (`<unit>` element). The library applies unit conversion automatically when loading.

## Format Auto-Detection

When loading from a file path, the library tries format detection from binary magic numbers before falling back to the file extension. This means you can load a GLB file named `.bin` or an STL file named `.model` without specifying the format explicitly.

When loading from a `Buffer` with `scene.openFromBuffer()`, magic-number detection is the primary mechanism:

```typescript
import { Scene } from '@aspose/3d';
import * as fs from 'fs';

const buffer = fs.readFileSync('model.glb');
const scene = new Scene();
scene.openFromBuffer(buffer);  // format detected from magic bytes: 'glTF'

console.log(`Root has ${scene.rootNode.childNodes.length} child node(s)`);
```

Formats with reliable magic numbers: GLB (`glTF`), STL binary (80-byte header + triangle count), 3MF (ZIP magic `PK`). OBJ and COLLADA are text-based and are detected from file extension or by the options class you pass.

## Tips

- **OBJ is import-only** — to export geometry originally loaded from OBJ, save to glTF, GLB, STL, 3MF, FBX, or COLLADA.
- **Use GLB for web delivery** — the self-contained binary format avoids CORS issues with `.bin` sidecars and loads faster in WebGL renderers.
- **Pass format-specific options** — generic `scene.open(path)` works for most formats, but passing the loader options class enables format-specific behaviour such as OBJ material loading or STL coordinate normalization.
- **`xmldom` is required for COLLADA** — it is installed automatically. Do not add it to `peerDependencies` or try to remove it; the COLLADA reader calls it directly.

## Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| OBJ materials are empty after load | `enableMaterials` not set | Pass `ObjLoadOptions` with `enableMaterials = true` |
| GLB produces a `.bin` sidecar | `binaryMode` defaulting to `false` | Set `opts.binaryMode = true` in `GltfSaveOptions` |
| `scene.open()` throws "unsupported format" | File extension not recognized | Pass the matching `*LoadOptions` class or use `openFromBuffer()` |
| COLLADA load fails with XML error | `xmldom` missing or mismatched | Run `npm install @aspose/3d` again; `xmldom` is a direct dependency |
| STL normals lost in ASCII export | ASCII STL drops per-face normals | Use `binaryFormat = true` for normal-preserving output |

## See Also

- [Features and Functionalities](/docs.aspose.org/3d/typescript/developer-guide/features/) — scene graph, mesh, materials, animation, and math APIs.
- [Scene Graph](/docs.aspose.org/3d/typescript/developer-guide/scene-graph/) — building and traversing the node tree.
- [How to Build a 3D Mesh Programmatically](/kb.aspose.org/3d/typescript/how-to-build-mesh-programmatically-in-typescript/)
