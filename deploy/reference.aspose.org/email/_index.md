---
canonical: https://reference.aspose.org/email/_index/
canonical_import: aspose.email
code_import: aspose.email
date: '2026-03-24T16:46:41Z'
dateModified: '2026-03-24T16:46:41Z'
datePublished: '2026-03-24T16:46:41Z'
description: It supports parsing message structures, inspecting MAPI properties, and
  converting between `MapiMessage` and standard `email.message.[identifier omitted]`...
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
page_role: toc
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Email FOSS Reference _Index
slug: _index
title: Reference _Index
type: toc
url: /reference.aspose.org/email/_index/
weight: 5
---

## Capabilities

Aspose.Email FOSS provides low- and high-level APIs for reading, writing, and manipulating Outlook MSG files and Compound File Binary (CFB) containers in Python. It supports parsing message structures, inspecting MAPI properties, and converting between `MapiMessage` and standard `email.message.[identifier omitted]` objects.

- Read and write MSG files using `MapiMessage` with support for subject, body, message class, and transport headers
- Inspect and modify MAPI properties via `MapiProperty`, `MapiNamedProperty`, and `CommonMessagePropertyId`
- Handle attachments and embedded messages through `MapiAttachment`
- Parse CFB containers using `CFBReader` and serialize them with `CFBWriter`
- Convert between `MapiMessage` and `email.message.EmailMessage` for interoperability

## Quick Install

This section covers installation and setup for Aspose.Email FOSS, the Python API for reading, writing, and converting Outlook MSG files and Compound File Binary (CFB) containers.

```bash
pip install aspose.email
```

After installation, verify the package is correctly installed by importing `aspose.email` and instantiating `MapiMessage` using a known MSG file path. Use `MapiMessage.from_file()` to confirm the library loads and parses MSG content without errors.

## Getting Started

This section covers the Python API for reading, inspecting, and manipulating Outlook MSG files and Compound File Binary (CFB) containers using Aspose.Email FOSS. The library exposes core classes like `MapiMessage` for high-level message handling and `CFBReader`/`CFBWriter` for low-level file structure access.

```python
import aspose.email

# Load an MSG file and access its subject and body
msg = aspose.email.MapiMessage.from_file("message.msg")
print(msg.subject)
print(msg.body)
```

## Developer Guide

This section covers the Python API for reading, inspecting, and manipulating Outlook MSG files and Compound File Binary (CFB) containers using Aspose.Email FOSS. The core classes include `MapiMessage` for high-level message handling, `CFBReader`/`CFBWriter` for low-level CFB parsing and serialization, and supporting types like `MapiAttachment`, `MapiProperty`, and `CommonMessagePropertyId` for structured access to message metadata.

Developers can load MSG files via `MapiMessage.from_file()` or convert from [identifier omitted] using `MapiMessage.from_email_message()`. For deeper inspection, `CFBReader` exposes raw CFB structure through methods like `get_stream_data()` and `iter_storages()`. Attachments and embedded messages are handled via `MapiAttachment`, with support for both binary data and nested `MapiMessage` instances.

- Load and inspect MSG files with `MapiMessage` and `MsgReader`
- Parse CFB containers using `CFBReader`, `CFBDocument`, and `CFBWriter`
- Manage message properties via `MapiProperty`, `CommonMessagePropertyId`, and `MapiNamedProperty`
- Handle attachments and embedded messages with `MapiAttachment`

## See Also

This section covers the Python API for MSG and CFB file processing in Aspose.Email FOSS. The library provides classes for reading, writing, and manipulating Outlook message formats and Compound File Binary containers.

- `MapiMessage` — create, load, and manipulate MSG messages with full property and attachment support
- `CFBReader` and `CFBWriter` — parse and serialize Compound File Binary containers at the low level
- `MapiAttachment` and `MapiRecipient` — work with message attachments and recipients
- `MsgDocument` and `MsgReader` — read structured MSG files and extract embedded content
- `CommonMessagePropertyId` and `PropertyId` — access standard MAPI property identifiers
