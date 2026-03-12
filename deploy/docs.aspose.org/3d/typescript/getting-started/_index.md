---
page_role: howto_article
title: Getting Started
description: >-
  Prerequisites and first steps for using Aspose.3D FOSS for TypeScript —
  Node.js version requirements, npm installation, and TypeScript configuration.
type: docs
weight: 10
---

Aspose.3D FOSS for TypeScript is distributed as an npm package and requires only a single command to install. This section walks you through the prerequisites, installation, and a minimal first program that proves the library is working correctly in your environment.

## Prerequisites

Before installing the package, ensure your environment meets the following requirements:

| Requirement | Minimum Version | Recommended |
|---|---|---|
| Node.js | 16 LTS | 20 LTS or 22 LTS |
| npm | 7 | 10 (bundled with Node.js 20+) |
| TypeScript | 5.0 | 5.4+ |

**Node.js**: The library targets CommonJS output and relies on built-in Node.js APIs (`fs`, `Buffer`, `path`). Any of Node.js 16, 18, 20, or 22 is supported. Older versions (14 and below) are not supported. Download Node.js from [nodejs.org](https://nodejs.org/).

**TypeScript**: The library is authored with strict compiler settings (`noImplicitAny`, `strictNullChecks`). TypeScript 5.0 or later is required for full type-checking compatibility. Install it locally in your project with `npm install -D typescript`.

**npm or yarn**: Either package manager works. The examples in this guide use npm. If you use yarn, replace `npm install` with `yarn add` throughout.

## Installing the Package

See the [Installation](installation.md) guide for the complete setup walkthrough, including:

- Installing `@aspose/3d` via npm
- Configuring `tsconfig.json` for compatibility
- Verifying the installation with a quick import test
- A complete quick-start script that loads a scene and prints node information
- Notes on the single transitive dependency (`xmldom`)

## Available Topics

- **[Installation](installation.md)** — Step-by-step setup guide with TypeScript configuration and a verified quick-start example.
