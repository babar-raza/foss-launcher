---
canonical: https://reference.aspose.org/3d/_index/
canonical_import: aspose_3d_foss
date: '2026-03-11T12:10:17Z'
dateModified: '2026-03-11T12:10:17Z'
datePublished: '2026-03-11T12:10:17Z'
description: The library exposes foundational classes like `Scene`, `Node`, `Mesh`,
  and `Geometry` to construct and modify 3D content programmatically.
display_name: Aspose.3D
family: 3d
keywords:
- python 3d game
- python 3d engine
- python 3d visualization
- 3d python
- 3d python game
- 3d python game engine
- 3d python logo
- 3d python library
lastmod: '2026-03-11T12:10:17Z'
page_role: toc
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.3D Table of Contents
slug: _index
title: Table of Contents
type: toc
url: /reference.aspose.org/3d/_index/
weight: 5
---

## Capabilities

Aspose.3D provides core 3D scene manipulation capabilities for Python developers building 3d python game engines, 3d python visualization tools, or python 3d game applications. The library exposes foundational classes like `Scene`, `Node`, `Mesh`, and `Geometry` to construct and modify 3D content programmatically.

- Create and edit 3D scenes using `Scene`, `Node`, and `Mesh` classes
- Define geometry with control points and polygons via `Mesh` and `Geometry`
- Manage object properties and metadata through `A3DObject`, `PropertyCollection`, and `AssetInfo`
- Configure rendering attributes such as visibility and shadow casting on `Geometry`

Animation API stubs (`AnimationClip`, `AnimationNode`, `AnimationChannel`, `BindPoint`) are present in the API surface but are not yet functional. Keyframe-based animation workflows are planned for a future release.

`Scene` objects like `Camera` and `Light` integrate into the scene hierarchy via `Node` and support exclusion and naming. The `GlobalTransform` class provides access to translation, rotation, scale, and full transform matrices for world-space positioning. All named entities implement `INamedObject` to support identification and organization within complex 3d python scenes.

## Quick Install

Install Aspose.3D for Python using pip to access core 3D classes like `Scene`, `Mesh`, `Node`, and `Entity` for python 3d visualization and python 3d game development workflows.

```bash
pip install aspose-3d-foss
```

After installation, verify the setup by importing `aspose.threed` and printing a confirmation message. This confirms the library is correctly installed and ready for use in 3d python projects.

```python
import aspose.threed
print('Installation successful')
```

## Getting Started

Aspose.3D provides core 3D scene manipulation capabilities in Python, enabling developers to build 3D python visualizations and integrate 3D python game engine components. The library exposes foundational classes like `Scene`, `Node`, `Mesh`, and `Entity` for constructing and managing 3D content programmatically.

## Developer Guide

Aspose.3D for Python provides core classes for managing 3D scene objects, including `A3DObject`, `Entity`, `Node`, and `Scene`. Developers working on python 3d game, python 3d engine, or python 3d visualization projects can use these classes to construct and manipulate hierarchical 3D structures. The `A3DObject` base class exposes `name` and `properties` attributes to manage object identity and metadata, while `Entity` adds scene graph integration via `parent_node` and `excluded`.

For geometric content, `Mesh` and `Geometry` classes provide control point and polygon definitions. The `Geometry` class exposes `visible`, `cast_shadows`, and `receive_shadows` to control rendering behavior, while `Mesh` (a subclass of `Geometry`) supports direct polygon construction. Scene-level asset metadata is managed through `AssetInfo`, which exposes `title`, `subject`, and `author` for document properties.

## See Also

- Learn about the [`Scene`](Scene) class for managing 3D scenes and objects
- Explore [`Mesh`](Mesh) and [`Geometry`](Geometry) classes for 3D model construction
- Review [`Node`](Node) and [`Entity`](Entity) classes for scene graph organization
