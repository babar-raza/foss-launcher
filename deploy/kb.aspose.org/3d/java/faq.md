---
canonical: https://kb.aspose.org/3d/java/faq/
canonical_import: com.aspose.threed
code_import: com.aspose.threed
date: '2026-03-24T16:56:25Z'
dateModified: '2026-03-24T16:56:25Z'
datePublished: '2026-03-24T16:56:25Z'
description: However, USD (.usd, .usda, .usdc) import is not implemented and will
  fail if attempted. The library also does not support importing some other formats...
display_name: Aspose.3D
family: 3d
keywords:
- 3d javascript
- 3d javascript library
- 3d java
- 3d java skins
- 3d javascript game engine
- 3d javascript game
- 3d javascript framework
- 3d java game engine
lastmod: '2026-03-24T16:56:25Z'
page_role: faq
platform: java
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D FAQ | Guide
slug: faq
title: Aspose.3D FAQ
type: faq
url: /kb.aspose.org/3d/java/faq/
weight: 8
---

## Frequently Asked Questions

### What file formats can Aspose.3D import?

Aspose.3D supports importing several 3D formats including STL, OBJ, 3DS, and FBX. However, USD (.usd, .usda, .usdc) import is not implemented and will fail if attempted. The library also does not support importing some other formats listed in FILE_FORMATS.md as 'Not implemented'.

### Can Aspose.3D `export` animations and constraints from FBX files?

No, Aspose.3D does not support advanced FBX features such as animations and constraints. While basic FBX geometry can be imported and exported, animation data and constraint information are not processed or preserved during conversion. This limitation applies to both import and `export` operations.

### Is MTL file `export` supported when saving OBJ files?

MTL `export` is not yet implemented in Aspose.3D. When exporting a scene to OBJ format, the library generates the .obj file but does not produce a corresponding .mtl file with material definitions. You must manually `create` or manage material files if needed.

### How do I `load` a 3D file using Aspose.3D in Java?

Use the `Scene` class to `load` supported 3D files. First, `create` a `Scene` instance, then call `load()` with a file path or input stream. The following example loads an STL file and saves it as FBX.

```java
import com.aspose.threed.*;

Scene scene = new Scene();
scene.load("input.stl");
scene.save("output.fbx", new FbxSaveOptions());
```

### Does Aspose.3D support ASCII FBX format?

ASCII FBX format is not yet supported. Aspose.3D only handles binary FBX files during import and `export` operations. Attempting to use or generate ASCII FBX will not work as the parser and writer for ASCII FBX have not been implemented.

### Why does my exported STL file have duplicate vertices?

Aspose.3D does not implement vertex deduplication for STL files. Each face uses separate vertices instead of sharing them, which increases file `size` and may affect rendering performance. This is a known limitation and applies to all `export` formats where vertex sharing is not enforced.

## See Also

Aspose.3D is a Java library for working with 3D files, released under the MIT License. It supports importing and exporting common 3D formats like STL, GLTF, and FBX, though several features remain incomplete. For example, vertex deduplication is not implemented for STL files, and ASCII FBX format is not yet supported. Advanced FBX features such as animations and constraints are also not implemented, and MTL `export` for OBJ files remains unimplemented. The library is a work-in-progress port, and current status is tracked in TODO.md and FILE_FORMATS.md.

- [Troubleshooting common issues](/kb.aspose.org/3d/java/troubleshooting/)
- [Convert file formats step-by-step](/kb.aspose.org/3d/java/how-to-convert-fbx-to-gltf-java/)
- [Fix common errors effectively](/kb.aspose.org/3d/java/how-to-fix-3d-models-errors-java/)
- [Load files correctly](/kb.aspose.org/3d/java/how-to-load-3d-models-java/)
- [Optimize performance tips](/kb.aspose.org/3d/java/how-to-optimize-3d-models-java/)
