---
page_role: howto_article
title: "Working with the Scene Graph"
description: "Learn how to build, traverse, and transform a 3D scene graph in TypeScript using @aspose/3d — from creating nodes and meshes to saving the result as glTF or GLB."
type: docs
weight: 20
---

All 3D content in Aspose.3D FOSS for TypeScript lives inside a `Scene` object organized as a tree of `Node` objects. Understanding this hierarchy is the foundation for building, loading, and processing any 3D file.

## Installation

Install the package from npm before running any of the code in this guide:

```bash
npm install @aspose/3d
```

Ensure your `tsconfig.json` includes `"module": "commonjs"` and `"moduleResolution": "node"` for correct sub-path import resolution.

## Scene Graph Concepts

The scene graph has three tiers:

| Tier | Class | Role |
|---|---|---|
| Scene | `Scene` | Top-level container. Holds `rootNode`, `animationClips`, and `assetInfo`. |
| Node | `Node` | Named tree node. Can have child nodes, an entity, a transform, and materials. |
| Entity | `Mesh`, `Camera`, `Light`, … | Content attached to a node. A node carries at most one entity. |

The inheritance chain for the main building blocks is:

```
A3DObject
  └─ SceneObject
       ├─ Node          (tree structure)
       └─ Entity
            └─ Geometry
                 └─ Mesh   (polygon geometry)
```

`scene.rootNode` is created automatically. You do not create it manually; you create child nodes under it.

## Step 1: Create a Scene

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
console.log(scene.rootNode.name); // 'RootNode'
```

A new `Scene` starts with an empty root node and no animation clips. You build content by attaching child nodes.

## Step 2: Add Child Nodes

Use `createChildNode()` to grow the tree. The method returns the new `Node`, so you can chain further calls from any level:

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
const parent = scene.rootNode.createChildNode('parent');
const child = parent.createChildNode('child');

console.log(scene.rootNode.childNodes.length); // 1 (parent)
console.log(parent.childNodes.length);         // 1 (child)
```

Node names are arbitrary strings. Names do not need to be unique, but using meaningful names makes traversal code easier to debug.

## Step 3: Create a Mesh and Set Vertices

`Mesh` is the primary geometry class. Add vertex positions by pushing `Vector4` values into `mesh.controlPoints`, then call `createPolygon()` to define faces by vertex index:

```typescript
import { Scene } from '@aspose/3d';
import { Mesh } from '@aspose/3d/entities';
import { Vector4 } from '@aspose/3d/utilities';

const scene = new Scene();
const child = scene.rootNode.createChildNode('parent').createChildNode('child');

const mesh = new Mesh('cube');
mesh.controlPoints.push(new Vector4(0, 0, 0, 1));
mesh.controlPoints.push(new Vector4(1, 0, 0, 1));
mesh.controlPoints.push(new Vector4(1, 1, 0, 1));
mesh.controlPoints.push(new Vector4(0, 1, 0, 1));
mesh.createPolygon(0, 1, 2, 3); // quad face using all four vertices

child.entity = mesh;

console.log(mesh.controlPoints.length); // 4
console.log(mesh.polygonCount);         // 1
```

`Vector4` uses homogeneous coordinates: the `w` component is `1` for positions and `0` for direction vectors.

## Step 4: Set Node Transforms

Each node has a `transform` property with `translation`, `rotation`, and `scale`. Set `translation` to move the node relative to its parent:

```typescript
import { Scene } from '@aspose/3d';
import { Mesh } from '@aspose/3d/entities';
import { Vector4, Vector3 } from '@aspose/3d/utilities';

const scene = new Scene();
const parent = scene.rootNode.createChildNode('parent');
const child = parent.createChildNode('child');

const mesh = new Mesh('cube');
mesh.controlPoints.push(new Vector4(0, 0, 0, 1));
mesh.controlPoints.push(new Vector4(1, 0, 0, 1));
mesh.controlPoints.push(new Vector4(1, 1, 0, 1));
mesh.controlPoints.push(new Vector4(0, 1, 0, 1));
mesh.createPolygon(0, 1, 2, 3);
child.entity = mesh;

child.transform.translation = new Vector3(2.0, 0.0, 0.0);
```

`globalTransform` provides the world-space transformation matrix (read-only), computed by concatenating all ancestor transforms.

## Step 5: Traverse the Tree

Write a recursive function to visit every node. Check `node.entity` and `node.childNodes` at each level:

```typescript
function traverse(node: any, depth = 0): void {
    const indent = '  '.repeat(depth);
    const entityType = node.entity ? node.entity.constructor.name : 'none';
    console.log(`${indent}${node.name} [${entityType}]`);
    for (const child of node.childNodes) {
        traverse(child, depth + 1);
    }
}

traverse(scene.rootNode);
```

For the hierarchy created above, the output will be:

```
RootNode [none]
  parent [none]
    child [Mesh]
```

Always guard entity access with a null check before casting to a specific type. Not every node carries an entity.

## Step 6: Save to glTF or GLB

Use `GltfSaveOptions` to control the output format. Set `binaryMode = true` to produce a single self-contained `.glb` file; leave it `false` for the JSON `.gltf` + `.bin` sidecar pair:

```typescript
import { Scene } from '@aspose/3d';
import { Mesh } from '@aspose/3d/entities';
import { Vector4, Vector3 } from '@aspose/3d/utilities';
import { GltfSaveOptions, GltfFormat } from '@aspose/3d/formats/gltf';

const scene = new Scene();
const parent = scene.rootNode.createChildNode('parent');
const child = parent.createChildNode('child');

const mesh = new Mesh('cube');
mesh.controlPoints.push(new Vector4(0, 0, 0, 1));
mesh.controlPoints.push(new Vector4(1, 0, 0, 1));
mesh.controlPoints.push(new Vector4(1, 1, 0, 1));
mesh.controlPoints.push(new Vector4(0, 1, 0, 1));
mesh.createPolygon(0, 1, 2, 3);
child.entity = mesh;

child.transform.translation = new Vector3(2.0, 0.0, 0.0);

const saveOpts = new GltfSaveOptions();
saveOpts.binaryMode = true;                             // write a single .glb file
scene.save('scene.glb', GltfFormat.getInstance(), saveOpts);

console.log('Scene saved to scene.glb');
```

Pass `GltfFormat.getInstance()` as the format argument so the library uses the correct encoder regardless of the file extension.

## Tips and Best Practices

- **Use `createChildNode()` instead of constructing `Node` directly** — `createChildNode()` automatically wires the parent-child relationship and registers the node in the tree.
- **Check `node.entity` before accessing entity properties** — many nodes (group nodes, bones, locators) carry no entity. Always guard with a null check or `instanceof` test.
- **Set `translation` on child nodes, not on mesh vertices** — modifying `transform.translation` is non-destructive and composable with parent transforms.
- **Prefer `binaryMode = true` for GLB** — a single `.glb` file is easier to distribute, load in browsers, and import into game engines than the split `.gltf` + `.bin` format.
- **Traverse via `for...of` over `childNodes`** — avoid numeric indexing; use the iterable directly for forward compatibility.

## Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| `child.entity = mesh` has no effect on export | Entity assigned to wrong node level | Assign `entity` to the leaf node, not to a group node |
| `node.entity` is always `null` | Only checking `rootNode` itself | Recurse into `node.childNodes`; `rootNode` typically has no entity |
| Transform not reflected in GLB viewer | `globalTransform` not updated | `globalTransform` is computed on save; set `transform.translation` before calling `scene.save()` |
| GLB produces a separate `.bin` sidecar | `binaryMode` defaults to `false` | Set `saveOpts.binaryMode = true` |

## See Also

- [Features and Functionalities](./features.md) — full API reference for all feature areas.
- [Format Support](./format-support.md) — supported 3D formats, read/write capability, and format options.
- [How to Build a 3D Mesh Programmatically](../../developer-guide/scene-graph.md)
