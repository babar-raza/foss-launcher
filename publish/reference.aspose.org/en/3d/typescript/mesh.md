---
page_role: howto_article
linkTitle: "Class Mesh"
title: "Class Mesh"
description: "Mesh is the primary polygon geometry entity in @aspose/3d. It stores vertex positions as control points, defines polygon faces by vertex index lists, and supports multiple vertex element data layers such as normals and UV coordinates."
summary: "Mesh is the primary polygon geometry entity in @aspose/3d. It stores vertex positions as control points, defines polygon faces by vertex index lists, and supports multiple vertex element data layers such as normals and UV coordinates."
categories:
  - Class
layout: "reference-single"
---

Package: [@aspose/3d](https://www.npmjs.com/package/@aspose/3d) (v24.12.0)

`Mesh` is also available via the sub-path import `@aspose/3d/entities`.

Mesh is the primary polygon geometry entity in `@aspose/3d`. It stores vertex positions as control points, defines polygon faces by vertex index lists, and supports multiple vertex element data layers such as normals and UV coordinates.

```typescript
export class Mesh extends Geometry
```

#### Inheritance

A3DObject ←
SceneObject ←
Entity ←
Geometry ←
Mesh

## Examples

Build a single triangle mesh, attach it to the scene, and save to GLB.

```typescript
import { Scene, FileFormat } from '@aspose/3d';
import { Mesh } from '@aspose/3d/entities';

// Create the mesh and define three control points (vertices)
const mesh = new Mesh();
mesh.controlPoints.push(
  { x: 0, y: 1, z: 0, w: 1 },   // apex
  { x: -1, y: 0, z: 0, w: 1 },  // bottom-left
  { x: 1, y: 0, z: 0, w: 1 },   // bottom-right
);

// Define one triangular polygon using vertex indices
mesh.createPolygon(0, 1, 2);

// Attach the mesh to the scene and save
const scene = new Scene();
scene.rootNode.createChildNode('triangle', mesh);
scene.save('triangle.glb', FileFormat.GLTF2_BINARY);
console.log(`Polygon count: ${mesh.polygonCount}`); // 1
```

## Properties

| Property | Type | Description |
|---|---|---|
| `controlPoints` | `Vector4[]` | The vertex positions of the mesh. Each point uses homogeneous coordinates (`x`, `y`, `z`, `w`). Add points by pushing to this array before defining polygons. |
| `polygonCount` | `number` | Read-only. The number of polygons (faces) currently defined on the mesh. |
| `polygons` | `number[][]` | Read-only. The polygon index table. Each entry is an array of control point indices that define one face. |
| `edges` | `number[]` | The edge list, used for hard-edge marking and crease weighting. |
| `vertexElements` | `VertexElement[]` | The collection of vertex element layers (normals, UVs, vertex colors, etc.) attached to this mesh. |
| `visible` | `boolean` | Whether the mesh is rendered. Default is `true`. |
| `castShadows` | `boolean` | Whether the mesh casts shadows in supported renderers. Default is `true`. |
| `receiveShadows` | `boolean` | Whether the mesh receives shadows from other objects. Default is `true`. |

## Methods

### createPolygon(...indices)

Defines a new polygon face using the provided control point indices. Indices must reference valid positions in `controlPoints`.

```typescript
createPolygon(...indices: number[]): void
```

#### Parameters

`...indices` `number[]`

Three or more zero-based indices into the `controlPoints` array, in counter-clockwise winding order.

#### Returns

`void`

#### Examples

```typescript
import { Mesh } from '@aspose/3d/entities';

const mesh = new Mesh();
mesh.controlPoints.push(
  { x: 0, y: 0, z: 0, w: 1 },
  { x: 1, y: 0, z: 0, w: 1 },
  { x: 1, y: 1, z: 0, w: 1 },
  { x: 0, y: 1, z: 0, w: 1 },
);
// Define a quad as two triangles, or a single quad polygon:
mesh.createPolygon(0, 1, 2, 3);
console.log(`Polygons: ${mesh.polygonCount}`); // 1
```

---

### triangulate()

Converts all non-triangular polygons in this mesh into triangles. Returns the triangulated mesh (may be the same instance or a new one).

```typescript
triangulate(): Mesh
```

#### Returns

`Mesh`

The triangulated mesh.

#### Examples

```typescript
import { Mesh } from '@aspose/3d/entities';

const mesh = new Mesh();
mesh.controlPoints.push(
  { x: 0, y: 0, z: 0, w: 1 },
  { x: 1, y: 0, z: 0, w: 1 },
  { x: 1, y: 1, z: 0, w: 1 },
  { x: 0, y: 1, z: 0, w: 1 },
);
mesh.createPolygon(0, 1, 2, 3); // quad
const triangulated = mesh.triangulate();
console.log(`Polygons after triangulation: ${triangulated.polygonCount}`); // 2
```

---

### toMesh()

Returns the mesh as a `Mesh` instance. For `Mesh` objects this is an identity operation; the method is more meaningful on primitive geometry types that inherit from `Geometry`.

```typescript
toMesh(): Mesh
```

#### Returns

`Mesh`

This mesh instance.

---

### static union(a, b)

Performs a Boolean union of two meshes. The result contains the combined volume of both inputs.

```typescript
static union(a: Mesh, b: Mesh): Mesh
```

#### Parameters

`a` `Mesh`

The first mesh operand.

`b` `Mesh`

The second mesh operand.

#### Returns

`Mesh`

A new mesh representing the union of `a` and `b`.

#### Examples

```typescript
import { Mesh } from '@aspose/3d/entities';

// Assumes meshA and meshB are already populated Mesh instances
const combined = Mesh.union(meshA, meshB);
console.log(`Union polygon count: ${combined.polygonCount}`);
```

---

### static difference(a, b)

Performs a Boolean difference, subtracting the volume of mesh `b` from mesh `a`.

```typescript
static difference(a: Mesh, b: Mesh): Mesh
```

#### Parameters

`a` `Mesh`

The base mesh.

`b` `Mesh`

The mesh to subtract from `a`.

#### Returns

`Mesh`

A new mesh representing `a` minus `b`.

#### Examples

```typescript
import { Mesh } from '@aspose/3d/entities';

const result = Mesh.difference(meshA, meshB);
console.log(`Difference polygon count: ${result.polygonCount}`);
```

---

### static intersect(a, b)

Performs a Boolean intersection of two meshes. The result contains only the overlapping volume.

```typescript
static intersect(a: Mesh, b: Mesh): Mesh
```

#### Parameters

`a` `Mesh`

The first mesh operand.

`b` `Mesh`

The second mesh operand.

#### Returns

`Mesh`

A new mesh representing the intersection of `a` and `b`.

#### Examples

```typescript
import { Mesh } from '@aspose/3d/entities';

const overlap = Mesh.intersect(meshA, meshB);
console.log(`Intersection polygon count: ${overlap.polygonCount}`);
```

---

### createElement(type, mapping?, reference?)

Creates a new `VertexElement` data layer on this mesh for custom per-vertex attributes.

```typescript
createElement(
  type: VertexElementType,
  mapping?: MappingMode,
  reference?: ReferenceMode
): VertexElement
```

#### Parameters

`type` `VertexElementType`

The kind of vertex attribute to create (for example, `VertexElementType.Normal`).

`mapping` `MappingMode` (optional)

How the element data is mapped to the mesh topology. Defaults to `MappingMode.ControlPoint`.

`reference` `ReferenceMode` (optional)

How the element indices reference the data array. Defaults to `ReferenceMode.Direct`.

#### Returns

`VertexElement`

The newly created vertex element layer.

---

### createElementUV(mapping, mappingMode?, referenceMode?)

Creates a UV coordinate layer on this mesh.

```typescript
createElementUV(
  mapping: TextureMapping,
  mappingMode?: MappingMode,
  referenceMode?: ReferenceMode
): VertexElementUV
```

#### Parameters

`mapping` `TextureMapping`

The UV channel to create (for example, `TextureMapping.Diffuse`).

`mappingMode` `MappingMode` (optional)

How UV coordinates are mapped to vertices.

`referenceMode` `ReferenceMode` (optional)

How UV index data references the UV array.

#### Returns

`VertexElementUV`

The newly created UV element layer.

#### Examples

```typescript
import { Mesh } from '@aspose/3d/entities';
import { TextureMapping } from '@aspose/3d';

const mesh = new Mesh();
// ... define control points and polygons ...
const uvLayer = mesh.createElementUV(TextureMapping.Diffuse);
console.log(`UV element created: ${uvLayer !== undefined}`);
```
