---
page_role: howto_article
title: "How to Save 3D Models in TypeScript"
description: "Learn how to save 3D scenes to glTF, OBJ, STL, FBX, 3MF, and COLLADA formats from TypeScript using @aspose/3d FOSS."
date: 2026-03-11
weight: 25
draft: false
type: "topic"
keywords: ["save 3d model typescript", "export gltf nodejs", "aspose 3d save", "@aspose/3d export", "typescript write 3d file", "scene save typescript"]
step1: "Install @aspose/3d via npm"
step2: "Load or construct a Scene"
step3: "Save using scene.save() with auto-detected format"
step4: "Use format-specific SaveOptions for fine-grained control"
step5: "Save to a Buffer for in-memory output"
step6: "Verify the output file"
---

Aspose.3D FOSS for TypeScript saves scenes to all supported formats with a single `scene.save()` call. The output format is detected automatically from the file extension. This guide covers saving to each format and using format-specific options.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install @aspose/3d

```bash
npm install @aspose/3d
```

---

### Step 2: Load or Construct a Scene

Either load an existing file or build a scene programmatically before saving.

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

// Load from file
const scene = new Scene();
scene.open('source.obj', new ObjLoadOptions());

// Or create a new empty scene
const emptyScene = new Scene();
```

---

### Step 3: Save with Auto-Detected Format

`scene.save(path)` detects the output format from the file extension:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('input.obj', new ObjLoadOptions());

// Save as binary glTF
scene.save('output.glb');

// Save as JSON glTF
scene.save('output.gltf');

// Save as STL
scene.save('output.stl');

// Save as OBJ
scene.save('output.obj');

// Save as FBX
scene.save('output.fbx');

// Save as 3MF
scene.save('output.3mf');

// Save as COLLADA
scene.save('output.dae');
```

---

### Step 4: Use Format-Specific SaveOptions

For fine-grained control, pass a format-specific options object:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

// Export to GLB with specific options
const saveOptions = new GltfSaveOptions();
saveOptions.embedAssets = true;  // embed textures into binary GLB

scene.save('output.glb', saveOptions);
```

---

### Step 5: Save to a Buffer (In-Memory)

Use `scene.saveToBuffer()` to get the output as a `Buffer` without writing to disk:

```typescript
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';

const scene = new Scene();
scene.open('model.obj', new ObjLoadOptions());

const buffer = scene.saveToBuffer('output.glb');
console.log(`Buffer size: ${buffer.length} bytes`);

// Send via HTTP, upload to S3, etc.
```

---

### Step 6: Verify the Output

After saving, verify the file exists and has a non-zero size:

```typescript
import * as fs from 'fs';

const stats = fs.statSync('output.glb');
console.log(`Saved output.glb: ${stats.size} bytes`);
```

{{% /steps %}}

---

## Format Support Matrix

| Extension | Format | Notes |
|-----------|--------|-------|
| `.glb` | glTF 2.0 Binary | Recommended for glTF; all assets embedded in single file |
| `.gltf` | glTF 2.0 JSON | Separate `.bin` and texture files alongside JSON |
| `.obj` | Wavefront OBJ | Writes `.mtl` material file alongside `.obj` when materials present |
| `.stl` | STL | Default: binary STL; use `StlSaveOptions.ascii = true` for text |
| `.fbx` | Autodesk FBX | Binary FBX format |
| `.3mf` | 3D Manufacturing | Suitable for 3D printing workflows |
| `.dae` | COLLADA | XML-based interchange format |

---

## Common Issues and Fixes

**`Error: Unsupported format` when saving**

Check that the file extension matches a supported format. The library uses the extension to detect format; a file named `output.xyz` will fail.

**`.obj` file saves but materials are missing**

When saving OBJ, the material library (`.mtl`) is written automatically alongside the `.obj`. Both files must be in the same directory when re-opening. If you only need geometry, set `ObjSaveOptions.enableMaterials = false`.

**Large `.gltf` with separate textures**

Use `.glb` instead of `.gltf` — it bundles all textures and binary data into a single file. Pass `GltfSaveOptions.embedAssets = true` to ensure textures are inlined.

---

## Frequently Asked Questions

**Can I save to multiple formats in one run?**

Yes — call `scene.save()` multiple times with different paths:

```typescript
scene.save('output.glb');
scene.save('output.stl');
scene.save('output.obj');
```

**Does saving modify the scene?**

No. `scene.save()` is a read-only operation on the scene graph. You can save the same scene to multiple formats without any side effects.

**Can I overwrite the source file?**

Yes. Pass the same path to `scene.save()` that you used in `scene.open()`. The library writes to a buffer and then writes to disk.

---

## See Also

- [How to Load 3D Models in TypeScript](/kb.aspose.org/3d/typescript/how-to-load-3d-models-in-typescript/)
- [How to Export glTF in TypeScript](/kb.aspose.org/3d/typescript/how-to-export-gltf-in-typescript/)
- [Format Support](/docs.aspose.org/3d/typescript/developer-guide/format-support/)
- [API Reference](/reference.aspose.org/3d/typescript/)
