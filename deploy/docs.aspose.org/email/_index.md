---
canonical: https://docs.aspose.org/email/_index/
canonical_import: aspose.email
code_import: aspose.email
date: '2026-03-24T16:46:41Z'
dateModified: '2026-03-24T16:46:41Z'
datePublished: '2026-03-24T16:46:41Z'
description: It supports both structured access to internal storages and streams via
  `CFBReader`/`CFBWriter`, and high-level message handling through `MapiMessage`.
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
seoTitle: Aspose.Email FOSS Docs _Index
slug: _index
title: Docs _Index
type: toc
url: /docs.aspose.org/email/_index/
weight: 2
---

## Capabilities

Aspose.Email FOSS provides low- and high-level APIs for reading, writing, and manipulating Outlook MSG files and Compound File Binary (CFB) containers in Python. It supports both structured access to internal storages and streams via `CFBReader`/`CFBWriter`, and high-level message handling through `MapiMessage`.

- Read and parse MSG files using `MapiMessage.from_file()` and inspect properties like `subject`, `body`, and `message_class`
- Convert between `MapiMessage` and Python's `email.message.EmailMessage` using `from_email_message()` and `to_email_message()`
- Work with attachments, recipients, and embedded messages via `MapiAttachment` and `MapiMessage` properties
- Inspect and modify CFB containers using `CFBReader`, `CFBDocument`, and `CFBWriter` for advanced scenarios

## Quick Install

This section covers installation and setup for Aspose.Email FOSS, the Python API for reading, editing, and converting Outlook MSG files and Compound File Binary (CFB) containers.

```bash
pip install aspose.email
```

After installation, verify the package is correctly installed by importing `aspose.email` and instantiating `MapiMessage` using a sample MSG file. Use `MapiMessage.from_file()` to confirm the library loads MSG content without errors.

## Getting Started

This section covers the Python API for reading, inspecting, and manipulating Outlook MSG files and Compound File Binary (CFB) containers using Aspose.Email FOSS. The library exposes low-level CFB parsing via `CFBReader`, `CFBDocument`, and `CFBWriter`, and high-level email message handling via `MapiMessage`, `MapiAttachment`, and related classes.

```python
import aspose.email

# Load an MSG file and access its subject and body
msg = aspose.email.MapiMessage.from_file("message.msg")
print(msg.subject)
print(msg.body)
```

## Developer Guide

This section covers the Python API for reading, inspecting, and manipulating Outlook MSG files and Compound File Binary (CFB) containers using Aspose.Email FOSS. It focuses on core classes like `MapiMessage` for high-level message handling and `CFBReader`/`CFBWriter` for low-level file structure access.

Use `MapiMessage.from_file()` to load MSG files and access properties like `subject`, `body`, and `message_class`. Convert between `MapiMessage` and `email.message.[identifier omitted]` using `from_email_message()` and `to_email_message()` (implied by API surface). For raw CFB inspection, instantiate `CFBReader.from_file()` to enumerate storages and streams via `iter_storages()` and `get_stream_data()`.

- Load and inspect MSG files with `MapiMessage` and `MsgReader`
- Parse CFB containers using `CFBReader`, `CFBDocument`, and `DirectoryEntry`
- Create or modify messages via `MapiMessage.create()` and `MapiAttachment`
- Work with named properties using `MapiNamedProperty` and `CommonMessagePropertyId`

## See Also

- Read MSG files and inspect MAPI properties using `MapiMessage` and `MsgReader`
- Parse CFB containers and navigate directory entries with `CFBReader` and `DirectoryEntry`
- Convert between `MapiMessage` and Python's `email.message.EmailMessage`
- Work with attachments, recipients, and embedded messages via `MapiAttachment` and `MapiRecipient`
- Write and serialize CFB documents using `CFBWriter` and `CFBStorage`
