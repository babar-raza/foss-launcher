---
page_role: howto_article
title: "API Overview — @aspose/3d for TypeScript"
description: "Complete API reference overview for @aspose/3d — classes, enumerations, format modules, and usage patterns for loading, building, and exporting 3D scenes in TypeScript and Node.js."
summary: "Complete API reference overview for @aspose/3d — classes, enumerations, format modules, and usage patterns for loading, building, and exporting 3D scenes in TypeScript and Node.js."
categories:
  - Reference
layout: "reference-single"
weight: 5
---

Package: [@aspose/3d](https://www.npmjs.com/package/@aspose/3d) (v24.12.0)
Language: TypeScript / Node.js 16+
License: MIT

`@aspose/3d` is a MIT-licensed library for reading, constructing, and exporting 3D scenes in Node.js. It ships with complete TypeScript type definitions, a single runtime dependency (`xmldom`), and supports seven major 3D file formats. All I/O is synchronous. No native addons are required.

---

## Installation

```bash
npm install @aspose/3d
```

Minimum `tsconfig.json` settings for correct sub-path resolution:

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

---

## Core Classes

### Scene

The root container for a 3D scene. All content — nodes, geometry, materials, and animations — is stored in a tree rooted at `scene.rootNode`. Use `open()` / `openFromBuffer()` to load a file and `save()` / `saveToBuffer()` to export.

| Member | Signature | Description |
|--------|-----------|-------------|
| `rootNode` | `Node` | Root of the scene graph |
| `assetInfo` | `AssetInfo` | File metadata (creator, units, coordinate system) |
| `animationClips` | `AnimationClip[]` | All animation clips in the scene |
| `open(path, opts?)` | `(string, LoadOptions?) → void` | Load a file from disk |
| `openFromBuffer(buf, opts?)` | `(Buffer, LoadOptions?) → void` | Load from in-memory buffer |
| `save(path, opts?)` | `(string, SaveOptions?) → void` | Save to disk (format inferred from extension) |
| `saveToBuffer(ext, opts?)` | `(string, SaveOptions?) → Buffer` | Save to in-memory buffer |
| `createAnimationClip(name)` | `(string) → AnimationClip` | Create and register a new animation clip |

### Node

A named tree node in the scene graph. Nodes carry an optional `Entity` (mesh, camera, light) and a `Transform` that positions the node relative to its parent.

| Member | Signature | Description |
|--------|-----------|-------------|
| `name` | `string` | Node name |
| `childNodes` | `Node[]` | Direct child nodes |
| `entity` | `Entity \| null` | Attached geometry, camera, or light |
| `transform` | `Transform` | Local translation, rotation, scale |
| `materials` | `Material[]` | Materials assigned to this node |
| `createChildNode(name)` | `(string) → Node` | Add a child node |
| `getChildNode(name)` | `(string) → Node \| null` | Find a child by name |

### Mesh

Polygon mesh — the primary geometry type. Extends `Geometry`.

| Member | Signature | Description |
|--------|-----------|-------------|
| `controlPoints` | `Vector4[]` | Vertex positions (w=1 for positions) |
| `polygonCount` | `number` | Number of polygons |
| `createPolygon(indices)` | `(number[]) → void` | Add a polygon (triangle or quad) |
| `getElement(type)` | `(VertexElementType) → VertexElement \| null` | Get a vertex element by semantic |
| `createElement(type)` | `(VertexElementType) → VertexElement` | Create a vertex element |

### Transform

Local transformation applied to a node.

| Member | Type | Description |
|--------|------|-------------|
| `translation` | `Vector3` | Local position |
| `eulerAngles` | `Vector3` | Euler rotation in degrees (XYZ order) |
| `rotation` | `Quaternion` | Rotation as a quaternion |
| `scale` | `Vector3` | Local scale |

---

## Material Classes

| Class | Description | Key Properties |
|-------|-------------|----------------|
| `LambertMaterial` | Diffuse + ambient shading | `diffuseColor`, `ambientColor`, `transparency` |
| `PhongMaterial` | Adds specular + emissive to Lambert | `specularColor`, `shininess`, `emissiveColor` |
| `PbrMaterial` | Physically-based for glTF 2.0 | `albedo`, `metallic`, `roughness`, `emissive` |

---

## Math Classes

| Class | Description |
|-------|-------------|
| `Vector3` | 3-component double-precision vector (`x`, `y`, `z`) |
| `Vector4` | 4-component vector for homogeneous math (`x`, `y`, `z`, `w`) |
| `FVector3` | Single-precision variant used in vertex data |
| `Matrix4` | 4×4 transformation matrix; `multiply`, `invert`, `decompose` |
| `Quaternion` | Rotation quaternion; `fromEulerAngle`, `toEulerAngles`, `slerp` |
| `BoundingBox` | Axis-aligned bounding box; `min`, `max`, `center`, `size`, `merge` |

---

## Animation Classes

| Class | Description |
|-------|-------------|
| `AnimationClip` | Named clip; contains `AnimationNode` list; accessed via `scene.animationClips` |
| `AnimationNode` | Binds a clip to a named scene node; contains `AnimationChannel` list |
| `AnimationChannel` | Targets a single property (e.g. translation X); holds a `KeyframeSequence` |
| `KeyframeSequence` | Ordered list of `KeyFrame` objects with `interpolation` and `extrapolation` |
| `KeyFrame` | Single time/value pair |

---

## Enumerations

| Enum | Values | Notes |
|------|--------|-------|
| `VertexElementType` | `NORMAL`, `UV`, `VERTEX_COLOR`, `BINORMAL`, `TANGENT` | Vertex element semantic |
| `MappingMode` | `CONTROL_POINT`, `POLYGON_VERTEX`, `POLYGON`, `ALL_SAME` | How data maps to geometry |
| `ReferenceMode` | `Direct`, `IndexToDirect` | Indexing strategy for vertex element data |
| `Interpolation` | `Linear`, `Constant`, `Cubic` | Keyframe interpolation |
| `Extrapolation` | `Constant`, `Cycle`, `Mirror` | Behavior outside keyframe range |

---

## Format Modules

Format-specific options classes are exported from sub-path modules. Import them separately:

```typescript
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';
import { StlLoadOptions, StlSaveOptions } from '@aspose/3d/formats/stl';
import { FbxLoadOptions, FbxSaveOptions } from '@aspose/3d/formats/fbx';
import { ColladaLoadOptions } from '@aspose/3d/formats/collada';
import { ThreeMfSaveOptions } from '@aspose/3d/formats/3mf';
```

### OBJ Module (`@aspose/3d/formats/obj`)

| Class | Key Options |
|-------|-------------|
| `ObjLoadOptions` | `enableMaterials`, `flipCoordinateSystem`, `scale`, `normalizeNormal` |

### glTF/GLB Module (`@aspose/3d/formats/gltf`)

| Class | Key Options |
|-------|-------------|
| `GltfSaveOptions` | `binaryMode` (true → .glb), `embedAssets` |
| `GltfFormat` | `GltfFormat.getInstance()` — format instance for `scene.save()` |

### STL Module (`@aspose/3d/formats/stl`)

| Class | Key Options |
|-------|-------------|
| `StlLoadOptions` | — |
| `StlSaveOptions` | `binaryMode` (false → ASCII, true → binary) |

### FBX Module (`@aspose/3d/formats/fbx`)

| Class | Key Options |
|-------|-------------|
| `FbxLoadOptions` | — |
| `FbxSaveOptions` | `exportFbxVersion` |

---

## Supported Formats

| Format | Extension | Read | Write |
|--------|-----------|:----:|:-----:|
| OBJ (Wavefront) | `.obj` | Yes | No |
| glTF 2.0 | `.gltf` | Yes | Yes |
| GLB (binary glTF) | `.glb` | Yes | Yes |
| STL | `.stl` | Yes | Yes |
| FBX | `.fbx` | Yes | Yes |
| COLLADA | `.dae` | Yes | Yes |
| 3MF | `.3mf` | Yes | Yes |

---

## Quick Reference Example

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

// Load OBJ with materials
const scene = new Scene();
const loadOpts = new ObjLoadOptions();
loadOpts.enableMaterials = true;
scene.open('input.obj', loadOpts);

// Inspect root nodes
for (const node of scene.rootNode.childNodes) {
    console.log(`Node: ${node.name}, entity: ${node.entity?.constructor.name}`);
}

// Export as compact GLB
const saveOpts = new GltfSaveOptions();
saveOpts.embedAssets = true;
scene.save('output.glb', saveOpts);
```

---

## See Also

- [Class Scene](scene/)
- [Class Node](node/)
- [Class Mesh](mesh/)
- [Features and Functionalities](/docs.aspose.org/3d/typescript/developer-guide/features/)
- [Format Support](/docs.aspose.org/3d/typescript/developer-guide/format-support/)
