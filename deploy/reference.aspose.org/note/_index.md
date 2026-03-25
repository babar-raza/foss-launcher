---
canonical: https://reference.aspose.org/note/_index/
canonical_import: aspose.note
code_import: aspose.note
date: '2026-03-24T16:57:01Z'
dateModified: '2026-03-24T16:57:01Z'
datePublished: '2026-03-24T16:57:01Z'
description: The library provides core classes for DOM manipulation, layout inspection,
  and PDF export.
display_name: Aspose.Note
family: note
keywords:
- note python
- note python code
- note python google
- python note pdf
- python note pad
- python note taking app
- python note syntax
- python note for professional
lastmod: '2026-03-24T16:57:01Z'
page_role: toc
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Note Reference _Index
slug: _index
title: Reference _Index
type: toc
url: /reference.aspose.org/note/_index/
weight: 5
---

## Capabilities

This section covers the Python API for reading, inspecting, and converting Microsoft OneNote (.one) files using Aspose.Note. The library provides core classes for DOM manipulation, layout inspection, and PDF export.

- Load and inspect OneNote documents via the `Document` class
- Traverse document structure using `CompositeNode` and `DocumentVisitor`
- Extract page history with `GetPageHistory()`
- Convert documents to PDF using `Save()` with `SaveFormat.Pdf`
- Handle errors and file format detection with `FileFormat`, `AsposeNoteError`, and exception types

The `Document` class serves as the root node, exposing `FileFormat` (read-only) and methods like `Count()`, `DetectLayoutChanges()`, and `Save()`. Use `CompositeNode` methods such as `AppendChildLast()` and `RemoveChild()` to modify the node hierarchy programmatically.

For visitor-based processing, implement `DocumentVisitor` and override methods like `VisitPageStart()` and `VisitTitleStart()` to walk the document tree. Tagging features include the static `NoteTag.CreateYellowStar()` method.

## Quick Install

This section covers installation and setup for Aspose.Note, the Python API for reading and processing Microsoft OneNote files. Use pip to install the package, then verify the installation by importing the core `Document` class.

```bash
pip install aspose-note
```

After installation, confirm the package is correctly installed by running `import aspose.note` in a Python interpreter or script. Then instantiate `Document` with a valid .one file path to verify basic functionality.

## Getting Started

This section covers the Python API for reading and manipulating Microsoft OneNote (.one) files using Aspose.Note. The core functionality centers on the `Document` class for loading and saving files, and `CompositeNode`-based classes for building and traversing the document object model.

```python
import aspose.note

doc = aspose.note.Document("input.one")
print(f"Page count: {doc.count()}")
```

## Developer Guide

This section covers the Python API for reading, navigating, and converting OneNote documents using Aspose.Note. The core functionality centers on the `Document` class for loading and saving files, and `CompositeNode`-based classes for DOM traversal and manipulation.

Use `import aspose.note` to access all public types. Key operations include loading `.one` files via `Document`, detecting layout changes with `DetectLayoutChanges()`, and saving output as PDF using `Save()`. `Page` history retrieval and node tree navigation are supported through `GetPageHistory()` and `CompositeNode` methods like `AppendChildLast()` and `FirstChild`.

- Load and save OneNote documents — `Document` class with `Save()` and `FileFormat` support
- Traverse document structure — `CompositeNode` methods (`AppendChildLast`, `FirstChild`, `GetEnumerator`)
- Handle page history — `GetPageHistory()` for version tracking
- Apply tags — `NoteTag.CreateYellowStar()` for marking content
- Manage images — `Image` class with `Alignment` and `Replace()`

## See Also

This section covers the Python API for reading and processing Microsoft OneNote files using Aspose.Note. The API surface includes core classes for document manipulation, node composition, and file format handling.

- [`Document`](#) — load, inspect, and save OneNote files; access page history and detect layout changes.
- [`CompositeNode`](#) — manage hierarchical node structures via append, insert, and remove operations.
- [`DocumentVisitor`](#) — traverse document nodes using the visitor pattern for custom processing.
- [`FileFormat`](#) — enumerate supported OneNote file formats: OneNote 2007, 2010, and Online.
- [`SaveFormat`](#) — specify output format for saving documents (currently PDF only).
