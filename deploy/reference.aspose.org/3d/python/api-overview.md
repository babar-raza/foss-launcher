---
canonical: https://reference.aspose.org/3d/python/api-overview/
canonical_import: aspose.threed
date: '2026-03-12T15:45:33Z'
dateModified: '2026-03-12T15:45:33Z'
datePublished: '2026-03-12T15:45:33Z'
description: The `Scene` class serves as the root container with hierarchical child
  node management for organizing 3D `scene` content. The `Node` class supports...
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
lastmod: '2026-03-12T15:45:33Z'
page_role: api_reference
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D API Reference | Guide
slug: api-overview
title: Aspose.3D API Reference
type: api_reference
url: /reference.aspose.org/3d/python/api-overview/
weight: 6
---

## Overview

Aspose.3D for Python enables programmatic manipulation of 3D scenes, including loading, inspecting, and organizing 3D content using the `Scene`, `Node`, and `Entity` classes. The `Scene` class serves as the root container with hierarchical child node management for organizing 3D `scene` content. The `Node` class supports parent-child relationships, `entity` attachment, and `material` assignment for building 3D `scene` hierarchies, with methods like `parent_node`, `entity`, `material`, `visible`, and `excluded`.

## Public API

Aspose.3D for Python provides a focused set of classes for loading, inspecting, and manipulating 3D scenes. The core hierarchy starts with the `Scene` class, which holds a root node and manages child nodes for organizing 3D content. The `Node` class enables parent-child relationships, `entity` attachment (e.g., `Mesh`), and `material` assignment—forming the backbone of `scene` graph construction. Animation support is provided through `AnimationClip`, `AnimationNode`, and `KeyframeSequence`, which allow keyframe-based animation definition and manipulation.

```python
from aspose.threed import Scene
from aspose.threed import FileFormat

# Load a 3D file and inspect its root node
scene = Scene.from_file('model.fbx')
print(f"Root node: {scene.root_node.name}")
print(f"Child node count: {len(scene.root_node.child_nodes)}")

# Inspect first mesh entity
for node in scene.root_node.child_nodes:
    if node.entity:
        print(f"Entity type: {type(node.entity).__name__}")
        break
```

The `FileFormat` class exposes static methods for common 3D `formats` (e.g., `WAVEFRONT_OBJ`, `GLTF2`, `FBX7400ASCII`, `MICROSOFT_3MF_FORMAT`) and a `detect()` method to infer format from a stream or filename. The `SceneObject` base class provides access to the parent `Scene` via its `scene` `property`, while `A3DObject` supports named objects with extensible `properties` via `name` and `properties`. Animation-related classes like `KeyframeSequence` and `AnimationClip` support keyframe management and clip metadata (`name`, `description`, `start`/`stop` times).

| Class | Key Methods | Key Properties | Description |
|-------|-------------|----------------|-------------|
| `Scene` | `from_file`(), `open`() | `root_node` | Top-level container for 3D content with hierarchical node management |
| `Node` | `parent_node`(), `entity`(), `material`() | `child_nodes`, `entity`, `material` | `Scene` graph node supporting hierarchy, `entity` and `material` attachment |
| `Entity` | `parent_node`(), `excluded`(), `get_bounding_box`() | `parent_nodes`, `excluded` | Base class for renderable objects (e.g., `Mesh`) |
| `KeyframeSequence` | `reset`(), `add`(), `name`() | — | Stores keyframes for animation channels |
| `AnimationClip` | `create_animation_node`(), `name`(), `start`(), `stop`() | `animations`, `description` | Defines an animation sequence with `start`/`stop` times |
| `FileFormat` | `WAVEFRONT_OBJ`(), `GLTF2`(), `detect`() | `extension`, `content_type` | Format constants and auto-detection utility |
| `AssetInfo` | `title`(), `author`(), `keywords`() | `title`, `author`, `keywords` | Metadata for 3D assets |
| `SceneObject` | `scene`() | — | Base class providing access to parent `scene` |
| `ExtrapolationType` | — | — | Enum: CONSTANT, GRADIENT, CYCLE, CYCLE_RELATIVE, OSCILLATE |

## Common Patterns

Aspose.3D enables loading and inspecting 3D scenes using the `Scene` class, which exposes a hierarchical structure via `root_node`. The `Node` class supports parent-child relationships and `entity` attachment, allowing developers to build and traverse 3D `scene` hierarchies in Python 3D engine or visualization workflows.

The `AssetInfo` class provides metadata access through methods like `title`, `author`, and `keywords`. These can be used to read or set document `properties` during import or export operations in 3D python applications.

| Method | Return | Description |
|--------|--------|-------------|
| `title(value: str)` | str | Gets or sets the document `title` |
| `subject(value: str)` | str | Gets or sets the document `subject` |
| `author(value: str)` | str | Gets or sets the document `author` |
| `keywords(value: str)` | str | Gets or sets document `keywords` |
| `revision(value: str)` | str | Gets or sets the `revision` string |

## See Also

Developers building 3D python game engines or visualization tools can use Aspose.3D to load and manipulate 3D assets. The `library` supports Phong and Lambert `materials` with configurable diffuse, specular, `ambient`, and transparency `properties`, and provides file format detection and conversion for OBJ, GLTF, 3MF, and FBX `formats`.

```python
import aspose.threed

# Detect file format from stream
with open('model.obj', 'rb') as f:
    fmt = aspose.threed.FileFormat.detect(f, 'model.obj')
    print(fmt.file_format_type)
```

- [Node class reference](/reference.aspose.org/3d/python/entity/)
- [Frequently asked questions](/kb.aspose.org/3d/python/faq/)
- [Troubleshooting common issues](/kb.aspose.org/3d/python/troubleshooting/)
- [Getting started guide](/docs.aspose.org/3d/python/developer-guide/getting-started/)
- [Installation instructions](/docs.aspose.org/3d/python/developer-guide/installation/)
