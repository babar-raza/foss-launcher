---
page_role: howto_article
title: "How to Build a 3D Mesh Programmatically in TypeScript"
description: "Step-by-step guide to constructing a polygon mesh with vertices, faces, and normals from scratch in TypeScript using the @aspose/3d FOSS package, then saving the result as glTF."
date: 2026-01-20
weight: 30
draft: false
type: "topic"
keywords: [
    "build mesh typescript",
    "create 3d mesh nodejs",
    "aspose 3d mesh programmatic",
    "control points polygon typescript",
    "vertex normals aspose 3d",
    "mesh to gltf typescript",
    "aspose 3d foss typescript",
    "VertexElementNormal typescript",
    "createPolygon aspose 3d"
]
step1: "Install @aspose/3d via npm"
step2: "Create a Scene and Node"
step3: "Create a Mesh object"
step4: "Add control points (vertices)"
step5: "Create polygon faces"
step6: "Add vertex normals"
step7: "Attach the mesh to the node and save to glTF"
---

Aspose.3D FOSS for TypeScript lets you build 3D geometry entirely in code without loading any file. You define vertex positions as control points, specify polygon faces by index, and attach optional vertex elements such as normals, UVs, or vertex colors. The result can be saved to any writable format — glTF, GLB, STL, FBX, or COLLADA.

## Prerequisites

- Node.js 16 or later
- TypeScript 5.0 or later
- `@aspose/3d` installed (see Step 1)

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install @aspose/3d

```bash
npm install @aspose/3d
```

No native addons or system libraries are required. The package includes TypeScript type definitions.

Minimum `tsconfig.json`:

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

### Step 2: Create a Scene and Node

A `Scene` is the top-level container. All geometry must be attached to a `Node` inside the scene tree:

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
const node = scene.rootNode.createChildNode('triangle');
```

`createChildNode(name)` creates a named node and wires it as a child of the current node. The returned `Node` object is where you will attach the mesh in Step 7.

---

### Step 3: Create a Mesh Object

`Mesh` holds vertex positions and polygon definitions. Construct one with an optional name:

```typescript
import { Mesh } from '@aspose/3d/entities';

const mesh = new Mesh('triangle');
```

The mesh starts empty — no vertices and no faces. You add them in the next steps.

---

### Step 4: Add Control Points (Vertices)

Control points are the vertex positions in local space. Push `Vector4` values into `mesh.controlPoints`. The fourth component (`w`) is `1` for positions:

```typescript
import { Vector4 } from '@aspose/3d/utilities';

mesh.controlPoints.push(new Vector4(0.0, 0.0, 0.0, 1.0)); // index 0
mesh.controlPoints.push(new Vector4(1.0, 0.0, 0.0, 1.0)); // index 1
mesh.controlPoints.push(new Vector4(0.5, 1.0, 0.0, 1.0)); // index 2
```

You reference these positions by their zero-based index when defining polygon faces.

---

### Step 5: Create Polygon Faces

`createPolygon()` defines a face by listing the vertex indices in order. Three indices make a triangle:

```typescript
mesh.createPolygon(0, 1, 2);
```

You can also define quads (four indices) or arbitrary polygons for formats that support them. For glTF, the library will automatically triangulate quads and n-gons on export.

---

### Step 6: Add Vertex Normals

Normals improve rendering quality. Use `mesh.createElement()` to create a `VertexElementNormal` and fill its `data` array with one normal per control point:

```typescript
import { VertexElementNormal } from '@aspose/3d/entities';
import { VertexElementType, MappingMode, ReferenceMode } from '@aspose/3d/entities';

const normals = mesh.createElement(
    VertexElementType.Normal,
    MappingMode.ControlPoint,
    ReferenceMode.Direct
) as VertexElementNormal;

normals.data.push(new Vector4(0, 0, 1, 0)); // normal for vertex 0 (pointing +Z)
normals.data.push(new Vector4(0, 0, 1, 0)); // normal for vertex 1
normals.data.push(new Vector4(0, 0, 1, 0)); // normal for vertex 2
```

`MappingMode.ControlPoint` means one normal per vertex. `ReferenceMode.Direct` means the `data` array is indexed directly by the polygon vertex index.

---

### Step 7: Attach the Mesh and Save to glTF

Assign the mesh to the node via `node.entity`, then save the scene:

```typescript
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

node.entity = mesh;

const saveOpts = new GltfSaveOptions();
scene.save('triangle.gltf', GltfFormat.getInstance(), saveOpts);
console.log('Triangle mesh saved to triangle.gltf');
```

To produce a single self-contained `.glb` file instead, set `saveOpts.binaryMode = true` and change the output file extension to `.glb`.

{{% /steps %}}

## Complete Example

The following is the full script combining all steps above:

```typescript
import { Scene } from '@aspose/3d';
import { Mesh, VertexElementNormal } from '@aspose/3d/entities';
import { VertexElementType, MappingMode, ReferenceMode } from '@aspose/3d/entities';
import { Vector4 } from '@aspose/3d/utilities';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
const node = scene.rootNode.createChildNode('triangle');

const mesh = new Mesh('triangle');

mesh.controlPoints.push(new Vector4(0.0, 0.0, 0.0, 1.0));
mesh.controlPoints.push(new Vector4(1.0, 0.0, 0.0, 1.0));
mesh.controlPoints.push(new Vector4(0.5, 1.0, 0.0, 1.0));

mesh.createPolygon(0, 1, 2);

const normals = mesh.createElement(
    VertexElementType.Normal,
    MappingMode.ControlPoint,
    ReferenceMode.Direct
) as VertexElementNormal;
normals.data.push(new Vector4(0, 0, 1, 0));
normals.data.push(new Vector4(0, 0, 1, 0));
normals.data.push(new Vector4(0, 0, 1, 0));

node.entity = mesh;

const saveOpts = new GltfSaveOptions();
scene.save('triangle.gltf', GltfFormat.getInstance(), saveOpts);
console.log('Triangle mesh saved to triangle.gltf');
```

Run with `ts-node`:

```bash
npx ts-node triangle.ts
```

## Common Issues

| Issue | Cause | Fix |
|---|---|---|
| `mesh.controlPoints.length` is 0 after push | Mesh not referenced by any node | Push before assigning `node.entity`; order does not matter, but verify the reference |
| Export produces empty geometry | `node.entity` not assigned | Ensure `node.entity = mesh` before calling `scene.save()` |
| Normal count mismatch | `data` array shorter than `controlPoints` | Add one normal entry per control point when using `MappingMode.ControlPoint` |
| glTF viewer shows black mesh | Normals pointing inward | Reverse winding order in `createPolygon` (e.g., `0, 2, 1`) or negate normal vectors |
| TypeScript: 'normals.data' property not found | Wrong import path | Import `VertexElementNormal` from `@aspose/3d/entities`, not from `@aspose/3d` root |

## Frequently Asked Questions

**Can I create quads instead of triangles?**
Yes. Pass four indices to `createPolygon(0, 1, 2, 3)`. The library triangulates quads during export to formats that require triangles (glTF, STL).

**What is the difference between `MappingMode.ControlPoint` and `MappingMode.ByPolygonVertex`?**
`ControlPoint` stores one value per unique vertex. `ByPolygonVertex` stores one value per polygon-vertex pair, which allows different normals at the same vertex when it belongs to multiple polygons (hard edges).

**Do I need to triangulate the mesh before saving to STL?**
No. The library handles triangulation automatically when exporting to formats that require triangles. You can define quads and n-gons in the mesh and save to STL directly.

**How do I add UV coordinates?**
Use `mesh.createElementUV(TextureMapping.Diffuse, MappingMode.ControlPoint, ReferenceMode.Direct)` to create a `VertexElementUV`, then push `Vector4` values into its `data` array, one per control point.

**Can I build multiple meshes in one scene?**
Yes. Create multiple nodes under `scene.rootNode` and assign a separate `Mesh` to each node's `entity` property.

## See Also

- [How to Traverse a 3D Scene Graph in TypeScript](./how-to-traverse-scene-graph-in-typescript.md)
- [How to Export 3D Scenes to glTF/GLB in TypeScript](./how-to-export-gltf-in-typescript.md)
- [Developer Guide: Scene Graph](../../docs.aspose.net/3d/typescript/developer-guide/scene-graph/)
- [npm: @aspose/3d](https://www.npmjs.com/package/@aspose/3d)
