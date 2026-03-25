---
canonical: https://kb.aspose.org/3d/java/troubleshooting/
canonical_import: com.aspose.threed
code_import: com.aspose.threed
date: '2026-03-24T16:56:25Z'
dateModified: '2026-03-24T16:56:25Z'
datePublished: '2026-03-24T16:56:25Z'
description: This occurs because several formats (e.g., USD) have no importer implementation
  yet, as confirmed in FILE_FORMATS.md.
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
page_role: troubleshooting
platform: java
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D Troubleshooting
slug: troubleshooting
title: Troubleshooting
type: troubleshooting
url: /kb.aspose.org/3d/java/troubleshooting/
weight: 9
---

## Common Issues

If `load()` throws `ImportException` with a message indicating the format is not supported, the file format lacks import support in Aspose.3D. This occurs because several formats (e.g., USD) have no importer implementation yet, as confirmed in FILE_FORMATS.md.

If you attempt to `export` an OBJ file with MTL references, the `export` completes but the MTL file is not generated. This is expected behavior because MTL `export` is not yet implemented in Aspose.3D, per FILE_FORMATS.md.

If you `load` an FBX file containing animations or constraints and expect them to be preserved, they will be ignored during import or `export`. Aspose.3D does not yet support advanced FBX features such as animations and constraints, as stated in FILE_FORMATS.md.

If you `export` to ASCII FBX format and observe unexpected binary output or an error, this is because ASCII FBX format is not yet implemented in Aspose.3D.

If you `export` an STL file and notice duplicated vertices or increased file `size`, this is due to the lack of vertex deduplication: Aspose.3D uses separate vertices for each face instead of sharing them.

```java
import com.aspose.threed.*;

try {
    Scene scene = new Scene();
    // Attempting to load an unsupported format like USD will throw ImportException
    scene.open("model.usd");
} catch (ImportException e) {
    System.err.println("Format not supported: " + e.getMessage());
}
```

## Error Messages

If `Scene` throws `ImportException` when loading a file, the format may be unsupported or the file may be corrupted. Check the file extension and verify support in `FileFormat.getFormatByExtension()`.

If `FbxExporter` throws `ExportException` during `export`, FBX `export` is not yet implemented — only a stub exists. Use `FileFormat.getCanExport()` to confirm support before calling `export`.

If OBJ `export` produces no MTL file, this is expected behavior: MTL `export` is not yet implemented for OBJ files per current limitations.

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportException` on USD file `load` | USD import is not implemented | Use a supported format like FBX or GLTF |
| `ExportException` when calling `FbxExporter.export()` | FBX `export` stub exists but is non-functional | Avoid FBX `export` until full implementation |
| Missing MTL file after OBJ `export` | MTL `export` not yet implemented | Manually generate MTL or use alternative formats |
| Unexpected geometry duplication in STL | Vertex deduplication not implemented | Expect separate vertices per face; deduplicate post-`export` if needed |
| `ImportException` on ASCII FBX | ASCII FBX format not yet supported | Use binary FBX format instead |
| Animation data lost in FBX round-trip | Advanced FBX features (animations, constraints) not implemented | Avoid relying on animation data until supported |

{{< callout >}}
This is a work-in-progress port. Check FILE_FORMATS.md for current format support status and TODO.md for implementation progress.
{{< /callout >}}

## Getting Help

If `Scene` throws `ImportException` when loading a USD file, the format is not implemented — Aspose.3D does not yet support USD (.usd, .usda, .usdc).

If FBX animations or constraints fail to `load` correctly, this is expected — advanced FBX features are not implemented. The library only supports basic FBX geometry and scene hierarchy.

If ASCII FBX files cause errors, check the file encoding — the library only supports binary FBX; ASCII FBX format is not yet implemented.

- Report bugs or request features at https://github.com/aspose-3d/Aspose.3D.Java/issues
- Review format support status in FILE_FORMATS.md
- Check TODO.md for current implementation progress

## See Also

If `FbxExporter` throws `ExportException` during `export`, the operation is not implemented — only a stub exists. Check the `export` target format and verify it is supported before calling `export()`.

When exporting STL files, expect larger file sizes because vertex deduplication is not implemented — each face uses separate vertices. This behavior is by design per the current implementation.

- [Frequently asked questions](/kb.aspose.org/3d/java/faq/)
- [API reference documentation](/reference.aspose.org/3d/java/api-overview/)
- [Getting started guide](/docs.aspose.org/3d/java/developer-guide/getting-started/)
- [Key features overview](/blog.aspose.org/3d/java/3d-key-features/)
- [Translation transform support](/blog.aspose.org/3d/java/introducing-3d-foss-java/)
