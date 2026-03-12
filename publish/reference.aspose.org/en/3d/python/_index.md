---
page_role: howto_article
title: "Aspose.3D FOSS for Python — API Reference"
description: "Complete API reference for Aspose.3D FOSS for Python (aspose-3d-foss 26.1.0). All public classes organized by category with descriptions."
date: 2026-01-15
weight: 1
draft: false
type: "topic"
keywords: ["aspose 3d python api", "aspose threed reference", "3d python classes", "scene node mesh python", "aspose 3d foss api reference"]
---

API reference for **aspose-3d-foss 26.1.0** (Python 3.7 – 3.12, MIT license).

All classes are imported from the `aspose.threed` package or its sub-packages. The root import is:

```python
import aspose.threed
##or selectively:
from aspose.threed import Scene, Node
from aspose.threed.entities import Mesh, Camera, Light
from aspose.threed.formats import ObjLoadOptions, StlSaveOptions, GltfSaveOptions
from aspose.threed.utilities import Vector3, Matrix4, BoundingBox
from aspose.threed.animation import AnimationClip, KeyFrame
```

---

## Core Scene Graph

| Class | Description |
|---|---|
| `Scene` | Top-level container for all 3D scene data. Holds the root node, asset metadata, and animation clips. Exposes `from_file()`, `open()`, and `save()` as the primary I/O entry points. |
| `Node` | A named node in the scene hierarchy. Owns a list of child nodes and a list of attached `Entity` objects such as meshes, cameras, and lights. Carries a local `Transform`. |
| `Entity` | Abstract base class for all objects that can be attached to a `Node`. Provides name and identity but no geometry of its own. |
| `SceneObject` | Base class shared by `Node` and `Entity`. Provides the property collection interface used for user-defined metadata. |
| `A3DObject` | Root base class for all Aspose.3D managed objects. Exposes the name property and the `Properties` collection. |
| `INamedObject` | Interface that guarantees a `name` property. Implemented by `Node`, `Entity`, and several format-specific descriptor types. |

---

## Geometry and Mesh

| Class | Description |
|---|---|
| `Mesh` | Polygon mesh entity. Stores control points (vertex positions as `Vector4`), polygon face lists (lists of control-point indices), and vertex element layers (normals, UVs, vertex colours). |
| `Geometry` | Abstract base for mesh-like geometry types. Defines the control-point array and the collection of `VertexElement` layers. `Mesh` inherits from `Geometry`. |
| `VertexElement` | Abstract base for a data layer attached to geometry (normals, UVs, colours, etc.). Carries `mapping_mode`, `reference_mode`, and a `data` list. |
| `VertexElementNormal` | Stores one normal vector per vertex or per polygon corner, depending on `mapping_mode`. Data values are `Vector4` instances with `w` unused. |
| `VertexElementUV` | Stores texture-coordinate pairs (`Vector2`) per vertex or per polygon corner. A mesh may carry multiple UV layers for different texture channels. |
| `VertexElementVertexColor` | Stores per-vertex or per-corner RGBA colour data as `Vector4` (r, g, b, a in the range 0–1). |
| `VertexElementSmoothingGroup` | Stores per-polygon smoothing group integer IDs, used by the OBJ importer to reproduce the original smoothing group assignments from the source file. |
| `VertexElementType` | Enumeration identifying the semantic role of a vertex element layer: `NORMAL`, `UV`, `VERTEX_COLOR`, `SMOOTHING_GROUP`, and others. Pass values to `Mesh.get_element()`. |
| `MappingMode` | Enumeration controlling which primitive a vertex element value maps to: `CONTROL_POINT`, `POLYGON_VERTEX`, `POLYGON`, `EDGE`, or `ALL_SAME`. |
| `ReferenceMode` | Enumeration controlling how values are indexed: `DIRECT` (one value per mapping primitive) or `INDEX_TO_DIRECT` (values array plus a separate indices array). |

---

## Transform and Spatial

| Class | Description |
|---|---|
| [`Transform`](/reference.aspose.org/3d/python/transform/) | Local transformation attached to a `Node`. Provides translation, rotation (as `Quaternion`), and scale components, plus convenience properties for Euler angles. |
| `GlobalTransform` | Read-only view of a node's world-space transformation after composing all ancestor transforms. Accessed via `Node.global_transform`. |
| `AssetInfo` | Metadata block attached to a `Scene`. Stores authoring application name, unit name, unit scale factor, coordinate system axis definitions, and creation/modification timestamps. |

---

## Materials and Shading

| Class | Description |
|---|---|
| `Material` | Abstract base class for all material types. Provides a name and a property collection for numeric and colour parameters. |
| [`LambertMaterial`](/reference.aspose.org/3d/python/material/) | Diffuse-only material model. Stores ambient colour, diffuse colour, emissive colour, and transparency. Loaded from OBJ files that use basic `Ka`/`Kd`/`Ke` declarations. |
| [`PhongMaterial`](/reference.aspose.org/3d/python/material/) | Extends `LambertMaterial` with specular colour and shininess (specular exponent). Loaded from OBJ files that use `Ks`/`Ns` declarations. |

---

## Camera and Lighting

| Class | Description |
|---|---|
| [`Camera`](/reference.aspose.org/3d/python/camera/) | Camera entity. Stores projection type, field of view, near and far clip distances, and aspect ratio. Attached to a `Node` to define viewpoint transforms. |
| [`Light`](/reference.aspose.org/3d/python/light/) | Light-source entity. Stores light type, colour, intensity, and attenuation parameters. |
| `LightType` | Enumeration of supported light categories: `POINT`, `DIRECTIONAL`, `SPOT`, `AREA`. |
| `ProjectionType` | Enumeration of camera projection modes: `PERSPECTIVE` and `ORTHOGRAPHIC`. |

---

## Math Utilities

| Class | Description |
|---|---|
| `Vector2` | Double-precision 2-component vector (`x`, `y`). Used for UV texture coordinates. |
| `Vector3` | Double-precision 3-component vector (`x`, `y`, `z`). Used for positions, directions, and scale. |
| `Vector4` | Double-precision 4-component vector (`x`, `y`, `z`, `w`). Used for control points (homogeneous positions) and normal data. |
| `FVector2` | Single-precision 2-component float vector. Used internally for compact storage. |
| `FVector3` | Single-precision 3-component float vector. Appears in some vertex element data arrays where memory efficiency matters. |
| `FVector4` | Single-precision 4-component float vector. |
| `Quaternion` | Unit quaternion for representing rotations (`x`, `y`, `z`, `w`). Used by `Transform.rotation`. |
| `Matrix4` | 4×4 double-precision transformation matrix. Used for world/local transform computations and can be constructed from TRS decompositions. |
| `BoundingBox` | Axis-aligned bounding box defined by a minimum and maximum `Vector3`. Used for spatial queries and frustum culling helpers. |

---

## Animation

| Class | Description |
|---|---|
| `AnimationClip` | Named container for a set of animated channels covering one playback range. A `Scene` may hold multiple clips (e.g., "Walk", "Run"). |
| `AnimationNode` | Binds an `AnimationClip` to a specific scene node or property. Acts as the bridge between clip data and scene graph objects. |
| `AnimationChannel` | A single animated property stream within a clip, targeting a named property on an object (e.g., `Transform.translation.x`). |
| `KeyFrame` | A single time–value sample within a `KeyframeSequence`. Stores the time (in seconds) and the value at that time. |
| `KeyframeSequence` | An ordered list of `KeyFrame` objects for one scalar channel, together with interpolation and extrapolation settings. |
| `Interpolation` | Enumeration of interpolation modes between keyframes: `CONSTANT`, `LINEAR`, `BEZIER`, `B_SPLINE`, `CARDINAL_SPLINE`, `CUBIC`. |
| `Extrapolation` | Enumeration of behaviours beyond the first and last keyframe: `CONST`, `LINEAR`, `REPEAT`, `MIRROR_REPEAT`, `RELATIVE_REPEAT`. |

---

## Format I/O

| Symbol | Description |
|---|---|
| `Scene.from_file(path)` | Static method. Opens the file at `path`, detects the format from the extension, and returns a populated `Scene`. Raises on file-not-found or unsupported format. |
| `Scene.open(path, options=None)` | Instance method. Opens a file into an existing `Scene` instance, optionally using a format-specific `LoadOptions` subclass. |
| `Scene.save(path, options=None)` | Instance method. Serialises the scene to `path` using the format inferred from the extension, optionally using a format-specific `SaveOptions` subclass. |
| `FileFormat` | Enumeration / registry of supported file formats. Contains entries such as `FileFormat.WAVEFRONT_OBJ`, `FileFormat.STL`, `FileFormat.GLTF2`, `FileFormat.COLLADA`, `FileFormat.THREED_MF`. |
| `IOService` | Internal I/O abstraction used by format importers and exporters. Not typically used directly by application code. |
| `LoadOptions` | Abstract base class for all format-specific load-option objects. Subclassed by `ObjLoadOptions`, `StlLoadOptions`, `GltfLoadOptions`, `ColladaLoadOptions`, `ThreeMfLoadOptions`. |
| `SaveOptions` | Abstract base class for all format-specific save-option objects. Subclassed by `ObjSaveOptions`, `StlSaveOptions`, `GltfSaveOptions`, `ThreeMfSaveOptions`. |

---

## OBJ Format

| Class | Description |
|---|---|
| `ObjImporter` | Internal importer class that parses Wavefront OBJ and MTL files. Invoked automatically by `Scene.from_file()` for `.obj` extensions. |
| `ObjLoadOptions` | Load options for Wavefront OBJ files. Key properties: `flip_coordinate_system` (bool), `scale` (float), `enable_materials` (bool, loads the `.mtl` file), `normalize_normal` (bool). |
| `ObjSaveOptions` | Save options for Wavefront OBJ output. Controls how normals, UVs, and material references are written. |
| `ObjFormat` | Format descriptor for Wavefront OBJ. Accessible as `FileFormat.WAVEFRONT_OBJ`. |

---

## STL Format

| Class | Description |
|---|---|
| `StlImporter` | Internal importer that reads both binary and ASCII STL files. Selected automatically by extension. |
| `StlExporter` | Internal exporter that writes binary STL. |
| `StlLoadOptions` | Load options for STL files. Supports coordinate-system and scale adjustments consistent with `ObjLoadOptions`. |
| `StlSaveOptions` | Save options for STL output. Defaults to binary STL, which is more compact than ASCII for most geometry. |
| `StlFormat` | Format descriptor for STL. Accessible as `FileFormat.STL`. |

---

## glTF Format

| Class | Description |
|---|---|
| `GltfLoadOptions` | Load options for glTF 2.0 and GLB files. Supports coordinate-system adjustments. |
| `GltfSaveOptions` | Save options for glTF 2.0 output. Use a `.gltf` extension for JSON + external buffer, or `.glb` for a self-contained binary package. |
| `GltfFormat` | Format descriptor for glTF 2.0 / GLB. Accessible as `FileFormat.GLTF2`. |

---

## COLLADA Format

| Class | Description |
|---|---|
| `ColladaLoadOptions` | Load options for COLLADA (`.dae`) files. Controls axis remapping and unit scale on import. |
| `ColladaFormat` | Format descriptor for COLLADA. Accessible as `FileFormat.COLLADA`. |

---

## 3MF Format

| Class | Description |
|---|---|
| `ThreeMfLoadOptions` | Load options for 3MF (`.3mf`) files. Supports unit and axis settings. |
| `ThreeMfSaveOptions` | Save options for 3MF output. 3MF is the preferred format for 3D printing workflows. |
| `ThreeMfFormat` | Format descriptor for 3MF. Accessible as `FileFormat.THREED_MF`. |

---

## Enumerations

| Enumeration | Description |
|---|---|
| `Axis` | Identifies a coordinate axis: `X_AXIS`, `Y_AXIS`, `Z_AXIS`. Used in coordinate-system remapping options. |
| `CoordinateSystem` | Specifies handedness convention: `RIGHT_HAND` or `LEFT_HAND`. |
| `TextureMapping` | Identifies how a texture is mapped to geometry: `DIFFUSE`, `SPECULAR`, `EMISSIVE`, `NORMAL`, `AMBIENT`, etc. |

---

## Properties System

| Class | Description |
|---|---|
| `Property` | A single named typed property on an `A3DObject`. Stores the property name, type descriptor, and current value. |
| `PropertyCollection` | Iterable collection of `Property` objects attached to an `A3DObject`. Supports lookup by name and iteration over all defined properties. |
| `CustomObject` | A lightweight `A3DObject` subclass that carries only a name and an arbitrary `PropertyCollection`. Used for storing user-defined metadata on scene objects. |

---

## Image and Render

| Class | Description |
|---|---|
| `ImageRenderOptions` | Options for software rasterisation when rendering a scene to an image buffer. Stores background colour, image dimensions, and camera reference. This feature is available in supported configurations. |

---

## See Also

- [How to Load 3D Models in Python](/kb.aspose.net/3d/python/how-to-load-3d-models-in-python/)
- [How to Convert 3D Models in Python](/kb.aspose.net/3d/python/how-to-convert-3d-models-in-python/)
- [PyPI: aspose-3d-foss](https://pypi.org/project/aspose-3d-foss/)
