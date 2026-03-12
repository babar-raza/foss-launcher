---
page_role: howto_article
title: "Converting Between 3D Formats in TypeScript with @aspose/3d"
seoTitle: "Convert 3D Files in TypeScript: OBJ, glTF, STL, FBX with @aspose/3d"
description: "Learn how to convert 3D files between OBJ, glTF/GLB, STL, 3MF, FBX, and COLLADA formats in Node.js TypeScript applications using the @aspose/3d library."
date: "2026-02-15"
author: "Aspose Team"
summary: "A practical guide to converting 3D file formats in Node.js using @aspose/3d v24.12.0, covering the most common workflows: OBJ to GLB for the web, OBJ to STL for 3D printing, STL to glTF for visualization, 3MF to glTF for manufacturing pipelines, and batch conversion patterns."
tags: ["typescript", "nodejs", "3d", "gltf", "stl", "format conversion"]
categories: ["Developer Guides", "3D"]
---

Node.js developers working with 3D content frequently need to convert between formats: a design tool exports OBJ, a web renderer expects GLB, a 3D printer requires STL, and a manufacturing pipeline uses 3MF. Handling these conversions with a single, consistent API reduces the number of external tools in a pipeline and keeps conversion logic inside the application code where it can be tested and versioned.

The `@aspose/3d` package (v24.12.0, MIT license) provides a TypeScript-first API for reading and writing all major 3D formats in Node.js. This guide walks through the most common conversion workflows.

## Installation

```bash
npm install @aspose/3d
```

Requirements: Node.js 16, 18, 20, or 22; TypeScript 5.0 or later. The only runtime dependency is `xmldom`.

## Supported Formats

The table below lists the formats covered in this guide and their read/write support.

| Format | Extension | Read | Write | Notes |
|---|---|:---:|:---:|---|
| Wavefront OBJ | `.obj` | Yes | No | Import-only in @aspose/3d |
| glTF 2.0 (JSON) | `.gltf` | Yes | Yes | Standard web delivery format |
| glTF 2.0 (Binary) | `.glb` | Yes | Yes | Self-contained, preferred for web |
| STL (ASCII/Binary) | `.stl` | Yes | Yes | Standard 3D printing format |
| 3MF | `.3mf` | Yes | Yes | Manufacturing format with rich metadata |
| FBX | `.fbx` | Yes | Yes | Common exchange format from DCC tools |
| COLLADA | `.dae` | Yes | Yes | XML-based exchange format |

**Important:** OBJ is an import-only format in `@aspose/3d`. You can read OBJ files into a `Scene` and save to any supported output format, but you cannot save a scene as OBJ.

## OBJ to GLB (Web Delivery)

Converting OBJ to binary glTF (GLB) is the most common web workflow. GLB is a self-contained binary bundle: textures, geometry, and metadata in a single file, which makes it efficient for HTTP delivery and direct loading by Three.js, Babylon.js, and model-viewer.

```typescript
import { Scene, FileFormat } from '@aspose/3d';

async function convertObjToGlb(inputPath: string, outputPath: string): Promise<void> {
  const scene = new Scene();
  scene.open(inputPath);
  scene.save(outputPath, FileFormat.GLTF2_BINARY);
  console.log(`Converted ${inputPath} -> ${outputPath}`);
}

convertObjToGlb('model.obj', 'model.glb');
```

The `FileFormat.GLTF2_BINARY` constant selects the binary GLB container. Use `FileFormat.GLTF2` if you need the separate `.gltf` + `.bin` layout instead.

## OBJ to STL (3D Printing Prep)

STL is the lingua franca of FDM and SLA 3D printing. Slicers such as PrusaSlicer, Bambu Studio, and Chitubox all accept STL. Converting from OBJ to STL is straightforward because both formats store triangle meshes.

```typescript
import { Scene, FileFormat } from '@aspose/3d';

function convertObjToStl(inputPath: string, outputPath: string): void {
  const scene = new Scene();
  scene.open(inputPath);
  scene.save(outputPath, FileFormat.STL);
  console.log(`STL written to ${outputPath}`);
}

convertObjToStl('part.obj', 'part.stl');
```

STL does not store color, material, or UV data. If your OBJ file uses material groups, that information is dropped during export. For color-preserving print formats, consider 3MF instead (see below).

## STL to glTF (Scanner and CAD to Web)

Structured-light scanners and parametric CAD exporters commonly output STL. Converting to glTF makes the geometry accessible in web-based viewers and AR platforms without a server-side rendering step.

```typescript
import { Scene, FileFormat } from '@aspose/3d';

function convertStlToGltf(inputPath: string, outputPath: string): void {
  const scene = new Scene();
  scene.open(inputPath);
  // Save as separate .gltf + .bin files
  scene.save(outputPath, FileFormat.GLTF2);
  console.log(`glTF written to ${outputPath}`);
}

convertStlToGltf('scan_output.stl', 'scan_output.gltf');
```

Because STL carries no material or texture information, the resulting glTF file will contain geometry only. You can attach materials programmatically to scene nodes after loading if needed.

## 3MF to glTF (Manufacturing to Visualization)

The 3D Manufacturing Format (3MF) is increasingly used in additive manufacturing workflows because it stores color, materials, component trees, and print metadata alongside geometry. Converting 3MF to glTF enables downstream visualization in web tools while preserving the scene structure.

```typescript
import { Scene, FileFormat } from '@aspose/3d';

function convert3mfToGlb(inputPath: string, outputPath: string): void {
  const scene = new Scene();
  scene.open(inputPath);
  scene.save(outputPath, FileFormat.GLTF2_BINARY);
  console.log(`3MF -> GLB: ${outputPath}`);
}

convert3mfToGlb('assembly.3mf', 'assembly.glb');
```

3MF files often contain multi-component assemblies. The scene graph produced by `scene.open()` preserves the component hierarchy in `scene.rootNode.childNodes`, so you can inspect or manipulate individual parts before saving.

## Batch Conversion Pattern

When processing a directory of files, wrap each conversion in a `try/catch` so that a single corrupt file does not abort the entire batch.

```typescript
import { Scene, FileFormat } from '@aspose/3d';
import { readdirSync } from 'fs';
import { join, basename, extname } from 'path';

interface ConversionResult {
  input: string;
  output: string;
  success: boolean;
  error?: string;
}

function batchConvertToGlb(
  inputDir: string,
  outputDir: string,
  extensions: string[] = ['.obj', '.stl', '.3mf', '.fbx', '.dae']
): ConversionResult[] {
  const results: ConversionResult[] = [];

  const files = readdirSync(inputDir).filter((f) =>
    extensions.includes(extname(f).toLowerCase())
  );

  for (const file of files) {
    const inputPath = join(inputDir, file);
    const outputPath = join(outputDir, basename(file, extname(file)) + '.glb');

    try {
      const scene = new Scene();
      scene.open(inputPath);
      scene.save(outputPath, FileFormat.GLTF2_BINARY);
      results.push({ input: inputPath, output: outputPath, success: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      results.push({ input: inputPath, output: outputPath, success: false, error: message });
      console.error(`Failed to convert ${file}: ${message}`);
    }
  }

  const succeeded = results.filter((r) => r.success).length;
  console.log(`Batch complete: ${succeeded}/${results.length} files converted.`);
  return results;
}

// Usage
batchConvertToGlb('./input', './output');
```

The pattern above reads each supported file extension from an input directory, converts to GLB, and logs any failures without stopping the loop. The returned array of `ConversionResult` objects can be used for reporting or retry logic.

## Conclusion

`@aspose/3d` covers the full range of format conversion needs in a Node.js TypeScript application with a consistent two-step API: `scene.open()` to load, `scene.save()` to write. The key constraint to remember is that OBJ is import-only — you can read OBJ files and convert them to any supported output, but you cannot write back to OBJ.

For more detail on the `Scene`, `Node`, and `Mesh` classes used in these examples, see the class reference pages in this documentation.
