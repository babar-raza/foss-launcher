---
page_role: howto_article
title: "Features and Functionalities"
description: "Complete reference for Aspose.3D FOSS for TypeScript — format support, scene graph, geometry, materials, math, animation, and buffer loading, with TypeScript code examples."
type: docs
weight: 10
---

Aspose.3D FOSS for TypeScript is a MIT-licensed Node.js library for loading, constructing, and exporting 3D scenes. It ships with complete TypeScript type definitions, a single runtime dependency (`xmldom`), and support for six major 3D file formats. This page is the primary reference for all feature areas and includes runnable TypeScript code examples for each one.

## Installation and Setup

Install the package from npm using a single command:

```bash
npm install @aspose/3d
```

The package targets CommonJS and requires Node.js 16 or later. After installation, verify your `tsconfig.json` includes the following compiler options for full compatibility:

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

Import the main `Scene` class from the package root. Format-specific option classes are imported from their respective sub-paths:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';
```

## Features and Functionalities

### Format Support

Aspose.3D FOSS for TypeScript reads and writes six major 3D file formats. Format detection is automatic from binary magic numbers when loading, so you do not need to specify the source format explicitly.

| Format | Read | Write | Notes |
|---|---|---|---|
| OBJ (Wavefront) | Yes | No | Import only; .mtl material loading via `ObjLoadOptions.enableMaterials` |
| glTF 2.0 | Yes | Yes | JSON text format; PBR materials |
| GLB | Yes | Yes | Binary glTF; set `GltfSaveOptions.binaryMode = true` |
| STL | Yes | Yes | Binary and ASCII; full roundtrip verified |
| 3MF | Yes | Yes | 3D Manufacturing Format with color and material metadata |
| FBX | Yes | Yes | Scene hierarchy, mesh, animation, and material data |
| COLLADA (DAE) | Yes | Yes | Unit scaling, geometry, materials, and animation clips |

**Loading OBJ with materials:**

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
const options = new ObjLoadOptions();
options.enableMaterials = true;
options.flipCoordinateSystem = false;
options.scale = 1.0;
options.normalizeNormal = true;
scene.open('model.obj', options);
```

**Saving to GLB (binary glTF):**

```typescript
import { Scene } from '@aspose/3d';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
// ... build or load scene content

const opts = new GltfSaveOptions();
opts.binaryMode = true;
scene.save('output.glb', GltfFormat.getInstance(), opts);
```

### Scene Graph

All 3D content is organized as a tree of `Node` objects rooted at `scene.rootNode`. Each node can carry an `Entity` (a `Mesh`, `Camera`, `Light`, or other `SceneObject`) and a `Transform` that positions it relative to its parent.

Key scene-graph classes:

- `Scene` — the top-level container; holds `rootNode` and `animationClips`
- `Node` — a named tree node with `childNodes`, `entity`, `transform`, and `materials`
- `Entity` — base class for attachable objects (`Mesh`, `Camera`, `Light`)
- `SceneObject` — base class shared by `Node` and `Entity`
- `A3DObject` — root base class with `name` and property bag
- `Transform` — local translation, rotation (Euler and Quaternion), and scale

**Traversing the scene graph:**

```typescript
import { Scene, Node, Mesh } from '@aspose/3d';

const scene = new Scene();
scene.open('model.obj');

function visit(node: Node, depth: number = 0): void {
  const indent = '  '.repeat(depth);
  console.log(`${indent}Node: ${node.name}`);
  if (node.entity) {
    console.log(`${indent}  Entity: ${node.entity.constructor.name}`);
  }
  for (const child of node.childNodes) {
    visit(child, depth + 1);
  }
}

visit(scene.rootNode);
```

**Creating a scene hierarchy programmatically:**

```typescript
import { Scene, Node } from '@aspose/3d';

const scene = new Scene();
const parent = scene.rootNode.createChildNode('chassis');
const wheel = parent.createChildNode('wheel_fl');
wheel.transform.translation.set(0.9, -0.3, 1.4);
```

### Geometry and Mesh

`Mesh` is the primary geometry type. It extends `Geometry` and exposes control points (vertices), polygon indices, and vertex elements for normals, UVs, and vertex colors.

Key geometry classes:

- `Mesh` — polygon mesh with `controlPoints` and `polygonCount`
- `Geometry` — base class with vertex-element management
- `VertexElementNormal` — per-vertex or per-polygon-vertex normals
- `VertexElementUV` — texture coordinates (one or more UV channels)
- `VertexElementVertexColor` — per-vertex color data
- `MappingMode` — controls how element data maps to polygons (`ByControlPoint`, `ByPolygonVertex`, etc.)
- `ReferenceMode` — controls indexing strategy (`Direct`, `IndexToDirect`)
- `VertexElementType` — identifies the semantic of a vertex element
- `TextureMapping` — texture channel enumeration

**Reading mesh data from a loaded scene:**

```typescript
import { Scene, Mesh, VertexElementType } from '@aspose/3d';

const scene = new Scene();
scene.open('model.stl');

for (const node of scene.rootNode.childNodes) {
  if (node.entity instanceof Mesh) {
    const mesh = node.entity as Mesh;
    console.log(`Mesh "${node.name}": ${mesh.controlPoints.length} vertices, ${mesh.polygonCount} polygons`);

    const normals = mesh.getElement(VertexElementType.NORMAL);
    if (normals) {
      console.log(`  Normal mapping: ${normals.mappingMode}`);
    }
  }
}
```

### Material System

Aspose.3D FOSS for TypeScript supports three material types covering the full range from legacy Phong shading to physically-based rendering:

- `LambertMaterial` — diffuse color and ambient color; maps to simple OBJ/DAE materials
- `PhongMaterial` — adds specular color, shininess, and emissive; the default OBJ material type
- `PbrMaterial` — physically-based roughness/metallic model; used for glTF 2.0 import and export

**Reading materials from a loaded OBJ scene:**

```typescript
import { Scene, PhongMaterial, LambertMaterial } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
const options = new ObjLoadOptions();
options.enableMaterials = true;
scene.open('model.obj', options);

for (const node of scene.rootNode.childNodes) {
  for (const mat of node.materials) {
    if (mat instanceof PhongMaterial) {
      const phong = mat as PhongMaterial;
      console.log(`  Phong: diffuse=${JSON.stringify(phong.diffuseColor)}, shininess=${phong.shininess}`);
    } else if (mat instanceof LambertMaterial) {
      console.log(`  Lambert: diffuse=${JSON.stringify((mat as LambertMaterial).diffuseColor)}`);
    }
  }
}
```

**Applying a PBR material when building a glTF scene:**

```typescript
import { Scene, Node, PbrMaterial } from '@aspose/3d';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
const node = scene.rootNode.createChildNode('sphere');
const mat = new PbrMaterial();
mat.albedo.set(0.8, 0.2, 0.2);   // red-tinted albedo
mat.metallic = 0.0;
mat.roughness = 0.5;
node.material = mat;

const opts = new GltfSaveOptions();
opts.binaryMode = false;
scene.save('output.gltf', GltfFormat.getInstance(), opts);
```

### Math Utilities

The library ships with a complete set of 3D math types, all fully typed:

- `Vector3` — 3-component vector; supports `add`, `subtract`, `scale`, `dot`, `cross`, `normalize`, `length`
- `Vector4` — 4-component vector for homogeneous coordinates
- `Matrix4` — 4×4 transformation matrix with `multiply`, `invert`, `transpose`, `decompose`
- `Quaternion` — rotation quaternion with `fromEulerAngles`, `toEulerAngles`, `slerp`, `normalize`
- `BoundingBox` — axis-aligned bounding box with `min`, `max`, `center`, `size`, `merge`
- `FVector3` — single-precision variant of `Vector3` used in vertex element data

**Computing a bounding box from mesh vertices:**

```typescript
import { Scene, Mesh, Vector3, BoundingBox } from '@aspose/3d';

const scene = new Scene();
scene.open('model.obj');

let box = new BoundingBox();
for (const node of scene.rootNode.childNodes) {
  if (node.entity instanceof Mesh) {
    for (const pt of (node.entity as Mesh).controlPoints) {
      box.merge(new Vector3(pt.x, pt.y, pt.z));
    }
  }
}
console.log('Center:', box.center);
console.log('Extents:', box.size);
```

**Building a transform from Euler angles:**

```typescript
import { Quaternion, Vector3, Matrix4 } from '@aspose/3d';

const rot = Quaternion.fromEulerAngle(0, Math.PI / 4, 0); // 45° around Y
const mat = new Matrix4();
mat.setTRS(new Vector3(0, 0, 0), rot, new Vector3(1, 1, 1));
```

### Animation System

The animation API models clips, nodes, channels, and keyframe sequences:

- `AnimationClip` — named collection of animation nodes; accessed via `scene.animationClips`
- `AnimationNode` — binds a clip to a scene node by name
- `AnimationChannel` — targets a specific property (e.g., translation X) within an animation node
- `KeyFrame` — a single time/value pair
- `KeyframeSequence` — ordered list of `KeyFrame` objects with `Interpolation` and `Extrapolation` settings
- `Interpolation` — keyframe interpolation mode: `Linear`, `Constant`, `Cubic`
- `Extrapolation` — behavior before/after the keyframe range: `Constant`, `Cycle`, `Mirror`

**Reading animation data from a loaded scene:**

```typescript
import { Scene, AnimationClip, KeyframeSequence } from '@aspose/3d';

const scene = new Scene();
scene.open('animated.fbx');

for (const clip of scene.animationClips) {
  console.log(`Clip: "${clip.name}"`);
  for (const animNode of clip.nodes) {
    console.log(`  Node: ${animNode.name}`);
    for (const channel of animNode.channels) {
      const seq: KeyframeSequence = channel.keyframeSequence;
      console.log(`    Channel "${channel.name}": ${seq.keyFrames.length} keyframes`);
      console.log(`    Interpolation: ${seq.interpolation}`);
    }
  }
}
```

### Stream and Buffer Support

Use `scene.openFromBuffer()` to load a 3D scene directly from an in-memory `Buffer`. This is the recommended pattern for serverless functions, streaming pipelines, and processing assets fetched over HTTP without writing to disk.

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import * as fs from 'fs';

// Load file into memory, then parse from buffer
const buffer: Buffer = fs.readFileSync('model.obj');
const scene = new Scene();
const options = new ObjLoadOptions();
options.enableMaterials = true;
scene.openFromBuffer(buffer, options);

for (const node of scene.rootNode.childNodes) {
  if (node.entity) {
    console.log(node.name, node.entity.constructor.name);
  }
}
```

Format auto-detection from binary magic numbers applies when loading from buffer, so GLB, STL binary, and 3MF files are recognized without specifying a format parameter.

## Usage Examples

### Example 1: Load OBJ and Export to GLB

This example loads a Wavefront OBJ file with materials, then re-exports the scene as a binary glTF (GLB) file suitable for web and game engine use.

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

async function convertObjToGlb(inputPath: string, outputPath: string): Promise<void> {
  const scene = new Scene();

  const loadOpts = new ObjLoadOptions();
  loadOpts.enableMaterials = true;
  loadOpts.flipCoordinateSystem = false;
  loadOpts.normalizeNormal = true;
  scene.open(inputPath, loadOpts);

  // Report what was loaded
  for (const node of scene.rootNode.childNodes) {
    if (node.entity) {
      console.log(`Loaded: ${node.name} (${node.entity.constructor.name})`);
    }
  }

  const saveOpts = new GltfSaveOptions();
  saveOpts.binaryMode = true; // write .glb instead of .gltf + .bin
  scene.save(outputPath, GltfFormat.getInstance(), saveOpts);

  console.log(`Exported GLB to: ${outputPath}`);
}

convertObjToGlb('input.obj', 'output.glb');
```

### Example 2: Round-Trip STL with Normal Validation

This example loads a binary STL file, prints per-vertex normal information, then re-exports the scene as ASCII STL and verifies the roundtrip.

```typescript
import { Scene, Mesh, VertexElementNormal, VertexElementType } from '@aspose/3d';
import { StlLoadOptions, StlSaveOptions } from '@aspose/3d/formats/stl';

const scene = new Scene();
const loadOpts = new StlLoadOptions();
scene.open('model.stl', loadOpts);

let totalPolygons = 0;
for (const node of scene.rootNode.childNodes) {
  if (node.entity instanceof Mesh) {
    const mesh = node.entity as Mesh;
    totalPolygons += mesh.polygonCount;

    const normElem = mesh.getElement(VertexElementType.NORMAL) as VertexElementNormal | null;
    if (normElem) {
      console.log(`  Normals: ${normElem.data.length} entries, mapping=${normElem.mappingMode}`);
    }
  }
}
console.log(`Total polygons: ${totalPolygons}`);

// Re-export as ASCII STL
const saveOpts = new StlSaveOptions();
saveOpts.binaryMode = false; // ASCII output
scene.save('output_ascii.stl', saveOpts);
```

### Example 3: Build a Scene Programmatically and Save as glTF

This example constructs a scene with a PBR material from scratch and saves it as a JSON glTF file.

```typescript
import { Scene, Mesh, PbrMaterial, Vector4 } from '@aspose/3d';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
const node = scene.rootNode.createChildNode('floor');

// Build a simple quad mesh (two triangles)
// controlPoints are Vector4 (x, y, z, w) where w=1 for positions
const mesh = new Mesh();
mesh.controlPoints.push(
  new Vector4(-1, 0, -1, 1),
  new Vector4( 1, 0, -1, 1),
  new Vector4( 1, 0,  1, 1),
  new Vector4(-1, 0,  1, 1),
);
mesh.createPolygon([0, 1, 2]);
mesh.createPolygon([0, 2, 3]);
node.entity = mesh;

// Apply a PBR material
const mat = new PbrMaterial();
mat.albedo.set(0.6, 0.6, 0.6);
mat.metallic = 0.0;
mat.roughness = 0.8;
node.material = mat;

// Save as JSON glTF
const opts = new GltfSaveOptions();
opts.binaryMode = false;
scene.save('floor.gltf', GltfFormat.getInstance(), opts);
console.log('Scene written to floor.gltf');
```

## Tips and Best Practices

- **Use `ObjLoadOptions.enableMaterials = true`** whenever you need material data from .mtl files. Without it, the material list on each node will be empty.
- **Prefer `binaryMode = true` for GLB** when producing assets for web or game engines. Binary GLB is a single self-contained file and loads faster in browsers and engines than the JSON + .bin split.
- **Use `openFromBuffer()` in serverless environments** to avoid temporary file I/O. Fetch the asset, pass the `Buffer` directly, and write the output to a stream or another buffer.
- **Check `node.entity` before casting** — not all nodes carry an entity. Always guard with an `instanceof` check before accessing `Mesh`-specific properties such as `controlPoints`.
- **Set `normalizeNormal = true` in `ObjLoadOptions`** when your source OBJ files come from untrusted sources. This prevents degenerate normals from propagating into downstream rendering or validation steps.
- **Keep `strict: true` in tsconfig.json** — the library is authored with `noImplicitAny` and `strictNullChecks`. Disabling `strict` masks real type errors and defeats the value of the typed API.
- **Traverse via `childNodes`, not an index loop** — the `childNodes` property returns an iterable; avoid relying on numeric indexing for forward compatibility.

## Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| Materials list empty after OBJ load | `enableMaterials` not set | Set `options.enableMaterials = true` |
| GLB file contains separate .bin sidecar | `binaryMode` defaulting to `false` | Set `opts.binaryMode = true` |
| Vertex normals missing in STL output | STL ASCII mode omits per-face normals | Switch to `binaryMode = true` or compute normals before export |
| `node.entity` is always `null` | Traversing only `rootNode`, not its children | Recurse into `node.childNodes` |
| TypeScript error: property does not exist | Old `@types` cache | Run `npm install @aspose/3d` again; no separate `@types` package is needed |
| `openFromBuffer` throws format error | Format not auto-detectable from magic | Pass explicit format option class as second argument |

## Frequently Asked Questions

**Does the library require any native addons or system packages?**
No. Aspose.3D FOSS for TypeScript has a single runtime dependency: `xmldom`, which is pure JavaScript and installed automatically by npm. There are no `.node` native addons and no system packages to install.

**Which Node.js versions are supported?**
Node.js 16, 18, 20, and 22 LTS. The library targets CommonJS output and uses ES2020 language features internally.

**Can I use the library in a browser bundle (webpack/esbuild)?**
The library targets Node.js and uses the Node.js `fs` and `Buffer` APIs. Browser bundling is not officially supported. For browser use, load the scene server-side and transmit the result (e.g., as GLB) to the client.

**What is the difference between `GltfSaveOptions.binaryMode = true` and `false`?**
`binaryMode = false` produces a `.gltf` JSON file plus a separate `.bin` binary buffer sidecar. `binaryMode = true` produces a single self-contained `.glb` file. Use `true` for production asset delivery.

**Can I load a file from an HTTP response without saving it to disk?**
Yes. Fetch the response as a `Buffer` (e.g., using `node-fetch` or the built-in `fetch` in Node 18+), then call `scene.openFromBuffer(buffer, options)`.

**Is FBX support complete?**
FBX reading and writing is supported for scene hierarchy, mesh and geometry data, animation clips, and materials. Highly complex FBX files with embedded media may produce partial results; test with your specific asset corpus.

**Does the library support TypeScript 4.x?**
TypeScript 5.0+ is recommended. TypeScript 4.7+ should work in practice, but the library is tested and authored against 5.0+.

## API Reference Summary

| Class | Module | Purpose |
|---|---|---|
| `Scene` | `@aspose/3d` | Top-level scene container; `open()`, `openFromBuffer()`, `save()`, `rootNode`, `animationClips` |
| `Node` | `@aspose/3d` | Scene-graph node; `childNodes`, `entity`, `transform`, `materials`, `createChildNode()` |
| `Entity` | `@aspose/3d` | Base class for scene-attachable objects |
| `SceneObject` | `@aspose/3d` | Base class shared by `Node` and `Entity` |
| `A3DObject` | `@aspose/3d` | Root base with `name` and property bag |
| `Transform` | `@aspose/3d` | Local translation, rotation, and scale |
| `Mesh` | `@aspose/3d` | Polygon mesh; `controlPoints`, `polygonCount`, `createPolygon()`, vertex elements |
| `Geometry` | `@aspose/3d` | Base class for geometry types |
| `Camera` | `@aspose/3d` | Camera entity with field-of-view and projection settings |
| `Light` | `@aspose/3d` | Light entity (point, directional, spot) |
| `LambertMaterial` | `@aspose/3d` | Diffuse + ambient shading model |
| `PhongMaterial` | `@aspose/3d` | Phong shading with specular and emissive |
| `PbrMaterial` | `@aspose/3d` | Physically-based roughness/metallic model for glTF |
| `Vector3` | `@aspose/3d` | 3-component double-precision vector |
| `Vector4` | `@aspose/3d` | 4-component vector for homogeneous math |
| `Matrix4` | `@aspose/3d` | 4×4 transformation matrix |
| `Quaternion` | `@aspose/3d` | Rotation quaternion |
| `BoundingBox` | `@aspose/3d` | Axis-aligned bounding box |
| `FVector3` | `@aspose/3d` | Single-precision variant of `Vector3` |
| `VertexElementNormal` | `@aspose/3d` | Per-vertex or per-polygon-vertex normals |
| `VertexElementUV` | `@aspose/3d` | Texture coordinate vertex element |
| `VertexElementVertexColor` | `@aspose/3d` | Per-vertex color vertex element |
| `MappingMode` | `@aspose/3d` | Enum: `CONTROL_POINT`, `POLYGON_VERTEX`, `POLYGON`, `ALL_SAME` |
| `ReferenceMode` | `@aspose/3d` | Enum: `Direct`, `IndexToDirect` |
| `AnimationClip` | `@aspose/3d` | Named animation; contains `AnimationNode` list |
| `AnimationNode` | `@aspose/3d` | Binds clip to scene node; contains `AnimationChannel` list |
| `AnimationChannel` | `@aspose/3d` | Targets a property; holds `KeyframeSequence` |
| `KeyFrame` | `@aspose/3d` | Single time/value keyframe pair |
| `KeyframeSequence` | `@aspose/3d` | Ordered keyframe list with interpolation and extrapolation |
| `Interpolation` | `@aspose/3d` | Enum: `Linear`, `Constant`, `Cubic` |
| `Extrapolation` | `@aspose/3d` | Enum: `Constant`, `Cycle`, `Mirror` |
| `ObjLoadOptions` | `@aspose/3d/formats/obj` | OBJ import options: `enableMaterials`, `flipCoordinateSystem`, `scale`, `normalizeNormal` |
| `GltfSaveOptions` | `@aspose/3d/formats/gltf` | glTF/GLB export options: `binaryMode` |
| `GltfFormat` | `@aspose/3d/formats/gltf` | Format instance for glTF/GLB; pass to `scene.save()` |
| `StlLoadOptions` | `@aspose/3d/formats/stl` | STL import options |
| `StlSaveOptions` | `@aspose/3d/formats/stl` | STL export options: `binaryFormat` |
| `StlImporter` | `@aspose/3d/formats/stl` | Low-level STL reader |
| `StlExporter` | `@aspose/3d/formats/stl` | Low-level STL writer |
