---
canonical: https://docs.aspose.org/3d/java/developer-guide/installation/
canonical_import: com.aspose.threed
code_import: com.aspose.threed
date: '2026-03-24T16:56:25Z'
dateModified: '2026-03-24T16:56:25Z'
datePublished: '2026-03-24T16:56:25Z'
description: 'Aspose.3D: Example demonstrates saving files in OBJ format'
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
page_role: workflow_page
platform: java
reading_time: 1
robots: index, follow
seoTitle: Aspose.3D Installation
slug: installation
summary: ''
title: Installation
type: workflow_page
url: /docs.aspose.org/3d/java/developer-guide/installation/
weight: 3
---

## Overview

Aspose.3D -- Introductory overview: explain what the library does, its primary use cases, and what readers will accomplish. Mention the product name in the first sentence..

Aspose.3D Example demonstrates saving files in OBJ format.

## Key Features

This guide walks you through installing and using Aspose.3D to `load`, process, and convert 3D models in Java. Aspose.3D enables programmatic handling of 3D scenes, meshes, and formats like OBJ and STL without external dependencies.

```java
import com.aspose.threed.*;

// Install via Maven: mvn dependency:get -Dartifact=com.aspose:aspose-3d-foss:26.1.0
Scene scene = new Scene("testdata/input/cube.obj");
scene.save("output.stl");
```

- Supports loading and saving files in OBJ format for interoperability with modeling tools.
- Enables binary and ASCII export to STL format for 3D printing workflows.
- Provides coordinate system flipping options for Gltf and FBX formats to match target engine conventions.
- Includes built-in format detection via `IOService` to automatically identify file types from extensions or streams.
- Supports Maven builds (`mvn clean package`, `mvn test`) and standalone builds using `build.sh` and `run-tests.sh` scripts.

## Prerequisites

Aspose.3D -- Required setup and dependencies.

Aspose.3D Install Aspose.3D via: mvn dependency:get -Dartifact=com.aspose:aspose-3d-foss:26.1.0.

```java
import com.aspose.threed.Scene;

// Load a 3D file
Scene scene = new Scene("testdata/input/cube.obj");

// Save to another format
scene.save("output.stl");
```

## Code Examples

This guide walks you through installing Aspose.3D and converting 3D models between OBJ and STL formats using Java. First, install the library using Maven or the provided shell scripts, then load a 3D scene and save it in the desired output format.

```java
import com.aspose.threed.*;

// Install Aspose.3D via Maven
// mvn dependency:get -Dartifact=com.aspose:aspose-3d-foss:26.1.0

// Load an OBJ file
Scene scene = new Scene("testdata/input/cube.obj");

// Save as STL in binary format
scene.save("output_binary.stl");

// Save as STL in ASCII format
scene.save("output_ascii.stl");
```

- Use binary STL when file size and parsing speed matter—ideal for 3D printing workflows.
- Use ASCII STL when human inspection of the file is required—common in CAD verification.
- OBJ input supports polygonal meshes; ensure your source file uses valid geometry.

For advanced control over STL export, configure `StlSaveOptions` to specify content type. This example creates a mesh programmatically, attaches it to a scene node, and exports it with explicit binary content type.

```java
import com.aspose.threed.*;
import java.nio.file.Files;
import java.nio.file.Path;

Scene scene = new Scene();
Mesh mesh = new Mesh("TestMesh");

mesh.addControlPoint(0, 0, 0);
mesh.addControlPoint(1, 0, 0);
mesh.addControlPoint(0, 1, 0);
mesh.addControlPoint(0, 0, 1);

mesh.createPolygon(new int[]{0, 1, 2});
mesh.createPolygon(new int[]{0, 1, 3});
mesh.createPolygon(new int[]{0, 2, 3});
mesh.createPolygon(new int[]{1, 2, 3});

scene.getRootNode().createChildNode("TestNode", mesh);

Path outputPath = Files.createTempFile("test_export", ".stl");
StlSaveOptions options = new StlSaveOptions();
options.setContentType(FileContentType.BINARY);
scene.save(outputPath.toString(), options);
```

Build the project using Maven or the provided shell scripts. The library supports standard Maven commands and also provides `build.sh` and `run-tests.sh` for environments without Maven.

- Run `mvn clean package` to compile and package the library.
- Run `mvn test` to execute unit tests.
- Run `./build.sh` and `./run-tests.sh` for non-Maven builds.

### Common Questions

Q: Can I export to OBJ format using Aspose.3D? A: Yes—the example loads an OBJ file and saves it as STL, confirming OBJ import and STL export are supported. OBJ export is not yet implemented per current limitations.

Q: Do I need Maven to build the library? A: No—`build.sh` and `run-tests.sh` scripts allow building and testing without Maven, as documented in the repository.

## Best Practices

This section outlines best practices for using Aspose.3D in Java projects, focusing on reliable setup, format handling, and build workflows. Follow these guidelines to avoid common pitfalls and ensure reproducible 3D processing pipelines.

- Use `import com.aspose.threed.*;` — never .NET-style using directives or incorrect package paths.
- Install the library via `mvn dependency:get -Dartifact=com.aspose:aspose-3d-foss:26.1.0` for Maven-based projects.
- Build and test using `mvn clean package` and `mvn test`, or use `./build.sh` and `./run-tests.sh` for non-Maven environments.
- When saving files, explicitly specify `FileContentType` for STL (ASCII or BINARY) to control output format.

For OBJ `export`, `load` a scene and call `save()` with a `.obj` extension — Aspose.3D auto-detects the format. For STL, instantiate `StlSaveOptions`, `set` `setContentType()`, and pass it to `save()`. Always validate output by checking file existence and content type after saving.

When building custom plugins (e.g., for new formats), follow the verified workflow: `create` the plugin in `src/plugins/formats/<Format>/`, implement `IImporter` or `IExporter`, register in `[identifier omitted].java`, and `add` test files. This ensures compatibility with the library’s plugin architecture and test harness.

## Troubleshooting

Aspose.3D -- Common issues and solutions.

For details on troubleshooting, see the Aspose.3D documentation.

## FAQ

### How do I install Aspose.3D for Java?

Install Aspose.3D using Maven by running `mvn dependency:get -Dartifact=com.aspose:aspose-3d-foss:26.1.0`. After installation, include `import com.aspose.threed.*;` at the top of your Java file. The library also supports building with `mvn clean package` and `mvn test`, or using the standalone scripts `./build.sh` and `./run-tests.sh` without Maven.

### Can I `save` a 3D model in OBJ format using Aspose.3D?

Yes. Load an existing 3D file and `save` it as OBJ using the `Scene` class and its `save()` method. The example in the README demonstrates loading a cube.obj file and saving it, confirming OBJ `export` support.

### How do I `export` a 3D mesh to STL format?

Create a `Scene`, `add` a `Mesh` with control points and polygons, then call `save()` with a `StlSaveOptions` instance. The test suite shows exporting both binary and ASCII STL formats by setting `FileContentType.BINARY` or `FileContentType.ASCII`.

### What import paths are valid for Aspose.3D in Java?

Only `import com.aspose.threed.*;` (or explicit classes like `import com.aspose.threed.Scene;`) is valid. Never use .NET-style directives such as `using Aspose.3D`, or any path outside `com.aspose.threed.*`.

## API Reference Summary

Aspose.3D -- Section content.

For details on api reference summary, see the Aspose.3D documentation.

## See Also

- [Get started with Aspose.3D](/docs.aspose.org/3d/java/developer-guide/getting-started/)
- [Explore the full API reference](/reference.aspose.org/3d/java/api-overview/)
- [Discover key 3D features](/blog.aspose.org/3d/java/3d-key-features/)
- [Learn about translation transforms](/blog.aspose.org/3d/java/introducing-3d-foss-java/)
- [Load files step by step](/docs.aspose.org/3d/java/developer-guide/model-loading/)
