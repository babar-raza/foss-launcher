---
canonical: https://kb.aspose.org/email/python/how-to-load-files-python/
canonical_import: aspose.email
code_import: aspose.email
date: '2026-03-24T16:46:41Z'
dateModified: '2026-03-24T16:46:41Z'
datePublished: '2026-03-24T16:46:41Z'
description: The library parses structured email and storage formats via dedicated
  readers and high-level message objects.
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
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Load Files with Aspose.Email FOSS | Guide
slug: how-to-load-files-python
title: How to Load Files with Aspose.Email FOSS
type: howto_article
url: /kb.aspose.org/email/python/how-to-load-files-python/
weight: 11
---

## Problem

You will load Outlook MSG files and Compound File Binary (CFB) containers into Aspose.Email FOSS using the `MapiMessage.from_file()` and `CFBDocument.from_file()` methods. The library parses structured email and storage formats via dedicated readers and high-level message objects.

## Prerequisites

You will load email files (MSG, EML) and inspect their low-level CFB structure using Aspose.Email FOSS. Ensure Python 3.8+ is installed, then install the package via pip and import it using the canonical path `aspose.email`.

- Python 3.8 or later
- Install the package with `pip install aspose.email`
- Import the library using `import aspose.email` (no aliases or alternative paths)

```python
import aspose.email
```

## Loading the File

You will load email files using Aspose.Email FOSS by reading MSG or CFB containers via `MapiMessage.from_file()` or `CFBReader.from_file()`, supporting both direct file paths and stream-based inputs.

- Install the `aspose.email` package via pip: `pip install aspose.email`
- Ensure input files are valid MSG (CFB-based) or raw email formats

### Load an MSG file from a file path

Use `MapiMessage.from_file()` to load a Microsoft Outlook MSG file directly from disk. This method parses the underlying CFB structure and returns a fully populated `MapiMessage` object.

```python
import aspose.email

message = aspose.email.MapiMessage.from_file("message.msg")
```

This returns a `MapiMessage` instance with properties like `subject`, `body`, and `message_class` populated from the file.

### Load a CFB container using a low-level reader

For advanced scenarios, use `CFBReader.from_file()` to inspect raw CFB structure before constructing higher-level objects. This gives access to storages, streams, and directory entries.

```python
reader = aspose.email.CFBReader.from_file("container.msg")
```

The reader object exposes properties like `sector_size`, `major_version`, and methods like `get_stream_data()` for granular access.

### Error handling for malformed files

Wrap file-loading calls in a try-except block to catch `CFBError` for invalid Compound File Binary content or `MsgError` for malformed MSG streams.

```python
try:
    message = aspose.email.MapiMessage.from_file("message.msg")
except aspose.email.CFBError as e:
    print(f"CFB parsing failed: {e}")
except aspose.email.MsgError as e:
    print(f"MSG parsing failed: {e}")
```

This ensures robust handling of corrupted or unsupported email files during loading operations.

### Next steps

After loading, you can inspect message properties, extract attachments via `MapiAttachment`, or convert to [identifier omitted] for further processing.

## Code Example

You will load an Outlook MSG file using Aspose.Email FOSS, inspect its core properties, and print a summary of the message `subject` and class. This example uses the `MapiMessage.from_file()` method to parse the file and access its `subject` and `message_class` properties.

```python
import aspose.email

# Load an MSG file and inspect its properties
msg = aspose.email.MapiMessage.from_file("sample.msg")

# Print summary
print(f"Subject: {msg.subject}")
print(f"Message Class: {msg.message_class}")
```

The `MapiMessage.from_file()` method parses the Compound File Binary (CFB) container and returns a `MapiMessage` instance. You can then read the `subject` and `message_class` properties directly. These properties are defined in the API surface and reflect core MAPI semantics.

This approach works for any valid MSG file conforming to the CFB format. If the file is malformed, Aspose.Email FOSS raises a `CFBError` or `MsgError` depending on the failure point.

## Supported Formats

Aspose.Email FOSS supports loading Outlook MSG files and Compound File Binary (CFB) containers. You can load these formats using `MapiMessage.from_file()` for high-level message access or `CFBReader`/`CFBDocument` for low-level structure inspection.

| Format | Extension | Notes |
|--------|-----------|-------|
| Outlook MSG | `.msg` | Loaded via `MapiMessage.from_file()`; supports full MAPI property inspection and conversion to [identifier omitted] |
| Compound File Binary (CFB) | `.msg`, `.ost`, `.pst`, `.doc`, `.xls`, `.ppt` | Low-level container format; use `CFBReader.from_file()` or `CFBDocument.from_file()` to inspect storages and streams |
| [identifier omitted] (RFC 822) | `.eml` | Converted to/from `MapiMessage` using `MapiMessage.from_email_message()` and `MapiMessage.to_email_message()` |

## See Also

You will load email files using Aspose.Email FOSS to inspect and manipulate low-level message structures. The library supports reading Outlook MSG and CFB containers via dedicated readers and storage classes.

```python
import aspose.email
from aspose.email import MsgReader, MapiMessage

reader = MsgReader("message.msg")
msg = reader.read_message()
print(f"Subject: {msg.subject}")
```

- [Frequently asked questions](/kb.aspose.org/email/python/faq/)
- [Key capabilities overview](/blog.aspose.org/email/python/email-key-features/)
- [Python library introduction](/blog.aspose.org/email/python/introducing-email-foss-python/)
- [Real-world application examples](/kb.aspose.org/email/python/developer-guide/use-cases/)
- [Product overview and details](/products.aspose.org/email/_index/)
