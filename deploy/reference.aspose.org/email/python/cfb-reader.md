---
canonical: https://reference.aspose.org/email/python/cfb-reader/
canonical_import: aspose.email
code_import: aspose.email
date: '2026-03-24T16:46:41Z'
dateModified: '2026-03-24T16:46:41Z'
datePublished: '2026-03-24T16:46:41Z'
description: It serves as the in-memory representation used by the `CFBWriter` to
  serialize CFB containers deterministically.
display_name: Aspose.Email FOSS
family: email
keywords:
- email python
- email python library
- email python package
- email python module
- email python install
- email python code
- email python documentation
- email python regex
lastmod: '2026-03-24T16:46:41Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: The CFBDocument class represents a mutable Compound File
slug: cfb-reader
title: The CFBDocument class represents a mutable Compound File Binary (CFB) documen...
type: reference_object_page
url: /reference.aspose.org/email/python/cfb-reader/
weight: 19
---

## Overview

The `CFBDocument` class represents a mutable Compound File Binary (CFB) document and can be constructed from a file or a `CFBReader` instance. It serves as the in-memory representation used by the `CFBWriter` to serialize CFB containers deterministically.

```python
from aspose.email import CFBDocument, CFBReader

reader = CFBReader.from_file("example.msg")
document = CFBDocument.from_reader(reader)
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `from_reader` | `from_reader`(reader: `CFBReader`) -> '`CFBDocument`' | Constructs a document from a `CFBReader` instance. |
| `from_file` | `from_file`(path: Path | str) -> '`CFBDocument`' | Constructs a document by reading a CFB file. |

## Constructor

The `CFBDocument` class represents a mutable Compound File Binary (CFB) document and can be constructed from a file or a `CFBReader` instance. It serves as an in-memory representation of the CFB structure for modification and serialization via `CFBWriter`.

| Method | Signature | Description |
|--------|-----------|-------------|
| `from_file` | `from_file(path: Path | str) -> 'CFBDocument'` | Constructs a `CFBDocument` by reading a CFB file. |
| `from_reader` | `from_reader(reader: CFBReader) -> 'CFBDocument'` | Constructs a `CFBDocument` from an existing `CFBReader` instance. |

```python
import aspose.email
from aspose.email import CFBReader, CFBDocument

reader = CFBReader.from_file("example.msg")
document = CFBDocument.from_reader(reader)
```

## Properties

| Name | Type | Description |
|------|------|-------------|
| root_storage | `CFBStorage` | The root storage node of the CFB document. |
| header | `Header` | The CFB header record defining geometry and allocation chain entry points. |
| storages | list[`CFBStorage`] | List of top-level storage nodes in the document. |
| streams | list[`CFBStream`] | List of top-level stream nodes in the document. |

```python
from aspose.email import CFBDocument, CFBReader

reader = CFBReader.from_file("example.msg")
document = CFBDocument.from_reader(reader)
print(document.header.sector_size)
```

## Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `from_reader(reader: CFBReader) -> 'CFBDocument'` | `CFBDocument` | Constructs a `CFBDocument` from an existing `CFBReader` instance. |
| `from_file(path: Path | str) -> 'CFBDocument'` | `CFBDocument` | Constructs a `CFBDocument` by reading a CFB file directly. |

```python
from aspose.email import CFBDocument, CFBReader

# Load a CFB file and construct a document
reader = CFBReader.from_file("example.msg")
document = CFBDocument.from_reader(reader)
```

## Example

The following example demonstrates constructing a `CFBDocument` from a file using `CFBDocument.from_file()`, then reading stream data via a `CFBReader` instance. It shows how to open a CFB container, inspect directory entries, and extract raw stream bytes using `get_stream_data()`.

```python
import aspose.email
from aspose.email import CFBReader, CFBDocument

# Load CFB container from file
reader = CFBReader.from_file("example.msg")

# Resolve a stream by name and read its data
stream_id = reader.resolve_path("\x01Storage\x01Stream")
data = reader.get_stream_data(stream_id)

# Construct a CFBDocument from the reader
doc = CFBDocument.from_reader(reader)

print(f"Stream data length: {len(data)} bytes")
```

## See Also

The `CFBDocument` class represents a mutable Compound File Binary (CFB) document and can be constructed from a file or a `CFBReader` instance. Related classes include `CFBReader` for reading CFB containers, `CFBWriter` for serialization, and `DirectoryEntry` for inspecting container structure.

```python
from aspose.email import CFBReader, CFBDocument

reader = CFBReader.from_file("example.msg")
document = CFBDocument.from_reader(reader)
entry = reader.get_entry(reader.iter_storages().__next__())
print(entry.is_storage(), entry.is_stream(), entry.is_root())
```

- [Aspose.Email FOSS API reference](/reference.aspose.org/email/python/api-overview/)
- [Key features overview](/blog.aspose.org/email/python/email-key-features/)
- [Introducing Aspose.Email FOSS Python](/blog.aspose.org/email/python/introducing-email-foss-python/)
- [Convert file formats guide](/kb.aspose.org/email/python/how-to-convert-files-python/)
- [Fix common errors](/kb.aspose.org/email/python/how-to-fix-files-errors-python/)
