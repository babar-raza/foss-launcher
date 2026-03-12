---
page_role: howto_article
linkTitle: "Class Scene"
title: "Class Scene"
description: "Scene is the root container for a 3D scene graph in @aspose/3d. It holds the node hierarchy, metadata, and animation clips, and provides the primary I/O interface for loading and saving 3D files."
summary: "Scene is the root container for a 3D scene graph in @aspose/3d. It holds the node hierarchy, metadata, and animation clips, and provides the primary I/O interface for loading and saving 3D files."
categories:
  - Class
layout: "reference-single"
---

Package: [@aspose/3d](https://www.npmjs.com/package/@aspose/3d) (v24.12.0)

Scene is the root container for a 3D scene graph in `@aspose/3d`. It holds the node hierarchy, metadata, and animation clips, and provides the primary I/O interface for loading and saving 3D files.

```typescript
export class Scene extends SceneObject
```

#### Inheritance

A3DObject ←
SceneObject ←
Scene

## Examples

Load an OBJ file and print the number of child nodes in the root of the scene graph.

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('model.obj');

function countNodes(node: any): number {
  let total = 1;
  for (const child of node.childNodes) {
    total += countNodes(child);
  }
  return total;
}

const nodeCount = countNodes(scene.rootNode);
console.log(`Total nodes in scene: ${nodeCount}`);
```

## Properties

| Property | Type | Description |
|---|---|---|
| `rootNode` | `Node` | The root node of the scene graph. All geometry, lights, cameras, and other objects are attached beneath this node. |
| `assetInfo` | `AssetInfo` | Metadata about the asset, including creator, creation time, unit information, and coordinate system. |
| `animationClips` | `AnimationClip[]` | The collection of animation clips defined in the scene. Each clip contains animation curves for nodes and their properties. |
| `subScenes` | `Scene[]` | Sub-scenes embedded within this scene. Used by formats such as FBX that support scene hierarchies. |

## Methods

### open(fileOrStream, options?)

Loads a 3D file from a file path or a `Buffer` into the scene, replacing any existing content.

```typescript
open(fileOrStream: string | Buffer, options?: LoadOptions): void
```

#### Parameters

`fileOrStream` `string | Buffer`

The path to the source file, or a `Buffer` containing the raw file data.

`options` `LoadOptions` (optional)

Format-specific load options. Pass `undefined` to use defaults.

#### Returns

`void`

#### Examples

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('input.fbx');
console.log(`Loaded scene with root node: ${scene.rootNode.name}`);
```

---

### openFromBuffer(buffer, options?)

Loads a 3D file from an in-memory `Buffer`. This is the preferred overload when the file data has already been read into memory.

```typescript
openFromBuffer(buffer: Buffer, options?: LoadOptions): void
```

#### Parameters

`buffer` `Buffer`

A Node.js `Buffer` containing the complete file content.

`options` `LoadOptions` (optional)

Format-specific load options.

#### Returns

`void`

#### Examples

```typescript
import { Scene } from '@aspose/3d';
import { readFileSync } from 'fs';

const data = readFileSync('model.glb');
const scene = new Scene();
scene.openFromBuffer(data);
console.log(`Animation clips: ${scene.animationClips.length}`);
```

---

### save(fileOrStream, format, options?)

Saves the scene to a file in the specified format.

```typescript
save(fileOrStream: string, format: FileFormat, options?: SaveOptions): void
```

#### Parameters

`fileOrStream` `string`

The destination file path.

`format` `FileFormat`

The output format, for example `FileFormat.GLTF2_BINARY` or `FileFormat.STL`.

`options` `SaveOptions` (optional)

Format-specific save options.

#### Returns

`void`

#### Examples

```typescript
import { Scene, FileFormat } from '@aspose/3d';

const scene = new Scene();
scene.open('input.obj');
scene.save('output.glb', FileFormat.GLTF2_BINARY);
console.log('Scene saved as GLB.');
```

---

### createAnimationClip(name)

Creates a new named animation clip and adds it to the scene's `animationClips` collection.

```typescript
createAnimationClip(name: string): AnimationClip
```

#### Parameters

`name` `string`

A descriptive name for the new animation clip.

#### Returns

`AnimationClip`

The newly created `AnimationClip` instance.

#### Examples

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
const clip = scene.createAnimationClip('WalkCycle');
console.log(`Created clip: ${clip.name}`);
console.log(`Total clips: ${scene.animationClips.length}`);
```
