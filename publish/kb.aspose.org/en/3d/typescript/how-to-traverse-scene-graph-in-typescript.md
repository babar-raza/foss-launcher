---
page_role: howto_article
title: "How to Traverse a 3D Scene Graph in TypeScript"
description: "Learn how to recursively walk a 3D scene tree in TypeScript using @aspose/3d, access entity types on each node, filter Mesh nodes, and collect vertex counts."
date: 2026-01-20
weight: 40
draft: false
type: "topic"
keywords: [
    "traverse scene graph typescript",
    "aspose 3d node traversal",
    "scene tree walk nodejs",
    "filter mesh nodes typescript",
    "vertex count aspose 3d",
    "aspose 3d foss typescript",
    "scene rootNode childNodes",
    "recursive node visit typescript"
]
step1: "Install @aspose/3d and import the required classes"
step2: "Load a 3D scene from a file"
step3: "Write a recursive traversal function"
step4: "Access the entity type on each node"
step5: "Filter nodes by entity type to find Mesh nodes"
step6: "Collect all meshes and print vertex and polygon counts"
---

The scene graph in Aspose.3D FOSS for TypeScript is a tree of `Node` objects rooted at `scene.rootNode`. Traversal is recursive: each node exposes a `childNodes` iterable and an optional `entity` property. This guide shows how to walk the entire tree, identify entity types, and collect mesh statistics.

## Prerequisites

- Node.js 16 or later
- TypeScript 5.0 or later
- `@aspose/3d` installed

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install and Import

Install the package:

```bash
npm install @aspose/3d
```

Import the classes used in this guide:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { Mesh } from '@aspose/3d/entities';
```

`Scene` and `Mesh` are the core classes. `ObjLoadOptions` is used in the load example; substitute the matching options class for other formats.

---

### Step 2: Load a Scene from a File

Create a `Scene` and call `scene.open()` with a file path. Format detection is automatic from binary magic numbers, so you do not need to specify the format for GLB, STL, or 3MF files:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

console.log(`Root node: "${scene.rootNode.name}"`);
console.log(`Top-level children: ${scene.rootNode.childNodes.length}`);
```

You can also load from a `Buffer` in memory using `scene.openFromBuffer(buffer, options)` — useful in serverless pipelines where disk I/O is not available.

---

### Step 3: Write a Recursive Traversal Function

Recursion over `childNodes` is the standard pattern. The function visits each node depth-first:

```typescript
function traverse(node: any, depth = 0): void {
    const indent = '  '.repeat(depth);
    const entityType = node.entity ? node.entity.constructor.name : '-';
    console.log(`${indent}[${entityType}] ${node.name}`);
    for (const child of node.childNodes) {
        traverse(child, depth + 1);
    }
}

traverse(scene.rootNode);
```

For a scene with one mesh named `Cube`, the output will look like:

```
[-] RootNode
  [Mesh] Cube
```

`node.entity` is `null` for group nodes, bones, and locators. The `constructor.name` check works for any entity type: `Mesh`, `Camera`, `Light`, etc.

---

### Step 4: Access the Entity Type on Each Node

To take action based on entity type, use an `instanceof` check after the null guard:

```typescript
import { Mesh } from '@aspose/3d/entities';

function visitWithTypeCheck(node: any, depth = 0): void {
    const indent = '  '.repeat(depth);
    if (node.entity instanceof Mesh) {
        const mesh = node.entity as Mesh;
        console.log(`${indent}MESH "${node.name}": ${mesh.controlPoints.length} vertices`);
    } else if (node.entity) {
        console.log(`${indent}${node.entity.constructor.name} "${node.name}"`);
    } else {
        console.log(`${indent}GROUP "${node.name}"`);
    }
    for (const child of node.childNodes) {
        visitWithTypeCheck(child, depth + 1);
    }
}

visitWithTypeCheck(scene.rootNode);
```

`instanceof Mesh` is the safest way to confirm the entity is a polygon mesh before accessing `controlPoints`, `polygonCount`, or vertex elements.

---

### Step 5: Filter Nodes by Entity Type

To collect only mesh-bearing nodes without printing the full tree, use a recursive accumulator:

```typescript
import { Mesh } from '@aspose/3d/entities';

function collectMeshes(
    node: any,
    results: Array<{ name: string; mesh: Mesh }> = []
): Array<{ name: string; mesh: Mesh }> {
    if (node.entity instanceof Mesh) {
        results.push({ name: node.name, mesh: node.entity as Mesh });
    }
    for (const child of node.childNodes) {
        collectMeshes(child, results);
    }
    return results;
}

const meshNodes = collectMeshes(scene.rootNode);
console.log(`Found ${meshNodes.length} mesh node(s)`);
```

The function accepts an optional `results` array so callers can pre-populate it for merging results across multiple subtrees.

---

### Step 6: Collect All Meshes and Print Vertex Counts

Extend the collector to print per-mesh statistics:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { Mesh } from '@aspose/3d/entities';

function collectMeshes(node: any, results: Array<{name: string, mesh: Mesh}> = []) {
    if (node.entity instanceof Mesh) {
        results.push({ name: node.name, mesh: node.entity as Mesh });
    }
    for (const child of node.childNodes) {
        collectMeshes(child, results);
    }
    return results;
}

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

const meshes = collectMeshes(scene.rootNode);
for (const { name, mesh } of meshes) {
    console.log(`${name}: ${mesh.controlPoints.length} vertices, ${mesh.polygonCount} polygons`);
}
```

Example output for a two-mesh scene:

```
Cube: 8 vertices, 6 polygons
Sphere: 482 vertices, 480 polygons
```

{{% /steps %}}

## Tips and Best Practices

- **Always null-check `node.entity`** before accessing entity-specific properties. Many nodes are pure group nodes that carry no entity.
- **Use `instanceof` over `constructor.name`** for type checks in logic paths. `instanceof` is refactor-safe; string comparison on `constructor.name` breaks with minification.
- **Traverse via `for...of` over `childNodes`** — the iterable handles all array sizes safely. Avoid numeric indexing for forward compatibility.
- **Avoid mutating the tree during traversal** — do not add or remove nodes inside the recursive call. Collect results first, then modify.
- **Pass a results array as a parameter** — this avoids allocating a new array on every recursive call and makes it easy to merge subtree results.

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `childNodes` has zero length on `rootNode` | Model not loaded | Ensure `scene.open()` completed without error before traversing |
| `node.entity instanceof Mesh` never true | Wrong `Mesh` import path | Import `Mesh` from `@aspose/3d/entities`, not from `@aspose/3d` root |
| Traversal misses nested meshes | Not recursing into all children | Ensure the recursive call covers every element in `node.childNodes` |
| `mesh.controlPoints.length` is 0 | Mesh loaded but contains no geometry | Check OBJ source for empty groups; use `mesh.polygonCount` as a secondary check |
| Stack overflow on deep hierarchies | Very deep scene tree (hundreds of levels) | Replace recursion with an explicit stack using `Array.push` / `Array.pop` |

## Frequently Asked Questions

**Does `scene.rootNode` itself carry an entity?**
No. The root node is a container created automatically by the library. It has no entity. Your geometry and other scene objects live on child nodes one or more levels below `rootNode`.

**What is the difference between `node.entity` and `node.entities`?**
`node.entity` holds the single primary entity (the common case). Some older FBX and COLLADA files may produce nodes with multiple attached entities; in that case `node.entities` (plural) provides the full list.

**Can I traverse in breadth-first order instead of depth-first?**
Yes. Use a queue instead of a recursive call: push `scene.rootNode` into an array, then shift and process nodes while pushing each node's `childNodes` into the queue tail.

**Is `scene.open()` synchronous?**
Yes. `scene.open()` and `scene.openFromBuffer()` both block the calling thread until the file is fully parsed. Wrap them in a worker thread if you need to keep the event loop responsive.

**How do I get world-space positions from a node?**
Read `node.globalTransform` — it returns a read-only `GlobalTransform` with the world-space matrix, composed from all ancestor transforms. For explicit matrix math, call `node.evaluateGlobalTransform(false)`.

**What entity types are possible besides `Mesh`?**
`Camera`, `Light`, and custom skeleton/bone entities. Check `node.entity.constructor.name` or use `instanceof` with the specific class imported from `@aspose/3d`.

## See Also

- [How to Load 3D Models in TypeScript](/kb.aspose.org/3d/typescript/how-to-load-3d-models-in-typescript/)
- [How to Build a 3D Mesh Programmatically in TypeScript](/kb.aspose.org/3d/typescript/how-to-build-mesh-programmatically-in-typescript/)
- [Developer Guide: Scene Graph](/docs.aspose.org/3d/typescript/developer-guide/scene-graph/)
- [npm: @aspose/3d](https://www.npmjs.com/package/@aspose/3d)
