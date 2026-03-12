---
page_role: howto_article
linkTitle: "Class Node"
title: "Class Node"
description: "Node represents a named element in the scene graph hierarchy. Each node has a local transform, can hold child nodes, and carries zero or more Entity objects such as meshes, cameras, or lights."
summary: "Node represents a named element in the scene graph hierarchy. Each node has a local transform, can hold child nodes, and carries zero or more Entity objects such as meshes, cameras, or lights."
categories:
  - Class
layout: "reference-single"
---

Package: [@aspose/3d](https://www.npmjs.com/package/@aspose/3d) (v24.12.0)

Node represents a named element in the scene graph hierarchy. Each node has a local transform, can hold child nodes, and carries zero or more `Entity` objects such as meshes, cameras, or lights.

```typescript
export class Node extends SceneObject
```

#### Inheritance

A3DObject ←
SceneObject ←
Node

## Examples

Create a parent node, attach two child nodes to it, and traverse the full hierarchy by name.

```typescript
import { Scene, Node } from '@aspose/3d';

const scene = new Scene();
const root = scene.rootNode;

const vehicle = root.createChildNode('vehicle');
const body = vehicle.createChildNode('body');
const wheel = vehicle.createChildNode('wheel_front_left');

function traverse(node: Node, depth = 0): void {
  console.log(' '.repeat(depth * 2) + node.name);
  for (const child of node.childNodes) {
    traverse(child, depth + 1);
  }
}

traverse(root);
// Output:
//   vehicle
//     body
//     wheel_front_left
```

## Properties

| Property | Type | Description |
|---|---|---|
| `name` | `string` | The name of this node. Used to identify the node within the scene graph. |
| `parentNode` | `Node \| null` | The parent node in the hierarchy. `null` for the root node. |
| `childNodes` | `Node[]` | An array of direct child nodes attached to this node. |
| `entities` | `Entity[]` | The list of entities (meshes, cameras, lights, etc.) attached to this node. |
| `materials` | `Material[]` | The list of materials associated with this node. |
| `transform` | `Transform` | The local transform of this node, with `translation: Vector3`, `rotation: Quaternion`, and `scale: Vector3` components. |
| `globalTransform` | `GlobalTransform` | Read-only. The world-space transform, computed by multiplying all ancestor transforms up to the root. |
| `visible` | `boolean` | Whether this node and its subtree are rendered. Default is `true`. |
| `excluded` | `boolean` | When `true`, the node and its subtree are excluded from export. Default is `false`. |
| `entity` | `Entity \| undefined` | Convenience getter and setter for the first entity in the `entities` array. Returns `undefined` if no entities are attached. |

## Methods

### addChildNode(node)

Appends an existing `Node` instance as a direct child of this node.

```typescript
addChildNode(node: Node): void
```

#### Parameters

`node` `Node`

The node to attach. The node is reparented from its current parent to this node.

#### Returns

`void`

#### Examples

```typescript
import { Scene, Node } from '@aspose/3d';

const scene = new Scene();
const parent = scene.rootNode.createChildNode('parent');
const child = new Node('child');
parent.addChildNode(child);
console.log(`Children of parent: ${parent.childNodes.length}`); // 1
```

---

### createChildNode(name?, entity?, material?)

Creates a new `Node`, optionally with a name, an entity, and a material, and appends it as a child of this node.

```typescript
createChildNode(name?: string, entity?: Entity, material?: Material): Node
```

#### Parameters

`name` `string` (optional)

The name for the new child node.

`entity` `Entity` (optional)

An entity to attach to the new node, for example a `Mesh` instance.

`material` `Material` (optional)

A material to associate with the new node.

#### Returns

`Node`

The newly created child node.

#### Examples

```typescript
import { Scene } from '@aspose/3d';
import { Mesh } from '@aspose/3d/entities';

const scene = new Scene();
const mesh = new Mesh();
// ... populate mesh ...
const meshNode = scene.rootNode.createChildNode('geometry', mesh);
console.log(`Node name: ${meshNode.name}`);
console.log(`Entities attached: ${meshNode.entities.length}`);
```

---

### evaluateGlobalTransform(withGeometricTransform)

Computes and returns the world-space transformation matrix for this node. Pass `true` to include the geometric transform offset stored on the node (used by some FBX exporters).

```typescript
evaluateGlobalTransform(withGeometricTransform: boolean): Matrix4
```

#### Parameters

`withGeometricTransform` `boolean`

When `true`, includes the geometric transform in the result.

#### Returns

`Matrix4`

The 4×4 world-space transformation matrix.

#### Examples

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('model.fbx');
const node = scene.rootNode.childNodes[0];
const matrix = node.evaluateGlobalTransform(false);
console.log('World transform matrix computed.');
```

---

### getBoundingBox()

Calculates the axis-aligned bounding box of this node and all its descendants in world space.

```typescript
getBoundingBox(): BoundingBox
```

#### Returns

`BoundingBox`

The axis-aligned bounding box enclosing all geometry under this node.

#### Examples

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('model.obj');
const bbox = scene.rootNode.getBoundingBox();
console.log(`Min: ${JSON.stringify(bbox.minimum)}`);
console.log(`Max: ${JSON.stringify(bbox.maximum)}`);
```

---

### merge(node)

Merges the content of another node (its entities, materials, and children) into this node and removes the source node from the scene.

```typescript
merge(node: Node): void
```

#### Parameters

`node` `Node`

The source node whose content is merged into this node.

#### Returns

`void`

#### Examples

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('multi_part.fbx');

const root = scene.rootNode;
if (root.childNodes.length >= 2) {
  root.childNodes[0].merge(root.childNodes[1]);
  console.log(`Children after merge: ${root.childNodes.length}`);
}
```
