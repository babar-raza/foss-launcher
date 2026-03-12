---
page_role: howto_article
title: "Real-World Use Cases for @aspose/3d in TypeScript"
description: "Practical examples of using @aspose/3d in TypeScript — web service asset conversion, CI pipeline format validation, batch processing, and 3D printing file preparation."
date: 2026-03-11
weight: 50
draft: false
type: "topic"
keywords: ["aspose 3d typescript use cases", "@aspose/3d examples", "3d file conversion nodejs", "batch 3d processing typescript", "fbx to glb typescript"]
---

This page covers practical, production-grade use cases for `@aspose/3d` in TypeScript and Node.js — from HTTP API services to CI validation pipelines.

---

## Use Case 1: HTTP Service for 3D Asset Conversion

Build an Express.js endpoint that accepts an uploaded 3D file and returns a converted GLB:

```typescript
// converter-service.ts
import express from 'express';
import multer from 'multer';
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

app.post('/convert/obj-to-glb', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    const scene = new Scene();
    const loadOpts = new ObjLoadOptions();
    loadOpts.enableMaterials = true;
    scene.openFromBuffer(req.file.buffer, loadOpts);

    const saveOpts = new GltfSaveOptions();
    saveOpts.binaryMode = true;
    saveOpts.embedAssets = true;

    const glbBuffer = scene.saveToBuffer('output.glb', saveOpts);

    res.setHeader('Content-Type', 'model/gltf-binary');
    res.setHeader('Content-Disposition', 'attachment; filename="output.glb"');
    res.send(glbBuffer);
});

app.listen(3000, () => console.log('Converter service listening on :3000'));
```

This pattern requires no temporary files and works inside Docker containers or serverless environments.

---

## Use Case 2: CI Pipeline — Validate 3D Asset Integrity

Add a Node.js script to your CI pipeline that verifies all committed 3D files load correctly and contain geometry:

```typescript
// scripts/validate-assets.ts
import * as fs from 'fs';
import * as path from 'path';
import { Scene, Mesh } from '@aspose/3d';

const ASSET_DIR = './assets/3d';
const EXTENSIONS = ['.obj', '.fbx', '.glb', '.stl', '.dae'];

let failed = 0;

function countMeshes(node: any): number {
    let count = node.entity instanceof Mesh ? 1 : 0;
    for (const child of node.childNodes) count += countMeshes(child);
    return count;
}

for (const file of fs.readdirSync(ASSET_DIR)) {
    const ext = path.extname(file).toLowerCase();
    if (!EXTENSIONS.includes(ext)) continue;

    const filePath = path.join(ASSET_DIR, file);
    try {
        const scene = new Scene();
        scene.open(filePath);
        const meshCount = countMeshes(scene.rootNode);
        if (meshCount === 0) {
            console.error(`FAIL: ${file} — no meshes found`);
            failed++;
        } else {
            console.log(`OK: ${file} — ${meshCount} mesh(es)`);
        }
    } catch (err) {
        console.error(`ERROR: ${file} — ${(err as Error).message}`);
        failed++;
    }
}

if (failed > 0) {
    console.error(`\n${failed} asset(s) failed validation`);
    process.exit(1);
}
console.log('All assets validated successfully.');
```

Add to your `package.json` scripts and call from your CI step:

```json
{
  "scripts": {
    "validate-assets": "npx ts-node scripts/validate-assets.ts"
  }
}
```

---

## Use Case 3: Batch Conversion with Worker Threads

Convert a directory of OBJ files to GLB in parallel using Node.js worker threads:

```typescript
// worker.ts
import { workerData, parentPort } from 'worker_threads';
import { Scene } from '@aspose/3d';
import { ObjLoadOptions } from '@aspose/3d/formats/obj';
import { GltfSaveOptions } from '@aspose/3d/formats/gltf';

const { inputPath, outputPath } = workerData as { inputPath: string; outputPath: string };

const scene = new Scene();
const loadOpts = new ObjLoadOptions();
loadOpts.enableMaterials = true;
loadOpts.normalizeNormal = true;
scene.open(inputPath);

const saveOpts = new GltfSaveOptions();
saveOpts.binaryMode = true;
saveOpts.embedAssets = true;
scene.save(outputPath, saveOpts);

parentPort?.postMessage({ ok: true, output: outputPath });
```

```typescript
// main.ts
import { Worker } from 'worker_threads';
import * as fs from 'fs';
import * as path from 'path';

const INPUT_DIR = './input';
const OUTPUT_DIR = './output';
const CONCURRENCY = 4;

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const files = fs.readdirSync(INPUT_DIR).filter(f => f.endsWith('.obj'));
let active = 0;
let index = 0;

function dispatch(): void {
    while (active < CONCURRENCY && index < files.length) {
        const file = files[index++];
        const inputPath = path.join(INPUT_DIR, file);
        const outputPath = path.join(OUTPUT_DIR, file.replace('.obj', '.glb'));

        active++;
        const worker = new Worker(path.resolve('./dist/worker.js'), {
            workerData: { inputPath, outputPath }
        });

        worker.on('message', msg => {
            console.log(`Converted: ${msg.output}`);
            active--;
            dispatch();
        });

        worker.on('error', err => {
            console.error(`Failed: ${inputPath} — ${err.message}`);
            active--;
            dispatch();
        });
    }
}

dispatch();
```

Run with `npx tsc && node dist/main.js`. Adjust `CONCURRENCY` to match available CPU cores.

---

## Use Case 4: Prepare Models for 3D Printing

Convert FBX source files to 3MF format for slicer software:

```typescript
import * as fs from 'fs';
import * as path from 'path';
import { Scene } from '@aspose/3d';

const SOURCE_DIR = './models/fbx';
const PRINT_DIR = './models/print';

fs.mkdirSync(PRINT_DIR, { recursive: true });

for (const file of fs.readdirSync(SOURCE_DIR)) {
    if (!file.endsWith('.fbx')) continue;

    const inputPath = path.join(SOURCE_DIR, file);
    const outputPath = path.join(PRINT_DIR, file.replace('.fbx', '.3mf'));

    const scene = new Scene();
    scene.open(inputPath);
    scene.save(outputPath);

    const { size } = fs.statSync(outputPath);
    console.log(`${file} → ${path.basename(outputPath)} (${Math.round(size / 1024)} KB)`);
}
```

For STL output (maximum slicer compatibility), change the output extension to `.stl`. Note that STL loses material and color data.

---

## Use Case 5: Extract Scene Statistics for an Asset Database

Scan a repository of 3D files and emit a JSON summary for ingestion into an asset management system:

```typescript
import * as fs from 'fs';
import * as path from 'path';
import { Scene, Mesh, Node } from '@aspose/3d';

interface AssetStats {
    file: string;
    format: string;
    meshCount: number;
    totalVertices: number;
    totalPolygons: number;
    animationClips: number;
    sizeBytes: number;
}

function collectStats(node: Node, stats: AssetStats): void {
    if (node.entity instanceof Mesh) {
        const mesh = node.entity as Mesh;
        stats.meshCount++;
        stats.totalVertices += mesh.controlPoints.length;
        stats.totalPolygons += mesh.polygonCount;
    }
    for (const child of node.childNodes) {
        collectStats(child, stats);
    }
}

const SCAN_DIR = './assets';
const results: AssetStats[] = [];
const EXTENSIONS = ['.obj', '.fbx', '.glb', '.gltf', '.stl', '.dae', '.3mf'];

for (const file of fs.readdirSync(SCAN_DIR)) {
    const ext = path.extname(file).toLowerCase();
    if (!EXTENSIONS.includes(ext)) continue;

    const filePath = path.join(SCAN_DIR, file);
    const stats: AssetStats = {
        file, format: ext.slice(1).toUpperCase(),
        meshCount: 0, totalVertices: 0, totalPolygons: 0,
        animationClips: 0, sizeBytes: fs.statSync(filePath).size
    };

    try {
        const scene = new Scene();
        scene.open(filePath);
        collectStats(scene.rootNode, stats);
        stats.animationClips = scene.animationClips.length;
    } catch {
        // skip unreadable files
    }

    results.push(stats);
}

fs.writeFileSync('asset-stats.json', JSON.stringify(results, null, 2));
console.log(`Scanned ${results.length} assets → asset-stats.json`);
```

---

## See Also

- [How to Convert 3D Models](/kb.aspose.org/3d/typescript/how-to-convert-3d-models-typescript/)
- [How to Optimize 3D Models](/kb.aspose.org/3d/typescript/how-to-optimize-3d-models-typescript/)
- [Rendering and Export](/docs.aspose.org/3d/typescript/developer-guide/rendering/)
- [API Overview](/reference.aspose.org/3d/typescript/api-overview/)
