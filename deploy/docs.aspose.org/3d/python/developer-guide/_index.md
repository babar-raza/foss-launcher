---
page_role: howto_article
title: Developer Guide
description: >-
  A complete developer guide for Aspose.3D FOSS for Python — covering format
  support, scene-graph construction, materials, math utilities, animation, and
  production best practices.
type: docs
weight: 99
---

Aspose.3D FOSS for Python is an open-source, MIT-licensed library that lets Python developers load, construct, transform, and export 3D scenes without any external runtime dependencies. Whether you are building an asset pipeline, a validation tool, a geometry processing script, or a format-conversion service, this library provides a clean, consistent API backed by a scene-graph model that mirrors industry-standard 3D concepts.

This Developer Guide covers everything you need to go beyond the quick-start installation and write production-quality 3D processing code.

## What You Will Find in This Section

### Features and Functionalities

The [Features](features.md) page is the primary reference for working with Aspose.3D FOSS for Python. It covers:

- **Format support** — OBJ (with .mtl materials), STL (binary and ASCII), glTF 2.0 / GLB, COLLADA (DAE), 3MF, and the in-progress FBX tokenizer, with per-format load and save option classes.
- **Scene graph** — How `Scene`, `Node`, `Entity`, `Transform`, and `GlobalTransform` compose into a full scene hierarchy, including child-node traversal patterns.
- **Mesh API** — Working with `control_points`, `VertexElementNormal`, `VertexElementUV`, `VertexElementVertexColor`, and `VertexElementSmoothingGroup` for geometry processing.
- **Material system** — Applying `LambertMaterial` and `PhongMaterial` to scene nodes, and reading material properties loaded from .mtl files.
- **Math utilities** — Using `Vector2`, `Vector3`, `Vector4`, `FVector3`, `Quaternion`, `Matrix4`, and `BoundingBox` for transforms, bounding-box queries, and geometric calculations.
- **Animation** — Constructing and reading `AnimationClip`, `AnimationNode`, `KeyFrame`, and `KeyframeSequence` data.
- **Load and save options** — Per-format option classes such as `ObjLoadOptions` (flip_coordinate_system, scale, enable_materials, normalize_normal) and `StlSaveOptions`.
- **Complete usage examples** — End-to-end Python scripts for loading OBJ, exporting STL, round-tripping glTF, and traversing scene graphs.
- **Tips, common issues, and FAQ** — Practical guidance for avoiding common pitfalls in production use.
- **API reference summary** — Quick-reference listing of all key classes.

## Key Concepts

**Scene graph**: All 3D content in Aspose.3D FOSS is represented as a tree of `Node` objects rooted at `scene.root_node`. Each node can carry an `Entity` (such as a `Mesh`, `Camera`, or `Light`) and a `Transform` that positions it in the hierarchy.

**Format-agnostic API**: You open any supported format through `Scene.open()` or `Scene.from_file()` and save to any supported format through `Scene.save()`. The same scene-graph objects are used regardless of the source or destination format.

**Zero dependencies**: The library is pure Python. There is no native extension to compile, no system package to install, and no third-party library to manage.

## Getting Started

If you have not yet installed the library, see the [Getting Started](../getting-started/_index.md) section and the [Installation](../getting-started/installation.md) guide before reading further.

## Available Topics

- **[Features and Functionalities](features.md)** — Complete API reference with code examples for every major feature area.
