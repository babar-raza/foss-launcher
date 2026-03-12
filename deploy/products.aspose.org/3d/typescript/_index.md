---
page_role: howto_article
# Static
layout: "family"
type: "_default"

# Head
head_title: "Aspose.3D FOSS for TypeScript | Open-Source 3D Library for Node.js"
head_description: "Aspose.3D FOSS for TypeScript is a free, MIT-licensed library for loading, building, and exporting 3D scenes in OBJ, glTF/GLB, STL, 3MF, FBX, and COLLADA formats. Strong TypeScript types, single dependency."

# Header
title: "Aspose.3D FOSS for TypeScript"
description: "Load, construct, transform, and export 3D scenes from Node.js — fully typed, open-source, and production-ready with a single npm install."
button:
  enable: true

# Overview
overview:
  enable: true
  content: |
    Aspose.3D FOSS for TypeScript is a MIT-licensed library for working with 3D file formats in Node.js applications. Install it with a single `npm install @aspose/3d` command and start reading, constructing, and writing 3D scenes in TypeScript immediately — no native addons to compile, no external SDKs to install, and no renderer required.

    The library exposes a fully typed scene-graph API built around `Scene`, `Node`, `Entity`, `Mesh`, `Camera`, `Light`, and `Transform` — the same conceptual model used by professional 3D tools. Format support includes OBJ (Wavefront, with .mtl material loading), glTF 2.0 and GLB binary (PBR materials, binary mode via `GltfSaveOptions`), STL (binary and ASCII, full roundtrip), COLLADA (DAE), 3MF, and FBX. Per-format option classes such as `ObjLoadOptions` and `GltfSaveOptions` give you precise control over coordinate-system orientation, scale, normal normalization, binary vs. JSON output, and material loading — without writing any format-specific parsing code.

    Because Aspose.3D FOSS targets Node.js 16, 18, 20, and 22+ with TypeScript 5.0+ and compiles to CommonJS, it runs identically on developer workstations, Linux CI runners, Docker containers, and serverless functions. The library ships with strict TypeScript compiler settings (`noImplicitAny`, `strictNullChecks`) so your IDE provides full autocomplete and compile-time safety for every 3D API call. Its single runtime dependency — `xmldom` — is installed automatically and requires no additional configuration.

# Testimonials section
testimonialswrapper:
  enable: true
  title: "What Developers Are Saying"
  subtitle: "Developer feedback on Aspose.3D FOSS for TypeScript."
  caseStudiesLink: "https://library.conholdate.app/org/aspose/files/aspose.3d"
  tmessage: "We needed to validate, re-orient, and re-export thousands of OBJ and GLB assets as part of our Node.js CI pipeline. Aspose.3D FOSS installed in seconds, shipped with full TypeScript types, and handled every edge case our test corpus threw at it — including coordinate-system flipping and binary STL roundtrips. It saved us weeks of custom parser work."
  poster: "Engineering Lead | Independent Game Studio"

# Support
support:
  enable: true

# Back to top
back_to_top:
  enable: true
---
