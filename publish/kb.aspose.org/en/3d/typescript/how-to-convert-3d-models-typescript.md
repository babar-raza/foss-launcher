---
page_role: howto_article
title: "How to Convert 3D Models in TypeScript"
description: "Learn how to convert between 3D file formats (OBJ, glTF, FBX, STL, 3MF, COLLADA) in TypeScript using @aspose/3d FOSS."
date: 2026-03-11
weight: 30
draft: false
type: "topic"
keywords: ["convert 3d models typescript", "obj to gltf nodejs", "fbx to glb typescript", "aspose 3d convert", "@aspose/3d convert formats", "3d format conversion typescript"]
step1: "Install @aspose/3d via npm"
step2: "Load the source file with scene.open()"
step3: "Save to the target format with scene.save()"
step4: "Use format-specific options for accurate conversion"
step5: "Batch-convert multiple files"
---

Aspose.3D FOSS for TypeScript converts between 3D formats by loading into a neutral `Scene` representation and saving to the target format. This guide shows the most common conversions.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install @aspose/3d

```bash
npm install @aspose/3d
```

---

### Step 2: Load the Source File

Create a `Scene` and call `scene.open()`. Use the format-specific `*LoadOptions` class for best results.

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
const opts = new ObjLoadOptions();
opts.enableMaterials = true;
scene.open('model.obj', opts);
```

---

### Step 3: Save to the Target Format

Call `scene.save()` with the output path. The output format is detected from the file extension.

```typescript
// OBJ → glTF binary (GLB)
scene.save('output.glb');

// OBJ → STL
scene.save('output.stl');

// OBJ → FBX
scene.save('output.fbx');
```

---

### Step 4: Common Conversion Examples

#### OBJ to glTF / GLB

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());
scene.save('model.glb');
console.log('Converted OBJ → GLB');
```

#### FBX to glTF

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('scene.fbx');
scene.save('scene.gltf');
console.log('Converted FBX → glTF');
```

#### glTF to STL

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('model.glb');
scene.save('model.stl');
console.log('Converted GLB → STL');
```

#### COLLADA to 3MF

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
scene.open('model.dae');
scene.save('model.3mf');
console.log('Converted COLLADA → 3MF');
```

---

### Step 5: Batch Convert Multiple Files

```typescript
import * as fs from 'fs';
import * as path from 'path';
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const inputDir = './input';
const outputDir = './output';

fs.mkdirSync(outputDir, { recursive: true });

const objFiles = fs.readdirSync(inputDir).filter(f => f.endsWith('.obj'));

for (const file of objFiles) {
    const inputPath = path.join(inputDir, file);
    const outputFile = file.replace('.obj', '.glb');
    const outputPath = path.join(outputDir, outputFile);

    const scene = new Scene();
    scene.open(inputPath, new ObjLoadOptions());
    scene.save(outputPath);

    console.log(`Converted ${file} → ${outputFile}`);
}
```

{{% /steps %}}

---

## Supported Conversion Matrix

| From \ To | glTF/GLB | OBJ | STL | FBX | 3MF | COLLADA |
|-----------|----------|-----|-----|-----|-----|---------|
| OBJ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| glTF/GLB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| FBX | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| STL | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3MF | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| COLLADA | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Common Issues and Fixes

**Materials are lost after conversion**

OBJ materials (`usemtl`, `.mtl` file) are loaded when `ObjLoadOptions.enableMaterials = true`. When saving to glTF, PBR material properties are mapped automatically. Complex materials (procedural, multi-layer) may convert with reduced fidelity.

**Mesh appears scaled incorrectly**

Different formats use different default units (millimeters for STL, meters for glTF). Use `ObjLoadOptions.scale` when loading or `StlSaveOptions.scaleFactor` when saving to normalize units.

**Coordinate system mismatch (model flipped or rotated)**

Some formats use right-hand Y-up, others Z-up. Use `ObjLoadOptions.flipCoordinateSystem = true` or apply a rotation to the root node after loading.

---

## Frequently Asked Questions

**Does conversion preserve animations?**

Animation data is preserved when converting between formats that support it (FBX → glTF, COLLADA → FBX, etc.). STL and OBJ do not carry animation data.

**Is texture data preserved?**

Textures referenced by OBJ materials or embedded in glTF are carried through to the scene graph. When saving to a format that embeds textures (GLB with `embedAssets = true`), textures are included. For OBJ output, textures are saved as separate files alongside the `.obj`.

**Can I convert many files in parallel?**

`scene.open()` and `scene.save()` are synchronous. Use Node.js `worker_threads` for parallel processing.

---

## See Also

- [How to Load 3D Models in TypeScript](/kb.aspose.org/3d/typescript/how-to-load-3d-models-in-typescript/)
- [How to Save 3D Models in TypeScript](/kb.aspose.org/3d/typescript/how-to-save-3d-models-typescript/)
- [Format Support](/docs.aspose.org/3d/typescript/developer-guide/format-support/)
- [API Reference](/reference.aspose.org/3d/typescript/)
