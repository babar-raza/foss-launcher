---
page_role: howto_article
title: Developer Guide
description: >-
  A complete developer guide for Aspose.3D FOSS for TypeScript — covering format
  support, scene-graph construction, materials, math utilities, animation, buffer
  loading, and production best practices.
type: docs
weight: 99
---

Aspose.3D FOSS for TypeScript is an open-source, MIT-licensed library that lets Node.js developers load, construct, transform, and export 3D scenes with full TypeScript type safety. Whether you are building an asset pipeline, a format-conversion service, a geometry validation tool, or a 3D content authoring script, this library provides a clean, consistent API backed by a scene-graph model that mirrors industry-standard 3D concepts.

This Developer Guide covers everything you need to go beyond the quick-start installation and write production-quality 3D processing code.

## What You Will Find in This Section

### Features and Functionalities

The [Features](features.md) page is the primary reference for working with Aspose.3D FOSS for TypeScript. It covers:

- **Format support** — OBJ (with .mtl materials), glTF 2.0 / GLB binary, STL (binary and ASCII), COLLADA (DAE), 3MF, and FBX, with per-format load and save option classes including `ObjLoadOptions` and `GltfSaveOptions`.
- **Scene graph** — How `Scene`, `Node`, `Entity`, `Transform`, and `SceneObject` compose into a full scene hierarchy, including child-node traversal patterns.
- **Geometry and mesh API** — Working with `Mesh`, `Geometry`, `VertexElementNormal`, `VertexElementUV`, `VertexElementVertexColor`, `MappingMode`, and `ReferenceMode` for geometry processing.
- **Material system** — Applying `LambertMaterial`, `PhongMaterial`, and `PbrMaterial` (PBR for glTF) to scene nodes, and reading material properties loaded from .mtl files.
- **Math utilities** — Using `Vector3`, `Vector4`, `Matrix4`, `Quaternion`, and `BoundingBox` for transforms, bounding-box queries, and geometric calculations.
- **Animation** — Constructing and reading `AnimationClip`, `AnimationNode`, `AnimationChannel`, `KeyFrame`, `KeyframeSequence`, `Interpolation`, and `Extrapolation` data.
- **Stream and buffer support** — Loading 3D scenes from in-memory `Buffer` objects via `scene.openFromBuffer()` for serverless and streaming use cases.
- **Complete usage examples** — End-to-end TypeScript scripts for loading OBJ, exporting GLB, round-tripping STL, and traversing scene graphs.
- **Tips, common issues, and FAQ** — Practical guidance for avoiding common pitfalls in production use.
- **API reference summary** — Quick-reference listing of all key classes and their primary methods.

## Key Concepts

**Scene graph**: All 3D content in Aspose.3D FOSS is represented as a tree of `Node` objects rooted at `scene.rootNode`. Each node can carry an `Entity` (such as a `Mesh`, `Camera`, or `Light`) and a `Transform` that positions it in the hierarchy.

**Format-agnostic API**: You open any supported format through `scene.open()` or `scene.openFromBuffer()` and save to any supported format through `scene.save()`. The same scene-graph objects are used regardless of the source or destination format.

**Strong TypeScript typing**: The library ships with strict compiler settings (`noImplicitAny`, `strictNullChecks`) and complete type definitions. Every class, method, and option property is fully typed, giving you IDE autocomplete and compile-time safety throughout your 3D processing code.

**Single dependency**: The only runtime dependency is `xmldom`, which is installed automatically by npm. There are no native addons to compile and no system packages to install.

## Getting Started

If you have not yet installed the library, see the [Getting Started](../getting-started/_index.md) section and the [Installation](../getting-started/installation.md) guide before reading further.

## Available Topics

- **[Features and Functionalities](features.md)** — Complete API reference with code examples for every major feature area.
