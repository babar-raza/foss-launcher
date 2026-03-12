---
page_role: howto_article
title: "Aspose.3D FOSS for TypeScript — API Reference"
description: "Complete API reference for @aspose/3d version 24.12.0. All public classes, enumerations, and options types organized by category."
date: 2026-01-20
weight: 1
draft: false
type: "topic"
keywords: ["aspose 3d typescript api", "aspose 3d class reference", "3d nodejs api reference", "@aspose/3d classes"]
---

API reference for `@aspose/3d` version **24.12.0**. Install via:

```bash
npm install @aspose/3d
```

Runtime: Node.js 16, 18, 20, 22+ · Language: TypeScript 5.0+ / JavaScript (CommonJS) · License: MIT

---

## Core Scene Graph

### Scene

The root container for a 3D scene. Call `scene.open()` or `scene.openFromBuffer()` to load a file, and `scene.save()` to write output. Exposes `scene.rootNode` as the entry point to the node hierarchy.

### Node

A named node in the scene tree. Holds a `Transform`, an optional `entity` (mesh, camera, light, or other `SceneObject`), and zero or more child nodes accessible via `childNodes`.

### Entity

Base class for all objects that can be attached to a `Node` as its primary entity. Subclassed by `Mesh`, `Camera`, `Light`, and others.

### SceneObject

Abstract base for named objects that belong to a scene. Provides the `name` property and scene-membership tracking shared by nodes, entities, and asset-level objects.

### A3DObject

Root base class for all Aspose.3D objects. Provides the property system (`getProperty`, `setProperty`) and the `name` field inherited by every public class.

---

## Geometry and Mesh

### Mesh

Represents a polygon mesh. Contains a `controlPoints` array of `Vector4` vertices and polygon definitions created via `createPolygon()`. Call `triangulate()` to convert all polygons to triangles before export.

### Geometry

Base class for all geometry types. Holds `controlPoints` and the collection of vertex elements (normals, UVs, colors) attached to the geometry.

### VertexElement

Base class for per-vertex attribute channels attached to a `Geometry`. Subclasses carry typed data arrays and `mappingMode` / `referenceMode` metadata.

### VertexElementNormal

A `VertexElement` subclass that stores surface normals as `FVector3` values. Required by most renderers for correct lighting.

### VertexElementUV

A `VertexElement` subclass that stores 2D texture coordinates. A single mesh may have multiple UV sets for different texture layers.

### VertexElementVertexColor

A `VertexElement` subclass that stores per-vertex RGBA color values.

### VertexElementType

Enumeration of the attribute channel types that a `VertexElement` can represent (e.g., `Normal`, `UV`, `VertexColor`, `Tangent`, `BiTangent`).

### MappingMode

Enumeration controlling how element data maps onto geometry: `ControlPoint`, `PolygonVertex`, `Polygon`, or `AllSame`.

### ReferenceMode

Enumeration controlling how element indices reference data: `Direct` (one-to-one) or `IndexToDirect` (via an index array).

### TextureMapping

Enumeration of UV coordinate generation modes used when mapping textures onto a surface.

---

## Transform and Spatial

### Transform

Holds the local position (`translation`), rotation (`rotation` as `Quaternion`), and scale (`scale`) of a `Node`. Changes here affect the node and all its children.

### GlobalTransform

Read-only view of a node's world-space transform, computed by accumulating all ancestor `Transform` values. Access via `node.globalTransform`.

### BoundingBox

An axis-aligned bounding box defined by a minimum and maximum `Vector3` corner. Used to describe the spatial extent of a mesh or scene.

---

## Materials

### Material

Abstract base class for all material types. Exposes a name and the shared property-collection infrastructure.

### LambertMaterial

A diffuse-only material with ambient, diffuse, and emissive color channels. Suitable for non-specular surfaces.

### PhongMaterial

Extends `LambertMaterial` with specular color and shininess properties for Phong shading.

### PbrMaterial

A physically-based rendering material with metallic, roughness, base-color, and normal-map channels. Maps directly to the glTF 2.0 PBR material model.

---

## Camera and Lighting

### Camera

A viewpoint node entity with projection type, field of view, near/far clip distances, and aspect ratio properties.

### Light

A light-source node entity. Type is controlled by the `LightType` enumeration.

### LightType

Enumeration of supported light kinds: `Point`, `Directional`, and `Spot`.

### ProjectionType

Enumeration of camera projection modes: `Perspective` and `Orthographic`.

---

## Math Utilities

### Vector3

A three-component floating-point vector with `x`, `y`, `z` fields and common arithmetic methods.

### Vector4

A four-component floating-point vector with `x`, `y`, `z`, `w` fields. Used as the type of entries in `Mesh.controlPoints`.

### FVector3

A compact three-component single-precision float vector used in vertex element data arrays for normals and tangents.

### Matrix4

A 4×4 transformation matrix. Supports multiplication, inversion, and decomposition into translation, rotation, and scale components.

### Quaternion

A unit quaternion for representing rotations without gimbal lock. Provides `slerp()` for smooth interpolation and conversion to/from Euler angles.

---

## Animation

### AnimationClip

A named, time-bounded collection of `AnimationNode` tracks. The primary container for keyframe animation data loaded from FBX or COLLADA files.

### AnimationNode

A named animation track that targets a specific property path on a scene object. Contains one or more `AnimationChannel` objects.

### AnimationChannel

A single animated property channel within an `AnimationNode`. Holds a `KeyframeSequence` of time/value pairs.

### KeyFrame

A single time/value sample in a `KeyframeSequence`. Carries the time stamp (in seconds), the value, and tangent information for interpolation.

### KeyframeSequence

An ordered list of `KeyFrame` samples for one property channel, along with the `Interpolation` and `Extrapolation` settings that govern playback.

### Interpolation

Enumeration of keyframe interpolation modes: `Constant`, `Linear`, and `Bezier`.

### Extrapolation

Defines behavior outside the keyframe range (before the first key and after the last key). Controlled by `ExtrapolationType`.

### StepMode

Enumeration controlling how stepped (constant) interpolation is applied at boundaries.

### WeightedMode

Enumeration for Bezier tangent weight handling: `None`, `Right`, `NextLeft`, or `Both`.

### ExtrapolationType

Enumeration of out-of-range behaviors: `Constant`, `Linear`, `Cycle`, `CycleOffset`, and `Oscillate`.

---

## Format I/O

### FileFormat

Base descriptor for a 3D file format. Each supported format provides a concrete singleton via `getInstance()`.

### Importer

Base class for format-specific import implementations. Not instantiated directly — invoked internally by `scene.open()`.

### Exporter

Base class for format-specific export implementations. Not instantiated directly — invoked internally by `scene.save()`.

### LoadOptions

Base class for format-specific load option objects. Pass a subclass instance to `scene.open()` or `scene.openFromBuffer()`.

### SaveOptions

Base class for format-specific save option objects. Pass a subclass instance to `scene.save()`.

### IOService

Internal service interface that abstracts file-system and buffer I/O for importers and exporters.

---

## OBJ Format

> **Import only.** OBJ export (`canExport: false`) is not supported.

### ObjImporter

Internal importer that reads Wavefront OBJ files, resolves `.mtl` material libraries, and populates a `Scene`. Invoked automatically when `ObjLoadOptions` is passed to `scene.open()`.

### ObjLoadOptions

Load options for OBJ files. Key property: `enableMaterials` (boolean) — when `true`, the importer resolves the `.mtl` file referenced by the `mtllib` directive.

### ObjSaveOptions

Defined in the API surface for completeness but not functional — OBJ export is not supported. Attempting to save to OBJ will throw an unsupported-operation error.

### ObjFormat

Format descriptor singleton for OBJ. `canExport` is `false`; `canImport` is `true`.

---

## glTF Format

### GltfImporter

Reads glTF 2.0 JSON (`.gltf`) and binary GLB (`.glb`) files. Handles embedded and external buffer references, PBR materials, skins, and animation clips.

### GltfExporter

Writes glTF 2.0 output. When `GltfSaveOptions.binaryMode` is `true`, produces a self-contained GLB; otherwise writes a JSON `.gltf` with a companion `.bin` buffer.

### GltfLoadOptions

Load options for glTF/GLB files. Controls buffer resolution and texture loading behavior.

### GltfSaveOptions

Save options for glTF/GLB export. Notable properties: `binaryMode` (boolean, `true` → GLB), `embedImages` (boolean, embeds textures inline), `flipTexCoordV` (boolean, flips UV vertical axis).

### GltfFormat

Format descriptor singleton. Obtain via `GltfFormat.getInstance()` and pass to `scene.save()` as the second argument.

---

## STL Format

### StlImporter

Reads both ASCII and binary STL files into a `Scene` containing a single `Mesh` entity.

### StlExporter

Writes binary STL. The output contains the triangulated mesh from the scene; non-triangle polygons are triangulated automatically.

### StlLoadOptions

Load options for STL. Controls whether the importer flips normals during import.

### StlSaveOptions

Save options for STL export. Controls whether the output is ASCII or binary STL.

### StlFormat

Format descriptor singleton. Obtain via `StlFormat.getInstance()`.

---

## 3MF Format

### ThreeMfImporter

Reads Open Packaging Convention 3MF archives and populates a `Scene` with mesh objects, colors, and material properties.

### ThreeMfExporter

Writes a valid 3MF archive from the current scene. Suitable for 3D printing workflows.

### ThreeMfLoadOptions

Load options for 3MF files.

### ThreeMfSaveOptions

Save options for 3MF export.

### ThreeMfFormat

Format descriptor singleton. Obtain via `ThreeMfFormat.getInstance()`.

---

## FBX Format

### FbxImporter

Reads FBX binary and ASCII files including geometry, materials, skeletons, blend shapes, and animation clips.

### FbxExporter

Writes FBX files from the current scene. Both binary and ASCII FBX output are supported depending on options.

### FbxLoadOptions

Load options for FBX. Controls whether animation, skins, and blend shapes are imported.

### FbxSaveOptions

Save options for FBX export. Controls binary vs ASCII output and the target FBX version.

### FbxFormat

Format descriptor singleton. Obtain via `FbxFormat.getInstance()`.

---

## COLLADA Format

> COLLADA import and export require the `xmldom` peer dependency, which is installed automatically with `@aspose/3d`.

### ColladaImporter

Reads COLLADA (`.dae`) XML files using `xmldom`. Handles geometry, materials, cameras, lights, and animation.

### ColladaExporter

Writes COLLADA XML output from the current scene. Suitable for interchange with DCC tools (Blender, Maya, etc.).

### ColladaFormat

Format descriptor singleton. Obtain via `ColladaFormat.getInstance()`.

---

## Properties System

### Property

A typed name/value pair that can be attached to any `A3DObject`. Supports scalar and vector value types.

### PropertyCollection

An ordered container of `Property` objects. Accessible on any `A3DObject` via `getProperties()` or the `properties` accessor.

### CustomObject

A free-form property bag that extends `A3DObject`. Used to store arbitrary metadata that does not map to a standard class.

---

## Asset Info

### AssetInfo

Carries scene-level metadata loaded from the source file: author, application name, creation date, unit scale, and coordinate axis information.

### ImageRenderOptions

Options controlling how textures and images are resolved and encoded when saving to formats that embed image data (e.g., GLB with `embedImages: true`).

---

## See Also

- [Knowledge Base: How-To Guides](/kb/3d/typescript/)
- [npm: @aspose/3d](https://www.npmjs.com/package/@aspose/3d)
- [GitHub: aspose-3d-node](https://github.com/aspose-3d/aspose-3d-node)
