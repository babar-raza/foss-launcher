---
canonical: https://reference.aspose.org/3d/_index/
canonical_import: aspose.threed
code_import: aspose.threed
date: '2026-03-24T16:58:09Z'
dateModified: '2026-03-24T16:58:09Z'
datePublished: '2026-03-24T16:58:09Z'
description: The `library` enables loading, editing, and saving 3D models using core
  classes like `Scene`, `Node`, `Entity`, and `FileFormat`.
display_name: Aspose.3D
family: 3d
keywords:
- 3d python
- 3d python game engine
- 3d python game
- 3d python logo
- 3d python plot
- 3d python library
- 3d python program
- 3d python engine
lastmod: '2026-03-24T16:58:09Z'
page_role: toc
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.3D Reference _Index
slug: _index
title: Reference _Index
type: toc
url: /reference.aspose.org/3d/_index/
weight: 5
---

## Capabilities

This section covers the Python API for 3D `scene` manipulation, format I/O, and animation support in Aspose.3D. The `library` enables loading, editing, and saving 3D models using core classes like `Scene`, `Node`, `Entity`, and `FileFormat`.

- Open and save 3D scenes in OBJ, GLTF, 3MF, and FBX formats using `FileFormat` and `Scene.save()` / `Scene.open()`
- Build and modify scene hierarchies with `Node` and `Entity` objects, including adding child nodes and entities
- Create and manage animation clips, nodes, and keyframe sequences via `AnimationClip`, `AnimationNode`, and `BindPoint`
- Work with geometry data through `Mesh` and `Geometry` classes, including vertex elements and polygon topology

Aspose.3D supports 3D Python workflows for visualization, game asset preparation, and 3D printing pipelines. Developers can use `Scene` to load models, traverse `Node` trees, and `export` to `target` `formats` using `FileFormat` detection and explicit format selection.

## Quick Install

This section covers installation and setup for Aspose.3D, the Python `library` for 3D model processing, `scene` manipulation, and format conversion. Use pip to install the package, then verify the installation by importing the core module.

```bash
pip install aspose-3d
```

After installation, verify the setup by importing `aspose.threed` and instantiating a `Scene` object. This confirms the `library` loads correctly and the core API surface is accessible.

```python
import aspose.threed
scene = aspose.threed.Scene()
```

## Getting Started

This section covers the Python API for 3D `scene` creation, loading, and saving using Aspose.3D. The `library` supports core 3D operations through classes like `Scene`, `Node`, `Entity`, `Geometry`, and `FileFormat`, enabling 3D python program development for modeling, visualization, and format conversion workflows.

- Open and save 3D scenes in OBJ, GLTF, 3MF, and FBX formats
- Build scenes hierarchically using `Node` and `Entity` objects
- Create and manipulate geometry with `Geometry` and `Mesh` classes
- Manage animations via `AnimationClip`, `AnimationNode`, and `BindPoint`

## Developer Guide

This section covers the core classes and operations for loading, constructing, and manipulating 3D scenes in Aspose.3D using Python. It provides navigational guidance to the API surface for developers building 3D python applications, including 3D python game engine components, 3D python plots, and 3D python logo generation workflows.

The `Scene` class serves as the root container for 3D content, supporting `open()` and `save()` operations across supported `formats` including OBJ, GLTF, STL, and 3MF. Use `Node` and `Entity` to build hierarchical `scene` graphs, where `Node.add_entity()` and `Node.create_child_node()` establish object relationships. The `FileFormat` class provides static format identifiers and automatic format detection via `detect()`.

Animation support is provided through `AnimationClip`, `AnimationNode`, and `BindPoint`, enabling keyframe-based animation of `scene` `properties`. `Geometry` and mesh `data` are represented by `Geometry` and `Mesh`, with vertex element management via `create_element()` and `get_element()`. All classes conform to the `A3DObject` base interface for `property` access and `scene` graph integration.

## See Also

This section covers the Python API for 3D `scene` management, geometry handling, and file format operations in Aspose.3D. The API surface includes core classes like `Scene`, `Node`, `Entity`, `Geometry`, `Mesh`, and `FileFormat` for loading, manipulating, and saving 3D assets.

- [Scene and Node Hierarchy](scene-node-hierarchy.md) — manage 3D scene structure using `Scene`, `Node`, and `Entity` classes.
- [Geometry and Mesh Processing](geometry-mesh.md) — create and modify vertex data, polygons, and mesh topology.
- [File Format Import and Export](file-formats.md) — load and save 3D models in OBJ, GLTF, STL, and 3MF formats.
- [Animation System](animation.md) — define animation clips, nodes, and keyframe sequences using `AnimationClip` and `BindPoint`.
