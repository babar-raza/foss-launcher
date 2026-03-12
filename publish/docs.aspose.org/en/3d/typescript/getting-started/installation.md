---
page_role: howto_article
title: "Installation"
description: "Install Aspose.3D FOSS for TypeScript with npm, configure tsconfig.json, verify the setup, and run a quick-start scene-loading script in Node.js."
type: docs
weight: 10
---

This guide covers everything you need to install Aspose.3D FOSS for TypeScript and confirm that it is working correctly before you write your first 3D processing script.

## Prerequisites

Ensure the following are installed and on your `PATH` before proceeding:

| Tool | Minimum | Notes |
|---|---|---|
| Node.js | 16 LTS | 18, 20, or 22 LTS recommended |
| npm | 7 | Bundled with Node.js |
| TypeScript | 5.0 | Install via `npm install -D typescript` |

To check your versions:

```bash
node --version   # v16.x.x or later
npm --version    # 7.x or later
npx tsc --version  # Version 5.x.x
```

## Step 1: Create a Project (if needed)

If you are adding Aspose.3D to an existing TypeScript project, skip this step and go directly to Step 2.

For a fresh project:

```bash
mkdir my-3d-project && cd my-3d-project
npm init -y
npm install -D typescript ts-node @types/node
```

## Step 2: Install @aspose/3d

```bash
npm install @aspose/3d
```

This installs the package and its single transitive dependency, `xmldom`, automatically. No additional system packages, native addons, or compilers are required. The installation is complete when `@aspose/3d` appears in your `package.json` under `dependencies`.

Verify the install:

```bash
ls node_modules/@aspose/3d
```

You should see the package directory with `package.json`, type definition files (`.d.ts`), and compiled JavaScript.

## Step 3: Configure TypeScript

Add or update `tsconfig.json` in your project root with the following settings. These are required for full compatibility with the library's type definitions and CommonJS output:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "moduleResolution": "node",
    "esModuleInterop": true,
    "strict": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
```

Key settings and why they matter:

| Setting | Value | Why |
|---|---|---|
| `target` | `ES2020` | Enables async/await, optional chaining, and other ES2020 features used internally |
| `module` | `commonjs` | The library ships CommonJS output; must match |
| `moduleResolution` | `node` | Required for correct resolution of the `@aspose/3d` sub-path imports |
| `esModuleInterop` | `true` | Enables default imports from CommonJS modules without namespace workarounds |
| `strict` | `true` | The library is authored with `noImplicitAny` and `strictNullChecks`; keep this on |

## Step 4: Verify the Installation

Create `src/verify.ts` with the following minimal import test:

```typescript
import { Scene } from '@aspose/3d';

const scene = new Scene();
console.log('Aspose.3D FOSS for TypeScript is installed correctly.');
console.log('rootNode name:', scene.rootNode.name);
```

Compile and run:

```bash
npx tsc
node dist/verify.js
```

Expected output:

```
Aspose.3D FOSS for TypeScript is installed correctly.
rootNode name: RootNode
```

If you prefer to skip the compile step during development, run directly with `ts-node`:

```bash
npx ts-node src/verify.ts
```

## Step 5: Quick Start — Load a Scene and Print Node Info

The following script loads a 3D file and prints the name and entity type of every node in the scene. It works with any supported format: OBJ, glTF, GLB, STL, 3MF, FBX, or COLLADA.

```typescript
import { Scene, Node } from '@aspose/3d';

function printNode(node: Node, depth: number = 0): void {
  const indent = '  '.repeat(depth);
  const entityType = node.entity ? node.entity.constructor.name : '(no entity)';
  console.log(`${indent}${node.name} [${entityType}]`);
  for (const child of node.childNodes) {
    printNode(child, depth + 1);
  }
}

const scene = new Scene();

// Replace 'model.obj' with any supported 3D file path.
// Format is detected automatically from binary magic numbers.
scene.open('model.obj');

console.log('Scene loaded. Node hierarchy:');
printNode(scene.rootNode);
```

Save this as `src/quickstart.ts` and run it:

```bash
npx ts-node src/quickstart.ts
```

For an OBJ file with one mesh named `Cube`, the output will look like:

```
Scene loaded. Node hierarchy:
  RootNode [(no entity)]
    Cube [Mesh]
```

## Dependency Notes

Aspose.3D FOSS for TypeScript has exactly one runtime dependency:

| Package | Purpose | Installed automatically |
|---|---|---|
| `xmldom` | XML parsing for COLLADA (DAE) and 3MF format support | Yes — by `npm install @aspose/3d` |

You do not need to install `xmldom` manually. It will appear in your `node_modules` after the main install command. There are no native addons (`.node` files) and no system libraries required.

## Next Steps

Now that the library is installed and verified:

- Read the [Developer Guide](/docs.aspose.org/3d/typescript/developer-guide/) for a complete walkthrough of all feature areas.
- See [Features and Functionalities](/docs.aspose.org/3d/typescript/developer-guide/features/) for format support details, scene-graph patterns, material and animation APIs, and full TypeScript code examples.
